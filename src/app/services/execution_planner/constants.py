"""Limits and supported values for execution planning."""

MAX_SELECTED_REVIEWERS = 3
MAX_GENERATOR_SKILLS = 3
MAX_SKILLS_PER_REVIEWER = 3
STRICTNESS_DEVIATION = 15

DEFAULT_PHASE = "prototype"
VALID_PHASES = {"prototype", "mvp", "production"}
VALID_AGENT_ROLES = {"generator", "reviewer"}
