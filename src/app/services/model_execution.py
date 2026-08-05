"""Provider-neutral execution for catalog-backed model deployments."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Mapping, Sequence

import httpx

from src.app.catalogs.models import (
    ModelCatalogEntry,
    ModelDeployment,
    ModelEndpoint,
)
from src.app.catalogs.providers import ProviderId
from src.app.models.provider import ProviderCredential
from src.app.repositories.providers.provider_repository import ProviderRepository
from src.app.services.models.service import ModelCatalogService
from src.app.services.providers.secret import SecretService


class ModelExecutionError(RuntimeError):
    """Base error raised when a catalog model cannot execute."""


class ModelDeploymentUnavailableError(ModelExecutionError):
    """Raised when no enabled provider deployment exists for a model."""


class ModelExecutionResponseError(ModelExecutionError):
    """Raised when a provider response cannot be normalized."""


@dataclass(frozen=True, slots=True)
class ModelExecutionResult:
    """Normalized response from one configured catalog model."""

    text: str
    provider_id: ProviderId
    model_id: str
    input_tokens: int
    output_tokens: int
    duration_ms: int


class ModelExecutionService:
    """Execute logical model IDs through enabled workspace deployments."""

    def __init__(
        self,
        *,
        model_catalog_service: ModelCatalogService,
        provider_repository: ProviderRepository,
        secret_service: SecretService,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Store catalog, credential, secret, and HTTP dependencies."""

        self._model_catalog_service = model_catalog_service
        self._provider_repository = provider_repository
        self._secret_service = secret_service
        self._client = client

    async def execute(
        self,
        *,
        workspace_id: str,
        model_id: str,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
    ) -> ModelExecutionResult:
        """Invoke one enabled deployment for a logical catalog model."""

        model = self._model_catalog_service.require_model(model_id)
        deployment, credential = await self._resolve_deployment(
            workspace_id=workspace_id,
            model=model,
        )
        api_key = self._decrypt_api_key(credential)
        start = perf_counter()

        try:
            response = await self._post_completion(
                deployment=deployment,
                credential=credential,
                api_key=api_key,
                prompt=prompt,
                system_prompt=system_prompt,
                json_mode=json_mode,
            )
        finally:
            api_key = None

        return self._to_result(
            response=response,
            deployment=deployment,
            model_id=model.id,
            duration_ms=round((perf_counter() - start) * 1000),
        )

    async def _resolve_deployment(
        self,
        *,
        workspace_id: str,
        model: ModelCatalogEntry,
    ) -> tuple[ModelDeployment, ProviderCredential]:
        """Select the first enabled configured deployment in catalog order."""

        for deployment in model.deployments:
            credential = await self._provider_repository.get(
                workspace_id,
                deployment.provider_id.value,
            )
            if credential is not None and credential.enabled and credential.base_url:
                return deployment, credential

        raise ModelDeploymentUnavailableError(
            f"Model '{model.id}' has no enabled configured deployment."
        )

    def _decrypt_api_key(self, credential: ProviderCredential) -> str | None:
        """Decrypt the credential only for the duration of one request."""

        if credential.key_ciphertext is None:
            return None
        return self._secret_service.decrypt_secret(credential.key_ciphertext)

    async def _post_completion(
        self,
        *,
        deployment: ModelDeployment,
        credential: ProviderCredential,
        api_key: str | None,
        prompt: str,
        system_prompt: str | None,
        json_mode: bool,
    ) -> Mapping[str, object]:
        """Send one request using the deployment's declared endpoint."""

        url, headers, payload = self._request_parts(
            deployment=deployment,
            credential=credential,
            api_key=api_key,
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=json_mode,
        )
        response = await self._request_json(
            url=url,
            headers=headers,
            payload=payload,
        )
        return response

    def _request_parts(
        self,
        *,
        deployment: ModelDeployment,
        credential: ProviderCredential,
        api_key: str | None,
        prompt: str,
        system_prompt: str | None,
        json_mode: bool,
    ) -> tuple[str, dict[str, str], dict[str, object]]:
        """Build provider-specific request parts from one deployment."""

        base_url = credential.base_url
        if base_url is None:
            raise ModelDeploymentUnavailableError(
                f"Provider '{credential.provider}' has no base URL."
            )

        if deployment.endpoint == ModelEndpoint.MESSAGES:
            headers = {
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            }
            if api_key:
                headers['x-api-key'] = api_key
            payload: dict[str, object] = {
                'model': deployment.provider_model_id,
                'max_tokens': deployment.max_output_tokens or 4096,
                'messages': [{'role': 'user', 'content': prompt}],
            }
            if system_prompt:
                payload['system'] = system_prompt
            return f"{base_url.rstrip('/')}/messages", headers, payload

        headers = {'content-type': 'application/json'}
        if api_key:
            headers['authorization'] = f'Bearer {api_key}'
        messages = [{'role': 'user', 'content': prompt}]
        if system_prompt:
            messages.insert(0, {'role': 'system', 'content': system_prompt})

        if deployment.endpoint == ModelEndpoint.CHAT_COMPLETIONS:
            payload: dict[str, object] = {
                'model': deployment.provider_model_id,
                'messages': messages,
                'max_tokens': deployment.max_output_tokens or 4096,
            }
            if json_mode:
                payload['response_format'] = {'type': 'json_object'}
            return (
                f"{base_url.rstrip('/')}/chat/completions",
                headers,
                payload,
            )

        if deployment.endpoint == ModelEndpoint.RESPONSES:
            payload = {
                'model': deployment.provider_model_id,
                'input': messages,
            }
            return f"{base_url.rstrip('/')}/responses", headers, payload

        raise ModelExecutionError(
            f"Model endpoint '{deployment.endpoint}' is not supported."
        )

    async def _request_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> Mapping[str, object]:
        """Send one JSON completion request and normalize transport failures."""

        try:
            if self._client is not None:
                response = await self._client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
            else:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                    )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as error:
            raise ModelExecutionError(
                f"Model provider returned HTTP {error.response.status_code}."
            ) from error
        except httpx.RequestError as error:
            raise ModelExecutionError('Model provider could not be reached.') from error
        except ValueError as error:
            raise ModelExecutionResponseError(
                'Model provider returned invalid JSON.'
            ) from error

        if not isinstance(body, Mapping):
            raise ModelExecutionResponseError(
                'Model provider response must be a JSON object.'
            )
        return body

    @staticmethod
    def _to_result(
        *,
        response: Mapping[str, object],
        deployment: ModelDeployment,
        model_id: str,
        duration_ms: int,
    ) -> ModelExecutionResult:
        """Normalize response text and usage for each catalog endpoint."""

        text = _response_text(response, deployment.endpoint)
        usage = response.get('usage')
        usage_data = usage if isinstance(usage, Mapping) else {}
        return ModelExecutionResult(
            text=text,
            provider_id=deployment.provider_id,
            model_id=model_id,
            input_tokens=_usage_value(usage_data, 'input_tokens', 'prompt_tokens'),
            output_tokens=_usage_value(
                usage_data,
                'output_tokens',
                'completion_tokens',
            ),
            duration_ms=duration_ms,
        )


def _response_text(response: Mapping[str, object], endpoint: ModelEndpoint) -> str:
    """Extract non-empty generated text from one provider response."""

    if endpoint == ModelEndpoint.MESSAGES:
        content = response.get('content')
        if isinstance(content, Sequence) and not isinstance(content, str):
            parts = [
                item.get('text')
                for item in content
                if isinstance(item, Mapping) and isinstance(item.get('text'), str)
            ]
            if parts:
                return ''.join(parts).strip()

    if endpoint == ModelEndpoint.CHAT_COMPLETIONS:
        choices = response.get('choices')
        if isinstance(choices, Sequence) and not isinstance(choices, str):
            first = choices[0] if choices else None
            if isinstance(first, Mapping):
                message = first.get('message')
                if isinstance(message, Mapping) and isinstance(message.get('content'), str):
                    return str(message['content']).strip()

    if endpoint == ModelEndpoint.RESPONSES:
        output_text = response.get('output_text')
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

    raise ModelExecutionResponseError('Model provider response contains no text.')


def _usage_value(
    usage: Mapping[str, object],
    *keys: str,
) -> int:
    """Return the first non-negative integer usage value from aliases."""

    for key in keys:
        value = usage.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return 0
