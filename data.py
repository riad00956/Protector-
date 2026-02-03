import json
import time
import os

DB_FILE = "db.json"

# Load DB
def load_db():
    if not os.path.exists(DB_FILE):
        return {"admins": [], "targets": [], "maintenance": None, "permissions": {}}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"admins": [], "targets": [], "maintenance": None, "permissions": {}}

# Save DB
def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

# Check Admin
def is_admin(user_id, db):
    return user_id in db.get("admins", [])

# Save target chat
def save_target(chat_id, db):
    if chat_id not in db["targets"]:
        db["targets"].append(chat_id)
        save_db(db)

# Maintenance status
def is_maintenance(db):
    m = db.get("maintenance")
    if m and time.time() < m:
        return True
    return False

def set_maintenance(minutes, db):
    db["maintenance"] = time.time() + minutes*60
    save_db(db)

def stop_maintenance(db):
    db["maintenance"] = None
    save_db(db)
