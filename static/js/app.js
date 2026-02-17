/**
 * app.js
 * Nexus frontend — communicates with the Python HTTP backend.
 * Manages UI state, uploads, mode switching, and chat.
 */

(function () {
  'use strict';

  // ── State ────────────────────────────────────────────────────────────
  const state = {
    mode:       'general',
    streaming:  false,
    queryCount: 0,
    modes:      {},   // fetched from /api/modes
  };

  // ── DOM refs ─────────────────────────────────────────────────────────
  const $ = id => document.getElementById(id);

  const apiKeyInput    = $('apiKeyInput');
  const toggleKeyBtn   = $('toggleKey');
  const uploadZone     = $('uploadZone');
  const fileInput      = $('fileInput');
  const docListEl      = $('docList');
  const processBtn     = $('processBtn');
  const processingWrap = $('processingWrap');
  const modeGrid       = $('modeGrid');
  const promptChipsEl  = $('promptChips');
  const streamEl       = $('stream');
  const welcome        = $('welcome');
  const userInput      = $('userInput');
  const sendBtn        = $('sendBtn');
  const clearBtn       = $('clearBtn');
  const modePill       = $('modePill');
  const docCountEl     = $('docCount');
  const msgCountEl     = $('msgCount');
  const charCountEl    = $('charCount');
  const notifyEl       = $('notify');

  // ── Init ─────────────────────────────────────────────────────────────
  async function init() {
    _restoreKey();
    await _loadModes();
    _bindEvents();
    await _refreshDocList();
    console.log('%cNexus Bot ready', 'color:#c8f562;font-weight:bold;');
  }

  // ── Load modes from server ────────────────────────────────────────────
  async function _loadModes() {
    try {
      const res  = await fetch('/api/modes');
      const data = await res.json();
      if (data.ok) {
        state.modes = data.modes;
        _renderChips(state.mode);
      }
    } catch (e) {
      console.warn('Could not load modes:', e);
    }
  }

  // ── Event bindings ───────────────────────────────────────────────────
  function _bindEvents() {
    // API key toggle
    toggleKeyBtn.addEventListener('click', () => {
      const hidden = apiKeyInput.type === 'password';
      apiKeyInput.type  = hidden ? 'text' : 'password';
      toggleKeyBtn.textContent = hidden ? '🙈' : '👁';
    });

    // Persist key in sessionStorage
    apiKeyInput.addEventListener('input', () =>
      sessionStorage.setItem('nexus_key', apiKeyInput.value)
    );

    // Upload
    uploadZone.addEventListener('dragover', e => {
      e.preventDefault(); uploadZone.classList.add('drag-over');
    });
    uploadZone.addEventListener('dragleave', () =>
      uploadZone.classList.remove('drag-over')
    );
    uploadZone.addEventListener('drop', e => {
      e.preventDefault();
      uploadZone.classList.remove('drag-over');
      _uploadFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', () => {
      _uploadFiles(fileInput.files);
      fileInput.value = '';
    });

    // Ingest
    processBtn.addEventListener('click', _ingestDocs);

    // Mode buttons
    modeGrid.querySelectorAll('.mode-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        modeGrid.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.mode = btn.dataset.mode;
        const label = (state.modes[state.mode] || {}).label || state.mode;
        modePill.textContent = label;
        _renderChips(state.mode);
      });
    });

    // Send button & keyboard
    sendBtn.addEventListener('click', _handleSend);
    userInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); _handleSend(); }
    });
    userInput.addEventListener('input', _updateInput);

    // Clear
    clearBtn.addEventListener('click', async () => {
      if (!confirm('Clear conversation history?')) return;
      await fetch('/api/clear', { method: 'POST' });
      streamEl.innerHTML = '';
      streamEl.appendChild(welcome);
      welcome.style.display = 'flex';
      state.queryCount = 0;
      msgCountEl.textContent = '0 Queries';
    });

    // Ctrl+/ focus shortcut
    document.addEventListener('keydown', e => {
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault(); userInput.focus();
      }
    });
  }

  // ── Restore API key ───────────────────────────────────────────────────
  function _restoreKey() {
    const saved = sessionStorage.getItem('nexus_key');
    if (saved) apiKeyInput.value = saved;
  }

  // ── Upload files to Python backend ────────────────────────────────────
  async function _uploadFiles(files) {
    if (!files || files.length === 0) return;

    const form = new FormData();
    for (const f of files) form.append('file', f);

    try {
      const res  = await fetch('/api/upload', { method: 'POST', body: form });
      const data = await res.json();

      if (!data.ok) { _notify(data.error, 'error'); return; }

      data.results.forEach(r => _notify(r.message, r.ok ? 'success' : 'warn'));
      _renderDocList(data.documents);
      processBtn.disabled = data.documents.length === 0;

    } catch (e) {
      _notify('Upload failed: ' + e.message, 'error');
    }
  }

  // ── Refresh doc list from server ──────────────────────────────────────
  async function _refreshDocList() {
    try {
      const res  = await fetch('/api/documents');
      const data = await res.json();
      if (data.ok) {
        _renderDocList(data.documents);
        processBtn.disabled = data.documents.length === 0;
        if (data.ingested)
          processBtn.textContent = '✅ Re-ingest Documents';
      }
    } catch (_) {}
  }

  // ── Render document list ──────────────────────────────────────────────
  function _renderDocList(docs) {
    docListEl.innerHTML = '';
    docCountEl.textContent = `${docs.length} Document${docs.length !== 1 ? 's' : ''}`;

    docs.forEach(doc => {
      const el      = document.createElement('div');
      el.className  = 'doc-item';
      el.innerHTML  = `
        <span class="doc-name" title="${_esc(doc.name)}">📄 ${_esc(doc.name)}</span>
        <span class="doc-badge">${_esc(doc.size_label)}</span>
        <button class="doc-remove" data-name="${_esc(doc.name)}" title="Remove">✕</button>
      `;
      el.querySelector('.doc-remove').addEventListener('click', () => _removeDoc(doc.name));
      docListEl.appendChild(el);
    });
  }

  // ── Remove document ───────────────────────────────────────────────────
  async function _removeDoc(name) {
    try {
      const res  = await fetch('/api/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (data.ok) {
        _notify(`Removed: ${name}`, 'success');
        _renderDocList(data.documents);
        processBtn.disabled = data.documents.length === 0;
        if (data.documents.length === 0)
          processBtn.textContent = '⚡ Ingest Documents';
      } else {
        _notify(data.error, 'error');
      }
    } catch (e) {
      _notify('Remove failed: ' + e.message, 'error');
    }
  }

  // ── Ingest documents ──────────────────────────────────────────────────
  async function _ingestDocs() {
    processBtn.disabled          = true;
    processingWrap.style.display = 'block';

    try {
      const res  = await fetch('/api/ingest', { method: 'POST' });
      const data = await res.json();

      processingWrap.style.display = 'none';

      if (data.ok) {
        processBtn.textContent = '✅ Re-ingest Documents';
        processBtn.disabled    = false;
        _notify(data.message, 'success');
      } else {
        processBtn.disabled = false;
        _notify(data.error, 'error');
      }
    } catch (e) {
      processingWrap.style.display = 'none';
      processBtn.disabled = false;
      _notify('Ingest failed: ' + e.message, 'error');
    }
  }

  // ── Render quick chips ─────────────────────────────────────────────────
  function _renderChips(mode) {
    promptChipsEl.innerHTML = '';
    const modeData = state.modes[mode];
    if (!modeData) return;

    modeData.chips.forEach(text => {
      const btn     = document.createElement('button');
      btn.className = 'chip';
      btn.textContent = text;
      btn.addEventListener('click', () => {
        userInput.value = text;
        _updateInput();
        userInput.focus();
      });
      promptChipsEl.appendChild(btn);
    });
  }

  // ── Send message ──────────────────────────────────────────────────────
  async function _handleSend() {
    const query = userInput.value.trim();
    if (!query || state.streaming) return;

    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
      _notify('Please enter your OpenRouter API key', 'error');
      apiKeyInput.focus();
      return;
    }

    // Hide welcome
    if (welcome) welcome.style.display = 'none';

    // Append user message
    _appendMessage('user', query);
    userInput.value = '';
    _updateInput();

    state.queryCount++;
    msgCountEl.textContent = `${state.queryCount} Quer${state.queryCount !== 1 ? 'ies' : 'y'}`;

    state.streaming  = true;
    sendBtn.disabled = true;
    const typingEl   = _appendTyping();

    try {
      const res  = await fetch('/api/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, query, mode: state.mode }),
      });
      const data = await res.json();

      typingEl.remove();

      if (data.ok) {
        _appendMessage('assistant', data.reply);
      } else {
        _appendMessage('assistant', '⚠️ ' + data.error, true);
        _notify(data.error, 'error');
      }

    } catch (e) {
      typingEl.remove();
      _appendMessage('assistant', '⚠️ Network error: ' + e.message, true);
      _notify('Network error: ' + e.message, 'error');
    }

    state.streaming  = false;
    sendBtn.disabled = false;
    userInput.focus();
  }

  // ── Append message bubble ─────────────────────────────────────────────
  function _appendMessage(role, text, isError = false) {
    const div       = document.createElement('div');
    div.className   = `msg ${role}`;
    const avatar    = role === 'user' ? 'U' : '⚡';
    const label     = role === 'user' ? 'You' : 'Nexus · Nemotron 12B';

    div.innerHTML = `
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-body">
        <div class="msg-role">${label}</div>
        <div class="msg-bubble${isError ? ' is-error' : ''}">${Renderer.render(text)}</div>
      </div>`;

    streamEl.appendChild(div);
    streamEl.scrollTop = streamEl.scrollHeight;
  }

  // ── Typing indicator ──────────────────────────────────────────────────
  function _appendTyping() {
    const div     = document.createElement('div');
    div.className = 'msg assistant';
    div.innerHTML = `
      <div class="msg-avatar">⚡</div>
      <div class="msg-body">
        <div class="msg-role">Nexus · Nemotron 12B</div>
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>`;
    streamEl.appendChild(div);
    streamEl.scrollTop = streamEl.scrollHeight;
    return div;
  }

  // ── Input helpers ─────────────────────────────────────────────────────
  function _updateInput() {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
    const len = userInput.value.length;
    charCountEl.textContent = `${len} char${len !== 1 ? 's' : ''}`;
  }

  // ── Toast notifications ───────────────────────────────────────────────
  const ICONS = { success: '✅', error: '❌', warn: '⚠️' };

  function _notify(msg, type = 'success', ms = 3500) {
    const el      = document.createElement('div');
    el.className  = `notif ${type}`;
    el.innerHTML  = `<span>${ICONS[type] || 'ℹ️'}</span><span>${_esc(String(msg))}</span>`;
    notifyEl.appendChild(el);
    setTimeout(() => {
      el.style.opacity   = '0';
      el.style.transform = 'translateX(20px)';
      setTimeout(() => el.remove(), 220);
    }, ms);
  }

  // ── HTML escaper ──────────────────────────────────────────────────────
  function _esc(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Boot ──────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);

})();
