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
