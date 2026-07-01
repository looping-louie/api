# USE

## Repo

To get the repo up and running, follow the steps:

1. Run `make install` to create the virtualenv, install requirements and initialize the .env file.
2. Manually add the required API keys in your new .env file.
3. Run `make run` to start the uvicorn.

## Api

The API currently has a single endpoint /run. You can call it like this:

```
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/home/jadraque/Documents/source/looping-louie/web",
    "prompt": "Fix the Nuxt layout warning. Ensure the default layout is actually used by app.vue. Do not redesign the homepage. Keep changes minimal.",
    "max_iterations": 2,
    "generator_model": "zai-org/GLM-5.2",
    "reviewer_model": "gpt-4.1-mini",
    "skills": ["small_patch_quality", "nuxt_code_review"]
  }'
```

***

# RULES

- Looping Louie only runs against a clean committed Git state.
  Commit or stash your changes before running.

***

# LOGIC

/run
→ runner.py
→ workspace.py crea worktree
→ repository.py genera snapshot
→ llm_together.py genera patch
→ patcher.py valida/aplica en worktree
→ patcher.py saca diff real
→ llm_openai.py revisa diff + changed files
→ si aprueba: patcher.py aplica final_diff en repo original
→ workspace.py borra worktree