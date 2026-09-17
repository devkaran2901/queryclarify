let currentChatId = null;
let currentSessionId = "default";
let isSubmitting = false;

// Expose functions globally to window immediately
window.initApp = initApp;
window.loadChats = loadChats;
window.renderChatList = renderChatList;
window.createNewChat = createNewChat;
window.selectChat = selectChat;
window.deleteChat = deleteChat;
window.renderChatMessages = renderChatMessages;
window.handleFormSubmit = handleFormSubmit;
window.handleClarificationChoice = handleClarificationChoice;
window.appendUserMessageUI = appendUserMessageUI;
window.appendAssistantMessageUI = appendAssistantMessageUI;
window.openSettingsModal = openSettingsModal;
window.closeSettingsModal = closeSettingsModal;
window.toggleSettingsModal = toggleSettingsModal;
window.openSchemaModal = openSchemaModal;
window.closeSchemaModal = closeSchemaModal;
window.toggleSchemaModal = toggleSchemaModal;
window.testDBConnection = testDBConnection;
window.connectCustomDB = connectCustomDB;
window.disconnectDB = disconnectDB;
window.loadDBSchema = loadDBSchema;

function initApp() {
  loadChats();
  loadDBSchema();

  const newChatBtn = document.getElementById('newChatBtn');
  if (newChatBtn) newChatBtn.onclick = createNewChat;

  const settingsBtn = document.getElementById('settingsBtn');
  if (settingsBtn) settingsBtn.onclick = openSettingsModal;

  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  if (closeSettingsBtn) closeSettingsBtn.onclick = closeSettingsModal;

  const schemaTopBtn = document.getElementById('schemaTopBtn');
  if (schemaTopBtn) schemaTopBtn.onclick = openSchemaModal;

  const closeSchemaBtn = document.getElementById('closeSchemaBtn');
  if (closeSchemaBtn) closeSchemaBtn.onclick = closeSchemaModal;

  const settingsModal = document.getElementById('settingsModal');
  if (settingsModal) {
    settingsModal.onclick = (e) => {
      if (e.target === settingsModal) closeSettingsModal();
    };
  }

  const schemaModal = document.getElementById('schemaModal');
  if (schemaModal) {
    schemaModal.onclick = (e) => {
      if (e.target === schemaModal) closeSchemaModal();
    };
  }

  const testDBBtn = document.getElementById('testDBBtn');
  if (testDBBtn) testDBBtn.onclick = testDBConnection;

  const connectDBBtn = document.getElementById('connectDBBtn');
  if (connectDBBtn) connectDBBtn.onclick = connectCustomDB;

  const disconnectDBBtn = document.getElementById('disconnectDBBtn');
  if (disconnectDBBtn) disconnectDBBtn.onclick = disconnectDB;

  const queryForm = document.getElementById('queryForm');
  if (queryForm) queryForm.onsubmit = handleFormSubmit;
}

// Immediate execution or DOMContentLoaded safety check
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}

async function loadChats() {
  try {
    const res = await fetch('/api/chats');
    if (!res.ok) return;
    const chats = await res.json();
    renderChatList(chats);

    if (chats.length > 0) {
      if (!currentChatId || !chats.some(c => c.id === currentChatId)) {
        selectChat(chats[0].id);
      }
    } else {
      createNewChat();
    }
  } catch (e) {
    console.error("Error loading chats:", e);
  }
}

function renderChatList(chats) {
  const container = document.getElementById('chatList');
  if (!container) return;
  container.innerHTML = '';

  chats.forEach(chat => {
    const item = document.createElement('div');
    item.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
    item.dataset.chatId = chat.id;
    item.innerHTML = `
      <span class="chat-title" title="${escapeHtml(chat.title)}">${escapeHtml(chat.title)}</span>
      <button class="btn-delete-chat" title="Delete Chat" onclick="event.stopPropagation(); deleteChat('${chat.id}')">&times;</button>
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
    if (!res.ok) return;
    const newChat = await res.json();
    currentChatId = newChat.id;
    
    const chatsRes = await fetch('/api/chats');
    if (chatsRes.ok) {
      renderChatList(await chatsRes.json());
    }
    
    selectChat(newChat.id);
  } catch (e) {
    console.error("Error creating chat:", e);
  }
}

async function selectChat(chatId) {
  currentChatId = chatId;
  try {
    const res = await fetch(`/api/chats/${chatId}`);
    if (!res.ok) return;
    const chat = await res.json();
    renderChatMessages(chat);

    // Update active highlight in sidebar
    const items = document.querySelectorAll('.chat-item');
    items.forEach(item => {
      if (item.dataset.chatId === chatId) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  } catch (e) {
    console.error("Error selecting chat:", e);
  }
}

async function deleteChat(chatId) {
  if (!confirm("Are you sure you want to delete this conversation?")) return;

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
  if (!viewport) return;
  viewport.innerHTML = '';

  if (!chat.messages || chat.messages.length === 0) {
    viewport.innerHTML = `
      <div class="welcome-card">
        <div class="welcome-icon">⚡</div>
        <h2>Welcome to QueryClarify</h2>
        <p>Connect your PostgreSQL database in Settings or ask natural language questions about the connected database.</p>
        <div class="welcome-grid">
          <div class="grid-item">
            <h4>Dynamic Ambiguity</h4>
            <p>Detects vague intent against your connected database schema.</p>
          </div>
          <div class="grid-item">
            <h4>SQLGlot Read-Only</h4>
            <p>Strictly blocks write/mutation queries (`DROP`, `DELETE`, `UPDATE`).</p>
          </div>
          <div class="grid-item">
            <h4>Custom Database</h4>
            <p>Connect any arbitrary PostgreSQL database via Settings.</p>
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
  if (event) event.preventDefault();
  if (isSubmitting) return;

  const input = document.getElementById('queryInput');
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;

  isSubmitting = true;
  input.value = '';

  try {
    if (!currentChatId) {
      await createNewChat();
    }

    appendUserMessageUI(text);
    const loadingCard = appendLoadingIndicator();

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
    if (loadingCard) loadingCard.remove();

    if (!res.ok) {
      appendErrorMessage(msg.detail || msg.message || "Failed to process query.");
      return;
    }

    appendAssistantMessageUI(msg);

    // Refresh chat titles without resetting active session view
    const chatsRes = await fetch('/api/chats');
    if (chatsRes.ok) {
      renderChatList(await chatsRes.json());
    }

  } catch (e) {
    appendErrorMessage("Failed to process request: " + e.message);
  } finally {
    isSubmitting = false;
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
    if (loadingCard) loadingCard.remove();

    if (!res.ok) {
      appendErrorMessage(msg.detail || msg.message || "Failed to submit clarification.");
      return;
    }

    appendAssistantMessageUI(msg);

  } catch (e) {
    if (loadingCard) loadingCard.remove();
    appendErrorMessage("Failed to submit clarification: " + e.message);
  }
}

function appendUserMessageUI(text) {
  const viewport = document.getElementById('chatViewport');
  if (!viewport) return;
  
  const welcomeCard = viewport.querySelector('.welcome-card');
  if (welcomeCard) welcomeCard.remove();

  const userMsg = document.createElement('div');
  userMsg.className = 'user-message';
  userMsg.textContent = text;
  viewport.appendChild(userMsg);
  viewport.scrollTop = viewport.scrollHeight;
}

function appendAssistantMessageUI(msg) {
  const viewport = document.getElementById('chatViewport');
  if (!viewport) return;
  
  const welcomeCard = viewport.querySelector('.welcome-card');
  if (welcomeCard) welcomeCard.remove();

  const aiCard = document.createElement('div');
  aiCard.className = 'ai-card';

  if (msg.status === 'clarification_required') {
    aiCard.innerHTML = `
      <div class="ambiguity-banner">
        <div class="ambiguity-header">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>Ambiguous Intent Detected (${escapeHtml(msg.ambiguity ? msg.ambiguity.ambiguity_type : 'Ambiguity')})</span>
        </div>
        <p class="ambiguity-reason">${escapeHtml(msg.ambiguity ? msg.ambiguity.reason : '')}</p>
        <div class="ambiguity-question">${escapeHtml(msg.clarification_question || '')}</div>
        <div class="options-grid" id="opts-${msg.id}"></div>
      </div>
    `;

    viewport.appendChild(aiCard);

    const optsContainer = aiCard.querySelector(`#opts-${msg.id}`);
    if (optsContainer && msg.clarification_options) {
      msg.clarification_options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'btn-option';
        btn.type = 'button';
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
    if (msg.rows && msg.rows.length > 0 && msg.columns && msg.columns.length > 0) {
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
        <div class="metric-item">Execution Latency: <span>${msg.execution_time_ms ? msg.execution_time_ms + ' ms' : 'N/A'}</span></div>
        <div class="metric-item">Rows Returned: <span>${msg.row_count !== undefined && msg.row_count !== null ? msg.row_count : 0}</span></div>
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
  if (!viewport) return null;
  const card = document.createElement('div');
  card.className = 'ai-card';
  card.innerHTML = `<div class="summary-box">Thinking, inspecting schema, and analyzing query...</div>`;
  viewport.appendChild(card);
  viewport.scrollTop = viewport.scrollHeight;
  return card;
}

function appendErrorMessage(errorMsg) {
  const viewport = document.getElementById('chatViewport');
  if (!viewport) return;
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

/* Modal Open / Close Logic */
function openSettingsModal() {
  const modal = document.getElementById('settingsModal');
  if (modal) modal.classList.add('active');
}

function closeSettingsModal() {
  const modal = document.getElementById('settingsModal');
  if (modal) modal.classList.remove('active');
}

function toggleSettingsModal() {
  const modal = document.getElementById('settingsModal');
  if (modal) modal.classList.toggle('active');
}

async function openSchemaModal() {
  const modal = document.getElementById('schemaModal');
  if (!modal) return;
  modal.classList.add('active');
  await loadDBSchema();
}

function closeSchemaModal() {
  const modal = document.getElementById('schemaModal');
  if (modal) modal.classList.remove('active');
}

async function toggleSchemaModal() {
  const modal = document.getElementById('schemaModal');
  if (!modal) return;
  if (modal.classList.contains('active')) {
    closeSchemaModal();
  } else {
    await openSchemaModal();
  }
}

async function testDBConnection() {
  const feedback = document.getElementById('dbFeedback');
  if (!feedback) return;
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
  if (!feedback) return;
  feedback.className = 'feedback-msg';
  feedback.style.display = 'block';
  feedback.textContent = "Connecting database...";

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
      setTimeout(closeSettingsModal, 1200);
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
    if (feedback) {
      feedback.className = 'feedback-msg success';
      feedback.textContent = "Disconnected custom DB. Reverted to demo database.";
    }
    updateHeaderStatus(false, "queryclarify (demo DB)");
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
    const schemaEl = document.getElementById('schemaText');
    if (schemaEl) schemaEl.textContent = data.schema_text;
    updateHeaderStatus(data.connected, data.database_name);
  } catch (e) {
    console.error("Error loading schema:", e);
  }
}

function updateHeaderStatus(isConnected, dbName) {
  const text = document.getElementById('statusText');
  if (text) text.textContent = `Connected to: ${dbName}`;
}

function getDBFormPayload() {
  return {
    host: (document.getElementById('dbHost') ? document.getElementById('dbHost').value : "") || "localhost",
    port: parseInt(document.getElementById('dbPort') ? document.getElementById('dbPort').value : 5432) || 5432,
    database: document.getElementById('dbName') ? document.getElementById('dbName').value : "",
    username: document.getElementById('dbUser') ? document.getElementById('dbUser').value : "",
    password: document.getElementById('dbPassword') ? document.getElementById('dbPassword').value : ""
  };
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
