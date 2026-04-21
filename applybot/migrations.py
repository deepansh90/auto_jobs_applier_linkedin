import os
import shutil

def migrate_legacy_directories():
    """
    Migrates the upstream legacy 'all excels/' directory to 'history/',
    renaming the CSV files logically so as to avoid silently breaking old user data.
    """
    legacy_path = "all excels"
    new_path = "history"

    if os.path.exists(legacy_path) and os.path.isdir(legacy_path):
        os.makedirs(new_path, exist_ok=True)
        
        legacy_applied = os.path.join(legacy_path, "all_applied_applications_history.csv")
        new_applied = os.path.join(new_path, "applications.csv")
        if os.path.exists(legacy_applied) and not os.path.exists(new_applied):
            shutil.move(legacy_applied, new_applied)

        legacy_failed = os.path.join(legacy_path, "all_failed_applications_history.csv")
        new_failed = os.path.join(new_path, "failures.csv")
        if os.path.exists(legacy_failed) and not os.path.exists(new_failed):
            shutil.move(legacy_failed, new_failed)
            
        print(f"[applybot.migrations] Extracted legacy data to '{new_path}/'")
        
        # Clean up legacy dir safely if empty
        try:
            if not os.listdir(legacy_path):
                os.rmdir(legacy_path)
        except OSError:
            pass
