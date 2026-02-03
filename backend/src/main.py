import os
from dotenv import load_dotenv
load_dotenv()

import uuid
import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
import re

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.agents.research_agent import create_research_crew

app = FastAPI(title="Multi-Agent Research Backend")

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Job Storage
# ---------------------------------------------------------
jobs = {}

class ResearchRequest(BaseModel):
    topic: str

# ---------------------------------------------------------
# LOG CLEANING UTILITIES
# ---------------------------------------------------------

def strip_ansi_codes(text: str) -> str:
    """
    Remove ANSI escape sequences (color codes, cursor movement, etc.)
    from terminal output to make it clean for UI display.
    """
    ansi_escape = re.compile(r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''', re.VERBOSE)
    return ansi_escape.sub('', text)

def clean_log_message(raw_message: str) -> str:
    """
    Clean up log messages for better readability in the Flutter UI.
    - Strips ANSI codes
    - Removes excessive whitespace
    - Preserves important structure
    """
    # Strip ANSI codes
    cleaned = strip_ansi_codes(raw_message)
    
    # Remove excessive blank lines (but keep intentional structure)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Remove trailing/leading whitespace from each line
    lines = [line.rstrip() for line in cleaned.split('\n')]
    cleaned = '\n'.join(lines)
    
    return cleaned.strip()

# ---------------------------------------------------------
# LOGGING SYSTEM (captures ALL logs)
# ---------------------------------------------------------

# Global queue for log messages
log_queue = Queue()

# Handler that pushes logs into the queue
queue_handler = QueueHandler(log_queue)

# Attach handler to root logger (captures CrewAI, MCP, Brave, etc.)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(queue_handler)

# Also capture stdout/stderr for tools that print directly
import sys
from io import StringIO

class LogCapture:
    """Capture stdout/stderr and send to job logs"""
    def __init__(self, job_id: str, stream_name: str):
        self.job_id = job_id
        self.stream_name = stream_name
        self.buffer = []
        
    def write(self, text):
        if text and text.strip():
            # Clean the text before storing
            cleaned = clean_log_message(text)
            if cleaned:
                add_log(self.job_id, cleaned)
        
        # Also write to original stream for debugging
        sys.__stdout__.write(text)
        
    def flush(self):
        sys.__stdout__.flush()

# Store raw logs into job
def add_log(job_id: str, raw: str):
    """Add a cleaned log message to the job's log list"""
    try:
        cleaned = clean_log_message(raw)
        if cleaned and job_id in jobs:
            jobs[job_id]["logs"].append(cleaned)
    except Exception as e:
        # Failsafe - don't crash if logging fails
        print(f"Warning: Failed to add log: {e}")

# Listener that consumes logs from queue and stores them
def start_log_listener(job_id: str):
    def handle_log(record):
        try:
            # Get the full formatted message
            msg = record.getMessage()
            
            # Add logger name context for important logs
            if record.name != 'root' and not msg.startswith('['):
                msg = f"[{record.name}] {msg}"
                
            add_log(job_id, msg)
        except Exception as e:
            print(f"Warning: Failed to handle log record: {e}")

    listener = QueueListener(log_queue, handle_log)
    listener.start()
    return listener

# ---------------------------------------------------------
# Background Task
# ---------------------------------------------------------
def run_crew_task(job_id: str, topic: str):
    # Start capturing logs for this job
    listener = start_log_listener(job_id)
    
    # Redirect stdout/stderr to capture print statements
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        logging.info(f"🚀 Starting research on: {topic}")
        logging.info("=" * 60)

        # Capture stdout/stderr
        sys.stdout = LogCapture(job_id, "stdout")
        sys.stderr = LogCapture(job_id, "stderr")

        crew = create_research_crew(topic)

        # CrewAI internally prints logs — now captured automatically
        result = crew.kickoff()

        logging.info("=" * 60)
        logging.info(f"✅ Research completed successfully!")

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = str(result)

    except Exception as e:
        logging.error(f"❌ Error during research: {str(e)}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["result"] = str(e)

    finally:
        # Restore original stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Stop log listener
        listener.stop()

# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.get("/")
def health_check():
    return {"status": "online", "system": "Cloud-Ready"}

@app.post("/research")
def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "running",
        "topic": request.topic,
        "result": None,
        "logs": []  # cleaned logs stored here
    }

    background_tasks.add_task(run_crew_task, job_id, request.topic)

    return {
        "job_id": job_id,
        "message": "Research started. Poll /research/{job_id} for updates."
    }

@app.get("/research/{job_id}")
def get_research_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

# ---------------------------------------------------------
# Run Server
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Multi-Agent Research Backend")
    print("=" * 60)
    print("📡 Server is running!")
    print("👉 API Docs: http://localhost:8000/docs")
    print("👉 Health Check: http://localhost:8000/")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)