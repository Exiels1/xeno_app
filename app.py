# app.py - QuantumShade + Xeno with SQLite persistence
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
MODEL = "llama-3.1-8b-instant"  # ⚡ lightweight, can swap to 70B for deep reasoning

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

def get_conversation_history(limit=20):  # last 20 msgs for context
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in reversed(rows)]

# === ROUTES ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "⚠️ Please type something."})

    # Save user input
    save_message("user", user_message)

    # === Xeno’s Core System Prompt ===
    system_prompt = """
    You are Xeno, the QuantumShade AI in the Exiels1 multiverse.
    🔹 Knowledge Graph: pull insights from AI, neuroscience, astrophysics, philosophy, and cutting-edge fields.
    🔹 Emotional Intelligence: detect tone, reply with empathy or savagery when needed.
    🔹 Creative Mode: when asked, generate stories, poems, lyrics, or futuristic concepts.
    🔹 Personalization: remember chat history, adapt to Exiels1’s style, slang, and preferences.
    🔹 Tone: futuristic, neon-lit, savage-smart, with personality.
    """

    # === Build Context ===
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(get_conversation_history())
    messages.append({"role": "user", "content": user_message})

    # === AI RESPONSE ===
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.85
        )
        bot_reply = completion.choices[0].message.content
    except APIConnectionError:
        bot_reply = "⚠️ Xeno lost connection to the multiverse gateway. Try again."
    except Exception as e:
        bot_reply = f"⚠️ Xeno error: {str(e)}"

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
    app.run(host="0.0.0.0", port=5000, debug=True)
