"""Contract tests for predefined loop catalog entries."""

from __future__ import annotations

from src.app.catalogs.loops import LOOP_CATALOG


def test_loop_catalog_contains_the_two_supported_workflows() -> None:
    """Catalog loops retain the confirmed names and artifact contracts."""

    by_id = {
        entry.id: entry
        for entry in LOOP_CATALOG
    }

    assert set(by_id) == {
        "builtin:loop:shape-ideas",
        "builtin:loop:plan-implementation",
    }
    shape = by_id["builtin:loop:shape-ideas"]
    plan = by_id["builtin:loop:plan-implementation"]
    assert shape.title == "shape ideas"
    assert shape.output_files == ("ideas.md",)
    assert "# Idea title" in shape.output_description
    assert "## Open decisions" in shape.output_description
    assert plan.title == "plan implementation"
    assert plan.output_files == ("tasks.json",)
    assert '"commit_message"' in plan.output_description
    assert plan.output_schema is not None
    assert plan.output_schema["type"] == "array"


def test_loop_catalog_uses_confirmed_model_and_team_assignments() -> None:
    """Every predefined agent uses the lowercase model and selected persona."""

    expected_personas = {
        "builtin:loop:shape-ideas": (
            "builtin:persona:product_manager",
            "builtin:persona:ux_designer",
            "builtin:persona:devils_advocate",
            "builtin:persona:editor",
        ),
        "builtin:loop:plan-implementation": (
            "builtin:persona:tech_lead",
            "builtin:persona:platform_architect",
            "builtin:persona:devils_advocate",
            "builtin:persona:editor",
        ),
    }
    for entry in LOOP_CATALOG:
        assert entry.flow == "roundtable"
        assert entry.max_iterations == 3
        assert {
            agent.model_id
            for agent in entry.agents
        } == {"deepseek-v4-pro"}
        assert tuple(
            agent.persona_id
            for agent in entry.agents
        ) == expected_personas[entry.id]
        assert tuple(agent.role for agent in entry.agents) == (
            "generator",
            "generator",
            "reviewer",
            "aggregator",
        )
