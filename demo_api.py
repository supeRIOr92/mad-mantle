"""
demo_api.py
MAD Demo Control API
Run: uvicorn demo_api:app --host 0.0.0.0 --port 8001
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from demo_simulator import start_simulation, pause_simulation, reset_simulation, get_status

app = FastAPI(title="MAD Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class StartRequest(BaseModel):
    scenario: str
    speed: float = 1.0

@app.post("/demo/start")
async def demo_start(req: StartRequest):
    result = await start_simulation(req.scenario, req.speed)
    return result

@app.post("/demo/pause")
async def demo_pause():
    return await pause_simulation()

@app.post("/demo/reset")
async def demo_reset():
    return await reset_simulation()

@app.get("/demo/status")
async def demo_status():
    return get_status()
