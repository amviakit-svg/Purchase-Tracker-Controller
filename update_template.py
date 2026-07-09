import os
import shutil
import sqlite3
import sys

def main():
    metadata_path = os.path.join('data', 'metadata.db')
    template_path = 'deploy_template.db'
    
    if not os.path.exists(metadata_path):
        print(f"Error: {metadata_path} not found. Cannot update template.")
        sys.exit(1)
        
    print(f"Copying {metadata_path} to {template_path}...")
    shutil.copy2(metadata_path, template_path)
    
    print("Scrubbing sensitive client data from template...")
    try:
        conn = sqlite3.connect(template_path)
        cursor = conn.cursor()
        
        # Tables to completely clear
        sensitive_tables = [
            'files', 
            'processed_files', 
            'rejected_artefacts', 
            'audit_logs', 
            'notifications', 
            'recycle_bin'
        ]
        
        for table in sensitive_tables:
            try:
                cursor.execute(f"DELETE FROM {table};")
                print(f" - Cleared {table}")
            except sqlite3.OperationalError as e:
                print(f" - Skipped {table} (not found or error: {e})")
                
        # Note: Deliberately preserving template_company_id as requested
        # so that all module configurations remain intact for the new system.

            
        # Commit all deletions before running VACUUM
        conn.commit()

        # Scrub DuckDB master files
        print("\nScrubbing DuckDB master files (preserving 4 sample rows)...")
        try:
            import duckdb
            cursor.execute("SELECT module_id, folder_id FROM master_files")
            for row in cursor.fetchall():
                mod_id, fol_id = row
                duck_path = os.path.join('data', f'module_{mod_id}', 'master_files', f'folder_{fol_id}', f'folder_{fol_id}_master.duckdb')
                if os.path.exists(duck_path):
                    try:
                        dconn = duckdb.connect(duck_path)
                        # Check if table exists
                        tables = dconn.execute("SHOW TABLES").fetchall()
                        if ('master_data',) in tables:
                            # Keep 4 rows
                            dconn.execute("DELETE FROM master_data WHERE rowid NOT IN (SELECT rowid FROM master_data LIMIT 4)")
                            print(f" - Scrubbed {duck_path} (kept 4 rows)")
                        dconn.close()
                    except Exception as e:
                        print(f" - Failed to scrub {duck_path}: {e}")
        except ImportError:
            print(" - DuckDB not installed. Skipping DuckDB scrub.")
        
        # Shrink the database file after deletions
        cursor.execute("VACUUM;")
        
        conn.close()
        print("\nTemplate successfully updated and scrubbed!")
        
    except Exception as e:
        print(f"Error during database scrub: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
