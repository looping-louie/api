"""Tests for catalog-backed provider-neutral model execution."""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from typing import Any

import httpx
import pytest

from src.app.catalogs.models import (
    CatalogIndex,
    ModelCapability,
    ModelCatalogEntry,
    ModelEndpoint,
    ModelLab,
    ModelOffering,
    ProviderModelOffering,
)
from src.app.catalogs.providers import ProviderId
from src.app.models.linked_service import LinkedService
from src.app.services.models import (
    ModelDeploymentUnavailableError,
    ModelExecutionService,
)
from tests.factories.models import build_offering, build_provider


class FakeModelCatalogService:
    """Return one catalog model for execution-service tests."""

    def __init__(
        self,
        model_entry: ModelCatalogEntry,
        offerings: tuple[ModelOffering, ...],
    ) -> None:
        """Store the test model returned by require_model."""

        self._model_entry = model_entry
        self._offerings = offerings

    def require_model(self, model_id: str) -> ModelCatalogEntry:
        """Return the configured model when its ID matches."""

        assert model_id == self._model_entry.id
        return self._model_entry

    def offerings_for_model(
        self,
        model_entry: ModelCatalogEntry,
    ) -> tuple[ModelOffering, ...]:
        """Return provider-owned offerings for the configured test model."""

        assert model_entry == self._model_entry
        return self._offerings


class FakeLinkedServiceRepository:
    """Store legacy workspace-owner linked services in memory."""

    def __init__(self, linked_services: list[LinkedService]) -> None:
        """Index linked services by the legacy workspace and identifier."""

        self._linked_services = {
            ('workspace-1', linked_service.id): linked_service
            for linked_service in linked_services
        }

    async def get_for_workspace_owner(
        self,
        workspace_id: str,
        service_id: str,
    ) -> LinkedService | None:
        """Return one linked service through the workspace owner."""

        return self._linked_services.get((workspace_id, service_id))


class FakeSecretService:
    """Return a deterministic plaintext key for encrypted test credentials."""

    def decrypt_secret(self, ciphertext: str) -> str:
        """Decode the expected test cipher value."""

        assert ciphertext == 'ciphertext'
        return 'test-key'


def model() -> ModelCatalogEntry:
    """Build one provider-neutral logical model."""

    return ModelCatalogEntry(
        id='model-1',
        name='Model',
        vendor='Test',
        lab=ModelLab.OPENAI,
        family='Test',
        description='Test model.',
        released_at=date(2026, 1, 1),
        capabilities=frozenset({ModelCapability.TEXT}),
    )


def linked_service(provider: ProviderId) -> LinkedService:
    """Build one enabled configured linked service."""

    now = datetime(2026, 8, 3, tzinfo=UTC)
    return LinkedService(
        id='linked-service-1',
        user_id='user-1',
        name='Selected provider',
        provider_type=provider.value,
        enabled=True,
        key_trimmed='test-****************',
        key_ciphertext='ciphertext',
        key_version=1,
        base_url=f'https://{provider}.linked.example/v1',
        version=1,
        created_at=now,
        updated_at=now,
    )


def service(
    *,
    offerings: tuple[ProviderModelOffering, ...],
    provider_id: ProviderId = ProviderId.TOGETHER,
    linked_services: list[LinkedService],
    handler: Any,
) -> ModelExecutionService:
    """Build the executor with a transport that captures no real network calls."""

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model_entry = model()
    catalog_index = CatalogIndex(
        models=(model_entry,),
        providers=(build_provider(
            *offerings,
            provider_id=provider_id,
        ),),
    )
    return ModelExecutionService(
        model_catalog_service=FakeModelCatalogService(
            model_entry,
            catalog_index.offerings_for_model(model_entry.id),
        ),
        secret_service=FakeSecretService(),
        linked_service_repository=FakeLinkedServiceRepository(linked_services),
        client=client,
    )


@pytest.mark.asyncio
async def test_executes_chat_completion_for_enabled_catalog_deployment() -> None:
    """Configured Together deployment uses its catalog model and bearer key."""

    offering = build_offering()

    def handler(request: httpx.Request) -> httpx.Response:
        """Assert the outgoing OpenAI-compatible chat request."""

        assert request.url == 'https://together.linked.example/v1/chat/completions'
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
        offerings=(offering,),
        linked_services=[linked_service(ProviderId.TOGETHER)],
        handler=handler,
    ).execute(
        workspace_id='workspace-1',
        linked_service_id='linked-service-1',
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

    offering = build_offering(
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
        offerings=(offering,),
        linked_services=[linked_service(ProviderId.TOGETHER)],
        handler=handler,
    ).execute(
        workspace_id='workspace-1',
        linked_service_id='linked-service-1',
        model_id='model-1',
        prompt='User prompt.',
    )


@pytest.mark.asyncio
async def test_executes_chat_completion_in_json_mode() -> None:
    """JSON mode requests an OpenAI-compatible structured response."""

    offering = build_offering()

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
        offerings=(offering,),
        linked_services=[linked_service(ProviderId.TOGETHER)],
        handler=handler,
    ).execute(
        workspace_id='workspace-1',
        linked_service_id='linked-service-1',
        model_id='model-1',
        prompt='Return JSON.',
        json_mode=True,
    )

    assert result.text == '{"ok": true}'


@pytest.mark.asyncio
async def test_executes_model_through_selected_linked_service() -> None:
    """Selected linked services define the execution route."""

    offering = build_offering()

    def handler(request: httpx.Request) -> httpx.Response:
        """Assert execution uses the selected service URL and credential."""

        assert request.url == (
            'https://together.linked.example/v1/chat/completions'
        )
        assert request.headers['authorization'] == 'Bearer test-key'
        return httpx.Response(
            200,
            json={
                'choices': [{'message': {'content': 'Generated text.'}}],
            },
        )

    executor = service(
        offerings=(offering,),
        linked_services=[linked_service(ProviderId.TOGETHER)],
        handler=handler,
    )

    result = await executor.execute(
        workspace_id='workspace-1',
        linked_service_id='linked-service-1',
        model_id='model-1',
        prompt='User prompt.',
    )

    assert result.model_id == 'model-1'
    assert result.provider_id == ProviderId.TOGETHER


@pytest.mark.asyncio
async def test_executes_anthropic_messages_deployment() -> None:
    """Configured Anthropic deployment uses the native messages protocol."""

    offering = build_offering(
        provider_model_id='claude-test',
        endpoint=ModelEndpoint.MESSAGES,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        """Assert the outgoing Anthropic messages request."""

        assert request.url == 'https://anthropic.linked.example/v1/messages'
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
        offerings=(offering,),
        provider_id=ProviderId.ANTHROPIC,
        linked_services=[linked_service(ProviderId.ANTHROPIC)],
        handler=handler,
    ).execute(
        workspace_id='workspace-1',
        linked_service_id='linked-service-1',
        model_id='model-1',
        prompt='User prompt.',
        system_prompt='System instructions.',
    )

    assert result.text == 'Generated text.'
    assert result.provider_id == ProviderId.ANTHROPIC


@pytest.mark.asyncio
async def test_rejects_model_without_enabled_configured_deployment() -> None:
    """A logical model cannot execute without its selected linked service."""

    offering = build_offering(
        provider_model_id='gpt-test',
        endpoint=ModelEndpoint.RESPONSES,
    )

    with pytest.raises(ModelDeploymentUnavailableError):
        await service(
            offerings=(offering,),
            provider_id=ProviderId.OPENAI,
            linked_services=[],
            handler=lambda request: httpx.Response(500),
        ).execute(
            workspace_id='workspace-1',
            linked_service_id='linked-service-1',
            model_id='model-1',
            prompt='User prompt.',
        )
