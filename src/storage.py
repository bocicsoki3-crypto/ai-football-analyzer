import json
import os
import uuid

DATA_FILE = "data/saved_tips.json"

def load_tips():
    """Loads tips from the JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_tip(tip_data):
    """Saves a single tip or list of tips to the JSON file."""
    tips = load_tips()
    
    # Ensure tip_data is a list
    if not isinstance(tip_data, list):
        new_tips = [tip_data]
    else:
        new_tips = tip_data
        
    # Ensure directory exists
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
    # Add UUID and default status if missing
    for tip in new_tips:
        if "id" not in tip:
            tip["id"] = str(uuid.uuid4())
        if "status" not in tip:
            tip["status"] = "pending"
            
    tips.extend(new_tips)
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tips, f, indent=4, ensure_ascii=False)

def update_tip_status(tip_id, new_status):
    """Updates the status of a tip (won/lost/pending)."""
    tips = load_tips()
    updated = False
    for tip in tips:
        if tip["id"] == tip_id:
            tip["status"] = new_status
            updated = True
            break
            
    if updated:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tips, f, indent=4, ensure_ascii=False)
    return updated

def delete_tip(tip_id):
    """Deletes a tip by ID."""
    tips = load_tips()
    tips = [t for t in tips if t["id"] != tip_id]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tips, f, indent=4, ensure_ascii=False)
