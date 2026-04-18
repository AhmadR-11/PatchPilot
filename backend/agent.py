# The LangChain Agentic AI logic

# agent.py
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from github_tools import get_github_file, create_pull_request
from dotenv import load_dotenv

load_dotenv()

# 1. Define the LLM (Gemini)
#    langchain-google-genai reads the GOOGLE_API_KEY environment variable automatically.
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# 2. Define the tools
tools = [get_github_file, create_pull_request]

# 3. System prompt — passed directly as a string to create_react_agent
system_prompt = """You are PatchPilot, an elite DevOps AI Agent.
Your job is to analyze failed CI/CD pipeline logs, find the bug in the code, and submit a fix.

Follow these exact steps:
1. Read the error logs provided by the user.
2. Identify which file is causing the error. (e.g., a syntax error in a .js file or a bad PATH variable in a config).
3. Use the 'get_github_file' tool to read the contents of the broken file.
4. Figure out how to fix the code.
5. Use the 'create_pull_request' tool to submit the fixed code.

Only reply with the final result or the PR link once you are finished."""

# 4. Construct the Agent using LangGraph (replaces the old create_tool_calling_agent + AgentExecutor)
#    create_react_agent is the modern API in LangChain 1.x / LangGraph 1.x
agent = create_react_agent(llm, tools, prompt=system_prompt)

def run_patchpilot(repo_name: str, error_logs: str):
    """Entry point for the FastAPI server to trigger the agent."""
    print(f"\n🚀 PatchPilot activated for repository: {repo_name}...")
    
    user_input = f"Repository: {repo_name}\n\nPipeline Error Logs:\n{error_logs}\n\nPlease fix this."
    
    # Execute the agent — LangGraph uses a messages-based interface
    response = agent.invoke({"messages": [("human", user_input)]})
    
    # The final AI message is the last item in the messages list
    return response["messages"][-1].content