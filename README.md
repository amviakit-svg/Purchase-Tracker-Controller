# Purchase Tracker Controller

A powerful data reconciliation platform built with Python (FastAPI) and DuckDB for handling large-scale Excel file processing, rule-based matching, and automated reporting.

> **Note:** The application is also known internally as the "Reconciliation Tool". The product has been rebranded to **Purchase Tracker Controller** for the user-facing product name.

## Quick Start

### Option 1: One-time Setup (First Run Only)
If you don't have a `venv/` folder yet, double-click **`setup.bat`** to:
- Verify Python is installed
- Create the `venv\` virtual environment
- Install all dependencies from `backend\requirements.txt`

You only need to run this once per machine (or after the requirements change).

### Option 2: Start Server (Easiest - Background Mode)
Double-click **`start_server.bat`**. This will:
- Start the server in the **background** (no terminal window to keep open!)
- You can close the startup window immediately after it starts
- The server will keep running until you restart your computer

Then open your browser to: **http://localhost:8000**

### Option 3: Start with Browser Auto-Open
Double-click **`start_background.vbs`**. This will:
- Start the server silently in the background (no window at all!)
- Automatically open your browser to the tool

### Option 4: Stop the Server
To stop the background server, run:
```cmd
taskkill /f /im python.exe
```

### Option 5: Command Line (For Developers)
Open Command Prompt in the project folder and run:
```cmd
venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Then open your browser to: **http://localhost:8000**

---

## Project Structure

```
Purchase Tracker Controller/
├── backend/
│   ├── main.py            # FastAPI application (primary entry point)
│   ├── database.py        # SQLite schema, migrations, queries
│   ├── primary_data.py    # Phase 1 — unique-value extraction
│   ├── formula_engine.py  # Custom formula expression parser
│   ├── auto_sync.py       # Debounced background DuckDB sync
│   ├── filename_parser.py # Indian FY / month detection from filenames
│   ├── seed.py            # One-time default-company/module/user seeder
│   ├── migrate_file_paths.py  # One-shot path migration utility
│   ├── update_readmes.py  # Module-level README generator
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html         # Single-page application UI (~5,400 lines)
│   ├── activities.js      # Master-file activity steps viewer
│   └── notif_logic.js     # Notifications + toasts
├── data/                  # Created on first run
│   ├── uploads/           # Uploaded Excel/CSV files
│   ├── master_files/      # DuckDB master files (per folder)
│   ├── processed/         # Final reconciliation reports
│   └── metadata.db        # SQLite metadata store
├── venv/                  # Python virtual environment (created by setup.bat)
├── setup.bat              # First-time setup (run once)
├── start_server.bat       # One-click server startup
├── start_background.vbs   # Silent background launcher with auto-restart
├── install_service.bat    # NSSM Windows service installer
├── deploy.bat             # PyInstaller standalone-build entry point
├── restart_server.py      # Kill-and-restart helper
└── README.md
```

---

## Features

### 1. Dashboard
- Overview statistics (Files, Folders, Master Files, Rules)
- Financial-year tree view (Indian FY Apr–Mar)
- Recent activity tracking
- Reconciliation status indicators

### 2. Upload & File Management
- **Drag-and-drop upload** for Excel files (.xlsx, .xls, .csv)
- **Folder management** with subfolder support
- **File details** view showing sheets, rows, and columns
- **Bulk operations**: Move, Delete, Multi-select
- **Master File Creation**: Merge folder files into DuckDB for fast processing
- **Auto-Sync** (optional): New files are appended and deleted files removed from the master in the background

### 3. Rule Mapping (4 Phases)
- **Phase 1**: Select primary data (File / Sheet / Column) and add extra fields (SUM / VLOOKUP)
- **Phase 2**: Configure matching rules (VLOOKUP, SUMIF, COUNTIF, addition, subtraction, calculation chains)
- **Phase 3**: Remarks and conditions
- **Phase 4**: Summary & pivot configuration with chart options

### 4. Activity Window
ETL-style persistent steps that survive across auto-sync cycles:
- Formula columns (SUM, SUBTRACT, MULTIPLY, DIVIDE, PERCENTAGE, CONCAT, ABS, EXPRESSION, etc.)
- SUMIF / COUNTIF / VLOOKUP / HLOOKUP across folders
- Find & Replace
- Column Rename / Delete
- Row Filter (AND / OR conditions)
- Reorder, enable/disable, and dry-run each step

### 5. Final Processing
- One-click execution of all configured rules
- Source-file filter (include/exclude specific source files)
- Phase-wise status tracking
- Pivot summaries with bar / pie / line charts
- Excel export of processed output

---

## Technology Stack

| Component         | Technology                          |
|-------------------|-------------------------------------|
| Backend           | FastAPI (Python)                    |
| Analytical DB     | DuckDB (handles millions of rows)   |
| Metadata DB       | SQLite                               |
| Frontend          | Vanilla JavaScript + Tailwind CSS   |
| File Processing   | Pandas + openpyxl                   |
| Charting          | Matplotlib                           |
| Auth (optional)   | bcrypt + python-jose (currently stubbed — see Known Limitations) |

---

## How to Use

1. **Run first-time setup** by double-clicking `setup.bat` (only needed once)
2. **Start the server** by double-clicking `start_server.bat`
3. **Open browser** to `http://localhost:8000`
4. **Go to Upload & Files tab**
   - Create folders as needed
   - Upload Excel files via drag-and-drop
   - Click on files to view detailed information
5. **Create Master Files**
   - Select a folder with files
   - Click "Create Master File"
   - Choose sheet, header row, and columns
   - Files are merged into a fast DuckDB database
6. **Configure Rules**
   - Phase 1: Select your primary data column
   - Phase 2: Add matching rules row by row
   - Phase 3: Set up remarks (coming soon / optional)
   - Phase 4: Define pivot summaries
7. **Run Processing**
   - Go to Final Processing tab
   - Click "Process All Rules"
   - Download your reconciliation report

---

## Requirements

- Python 3.10+ (tested on 3.14)
- Windows 10/11 (primary target)
- Modern web browser (Chrome, Firefox, Edge)
- ~500 MB free disk space for `venv\` and dependencies

---

## Dependencies

All dependencies are listed in `backend/requirements.txt` and installed automatically by `setup.bat`:

- fastapi
- uvicorn
- duckdb
- pandas
- openpyxl
- python-multipart
- matplotlib
- numpy
- Pillow
- bcrypt
- python-jose[cryptography]
- passlib

To reinstall dependencies manually:
```cmd
venv\Scripts\pip install -r backend\requirements.txt
```

---

## Known Limitations

The product is feature-complete for its target use case but has these caveats:

1. **Authentication is stubbed.** `get_current_active_user` and `require_role` in `backend/main.py` always return admin/1. The `bcrypt` / `python-jose` dependencies are declared in `requirements.txt` but the JWT/session flow is not wired up. Roles and page permissions are defined in the database but not enforced. The product is intended to be a single-user, local Windows tool.
2. **No automated test suite.** There is no `pytest` test suite. A hand-rolled smoke test (`test_master.py` at the project root) exercises the master-file workflow using FastAPI's `TestClient` and can be run manually with `venv\Scripts\python test_master.py`. The `/health` endpoint is the primary runtime verification.
3. **Windows-only startup scripts.** `start_server.bat`, `start_background.vbs`, and `install_service.bat` are Windows-only. For Linux/macOS, use `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` after creating a virtual environment.
4. **Tailwind via CDN.** The frontend loads Tailwind from a CDN at runtime (no build step). The first page load requires internet access for the CDN to respond.
5. **Very large rule sets** (hundreds of Phase 2 rules) may slow down the rule-loading screen due to sequential per-rule API calls.
6. **Single-process.** The server runs as one uvicorn worker. No clustering, no queue, no multi-tenant isolation at the runtime level (database-level isolation only).
7. **Notifications are not persisted in real-time** — they are stored in SQLite and polled by the frontend every 10 seconds. There is no WebSocket push.

---

## License

Internal / proprietary — see your distribution agreement.