/* ─────────────────────────────────────────────
   Ophthalmic Triage — Frontend (SSE streaming)
   Each agent step updates the sidebar in real-time.
───────────────────────────────────────────── */

const API_BASE = "https://ophthalmic-triage-production.up.railway.app";

let conversationHistory = [];
let currentEmr = null;

// ── DOM refs ──────────────────────────────────
const messagesEl    = document.getElementById("messages");
const inputEl       = document.getElementById("userInput");
const sendBtn       = document.getElementById("sendBtn");
const typingRow     = document.getElementById("typingRow");
const emrEl         = document.getElementById("emrContent");
const reportEl      = document.getElementById("reportContent");
const pipelineEl    = document.getElementById("pipelineSteps");
const triageBadge   = document.getElementById("triageBadge");
const triageLevelEl = document.getElementById("triageLevel");
const statusDot     = document.getElementById("statusDot");
const statusLabel   = document.getElementById("statusLabel");
const agentDebugEl  = document.getElementById("agentDebug");

// Model selector
const modelSelect = document.getElementById("modelSelect");
modelSelect.addEventListener("change", async () => {
  const model = modelSelect.value;
  try {
    await fetch(`${API_BASE}/model`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({model})
    });
    checkHealth();
  } catch (err) {
    console.error("Failed to change model:", err);
  }
});

// Clear button
const clearBtn = document.getElementById("clearBtn");
clearBtn.addEventListener("click", () => {
  if (confirm("确定要清空所有对话记录吗？")) {
    conversationHistory = [];
    currentEmr = null;
    messagesEl.innerHTML = `
      <div class="msg assistant">
        <div class="msg-avatar">🏥</div>
        <div class="msg-bubble">
          <p>Hello! I'm your ophthalmic triage assistant. Please describe your eye concern and I'll guide you to the right level of care.</p>
        </div>
      </div>`;
    emrEl.textContent = "尚未收集信息…";
    reportEl.textContent = "等待评估…";
    triageBadge.style.display = "none";
    initPipelineUI();
    agentDebugEl.innerHTML = '<div class="debug-idle">等待Agent执行…</div>';
  }
});

// Step label map
const STEP_LABELS = {
  1: { icon: "🛡️", name: "Safety Pre-Check" },
  2: { icon: "📋", name: "Recipient (EMR)" },
  3: { icon: "🔬", name: "Assessor (AAO)" },
  4: { icon: "💬", name: "Inquirer (Nurse)" },
  5: { icon: "🛡️", name: "Safety Post-Check" },
};

// ── Health check ──────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    if (res.ok) {
      const d = await res.json();
      statusDot.className = "status-dot online";
      statusLabel.textContent = `在线 · ${d.model?.split("/")[1] || ""}`;
      // Sync dropdown with backend model
      if (d.model) {
        modelSelect.value = d.model;
      }
    } else throw new Error();
  } catch {
    statusDot.className = "status-dot offline";
    statusLabel.textContent = "无法连接后端";
  }
}
checkHealth();
setInterval(checkHealth, 30000);

// ── Pipeline step UI ──────────────────────────
function initPipelineUI() {
  pipelineEl.innerHTML = "";
  for (let i = 1; i <= 5; i++) {
    const { icon, name } = STEP_LABELS[i];
    const div = document.createElement("div");
    div.id = `ps-${i}`;
    div.className = "pipeline-step";
    div.innerHTML = `
      <div class="step-num">${i}</div>
      <div class="step-info">
        <div class="step-agent">${icon} ${name}</div>
      </div>
      <span class="step-status" id="pss-${i}">待机</span>`;
    pipelineEl.appendChild(div);
  }
}

function setStepRunning(step) {
  console.log('setStepRunning called for step', step);
  const el = document.getElementById(`ps-${step}`);
  console.log('Found element:', el);
  if (!el) return;
  el.className = "pipeline-step active";
  const s = document.getElementById(`pss-${step}`);
  s.className = "step-status running";
  s.innerHTML = '<span class="spinner"></span>';
}

function setStepDone(step, status) {
  console.log('setStepDone called for step', step, 'status', status);
  const el = document.getElementById(`ps-${step}`);
  console.log('Found element:', el);
  if (!el) return;
  const isSafe = status === "SAFE" || status === "COMPLETE";
  el.className = `pipeline-step ${isSafe ? "done" : "unsafe"}`;
  const s = document.getElementById(`pss-${step}`);
  s.className = `step-status ${isSafe ? "SAFE" : "UNSAFE"}`;
  s.textContent = status === "COMPLETE" ? "✓" : status;
}

function addAgentDebug(step, agent, detail, input = null) {
  const agentClass = agent.toLowerCase().replace(/\s+/g, '-').split('-')[0];
  const entry = document.createElement('div');
  entry.className = `debug-entry ${agentClass}`;

  let html = `<div class="debug-header">Step ${step}: ${agent}</div>`;

  if (input) {
    html += `<div class="debug-label">📥 INPUT:</div>`;
    html += `<div class="debug-content">${escapeHtml(input)}</div>`;
  }

  html += `<div class="debug-label">📤 OUTPUT:</div>`;
  html += `<div class="debug-content">${escapeHtml(detail)}</div>`;

  entry.innerHTML = html;
  agentDebugEl.appendChild(entry);
  agentDebugEl.scrollTop = agentDebugEl.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ── Send message ──────────────────────────────
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  sendBtn.disabled = true;
  inputEl.disabled = true;
  inputEl.value = "";

  appendMessage("user", text);
  typingRow.style.display = "flex";

  // Reset sidebar
  emrEl.textContent = "⏳ 提取中…";
  reportEl.textContent = "⏳ 评估中…";
  initPipelineUI();
  agentDebugEl.innerHTML = '';

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: conversationHistory,
        currentEmr: currentEmr,
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (!res.body) throw new Error("No streaming body");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();

      if (value) {
        buffer += decoder.decode(value, { stream: true });
      }

      if (done) {
        console.log('Stream done, processing remaining buffer');
        // Process any remaining data in buffer
        if (buffer.trim()) {
          const lines = buffer.split("\n\n");
          for (const chunk of lines) {
            if (!chunk.startsWith("data: ")) continue;
            let event;
            try { event = JSON.parse(chunk.slice(6)); } catch { continue; }
            console.log('Final event:', event.type);

            if (event.type === "done") {
              console.log('Got done event from buffer');
              conversationHistory.push({ role: "user", content: text });
              conversationHistory.push({ role: "assistant", content: event.response });
              currentEmr = event.emr;

              emrEl.textContent    = event.emr_text || "—";
              reportEl.textContent = event.triage_report || "—";
              updateTriageBadge(event.triage_level, event.disposition_ready);

              const msgClass = triageClass(event.triage_level, event.disposition_ready);
              appendMessage("assistant", event.response, msgClass);

              speakText(event.response);

              if (event.disposition_ready) {
                showFinalResult(event.triage_level, event.emr_text, event.triage_report);
              }

              if (event.trigger_handoff) {
                appendMessage("assistant", "🔄 正在转接人工护士…");
              }
            }
          }
        }
        break;
      }

      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep incomplete chunk

      for (const chunk of lines) {
        if (!chunk.startsWith("data: ")) continue;
        let event;
        try {
          event = JSON.parse(chunk.slice(6));
        } catch (e) {
          console.error('Parse error:', e, chunk);
          continue;
        }

        console.log('Event:', event.type, event.step || '');

        if (event.type === "step_start") {
          console.log('Calling setStepRunning for step', event.step);
          setStepRunning(event.step);
        }

        if (event.type === "step_done") {
          console.log('Calling setStepDone for step', event.step, 'status', event.status);
          setStepDone(event.step, event.status);
          addAgentDebug(event.step, event.agent, event.detail || '—', event.input || null);
          if (event.step === 2) emrEl.textContent = event.detail || "—";
          if (event.step === 3) reportEl.textContent = event.detail || "—";
        }

        if (event.type === "done") {
          console.log('Got done event');
          conversationHistory.push({ role: "user", content: text });
          conversationHistory.push({ role: "assistant", content: event.response });
          currentEmr = event.emr;

          emrEl.textContent    = event.emr_text || "—";
          reportEl.textContent = event.triage_report || "—";
          updateTriageBadge(event.triage_level, event.disposition_ready);

          const msgClass = triageClass(event.triage_level, event.disposition_ready);
          appendMessage("assistant", event.response, msgClass);

          speakText(event.response);

          if (event.disposition_ready) {
            showFinalResult(event.triage_level, event.emr_text, event.triage_report);
          }

          if (event.trigger_handoff) {
            appendMessage("assistant", "🔄 正在转接人工护士…");
          }
          break;
        }
      }
    }

  } catch (err) {
    appendMessage("assistant",
      `⚠️ 连接错误：${err.message}。请确认后端已启动（python3 main.py）。`);
  } finally {
    typingRow.style.display = "none";
    sendBtn.disabled = false;
    inputEl.disabled = false;
    inputEl.focus();
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

// ── Render helpers ────────────────────────────
function appendMessage(role, text, extraClass = "") {
  const div = document.createElement("div");
  div.className = `msg ${role} ${extraClass}`.trim();
  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "🙋" : "🏥";
  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.textContent = text;
  div.appendChild(avatar);
  div.appendChild(bubble);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function triageClass(level, ready) {
  if (!ready) return "";
  if (level === "EMERGENT") return "emergent";
  if (level === "URGENT")   return "urgent";
  if (level === "ROUTINE")  return "routine";
  return "";
}

function updateTriageBadge(level, ready) {
  if (!level || level === "INCOMPLETE" || level === "None") {
    triageBadge.style.display = "none";
    return;
  }
  triageBadge.style.display = "flex";
  triageLevelEl.className = `badge-value ${level}`;
  const labels = {
    EMERGENT: "🚨 紧急 EMERGENT",
    URGENT:   "⚠️ 尽快 URGENT",
    ROUTINE:  "✅ 常规 ROUTINE",
  };
  triageLevelEl.textContent = labels[level] || level;
}

function showFinalResult(level, emrText, report) {
  const finalResult = document.getElementById('finalResult');
  const finalTriageLevel = document.getElementById('finalTriageLevel');
  const finalEmr = document.getElementById('finalEmr');
  const finalReport = document.getElementById('finalReport');

  const labels = {
    EMERGENT: "🚨 EMERGENT - Seek immediate care",
    URGENT: "⚠️ URGENT - See doctor within 24 hours",
    ROUTINE: "✅ ROUTINE - Schedule regular appointment",
  };

  finalTriageLevel.textContent = labels[level] || level;
  finalTriageLevel.className = `triage-badge-large ${level}`;
  finalEmr.textContent = emrText;
  finalReport.textContent = report;
  finalResult.style.display = 'block';
  finalResult.scrollIntoView({ behavior: 'smooth' });
}

// ── Add spinner CSS dynamically ───────────────
const style = document.createElement("style");
style.textContent = `
.spinner {
  display: inline-block; width: 12px; height: 12px;
  border: 2px solid #ccc; border-top-color: #1a73e8;
  border-radius: 50%; animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.step-status.running { background: rgba(26,115,232,.15); color: #1a73e8; }
`;
document.head.appendChild(style);

// ── Prompt Editor ─────────────────────────────
const toggleBtn = document.getElementById("togglePromptEditor");
const promptEditor = document.getElementById("promptEditor");
const agentSelect = document.getElementById("agentSelect");
const promptText = document.getElementById("promptText");
const saveBtn = document.getElementById("savePrompt");
const promptStatus = document.getElementById("promptStatus");

toggleBtn.addEventListener("click", () => {
  if (promptEditor.style.display === "none") {
    promptEditor.style.display = "block";
    toggleBtn.textContent = "收起";
    loadPrompt();
  } else {
    promptEditor.style.display = "none";
    toggleBtn.textContent = "展开";
  }
});

agentSelect.addEventListener("change", loadPrompt);

async function loadPrompt() {
  const agent = agentSelect.value;
  try {
    const res = await fetch(`${API_BASE}/prompts/${agent}`);
    const data = await res.json();
    promptText.value = data.prompt || "";
    promptStatus.textContent = "";
  } catch (err) {
    promptStatus.textContent = "⚠️ 加载失败";
  }
}

saveBtn.addEventListener("click", async () => {
  const agent = agentSelect.value;
  const prompt = promptText.value;
  try {
    const res = await fetch(`${API_BASE}/prompts/${agent}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({prompt})
    });
    if (res.ok) {
      promptStatus.textContent = "✅ 保存成功";
      setTimeout(() => promptStatus.textContent = "", 2000);
    } else {
      promptStatus.textContent = "❌ 保存失败";
    }
  } catch (err) {
    promptStatus.textContent = "❌ 网络错误";
  }
});

// ── Init & keyboard ───────────────────────────
initPipelineUI();

// Voice input (Web Speech API)
const voiceBtn = document.getElementById("voiceBtn");
let recognition = null;
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    inputEl.value = transcript;
    voiceBtn.textContent = '🎤';
  };

  recognition.onerror = () => {
    voiceBtn.textContent = '🎤';
  };

  recognition.onend = () => {
    voiceBtn.textContent = '🎤';
  };

  voiceBtn.addEventListener('click', () => {
    if (voiceBtn.textContent === '🎤') {
      recognition.start();
      voiceBtn.textContent = '🔴';
    } else {
      recognition.stop();
      voiceBtn.textContent = '🎤';
    }
  });
} else {
  voiceBtn.style.display = 'none';
}

// Voice output (Web Speech API)
function speakText(text) {
  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    utterance.pitch = 1.2;
    speechSynthesis.speak(utterance);
  }
}

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
