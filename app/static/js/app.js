let currentSessionId = null;

function usePrompt(promptText) {
  document.getElementById('queryInput').value = promptText;
  document.getElementById('queryForm').dispatchEvent(new Event('submit'));
}

async function handleFormSubmit(event) {
  event.preventDefault();
  const input = document.getElementById('queryInput');
  const question = input.value.trim();
  if (!question) return;

  // Append user message to chat viewport
  appendUserMessage(question);
  input.value = '';

  // Show loading indicator
  const loadingCard = appendLoadingIndicator();

  try {
    const payload = {
      session_id: currentSessionId,
      question: question
    };

    const response = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    loadingCard.remove();

    renderQueryResponse(data, question);

  } catch (error) {
    loadingCard.remove();
    appendErrorMessage("Failed to connect to QueryClarify server: " + error.message);
  }
}

async function handleClarificationChoice(optionId, question) {
  const loadingCard = appendLoadingIndicator();

  try {
    const payload = {
      session_id: currentSessionId,
      question: question,
      selected_option: optionId
    };

    const response = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    loadingCard.remove();

    renderQueryResponse(data, question);

  } catch (error) {
    loadingCard.remove();
    appendErrorMessage("Failed to submit clarification: " + error.message);
  }
}

function renderQueryResponse(data, question) {
  currentSessionId = data.session_id;
  const viewport = document.getElementById('chatViewport');
  
  // Hide welcome card if visible
  const welcomeCard = document.querySelector('.welcome-card');
  if (welcomeCard) welcomeCard.style.display = 'none';

  const aiCard = document.createElement('div');
  aiCard.className = 'ai-card';

  if (data.status === 'clarification_required') {
    // Render Ambiguity & Clarification Card
    aiCard.innerHTML = `
      <div class="ambiguity-banner">
        <div class="ambiguity-header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>Ambiguous Intent Detected (${data.ambiguity.ambiguity_type || 'Ambiguity'})</span>
        </div>
        <p class="ambiguity-reason">${data.ambiguity.reason}</p>
        <div class="ambiguity-question">${data.clarification_question}</div>
        <div class="options-grid" id="opts-${data.session_id}"></div>
      </div>
    `;

    viewport.appendChild(aiCard);

    const optsContainer = aiCard.querySelector(`#opts-${data.session_id}`);
    data.clarification_options.forEach(opt => {
      const btn = document.createElement('button');
      btn.className = 'btn-option';
      btn.innerHTML = `
        <span class="option-label">${opt.label}</span>
        <span class="option-desc">${opt.description}</span>
      `;
      btn.onclick = () => handleClarificationChoice(opt.id, question);
      optsContainer.appendChild(btn);
    });

  } else if (data.status === 'completed') {
    // Render Completed SQL & Data Table Card
    let tableHtml = '';
    if (data.rows && data.rows.length > 0) {
      const headers = data.columns.map(c => `<th>${c}</th>`).join('');
      const rows = data.rows.map(row => {
        const cells = data.columns.map(c => `<td>${row[c] !== null ? row[c] : ''}</td>`).join('');
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
        <strong>Result:</strong> ${data.summary}
      </div>

      <div class="sql-section">
        <div class="sql-header">
          <span>Generated SQL Query</span>
          <span class="badge-safety">✓ SQLGlot Read-Only Verified</span>
        </div>
        <div class="sql-code">${escapeHtml(data.sql)}</div>
      </div>

      ${tableHtml}

      <div class="metrics-bar">
        <div class="metric-item">Execution Latency: <span>${data.execution_time_ms} ms</span></div>
        <div class="metric-item">Rows Returned: <span>${data.row_count}</span></div>
        <div class="metric-item">Tables Referenced: <span>${data.tables_used ? data.tables_used.join(', ') : 'None'}</span></div>
      </div>
    `;

    viewport.appendChild(aiCard);

  } else if (data.status === 'error') {
    appendErrorMessage(data.error || "An error occurred during query execution.");
    return;
  }

  viewport.scrollTop = viewport.scrollHeight;
}

function appendUserMessage(text) {
  const viewport = document.getElementById('chatViewport');
  const welcomeCard = document.querySelector('.welcome-card');
  if (welcomeCard) welcomeCard.style.display = 'none';

  const userMsg = document.createElement('div');
  userMsg.className = 'user-message';
  userMsg.textContent = text;
  viewport.appendChild(userMsg);
  viewport.scrollTop = viewport.scrollHeight;
}

function appendLoadingIndicator() {
  const viewport = document.getElementById('chatViewport');
  const card = document.createElement('div');
  card.className = 'ai-card';
  card.innerHTML = `<div class="summary-box">Thinking, detecting ambiguity, and inspecting schema...</div>`;
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

async function toggleSchemaModal() {
  const modal = document.getElementById('schemaModal');
  if (modal.classList.contains('active')) {
    modal.classList.remove('active');
  } else {
    modal.classList.add('active');
    try {
      const res = await fetch('/api/schema');
      const data = await res.json();
      document.getElementById('schemaText').textContent = data.schema;
    } catch (e) {
      document.getElementById('schemaText').textContent = "Failed to load schema.";
    }
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
