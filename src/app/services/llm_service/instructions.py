SKILL_PLANNER_OUTPUT_INSTRUCTIONS = """
Return valid JSON only.

The JSON object must have this exact shape:

{
  "phase": "prototype|mvp|production",
  "reasoning": "Brief explanation",
  "reviewers": [
    {
      "skill": "skill id from the registry",
      "strictness": 0,
      "focus": "Task-specific review focus"
    }
  ]
}

Rules:
- Select only skills present in the registry.
- Select the minimum reviewer set required for this task.
- Never select more than the stated maximum.
- Include all explicitly required skills.
- Judge repository maturity from structural evidence.
- Do not demand production completeness from an early prototype.
- strictness must be an integer from 0 to 100.
- Do not include Markdown or additional prose.
""".strip()


GENERATOR_SYSTEM_PROMPT = """
You are a senior software engineer.

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
- Judge only the requested change.
- Do not penalise missing work that the task did not request.
- A blocking issue must be a concrete defect that prevents approval.
- Preferences, optional improvements and future hardening are not blocking.
- Do not output approved; the harness computes it.

Rules:
- score must be an integer from 0 to 100.
- blocking_issues must be a JSON array.
- feedback must be a non-empty JSON string.
- Do not include Markdown or additional prose.
""".strip()
