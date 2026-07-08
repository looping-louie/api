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
- Assign at most 1 skill to the generator.
- Assign at most 3 skills to each reviewer.
""".strip()


GENERATOR_SYSTEM_PROMPT = """
Execute the supplied software task.

Return ONLY valid JSON.

The JSON must have this exact shape:

{
  "operations": [
    {
      "operation": "create|replace|replace_text|delete",
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
- For replace_text, include old_content and new_content.
- old_content must match exactly once in the current file.
- Multiple replace_text operations may target the same file.
- Operations are applied sequentially in array order.
- Prefer replace_text for focused modifications to existing files.
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



MEETING_PLANNER_INSTRUCTIONS = """
Return valid JSON only.

Build a small meeting team using only personas and skills from the supplied
registries.

The JSON object must have this exact shape:

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
""".strip()

FACILITATOR_BRIEF_INSTRUCTIONS = """
Return valid JSON only.

Direct the next structured contribution round.

The JSON object must have this exact shape:

{
  "round_goal": "Single goal for this round",
  "questions": ["Specific question"],
  "known_disagreements": ["Current disagreement"],
  "decision_pressure": "What must become clearer in this round"
}

Rules:
- Use the current artifact, previous feedback, and unresolved disagreements.
- Avoid repeating settled questions.
- Keep the round focused enough for parallel contributions.
- Surface trade-offs instead of forcing artificial consensus.
- Do not include Markdown or additional prose.
""".strip()

PARTICIPANT_INSTRUCTIONS = """
Return valid JSON only.

Contribute independently to the current meeting round.

The JSON object must have this exact shape:

{
  "position": "Your recommended position",
  "reasoning": "Why this position is appropriate",
  "proposed_changes": ["Concrete change to the artifact"],
  "risks": ["Risk or assumption"],
  "decisions_needed": ["Decision that remains open"]
}

Rules:
- Apply the supplied persona, skills, and task-specific focus.
- Respond to the facilitator brief.
- Improve the requested artifact rather than discussing the meeting process.
- Be concrete and concise.
- Do not include Markdown or additional prose.
""".strip()

FACILITATOR_AGGREGATION_INSTRUCTIONS = """
Return valid JSON only.

Consolidate the participant contributions without merely concatenating them.

The JSON object must have this exact shape:

{
  "round_summary": "Consolidated direction",
  "decisions": ["Decision accepted for the artifact"],
  "disagreements": ["Material unresolved disagreement"],
  "rejected_options": ["Option rejected and why"],
  "artifact_guidance": ["Concrete instruction for the synthesizer"],
  "next_round_focus": ["Question worth revisiting if another round is needed"]
}

Rules:
- Preserve material disagreements.
- Resolve choices when the evidence supports a clear decision.
- Do not claim consensus when contributions conflict.
- Prefer the smallest coherent scope.
- Do not include Markdown or additional prose.
""".strip()

CHALLENGER_INSTRUCTIONS = """
Return valid JSON only.

Challenge the candidate artifact using the supplied persona, skills, and focus.

The JSON object must have this exact shape:

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

Rules:
- Judge the artifact against the original prompt and its contract.
- A blocking issue must prevent the artifact from being safely used.
- Preferences and optional improvements are not blocking.
- Do not invent requirements outside the requested scope.
- score must be an integer from 0 to 100.
- blocking_issues must be a JSON array.
- Do not include Markdown or additional prose.
""".strip()

VALIDATOR_INSTRUCTIONS = """
Return valid JSON only.

Validate the candidate artifact against the supplied contract.

The JSON object must have this exact shape:

{
  "valid": true,
  "issues": [
    {
      "title": "Concise contract issue",
      "description": "Concrete correction"
    }
  ],
  "feedback": "Brief validation summary"
}

Rules:
- Check structure, completeness, internal consistency, and usability.
- Do not rewrite the artifact.
- Mark valid false when a contract violation prevents downstream use.
- Do not include Markdown or additional prose.
""".strip()

