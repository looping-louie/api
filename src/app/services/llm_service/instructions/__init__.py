"""
Provider-independent model instructions loaded from Markdown files.
"""

from pathlib import Path


_INSTRUCTIONS_DIR = Path(__file__).parent


def _load_instruction(filename: str) -> str:
    """Load and normalize an instruction file."""
    return (_INSTRUCTIONS_DIR / filename).read_text(encoding="utf-8").strip()


EXECUTION_PLANNER_OUTPUT_INSTRUCTIONS = _load_instruction(
    "execution_planner.md"
)
GENERATOR_SYSTEM_PROMPT = _load_instruction("generator.md")
REVIEWER_OUTPUT_INSTRUCTIONS = _load_instruction("reviewer.md")
MEETING_PLANNER_INSTRUCTIONS = _load_instruction("meeting_planner.md")
FACILITATOR_BRIEF_INSTRUCTIONS = _load_instruction(
    "facilitator_brief.md"
)
PARTICIPANT_INSTRUCTIONS = _load_instruction("participant.md")
FACILITATOR_AGGREGATION_INSTRUCTIONS = _load_instruction(
    "facilitator_aggregation.md"
)
CHALLENGER_INSTRUCTIONS = _load_instruction("challenger.md")
VALIDATOR_INSTRUCTIONS = _load_instruction("validator.md")


__all__ = [
    "EXECUTION_PLANNER_OUTPUT_INSTRUCTIONS",
    "GENERATOR_SYSTEM_PROMPT",
    "REVIEWER_OUTPUT_INSTRUCTIONS",
    "MEETING_PLANNER_INSTRUCTIONS",
    "FACILITATOR_BRIEF_INSTRUCTIONS",
    "PARTICIPANT_INSTRUCTIONS",
    "FACILITATOR_AGGREGATION_INSTRUCTIONS",
    "CHALLENGER_INSTRUCTIONS",
    "VALIDATOR_INSTRUCTIONS",
]