import sqlite3
import os
import json
from datetime import datetime, timezone, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'metadata.db')

# Indian Standard Time (UTC+5:30). Used for any user-facing timestamp we
# INSERT into the DB so the rejected files table shows IST regardless of
# the host server's local TZ.
IST_TZ = timezone(timedelta(hours=5, minutes=30))
def _ist_now_str():
    """Current IST time as a 'YYYY-MM-DD HH:MM:SS' string (matches schema)."""
    return datetime.now(IST_TZ).strftime('%Y-%m-%d %H:%M:%S')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    try:

        # =================== CORE TABLES ===================
    
        # Companies table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # Modules table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',
                template_company_id INTEGER,
                readme_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # Company-Module association
        conn.execute('''
            CREATE TABLE IF NOT EXISTS company_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                module_id INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (module_id) REFERENCES modules (id),
                UNIQUE(company_id, module_id)
            )
        ''')
    
        # Super Admin table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS super_admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
    
        # Roles table (global, created by super admin)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                page_permissions TEXT NOT NULL,
                action_permissions TEXT NOT NULL,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # User-Module assignment table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                module_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (module_id) REFERENCES modules (id),
                UNIQUE(user_id, module_id)
            )
        ''')

        # Users table (company users)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                role TEXT DEFAULT 'viewer',
                role_id INTEGER,
                status TEXT DEFAULT 'active',
                first_login INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (role_id) REFERENCES roles (id),
                UNIQUE(company_id, email)
            )
        ''')
    
        # Website Settings table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS website_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                setting_group TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # Audit Logs table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_role TEXT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT,
                company_id INTEGER,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # Recycle Bin table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recycle_bin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                entity_name TEXT NOT NULL,
                original_path TEXT,
                metadata TEXT,
                deleted_by TEXT,
                module_id INTEGER,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # Folders table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                module_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                parent_id INTEGER,
                path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES folders (id)
            )
        ''')
    
        # Files table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                module_id INTEGER,
                folder_id INTEGER NOT NULL,
                name TEXT,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                format TEXT,
                size INTEGER,
                sheet_names TEXT,
                header_row INTEGER DEFAULT 1,
                sync_status TEXT DEFAULT 'pending',
                sync_error TEXT,
                uploaded_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (folder_id) REFERENCES folders (id)
            )
        ''')
    
        # Migrate existing files table if header_row doesn't exist
        cursor = conn.execute("PRAGMA table_info(files)")
        cols = [row['name'] for row in cursor.fetchall()]
        if 'header_row' not in cols:
            try:
                conn.execute("ALTER TABLE files ADD COLUMN header_row INTEGER DEFAULT 1")
                conn.commit()
            except Exception:
                pass
        if 'sync_status' not in cols:
            try:
                conn.execute("ALTER TABLE files ADD COLUMN sync_status TEXT DEFAULT 'pending'")
                conn.execute("ALTER TABLE files ADD COLUMN sync_error TEXT")
                conn.commit()
            except Exception:
                pass
        if 'uploaded_by' not in cols:
            try:
                conn.execute("ALTER TABLE files ADD COLUMN uploaded_by INTEGER")
                conn.commit()
            except Exception:
                pass
    
        # Master files table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS master_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                module_id INTEGER,
                folder_id INTEGER NOT NULL,
                db_path TEXT NOT NULL,
                sheet_name TEXT,
                columns TEXT,
                header_row INTEGER,
                concat_columns TEXT,
                rejected_files TEXT,
                formulas TEXT,
                auto_sync INTEGER DEFAULT 0,
                hidden_columns TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (folder_id) REFERENCES folders (id)
            )
        ''')
    
        # Migrate existing master_files table if auto_sync doesn't exist
        cursor = conn.execute("PRAGMA table_info(master_files)")
        cols = [row['name'] for row in cursor.fetchall()]
        if 'auto_sync' not in cols:
            try:
                conn.execute("ALTER TABLE master_files ADD COLUMN auto_sync INTEGER DEFAULT 0")
                conn.commit()
            except Exception:
                pass
            
        if 'hidden_columns' not in cols:
            try:
                conn.execute("ALTER TABLE master_files ADD COLUMN hidden_columns TEXT DEFAULT '[]'")
                conn.commit()
            except Exception:
                pass

        # Master Activities table (Activity Window - ETL-style persistent steps)
        # Captures user-applied transformations (formulas, find/replace, column ops)
        # so they survive across auto-sync cycles when files are added/removed.
        conn.execute('''
            CREATE TABLE IF NOT EXISTS master_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                master_file_id INTEGER,
                folder_id INTEGER NOT NULL,
                company_id INTEGER,
                module_id INTEGER,
                step_order INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                target_column TEXT,
                payload_json TEXT NOT NULL,
                is_enabled INTEGER DEFAULT 1,
                validation_status TEXT DEFAULT 'ok',
                last_error TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_applied_at TIMESTAMP,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE CASCADE
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_master_activities_scope ON master_activities(company_id, module_id, folder_id, step_order)')

        # Notifications table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                module_id INTEGER,
                user_id INTEGER,
                role_id INTEGER,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                link TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # Migrate existing notifications table for user_id and role_id
        cursor = conn.execute("PRAGMA table_info(notifications)")
        cols = [row['name'] for row in cursor.fetchall()]
        if 'user_id' not in cols:
            try:
                conn.execute("ALTER TABLE notifications ADD COLUMN user_id INTEGER")
                conn.execute("ALTER TABLE notifications ADD COLUMN role_id INTEGER")
                conn.commit()
            except Exception:
                pass
            
        # Rules configuration table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                module_id INTEGER,
                name TEXT,
                phase INTEGER NOT NULL,
                validation_id INTEGER DEFAULT 1,
                config TEXT NOT NULL,
                processing_type TEXT DEFAULT 'both',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
        # Processed files table
        # NOTE: the `validation` column is REQUIRED by get_processed_files() and
        # save_processed_file() and MUST be present in fresh schemas. It is
        # also added via the migrations block below for legacy DBs that
        # pre-date this column.
        conn.execute('''
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                module_id INTEGER,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                report_type TEXT,
                financial_year TEXT,
                month_name TEXT,
                month_number INTEGER,
                year INTEGER,
                source_primary_filename TEXT,
                total_rows INTEGER,
                rules_used INTEGER,
                sheets_data TEXT,
                file_size REAL,
                processing_time TEXT,
                validation INTEGER DEFAULT 2,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # =================== MIGRATIONS ===================

        # Helper to check if column exists
        def column_exists(table, column):
            try:
                conn.execute(f"SELECT {column} FROM {table} LIMIT 1")
                return True
            except Exception:
                return False

        # Migrate existing tables to add company_id and module_id
        tables_to_migrate = [
            ("folders", ["company_id", "module_id"]),
            ("files", ["company_id", "module_id"]),
            ("master_files", ["company_id", "module_id"]),
            ("rules", ["company_id", "module_id"]),
            ("processed_files", ["company_id", "module_id"]),
            ("recycle_bin", ["company_id", "module_id"])
        ]

        for table, columns in tables_to_migrate:
            for col in columns:
                if not column_exists(table, col):
                    try:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER")
                    except sqlite3.OperationalError:
                        pass

        # Migrate existing columns
        migrations = [
            ("rules", "processing_type", "TEXT DEFAULT 'both'"),
            ("master_files", "rejected_files", "TEXT"),
            ("processed_files", "file_size", "REAL"),
            ("processed_files", "processing_time", "TEXT"),
            ("processed_files", "validation", "INTEGER DEFAULT 2"),  # CRITICAL for /api/processed/files
            ("users", "first_login", "INTEGER DEFAULT 1"),
            ("users", "role_id", "INTEGER"),
            ("master_files", "formulas", "TEXT"),
            ("companies", "status", "TEXT DEFAULT 'active'"),
            ("modules", "status", "TEXT DEFAULT 'active'"),
            ("modules", "template_company_id", "INTEGER"),
            ("modules", "readme_content", "TEXT"),
            ("company_modules", "status", "TEXT DEFAULT 'active'"),
            ("users", "status", "TEXT DEFAULT 'active'"),
            ("super_admin", "status", "TEXT DEFAULT 'active'"),
            ("folders", "description", "TEXT"),
            ("folders", "path", "TEXT"),
            ("files", "name", "TEXT"),
            # ---- Duplicate detection (Concat) on master_file_configs ----
            ("master_file_configs", "dedup_enabled",   "INTEGER DEFAULT 0"),
            ("master_file_configs", "dedup_columns",   "TEXT"),
            ("master_file_configs", "dedup_separator", "TEXT DEFAULT ' | '"),
            ("master_file_configs", "updated_at",      "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ]

        for table, column, col_type in migrations:
            if not column_exists(table, column):
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                except sqlite3.OperationalError:
                    pass

        # ---- Rejected Artefacts table (downloadable full-file reject reports) ----
        conn.execute('''
            CREATE TABLE IF NOT EXISTS rejected_artefacts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id       INTEGER NOT NULL,
                file_id         INTEGER,
                original_name   TEXT NOT NULL,
                artefact_path   TEXT NOT NULL,
                reject_reason   TEXT,
                rejected_rows   INTEGER,
                total_rows      INTEGER,
                source          TEXT DEFAULT 'merge',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_rejected_artefacts_folder ON rejected_artefacts(folder_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_rejected_artefacts_file   ON rejected_artefacts(file_id)')

        # Migrations
        try:
            conn.execute('ALTER TABLE rules ADD COLUMN validation_id INTEGER DEFAULT 1')
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # =================== DEFAULT DATA ===================

        # Insert default modules
        conn.execute('''
            INSERT OR IGNORE INTO modules (id, name, code, description) VALUES (1, 'Website module', 'WEBSITE', 'Default Workspace')
        ''')

        # ---- Auto-seed when DB is empty (no template.db available) ----
        # If init_db() is being run on a fresh system with no template.db,
        # still seed a baseline structure so the app is usable immediately:
        #   - 1 Root folder, 1 Uploads folder (under module 1)
        #   - 1 sample demo master_file (so the dashboard / master view loads)
        #   - 1 sample processed_file (so the history view is non-empty)
        # The user can replace/delete these as soon as they start using the app.
        try:
            cursor = conn.execute('SELECT COUNT(*) FROM folders')
            folder_count = cursor.fetchone()[0]
            if folder_count == 0:
                # Use print() rather than logger.* because logging may not be
                # configured yet when init_db() is first called from tests.
                print("[init_db] Empty database detected - seeding default workspace structure.")
                # Root + Uploads folders under module 1
                cursor = conn.execute(
                    'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                    ('Root', 1, 1, 'Auto-seeded root', None, '/Root')
                )
                root_id = cursor.lastrowid
                cursor = conn.execute(
                    'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                    ('Uploads', 1, 1, 'Default uploads folder', root_id, '/Root/Uploads')
                )
                uploads_id = cursor.lastrowid

                # Sample demo folder + master file structure (so dashboard isn't empty)
                cursor = conn.execute(
                    'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                    ('Demo Project', 1, 1, 'Demo project seeded by init_db()', uploads_id, '/Root/Uploads/Demo Project')
                )
                demo_id = cursor.lastrowid

                # Sample master_files row (points to a placeholder .duckdb path)
                # This is intentionally a relative path - actual data files are
                # generated by the user when they upload.
                conn.execute(
                    '''INSERT INTO master_files
                       (folder_id, company_id, module_id, db_path, sheet_name, columns,
                        header_row, concat_columns, auto_sync, hidden_columns)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (demo_id, 1, 1,
                     f'data/uploads/Demo_Project_{demo_id}.duckdb',
                     'Sheet1', '[]', 1, '[]', 0, '[]')
                )

                # Sample processed_files row so the history view loads
                conn.execute(
                    '''INSERT INTO processed_files
                       (filename, file_path, report_type, financial_year, month_name,
                        month_number, year, source_primary_filename, total_rows, rules_used,
                        sheets_data, company_id, module_id, validation, file_size, processing_time)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    ('welcome_sample.xlsx',
                     'data/processed/welcome_sample.xlsx',
                     'Sample Report', '2025', 'January', 1, 2025,
                     'demo_primary.xlsx', 0, 0, '{}', 1, 1, 2,
                     1024.0, '0.5s')
                )

                # Sample activity so the Activity Window isn't empty
                conn.execute(
                    '''INSERT INTO master_activities
                       (folder_id, company_id, module_id, step_order, activity_type,
                        target_column, payload_json, is_enabled, validation_status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (demo_id, 1, 1, 10, 'WELCOME', None,
                     '{"note": "Welcome - replace this demo activity with your own formulas."}',
                     1, 'ok')
                )
                print("[init_db] Default workspace structure seeded.")
        except Exception as seed_err:
            print(f"[init_db] Auto-seed skipped due to: {seed_err}")

        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

# =================== HELPER FUNCTIONS ===================

def create_folder(name, company_id=None, module_id=None, description=None, parent_id=None):
    conn = get_db_connection()
    try:
    
        # Calculate path dynamically
        path = f"/Root/{name}"
        if parent_id:
            parent = conn.execute("SELECT path FROM folders WHERE id = ?", (parent_id,)).fetchone()
            if parent and parent['path']:
                path = f"{parent['path']}/{name}"
            
        cursor = conn.execute(
            'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
            (name, company_id, module_id, description, parent_id, path)
        )
        folder_id = cursor.lastrowid
        conn.commit()
        return folder_id

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_folders(company_id=None, module_id=None):
    conn = get_db_connection()
    try:
    
        # Auto-initialize Root and Uploads folders for this module if they don't exist
        if module_id:
            existing_root = conn.execute(
                'SELECT id FROM folders WHERE module_id = ? AND name = ? AND parent_id IS NULL',
                (module_id, 'Root')
            ).fetchone()
        
            if not existing_root:
                # Build the display path: /Root
                display_path = '/Root'
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                    ('Root', company_id, module_id, None, None, display_path)
                )
                root_id = cursor.lastrowid
            
                # Insert the 'Uploads' folder
                f_path = f"{display_path}/Uploads"
                cursor.execute(
                    'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                    ('Uploads', company_id, module_id, None, root_id, f_path)
                )
                conn.commit()
    
        if company_id and module_id:
            rows = conn.execute(
                '''SELECT f.*, (SELECT COUNT(1) FROM files fi WHERE fi.folder_id = f.id) as file_count 
                   FROM folders f WHERE f.company_id = ? AND f.module_id = ? 
                   ORDER BY f.created_at DESC''',
                (company_id, module_id)
            ).fetchall()
        elif module_id:
            # Fallback if no company_id but module_id is provided
            rows = conn.execute(
                '''SELECT f.*, (SELECT COUNT(1) FROM files fi WHERE fi.folder_id = f.id) as file_count 
                   FROM folders f WHERE f.module_id = ? 
                   ORDER BY f.created_at DESC''',
                (module_id,)
            ).fetchall()
        elif company_id:
            rows = conn.execute(
                '''SELECT f.*, (SELECT COUNT(1) FROM files fi WHERE fi.folder_id = f.id) as file_count 
                   FROM folders f WHERE f.company_id = ? 
                   ORDER BY f.created_at DESC''',
                (company_id,)
            ).fetchall()
        else:
            rows = conn.execute('''SELECT f.*, (SELECT COUNT(1) FROM files fi WHERE fi.folder_id = f.id) as file_count 
                                   FROM folders f ORDER BY f.created_at DESC''').fetchall()
        return [dict(row) for row in rows]

    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_folder(folder_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM files WHERE folder_id = ?', (folder_id,))
        conn.execute('DELETE FROM master_files WHERE folder_id = ?', (folder_id,))
        try:
            conn.execute('DELETE FROM master_file_configs WHERE folder_id = ?', (folder_id,))
        except Exception:
            pass
        conn.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
        conn.commit()

    finally:
        try:
            conn.close()
        except Exception:
            pass
def save_file_metadata(folder_id, original_name, file_path, file_format, size, sheet_names, company_id=None, module_id=None, header_row=1, uploaded_by=None):
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            '''INSERT INTO files (folder_id, name, original_name, file_path, format, size, sheet_names, company_id, module_id, header_row, uploaded_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (folder_id, original_name, original_name, file_path, file_format, size, json.dumps(sheet_names) if sheet_names else None, company_id, module_id, header_row, uploaded_by)
        )
        file_id = cursor.lastrowid
        conn.commit()
        return file_id

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_files_by_folder(folder_id):
    import json
    conn = get_db_connection()
    try:
        rows = conn.execute(
            '''SELECT f.*, u.name as uploaded_by_name 
               FROM files f 
               LEFT JOIN users u ON f.uploaded_by = u.id 
               WHERE f.folder_id = ? 
               ORDER BY f.created_at DESC''',
            (folder_id,)
        ).fetchall()
    
        result = []
        for row in rows:
            d = dict(row)
            try:
                if d.get('sheet_names'):
                    sheets = json.loads(d['sheet_names'])
                    if isinstance(sheets, str):
                        try:
                            sheets = json.loads(sheets)
                        except Exception:
                            pass
                        
                    if isinstance(sheets, list):
                        d['sheet_count'] = len(sheets)
                    else:
                        d['sheet_count'] = 1
                else:
                    d['sheet_count'] = 0
            except Exception:
                d['sheet_count'] = 0
            result.append(d)
        
        return result

    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_file(file_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
        conn.commit()

    finally:
        try:
            conn.close()
        except Exception:
            pass
def move_file(file_id, new_folder_id):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE files SET folder_id = ? WHERE id = ?', (new_folder_id, file_id))
        conn.commit()

    finally:
        try:
            conn.close()
        except Exception:
            pass
def save_master_file(folder_id, db_path, sheet_name=None, columns=None, header_row=None, concat_columns=None, rejected_files=None, formulas=None, company_id=None, module_id=None, auto_sync=None):
    conn = get_db_connection()
    try:
        # Check if exists
        existing = conn.execute('SELECT id FROM master_files WHERE folder_id = ?', (folder_id,)).fetchone()
        if existing:
            conn.execute(
                '''UPDATE master_files SET db_path = ?, sheet_name = ?, columns = ?, header_row = ?, 
                   concat_columns = ?, rejected_files = ?, formulas = ?, company_id = ?, module_id = ?, auto_sync = COALESCE(?, auto_sync) WHERE folder_id = ?''',
                (db_path, sheet_name, json.dumps(columns) if columns else None, header_row, 
                 json.dumps(concat_columns) if concat_columns else None, 
                 json.dumps(rejected_files) if rejected_files else None,
                 json.dumps(formulas) if formulas else None,
                 company_id, module_id, auto_sync, folder_id)
            )
        else:
            conn.execute(
                '''INSERT INTO master_files (folder_id, db_path, sheet_name, columns, header_row, 
                   concat_columns, rejected_files, formulas, company_id, module_id, auto_sync)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, 0))''',
                (folder_id, db_path, sheet_name, json.dumps(columns) if columns else None, header_row,
                 json.dumps(concat_columns) if concat_columns else None,
                 json.dumps(rejected_files) if rejected_files else None,
                 json.dumps(formulas) if formulas else None,
                 company_id, module_id, auto_sync)
            )
        conn.commit()

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_master_file(folder_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM master_files WHERE folder_id = ?', (folder_id,)).fetchone()
        return dict(row) if row else None

    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_master_file(folder_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM master_files WHERE folder_id = ?', (folder_id,))
        conn.commit()

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_master_formulas(folder_id):
    """Get persisted formulas for a master file."""
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT formulas FROM master_files WHERE folder_id = ?', (folder_id,)).fetchone()
        if row and row['formulas']:
            try:
                return json.loads(row['formulas'])
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    finally:
        try:
            conn.close()
        except Exception:
            pass
def update_master_formulas(folder_id, formulas_list):
    """Update persisted formulas for a master file."""
    conn = get_db_connection()
    try:
        conn.execute(
            'UPDATE master_files SET formulas = ? WHERE folder_id = ?',
            (json.dumps(formulas_list) if formulas_list else None, folder_id)
        )
        conn.commit()

    finally:
        try:
            conn.close()
        except Exception:
            pass
def save_rule(phase, config, name=None, company_id=None, module_id=None,
              processing_type='both', validation_id=1):
    """Save a rule row."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO rules (phase, config, name, company_id, module_id, processing_type, validation_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (phase, json.dumps(config), name, company_id, module_id, processing_type, validation_id)
        )
        rule_id = cursor.lastrowid
        conn.commit()
        return rule_id

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_rules_by_phase(phase, company_id=None, module_id=None, validation_id=1):
    """Get rules for a given phase."""
    conn = get_db_connection()
    try:
        if company_id and module_id:
            rows = conn.execute(
                'SELECT * FROM rules WHERE phase = ? AND company_id = ? AND module_id = ? AND validation_id = ? ORDER BY created_at ASC',
                (phase, company_id, module_id, validation_id)
            ).fetchall()
        elif company_id:
            rows = conn.execute(
                'SELECT * FROM rules WHERE phase = ? AND company_id = ? AND validation_id = ? ORDER BY created_at ASC',
                (phase, company_id, validation_id)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM rules WHERE phase = ? AND validation_id = ? ORDER BY created_at ASC',
                (phase, validation_id)
            ).fetchall()
        return [dict(row) for row in rows]

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_all_rules(company_id=None, module_id=None, validation_id=1):
    """Get all rules."""
    conn = get_db_connection()
    try:
        if company_id and module_id:
            rows = conn.execute(
                'SELECT * FROM rules WHERE company_id = ? AND module_id = ? AND validation_id = ? ORDER BY phase ASC, created_at ASC',
                (company_id, module_id, validation_id)
            ).fetchall()
        elif company_id:
            rows = conn.execute(
                'SELECT * FROM rules WHERE company_id = ? AND validation_id = ? ORDER BY phase ASC, created_at ASC',
                (company_id, validation_id)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM rules WHERE validation_id = ? ORDER BY phase ASC, created_at ASC',
                (validation_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_rule(rule_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM rules WHERE id = ?', (rule_id,))
        conn.commit()

    finally:
        try:
            conn.close()
        except Exception:
            pass
def move_to_recycle_bin(company_id=None, entity_type=None, entity_id=None, entity_name=None, original_path=None, metadata=None, deleted_by=None, module_id=None):
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO recycle_bin (company_id, entity_type, entity_id, entity_name, original_path, metadata, deleted_by, module_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (company_id, entity_type, entity_id, entity_name, original_path, json.dumps(metadata) if metadata else None, deleted_by, module_id)
        )
        conn.commit()

    # =================== STORAGE ERROR HANDLING ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
STORAGE_ERROR_MAP = {
    "company_not_found": {
        "reason": "Company record not found in database",
        "suggestion": "Verify the company exists. Super Admin must create the company first."
    },
    "module_not_found": {
        "reason": "Module record not found in database",
        "suggestion": "Verify the module exists. Check Modules page in Super Admin panel."
    },
    "dir_create_failed": {
        "reason_template": "Unable to create directory: {path}",
        "suggestion": "Check disk space and write permissions on the server filesystem. Error: {os_error}"
    },
    "disk_full": {
        "reason": "No disk space remaining on the server",
        "suggestion": "Free up disk space or contact your server administrator."
    },
    "permission_denied": {
        "reason_template": "Write permission denied for directory: {path}",
        "suggestion": "The server process needs write access. Check folder permissions and ensure the directory is writable."
    },
    "invalid_folder_name": {
        "reason_template": "Folder name '{name}' contains invalid characters",
        "suggestion": "Use only letters, numbers, spaces, hyphens, and underscores. Avoid characters: \\ / : * ? \" < > |"
    },
    "path_too_long": {
        "reason": "File path exceeds operating system limit (260 characters)",
        "suggestion": "Use shorter folder and file names. Keep the full path under 260 characters."
    },
    "file_exists": {
        "reason_template": "A file named '{name}' already exists in this folder",
        "suggestion": "Rename the file before uploading, or delete the existing file first."
    },
    "parent_missing": {
        "reason": "Parent directory does not exist on disk",
        "suggestion": "The folder structure may be incomplete. Try recreating the folder or contact support."
    },
    "unknown": {
        "reason": "An unexpected storage error occurred",
        "suggestion": "Check server logs for details and contact support if the issue persists."
    }
}

def format_storage_error(error_key, extra_context=None, status_code=500):
    """Build a structured storage error response with reason and actionable suggestion."""
    import os
    mapping = STORAGE_ERROR_MAP.get(error_key, STORAGE_ERROR_MAP["unknown"])
    reason = mapping.get("reason_template", mapping.get("reason", "Unknown error"))
    suggestion = mapping.get("suggestion", "Check server logs for details.")
    
    if extra_context:
        for k, v in extra_context.items():
            placeholder = "{" + k + "}"
            if placeholder in reason:
                reason = reason.replace(placeholder, str(v))
            if placeholder in suggestion:
                suggestion = suggestion.replace(placeholder, str(v))
    
    resp = {
        "success": False,
        "error_code": error_key,
        "reason": reason,
        "suggestion": suggestion,
        "path": extra_context.get("path", "") if extra_context else ""
    }
    if extra_context:
        for k, v in extra_context.items():
            if k not in ["path"]:
                resp[k] = v
    return resp

def is_valid_folder_name(name):
    """Validate folder name against forbidden characters."""
    if not name or not name.strip():
        return False
    forbidden = {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}
    if any(c in name for c in forbidden):
        return False
    if name.strip() in ('.', '..'):
        return False
    return True

def get_company_storage_path(company_id, module_id=None, subfolder=None):
    """
    Build storage path purely based on module_id to maintain module-wise isolation.
    Returns dict: {"success": True/False, "path": "...", ...}
    Path format: data/module_{module_id}/{subfolder}/
    Creates directories on demand.
    """
    import os
    import logging
    logger = logging.getLogger("reconciliation_tool")
    
    try:
        base_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        if module_id is None:
            module_id = 1
            
        path = os.path.join(base_dir, f"module_{module_id}")
        
        if subfolder:
            path = os.path.join(path, subfolder)
        
        # Create directories
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory '{path}': {e}")
            if e.errno == 28:  # No space left
                return format_storage_error("disk_full", {"path": path})
            elif e.errno == 13:  # Permission denied
                return format_storage_error("permission_denied", {"path": path, "os_error": str(e)})
            else:
                return format_storage_error("dir_create_failed", {"path": path, "os_error": str(e)})
        
        return {"success": True, "path": path}
    except Exception as e:
        logger.error(f"get_company_storage_path error: {e}")
        return format_storage_error("unknown", {"detail": str(e)})

def add_notification(company_id: int, module_id: int, notif_type: str, message: str, link: str = None, user_id: int = None, role_id: int = None):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO notifications (company_id, module_id, type, message, link, user_id, role_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (company_id, module_id, notif_type, message, link, user_id, role_id)
            )
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error adding notification: {e}")

def get_recent_notifications(company_id: int, module_id: int, limit: int = 50, user_id: int = None, role_id: int = None):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        try:
            query = "SELECT * FROM notifications WHERE 1=1"
            params = []
            if company_id:
                query += " AND company_id = ?"
                params.append(company_id)
            if module_id:
                query += " AND module_id = ?"
                params.append(module_id)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            else:
                query += " AND user_id IS NULL"
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
        
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return []

def get_company_activity_log(company_id: int, module_id: int = None, user_id: int = None, role_id: int = None, limit: int = 200):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        try:
            query = """
                SELECT n.*, u.name as user_name, u.email as user_email, r.name as role_name, m.name as module_name
                FROM notifications n
                LEFT JOIN users u ON n.user_id = u.id
                LEFT JOIN roles r ON n.role_id = r.id
                LEFT JOIN modules m ON n.module_id = m.id
                WHERE n.company_id = ?
            """
            params = [company_id]
        
            if module_id:
                query += " AND n.module_id = ?"
                params.append(module_id)
            if user_id:
                query += " AND n.user_id = ?"
                params.append(user_id)
            if role_id:
                query += " AND n.role_id = ?"
                params.append(role_id)
            
            query += " ORDER BY n.created_at DESC LIMIT ?"
            params.append(limit)
        
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error getting company activity log: {e}")
        return []

def mark_notification_read(notification_id: int, company_id: int = None, user_id: int = None):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        try:
            # For simplicity, marking it read sets is_read=1. If it's a global notification, it affects everyone.
            if company_id:
                conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND company_id = ?", (notification_id, company_id))
            else:
                conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
            conn.commit()
            return True
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        return False

def mark_all_notifications_read(company_id: int, module_id: int = None, user_id: int = None, role_id: int = None):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        try:
            query = "UPDATE notifications SET is_read = 1 WHERE 1=1"
            params = []
        
            if company_id:
                query += " AND company_id = ?"
                params.append(company_id)
            else:
                query += " AND company_id IS NULL"
            
            if module_id:
                query += " AND module_id = ?"
                params.append(module_id)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            else:
                query += " AND user_id IS NULL"

            conn.execute(query, params)
            conn.commit()
            return True
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error marking all notifications read: {e}")
        return False

def cleanup_old_notifications(days: int = 30):
    import logging
    logger = logging.getLogger("reconciliation_tool")
    try:
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM notifications WHERE created_at < datetime('now', ?)", (f'-{days} days',))
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {e}")

def get_user_folder_path(company_id, module_id, folder_name):
    """
    Get the physical path for a user-created folder within the uploads hierarchy.
    Returns dict: {"success": True/False, "path": "..."}
    Path: {CompanyName_CODE}/{ModuleName}/uploads/{folder_name}/
    """
    import os
    import logging
    logger = logging.getLogger("reconciliation_tool")
    
    # Validate folder name
    if not is_valid_folder_name(folder_name):
        return format_storage_error("invalid_folder_name", {"name": folder_name})
    
    result = get_company_storage_path(company_id, module_id, "uploads_files")
    if not result.get("success"):
        return result
    
    full_path = os.path.join(result["path"], folder_name)
    
    # Check path length
    if len(full_path) > 260:
        return format_storage_error("path_too_long", {"path": full_path})
    
    try:
        os.makedirs(full_path, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create user folder '{full_path}': {e}")
        if e.errno == 28:
            return format_storage_error("disk_full", {"path": full_path})
        elif e.errno == 13:
            return format_storage_error("permission_denied", {"path": full_path, "os_error": str(e)})
        else:
            return format_storage_error("dir_create_failed", {"path": full_path, "os_error": str(e)})
    
    return {"success": True, "path": full_path}

def create_company_file_structure(company_id, module_ids):
    """
    Create the full directory tree for a company's modules AND
    insert Root folder records in the folders database table.
    Returns dict: {"success": True/False, "created": N, "failed": N, "errors": [...]}
    """
    import logging
    logger = logging.getLogger("reconciliation_tool")
    
    subfolders = ["uploads_files", "master_files", "primary_data", "processed"]
    created = 0
    failed = 0
    errors = []
    
    for mid in module_ids:
        for sf in subfolders:
            result = get_company_storage_path(company_id, mid, sf)
            if result.get("success"):
                created += 1
            else:
                failed += 1
                errors.append({
                    "module_id": mid,
                    "subfolder": sf,
                    "error_code": result.get("error_code", "unknown"),
                    "reason": result.get("reason", ""),
                    "suggestion": result.get("suggestion", "")
                })
                logger.warning(f"Folder creation failed: company={company_id}, module={mid}, subfolder={sf}: {result}")
        
        # Auto-create Root folder record in the folders DB table for this module
        # if one doesn't already exist (ensures folder dropdown is populated)
        try:
            conn = get_db_connection()
            try:
                existing = conn.execute(
                    'SELECT id FROM folders WHERE company_id = ? AND module_id = ? AND name = ? AND parent_id IS NULL',
                    (company_id, mid, 'Root')
                ).fetchone()
                if not existing:
                    # Build the display path: /Root
                    display_path = '/Root'
                    cursor = conn.cursor()
                    cursor.execute(
                        'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                        ('Root', company_id, mid, None, None, display_path)
                    )
                    root_id = cursor.lastrowid
                
                    # Insert ONLY the 'Uploads' folder for standard manual file uploads
                    f_path = f"{display_path}/Uploads"
                    cursor.execute(
                        'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                        ('Uploads', company_id, mid, None, root_id, f_path)
                    )
                
                    logger.info(f"Created Root and Uploads folder for company={company_id}, module={mid}")
                conn.commit()
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Failed to create Root folder record for company={company_id}, module={mid}: {e}")
    
    return {
        "success": failed == 0,
        "created": created,
        "failed": failed,
        "errors": errors
    }

def get_physical_storage_path(base_dir, company_id, module_id, folder_id=None):
    """
    Build physical storage path using module-wise isolation.
    """
    import os
    import logging
    logger = logging.getLogger("reconciliation_tool")
    
    # Extract subfolder from base_dir (e.g., 'uploads', 'master_files', 'processed')
    subfolder = os.path.basename(os.path.normpath(base_dir))
    
    result = get_company_storage_path(company_id, module_id, subfolder)
    path = result.get("path") if result.get("success") else base_dir
    
    if folder_id is not None:
        path = os.path.join(path, f"folder_{folder_id}")
    
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        logger.warning(f"get_physical_storage_path: could not create {path}: {e}")
    
    return path


# =================== AUTH / USER FUNCTIONS ===================

def get_super_admin_by_email(email):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM super_admin WHERE LOWER(email) = LOWER(?)', (email,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_user_by_email(email, company_id=None):
    conn = get_db_connection()
    try:
        if company_id:
            row = conn.execute('SELECT * FROM users WHERE LOWER(email) = LOWER(?) AND company_id = ?', (email, company_id)).fetchone()
        else:
            row = conn.execute('SELECT * FROM users WHERE LOWER(email) = LOWER(?)', (email,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_company_by_id(company_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM companies WHERE id = ?', (company_id,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_company_by_code(code):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM companies WHERE LOWER(code) = LOWER(?)', (code,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_company_modules(company_id):
    conn = get_db_connection()
    try:
        rows = conn.execute('''
            SELECT m.* FROM modules m
            JOIN company_modules cm ON m.id = cm.module_id
            WHERE cm.company_id = ? AND cm.status = 'active'
            ORDER BY m.name
        ''', (company_id,)).fetchall()
        return [dict(row) for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_user_assigned_module_ids(user_id):
    conn = get_db_connection()
    try:
        rows = conn.execute('SELECT module_id FROM user_modules WHERE user_id = ?', (user_id,)).fetchall()
        return [row['module_id'] for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_role_by_id(role_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM roles WHERE id = ?', (role_id,)).fetchone()
        if not row:
            return None
        role = dict(row)
        # Parse JSON permissions
        for field in ('page_permissions', 'action_permissions'):
            if role.get(field):
                try:
                    role[field] = json.loads(role[field])
                except (json.JSONDecodeError, TypeError):
                    role[field] = []
            else:
                role[field] = []
        return role


    finally:
        try:
            conn.close()
        except Exception:
            pass
def update_role(role_id, **kwargs):
    if not kwargs:
        return
    
    conn = get_db_connection()
    try:
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = []
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                values.append(json.dumps(v))
            else:
                values.append(v)
        values.append(role_id)
    
        conn.execute(f'UPDATE roles SET {set_clause} WHERE id = ?', values)
        conn.commit()


    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_role(role_id):
    conn = get_db_connection()
    try:
        # Check if any users are using this role
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE role_id = ?", (role_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            return False
        
        conn.execute('DELETE FROM roles WHERE id = ? AND is_default = 0', (role_id,))
        conn.commit()
        return True


    finally:
        try:
            conn.close()
        except Exception:
            pass
def update_last_login(user_id, is_super_admin=False):
    conn = get_db_connection()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if is_super_admin:
            conn.execute('UPDATE super_admin SET last_login = ? WHERE id = ?', (now, user_id))
        else:
            conn.execute('UPDATE users SET last_login = ? WHERE id = ?', (now, user_id))
        conn.commit()


    finally:
        try:
            conn.close()
        except Exception:
            pass
def update_user(user_id, **kwargs):
    if not kwargs:
        return
    allowed = {'name', 'email', 'password_hash', 'role', 'role_id', 'status', 'first_login'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [user_id]
        conn.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
        conn.commit()


    finally:
        try:
            conn.close()
        except Exception:
            pass
def update_super_admin(admin_id, **kwargs):
    if not kwargs:
        return
    allowed = {'name', 'email', 'password_hash', 'status'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [admin_id]
        conn.execute(f'UPDATE super_admin SET {set_clause} WHERE id = ?', values)
        conn.commit()


    finally:
        try:
            conn.close()
        except Exception:
            pass
def save_audit_log(user_id=None, user_role=None, action=None, entity_type=None, entity_id=None, details=None, company_id=None, ip_address=None):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO audit_logs (user_id, user_role, action, entity_type, entity_id, details, company_id, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_role, action, entity_type, entity_id, details, company_id, ip_address))
        conn.commit()


    # =================== COMPANY FUNCTIONS ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_companies(status=None):
    conn = get_db_connection()
    try:
        if status:
            rows = conn.execute('SELECT * FROM companies WHERE status = ? ORDER BY created_at DESC', (status,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM companies ORDER BY created_at DESC').fetchall()
        return [dict(row) for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def create_company(name, code, email=None, phone=None, address=None):
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO companies (name, code, email, phone, address) VALUES (?, ?, ?, ?, ?)',
            (name, code, email, phone, address)
        )
        company_id = cursor.lastrowid
        conn.commit()
        return company_id


    finally:
        try:
            conn.close()
        except Exception:
            pass
def update_company(company_id, **kwargs):
    if not kwargs:
        return
    allowed = {'name', 'code', 'email', 'phone', 'address', 'status'}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    conn = get_db_connection()
    try:
        set_clause = ', '.join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [company_id]
        conn.execute(f'UPDATE companies SET {set_clause} WHERE id = ?', values)
        conn.commit()


    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_company(company_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM companies WHERE id = ?', (company_id,))
        conn.commit()


    # =================== MODULE FUNCTIONS ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_modules():
    conn = get_db_connection()
    try:
        rows = conn.execute('SELECT * FROM modules ORDER BY name').fetchall()
        return [dict(row) for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_module_by_id(module_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM modules WHERE id = ?', (module_id,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_module_by_code(code):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM modules WHERE code = ?', (code,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def assign_module_to_company(company_id, module_id):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT OR IGNORE INTO company_modules (company_id, module_id) VALUES (?, ?)
        ''', (company_id, module_id))
        conn.commit()


    finally:
        try:
            conn.close()
        except Exception:
            pass
def remove_module_from_company(company_id, module_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM company_modules WHERE company_id = ? AND module_id = ?', (company_id, module_id))
        conn.commit()


    # =================== USER MANAGEMENT FUNCTIONS ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_company_users(company_id, status=None):
    conn = get_db_connection()
    try:
        if status:
            rows = conn.execute('SELECT * FROM users WHERE company_id = ? AND status = ? ORDER BY created_at DESC', (company_id, status)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM users WHERE company_id = ? ORDER BY created_at DESC', (company_id,)).fetchall()
        return [dict(row) for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def create_user(email, password_hash, name=None, role='viewer', company_id=None, role_id=None):
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO users (email, password_hash, name, role, company_id, role_id) VALUES (?, ?, ?, ?, ?, ?)',
            (email, password_hash, name, role, company_id, role_id)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id


    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_user(user_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_roles():
    conn = get_db_connection()
    try:
        rows = conn.execute('SELECT * FROM roles ORDER BY name').fetchall()
        roles = []
        for row in rows:
            role = dict(row)
            # Parse JSON permissions
            for field in ('page_permissions', 'action_permissions'):
                if role.get(field):
                    try:
                        role[field] = json.loads(role[field])
                    except (json.JSONDecodeError, TypeError):
                        role[field] = []
                else:
                    role[field] = []
            roles.append(role)
        return roles


    # =================== USER MODULE ASSIGNMENT ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def assign_modules_to_user(user_id, module_ids):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM user_modules WHERE user_id = ?', (user_id,))
        for module_id in module_ids:
            conn.execute('INSERT OR IGNORE INTO user_modules (user_id, module_id) VALUES (?, ?)', (user_id, module_id))
        conn.commit()


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_user_modules(user_id):
    conn = get_db_connection()
    try:
        rows = conn.execute('''
            SELECT m.* FROM modules m
            JOIN user_modules um ON m.id = um.module_id
            WHERE um.user_id = ?
        ''', (user_id,)).fetchall()
        return [dict(row) for row in rows]


    # =================== WEBSITE SETTINGS ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_all_settings():
    conn = get_db_connection()
    try:
        rows = conn.execute('SELECT * FROM website_settings ORDER BY setting_group, setting_key').fetchall()
        return [dict(row) for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def set_setting(key, value, group='general'):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO website_settings (setting_key, setting_value, setting_group)
            VALUES (?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                setting_group = excluded.setting_group,
                updated_at = CURRENT_TIMESTAMP
        ''', (key, value, group))
        conn.commit()


    # =================== AUDIT LOGS ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_audit_logs(limit=100, offset=0, company_id=None):
    conn = get_db_connection()
    try:
        if company_id:
            rows = conn.execute('''
                SELECT * FROM audit_logs WHERE company_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (company_id, limit, offset)).fetchall()
        else:
            rows = conn.execute('''
                SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (limit, offset)).fetchall()
        return [dict(row) for row in rows]


    # =================== RECYCLE BIN ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_recycle_bin_items(company_id=None, module_id=None):
    conn = get_db_connection()
    try:
        if company_id and module_id:
            rows = conn.execute('SELECT * FROM recycle_bin WHERE company_id = ? AND module_id = ? ORDER BY deleted_at DESC', (company_id, module_id)).fetchall()
        elif company_id:
            rows = conn.execute('SELECT * FROM recycle_bin WHERE company_id = ? ORDER BY deleted_at DESC', (company_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM recycle_bin ORDER BY deleted_at DESC').fetchall()
        return [dict(row) for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_recycle_bin_item(recycle_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM recycle_bin WHERE id = ?', (recycle_id,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def restore_from_recycle_bin(recycle_id):
    """Restore an item from recycle bin back to its original state.
    Returns the restored entity info or None if not found."""
    conn = get_db_connection()
    try:
        item = conn.execute('SELECT * FROM recycle_bin WHERE id = ?', (recycle_id,)).fetchone()
        if not item:
            return None
    
        item = dict(item)
        entity_type = item.get('entity_type')
        entity_id = item.get('entity_id')
        entity_name = item.get('entity_name')
        original_path = item.get('original_path')
        metadata = item.get('metadata')
        company_id = item.get('company_id')
        module_id = item.get('module_id')
    
        if metadata:
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
    
        restored = None
    
        if entity_type == 'folder':
            # Re-create folder record
            cursor = conn.execute(
                'INSERT INTO folders (name, company_id, module_id, description, parent_id, path) VALUES (?, ?, ?, ?, ?, ?)',
                (entity_name, company_id, module_id, metadata.get('description'), metadata.get('parent_id'), original_path)
            )
            restored = {'id': cursor.lastrowid, 'name': entity_name, 'type': 'folder'}
        
            # Re-create physical directory if path exists
            if original_path:
                folder_dir = os.path.dirname(original_path)
                os.makedirs(folder_dir, exist_ok=True)
            
        elif entity_type == 'file':
            # Restore the physical file back to the uploads folder
            target_path = original_path
            if original_path and metadata.get('file_path'):
                try:
                    if os.path.exists(original_path):
                        target_path = metadata.get('file_path')
                        import os
                        
                        # Ensure no .deleted. suffix exists (legacy fallback)
                        if '.deleted.' in target_path:
                            target_path = target_path.split('.deleted.')[0]
                            
                        # If the destination already exists (user uploaded a file with same name),
                        # generate a safe, unique filename in the destination directory to prevent overwriting
                        if os.path.exists(target_path):
                            import time
                            base, ext = os.path.splitext(target_path)
                            target_path = f"{base}_restored_{int(time.time())}{ext}"
                            
                        import shutil
                        shutil.move(original_path, target_path)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Could not move restored file back to uploads: {e}")
                    target_path = original_path

            # Re-create file record
            cursor = conn.execute(
                'INSERT INTO files (folder_id, name, original_name, file_path, format, size, sheet_names, company_id, module_id, header_row, uploaded_by, sync_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (metadata.get('folder_id', 1), metadata.get('name', entity_name), entity_name, target_path, metadata.get('format'), 
                 metadata.get('size'), metadata.get('sheet_names'), company_id, module_id, metadata.get('header_row', 1), metadata.get('uploaded_by'), 'pending')
            )
            restored = {'id': cursor.lastrowid, 'name': entity_name, 'type': 'file', 'folder_id': metadata.get('folder_id', 1)}
        
        elif entity_type == 'master_file':
            # Re-create master file record
            cursor = conn.execute(
                'INSERT INTO master_files (folder_id, db_path, sheet_name, columns, header_row, concat_columns, rejected_files, formulas, company_id, module_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (entity_id, original_path, metadata.get('sheet_name'), metadata.get('columns'), 
                 metadata.get('header_row'), metadata.get('concat_columns'), metadata.get('rejected_files'),
                 metadata.get('formulas'), company_id, module_id)
            )
            restored = {'id': cursor.lastrowid, 'name': entity_name, 'type': 'master_file'}
    
        # Remove from recycle bin
        conn.execute('DELETE FROM recycle_bin WHERE id = ?', (recycle_id,))
        conn.commit()
        return restored


    finally:
        try:
            conn.close()
        except Exception:
            pass
def permanent_delete_from_recycle_bin(recycle_id):
    conn = get_db_connection()
    try:
        item = conn.execute('SELECT * FROM recycle_bin WHERE id = ?', (recycle_id,)).fetchone()
        if item:
            item = dict(item)
            # Physically delete the file/folder if it still exists on disk
            entity_type = item.get('entity_type')
            original_path = item.get('original_path')
        
            if original_path:
                if entity_type == 'file' and os.path.isfile(original_path):
                    try:
                        os.remove(original_path)
                    except OSError:
                        pass
                elif entity_type == 'folder' and os.path.isdir(original_path):
                    try:
                        # Only delete if empty
                        if not os.listdir(original_path):
                            os.rmdir(original_path)
                    except OSError:
                        pass
                elif entity_type == 'master_file' and os.path.isfile(original_path):
                    try:
                        os.remove(original_path)
                    except OSError:
                        pass
        
            conn.execute('DELETE FROM recycle_bin WHERE id = ?', (recycle_id,))
        conn.commit()


    # =================== RULE IMPORT/EXPORT ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def export_rules_json(company_id=None, module_id=None):
    conn = get_db_connection()
    try:
        if company_id and module_id:
            rows = conn.execute('SELECT * FROM rules WHERE company_id = ? AND module_id = ? ORDER BY phase', (company_id, module_id)).fetchall()
        elif company_id:
            rows = conn.execute('SELECT * FROM rules WHERE company_id = ? ORDER BY phase', (company_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM rules ORDER BY phase').fetchall()
        return [dict(row) for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def import_rules_from_json(rules_list, company_id=None, module_id=None):
    conn = get_db_connection()
    try:
        imported = 0
        for rule in rules_list:
            conn.execute('''
                INSERT INTO rules (phase, config, name, company_id, module_id, processing_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (rule.get('phase'), json.dumps(rule.get('config')), rule.get('name'), company_id, module_id, rule.get('processing_type', 'both')))
            imported += 1
        conn.commit()
        return imported


    finally:
        try:
            conn.close()
        except Exception:
            pass
def migrate_rules(from_company_id, to_company_id, from_module_id=None, to_module_id=None):
    conn = get_db_connection()
    try:
        if from_module_id:
            rows = conn.execute('SELECT * FROM rules WHERE company_id = ? AND module_id = ?', (from_company_id, from_module_id)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM rules WHERE company_id = ?', (from_company_id,)).fetchall()
        migrated = 0
        for row in rows:
            target_mod = to_module_id if to_module_id else row.get('module_id')
            conn.execute('''
                INSERT INTO rules (phase, config, name, company_id, module_id, processing_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (row['phase'], row['config'], row['name'], to_company_id, target_mod, row.get('processing_type', 'both')))
            migrated += 1
        conn.commit()
        return migrated


    # =================== PROCESSED FILES ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def save_processed_file(filename, file_path, report_type=None, financial_year=None, month_name=None, month_number=None, year=None, source_primary_filename=None, total_rows=None, rules_used=None, sheets_data=None, file_size=None, processing_time=None, company_id=None, module_id=None, validation_id=2):
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO processed_files (filename, file_path, report_type, financial_year, month_name, month_number, year, source_primary_filename, total_rows, rules_used, sheets_data, file_size, processing_time, company_id, module_id, validation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (filename, file_path, report_type, financial_year, month_name, month_number, year, source_primary_filename, total_rows, rules_used, sheets_data, file_size, processing_time, company_id, module_id, validation_id))
        file_id = cursor.lastrowid
        conn.commit()
        return file_id


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_processed_files(company_id=None, module_id=None, financial_year=None, report_type=None, month_name=None, validation_id=None):
    conn = get_db_connection()
    try:
        query = 'SELECT * FROM processed_files WHERE 1=1'
        params = []

        if company_id is not None:
            query += ' AND company_id = ?'
            params.append(company_id)
        if module_id is not None:
            query += ' AND module_id = ?'
            params.append(module_id)
        if financial_year is not None:
            if financial_year == 'Unknown':
                query += ' AND (financial_year IS NULL OR financial_year = ?)'
                params.append('Unknown')
            else:
                query += ' AND financial_year = ?'
                params.append(financial_year)

        if report_type is not None:
            if report_type == 'Unknown':
                query += ' AND (report_type IS NULL OR report_type = ?)'
                params.append('Unknown')
            else:
                query += ' AND report_type = ?'
                params.append(report_type)

        if month_name is not None:
            if month_name == 'Unknown':
                query += ' AND (month_name IS NULL OR month_name = ?)'
                params.append('Unknown')
            else:
                query += ' AND month_name = ?'
                params.append(month_name)
            
        if validation_id is not None:
            query += ' AND validation = ?'
            params.append(validation_id)

        query += ' ORDER BY created_at DESC'

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_processed_file_by_id(file_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM processed_files WHERE id = ?', (file_id,)).fetchone()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_processed_file(file_id):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM processed_files WHERE id = ?', (file_id,)).fetchone()
        conn.execute('DELETE FROM processed_files WHERE id = ?', (file_id,))
        conn.commit()
        return dict(row) if row else None


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_processed_tree(company_id=None, module_id=None):
    """Return processed files grouped by validation, financial_year and month_name for tree view."""
    from datetime import datetime
    
    conn = get_db_connection()
    try:
        query = 'SELECT * FROM processed_files'
        params = []
        if company_id is not None and module_id is not None:
            query += ' WHERE company_id = ? AND module_id = ?'
            params = [company_id, module_id]
        elif company_id is not None:
            query += ' WHERE company_id = ?'
            params = [company_id]
        query += ' ORDER BY validation ASC, year DESC, month_number DESC, created_at DESC'
        rows = conn.execute(query, params).fetchall()

        val_nodes = []
        val_map = {}
    
        for row in rows:
            r = dict(row)
        
            val_id = r.get('validation')
            if val_id == 1:
                val_name = "Validation 1 Report"
            elif val_id == 2:
                val_name = "Validation 2 Report"
            elif val_id == 3:
                val_name = "Validation 3 Report"
            else:
                val_name = f"Validation {val_id} Report" if val_id else "Other Reports"
            
            # Unconditionally derive year and month from the processed Date & Time (created_at)
            created_at_str = r.get('created_at')
            if created_at_str:
                try:
                    # Parse timestamp "YYYY-MM-DD HH:MM:SS"
                    dt = datetime.strptime(created_at_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                    fy = str(dt.year)
                    mn = dt.strftime("%B")
                except Exception:
                    fy = "Unknown"
                    mn = "Unknown"
            else:
                fy = "Unknown"
                mn = "Unknown"

            # 1. Get or create validation node
            if val_name not in val_map:
                val_node = {
                    "validation_name": val_name,
                    "validation_id": val_id,
                    "years": []
                }
                val_nodes.append(val_node)
                val_map[val_name] = (val_node, {})
            
            val_node, fy_map = val_map[val_name]

            # 2. Get or create financial_year node
            if fy not in fy_map:
                fy_node = {
                    "financial_year": fy,
                    "months": []
                }
                val_node["years"].append(fy_node)
                fy_map[fy] = (fy_node, {})
            
            fy_node, mn_map = fy_map[fy]
        
            # 3. Get or create month node
            if mn not in mn_map:
                mn_node = {
                    "month_name": mn,
                    "file_count": 0,
                    "files": []
                }
                fy_node["months"].append(mn_node)
                mn_map[mn] = mn_node
            
            mn_node = mn_map[mn]
            mn_node["file_count"] += 1
            mn_node["files"].append({
                "id": r.get("id"),
                "filename": r.get("filename"),
                "file_path": r.get("file_path"),
                "source_primary_filename": r.get("source_primary_filename"),
                "total_rows": r.get("total_rows"),
                "rules_used": r.get("rules_used"),
                "file_size": r.get("file_size"),
                "processing_time": r.get("processing_time"),
                "created_at": r.get("created_at")
            })
        
        return val_nodes


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_processed_stats(company_id=None, module_id=None):
    """Return processed file statistics."""
    conn = get_db_connection()
    try:
    
        where_clause = ""
        params = []
        if company_id is not None and module_id is not None:
            where_clause = " WHERE company_id = ? AND module_id = ?"
            params = [company_id, module_id]
        elif company_id is not None:
            where_clause = " WHERE company_id = ?"
            params = [company_id]
        
        # Total files
        total_files = conn.execute(f"SELECT COUNT(*) FROM processed_files{where_clause}", params).fetchone()[0]
    
        # Financial years count
        financial_years = conn.execute(f"SELECT COUNT(DISTINCT financial_year) FROM processed_files{where_clause}", params).fetchone()[0]
    
        # Report types count
        report_types = conn.execute(f"SELECT COUNT(DISTINCT report_type) FROM processed_files{where_clause}", params).fetchone()[0]
    
        # Months count
        months = conn.execute(f"SELECT COUNT(DISTINCT(financial_year || '-' || month_name)) FROM processed_files{where_clause}", params).fetchone()[0]
    
    
        return {
            "total_files": total_files,
            "financial_years": financial_years,
            "report_types": report_types,
            "months": months
        }


    # --- AUTO-SYNC HELPER FUNCTIONS ---

    finally:
        try:
            conn.close()
        except Exception:
            pass
def set_file_sync_status(file_id, status, error=None):
    conn = get_db_connection()
    try:
        try:
            conn.execute('UPDATE files SET sync_status = ?, sync_error = ? WHERE id = ?', (status, error, file_id))
            conn.commit()
        finally:
            pass

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_files_with_sync_status(folder_id):
    conn = get_db_connection()
    try:
        try:
            cursor = conn.execute('SELECT id, original_name, sync_status, sync_error FROM files WHERE folder_id = ?', (folder_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            pass


    # =================== MASTER ACTIVITIES (Activity Window) ===================
    # ETL-style persistent transformation steps applied to the master DuckDB table.
    # Activity types: FORMULA_ADD, FORMULA_UPDATE, FIND_REPLACE, COLUMN_RENAME, COLUMN_DELETE.

    finally:
        try:
            conn.close()
        except Exception:
            pass
def list_master_activities(folder_id, company_id=None, module_id=None, enabled_only=False):
    """Return all activities for a master file, ordered by step_order, then id."""
    conn = get_db_connection()
    try:
        try:
            query = "SELECT * FROM master_activities WHERE folder_id = ?"
            params = [folder_id]
            if company_id is not None:
                query += " AND (company_id = ? OR company_id IS NULL)"
                params.append(company_id)
            if module_id is not None:
                query += " AND (module_id = ? OR module_id IS NULL)"
                params.append(module_id)
            if enabled_only:
                query += " AND is_enabled = 1"
            query += " ORDER BY step_order ASC, id ASC"
            rows = conn.execute(query, params).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                # Parse payload_json for convenience
                try:
                    d['payload'] = json.loads(d.get('payload_json') or '{}')
                except (json.JSONDecodeError, TypeError):
                    d['payload'] = {}
                out.append(d)
            return out
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_master_activity(activity_id):
    conn = get_db_connection()
    try:
        try:
            row = conn.execute("SELECT * FROM master_activities WHERE id = ?", (activity_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d['payload'] = json.loads(d.get('payload_json') or '{}')
            except (json.JSONDecodeError, TypeError):
                d['payload'] = {}
            return d
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def create_master_activity(folder_id, activity_type, payload, step_order=None, target_column=None,
                            company_id=None, module_id=None, master_file_id=None, created_by=None):
    """Insert a new activity. payload is a dict that will be JSON-encoded."""
    conn = get_db_connection()
    try:
        try:
            # Auto-assign step_order if not provided: max + 10
            if step_order is None:
                row = conn.execute(
                    "SELECT COALESCE(MAX(step_order), 0) AS m FROM master_activities WHERE folder_id = ?",
                    (folder_id,)
                ).fetchone()
                step_order = (row['m'] if row else 0) + 10
            cur = conn.execute(
                '''INSERT INTO master_activities
                   (master_file_id, folder_id, company_id, module_id, step_order,
                    activity_type, target_column, payload_json, is_enabled, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)''',
                (master_file_id, folder_id, company_id, module_id, step_order,
                 activity_type, target_column, json.dumps(payload) if payload else '{}', created_by)
            )
            activity_id = cur.lastrowid
            conn.commit()
            return activity_id
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def find_activity_for_action(folder_id, action_type, target_column=None, payload_signature=None):
    """
    Find an existing activity that matches a user action. Used for dedup when the
    user applies the same formula/find-replace twice.

    Matching rules:
      - COLUMN_RENAME / COLUMN_DELETE: match by (activity_type, target_column)
      - FIND_REPLACE:                   match by (activity_type, payload signature)
      - FORMULA_ADD:                    match by (activity_type, target_column)
      - ROW_FILTER:                     match by (activity_type, payload signature)

    Returns the activity dict (with parsed payload) or None.
    """
    conn = get_db_connection()
    try:
        try:
            if target_column is not None:
                row = conn.execute(
                    """SELECT * FROM master_activities
                       WHERE folder_id = ? AND activity_type = ?
                         AND target_column = ? AND is_enabled = 1
                       ORDER BY id ASC LIMIT 1""",
                    (folder_id, action_type, target_column)
                ).fetchone()
            elif payload_signature is not None:
                # Use a LIKE on the JSON to find by signature
                row = conn.execute(
                    """SELECT * FROM master_activities
                       WHERE folder_id = ? AND activity_type = ? AND is_enabled = 1
                         AND payload_json LIKE ?
                       ORDER BY id ASC LIMIT 1""",
                    (folder_id, action_type, f'%{payload_signature}%')
                ).fetchone()
            else:
                return None
            if not row:
                return None
            d = dict(row)
            try:
                d['payload'] = json.loads(d.get('payload_json') or '{}')
            except (json.JSONDecodeError, TypeError):
                d['payload'] = {}
            return d
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def create_activity_from_action(folder_id, action_type, payload, target_column=None,
                                 company_id=None, module_id=None, master_file_id=None,
                                 user_id=None, dedup=True):
    """
    Auto-capture a user action as an Activity step. This is the SINGLE entry point
    called by every apply endpoint (formula, find-replace, delete-column, rename, filter).

    Behaviour:
      - If `dedup=True` and an existing enabled activity matches this action
        (by target_column or payload signature), UPDATE the existing activity's
        payload in place and return its id. This prevents duplicates when the
        user re-applies the same transformation.
      - Otherwise, INSERT a new activity with auto-assigned step_order.

    Returns dict: { activity_id, deduplicated: bool }
    """
    import logging
    logger = logging.getLogger("reconciliation_tool")
    if payload is None:
        payload = {}

    # Derive a stable signature for payload-based matching (FIND_REPLACE, ROW_FILTER)
    sig = None
    if action_type in ('FIND_REPLACE', 'ROW_FILTER'):
        # Use the user-facing inputs as the signature
        if action_type == 'FIND_REPLACE':
            sig = f'"find": {json.dumps(payload.get("find", ""))!r}'
        elif action_type == 'ROW_FILTER':
            sig = f'"filter": {json.dumps(payload, sort_keys=True)!r}'

    existing = None
    if dedup:
        try:
            existing = find_activity_for_action(
                folder_id, action_type,
                target_column=target_column,
                payload_signature=sig
            )
        except Exception as e:
            logger.warning(f"dedup lookup failed: {e}")

    if existing:
        # Update payload in place
        update_master_activity(existing['id'], payload=payload)
        return {"activity_id": existing['id'], "deduplicated": True}

    # No match — create new
    try:
        activity_id = create_master_activity(
            folder_id=folder_id,
            activity_type=action_type,
            payload=payload,
            target_column=target_column,
            company_id=company_id,
            module_id=module_id,
            master_file_id=master_file_id,
            created_by=user_id,
        )
        return {"activity_id": activity_id, "deduplicated": False}
    except Exception as e:
        logger.error(f"create_activity_from_action failed: {e}")
        return {"activity_id": None, "deduplicated": False, "error": str(e)}


def update_master_activity(activity_id, **kwargs):
    """Update an activity. Allowed: payload, step_order, is_enabled, target_column, validation_status, last_error, last_applied_at."""
    allowed = {'payload', 'step_order', 'is_enabled', 'target_column',
               'validation_status', 'last_error', 'last_applied_at'}
    fields = {}
    for k, v in kwargs.items():
        if k not in allowed:
            continue
        if k == 'payload' and not isinstance(v, str):
            fields['payload_json'] = json.dumps(v) if v else '{}'
        else:
            fields[k] = v
    if not fields:
        return
    conn = get_db_connection()
    try:
        try:
            set_clause = ', '.join(f"{k} = ?" for k in fields.keys())
            values = list(fields.values()) + [activity_id]
            conn.execute(f"UPDATE master_activities SET {set_clause} WHERE id = ?", values)
            conn.commit()
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def delete_master_activity(activity_id):
    conn = get_db_connection()
    try:
        try:
            conn.execute("DELETE FROM master_activities WHERE id = ?", (activity_id,))
            conn.commit()
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def reorder_master_activities(folder_id, ordered_ids):
    """Bulk update step_order for the given list of activity IDs (in order)."""
    conn = get_db_connection()
    try:
        try:
            for idx, aid in enumerate(ordered_ids):
                new_order = (idx + 1) * 10
                conn.execute(
                    "UPDATE master_activities SET step_order = ? WHERE id = ? AND folder_id = ?",
                    (new_order, aid, folder_id)
                )
            conn.commit()
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def mark_activity_applied(activity_id, status='ok', error=None):
    """Update last_applied_at + validation_status + last_error after auto-sync."""
    from datetime import datetime
    conn = get_db_connection()
    try:
        try:
            conn.execute(
                "UPDATE master_activities SET last_applied_at = ?, validation_status = ?, last_error = ? WHERE id = ?",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), status, error, activity_id)
            )
            conn.commit()
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def activity_already_migrated(activity_id_legacy):
    """Check whether a legacy master_formulas entry has already been migrated to master_activities.
    Used by the one-time migration to avoid duplicates."""
    conn = get_db_connection()
    try:
        try:
            row = conn.execute(
                "SELECT 1 FROM master_activities WHERE payload_json LIKE ? LIMIT 1",
                (f'%"legacy_formula_id": {int(activity_id_legacy)}%',)
            ).fetchone()
            return row is not None
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def migrate_legacy_master_formulas():
    """One-time migration: copy each row's master_files.formulas JSON entries into
    master_activities so they are re-applied by the new apply_activities() engine.
    Idempotent: skips entries that have already been migrated.

    Returns dict: {migrated_count, skipped_count, folders_scanned}
    """
    import logging
    logger = logging.getLogger("reconciliation_tool")
    migrated = 0
    skipped = 0
    folders_scanned = 0

    conn = get_db_connection()
    try:
        try:
            # Iterate over every master_files row
            masters = conn.execute("SELECT id, folder_id, company_id, module_id, formulas FROM master_files").fetchall()
            for m in masters:
                folders_scanned += 1
                master_id = m['id']
                folder_id = m['folder_id']
                company_id = m['company_id']
                module_id = m['module_id']
                formulas_json = m['formulas']
                if not formulas_json:
                    continue
                try:
                    formulas_list = json.loads(formulas_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(formulas_list, list):
                    continue

                for idx, f in enumerate(formulas_list):
                    if not isinstance(f, dict):
                        continue
                    # Skip if we've already migrated this exact entry
                    legacy_id = f.get('id')
                    if legacy_id is not None and activity_already_migrated(legacy_id):
                        skipped += 1
                        continue

                    ft = (f.get('formula_type') or f.get('type') or 'EXPRESSION').upper()
                    target_column = f.get('column_name') or f.get('output_column') or f.get('target_column')

                    if ft in ('FORMULA_ADD', 'EXPRESSION', 'SUMIF', 'COUNTIF', 'VLOOKUP'):
                        activity_type = 'FORMULA_ADD'
                        payload = {
                            'expression': f.get('expression') or f.get('formula') or '',
                            'output_column': target_column,
                            'data_type': f.get('data_type', 'DOUBLE'),
                            # Preserve original fields so reapply_formulas() can still work
                            'formula_type': ft,
                            'primary_column': f.get('primary_column'),
                            'secondary_file': f.get('secondary_file'),
                            'secondary_sheet': f.get('secondary_sheet'),
                            'secondary_match_column': f.get('secondary_match_column'),
                            'secondary_value_column': f.get('secondary_value_column'),
                            'legacy_formula_id': legacy_id,
                        }
                    else:
                        activity_type = 'FORMULA_ADD'
                        payload = {
                            'expression': json.dumps(f),
                            'output_column': target_column,
                            'data_type': 'DOUBLE',
                            'formula_type': ft,
                            'legacy_formula_id': legacy_id,
                        }

                    # step_order: keep relative ordering, multiply by 10 to leave room
                    step_order = (idx + 1) * 10
                    try:
                        create_master_activity(
                            folder_id=folder_id,
                            activity_type=activity_type,
                            payload=payload,
                            step_order=step_order,
                            target_column=target_column,
                            company_id=company_id,
                            module_id=module_id,
                            master_file_id=master_id,
                        )
                        migrated += 1
                    except Exception as e:
                        logger.warning(f"Migration: failed to migrate formula for folder={folder_id}: {e}")
                        skipped += 1
        finally:
            pass

        if migrated:
            logger.info(f"Legacy migration: migrated {migrated} formulas to master_activities (skipped {skipped})")
        return {"migrated": migrated, "skipped": skipped, "folders_scanned": folders_scanned}


    finally:
        try:
            conn.close()
        except Exception:
            pass
def clone_company_module(source_company_id: int, target_company_id: int, module_id: int):
    """
    Clones all configuration (folders, rules, master files, activities) from a source 
    company to a target company for a specific module.
    """
    import logging
    import uuid
    import shutil
    import os
    import json
    
    conn = get_db_connection()
    try:
        try:
            # 1. Clone Folders
            folder_map = {} # old_id -> new_id
            old_folders = conn.execute(
                "SELECT * FROM folders WHERE company_id = ? AND module_id = ? ORDER BY id ASC", 
                (source_company_id, module_id)
            ).fetchall()
        
            folder_map = {} # old_id -> new_id
            for f in old_folders:
                old_id = f['id']
                new_parent_id = folder_map.get(f['parent_id']) if f['parent_id'] else None
            
                # Generate correct new physical path for the new company
                path_result = get_user_folder_path(target_company_id, module_id, f['name'])
                new_path = path_result['path'] if path_result.get('success') else None
            
                # Ensure the physical directory is actually created
                if new_path:
                    try:
                        os.makedirs(new_path, exist_ok=True)
                    except Exception as e:
                        logging.getLogger("reconciliation_tool").error(f"Failed to create directory {new_path}: {e}")
            
                cursor = conn.execute(
                    """INSERT INTO folders (company_id, module_id, name, description, parent_id, path)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (target_company_id, module_id, f['name'], f['description'], new_parent_id, new_path)
                )
                folder_map[old_id] = cursor.lastrowid
            
            # 2. Clone Master Files (to get master_file_map first)
            master_file_map = {} # old_id -> new_id
            old_master_files = conn.execute(
                "SELECT * FROM master_files WHERE company_id = ? AND module_id = ?",
                (source_company_id, module_id)
            ).fetchall()
        
            for mf in old_master_files:
                old_mf_id = mf['id']
                if mf['folder_id'] not in folder_map:
                    continue
                
                new_db_path = f"data/master_dbs/folder_{folder_map[mf['folder_id']]}_{uuid.uuid4().hex[:8]}.duckdb"
            
                # Copy DuckDB file schema and 10 rows using DuckDB
                if os.path.exists(mf['db_path']):
                    os.makedirs(os.path.dirname(new_db_path), exist_ok=True)
                    import duckdb
                    try:
                        # Connect to new database, attach old one, and copy max 10 rows
                        new_con = duckdb.connect(new_db_path)
                        new_con.execute(f"ATTACH '{mf['db_path']}' AS old_db (READ_ONLY)")
                    
                        # Check if master_data table exists by trying to copy it
                        try:
                            new_con.execute("CREATE TABLE master_data AS SELECT * FROM old_db.main.master_data LIMIT 10")
                        except duckdb.CatalogException:
                            pass # old_db does not have master_data
                    
                        new_con.execute("DETACH old_db")
                        new_con.close()
                    except Exception as e:
                        logger.error(f"Failed to selectively clone DuckDB for {mf['db_path']}: {e}")
                        # Fallback to empty if it fails
            
                cursor = conn.execute(
                    """INSERT INTO master_files (company_id, module_id, folder_id, db_path, sheet_name, columns, header_row, concat_columns, rejected_files, formulas, auto_sync)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (target_company_id, module_id, folder_map[mf['folder_id']], new_db_path, mf['sheet_name'], mf['columns'], mf['header_row'], mf['concat_columns'], mf['rejected_files'], mf['formulas'], mf['auto_sync'])
                )
                master_file_map[old_mf_id] = cursor.lastrowid
            
                # Clone master_file_configs if exists
                old_config = conn.execute("SELECT * FROM master_file_configs WHERE folder_id = ?", (mf['folder_id'],)).fetchone()
                if old_config:
                    conn.execute(
                        """INSERT INTO master_file_configs (folder_id, columns, concat_columns, sheet_name, header_row)
                           VALUES (?, ?, ?, ?, ?)""",
                        (folder_map[mf['folder_id']], old_config['columns'], old_config['concat_columns'], old_config['sheet_name'], old_config['header_row'])
                    )
            
            def remap_json_ids(obj):
                if isinstance(obj, dict):
                    new_obj = {}
                    for k, v in obj.items():
                        if k in ['secondary_file', 'extract_file', 'primary_file', 'file_id'] and isinstance(v, str):
                            # If it's a bare number, it's a folder ID
                            if v.isdigit():
                                new_obj[k] = str(folder_map.get(int(v), v))
                            # If it starts with 'master_', the number after it is ALSO a folder ID!
                            elif v.startswith('master_'):
                                old_id_str = v.replace('master_', '')
                                if old_id_str.isdigit():
                                    new_obj[k] = f"master_{folder_map.get(int(old_id_str), old_id_str)}"
                                else:
                                    new_obj[k] = v
                            else:
                                new_obj[k] = v
                        elif isinstance(v, list) or isinstance(v, dict):
                            new_obj[k] = remap_json_ids(v)
                        else:
                            new_obj[k] = v
                    return new_obj
                elif isinstance(obj, list):
                    return [remap_json_ids(item) for item in obj]
                else:
                    return obj

            # 3. Clone Rules
            old_rules = conn.execute(
                "SELECT * FROM rules WHERE company_id = ? AND module_id = ?",
                (source_company_id, module_id)
            ).fetchall()
        
            for r in old_rules:
                config_str = r['config']
                try:
                    if config_str:
                        config_data = json.loads(config_str)
                        config_data = remap_json_ids(config_data)
                        config_str = json.dumps(config_data)
                except Exception:
                    pass # If it fails to parse, just use original
                
                conn.execute(
                    """INSERT INTO rules (company_id, module_id, name, phase, config, processing_type)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (target_company_id, module_id, r['name'], r['phase'], config_str, r['processing_type'])
                )
            
            # 4. Clone Master Activities
            old_activities = conn.execute(
                "SELECT * FROM master_activities WHERE company_id = ? AND module_id = ?",
                (source_company_id, module_id)
            ).fetchall()
        
            for act in old_activities:
                new_folder_id = folder_map.get(act['folder_id'])
                new_mf_id = master_file_map.get(act['master_file_id']) if act['master_file_id'] else None
            
                if not new_folder_id:
                    continue
                
                payload_str = act['payload_json']
                try:
                    if payload_str:
                        payload_data = json.loads(payload_str)
                        payload_data = remap_json_ids(payload_data)
                        payload_str = json.dumps(payload_data)
                except Exception:
                    pass
                
                conn.execute(
                    """INSERT INTO master_activities (master_file_id, folder_id, company_id, module_id, step_order, activity_type, target_column, payload_json, is_enabled)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (new_mf_id, new_folder_id, target_company_id, module_id, act['step_order'], act['activity_type'], act['target_column'], payload_str, act['is_enabled'])
                )

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            import logging
            logging.getLogger("reconciliation_tool").error(f"Error cloning module {module_id} from {source_company_id} to {target_company_id}: {e}")
            raise e
        finally:
            pass



    finally:
        try:
            conn.close()
        except Exception:
            pass
def set_module_template(module_id: int, template_company_id: int):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE modules SET template_company_id = ? WHERE id = ?', (template_company_id, module_id))
        conn.commit()


    # =================== DEDUP / DUPLICATE DETECTION (CONCAT) ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_dedup_config(folder_id):
    """
    Returns the persisted dedup config for a folder, or None if not configured.
    The dedup config is stored on master_file_configs.dedup_*.
    """
    conn = get_db_connection()
    try:
        try:
            row = conn.execute(
                "SELECT dedup_enabled, dedup_columns, dedup_separator "
                "FROM master_file_configs WHERE folder_id = ?",
                (folder_id,),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            cols_raw = d.get('dedup_columns')
            if cols_raw:
                try:
                    d['dedup_columns_list'] = json.loads(cols_raw)
                except (json.JSONDecodeError, TypeError):
                    d['dedup_columns_list'] = []
            else:
                d['dedup_columns_list'] = []
            d['dedup_enabled']  = bool(d.get('dedup_enabled') or 0)
            d['dedup_separator'] = d.get('dedup_separator') or ' | '
            return d
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def save_dedup_config(folder_id, enabled, columns, separator=' | '):
    """
    Persist the dedup config on master_file_configs.dedup_*.
    - columns may be a list or JSON string.
    - Creates the master_file_configs row if it doesn't exist (saving only
      the dedup fields; the other columns are filled with NULL and remain
      to be set when the master file is actually built).
    """
    if isinstance(columns, list):
        cols_json = json.dumps(columns)
    else:
        cols_json = columns or '[]'

    conn = get_db_connection()
    try:
        try:
            existing = conn.execute(
                "SELECT id FROM master_file_configs WHERE folder_id = ?",
                (folder_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE master_file_configs
                       SET dedup_enabled   = ?,
                           dedup_columns   = ?,
                           dedup_separator = ?,
                           updated_at      = CURRENT_TIMESTAMP
                     WHERE folder_id = ?
                    """,
                    (1 if enabled else 0, cols_json, separator, folder_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO master_file_configs
                        (folder_id, dedup_enabled, dedup_columns, dedup_separator, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (folder_id, 1 if enabled else 0, cols_json, separator),
                )
            conn.commit()
        finally:
            pass


    # =================== REJECTED ARTEFACTS ===================

    finally:
        try:
            conn.close()
        except Exception:
            pass
def save_rejected_artefact(folder_id, file_id, original_name, artefact_path,
                           reject_reason, rejected_rows, total_rows, source='merge'):
    """
    Persist a downloadable reject report (the full file + Status / Reject_Reason
    columns) for a file that was rejected by the dedup engine.
    Returns the new artefact's id.

    NOTE: `created_at` is explicitly set to IST (UTC+5:30) instead of relying
    on SQLite's `CURRENT_TIMESTAMP` default, so the rejected files table
    shows IST-correct timestamps regardless of the host server's TZ setting.
    """
    conn = get_db_connection()
    try:
        try:
            cur = conn.execute(
                """
                INSERT INTO rejected_artefacts
                    (folder_id, file_id, original_name, artefact_path,
                     reject_reason, rejected_rows, total_rows, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (folder_id, file_id, original_name, artefact_path,
                 reject_reason, rejected_rows, total_rows, source,
                 _ist_now_str()),
            )
            artefact_id = cur.lastrowid
            conn.commit()
            return artefact_id
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def list_rejected_artefacts(folder_id, file_id=None):
    """
    List reject reports for a folder (optionally for a specific file). Each row
    is decorated with `download_url` so the frontend can render a direct link.
    """
    conn = get_db_connection()
    try:
        try:
            if file_id is not None:
                rows = conn.execute(
                    """SELECT * FROM rejected_artefacts
                       WHERE folder_id = ? AND file_id = ?
                       ORDER BY created_at DESC""",
                    (folder_id, file_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM rejected_artefacts
                       WHERE folder_id = ?
                       ORDER BY created_at DESC""",
                    (folder_id,),
                ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d['download_url'] = f"/api/files/{d['file_id']}/rejected-download" if d.get('file_id') else None
                out.append(d)
            return out
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_latest_rejected_artefact_for_file(file_id):
    """
    Return the most recent reject artefact row for a file, or None.
    Used by the file-list endpoint to surface `rejected_artefact_id`,
    `rejected_artefact_rows`, `rejected_artefact_total` so the UI can show
    the 'Rejected & Download' pill.
    """
    conn = get_db_connection()
    try:
        try:
            row = conn.execute(
                """SELECT * FROM rejected_artefacts
                    WHERE file_id = ?
                    ORDER BY created_at DESC LIMIT 1""",
                (file_id,),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d['download_url'] = f"/api/files/{d['file_id']}/rejected-download"
            return d
        finally:
            pass


    finally:
        try:
            conn.close()
        except Exception:
            pass
def get_rejected_artefact_by_id(artefact_id):
    conn = get_db_connection()
    try:
        try:
            row = conn.execute(
                "SELECT * FROM rejected_artefacts WHERE id = ?",
                (artefact_id,),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d['download_url'] = f"/api/files/{d['file_id']}/rejected-download"
            return d
        finally:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
