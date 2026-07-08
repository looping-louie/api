"""
Provider-independent model instructions.

These prompts define output contracts only. Personas and skills are assembled
separately so execution behaviour can be composed without mixing role identity
with technical knowledge.
"""


EXECUTION_PLANNER_OUTPUT_INSTRUCTIONS = """
Return valid JSON only.

The JSON object must have this exact shape:

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
- Use preferred_skills as guidance, not as a mandatory restriction.
- Judge repository maturity from structural evidence.
- Do not demand production completeness from an early prototype.
- strictness must be an integer from 0 to 100.
- Keep focus concrete and specific to the task.
- Do not include Markdown or additional prose.
""".strip()


GENERATOR_SYSTEM_PROMPT = """
Execute the supplied software task.

Return ONLY valid JSON.

The JSON must have this exact shape:

{
  "operations": [
    {
      "operation": "create|replace|delete",
      "path": "relative/path/from/repo/root",
      "content": "full file content for create or replace"
    }
  ]
}

Rules:
- Follow the supplied persona, skills, focus, repository context, and task.
- No Markdown fences.
- No prose before or after the JSON.
- Use relative paths only.
- Do not use absolute paths.
- Do not write outside the repository.
- Do not modify .git or .looping-louie.
- For create and replace, include the full final file content.
- For delete, omit content.
- Prefer small, focused changes.
""".strip()


REVIEWER_OUTPUT_INSTRUCTIONS = """
Return valid JSON only.

The JSON object must have this exact shape:

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
""".strip()
