# PatchPilot Architecture & Developer Documentation

## 1. System Overview
**PatchPilot** is an autonomous DevOps AI Agent built to continuously monitor GitHub repositories for CI/CD pipeline failures. When a build fails (e.g., tests fail), PatchPilot intercepts the webhook, analyzes the build logs, clones the exact file causing the issue, surgically repairs the code using LLM reasoning, and automatically opens a Pull Request with the fix.

The system is separated into two components:
1. **Backend (FastAPI + LangGraph)**: Handles the AI logic, GitHub webhook listening, codebase manipulation, and state management.
2. **Frontend (Next.js)**: A real-time dashboard that streams the AI's internal thoughts and tool executions over WebSockets.

---

## 2. Technology Stack
### Backend
- **Framework**: FastAPI (Python)
- **AI Agent Orchestration**: LangChain & LangGraph (`create_react_agent`)
- **LLM Provider**: Swappable (currently configured for Cohere `command-r-plus-08-2024`, previously Groq, OpenAI, Google, DeepSeek, Ollama).
- **GitHub Integration**: PyGithub (`github` package) & Direct REST API calls (for logs)
- **Real-time Communication**: WebSockets (`ws_manager.py`)
- **Exposing Localhost**: ngrok

### Frontend
- **Framework**: Next.js 16.x (React)
- **Styling**: Tailwind CSS
- **Icons & Animation**: Lucide React, Framer Motion
- **State Management**: React Hooks (`useState`, `useEffect`)

---

## 3. Core Architecture & Workflow
### A. Webhook Interception (`main.py`)
1. GitHub Actions sends a `workflow_run` event to `/webhook`.
2. The server filters for `status == "completed"` and `conclusion == "failure"`.
3. It downloads the real GitHub Actions logs via `requests` and extracts them from the zip file.
4. It designates a unique `patchpilot-fix-<uuid>` branch.
5. It spins up a `BackgroundTasks` job to trigger the AI Agent so the webhook responds immediately (preventing GitHub timeout).

### B. Agentic Brain (`agent.py`)
1. Uses `create_react_agent` from LangGraph.
2. The LLM is provided a strict `system_prompt` outlining 4 steps: Analyze Logs, Explore Repo, Read File, Reason, and Apply Fix.
3. The agent streams its progress directly to the frontend via the `manager.sync_broadcast()` WebSocket manager.
4. **Retry Loop**: If a fix fails a subsequent CI run, `main.py` detects it and sends a "RETRY ATTEMPT" instruction to the agent up to a maximum of `MAX_RETRIES` (3).

### C. GitHub Tools (`github_tools.py`)
The LLM is given 4 specific capabilities (bound as LangChain `@tool`s):
1. `list_repo_files`: Recursively fetches the entire repository tree structure using the Git Tree API. This allows the LLM to find nested files.
2. `get_github_file`: Fetches the exact content of a target file.
3. `create_pull_request`: Takes an `original_snippet` and `fixed_snippet`. It finds the exact lines in the source file, surgically replaces them, pushes to the new fix branch, and opens a PR.
4. `update_fix_branch`: Used during retry loops. It modifies an existing fix branch instead of opening duplicate PRs.

### D. WebSocket Manager (`ws_manager.py`)
Maintains active connections from the Next.js frontend. It catches logs and status updates ("Idle", "Investigating", "Awaiting Approval") and broadcasts them to all connected clients.

---

## 4. AI Tool Calling (Surgical Patching)
A major innovation in this project is **Surgical Patching**. Early versions allowed the LLM to rewrite entire files, leading to code loss or corruption.
Now, the LLM must provide:
```json
{
  "original_snippet": "expect(1 + 1).toBe(4);",
  "fixed_snippet": "expect(1 + 1).toBe(2);"
}
```
The python backend searches the source file for the *exact* string match of `original_snippet` and replaces it. This guarantees no unrelated code is touched.

---

## 5. File Structure
```text
PatchPilot/
│
├── backend/                  # Python FastAPI application
│   ├── .env                  # API Keys (LLM, GitHub Token)
│   ├── requirements.txt      # Python dependencies
│   ├── main.py               # API endpoints, Webhook logic, Background tasks
│   ├── agent.py              # LangGraph Agent definition and prompt
│   ├── github_tools.py       # LangChain tools for GitHub interactions
│   └── ws_manager.py         # WebSocket connection state
│
└── frontend/                 # Next.js Application
    ├── package.json          # Node dependencies
    ├── tailwind.config.ts    # Tailwind configuration
    └── src/
        └── app/
            ├── globals.css   # Global styles
            └── page.tsx      # Main Dashboard (WebSocket client, UI)
```
