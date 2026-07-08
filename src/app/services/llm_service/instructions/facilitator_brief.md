# Meeting facilitator brief instructions

Return valid JSON only.

Direct the next structured contribution round.

The JSON object must have this exact shape:

```json
{
  "round_goal": "Single goal for this round",
  "questions": ["Specific question"],
  "known_disagreements": ["Current disagreement"],
  "decision_pressure": "What must become clearer in this round"
}
```

Rules:

- Use the current artifact, previous feedback, and unresolved disagreements.
- Avoid repeating settled questions.
- Keep the round focused enough for parallel contributions.
- Surface trade-offs instead of forcing artificial consensus.
- Do not include Markdown or additional prose.
