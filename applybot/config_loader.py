import json
import os
import sys

def apply_user_overlay():
    """
    Safely loads config/user.settings.json and overlays its values 
    onto the existing Python config modules.
    This replaces the brittle regex-rewriting pattern previously used.
    """
    settings_path = os.path.join("config", "user.settings.json")
    if not os.path.exists(settings_path):
        return

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[applybot.config_loader] Error loading {settings_path}: {e}")
        return

    # Map the JSON keys to their respective module targets
    # Example mapping schema:
    # "search_terms" -> "config.search", "search_terms"
    
    # Pre-import targeted modules to ensure they are available in sys.modules
    import config.search
    import config.settings
    import config.secrets
    try:
        import config.personals
    except ImportError:
        pass

    target_map = {
        "search_terms": "config.search",
        "search_location": "config.search",
        "job_type": "config.search",
        "on_site": "config.search",
        "experience_level": "config.search",
        "default_resume_path": "config.settings",
    }

    # Additionally, we can map things dynamically or statically.
    for key, val in data.items():
        target_mod = target_map.get(key)
        if target_mod and target_mod in sys.modules:
            setattr(sys.modules[target_mod], key, val)
        else:
            # Fallback if there are personals or generic settings
            if "config.personals" in sys.modules and hasattr(sys.modules["config.personals"], key):
                setattr(sys.modules["config.personals"], key, val)
            elif hasattr(sys.modules["config.settings"], key):
                setattr(sys.modules["config.settings"], key, val)

    print("[applybot.config_loader] Successfully loaded user.settings.json overlay")
