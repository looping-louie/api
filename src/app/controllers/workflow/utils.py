"""Private helper functions for workflow controller."""


def validate_and_apply_final_diff(
    *,
    repo_path: str,
    final_diff: str,
    execution_ports,
) -> None:
    """Apply an approved final diff to the original repository."""
    valid, error = execution_ports.git.validate_patch(
        repo_path,
        final_diff,
    )
    if not valid:
        raise RuntimeError(
            'Final diff does not apply to original repo: '
            f'{error}'
        )

    applied, error = execution_ports.git.apply_patch(
        repo_path,
        final_diff,
    )
    if not applied:
        raise RuntimeError(
            'Could not apply final diff to original repo: '
            f'{error}'
        )
