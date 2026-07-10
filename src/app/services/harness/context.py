"""Repository context helpers for harness prompts."""

from src.app.services.model_context import build_snapshot, format_snapshot_for_prompt


def build_repo_context(worktree_path: str) -> str:
    """Build the prompt-ready repository snapshot for the current worktree state."""
    snapshot = build_snapshot(worktree_path)
    return format_snapshot_for_prompt(snapshot)
