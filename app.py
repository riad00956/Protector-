import asyncio
import json
import re
import time
from aiohttp import web, ClientSession
from data import load_db, save_db, is_admin, save_target, is_maintenance, set_maintenance, stop_maintenance

TOKEN = ""
SUPER_ADM8000160699:AAF5ifoKw13-NgtuKzy00Yo9Zg18KgkI5tIIN = 7832264582
API = f"https://api.telegram.org/bot{TOKEN}"

# Inline Admin Panel settings
ADMIN_PANEL_CHAT_ID = -1001234567890  # যেই গ্রুপে admin panel চালাবে

# ================== TG REQUEST ==================
async def tg(method, data):
    async with ClientSession() as session:
        async with session.post(f"{API}/{method}", json=data) as r:
            try:
                return await r.json()
            except:
                return {}

# ================== LINK DETECTION ==================
def has_link(text, entities):
    if not text:
        return False
    if re.search(r"(https?://|www\.|t\.me/|[a-z0-9-]+\.[a-z]{2,})", text, re.I):
        return True
    if entities:
        for e in entities:
            if e.get("type") in ["url", "text_link"]:
                return True
    return False

# ================== MESSAGE HANDLER ==================
async def handle_message(msg):
    db = load_db()
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text","") or msg.get("caption","")
    is_group = msg["chat"]["type"] != "private"

    # Maintenance Silent
    if is_maintenance(db) and user_id != SUPER_ADMIN:
        return  # completely silent

    save_target(chat_id, db)

    # Start message
    if text == "/start":
        await tg("sendMessage", {"chat_id": chat_id, "text": "বট অন হয়েছে।"})
        return

    # Super Admin only
    if user_id == SUPER_ADMIN and chat_id == ADMIN_PANEL_CHAT_ID:
        await handle_admin_panel(text, chat_id, db)
        return

    # Admin Inline Panel trigger
    if text == "/admin" and is_admin(user_id, db) and chat_id == ADMIN_PANEL_CHAT_ID:
        await send_admin_panel(chat_id)
        return

    # Link delete in group
    if is_group and has_link(text, msg.get("entities")) and not is_admin(user_id, db):
        try:
            await tg("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
            await tg("sendMessage", {"chat_id": chat_id,
                "text": f"🚫 {msg['from']['first_name']}, লিংক দেয়া যাবে না!"})
        except:
            pass

# ================== ADMIN PANEL ==================
async def send_admin_panel(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text":"➕ Add Admin","callback_data":"add_admin"}],
            [{"text":"➖ Remove Admin","callback_data":"remove_admin"}],
            [{"text":"📋 Admin List","callback_data":"admin_list"}],
            [{"text":"🛠 Maintenance ON","callback_data":"maintenance_on"}],
            [{"text":"✅ Maintenance OFF","callback_data":"maintenance_off"}],
            [{"text":"📢 Broadcast","callback_data":"broadcast"}],
            [{"text":"🛑 Stop Bot","callback_data":"stop_bot"}]
        ]
    }
    await tg("sendMessage", {"chat_id": chat_id, "text":"Admin Panel", "reply_markup": keyboard})

async def handle_admin_panel(text, chat_id, db):
    if text.startswith("/m on"):
        try:
            minutes = int(text.split(" ")[2])
        except:
            minutes = 60
        set_maintenance(minutes, db)
        await tg("sendMessage", {"chat_id": chat_id, "text": f"🛠 Maintenance ON {minutes} min"})
    elif text == "/m off":
        stop_maintenance(db)
        await tg("sendMessage", {"chat_id": chat_id, "text":"✅ Maintenance OFF"})
    elif text.startswith("/bc"):
        bc_text = text.replace("/bc","").strip()
        if bc_text:
            count = 0
            for cid in db.get("targets",[]):
                r = await tg("sendMessage", {"chat_id": cid, "text": f"📢 Broadcast:\n\n{bc_text}"})
                if r.get("ok"):
                    count += 1
            await tg("sendMessage", {"chat_id": chat_id, "text": f"✅ Broadcast sent to {count} chats"})
    elif text == "/stop":
        await tg("sendMessage", {"chat_id": chat_id, "text":"Bot stopped by Super Admin"})
        exit()

# ================== CALLBACK HANDLER ==================
async def handle_callback(cb):
    db = load_db()
    chat_id = cb["message"]["chat"]["id"]
    user_id = cb["from"]["id"]

    if user_id != SUPER_ADMIN and not is_admin(user_id, db):
        return

    data = cb["data"]
    if data == "add_admin":
        db["wait_add"] = chat_id
        save_db(db)
        await tg("sendMessage", {"chat_id": chat_id, "text":"👑 যাকে Admin করবি তার User ID দাও"})
    elif data == "remove_admin":
        db["wait_remove"] = chat_id
        save_db(db)
        await tg("sendMessage", {"chat_id": chat_id, "text":"❌ যাকে বাদ দিবি তার User ID দাও"})
    elif data == "admin_list":
        admins = db.get("admins",[])
        await tg("sendMessage", {"chat_id": chat_id, "text":"👑 Admin List:\n"+ "\n".join(map(str,admins))})
    await tg("answerCallbackQuery", {"callback_query_id": cb["id"]})

# ================== WEBHOOK ==================
async def handle(request):
    data = await request.json()
    if "message" in data:
        await handle_message(data["message"])
    if "callback_query" in data:
        await handle_callback(data["callback_query"])
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.post("/", handle)])

if __name__=="__main__":
    web.run_app(app, host="0.0.0.0", port=8080)
