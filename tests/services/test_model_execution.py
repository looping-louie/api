"""Tests for catalog-backed provider-neutral model execution."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

import httpx
import pytest

from src.app.catalogs.models import (
    ModelCapability,
    ModelCatalogEntry,
    ModelDeployment,
    ModelEndpoint,
)
from src.app.catalogs.providers import ProviderId
from src.app.models.provider import ProviderCredential
from src.app.services.model_execution import (
    ModelDeploymentUnavailableError,
    ModelExecutionService,
)


class FakeModelCatalogService:
    """Return one catalog model for execution-service tests."""

    def __init__(self, model: ModelCatalogEntry) -> None:
        """Store the test model returned by require_model."""

        self.model = model

    def require_model(self, model_id: str) -> ModelCatalogEntry:
        """Return the configured model when its ID matches."""

        assert model_id == self.model.id
        return self.model


class FakeProviderRepository:
    """Store workspace provider credentials in memory."""

    def __init__(self, credentials: list[ProviderCredential]) -> None:
        """Index test credentials by workspace and provider."""

        self.credentials = {
            (credential.workspace_id, credential.provider): credential
            for credential in credentials
        }

    async def get(
        self,
        workspace_id: str,
        provider: str,
    ) -> ProviderCredential | None:
        """Return one stored provider credential."""

        return self.credentials.get((workspace_id, provider))


class FakeSecretService:
    """Return a deterministic plaintext key for encrypted test credentials."""

    def decrypt_secret(self, ciphertext: str) -> str:
        """Decode the expected test cipher value."""

        assert ciphertext == 'ciphertext'
        return 'test-key'


def model(*deployments: ModelDeployment) -> ModelCatalogEntry:
    """Build one logical model with the supplied deployment order."""

    return ModelCatalogEntry(
        id='model-1',
        name='Model',
        vendor='Test',
        family='Test',
        description='Test model.',
        capabilities=frozenset({ModelCapability.TEXT}),
        deployments=deployments,
    )


def credential(provider: ProviderId) -> ProviderCredential:
    """Build one enabled configured provider credential."""

    now = datetime(2026, 8, 3, tzinfo=UTC)
    return ProviderCredential(
        id=f'{provider}-credential',
        workspace_id='workspace-1',
        provider=provider.value,
        enabled=True,
        enabled_by='user-1',
        enabled_on=now,
        key_trimmed='test-****************',
        key_ciphertext='ciphertext',
        key_version=1,
        base_url=f'https://{provider}.example/v1',
        created_at=now,
        updated_at=now,
    )


def service(
    *,
    model_entry: ModelCatalogEntry,
    credentials: list[ProviderCredential],
    handler: Any,
) -> ModelExecutionService:
    """Build the executor with a transport that captures no real network calls."""

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ModelExecutionService(
        model_catalog_service=FakeModelCatalogService(model_entry),
        provider_repository=FakeProviderRepository(credentials),
        secret_service=FakeSecretService(),
        client=client,
    )


@pytest.mark.asyncio
async def test_executes_chat_completion_for_enabled_catalog_deployment() -> None:
    """Configured Together deployment uses its catalog model and bearer key."""

    deployment = ModelDeployment(
        provider_id=ProviderId.TOGETHER,
        provider_model_id='vendor/model-1',
        endpoint=ModelEndpoint.CHAT_COMPLETIONS,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        """Assert the outgoing OpenAI-compatible chat request."""

        assert request.url == 'https://together.example/v1/chat/completions'
        assert request.headers['authorization'] == 'Bearer test-key'
        assert json.loads(request.content) == {
            'model': 'vendor/model-1',
            'max_tokens': 4096,
            'messages': [
                {'role': 'system', 'content': 'System instructions.'},
                {'role': 'user', 'content': 'User prompt.'},
            ],
        }
        return httpx.Response(
            200,
            json={
                'choices': [{'message': {'content': 'Generated text.'}}],
                'usage': {'prompt_tokens': 3, 'completion_tokens': 2},
            },
        )

    result = await service(
        model_entry=model(deployment),
        credentials=[credential(ProviderId.TOGETHER)],
        handler=handler,
    ).execute(
        workspace_id='workspace-1',
        model_id='model-1',
        prompt='User prompt.',
        system_prompt='System instructions.',
    )

    assert result.text == 'Generated text.'
    assert result.provider_id == ProviderId.TOGETHER
    assert result.input_tokens == 3
    assert result.output_tokens == 2


@pytest.mark.asyncio
async def test_executes_chat_completion_with_deployment_output_limit() -> None:
    """A catalog deployment overrides the chat completion output default."""

    deployment = ModelDeployment(
        provider_id=ProviderId.TOGETHER,
        provider_model_id='vendor/model-1',
        endpoint=ModelEndpoint.CHAT_COMPLETIONS,
        max_output_tokens=8192,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        """Assert the configured output limit reaches the provider request."""

        assert json.loads(request.content)['max_tokens'] == 8192
        return httpx.Response(
            200,
            json={'choices': [{'message': {'content': 'Generated text.'}}]},
        )

    await service(
        model_entry=model(deployment),
        credentials=[credential(ProviderId.TOGETHER)],
        handler=handler,
    ).execute(
        workspace_id='workspace-1',
        model_id='model-1',
        prompt='User prompt.',
    )


@pytest.mark.asyncio
async def test_executes_chat_completion_in_json_mode() -> None:
    """JSON mode requests an OpenAI-compatible structured response."""

    deployment = ModelDeployment(
        provider_id=ProviderId.TOGETHER,
        provider_model_id='vendor/model-1',
        endpoint=ModelEndpoint.CHAT_COMPLETIONS,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        """Assert the structured-output request option."""

        assert json.loads(request.content)['response_format'] == {
            'type': 'json_object',
        }
        return httpx.Response(
            200,
            json={'choices': [{'message': {'content': '{"ok": true}'}}]},
        )

    result = await service(
        model_entry=model(deployment),
        credentials=[credential(ProviderId.TOGETHER)],
        handler=handler,
    ).execute(
        workspace_id='workspace-1',
        model_id='model-1',
        prompt='Return JSON.',
        json_mode=True,
    )

    assert result.text == '{"ok": true}'


@pytest.mark.asyncio
async def test_executes_anthropic_messages_deployment() -> None:
    """Configured Anthropic deployment uses the native messages protocol."""

    deployment = ModelDeployment(
        provider_id=ProviderId.ANTHROPIC,
        provider_model_id='claude-test',
        endpoint=ModelEndpoint.MESSAGES,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        """Assert the outgoing Anthropic messages request."""

        assert request.url == 'https://anthropic.example/v1/messages'
        assert request.headers['x-api-key'] == 'test-key'
        assert json.loads(request.content)['system'] == 'System instructions.'
        return httpx.Response(
            200,
            json={
                'content': [{'type': 'text', 'text': 'Generated text.'}],
                'usage': {'input_tokens': 3, 'output_tokens': 2},
            },
        )

    result = await service(
        model_entry=model(deployment),
        credentials=[credential(ProviderId.ANTHROPIC)],
        handler=handler,
    ).execute(
        workspace_id='workspace-1',
        model_id='model-1',
        prompt='User prompt.',
        system_prompt='System instructions.',
    )

    assert result.text == 'Generated text.'
    assert result.provider_id == ProviderId.ANTHROPIC


@pytest.mark.asyncio
async def test_rejects_model_without_enabled_configured_deployment() -> None:
    """A logical model cannot execute without an enabled deployment credential."""

    deployment = ModelDeployment(
        provider_id=ProviderId.OPENAI,
        provider_model_id='gpt-test',
        endpoint=ModelEndpoint.RESPONSES,
    )

    with pytest.raises(ModelDeploymentUnavailableError):
        await service(
            model_entry=model(deployment),
            credentials=[],
            handler=lambda request: httpx.Response(500),
        ).execute(
            workspace_id='workspace-1',
            model_id='model-1',
            prompt='User prompt.',
        )
