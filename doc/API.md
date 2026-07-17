# API

Looping Louie currently exposes two HTTP endpoints.

- `/task/run` executes one task end to end (transitional API-side harness path).
- `/meeting/run` runs a discussion between several personas to produce shape an
  idea or implement an execution plan.

---

## POST /task/run

Executes one task through planner, harness, and commit.

This endpoint is currently a transitional compatibility path while task
planning and review contracts are adopted by CLI-based execution.

---

## POST /meeting/run — Shape Idea

Executes a structured multi-persona meeting that transforms an initial idea into
a concise and decision-ready `idea.md` document.

The meeting planner assigns skills to the requested personas and divides them
between participants and challengers.

During each round, Looping Louie:

1. Asks the facilitator to define the round objective.
2. Executes participant contributions in parallel.
3. Consolidates agreements and disagreements.
4. Generates a complete candidate artifact.
5. Runs the challengers in parallel.
6. Validates the artifact structure and content.
7. Continues until approval or the configured round limit is reached.

The resulting document follows the standard idea structure and is limited to
1,000 words.

### Shape Idea Request

| Field               | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `meeting_type`      | Meeting preset. Must be `shape_idea`.                        |
| `prompt`            | Initial idea or problem to shape.                            |
| `max_iterations`    | Maximum number of contribution rounds. Defaults to `3`.      |
| `participant_model` | Model used for participant contributions.                    |
| `challenger_model`  | Model used by challengers and the validator.                 |
| `synthesizer_model` | Model used to write the complete artifact.                   |
| `planner_model`     | Model used by the meeting planner and facilitator.           |
| `required_personas` | Personas that must participate in the meeting.               |
| `required_skills`   | Skills that must be assigned to participants or challengers. |
| `constitution`      | Optional project principles and constraints.                 |

### Shape Idea Example

```sh
curl -s -X POST http://127.0.0.1:8000/meeting/run \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_type": "shape_idea",
    "prompt": "Quiero crear una funcionalidad para que equipos debatan ideas con varias personas y skills antes de convertirlas en tareas de implementación.",
    "max_iterations": 3,
    "participant_model": "zai-org/GLM-5.2",
    "challenger_model": "gpt-4.1-mini",
    "synthesizer_model": "gpt-4.1-mini",
    "planner_model": "gpt-4.1-mini",
    "required_personas": [
      "product_manager",
      "ux_designer",
      "tech_lead",
      "devils_advocate"
    ],
    "required_skills": [
      "idea_shaping",
      "customer_problem",
      "risk_analysis"
    ],
    "constitution": ""
  }' |
jq -r '.final_output' > idea.md
```

The complete API response includes the final artifact, approval state, meeting
trace, and aggregated model metrics.

---

## POST /meeting/run — Plan Implementation

Executes a structured multi-persona meeting that transforms an approved
`idea.md` document into an ordered `tasks.json` implementation backlog.

The complete contents of `idea.md` are sent inside the `prompt` field.

Each generated task:

1. Has a unique sequential identifier.
2. Starts with the `pending` status.
3. Contains a self-contained implementation prompt.
4. Preserves the approved scope and non-goals.
5. Includes sufficient acceptance criteria.
6. Produces one small and coherent commit.
7. Depends only on repository state or earlier tasks.

### Plan Implementation Request

| Field               | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `meeting_type`      | Meeting preset. Must be `plan_implementation`.               |
| `prompt`            | Complete contents of the approved `idea.md` document.        |
| `max_iterations`    | Maximum number of contribution rounds. Defaults to `3`.      |
| `participant_model` | Model used for participant contributions.                    |
| `challenger_model`  | Model used by challengers and the validator.                 |
| `synthesizer_model` | Model used to generate the final `tasks.json`.               |
| `planner_model`     | Model used by the meeting planner and facilitator.           |
| `required_personas` | Personas that must participate in the meeting.               |
| `required_skills`   | Skills that must be assigned to participants or challengers. |
| `constitution`      | Optional project principles and constraints.                 |

### Plan Implementation Example

```sh
jq -Rs '{
  meeting_type: "plan_implementation",
  prompt: (the content of idea.md, for instance),
  max_iterations: 3,
  participant_model: "zai-org/GLM-5.2",
  challenger_model: "gpt-4.1-mini",
  synthesizer_model: "gpt-4.1-mini",
  planner_model: "gpt-4.1-mini",
  required_personas: [
    "product_manager",
    "tech_lead",
    "ux_designer",
    "devils_advocate"
  ],
  required_skills: [
    "task_decomposition",
    "acceptance_criteria",
    "risk_analysis",
    "resilience"
  ],
  constitution: ""
}' idea.md |
curl -s -X POST http://127.0.0.1:8000/meeting/run \
  -H "Content-Type: application/json" \
  --data-binary @- |
jq -r '.final_output' > tasks.json
```

The generated file contains a JSON array with this task structure:

```json
{
  "id": "ideas-001",
  "status": "pending",
  "prompt": "Self-contained implementation instruction with acceptance criteria.",
  "run_id": "",
  "commit_message": "Add ideas empty state"
}
```
