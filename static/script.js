// static/script.js - QuantumShade chat client

// === Load chat history ===
async function loadHistory() {
  const res = await fetch('/history');
  const data = await res.json();
  const chatArea = document.getElementById('chatArea');
  chatArea.innerHTML = '';

  data.forEach(item => {
    const el = document.createElement('div');
    el.className = 'msg ' + (item[0] === 'user' ? 'user' : 'assistant');

    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.textContent = item[0] + ' • ' + new Date().toLocaleTimeString();

    const body = document.createElement('div');
    body.textContent = item[1];

    el.appendChild(meta);
    el.appendChild(body);
    chatArea.appendChild(el);
  });

  chatArea.scrollTop = chatArea.scrollHeight;
}

// === Send message ===
async function sendMessage(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('messageInput');
  const text = input.value.trim();
  if (!text) return;

  const chatArea = document.getElementById('chatArea');

  // Optimistic user message
  appendMessage('user', 'You', text);

  input.value = '';

  try {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });

    const j = await resp.json();

    appendMessage('assistant', 'Xeno', j.reply);

    // Optional: speak AI response
    speakMessage(j.reply);

  } catch (err) {
    console.error(err);
    appendMessage('assistant', 'Xeno', '⚠️ Error: Unable to get response.');
  }

  return false;
}

// === Append message helper ===
function appendMessage(role, sender, text) {
  const chatArea = document.getElementById('chatArea');
  const el = document.createElement('div');
  el.className = 'msg ' + role;

  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = sender + ' • ' + new Date().toLocaleTimeString();

  const body = document.createElement('div');
  body.textContent = text;

  el.appendChild(meta);
  el.appendChild(body);
  chatArea.appendChild(el);

  // Smooth scroll & fade-in
  el.style.opacity = 0;
  el.style.transform = 'translateY(10px)';
  setTimeout(() => {
    el.style.transition = 'all 0.3s ease';
    el.style.opacity = 1;
    el.style.transform = 'translateY(0)';
  }, 10);

  chatArea.scrollTop = chatArea.scrollHeight;
}

// === Text-to-speech ===
function speakMessage(text) {
  if (!text) return;
  if ('speechSynthesis' in window) {
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.0;
    window.speechSynthesis.speak(u);
  }
}

// === Initial load ===
loadHistory();

// === Bind send form ===
document.getElementById('chatForm').addEventListener('submit', sendMessage);

document.addEventListener("DOMContentLoaded", () => {
  const chatBox = document.getElementById("chat-box");
  const chatInput = document.getElementById("chat-input");
  const sendBtn = document.getElementById("send-btn");

  function appendMessage(sender, message, isTyping = false) {
    const msg = document.createElement("div");
    msg.classList.add("message", sender);

    if (isTyping) {
      msg.classList.add("typing-indicator");
      msg.innerHTML = `
        <span></span>
        <span></span>
        <span></span>
      `;
    } else {
      msg.textContent = message;
    }

    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msg;
  }

  async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    appendMessage("user", text);
    chatInput.value = "";

    // Add typing animation
    const typingMsg = appendMessage("xeno", "", true);

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();

      // Replace typing animation with reply
      typingMsg.remove();
      appendMessage("xeno", data.reply);
    } catch (err) {
      typingMsg.remove();
      appendMessage("xeno", "⚠️ Error connecting to server.");
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });
});
