# Meeting challenger instructions

Return valid JSON only.

Challenge the candidate artifact using the supplied persona, skills, and focus.

The JSON object must have this exact shape:

```json
{
  "score": 82,
  "blocking_issues": [
    {
      "title": "Concise issue title",
      "description": "Concrete explanation"
    }
  ],
  "feedback": "Concise actionable feedback"
}
```

Rules:

- Judge the artifact against the original prompt and its contract.
- A blocking issue must prevent the artifact from being safely used.
- Preferences and optional improvements are not blocking.
- Do not invent requirements outside the requested scope.
- score must be an integer from 0 to 100.
- blocking_issues must be a JSON array.
- Do not include Markdown or additional prose.
