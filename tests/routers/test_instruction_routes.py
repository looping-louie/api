from src.app.routers.personas import router as personas_router
from src.app.routers.skills import router as skills_router


def test_skill_action_routes_are_registered() -> None:
    routes = {
        (
            route.path,
            frozenset(route.methods or set()),
        )
        for route in skills_router.routes
    }

    assert (
        "/skills/{skill_id}/enabled",
        frozenset({"PUT"}),
    ) in routes
    assert (
        "/skills/{skill_id}/duplicate",
        frozenset({"POST"}),
    ) in routes


def test_persona_action_routes_are_registered() -> None:
    routes = {
        (
            route.path,
            frozenset(route.methods or set()),
        )
        for route in personas_router.routes
    }

    assert (
        "/personas/{persona_id}/enabled",
        frozenset({"PUT"}),
    ) in routes
    assert (
        "/personas/{persona_id}/duplicate",
        frozenset({"POST"}),
    ) in routes
