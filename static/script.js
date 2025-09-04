// QuantumShade Frontend — Xeno features: memory-driven UI, creative mode flag, sentiment glow, typing dots, knowledge graph

// ---- Preferences (local) ----
const PREFS_KEY = "xeno_prefs";
const prefs = loadPrefs();

function loadPrefs(){
  try { return JSON.parse(localStorage.getItem(PREFS_KEY)) || { name:"", style:"concise", theme:"quantum", creative:false }; }
  catch { return { name:"", style:"concise", theme:"quantum", creative:false }; }
}
function savePrefs(){
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  applyTheme();
  updateModeBadge();
}

// Apply theme
function applyTheme(){
  document.body.setAttribute("data-theme", prefs.theme || "quantum");
}

// Update mode badge
function updateModeBadge(){
  const badge = document.getElementById("modeBadge");
  badge.textContent = prefs.creative ? "Creative" : "Normal";
}

// ---- Elements ----
const chatArea = document.getElementById("chatArea");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const toggleCreative = document.getElementById("toggleCreative");
const btnProfile = document.getElementById("btnProfile");
const profileDrawer = document.getElementById("profileDrawer");
const btnCloseProfile = document.getElementById("btnCloseProfile");
const prefName = document.getElementById("prefName");
const prefStyle = document.getElementById("prefStyle");
const prefTheme = document.getElementById("prefTheme");
const btnSavePrefs = document.getElementById("btnSavePrefs");

const btnGraph = document.getElementById("btnGraph");
const btnRefreshGraph = document.getElementById("btnRefreshGraph");
const graphPanel = document.getElementById("graphPanel");

// Init UI with prefs
applyTheme();
updateModeBadge();
toggleCreative.checked = !!prefs.creative;
prefName.value = prefs.name || "";
prefStyle.value = prefs.style || "concise";
prefTheme.value = prefs.theme || "quantum";

// ---- Sentiment heuristic (lightweight) ----
function inferSentiment(text){
  const t = text.toLowerCase();
  const pos = ["great","awesome","nice","love","cool","thanks","perfect","good","yes"];
  const neg = ["bad","hate","angry","annoyed","wtf","no","broken","sad","error","issue","problem"];
  const score = pos.reduce((s,w)=>s+(t.includes(w)?1:0),0) - neg.reduce((s,w)=>s+(t.includes(w)?1:0),0);
  if (score > 0) return "happy";
  if (score < 0) return "sad";
  return "neutral";
}

// ---- Typing indicator ----
let typingEl = null;
function showTyping(){
  if (typingEl) return;
  typingEl = document.createElement("div");
  typingEl.className = "typing";
  typingEl.innerHTML = `<div class="dots"><span></span><span></span><span></span></div>`;
  chatArea.appendChild(typingEl);
  chatArea.scrollTop = chatArea.scrollHeight;
}
function hideTyping(){
  if (!typingEl) return;
  typingEl.remove();
  typingEl = null;
}

// ---- Append message ----
function appendMessage(role, text, mood=null){
  const el = document.createElement("div");
  el.className = `msg ${role} ${mood?mood:""}`;

  const meta = document.createElement("div");
  meta.className = "meta";
  const who = role === "user" ? (prefs.name || "You") : "Xeno";
  meta.textContent = `${who} • ${new Date().toLocaleTimeString()}`;

  const content = document.createElement("div");
  content.className = "content";
  content.textContent = text;

  el.appendChild(meta);
  el.appendChild(content);
  chatArea.appendChild(el);
  chatArea.scrollTop = chatArea.scrollHeight;
}

// ---- Load history ----
async function loadHistory(){
  try{
    const res = await fetch("/history");
    const data = await res.json(); // [{role, message, timestamp}, ...]
    chatArea.innerHTML = "";
    data.forEach(row=>{
      const mood = inferSentiment(row.message);
      appendMessage(row.role === "assistant" ? "assistant" : "user", row.message, mood);
    });
  }catch(e){
    appendMessage("assistant","(Couldn’t load history right now.)");
  }
}

// ---- Build “context note” for backend (until server supports prefs) ----
function buildContextPrefix(){
  const name = prefs.name ? `User name: ${prefs.name}. ` : "";
  const style = `Style: ${prefs.style}. `;
  const mode = prefs.creative ? "Mode: creative. " : "Mode: normal. ";
  return `[PREFERENCES] ${name}${style}${mode}`;
}

// ---- Send message ----
chatForm.addEventListener("submit", async (e)=>{
  e.preventDefault();
  const raw = messageInput.value.trim();
  if (!raw) return;

  const userMsg = raw;
  const sentiment = inferSentiment(userMsg);
  appendMessage("user", userMsg, sentiment);
  messageInput.value = "";

  showTyping();

  try{
    // We prepend a lightweight context prefix until you add server-side handling
    const payload = { message: `${buildContextPrefix()}\n${userMsg}` };

    const resp = await fetch("/chat", {
      method:"POST", headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(payload)
    });
    const j = await resp.json();

    hideTyping();
    const aiText = j.reply || "(No reply)";
    const aiMood = inferSentiment(aiText);
    appendMessage("assistant", aiText, aiMood);

    // Update knowledge graph with detected topics
    updateGraphFromText(userMsg + " " + aiText);

  }catch(err){
    hideTyping();
    appendMessage("assistant", "⚠️ Error contacting server.");
  }
});

// ---- Profile Drawer ----
btnProfile.addEventListener("click", ()=> profileDrawer.classList.add("open"));
btnCloseProfile.addEventListener("click", ()=> profileDrawer.classList.remove("open"));
btnSavePrefs.addEventListener("click", ()=>{
  prefs.name = prefName.value.trim();
  prefs.style = prefStyle.value;
  prefs.theme = prefTheme.value;
  savePrefs();
  profileDrawer.classList.remove("open");
});

// Creative Mode toggle
toggleCreative.addEventListener("change", ()=>{
  prefs.creative = toggleCreative.checked;
  savePrefs();
});

// ---- Graph Panel ----
btnRefreshGraph.addEventListener("click", ()=> rebuildGraphFromHistory());

// ---- Knowledge Graph (Cytoscape) ----
let cy = null;
function ensureGraph(){
  if (cy) return cy;
  cy = cytoscape({
    container: document.getElementById("graph"),
    style: [
      { selector: "node",
        style:{
          "background-color": "data(color)",
          "label": "data(label)",
          "color": "#cfe8ff",
          "font-size": 10,
          "text-outline-color":"#09111a",
          "text-outline-width":1
        }
      },
      { selector: "edge",
        style:{
          "width": 2,
          "line-color": "data(color)",
          "opacity": .8,
          "curve-style":"unbundled-bezier"
        }
      },
      { selector: ":selected", style:{ "border-width":2, "border-color":"#fff" } }
    ],
    layout: { name:"cose", animate:true, padding: 20 }
  });
  return cy;
}

function buildGraphElements() {
  return [
    { data: { id: 'session', label: 'Session' }, style: { 'background-color': '#7a8ca5', 'label': 'Session' } },
    { data: { id: 'code', label: 'CODE' }, style: { 'background-color': '#ffe08a', 'label': 'CODE' } },
    { data: { id: 'ai', label: 'AI' }, style: { 'background-color': '#00e6ff', 'label': 'AI' } },
    { data: { id: 'data', label: 'DATA' }, style: { 'background-color': '#8ab4ff', 'label': 'DATA' } },
    { data: { id: 'astro', label: 'ASTROPHYSICS' }, style: { 'background-color': '#ff3b88', 'label': 'ASTROPHYSICS' } },
    { data: { id: 'neuro', label: 'NEUROSCIENCE' }, style: { 'background-color': '#c0a0ff', 'label': 'NEUROSCIENCE' } },
    // Edges
    { data: { id: 'session-code', source: 'session', target: 'code' }, style: { 'line-color': '#ffe08a' } },
    { data: { id: 'session-ai', source: 'session', target: 'ai' }, style: { 'line-color': '#00e6ff' } },
    { data: { id: 'session-data', source: 'session', target: 'data' }, style: { 'line-color': '#8ab4ff' } },
    { data: { id: 'session-astro', source: 'session', target: 'astro' }, style: { 'line-color': '#ff3b88' } },
    { data: { id: 'session-neuro', source: 'session', target: 'neuro' }, style: { 'line-color': '#c0a0ff' } }
  ];
}

function ensureGraph() {
  if (!window.cy) {
    window.cy = cytoscape({
      container: document.getElementById('graph'),
      elements: buildGraphElements(),
      style: [
        { selector: 'node', style: { 'label': 'data(label)', 'color': '#e6eef6', 'font-size': '16px', 'text-valign': 'center', 'text-halign': 'center' } },
        { selector: 'edge', style: { 'width': 4, 'curve-style': 'bezier' } }
      ],
      layout: { name: 'cose' }
    });
  } else {
    window.cy.elements().remove();
    window.cy.add(buildGraphElements());
    window.cy.layout({ name: 'cose' }).run();
  }
}

// Call ensureGraph() on page load and when "Refresh from chat" is clicked
document.addEventListener("DOMContentLoaded", ensureGraph);
btnRefreshGraph.addEventListener("click", ensureGraph);

// ---- Boot ----
loadHistory();
rebuildGraphFromHistory();
