import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from groq import Groq
from groq._base_client import APIConnectionError

# === INIT APP ===
app = Flask(__name__)

# === DATABASE ===
def init_db():
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === GROQ CLIENT ===
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
model_to_use = "llama-3.3-13b-versatile"  # Use an existing supported model

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
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO messages (sender, message) VALUES (?, ?)", ("user", user_message))
    conn.commit()

    # === AI RESPONSE ===
    try:
        response = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[
                {"role": "system", "content": "You are Xeno, an adaptive, professional AI assistant. Keep responses concise and precise."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = response.choices[0].message.content
    except APIConnectionError as e:
        bot_reply = f"Connection error: {str(e)}"
    except Exception as e:
        bot_reply = f"Error generating response: {str(e)}"

    # Save bot message
    cur.execute("INSERT INTO messages (sender, message) VALUES (?, ?)", ("xeno", bot_reply))
    conn.commit()
    conn.close()

    return jsonify({"reply": bot_reply})

@app.route("/history", methods=["GET"])
def history():
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("SELECT sender, message FROM messages ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return jsonify(rows)

# === MAIN ===
if __name__ == "__main__":
    app.run(debug=True, port=5000)
