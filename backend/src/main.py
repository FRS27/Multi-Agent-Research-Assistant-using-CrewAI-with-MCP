import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables FIRST

import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn

# Import agents
from src.agents.research_agent import create_research_crew

app = FastAPI(title="Multi-Agent Research Backend")

jobs = {}

class ResearchRequest(BaseModel):
    topic: str

def run_crew_task(job_id: str, topic: str):
    try:
        print(f"[{job_id}] Starting research on: {topic}")
        crew = create_research_crew(topic)
        result = crew.kickoff()
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = str(result)
        print(f"[{job_id}] Research completed!")
    except Exception as e:
        print(f"[{job_id}] Error: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["result"] = str(e)

@app.get("/")
def health_check():
    return {"status": "online", "system": "Cloud-Ready"}

@app.post("/research")
def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "topic": request.topic,
        "result": None
    }
    background_tasks.add_task(run_crew_task, job_id, request.topic)
    return {
        "job_id": job_id,
        "message": "Research started. Use GET /research/{job_id} to check progress."
    }

@app.get("/research/{job_id}")
def get_research_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

if __name__ == "__main__":
    # This prints a clickable link in the terminal
    print("\n---------------------------------------------------------")
    print("🚀 Server is running! Open this link to control the agents:")
    print("👉 http://localhost:8000/docs")
    print("---------------------------------------------------------\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)