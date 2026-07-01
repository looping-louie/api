# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.schemas import RunRequest, RunResponse
from app.runner import run_harness

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest):
    return await run_harness(req)
