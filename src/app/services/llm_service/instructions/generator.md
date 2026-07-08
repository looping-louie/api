# Execution generator instructions

Execute the supplied software task.

Return ONLY valid JSON.

The JSON must have this exact shape:

```json
{
  "operations": [
    {
      "operation": "create|replace|replace_text|delete",
      "path": "relative/path/from/repo/root",
      "content": "full file content for create or replace"
    }
  ]
}
```

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
