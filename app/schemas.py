from pydantic import BaseModel


class RunRequest(BaseModel):
    prompt: str
    max_iterations: int = 3
    generator_model: str = "deepseek-ai/DeepSeek-V4-Pro"
    reviewer_model: str = "gpt-4.1-mini"
    skill: str = "web_foundations"
    repo_path: str


class IterationTrace(BaseModel):
    iteration: int
    generator_output: str
    reviewer_feedback: str
    approved: bool
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


class Metrics(BaseModel):
    iterations: int
    input_tokens: int
    output_tokens: int
    duration_ms: int
    tokens_per_second: float
    estimated_cost_eur: float


class RunResponse(BaseModel):
    final_output: str
    metrics: Metrics
    execution_trace: list[IterationTrace]