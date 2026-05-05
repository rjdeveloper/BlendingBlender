import json
import datetime
import os

LOG_FILE = "c:/blundai/audit_log.json"

def log_audit(action, details):
    """Log an action to the audit file with a timestamp."""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action": action,
        "details": details
    }
    
    # Create file if not exists
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)
            
    # Append to log
    try:
        with open(LOG_FILE, "r+") as f:
            data = json.load(f)
            data.append(log_entry)
            f.seek(0)
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Logging failed: {e}")

def natural_error_response(error_str, mode='cnc'):
    """Convert technical errors into natural, professional responses."""
    if mode == 'director':
        if "context is incorrect" in error_str.lower():
            return "The scene context wasn't ready for that take. I'm resetting the stage and trying the animation again."
        if "operator" in error_str.lower():
            return "That specific motion script failed. I'm rewriting the keyframe logic to get a smoother result."
        if "not found" in error_str.lower():
            return "I couldn't find the character or prop in the scene. Checking the hierarchy now."
        return f"Director's Note: {error_str}. I'm adjusting the script."
    else:
        if "context is incorrect" in error_str.lower():
            return "I tried to edit the part while it was in the wrong mode. I've switched to the correct view and am trying again."
        if "operator" in error_str.lower():
            return "The tool I used wasn't quite right for this material. Let me adjust my approach."
        if "not found" in error_str.lower():
            return "I couldn't find the object you're referring to. Let me scan the scene again to make sure I have the right part."
        return f"I hit a small snag: {error_str}. I'm adjusting my plan to fix this."
