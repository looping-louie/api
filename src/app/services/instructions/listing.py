"""Filtering and ordering shared by instruction catalog listings."""

from __future__ import annotations

from collections.abc import Sequence

from src.app.catalogs.library import (
    LibraryCategory,
    LibrarySort,
    LibraryStatus,
)

from .types import AvailableInstructionSummary


def filter_and_sort_instruction_summaries(
    summaries: list[AvailableInstructionSummary],
    *,
    status: LibraryStatus | None,
    categories: Sequence[LibraryCategory],
    sort: LibrarySort | None,
) -> list[AvailableInstructionSummary]:
    """Apply the common catalog filters and a stable ordering."""

    filtered = summaries

    if status is not None:
        enabled = status == LibraryStatus.ENABLED
        filtered = [
            summary
            for summary in filtered
            if summary.enabled is enabled
        ]

    if categories:
        selected_categories = {category.value for category in categories}
        filtered = [
            summary
            for summary in filtered
            if summary.category in selected_categories
        ]

    if sort == LibrarySort.ALPHABETICAL_DESC:
        return sorted(
            filtered,
            key=lambda summary: (summary.name.casefold(), summary.id),
            reverse=True,
        )

    if sort == LibrarySort.NEWEST:
        return sorted(
            filtered,
            key=lambda summary: (
                -summary.created_at.timestamp(),
                summary.name.casefold(),
                summary.id,
            ),
        )

    if sort == LibrarySort.OLDEST:
        return sorted(
            filtered,
            key=lambda summary: (
                summary.created_at,
                summary.name.casefold(),
                summary.id,
            ),
        )

    return sorted(
        filtered,
        key=lambda summary: (summary.name.casefold(), summary.id),
    )
