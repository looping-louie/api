"""Loading and validation of Markdown skill documents."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.app.models.skills import BuiltinSkill


_SKILL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\n(?P<yaml>.*?)\n---[ \t]*\n?(?P<body>.*)\Z",
    re.DOTALL,
)


class SkillDocumentError(ValueError):
    """Raised when a skill document or payload is invalid."""


@dataclass(frozen=True)
class ValidatedSkill:
    """Normalised skill content ready for persistence."""

    skill_id: str
    name: str
    description: str
    content: str
    metadata: dict[str, Any]


class SkillDocumentService:
    """Load built-in skills and validate editable skill fields."""

    def __init__(self, builtin_skills_path: Path) -> None:
        """Store the built-in skills directory."""

        self._builtin_skills_path = builtin_skills_path

    def list_builtin_skills(self) -> list[BuiltinSkill]:
        """Load every built-in Markdown skill."""

        if not self._builtin_skills_path.exists():
            return []

        skills = [
            self._load_builtin(path)
            for path in sorted(
                self._builtin_skills_path.rglob("*.md")
            )
        ]
        seen: set[str] = set()

        for skill in skills:
            if skill.skill_id in seen:
                raise SkillDocumentError(
                    f"Duplicate built-in skill id '{skill.skill_id}'."
                )

            seen.add(skill.skill_id)

        return skills

    def get_builtin_skill(
        self,
        skill_id: str,
    ) -> BuiltinSkill | None:
        """Return one built-in skill by id."""

        normalised_id = self.validate_skill_id(skill_id)

        for skill in self.list_builtin_skills():
            if skill.skill_id == normalised_id:
                return skill

        return None

    def validate_write(
        self,
        skill_id: str,
        name: str,
        description: str,
        content: str,
        metadata: dict[str, Any],
    ) -> ValidatedSkill:
        """Validate and normalise API-provided skill fields."""

        normalised_id = self.validate_skill_id(skill_id)
        clean_name = name.strip()
        clean_description = description.strip()
        clean_content = content.strip()

        if not clean_name:
            raise SkillDocumentError("Skill name cannot be empty.")

        if not clean_description:
            raise SkillDocumentError(
                "Skill description cannot be empty."
            )

        if not clean_content:
            raise SkillDocumentError("Skill content cannot be empty.")

        clean_metadata = self._normalise_metadata(metadata)
        clean_metadata["id"] = normalised_id
        clean_metadata["name"] = clean_name
        clean_metadata["description"] = clean_description

        return ValidatedSkill(
            skill_id=normalised_id,
            name=clean_name,
            description=clean_description,
            content=clean_content,
            metadata=clean_metadata,
        )

    @staticmethod
    def validate_skill_id(skill_id: str) -> str:
        """Validate and return a normalised skill id."""

        normalised_id = skill_id.strip().lower()

        if not _SKILL_ID_PATTERN.fullmatch(normalised_id):
            raise SkillDocumentError(
                "Skill ids must use lowercase letters, numbers, "
                "hyphens or underscores."
            )

        return normalised_id

    def _load_builtin(self, path: Path) -> BuiltinSkill:
        """Parse one Markdown file with YAML frontmatter."""

        raw_document = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_PATTERN.match(raw_document)

        if match is None:
            raise SkillDocumentError(
                f"Built-in skill '{path}' has no valid frontmatter."
            )

        metadata = yaml.safe_load(match.group("yaml")) or {}

        if not isinstance(metadata, dict):
            raise SkillDocumentError(
                f"Built-in skill '{path}' frontmatter must be a mapping."
            )

        clean_metadata = self._normalise_metadata(metadata)
        raw_skill_id = str(clean_metadata.get("id") or path.stem)
        skill_id = self.validate_skill_id(raw_skill_id)
        name = str(
            clean_metadata.get("name")
            or skill_id.replace("_", " ").replace("-", " ").title()
        ).strip()
        description = str(
            clean_metadata.get("description") or ""
        ).strip()
        content = match.group("body").strip()

        if not content:
            raise SkillDocumentError(
                f"Built-in skill '{path}' has no Markdown body."
            )

        clean_metadata["id"] = skill_id
        clean_metadata["name"] = name
        clean_metadata["description"] = description

        return BuiltinSkill(
            skill_id=skill_id,
            name=name,
            description=description,
            content=content,
            metadata=clean_metadata,
            file_path=str(path),
        )

    @staticmethod
    def _normalise_metadata(
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Ensure metadata can be stored as JSON."""

        if not isinstance(metadata, dict):
            raise SkillDocumentError(
                "Skill metadata must be an object."
            )

        serialised = json.dumps(
            metadata,
            ensure_ascii=False,
            default=str,
        )

        return json.loads(serialised)
