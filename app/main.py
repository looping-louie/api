# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.schemas import RunRequest, RunResponse
from app.runner import run_harness
from app.task_runner import RunTasksRequest, run_tasks

app = FastAPI()

@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest):
    return await run_harness(req)

@app.post("/run-tasks")
async def run_tasks_endpoint(req: RunTasksRequest):
    return await run_tasks(req)
