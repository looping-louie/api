# RULES

- Looping Louie only runs against a clean committed Git state.
  Commit or stash your changes before running.


# LOGIC

main.py
  recibe HTTP /run
    ↓
schemas.py
  valida input/output JSON
    ↓
runner.py
  ejecuta el loop
    ↓
llm_together.py
  llama DeepSeek
    ↓
llm_openai.py
  llama ChatGPT reviewer
    ↓
skills/web_development.py
  prompt del reviewer


/run
 ↓
schemas.py valida repo_path
 ↓
runner.py ve si hay repo_path
 ↓
repository.py lee carpeta
 ↓
runner.py mete snapshot en prompt
 ↓
llm_together.py llama DeepSeek

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