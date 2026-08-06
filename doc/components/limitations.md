# Current Limitations

The current MVP intentionally keeps the architecture simple. These are known
boundaries of the implementation, not guarantees about future behavior.

- Repository snapshots are static rather than task-aware.
- Providers are not abstracted behind a common interface.
- Reviewers operate on text only, without screenshots.
- File operations replace whole files rather than editing line ranges.
- Execution is sequential.
- Prompt caching is not implemented.

These limitations should be reviewed when the related capability is expanded.
