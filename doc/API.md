# API

The API currently has a single endpoint /run. You can call it like this:

```sh
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
