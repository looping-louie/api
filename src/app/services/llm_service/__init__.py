"""
LLM provider service.

Centralises the external model invocations used by the harness.

The harness currently uses:

- Together.ai models to generate structured file operations;
- OpenAI models to review candidate changes using review skills.

Responsibilities include:

- lazily initialising provider SDK clients;
- validating provider API-key configuration;
- executing generator and reviewer model requests;
- applying provider-specific request parameters;
- parsing structured reviewer verdicts;
- normalising text, token usage and timing metrics across providers.

This service is the only application component that should depend directly
on LLM provider SDKs. It does not construct repository context, apply file
operations or orchestrate harness iterations.
"""

from dotenv import load_dotenv


load_dotenv()
