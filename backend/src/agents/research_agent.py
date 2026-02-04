import os
from crewai import Agent, Crew, Process, Task, LLM
from crewai.mcp import MCPServerStdio
import time
from collections import defaultdict, deque

# Simple token rate limiter
class SimpleTPMLimiter:
    def __init__(self):
        self.usage = defaultdict(deque)  # model -> [(timestamp, tokens)]
        self.limits = {
            'groq/groq/compound': 60000,
            'groq/llama-3.3-70b-versatile': 10000,
            'groq/groq/compound-mini': 14000,
            'groq/meta-llama/llama-4-scout-17b-16e-instruct': 25000,
            'gemini/gemini-2.5-flash': 15000,
        }
    
    def wait_if_needed(self, model, estimated_tokens=500):
        limit = self.limits.get(model, 5000)
        now = time.time()
        
        # Remove old entries (older than 60 seconds)
        self.usage[model] = deque([
            (ts, tok) for ts, tok in self.usage[model] 
            if now - ts < 60
        ])
        
        # Calculate current usage
        current = sum(tok for _, tok in self.usage[model])
        
        # If would exceed limit, wait
        if current + estimated_tokens > limit:
            wait_time = 61 - (now - self.usage[model][0][0]) if self.usage[model] else 1
            print(f"⏳ Rate limit: waiting {wait_time:.1f}s for {model}")
            time.sleep(wait_time)
            self.usage[model].clear()
        
        # Record usage
        self.usage[model].append((now, estimated_tokens))

_limiter = SimpleTPMLimiter()

# Monkey-patch LLM to add rate limiting
original_llm_init = LLM.__init__
def rate_limited_init(self, *args, **kwargs):
    original_llm_init(self, *args, **kwargs)
    original_call = self.call
    
    def wrapped_call(*call_args, **call_kwargs):
        _limiter.wait_if_needed(self.model)
        return original_call(*call_args, **call_kwargs)
    
    self.call = wrapped_call

LLM.__init__ = rate_limited_init
# --- 1. Setup The LLMs ---

llm_gemini = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY")
)


llm_smart = LLM(
    model="groq/groq/compound", 
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

llm_fast=LLM(
    model= "groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
    
)

llm_AR=LLM(
    model= "groq/groq/compound-mini",
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

llm_write=LLM(
    model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


# --- 2. Setup MCP Servers (Dual Connection) ---

# Server A: Official Brave Search (Node.js)
brave_mcp = MCPServerStdio(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-brave-search"],
    env={"BRAVE_API_KEY": os.getenv("BRAVE_SEARCH_API_KEY")}
)

# Server B: Custom Academic Server (Python)
# We point to the python file we just created
academic_mcp = MCPServerStdio(
    command="python",
    args=["src/tools/academic_mcp.py"] 
)

# --- 3. Define Agents ---

# Agent 1: The Manager
manager = Agent(
    role="Research Manager",
    goal="Coordinate the research team.",
    backstory="You are a seasoned research director.",
    llm=llm_smart,
    verbose=True,
    max_rpm=15
)

# Agent 2: The Web Researcher (Uses Brave)
web_researcher = Agent(
    role="Senior Web Researcher",
    goal="Find deep, verifiable information on the internet.",
    backstory="You are an expert at finding hidden gems of information.",
    mcps=[brave_mcp], # Connected to Brave
    llm=llm_fast, 
    verbose=True,
    max_rpm=15
)

# Agent 3: The Academic Researcher (NEW AGENT!)
# This agent specializes in reading the scientific papers
academic_researcher = Agent(
    role="Academic Researcher",
    goal="Find and analyze top 10 scientific papers and technical publications.",
    backstory="You are a PhD researcher who loves reading ArXiv papers.",
    mcps=[academic_mcp], # Connected to our Custom Python MCP
    llm=llm_gemini,
    verbose=True,
    max_rpm=4

)

# Agent 4: The Writer
writer = Agent(
    role="Technical Writer",
    goal="Synthesize research into a clear, professional markdown report.",
    backstory="You are a technical writer who creates easy-to-read reports.",
    llm=llm_write,
    verbose=True,
    max_rpm=15
)

# --- 4. The Crew Setup Function ---

def create_research_crew(topic: str) -> Crew:
    # Task 1: General Web Search
    task_web = Task(
        description=f"Research general trends and news about: '{topic}'.",
        expected_output="A summary of web findings.",
        agent=web_researcher
    )

    # Task 2: Academic Search (New!)
    task_academic = Task(
        description=f"Search for recent scientific papers and technical studies about: '{topic}'. Focus on methodology and hard data.",
        expected_output="A list of relevant papers with summaries.",
        agent=academic_researcher
    )

    # Task 3: Synthesis
    task_write = Task(
        description=f"Write a comprehensive report about '{topic}'. Combine the web news with the scientific evidence from the papers.",
        expected_output="A professional Markdown article with citations.",
        agent=writer,
        context=[task_web, task_academic] # Context from BOTH researchers
    )

    crew = Crew(
        agents=[manager, web_researcher, academic_researcher, writer],
        tasks=[task_web, task_academic, task_write],
        process=Process.sequential,
        verbose=True
    )
    
    return crew