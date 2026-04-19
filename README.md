# PatchPilot 🚀

**PatchPilot** is an autonomous DevOps AI Agent designed to continuously monitor your GitHub repositories for CI/CD pipeline failures. When a build or test suite fails, PatchPilot jumps into action to analyze the logs, locate the bug, surgically patch the code, and submit a Pull Request for your review—all in real-time.

![PatchPilot Architecture](https://img.shields.io/badge/Status-Active-brightgreen)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)
![Next.js](https://img.shields.io/badge/Frontend-Next.js-black)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-blue)

---

## 🌟 Key Features

1. **Autonomous Bug Fixing**: PatchPilot automatically listens to GitHub webhooks. If a GitHub Action fails, it downloads the exact run logs, reads them, and deduces why the failure occurred.
2. **Surgical Code Patching**: Instead of rewriting entire files (which can cause code corruption), PatchPilot uses a precise `original_snippet` vs `fixed_snippet` patching algorithm to change only the exact lines that contain the bug.
3. **Multi-Attempt Retry Loop**: If PatchPilot's first fix fails the subsequent CI run, it does not spam your repository with new branches. Instead, it maintains the same fix branch and triggers a "Retry Attempt" to try a different approach (up to 3 retries).
4. **Real-Time Next.js Dashboard**: A beautiful, dark-mode terminal dashboard built with Next.js, Tailwind CSS, and Framer Motion. It connects to the backend via WebSockets to stream the AI's internal thoughts and tool executions live.
5. **Approval Gatekeeper**: PatchPilot will never merge code directly to `main`. It opens a Pull Request and pings the frontend dashboard with a "Review & Merge" link, leaving the final decision to a human engineer.
6. **LLM Agnostic**: Powered by LangChain, PatchPilot is currently configured for Cohere's `command-r-plus`, but can easily be swapped to use OpenAI, Google Gemini, Anthropic Claude, DeepSeek, or even local models via Ollama.

---

## 🏗️ Architecture

PatchPilot consists of two main folders:

- **`backend/`**: A Python FastAPI server that handles the LangGraph Agent, GitHub API interactions, webhook listening, and WebSocket broadcasting.
- **`frontend/`**: A Next.js application that provides the live UI.

For an in-depth look at the internal agent logic, tool calls, and state management, see the [Developer Documentation (doc.md)](doc.md).

---

## 🛠️ Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- ngrok (for receiving GitHub webhooks locally)

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` folder:
```env
# Change this depending on which LLM you use (currently Cohere)
COHERE_API_KEY="your-cohere-api-key"

# Fine-grained GitHub PAT with Repo permissions
GITHUB_TOKEN="ghp_your_github_token"
```

Start the backend server:
```bash
python main.py
```

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to view the live dashboard.

### 4. GitHub Webhook
Use ngrok to expose your local backend:
```bash
ngrok http 8000
```
Add the ngrok URL `https://<your-ngrok-id>.ngrok-free.app/webhook` to your GitHub Repository Settings -> Webhooks. Select **Workflow jobs** and **Workflow runs** as the trigger events.

---

## 🤖 Supported AI Models
PatchPilot uses `langchain` and can be pointed to almost any model. It has been tested and configured successfully with:
- **Cohere**: `command-r-plus-08-2024` (Excellent at tool calling)
- **OpenAI**: `gpt-4o` / `gpt-4o-mini`
- **Google**: `gemini-1.5-flash`
- **DeepSeek**: `deepseek-coder`
- **Ollama**: `qwen2.5-coder:3b` (for 100% local, offline execution)

---

## 📄 License
This project is open-source.