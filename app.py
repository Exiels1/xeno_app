import os
import sqlite3
from datetime import datetime
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
            message TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === GROQ CLIENT ===
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"  # Replace with your valid model

# === ROUTES ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Please send a message."})

    timestamp = datetime.utcnow().isoformat()

    # Save user message
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)",
        ("user", user_message, timestamp)
    )
    conn.commit()

    # === AI RESPONSE ===
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Xeno, an adaptive and professional AI assistant. "
                        "Respond concisely, clearly, and contextually. "
                        "For code, always format in markdown with proper syntax highlighting. "
                        "Use bullet points for instructions when helpful, "
                        "and avoid unnecessary fluff. "
                        "Keep a neutral, professional tone."
                    )
                },
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = response.choices[0].message.content
    except APIConnectionError as e:
        bot_reply = "Hmm… I’m having trouble connecting to the AI service. Please try again."
    except Exception as e:
        bot_reply = f"An unexpected error occurred: {str(e)}"

    # Save bot message
    cur.execute(
        "INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)",
        ("xeno", bot_reply, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

    return jsonify({"reply": bot_reply})

@app.route("/history", methods=["GET"])
def history():
    conn = sqlite3.connect("chat.db")
    cur = conn.cursor()
    cur.execute("SELECT sender, message, timestamp FROM messages ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    # Convert to list of dicts for frontend
    history_data = [
        {"role": sender, "message": message, "timestamp": timestamp}
        for sender, message, timestamp in rows
    ]
    return jsonify(history_data)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]

    # Save user message
    c.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", ("user", user_message))
    conn.commit()

    # Get AI reply
    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=get_conversation_history() + [{"role": "user", "content": user_message}]
    )
    reply = completion.choices[0].message.content

    # Save AI reply
    c.execute("INSERT INTO conversations (role, content) VALUES (?, ?)", ("assistant", reply))
    conn.commit()

    return jsonify({"reply": reply})

def get_conversation_history():
    c.execute("SELECT role, content FROM conversations ORDER BY id ASC")
    rows = c.fetchall()
    return [{"role": role, "content": content} for role, content in rows]


# === MAIN ===
if __name__ == "__main__":
    app.run(debug=True, port=5000)

#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 api key
