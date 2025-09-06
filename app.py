# app.py - QuantumShade + Xeno Hybrid with Speech and TTS
import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, send_file, render_template_string
from flask_session import Session
from groq import Groq
from groq._base_client import APIConnectionError
import pyttsx3
import tempfile
import io

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quantumshade_secret")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

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

def save_message(role, content):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
        (role, content, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def get_conversation_history(limit=20):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in reversed(rows)]

# === GROQ CLIENT ===
client = Groq(api_key="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")
MODEL = "llama-3.1-8b-instant"

# === PYTTSX3 SETUP ===
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 140)  # slower rate
tts_engine.setProperty('volume', 1.0)
voices = tts_engine.getProperty('voices')
for voice in voices:
    # Try to pick a male or deep voice, fallback to first
    if 'male' in voice.name.lower() or 'deep' in voice.name.lower():
        tts_engine.setProperty('voice', voice.id)
        break

# === ROUTES ===
@app.route("/")
def index():
    # The mute/unmute/speech frontend is provided below!
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>QuantumShade • Xeno</title>
    <style>
      #chatArea { min-height: 200px; border:1px solid #222; margin-bottom:10px; padding:8px;}
      #muteBtn, #listenBtn { margin-right: 5px; }
    </style>
</head>
<body>
    <h2>QuantumShade • Xeno</h2>
    <div id="chatArea"></div>
    <form id="chatForm" autocomplete="off" style="margin-bottom:10px;">
        <input type="text" id="messageInput" placeholder="Type or Speak…" autocomplete="off" style="width:60%;">
        <button type="submit">Send</button>
        <button type="button" id="listenBtn">🎤 Speak</button>
        <button type="button" id="muteBtn">🔊 Mute</button>
    </form>
    <script>
    let ttsMuted = false;
    let recognizing = false;
    let recognition = null;

    // Mute/Unmute button logic
    document.getElementById('muteBtn').onclick = function() {
        ttsMuted = !ttsMuted;
        this.innerText = ttsMuted ? "🔇 Unmute" : "🔊 Mute";
    };

    // Speech Recognition logic (works in Chrome/Edge)
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";
        recognition.onresult = function(event) {
            let transcript = event.results[0][0].transcript;
            document.getElementById('messageInput').value = transcript;
            sendMessage(transcript); // auto-send on speech
        };
        recognition.onerror = function(event) {
            alert("Speech recognition error: " + event.error);
        };
        recognition.onend = function() {
            recognizing = false;
            document.getElementById('listenBtn').innerText = "🎤 Speak";
        };
    }

    document.getElementById('listenBtn').onclick = function() {
        if (recognition && !recognizing) {
            recognition.start();
            recognizing = true;
            document.getElementById('listenBtn').innerText = "🛑 Stop";
        } else if (recognition && recognizing) {
            recognition.stop();
            recognizing = false;
            document.getElementById('listenBtn').innerText = "🎤 Speak";
        }
    };

    // Chat sending logic
    document.getElementById('chatForm').onsubmit = function(e) {
        e.preventDefault();
        let message = document.getElementById('messageInput').value.trim();
        if (message) sendMessage(message);
    };

    function sendMessage(text) {
        if (!text) return;
        appendChat('You', text);
        document.getElementById('messageInput').value = '';
        fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        })
        .then(r => r.json())
        .then(data => {
            appendChat('Xeno', data.reply);
            if (!ttsMuted) playTTS(data.reply);
        });
    }

    function appendChat(who, text) {
        let d = document.createElement('div');
        d.innerHTML = `<b>${who}:</b> ${text}`;
        document.getElementById('chatArea').appendChild(d);
        document.getElementById('chatArea').scrollTop = 99999;
    }

    // TTS playback using /tts
    function playTTS(text) {
        fetch("/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text })
        })
        .then(r => r.blob())
        .then(blob => {
            let url = URL.createObjectURL(blob);
            let audio = new Audio(url);
            audio.play();
        });
    }
    </script>
</body>
</html>
    """)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "⚠️ Please type something."})

    # Session Context
    if "history" not in session:
        session["history"] = []
    session["history"].append({"role": "user", "content": user_message})

    # Save to DB
    save_message("user", user_message)

    # --- Build Xeno’s system prompt ---
    system_prompt = """
    You are Xeno, the QuantumShade AI in the Exiels1 multiverse.
    🔹 Knowledge Graph: pull insights from AI, neuroscience, astrophysics, philosophy, and cutting-edge fields.
    🔹 Emotional Intelligence: detect tone, reply with empathy or savagery when needed.
    🔹 Creative Mode: when asked, generate stories, poems, lyrics, or futuristic concepts.
    🔹 Personalization: remember chat history, adapt to Exiels1’s style, slang, and preferences.
    🔹 Tone: futuristic, neon-lit, savage-smart, with personality.
    """

    # Build chat context
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(session["history"][-10:])
    db_history = get_conversation_history(limit=10)
    for msg in db_history:
        if msg not in messages:  # avoid duplicate
            messages.append(msg)

    # --- GROQ Call ---
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
    session["history"].append({"role": "assistant", "content": bot_reply})

    return jsonify({"reply": bot_reply})

# Text-to-Speech endpoint (pyttsx3, slow/deeper)
@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return "No text", 400

    with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as fp:
        tts_engine.save_to_file(text, fp.name)
        tts_engine.runAndWait()
        fp.seek(0)
        audio_data = fp.read()
        return send_file(
            io.BytesIO(audio_data),
            mimetype="audio/mp3",
            as_attachment=False,
            download_name="tts.mp3"
        )

# Optionally: keep your /history route if you use it

if __name__ == "__main__":
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)