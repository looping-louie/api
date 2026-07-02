# Looping Louie

## Installation

To get the repo up and running, follow the steps:

1. Run `make install` to create the virtualenv, install requirements and initialize the .env file.

## Configuration

1. Manually add the required API keys in your new .env file.

## Execution

1. Run `make run` to start the uvicorn.

## API

Check the API specific documentation [here][1]

## Caveat

- Looping Louie only runs against a clean committed Git state.
  Commit or stash your changes before running.

## Logic

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

## References

[1]: <./doc/API.md>
