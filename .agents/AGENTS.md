# Purchase Tracker Controller - AI Rules & Guidelines

These rules serve as persistent memory for AI agents interacting with this workspace. Follow these strictly to maintain the integrity of the project.

## Core Architecture
- **Backend:** Python / FastAPI
- **Database:** DuckDB (analytical) + SQLite (metadata)
- **Frontend:** Vanilla JavaScript, HTML, Tailwind CSS via CDN. (Single-page app in `frontend/index.html` ~13k lines)

## Critical Constraints & Rules

### 1. Server Port & Execution
- The primary server script is `start_server.bat`, which runs uvicorn on **Port 5000**.
- The `README.md` and `start_background.vbs` historically mention Port 8000, but the active production batch script uses 5000. Do not assume the server is down if it is not on 8000.
- **Do not** run the server via `python backend/main.py`. It must be run as a module: `python -m uvicorn backend.main:app` to avoid `ModuleNotFoundError` for internal modules.

### 2. Frontend Modification Safety
- The frontend is a massive Vanilla JS file (`index.html`). Be extremely careful with automated regex replacements or python patching scripts (e.g., `add_finally.py`).
- **Never** inject unverified syntax. Missing brackets or `catch` blocks will break the entire UI completely because the browser will fail to parse the `<script>` blocks.
- If modifying JS logic in `index.html`, prefer precise AST parsers or manual surgical replacements over brute-force scripts.
- Validate any JavaScript syntax modifications immediately (e.g., using `node --check` or the custom `check_js.js` script) to ensure the UI remains functional.

### 3. Tailwind CSS
- Tailwind is loaded via CDN. Do not introduce a build step (Node.js/npm) unless explicitly requested by the user.

### 4. Database Integrity
- DuckDB handles the heavy lifting for reconciliation rules. Do not modify the core schema or `dedup_engine.py` without explicit planning and user approval.

### 5. Deduplication and Row Restoration
- **Row Restoration Dedup**: When restoring a soft-deleted row from the Deleted Rows section, the system must validate the row against existing active rows in master_data using the deduplication engine. If a duplicate is found, the restoration must be rejected with the error 'Data already exist in master file' to prevent bypassing upload duplication checks.
