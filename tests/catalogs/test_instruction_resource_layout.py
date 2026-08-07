"""Filesystem contract tests for packaged instruction catalogs."""

from src.app.catalogs.personas.loader import (
    PERSONA_CATALOG_DIR,
    load_persona_catalog,
)
from src.app.catalogs.skills.loader import (
    SKILL_CATALOG_DIR,
    load_skill_catalog,
)


def test_every_manifest_entry_resolves_one_unique_markdown() -> None:
    """Every registry entry owns exactly one Markdown resource."""

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
    """Catalog identities and resource paths remain unique."""

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
    """Skill metadata lives in the registry rather than Markdown."""

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


def test_persona_manifest_uses_stable_skill_ids() -> None:
    """Persona associations use stable builtin skill identifiers."""

    for entry in load_persona_catalog():
        assert all(
            skill_id.startswith("builtin:skill:")
            for skill_id in entry.skill_ids
        )
