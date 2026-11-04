"""Domain errors raised while managing provider configuration."""


class ProviderError(Exception):
    """Base error for provider operations."""


class UnknownProviderError(ProviderError):
    """Raised when a provider is not part of the curated catalog."""

    def __init__(self, *, provider_id: str) -> None:
        super().__init__(f"Unknown provider '{provider_id}'.")
        self.provider_id = provider_id


class ProviderConfigurationError(ProviderError):
    """Raised when stored or supplied provider configuration is invalid."""

    def __init__(self, *, provider_id: str, reason: str) -> None:
        super().__init__(
            f"Provider '{provider_id}' configuration is invalid: {reason}."
        )
        self.provider_id = provider_id
        self.reason = reason
