import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from groq import Groq
from groq._base_client import APIConnectionError

# === INIT APP ===
app = Flask(__name__)

# === DATABASE ===
def init_db():
    with sqlite3.connect("chat.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

# === GROQ CLIENT ===
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
model_to_use = "mixtral-8x7b"  # Replace with valid, supported model

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
    with sqlite3.connect("chat.db") as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO messages (sender, message) VALUES (?, ?)", ("user", user_message))
        conn.commit()

    # === AI RESPONSE ===
    try:
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": "You are Xeno, an adaptive, professional AI assistant. Keep responses concise and precise."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = response.choices[0].message.content
    except APIConnectionError as e:
        print(f"[Groq Error] Connection error: {e}")
        bot_reply = "Connection error. Please try again later."
    except Exception as e:
        print(f"[Groq Error] General error: {e}")
        bot_reply = "Error generating response. Please try again later."

    # Save bot message
    with sqlite3.connect("chat.db") as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO messages (sender, message) VALUES (?, ?)", ("xeno", bot_reply))
        conn.commit()

    return jsonify({"reply": bot_reply})

@app.route("/history", methods=["GET"])
def history():
    with sqlite3.connect("chat.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT sender, message, timestamp FROM messages ORDER BY id ASC")
        rows = cur.fetchall()
    return jsonify(rows or [])

# === MAIN ===
if __name__ == "__main__":
    app.run(debug=True, port=5000)
