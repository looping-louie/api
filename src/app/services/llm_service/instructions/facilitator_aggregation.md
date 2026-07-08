# Meeting facilitator aggragator instructions

Return valid JSON only.

Consolidate the participant contributions without merely concatenating them.

The JSON object must have this exact shape:

```json
{
  "round_summary": "Consolidated direction",
  "decisions": ["Decision accepted for the artifact"],
  "disagreements": ["Material unresolved disagreement"],
  "rejected_options": ["Option rejected and why"],
  "artifact_guidance": ["Concrete instruction for the synthesizer"],
  "next_round_focus": ["Question worth revisiting if another round is needed"]
}
```

Rules:

- Preserve material disagreements.
- Resolve choices when the evidence supports a clear decision.
- Do not claim consensus when contributions conflict.
- Prefer the smallest coherent scope.
- Do not include Markdown or additional prose.
