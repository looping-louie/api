from pathlib import Path

import src.app.personas as legacy_personas
import src.app.skills as legacy_skills
from src.app.catalogs.personas.loader import (
    PERSONA_CATALOG_DIR,
    load_persona_catalog,
    load_persona_content,
)
from src.app.catalogs.skills.loader import (
    SKILL_CATALOG_DIR,
    load_skill_catalog,
    load_skill_content,
)


def test_every_manifest_entry_resolves_one_unique_markdown() -> None:
    for catalog_dir, registry in (
        (SKILL_CATALOG_DIR, load_skill_catalog()),
        (PERSONA_CATALOG_DIR, load_persona_catalog()),
    ):
        manifest_paths = {
            entry.content_path
            for entry in registry
        }
        markdown_paths = {
            path.relative_to(catalog_dir).as_posix()
            for path in (catalog_dir / "content").rglob("*.md")
        }

        assert len(manifest_paths) == len(registry)
        assert manifest_paths == markdown_paths


def test_manifests_have_stable_unique_ids_names_keys_and_paths() -> None:
    skills = load_skill_catalog()
    personas = load_persona_catalog()

    for prefix, registry in (
        ("builtin:skill:", skills),
        ("builtin:persona:", personas),
    ):
        assert all(entry.id.startswith(prefix) for entry in registry)
        assert len({entry.id for entry in registry}) == len(registry)
        assert len({entry.key for entry in registry}) == len(registry)
        assert len({entry.name for entry in registry}) == len(registry)
        assert len(
            {
                entry.content_path
                for entry in registry
            }
        ) == len(registry)


def test_skill_metadata_was_moved_out_of_markdown_front_matter() -> None:
    for entry in load_skill_catalog():
        assert entry.category
        assert entry.phase
        assert entry.artifacts
        assert entry.output
        assert entry.reviewer_default_strictness

        content = (
            SKILL_CATALOG_DIR
            / str(entry.content_path)
        ).read_text(encoding="utf-8")

        assert not content.startswith("---")


def test_persona_manifest_uses_stable_preferred_skill_ids() -> None:
    for entry in load_persona_catalog():
        assert all(
            skill_id.startswith("builtin:skill:")
            for skill_id in entry.preferred_skill_ids
        )


def test_content_loaders_accept_stable_ids_and_temporary_legacy_keys() -> None:
    assert load_skill_content(
        "builtin:skill:security"
    ) == load_skill_content("security")
    assert load_persona_content(
        "builtin:persona:tech_lead"
    ) == load_persona_content("tech_lead")


def test_legacy_wrappers_preserve_current_runtime_registry_shape() -> None:
    skills = legacy_skills.load_skill_registry()
    personas = legacy_personas.load_persona_registry()

    assert skills[0]["id"] == "web_development"
    assert personas[0]["id"] == "product_manager"
    assert personas[0]["preferred_skills"] == [
        "web_development",
        "accessibility",
        "privacy",
        "resilience",
    ]


def test_legacy_wrappers_are_explicitly_temporary() -> None:
    assert "Temporary compatibility wrapper" in (
        legacy_skills.__doc__
        or ""
    )
    assert "Temporary compatibility wrapper" in (
        legacy_personas.__doc__
        or ""
    )


def test_legacy_directories_contain_no_catalog_resources() -> None:
    app_dir = Path(legacy_skills.__file__).parents[1]

    assert not list((app_dir / "skills").glob("*.json"))
    assert not list((app_dir / "skills").rglob("*.md"))
    assert not list((app_dir / "personas").glob("*.json"))
    assert not list((app_dir / "personas").rglob("*.md"))
