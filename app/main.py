from fastapi import FastAPI
from pydantic import BaseModel

from app.agent.loop import run

app = FastAPI(title="Agent Learning Skeleton")


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/agent/run")
def agent_run(req: AskRequest) -> dict:
    return run(req.question)
