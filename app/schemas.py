from pydantic import BaseModel


class RunRequest(BaseModel):
    prompt: str
    repo_path: str
    max_iterations: int = 3
    generator_model: str = "deepseek-ai/DeepSeek-V4-Pro"
    reviewer_model: str = "gpt-4.1-mini"
    skill: str = "web_foundations"


class ModelMetrics(BaseModel):
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    duration_ms: int = 0
    tokens_per_second: float = 0


class ReviewerMetrics(ModelMetrics):
    skill: str


class RunMetrics(BaseModel):
    iterations: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    duration_ms: int
    tokens_per_second: float
    estimated_cost_eur: float = 0


class IterationTrace(BaseModel):
    iteration: int
    generator_output: str
    reviewer_feedback: str
    approved: bool
    generator_metrics: ModelMetrics
    reviewers_metrics: list[ReviewerMetrics]


class RunResponse(BaseModel):
    run_id: str
    final_output: str
    approved: bool
    run_metrics: RunMetrics
    execution_trace: list[IterationTrace]