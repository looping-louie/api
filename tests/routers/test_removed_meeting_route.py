"""Regression coverage for the removed legacy orchestration endpoint."""

from src.app.routers import router


def test_legacy_orchestration_route_is_not_registered() -> None:
    """The unversioned legacy run route must no longer be exposed."""

    registered_paths = {
        route.path
        for route in router.routes
    }

    assert "/meeting/run" not in registered_paths
