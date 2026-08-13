import json
import shutil
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import FastAPI

import src.app.bootstrap.application as bootstrap
from src.app.catalogs.instructions.resource_loader import CatalogLoadError
from src.app.catalogs.skills import SkillCategory
from src.app.catalogs.instructions import (
    PersonaCatalogEntry,
    SkillCatalogEntry,
)
from src.app.catalogs.instructions.loader import load_instruction_catalog
from src.app.catalogs.personas.loader import (
    PERSONA_CATALOG_DIR,
    load_persona_catalog,
)
from src.app.catalogs.skills.loader import (
    SKILL_CATALOG_DIR,
    load_skill_catalog,
)
from src.app.services.shared.settings import AppSettings


def copy_catalogs(tmp_path: Path) -> tuple[Path, Path]:
    skill_dir = tmp_path / "skills"
    persona_dir = tmp_path / "personas"
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(SKILL_CATALOG_DIR, skill_dir, ignore=ignore)
    shutil.copytree(PERSONA_CATALOG_DIR, persona_dir, ignore=ignore)
    return skill_dir, persona_dir


def update_registry(
    catalog_dir: Path,
    update: Any,
) -> None:
    registry_path = catalog_dir / "registry.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    update(data)
    registry_path.write_text(
        f"{json.dumps(data, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )


def find_by_key(entries: Any, key: str) -> Any:
    return next(
        entry
        for entry in entries
        if entry.key == key
    )


def test_loaders_return_immutable_typed_entries() -> None:
    catalog = load_instruction_catalog()

    assert isinstance(catalog.skills[0], SkillCatalogEntry)
    assert isinstance(catalog.personas[0], PersonaCatalogEntry)

    with pytest.raises(FrozenInstanceError):
        catalog.skills[0].name = "Changed"  # type: ignore[misc]


def test_skill_catalog_uses_the_stable_business_taxonomy() -> None:
    """Every packaged skill uses one of the twelve supported categories."""

    skills = load_skill_catalog()

    assert len(SkillCategory) == 12
    assert all(
        isinstance(skill.category, SkillCategory)
        for skill in skills
    )
    assert all(skill.catalog_version == 2 for skill in skills)


def test_checksum_is_deterministic() -> None:
    first_load = load_instruction_catalog()
    second_load = load_instruction_catalog()

    assert [
        entry.checksum
        for entry in first_load.entries
    ] == [
        entry.checksum
        for entry in second_load.entries
    ]


def test_checksum_changes_when_content_changes(
    tmp_path: Path,
) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)
    original = find_by_key(
        load_skill_catalog(skill_dir),
        "security",
    )
    content_path = skill_dir / str(original.content_path)
    content_path.write_text(
        f"{original.instructions}\nAdditional policy.\n",
        encoding="utf-8",
    )
    changed = find_by_key(
        load_skill_catalog(skill_dir),
        "security",
    )

    assert changed.checksum != original.checksum


def test_checksum_changes_when_metadata_changes(
    tmp_path: Path,
) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)
    original = find_by_key(
        load_skill_catalog(skill_dir),
        "security",
    )

    def change_description(data: list[dict[str, Any]]) -> None:
        data[4]["description"] = "Changed security description."

    update_registry(skill_dir, change_description)
    changed = find_by_key(
        load_skill_catalog(skill_dir),
        "security",
    )

    assert changed.checksum != original.checksum


def test_rejects_malformed_json(tmp_path: Path) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)
    (skill_dir / "registry.json").write_text(
        "{not-json",
        encoding="utf-8",
    )

    with pytest.raises(
        CatalogLoadError,
        match="Invalid catalog registry JSON",
    ):
        load_skill_catalog(skill_dir)


def test_rejects_missing_required_field(tmp_path: Path) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)

    def remove_name(data: list[dict[str, Any]]) -> None:
        del data[0]["name"]

    update_registry(skill_dir, remove_name)

    with pytest.raises(
        CatalogLoadError,
        match="'name'",
    ):
        load_skill_catalog(skill_dir)


def test_rejects_duplicate_ids(tmp_path: Path) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)

    def duplicate_id(data: list[dict[str, Any]]) -> None:
        data.append(dict(data[0]))

    update_registry(skill_dir, duplicate_id)

    with pytest.raises(
        CatalogLoadError,
        match="Duplicate catalog id",
    ):
        load_skill_catalog(skill_dir)


def test_rejects_non_positive_version(tmp_path: Path) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)

    def change_version(data: list[dict[str, Any]]) -> None:
        data[0]["version"] = 0

    update_registry(skill_dir, change_version)

    with pytest.raises(
        CatalogLoadError,
        match="'version'.*positive integer",
    ):
        load_skill_catalog(skill_dir)


def test_rejects_missing_content_file(tmp_path: Path) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)

    def change_content_path(data: list[dict[str, Any]]) -> None:
        data[0]["content_path"] = "content/nonexistent.md"
        data[0]["key"] = "nonexistent"
        data[0]["id"] = "builtin:skill:nonexistent"

    update_registry(skill_dir, change_content_path)

    with pytest.raises(
        CatalogLoadError,
        match="Catalog content does not exist",
    ):
        load_skill_catalog(skill_dir)


def test_rejects_invalid_roles(tmp_path: Path) -> None:
    _, persona_dir = copy_catalogs(tmp_path)

    def change_role(data: list[dict[str, Any]]) -> None:
        data[0]["applies_to"] = ["unsupported-role"]

    update_registry(persona_dir, change_role)

    with pytest.raises(
        CatalogLoadError,
        match="unsupported role",
    ):
        load_persona_catalog(persona_dir)


def test_rejects_strictness_outside_range(
    tmp_path: Path,
) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)

    def change_strictness(data: list[dict[str, Any]]) -> None:
        data[0]["reviewer_default_strictness"]["production"] = 101

    update_registry(skill_dir, change_strictness)

    with pytest.raises(
        CatalogLoadError,
        match="between 0 and 100",
    ):
        load_skill_catalog(skill_dir)


def test_rejects_unknown_associated_skill_reference(
    tmp_path: Path,
) -> None:
    skill_dir, persona_dir = copy_catalogs(tmp_path)

    def change_reference(data: list[dict[str, Any]]) -> None:
        data[0]["skill_ids"].append(
            "builtin:skill:missing"
        )

    update_registry(persona_dir, change_reference)

    with pytest.raises(
        CatalogLoadError,
        match="unknown associated skills",
    ):
        load_instruction_catalog(
            skill_catalog_dir=skill_dir,
            persona_catalog_dir=persona_dir,
        )


def test_rejects_content_that_disagrees_with_manifest_name(
    tmp_path: Path,
) -> None:
    skill_dir, _ = copy_catalogs(tmp_path)

    def change_name(data: list[dict[str, Any]]) -> None:
        data[0]["name"] = "Different Name"

    update_registry(skill_dir, change_name)

    with pytest.raises(
        CatalogLoadError,
        match="must start with",
    ):
        load_skill_catalog(skill_dir)


@pytest.mark.asyncio
async def test_invalid_catalog_prevents_application_startup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "invalid-catalog.db"

    async def run_migrations(*, database_path: Path) -> None:
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                CREATE TABLE schema_migrations (
                    version TEXT PRIMARY KEY
                )
                """
            )

    def reject_catalog() -> None:
        raise CatalogLoadError("Invalid packaged catalog.")

    monkeypatch.setattr(
        bootstrap,
        "run_sqlite_migrations",
        run_migrations,
    )
    monkeypatch.setattr(
        bootstrap,
        "load_instruction_catalog",
        reject_catalog,
    )
    settings = cast(
        AppSettings,
        SimpleNamespace(
            database_path=database_path,
            encryption_key="unused",
        ),
    )
    app = FastAPI()

    with pytest.raises(
        CatalogLoadError,
        match="Invalid packaged catalog",
    ):
        await bootstrap.configure_application(
            app,
            settings=settings,
        )

    assert database_path.exists() is True
    assert not hasattr(
        app.state,
        "persona_controller",
    )
