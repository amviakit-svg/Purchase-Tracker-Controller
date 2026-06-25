# Deployment Guide — Purchase Tracker Controller

This document explains exactly how to deploy this tool to another system
(client machine / staging / production) so that **all your real data**
flows over: master activities, saved configurations, folders, rules,
processed files, and uploaded raw files.

---

## What's included in the deploy bundle

There are **two artifacts** for a full deploy:

| Artifact | Size | Where it lives | Purpose |
|----------|------|----------------|---------|
| `deploy_template.db` | 405 KB | Git (`/deploy_template.db`) | Full SQLite snapshot of your `data/metadata.db` — folders, master_files, master_activities, rules, processed_files, configurations |
| `data/template_master_dbs/` | ~200 MB | NOT in Git (too big) | Full physical DuckDB masters + uploaded raw .xlsx + processed output .xlsx |
| `deploy_bundle.zip` | ~180 MB | Built locally on source, shipped to client | Everything above in one zip |

The `.gitignore` excludes runtime data (`data/uploads/`, `data/processed/`,
`data/metadata.db`, `data/logs/`, etc.) but **commits** the deploy bundle
files (`deploy_template.db` and the small `data/template_master_dbs/`
sample). The full ~200 MB binary bundle is too large for GitHub — ship it
via zip to the client instead.

---

## On the SOURCE machine (you, before deploy)

### Step 1: Refresh the deploy template DB (so the client gets your latest data)

```cmd
copy /Y data\metadata.db deploy_template.db
```

This copies your live `data/metadata.db` (which contains all folders,
master_files, master_activities, rules, processed_files, etc.) into
`deploy_template.db`, which the server reads on first launch.

### Step 2: Build the full binary bundle

```cmd
python _build_bundle.py
```

This produces `deploy_bundle.zip` (~180 MB) at the project root. The zip
contains:
- `deploy_template.db` (405 KB)
- `data/template_master_dbs/` — full physical DuckDB master files + full
  uploads + full processed output (everything the client needs to mirror
  your environment exactly)
- `backend/` (FastAPI source code)
- `frontend/` (HTML/JS source)

### Step 3: Commit and push the code + template DB

```cmd
git add deploy_template.db
git commit -m "Deploy: refresh template DB to latest state"
git push origin main
```

The 200 MB of binary is in `deploy_bundle.zip` — keep that on your
machine, ship it to the client separately.

---

## On the CLIENT machine (production deploy)

### Step 1: Get the code

Either:
- `git clone https://github.com/amviakit-svg/Purchase-Tracker-Controller.git` (gets code + deploy_template.db only), OR
- Unzip `deploy_bundle.zip` if you shipped the full bundle via file transfer.

### Step 2: Install dependencies

```cmd
cd Purchase-Tracker-Controller
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt
```

### Step 3: If you used `git clone` only (not the zip), copy the binary bundle

If you cloned the repo (which only has `deploy_template.db` and a small
`data/template_master_dbs/` sample), you also need to extract the binary
bundle to get the full master DuckDBs and uploaded/processed files:

```cmd
# In the repo root
# Unzip deploy_bundle.zip on top of the repo, overwriting existing files
# OR copy from a network share / SFTP drop / OneDrive:
#   - data/template_master_dbs/  -> ./data/template_master_dbs/
```

The server automatically picks up everything in `data/template_master_dbs/`
on first launch (via `startup_event()` in `backend/main.py`).

### Step 4: Start the server

```cmd
python backend\main.py
```

The server:
1. Sees no `data/metadata.db` → copies `deploy_template.db` → creates
   `data/metadata.db` with all your folders, master activities, rules,
   configurations, processed files.
2. Sees no `data/uploads/` → copies `data/template_master_dbs/` → creates
   `data/uploads/` with all your uploaded raw files.
3. Runs `init_db()` to ensure schema migrations apply cleanly.

### Step 5: Verify

```cmd
curl http://localhost:5000/api/processed/tree
```

You should see JSON with `validation_name` entries for all 3 validations
(1, 2, 3) and your full file counts.

---

## What if the client DOESN'T want GitHub?

Skip the `git push`. Just ship `deploy_bundle.zip` directly to the client
via SFTP, OneDrive, USB drive, etc. The client unzips it and runs Step 4
above — no Git involved.

---

## What if the client wants to EDIT and re-commit changes back?

Have them:
1. Edit the code in `backend/` and `frontend/`
2. Test locally
3. `git add . && git commit -m "..."` (the deploy_template.db has been
   auto-regenerated from their runtime `data/metadata.db` after each
   `init_db()` runs, so it's always in sync)
4. `git push` back to the GitHub repo (or your private Git server)

---

## Summary

| Question | Answer |
|----------|--------|
| What's the minimum needed for a working deploy? | `deploy_template.db` (405 KB) + `backend/` + `frontend/` |
| What if I want the client to have all my files? | Ship `deploy_bundle.zip` (~180 MB) instead |
| Where does `data/uploads/` come from? | Auto-created from `data/template_master_dbs/` on first start |
| Where do my processed output .xlsx files come from? | Same — from `data/template_master_dbs/processed/` |
| Where do my master DuckDBs come from? | Same — from `data/template_master_dbs/<folder_id>/` |
| Can the client just `git clone` and run? | Yes, but they'll only get the demo sample. For full data, use the zip. |