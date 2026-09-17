let currentChatId = null;
let currentSessionId = "default";

document.addEventListener('DOMContentLoaded', () => {
  loadChats();
  loadDBSchema();
});

async function loadChats() {
  try {
    const res = await fetch('/api/chats');
    const chats = await res.json();
    renderChatList(chats);

    if (chats.length > 0 && !currentChatId) {
      selectChat(chats[0].id);
    } else if (chats.length === 0) {
      createNewChat();
    }
  } catch (e) {
    console.error("Error loading chats:", e);
  }
}

function renderChatList(chats) {
  const container = document.getElementById('chatList');
  container.innerHTML = '';

  chats.forEach(chat => {
    const item = document.createElement('div');
    item.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
    item.innerHTML = `
      <span class="chat-title" title="${escapeHtml(chat.title)}">${escapeHtml(chat.title)}</span>
      <button class="btn-delete-chat" onclick="deleteChat(event, '${chat.id}')" title="Delete Chat">&times;</button>
    `;
    item.onclick = (e) => {
      if (!e.target.classList.contains('btn-delete-chat')) {
        selectChat(chat.id);
      }
    };
    container.appendChild(item);
  });
}

async function createNewChat() {
  try {
    const res = await fetch('/api/chats', {
      method: 'POST',
      headers: { 'x-session-id': currentSessionId }
    });
    const newChat = await res.json();
    currentChatId = newChat.id;
    await loadChats();
    selectChat(newChat.id);
  } catch (e) {
    console.error("Error creating chat:", e);
  }
}

async function selectChat(chatId) {
  currentChatId = chatId;
  try {
    const res = await fetch(`/api/chats/${chatId}`);
    const chat = await res.json();
    renderChatMessages(chat);
    renderChatList(await (await fetch('/api/chats')).json());
  } catch (e) {
    console.error("Error selecting chat:", e);
  }
}

async function deleteChat(event, chatId) {
  event.stopPropagation();
  if (!confirm("Are you sure you want to delete this chat session?")) return;

  try {
    await fetch(`/api/chats/${chatId}`, { method: 'DELETE' });
    if (currentChatId === chatId) {
      currentChatId = null;
    }
    loadChats();
  } catch (e) {
    console.error("Error deleting chat:", e);
  }
}

function renderChatMessages(chat) {
  const viewport = document.getElementById('chatViewport');
  viewport.innerHTML = '';

  if (!chat.messages || chat.messages.length === 0) {
    viewport.innerHTML = `
      <div class="welcome-card">
        <div class="welcome-icon">⚡</div>
        <h2>Welcome to QueryClarify</h2>
        <p>Connect your PostgreSQL database in Settings or ask questions about the connected database.</p>
        <div class="welcome-grid">
          <div class="grid-item">
            <h4>Dynamic Ambiguity</h4>
            <p>Identifies underspecified queries against your connected database schema.</p>
          </div>
          <div class="grid-item">
            <h4>SQLGlot Read-Only</h4>
            <p>Enforces read-only AST guardrails (blocks write/mutation queries).</p>
          </div>
          <div class="grid-item">
            <h4>Custom Database</h4>
            <p>Supports connecting any arbitrary PostgreSQL database.</p>
          </div>
        </div>
      </div>
    `;
    return;
  }

  chat.messages.forEach(msg => {
    if (msg.sender === 'user') {
      appendUserMessageUI(msg.text);
    } else {
      appendAssistantMessageUI(msg);
    }
  });

  viewport.scrollTop = viewport.scrollHeight;
}

async function handleFormSubmit(event) {
  event.preventDefault();
  const input = document.getElementById('queryInput');
  const text = input.value.trim();
  if (!text) return;

  if (!currentChatId) {
    await createNewChat();
  }

  appendUserMessageUI(text);
  input.value = '';

  const loadingCard = appendLoadingIndicator();

  try {
    const payload = {
      chat_id: currentChatId,
      message: text
    };

    const res = await fetch('/api/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const msg = await res.json();
    loadingCard.remove();

    appendAssistantMessageUI(msg);
    loadChats(); // Update chat titles in sidebar if changed

  } catch (e) {
    loadingCard.remove();
    appendErrorMessage("Failed to process request: " + e.message);
  }
}

async function handleClarificationChoice(optionId, question) {
  const loadingCard = appendLoadingIndicator();

  try {
    const payload = {
      chat_id: currentChatId,
      message: question,
      selected_option: optionId
    };

    const res = await fetch('/api/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const msg = await res.json();
    loadingCard.remove();

    appendAssistantMessageUI(msg);

  } catch (e) {
    loadingCard.remove();
    appendErrorMessage("Failed to submit clarification: " + e.message);
  }
}

function appendUserMessageUI(text) {
  const viewport = document.getElementById('chatViewport');
  const welcomeCard = document.querySelector('.welcome-card');
  if (welcomeCard) welcomeCard.style.display = 'none';

  const userMsg = document.createElement('div');
  userMsg.className = 'user-message';
  userMsg.textContent = text;
  viewport.appendChild(userMsg);
  viewport.scrollTop = viewport.scrollHeight;
}

function appendAssistantMessageUI(msg) {
  const viewport = document.getElementById('chatViewport');
  const welcomeCard = document.querySelector('.welcome-card');
  if (welcomeCard) welcomeCard.style.display = 'none';

  const aiCard = document.createElement('div');
  aiCard.className = 'ai-card';

  if (msg.status === 'clarification_required') {
    aiCard.innerHTML = `
      <div class="ambiguity-banner">
        <div class="ambiguity-header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>Ambiguous Intent Detected (${msg.ambiguity ? msg.ambiguity.ambiguity_type : 'Ambiguity'})</span>
        </div>
        <p class="ambiguity-reason">${msg.ambiguity ? msg.ambiguity.reason : ''}</p>
        <div class="ambiguity-question">${escapeHtml(msg.clarification_question || '')}</div>
        <div class="options-grid" id="opts-${msg.id}"></div>
      </div>
    `;

    viewport.appendChild(aiCard);

    const optsContainer = aiCard.querySelector(`#opts-${msg.id}`);
    if (msg.clarification_options) {
      msg.clarification_options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'btn-option';
        btn.innerHTML = `
          <span class="option-label">${escapeHtml(opt.label)}</span>
          <span class="option-desc">${escapeHtml(opt.description)}</span>
        `;
        btn.onclick = () => handleClarificationChoice(opt.id, msg.text);
        optsContainer.appendChild(btn);
      });
    }

  } else if (msg.status === 'completed') {
    let tableHtml = '';
    if (msg.rows && msg.rows.length > 0) {
      const headers = msg.columns.map(c => `<th>${escapeHtml(c)}</th>`).join('');
      const rows = msg.rows.map(row => {
        const cells = msg.columns.map(c => `<td>${row[c] !== null && row[c] !== undefined ? escapeHtml(String(row[c])) : ''}</td>`).join('');
        return `<tr>${cells}</tr>`;
      }).join('');

      tableHtml = `
        <div class="table-container">
          <table class="data-table">
            <thead><tr>${headers}</tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      `;
    }

    aiCard.innerHTML = `
      <div class="summary-box">
        <strong>Result:</strong> ${escapeHtml(msg.summary || msg.text)}
      </div>

      <div class="sql-section">
        <div class="sql-header">
          <span>Generated SQL Query</span>
          <span class="badge-safety">✓ SQLGlot Read-Only Verified</span>
        </div>
        <div class="sql-code">${escapeHtml(msg.sql)}</div>
      </div>

      ${tableHtml}

      <div class="metrics-bar">
        <div class="metric-item">Execution Latency: <span>${msg.execution_time_ms} ms</span></div>
        <div class="metric-item">Rows Returned: <span>${msg.row_count}</span></div>
        <div class="metric-item">Tables Referenced: <span>${msg.tables_used ? msg.tables_used.join(', ') : 'None'}</span></div>
      </div>
    `;

    viewport.appendChild(aiCard);

  } else if (msg.status === 'error') {
    appendErrorMessage(msg.error || msg.text);
    return;
  }

  viewport.scrollTop = viewport.scrollHeight;
}

function appendLoadingIndicator() {
  const viewport = document.getElementById('chatViewport');
  const card = document.createElement('div');
  card.className = 'ai-card';
  card.innerHTML = `<div class="summary-box">Thinking, inspecting database schema, and analyzing query...</div>`;
  viewport.appendChild(card);
  viewport.scrollTop = viewport.scrollHeight;
  return card;
}

function appendErrorMessage(errorMsg) {
  const viewport = document.getElementById('chatViewport');
  const card = document.createElement('div');
  card.className = 'ai-card';
  card.style.borderColor = 'rgba(244, 63, 94, 0.4)';
  card.innerHTML = `
    <div style="color: #f43f5e; font-weight: 600;">⚠️ Error</div>
    <div style="font-size: 0.9rem; color: #fca5a5;">${escapeHtml(errorMsg)}</div>
  `;
  viewport.appendChild(card);
  viewport.scrollTop = viewport.scrollHeight;
}

/* Database Settings Modal & Connection Logic */
function toggleSettingsModal() {
  const modal = document.getElementById('settingsModal');
  modal.classList.toggle('active');
}

async function testDBConnection() {
  const feedback = document.getElementById('dbFeedback');
  feedback.className = 'feedback-msg';
  feedback.style.display = 'block';
  feedback.textContent = "Testing connection...";

  const payload = getDBFormPayload();
  try {
    const res = await fetch('/api/database/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      feedback.className = 'feedback-msg success';
      feedback.textContent = "✓ " + data.message;
    } else {
      feedback.className = 'feedback-msg error';
      feedback.textContent = "❌ " + data.message;
    }
  } catch (e) {
    feedback.className = 'feedback-msg error';
    feedback.textContent = "❌ Connection test failed: " + e.message;
  }
}

async function connectCustomDB() {
  const feedback = document.getElementById('dbFeedback');
  feedback.className = 'feedback-msg';
  feedback.style.display = 'block';
  feedback.textContent = "Connecting to database...";

  const payload = getDBFormPayload();
  try {
    const res = await fetch('/api/database/connect', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-session-id': currentSessionId
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok && data.success) {
      feedback.className = 'feedback-msg success';
      feedback.textContent = "✓ " + data.message;
      updateHeaderStatus(true, payload.database);
      loadDBSchema();
      setTimeout(toggleSettingsModal, 1500);
    } else {
      feedback.className = 'feedback-msg error';
      feedback.textContent = "❌ " + (data.detail || data.message);
    }
  } catch (e) {
    feedback.className = 'feedback-msg error';
    feedback.textContent = "❌ Connect failed: " + e.message;
  }
}

async function disconnectDB() {
  try {
    await fetch('/api/database/disconnect', {
      method: 'POST',
      headers: { 'x-session-id': currentSessionId }
    });
    const feedback = document.getElementById('dbFeedback');
    feedback.className = 'feedback-msg success';
    feedback.textContent = "Disconnected custom DB. Reverted to demo database.";
    updateHeaderStatus(false, "queryclarify (demo e-commerce)");
    loadDBSchema();
  } catch (e) {
    console.error("Error disconnecting:", e);
  }
}

async function loadDBSchema() {
  try {
    const res = await fetch('/api/database/schema', {
      headers: { 'x-session-id': currentSessionId }
    });
    const data = await res.json();
    document.getElementById('schemaText').textContent = data.schema_text;
    updateHeaderStatus(data.connected, data.database_name);
  } catch (e) {
    console.error("Error loading schema:", e);
  }
}

function updateHeaderStatus(isConnected, dbName) {
  const text = document.getElementById('statusText');
  text.textContent = `Connected to: ${dbName}`;
}

function getDBFormPayload() {
  return {
    host: document.getElementById('dbHost').value || "localhost",
    port: parseInt(document.getElementById('dbPort').value) || 5432,
    database: document.getElementById('dbName').value,
    username: document.getElementById('dbUser').value,
    password: document.getElementById('dbPassword').value
  };
}

async function toggleSchemaModal() {
  const modal = document.getElementById('schemaModal');
  if (modal.classList.contains('active')) {
    modal.classList.remove('active');
  } else {
    modal.classList.add('active');
    await loadDBSchema();
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
