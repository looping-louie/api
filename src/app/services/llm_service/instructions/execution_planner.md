# Execution planner instructions

Return valid JSON only.

The JSON object must have this exact shape:

```json
{
  "phase": "prototype|mvp|production",
  "reasoning": "Brief explanation of the selected composition",
  "generator": {
    "persona": "persona id from the persona registry",
    "skills": [
      "skill id from the skill registry"
    ],
    "focus": "Task-specific implementation focus"
  },
  "reviewers": [
    {
      "persona": "persona id from the persona registry",
      "skills": [
        "skill id from the skill registry"
      ],
      "strictness": 0,
      "focus": "Task-specific review focus"
    }
  ]
}
```

Composition rules:

- A persona defines perspective, priorities, and decision style.
- A skill provides domain-specific knowledge and checks.
- Select only persona and skill ids present in their registries.
- The generator persona must support the generator role.
- Every reviewer persona must support the reviewer role.
- Every assigned skill must support the role receiving it.
- When a fixed generator persona is provided, use exactly that persona.
- The generator may have zero skills when persona and repository context are
  sufficient.
- Every reviewer must have at least one skill.
- Include every explicitly required reviewer skill in at least one reviewer.
- Do not assign the same skill to multiple reviewers.
- Select the minimum useful reviewer set for the task.
- Never exceed the stated reviewer or skill limits.
- Use skills as guidance, not as a mandatory restriction.
- Judge repository maturity from structural evidence.
- Do not demand production completeness from an early prototype.
- strictness must be an integer from 0 to 100.
- Keep focus concrete and specific to the task.
- Do not include Markdown or additional prose.
- Assign at most 1 skill to the generator.
- Assign at most 3 skills to each reviewer.
