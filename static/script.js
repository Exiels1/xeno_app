// === Append message helper ===
function appendMessage(role, sender, text, isTyping = false) {
  const chatArea = document.getElementById('chatArea');
  const el = document.createElement('div');
  el.className = 'msg ' + role;

  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = sender + ' • ' + new Date().toLocaleTimeString();

  const body = document.createElement('div');
  body.className = 'content';

  if (isTyping) {
    body.classList.add('typing-indicator');
    body.innerHTML = `<span></span><span></span><span></span>`;
  } else {
    body.textContent = text;
  }

  el.appendChild(meta);
  el.appendChild(body);
  chatArea.appendChild(el);

  chatArea.scrollTop = chatArea.scrollHeight;
  return el;
}

// === Send message ===
async function sendMessage(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('messageInput');
  const text = input.value.trim();
  if (!text) return;

  appendMessage('user', 'You', text);
  input.value = '';

  const typingEl = appendMessage('assistant', 'Xeno', '', true);

  try {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const j = await resp.json();

    typingEl.remove();
    appendMessage('assistant', 'Xeno', j.reply);
  } catch (err) {
    typingEl.remove();
    appendMessage('assistant', 'Xeno', '⚠️ Error getting response.');
  }
}

document.getElementById('chatForm').addEventListener('submit', sendMessage);
