# The FastAPI server & webhook listener

# main.py
from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
from agent import run_patchpilot

app = FastAPI(title="PatchPilot Backend")

# We run the agent as a background task. 
# GitHub webhooks require a 200 OK response within 10 seconds. 
# Because the AI takes 15-30 seconds to think, we tell GitHub "Message received!" immediately, 
# and let the AI run in the background.
def trigger_agent_task(repo_name: str, error_logs: str):
    try:
        run_patchpilot(repo_name, error_logs)
    except Exception as e:
        print(f"Agent crashed: {e}")

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Listens for GitHub Actions failures."""
    payload = await request.json()
    
    # Extract data from the GitHub webhook payload
    # Note: GitHub payloads are massive. We are extracting just what we need.
    action = payload.get("action")
    workflow_run = payload.get("workflow_run", {})
    repo = payload.get("repository", {})
    
    repo_name = repo.get("full_name")
    status = workflow_run.get("status")
    conclusion = workflow_run.get("conclusion")
    
    # We only care if a workflow is completed AND it failed
    if status == "completed" and conclusion == "failure":
        print(f"\n⚠️ Alert: Build failed for {repo_name}. Triggering PatchPilot...")
        
        # In a production app, you would use the GitHub API to fetch the actual console logs here.
        # For testing, we simulate passing the error log.
        simulated_error_log = "Error: Expected 2 but received 3 in dummy.test.js"
        
        # Send the task to the AI to run in the background
        background_tasks.add_task(trigger_agent_task, repo_name, simulated_error_log)
        
        return {"status": "PatchPilot triggered"}
    
    return {"status": "Ignored. Workflow did not fail."}

if __name__ == "__main__":
    print("Starting PatchPilot API...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)