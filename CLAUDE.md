# Setting up the Repo

- reference the @README.md file for the full context on how to set this repo up
- when asked for help in setting up the repo, slowly walk the user through setting up each step

# Running the Application

- NEVER run any python/pip commands without activating the virtual environment first (`. .venv/bin/activate`)
- Run the application with `python run.py`

# Code Reviews

- This repo is publicly accessible for our customers. It should NOT contain any details or information of our internal processes.
It should only pertain to the details documented in our [public API interface](https://docs.ada.cx/generative/reference/conversations/overview)
- All code should be written from the perspective of a customer attempting to integrate into this API interface
- Significant restructures to the code should be reflected in this @CLAUDE.md file
- All environment configuration should be added to the @.env.example template file

# Change Submissions

- Never commit directly into `main`; use a new pull request branch instead

# File Structure
- `docs/assets/` — Documentation assets
- `.env.example` — Template for required environment variables
- `pyproject.toml` — Project metadata and dependencies
- `run.py` — Entrypoint. Loads `.env` and starts the web server
- `app/` — Main application package
  - `__init__.py` — Configures and starts a nicegui application
  - `ada_api.py` — HTTP client for Ada's Conversations API
  - `data/` — Data models
    - `messages.py` — Models for various Ada message content types
  - `server/` — FastAPI/NiceGUI server routes.
    - `api.py` — Registers the webhook and webpage routers.
    - `webhooks.py` — Webhook endpoints: `POST /webhooks/start-handoff` and `POST /webhooks/events` (with Svix signature verification and event batching).
  - `webpage/` — NiceGUI frontend for the agent interface.
    - `index.py` — Main page (`/`) with chat UI, file upload, send message, and end handoff actions.
    - `agent_ui.py` — `AgentUI` class managing chat state, message rendering, ticket lifecycle, and transcript loading.
