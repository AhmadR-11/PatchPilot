# The FastAPI server & webhook listener

# main.py
from fastapi import FastAPI, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
import zipfile
import io
import os
import uuid
from dotenv import load_dotenv
from agent import run_patchpilot
from ws_manager import manager

load_dotenv()

app = FastAPI(title="PatchPilot Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MAX_RETRIES = 3  # Max fix attempts before giving up

# In-memory state: tracks active fix branches per repo
# Format: { "owner/repo": { "branch": "patchpilot-fix-abc123", "attempts": 1 } }
active_fix_states: dict = {}


def fetch_workflow_logs(repo_name: str, run_id: int) -> str:
    """Fetches real failure logs from a GitHub Actions workflow run."""
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # Get failed job/step summary
    jobs_url = f"https://api.github.com/repos/{repo_name}/actions/runs/{run_id}/jobs"
    jobs_response = requests.get(jobs_url, headers=headers)
    failed_steps = []
    if jobs_response.status_code == 200:
        for job in jobs_response.json().get("jobs", []):
            if job.get("conclusion") == "failure":
                for step in job.get("steps", []):
                    if step.get("conclusion") == "failure":
                        failed_steps.append(f"Job: '{job['name']}' → Step: '{step['name']}' FAILED")

    # Download and extract the log zip
    logs_url = f"https://api.github.com/repos/{repo_name}/actions/runs/{run_id}/logs"
    logs_response = requests.get(logs_url, headers=headers, allow_redirects=True)

    if logs_response.status_code == 200:
        try:
            zip_file = zipfile.ZipFile(io.BytesIO(logs_response.content))
            error_logs = []
            for filename in zip_file.namelist():
                with zip_file.open(filename) as f:
                    content = f.read().decode("utf-8", errors="ignore")
                    if "error" in content.lower() or "fail" in content.lower():
                        error_logs.append(f"--- {filename} ---\n{content[-3000:]}")
            if error_logs:
                return "\n\n".join(error_logs)
        except Exception as e:
            print(f"⚠️  Could not parse log zip: {e}")

    return "\n".join(failed_steps) if failed_steps else "Could not fetch logs."


def trigger_agent_task(repo_name: str, error_logs: str, fix_branch: str, attempt: int):
    try:
        run_patchpilot(repo_name, error_logs, fix_branch, attempt)
    except Exception as e:
        print(f"Agent crashed: {e}")


@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Listens for GitHub Actions workflow events."""
    payload = await request.json()

    workflow_run = payload.get("workflow_run", {})
    repo = payload.get("repository", {})

    repo_name = repo.get("full_name")
    status = workflow_run.get("status")
    conclusion = workflow_run.get("conclusion")
    run_id = workflow_run.get("id")
    head_branch = workflow_run.get("head_branch", "")

    # ─────────────────────────────────────────────────────────────
    # CASE 1: Event is from a PatchPilot fix branch
    # ─────────────────────────────────────────────────────────────
    if head_branch.startswith("patchpilot-fix"):

        # ✅ CI passed on the fix branch — clean up state, done!
        if status == "completed" and conclusion == "success":
            manager.sync_broadcast({"type": "log", "data": f"> 🎉 CI PASSED on fix branch '{head_branch}' for {repo_name}! Cleaning up state."})
            manager.sync_broadcast({"type": "status", "data": "Idle"})
            print(f"\n🎉 CI PASSED on fix branch '{head_branch}' for {repo_name}! Cleaning up state.")
            active_fix_states.pop(repo_name, None)
            return {"status": "Fix successful! CI passed on fix branch."}

        # ❌ CI failed on the fix branch — check if we should retry
        if status == "completed" and conclusion == "failure":
            repo_state = active_fix_states.get(repo_name)

            # Ignore if we have no state for this branch (stale/unknown branch)
            if not repo_state or repo_state["branch"] != head_branch:
                print(f"⏭️  Ignoring unknown PatchPilot branch: '{head_branch}'")
                return {"status": "Ignored. Unknown PatchPilot branch."}

            current_attempts = repo_state["attempts"]

            # Hit max retries — give up and alert
            if current_attempts >= MAX_RETRIES:
                manager.sync_broadcast({"type": "log", "data": f"> ⛔ Max retries ({MAX_RETRIES}) reached for {repo_name}. Manual fix required."})
                manager.sync_broadcast({"type": "status", "data": "Idle"})
                print(f"\n⛔ Max retries ({MAX_RETRIES}) reached for {repo_name}. Manual fix required.")
                active_fix_states.pop(repo_name, None)
                return {
                    "status": f"Max retries ({MAX_RETRIES}) reached. Manual intervention required.",
                    "fix_branch": head_branch
                }

            # Retry on the SAME branch — no new branch created
            new_attempt = current_attempts + 1
            repo_state["attempts"] = new_attempt
            
            manager.sync_broadcast({"type": "log", "data": f"> 🔄 Retry {new_attempt}/{MAX_RETRIES} for {repo_name} on branch '{head_branch}'"})
            manager.sync_broadcast({"type": "status", "data": "Investigating"})
            print(f"\n🔄 Retry {new_attempt}/{MAX_RETRIES} for {repo_name} on branch '{head_branch}'")

            real_error_logs = fetch_workflow_logs(repo_name, run_id)
            print(f"📋 Logs fetched. Triggering retry...")
            manager.sync_broadcast({"type": "log", "data": "> 📋 Logs fetched. Triggering retry..."})

            background_tasks.add_task(
                trigger_agent_task, repo_name, real_error_logs, head_branch, new_attempt
            )
            return {"status": f"PatchPilot retry {new_attempt}/{MAX_RETRIES} triggered on existing branch."}

        return {"status": "Ignored. Workflow not completed yet."}

    # ─────────────────────────────────────────────────────────────
    # CASE 2: Event is from a user branch (main, dev, etc.)
    # ─────────────────────────────────────────────────────────────
    if status == "completed" and conclusion == "failure":
        manager.sync_broadcast({"type": "status", "data": "Investigating"})
        manager.sync_broadcast({"type": "log", "data": f"> ⚠️  Build failed for '{repo_name}' on branch '{head_branch}' (run_id={run_id})"})
        manager.sync_broadcast({"type": "log", "data": "> 📋 Fetching real error logs..."})
        
        print(f"\n⚠️  Build failed for '{repo_name}' on branch '{head_branch}' (run_id={run_id})")
        print("📋 Fetching real error logs...")

        real_error_logs = fetch_workflow_logs(repo_name, run_id)
        
        manager.sync_broadcast({"type": "log", "data": f"> ✅ Logs fetched ({len(real_error_logs)} chars). Triggering PatchPilot..."})
        print(f"✅ Logs fetched ({len(real_error_logs)} chars). Triggering PatchPilot...")

        # Pre-generate the fix branch name and store state BEFORE the background task
        fix_branch = f"patchpilot-fix-{uuid.uuid4().hex[:6]}"
        active_fix_states[repo_name] = {"branch": fix_branch, "attempts": 1}

        print(f"🌿 Designated fix branch: {fix_branch}")
        manager.sync_broadcast({"type": "log", "data": f"> 🌿 Designated fix branch: {fix_branch}"})

        background_tasks.add_task(trigger_agent_task, repo_name, real_error_logs, fix_branch, 1)
        return {"status": "PatchPilot triggered", "fix_branch": fix_branch}

    return {"status": "Ignored. Workflow did not fail."}


if __name__ == "__main__":
    print("Starting PatchPilot API...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)