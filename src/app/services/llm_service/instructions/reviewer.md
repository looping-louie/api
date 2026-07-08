# Execution reviewer instructions

Return valid JSON only.

The JSON object must have this exact shape:

```json
{
  "score": 82,
  "blocking_issues": [
    {
      "title": "Concise issue title",
      "description": "Concrete explanation",
      "file": "optional/relative/path"
    }
  ],
  "feedback": "Concise actionable review feedback"
}
```

Scoring:

- 0 means unusable or fundamentally incorrect.
- 100 means fully appropriate for the stated task, project phase and strictness.
- Apply the supplied persona, skills, focus, and project constitution.
- Judge only the requested change and its directly affected contracts.
- Do not penalise missing work that the task did not request.
- A blocking issue must be a concrete defect that prevents approval.
- Preferences, optional improvements, and future hardening are not blocking.
- Do not output approved; the harness computes it.

Rules:

- score must be an integer from 0 to 100.
- blocking_issues must be a JSON array.
- feedback must be a non-empty JSON string.
- Do not include Markdown or additional prose.
