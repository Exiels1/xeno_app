import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from groq import Groq
from groq._base_client import APIConnectionError

# === INIT APP ===
app = Flask(__name__)

DB_FILE = "chat.db"

# === DATABASE ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === GROQ CLIENT ===
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"  # ✅ adjust if you want

# === HELPERS ===
def save_message(role, content):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def get_conversation_history(limit=50):  # limit avoids overload
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM conversations ORDER BY id ASC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in rows]

# === ROUTES ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Please send a message."})

    # Save user message
    save_message("user", user_message)

    # === AI RESPONSE ===
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=(
                [{"role": "system", "content": "You are Xeno, an adaptive assistant."}]
                + get_conversation_history()
                + [{"role": "user", "content": user_message}]
            )
        )
        bot_reply = completion.choices[0].message.content
    except APIConnectionError:
        bot_reply = "⚠️ Connection issue. Try again."
    except Exception as e:
        bot_reply = f"⚠️ Error: {str(e)}"

    # Save AI reply
    save_message("assistant", bot_reply)

    return jsonify({"reply": bot_reply})

@app.route("/history", methods=["GET"])
def history():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT role, content, timestamp FROM conversations ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    history_data = [
        {"role": role, "message": content, "timestamp": timestamp}
        for role, content, timestamp in rows
    ]
    return jsonify(history_data)

# === MAIN ===
if __name__ == "__main__":
    app.run(debug=True, port=5000)
