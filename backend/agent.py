# The LangChain Agentic AI logic

# agent.py
import os
from langchain_cohere import ChatCohere
from langgraph.prebuilt import create_react_agent
from github_tools import list_repo_files, get_github_file, create_pull_request, update_fix_branch
from dotenv import load_dotenv
from ws_manager import manager

load_dotenv()

# Using Cohere API for excellent tool calling performance
llm = ChatCohere(
    model="command-r-plus-08-2024", 
    cohere_api_key=os.getenv("COHERE_API_KEY"),
    temperature=0
)

tools = [list_repo_files, get_github_file, create_pull_request, update_fix_branch]

# LangGraph's create_react_agent handles binding automatically

system_prompt = """You are PatchPilot, an elite DevOps AI Agent.
Your job is to analyze real CI/CD failure logs, find the exact bug, and submit the correct fix.

⚠️ FOLLOW THESE STEPS EXACTLY:

STEP 1 — ANALYZE THE LOGS:
  Read the error logs. Identify:
  - Which file is broken
  - What the expected vs actual value is
  - The exact line if mentioned

STEP 2 — EXPLORE THE REPOSITORY:
  Use 'list_repo_files' to find the exact file path.

STEP 3 — READ THE CURRENT FILE:
  Use 'get_github_file' to read the COMPLETE file content.
  If a fix branch is specified in your instructions, pass it as branch_ref to see the current state.

STEP 4 — REASON ABOUT THE FIX:
  Think carefully:
  - What does the test/build EXPECT?
  - What is the MINIMAL change to make it pass?
  - Fix the CODE — do NOT change the test expectations.

STEP 5 — SUBMIT:
  Read your instructions carefully:

  A) If instructions say "FIRST ATTEMPT" → use 'create_pull_request':
     - original_snippet: exact broken lines (verbatim from the file)
     - fixed_snippet: the corrected lines only
     - branch_name: use the branch name given in your instructions

  B) If instructions say "RETRY ATTEMPT" → use 'update_fix_branch':
     - Read the file using get_github_file with branch_ref set to the fix branch
     - original_snippet: exact lines from the current state of the fix branch
     - fixed_snippet: your new corrected version
     - branch_name: the existing fix branch from your instructions

  ✅ DO: Provide only the specific lines to change (surgical patch).
  ❌ DON'T: Write the entire file — this causes code loss.

Report the final PR link or update confirmation when done."""

agent = create_react_agent(llm, tools, prompt=system_prompt)


def run_patchpilot(repo_name: str, error_logs: str, fix_branch: str, attempt: int):
    """Entry point called by the FastAPI background task."""
    is_retry = attempt > 1
    mode = f"RETRY ATTEMPT #{attempt}" if is_retry else "FIRST ATTEMPT"

    manager.sync_broadcast({"type": "status", "data": "Investigating"})
    manager.sync_broadcast({"type": "log", "data": f"> 🚀 PatchPilot [{mode}] for repository: {repo_name}..."})
    manager.sync_broadcast({"type": "log", "data": f"> 🌿 Fix branch: {fix_branch}"})
    print(f"\n🚀 PatchPilot [{mode}] for repository: {repo_name}...")
    print(f"🌿 Fix branch: {fix_branch}\n")

    if is_retry:
        fix_instruction = (
            f"\n\n⚠️  {mode}: A previous fix was pushed to branch '{fix_branch}' but CI still failed.\n"
            f"Do NOT call 'create_pull_request'. Instead:\n"
            f"1. Use 'get_github_file' with branch_ref='{fix_branch}' to see the current broken state.\n"
            f"2. Analyze what went wrong with the previous fix.\n"
            f"3. Use 'update_fix_branch' with branch_name='{fix_branch}' to push a new corrected fix."
        )
    else:
        fix_instruction = (
            f"\n\n✅ {mode}: Use 'create_pull_request' with branch_name='{fix_branch}'."
        )

    user_input = (
        f"Repository: {repo_name}\n\n"
        f"CI/CD Failure Logs:\n"
        f"{'-' * 50}\n"
        f"{error_logs}\n"
        f"{'-' * 50}"
        f"{fix_instruction}"
    )

    response = agent.invoke({"messages": [("human", user_input)]})
    final_output = response["messages"][-1].content
    manager.sync_broadcast({"type": "log", "data": f"> ✅ PatchPilot [{mode}] finished."})
    manager.sync_broadcast({"type": "status", "data": "Awaiting Approval"})
    print(f"\n✅ PatchPilot [{mode}] finished:\n{final_output}")
    return final_output