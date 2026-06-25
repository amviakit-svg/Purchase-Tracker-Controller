# Deployment Guide — Purchase Tracker Controller

This document explains exactly how to deploy this tool to a client machine
so that **all your real metadata flows over**: folders, master files,
master activities, rules, processed files, and saved configurations.
The client uploads their own files and runs their own processing on
their machine — runtime data is **not** shipped.

---

## What's included in the deploy bundle

| Artifact | Size | Where it lives | Purpose |
|----------|------|----------------|---------|
| `deploy_template.db` | ~400 KB | Git (`/deploy_template.db`) | Full SQLite snapshot of your `data/metadata.db`: folders, master_files, master_activities, rules, processed_files, configurations |
| `data/template_master_dbs/<folder>/folder_<folder>_master.duckdb` | ~2 MB total | Git | 1 sample DuckDB per master file, 4 rows each — keeps the Master View "alive" on the client |
| `data/uploads/` | (none) | NOT shipped | Client uploads their own files |
| `data/processed/` | (none) | NOT shipped | Client runs their own processing |

The total deploy bundle is **~2.5 MB** — small enough to live entirely in
Git with no LFS needed.

---

## On the SOURCE machine (you, before deploy)

### Step 1: Refresh the deploy template DB (so the client gets your latest metadata)

```cmd
python _build_template_only.py
```

This script:
1. Copies `data/metadata.db` → `deploy_template.db` (your full metadata)
2. Builds `data/template_master_dbs/` with one tiny sample DuckDB per master file
   (4 sample rows each — enough to keep the Master View alive on the client)
3. Re-points `deploy_template.db.master_files.db_path` at the sample DuckDBs
4. VACUUMs `deploy_template.db` to shrink it

### Step 2: Commit and push the deploy bundle to GitHub

```cmd
git add deploy_template.db data\template_master_dbs
git commit -m "Deploy: refresh template DB + sample master DuckDBs"
git push origin main
```

This is the entire deploy. ~2.5 MB, no LFS needed, no zip transfer needed.

---

## On the CLIENT machine (production deploy)

### Step 1: Get the code

```cmd
git clone https://github.com/amviakit-svg/Purchase-Tracker-Controller.git
cd Purchase-Tracker-Controller
```

This brings in:
- All `backend/` and `frontend/` code
- `deploy_template.db` (~400 KB) — your full metadata snapshot
- `data/template_master_dbs/` (~2 MB) — sample master DuckDBs

### Step 2: Install dependencies

```cmd
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt
```

### Step 3: Start the server

```cmd
python backend\main.py
```

The server's `startup_event()` will:
1. See no `data/metadata.db` exists → copies `deploy_template.db` → creates
   `data/metadata.db` with all your folders, master activities, rules,
   processed files, and saved configurations.
2. See no `data/uploads/` exists → copies `data/template_master_dbs/` →
   creates `data/uploads/` so the Master View has data to show.
3. Runs `init_db()` to ensure schema migrations apply cleanly.

The client now sees:
- ✅ All your folders (Root, Uploads, Demo Project, etc.)
- ✅ All your master_files (with 4 sample rows of master data each)
- ✅ All your saved master_activities (formulas, find/replace rules)
- ✅ All your rules (Phase 1/2/3/4 for each validation)
- ✅ All your processed_files history (the DB rows; the .xlsx files
  themselves are not shipped — the client must re-run processing on
  their own data)

### Step 4: Verify

```cmd
curl http://localhost:5000/api/processed/tree
```

You should see JSON with `validation_name` entries for all 3 validations.

### Step 5: Client uploads their own files

The client uses the UI to upload their Excel files. These land in
`data/uploads/` and trigger master file regeneration.

### Step 6: Client runs processing

The client clicks "Process" in the UI. The system runs all the rules
(which came from your deploy) on their files. The output is written to
`data/processed/` and `processed_files` DB rows are added.

---

## What if the client wants to EDIT and re-commit changes back?

Have them:
1. Edit code in `backend/` and `frontend/`
2. Test locally
3. `git add . && git commit -m "..."` (the deploy_template.db has been
   auto-regenerated from their runtime `data/metadata.db` after each
   `init_db()` runs, so it's always in sync)
4. `git push` back to the GitHub repo

---

## Summary

| Question | Answer |
|----------|--------|
| What's in the deploy bundle? | `deploy_template.db` (full metadata, ~400 KB) + `data/template_master_dbs/` (1 sample DuckDB per master, ~2 MB) |
| What's NOT in the deploy bundle? | Uploaded raw files, processed output files, runtime data — the client generates these themselves |
| Total bundle size | ~2.5 MB |
| How does the client get the bundle? | `git clone` (no separate file transfer needed) |
| Can the client just `git clone` and run? | Yes! Server auto-restores everything from `deploy_template.db` on first start |