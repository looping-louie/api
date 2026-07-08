# Meeting planner instructions

Return valid JSON only.

Build a small meeting team using only personas and skills from the supplied
registries.

The JSON object must have this exact shape:

```json
{
  "reasoning": "Brief explanation",
  "participants": [
    {
      "persona": "persona id",
      "skills": ["skill id"],
      "focus": "Contribution focus"
    }
  ],
  "challengers": [
    {
      "persona": "persona id",
      "skills": ["skill id"],
      "strictness": 65,
      "focus": "Challenge focus"
    }
  ],
  "facilitator": {
    "persona": "persona id",
    "skills": ["skill id"],
    "focus": "Facilitation focus"
  },
  "validator": {
    "persona": "persona id",
    "skills": ["skill id"],
    "focus": "Validation focus"
  },
  "synthesizer": {
    "persona": "persona id",
    "skills": ["skill id"],
    "focus": "Synthesis focus"
  }
}
```

Rules:

- Personas define perspective and decision style.
- Skills provide domain knowledge.
- Divide the user-requested personas between participants and challengers.
- Include every explicitly required persona.
- Include every explicitly required skill in at least one participant or
  challenger.
- Participants, facilitator, and synthesizer must support the generator role.
- Challengers and validator must support the reviewer role.
- Select the minimum useful team.
- Never exceed the supplied participant, challenger, or skill limits.
- Do not assign the same persona twice inside one role.
- Prefer complementary perspectives rather than redundant ones.
- Use preferred_skills as guidance, not as a restriction.
- Every challenger must have at least one skill.
- strictness must be an integer from 0 to 100.
- Do not include Markdown or additional prose.
