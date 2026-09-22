/**
 * VTUva Academic Assistant Frontend Engine
 * Connects to FastAPI Backend RAG API & MySQL Chat History (/api/chat)
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM ELEMENTS
  const navHome = document.getElementById('nav-home');
  const navChat = document.getElementById('nav-chat');
  const homeView = document.getElementById('home-view');
  const chatView = document.getElementById('chat-view');
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const messagesList = document.getElementById('messages-list');
  const chatMessagesContainer = document.getElementById('chat-messages-container');
  const newChatBtn = document.getElementById('new-chat-btn');
  const globalSearchTrigger = document.getElementById('global-search-trigger');
  const searchModal = document.getElementById('search-modal');
  const modalSearchField = document.getElementById('modal-search-field');
  const toast = document.getElementById('toast');
  const recentChatsList = document.getElementById('recent-chats-list');
  const dashboardRecentQuestions = document.getElementById('dashboard-recent-questions');
  const refreshHistoryLink = document.getElementById('view-all-history-link');

  // STATE
  let currentView = 'home'; // 'home' | 'chat'
  let isStreaming = false;
  let chatHistoryCache = [];
  const currentUserId = '1';

  // API Configuration
  const API_BASE_URL = 'http://localhost:8000';

  // 1. VIEW SWITCHER
  function switchView(viewName) {
    currentView = viewName;
    if (viewName === 'home') {
      homeView.classList.add('active');
      chatView.classList.remove('active');
      navHome.classList.add('active');
      navChat.classList.remove('active');
    } else {
      homeView.classList.remove('active');
      chatView.classList.add('active');
      navHome.classList.remove('active');
      navChat.classList.add('active');
    }
  }

  navHome?.addEventListener('click', () => switchView('home'));
  navChat?.addEventListener('click', () => switchView('chat'));

  // 2. TOAST NOTIFICATION
  function showToast(message = 'Copied to clipboard') {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2200);
  }

  // 3. PROMPT PILL CARDS CLICK HANDLERS
  document.querySelectorAll('.prompt-pill-card').forEach(card => {
    card.addEventListener('click', () => {
      const promptText = card.getAttribute('data-prompt');
      if (promptText) {
        chatInput.value = promptText;
        handleSend();
      }
    });
  });

  // FEATURE CARDS CLICK HANDLERS
  document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('click', () => {
      const title = card.querySelector('.card-title')?.innerText || 'VTU Assistance';
      chatInput.value = `Help me with ${title}`;
      chatInput.focus();
    });
  });

  // 4. QUICK FILTER CHIPS TOGGLE
  document.querySelectorAll('.chip-btn').forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('active');
      const filterName = chip.querySelector('span')?.innerText;
      showToast(`${filterName} filter ${chip.classList.contains('active') ? 'enabled' : 'disabled'}`);
    });
  });

  // 5. GLOBAL SEARCH MODAL (CTRL K)
  function openSearchModal() {
    searchModal?.classList.add('show');
    modalSearchField?.focus();
  }

  function closeSearchModal() {
    searchModal?.classList.remove('show');
    if (modalSearchField) modalSearchField.value = '';
  }

  globalSearchTrigger?.addEventListener('click', openSearchModal);

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'K' || e.key === 'k')) {
      e.preventDefault();
      openSearchModal();
    }
    if (e.key === 'Escape') {
      closeSearchModal();
    }
  });

  searchModal?.addEventListener('click', (e) => {
    if (e.target === searchModal) closeSearchModal();
  });

  document.querySelectorAll('.search-result-item').forEach(item => {
    item.addEventListener('click', () => {
      closeSearchModal();
      switchView('chat');
      showToast('Action executed');
    });
  });

  // 6. CHAT INPUT AUTO-RESIZE & KEYDOWN
  chatInput?.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
  });

  chatInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  sendBtn?.addEventListener('click', handleSend);

  // 7. SEND MESSAGE & POST /api/chat INTEGRATION
  function handleSend() {
    const text = chatInput.value.trim();
    if (!text || isStreaming) return;

    // Switch to Chat View
    switchView('chat');

    // Append User Bubble
    const userWrapper = document.createElement('div');
    userWrapper.className = 'message-wrapper user';
    userWrapper.innerHTML = `
      <div class="user-bubble">
        <span>${escapeHtml(text)}</span>
      </div>
    `;
    messagesList.appendChild(userWrapper);

    // Reset Input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;

    // Fetch Answer from FastAPI RAG Backend and save to MySQL
    fetchRAGAnswer(text);
  }

  async function fetchRAGAnswer(promptText) {
    isStreaming = true;

    // Create Assistant Bubble with Loading Spinner
    const assistantWrapper = document.createElement('div');
    assistantWrapper.className = 'message-wrapper assistant';
    assistantWrapper.innerHTML = `
      <div class="assistant-content">
        <div class="text-stream">
          <div style="display: flex; align-items: center; gap: 10px; color: #818cf8; font-size: 14px; padding: 4px 0;">
            <svg class="spin-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation: spin 1s linear infinite;">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
            <span>VTUva is searching documents & thinking...</span>
          </div>
        </div>
      </div>
    `;
    messagesList.appendChild(assistantWrapper);
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;

    const streamTarget = assistantWrapper.querySelector('.text-stream');

    function scrollToBottom() {
      if (!chatMessagesContainer) return;
      chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': currentUserId,
        },
        body: JSON.stringify({ question: promptText }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedAnswer = '';
      let sources = [];
      let isFirstChunk = true;
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const payload = JSON.parse(line.slice(6));
              if (payload.type === 'sources') {
                sources = payload.sources || [];
              } else if (payload.type === 'token') {
                if (isFirstChunk) {
                  streamTarget.innerHTML = '';
                  isFirstChunk = false;
                }
                accumulatedAnswer += payload.token;
                streamTarget.innerHTML = renderMarkdown(accumulatedAnswer);
                scrollToBottom();
              }
            } catch (e) {
              // Partial JSON line
            }
          }
        }
      }

      // Process remaining buffer if any
      if (buffer && buffer.startsWith('data: ')) {
        try {
          const payload = JSON.parse(buffer.slice(6));
          if (payload.type === 'token') {
            if (isFirstChunk) {
              streamTarget.innerHTML = '';
              isFirstChunk = false;
            }
            accumulatedAnswer += payload.token;
          }
        } catch (e) {}
      }

      // Generate HTML for referenced sources
      let sourcesHtml = '';
      if (sources.length > 0) {
        sourcesHtml = `
          <details class="sources-details">
            <summary>
              <span style="display: flex; align-items: center; gap: 8px;">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
                Referenced VTU Documents (${sources.length})
              </span>
              <span class="details-badge">Click to view references ▾</span>
            </summary>
            <div style="padding: 10px 14px 14px 14px; border-top: 1px solid rgba(99, 102, 241, 0.15); background: rgba(13, 13, 16, 0.5);">
              <ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px;">
                ${sources.map(s => {
                  const safeName = escapeHtml(s.file_name);
                  const safeSnippet = escapeHtml(s.snippet || '').replace(/'/g, "\\'").replace(/\n/g, ' ');
                  const safePath = escapeHtml(s.file_path || '');
                  return `
                    <li class="source-item" onclick="openDocumentPreview('${safeName}', ${s.page}, '${safeSnippet}', '${safePath}')">
                      <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="color: #e2e8f0; font-weight: 500;">📄 <strong>${safeName}</strong> <span style="color: #94a3b8; font-weight: normal;">(Page ${s.page})</span></span>
                        <span style="font-size: 11px; color: #818cf8; text-decoration: underline;">View Context &rarr;</span>
                      </div>
                    </li>
                  `;
                }).join('')}
              </ul>
            </div>
          </details>
        `;
      }

      if (isFirstChunk) {
        streamTarget.innerHTML = renderMarkdown(accumulatedAnswer || "No answer generated.");
      } else {
        streamTarget.innerHTML = renderMarkdown(accumulatedAnswer) + sourcesHtml;
      }
      
      scrollToBottom();
      setTimeout(scrollToBottom, 60);
      isStreaming = false;
      loadChatHistory(); // Refresh history from MySQL

    } catch (err) {
      console.error("VTUva Chat API Error:", err);
      streamTarget.innerHTML = `
        <div style="color: #f87171; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); padding: 12px 16px; border-radius: 10px; font-size: 13.5px; line-height: 1.5;">
          <strong>⚠️ Unable to connect to VTUva Backend</strong><br/>
          ${escapeHtml(err.message)}<br/>
          <span style="font-size: 12px; color: #9ca3af; margin-top: 4px; display: inline-block;">
            Make sure FastAPI server & MySQL database are running: <code>python backend/main.py</code>.
          </span>
        </div>
      `;
      isStreaming = false;
    }
  }

  // 8. FETCH & RENDER CHAT HISTORY (GET /api/chat/history)
  async function loadChatHistory() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/history`, {
        headers: {
          'X-User-ID': currentUserId,
        }
      });
      if (!res.ok) return;

      const history = await res.json();
      chatHistoryCache = history;

      // Render Sidebar Recent Chats (Latest first)
      if (recentChatsList) {
        if (history.length === 0) {
          recentChatsList.innerHTML = `<li style="padding: 10px 14px; font-size: 12.5px; color: var(--text-muted);">No chat history yet</li>`;
        } else {
          const reversed = history.slice().reverse();
          recentChatsList.innerHTML = reversed.map(item => `
            <li class="recent-item" data-id="${item.id}" onclick="displayStoredChat(${item.id})">
              <svg class="recent-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
              <div class="recent-info">
                <div class="recent-title">${escapeHtml(item.question)}</div>
                <div class="recent-time">${formatTimeAgo(item.created_at)}</div>
              </div>
            </li>
          `).join('');
        }
      }

      // Render Dashboard Recent Questions
      if (dashboardRecentQuestions) {
        if (history.length === 0) {
          dashboardRecentQuestions.innerHTML = `<div style="color: var(--text-sub); font-size: 13.5px; padding: 8px 0;">No previous questions found. Ask a question below!</div>`;
        } else {
          dashboardRecentQuestions.innerHTML = history.map((item, index) => `
            <div class="recent-question-card">
              <div class="recent-question-info">
                <span class="question-number">${index + 1}.</span>
                <span class="question-text">${escapeHtml(item.question)}</span>
              </div>
              <button class="btn-view-answer" onclick="displayStoredChat(${item.id})">View Answer</button>
            </div>
          `).join('');
        }
      }
    } catch (e) {
      console.error("Failed to load chat history:", e);
    }
  }

  // DISPLAY A STORED QUESTION & ANSWER IN CHAT VIEW
  window.displayStoredChat = function(chatId) {
    const item = chatHistoryCache.find(c => c.id === chatId);
    if (!item) return;

    switchView('chat');
    messagesList.innerHTML = `
      <div class="message-wrapper user">
        <div class="user-bubble">
          <span>${escapeHtml(item.question)}</span>
        </div>
      </div>
      <div class="message-wrapper assistant">
        <div class="assistant-content">
          <div class="text-stream">${renderMarkdown(item.answer)}</div>
        </div>
      </div>
    `;
    if (chatMessagesContainer) {
      chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }
  };

  refreshHistoryLink?.addEventListener('click', (e) => {
    e.preventDefault();
    loadChatHistory();
    showToast('Chat history updated');
  });

  function formatTimeAgo(dateString) {
    if (!dateString) return 'recently';
    const date = new Date(dateString);
    const diffSec = Math.floor((new Date() - date) / 1000);
    if (isNaN(diffSec) || diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  }

  // 9. MARKDOWN RENDERER
  function renderMarkdown(str) {
    if (!str) return '';
    let html = str;

    // Code blocks
    html = html.replace(/```(python|js|json|html|bash)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `
        <div class="code-block" style="background:#111115; border:1px solid #1a1a22; border-radius:10px; margin:14px 0; overflow:hidden;">
          <div style="background:#1a1a22; padding:6px 14px; display:flex; justify-content:space-between; align-items:center; font-size:12px; color:#9ca3af;">
            <span>${(lang || 'code').toUpperCase()}</span>
            <button class="copy-code-btn" style="background:rgba(255,255,255,0.06); border:none; color:#cbd5e1; padding:3px 8px; border-radius:4px; cursor:pointer; font-size:11px;" onclick="navigator.clipboard.writeText(\`${escapeHtml(code).replace(/`/g, '\\`')}\`); alert('Copied code!');">Copy</button>
          </div>
          <pre style="padding:14px; font-family:var(--font-mono); font-size:13px; color:#e2e8f0; overflow-x:auto; margin:0;"><code>${escapeHtml(code)}</code></pre>
        </div>
      `;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; font-family:var(--font-mono); font-size:12.5px;">$1</code>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Headings ###
    html = html.replace(/### (.*?)\n/g, '<h3 style="font-size:16px; font-weight:600; margin:14px 0 6px 0; color:#f3f4f6;">$1</h3>');
    html = html.replace(/## (.*?)\n/g, '<h2 style="font-size:18px; font-weight:700; margin:16px 0 8px 0; color:#f3f4f6;">$1</h2>');

    // Bullet points
    html = html.replace(/^\s*[\-\*]\s+(.*)$/gm, '<li style="margin-left:18px; margin-bottom:4px;">$1</li>');

    // Line breaks
    html = html.replace(/\n\n/g, '<br/><br/>');

    return html;
  }

  function escapeHtml(string) {
    return String(string)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // 10. NEW CHAT RESET
  newChatBtn?.addEventListener('click', () => {
    messagesList.innerHTML = '';
    switchView('home');
    if (chatInput) chatInput.value = '';
    showToast('Started new chat');
  });

  // 11. DOCUMENT PREVIEW MODAL HANDLER
  const docModal = document.getElementById('doc-modal');
  const docModalFilename = document.getElementById('doc-modal-filename');
  const docModalPagebadge = document.getElementById('doc-modal-pagebadge');
  const docModalSnippet = document.getElementById('doc-modal-snippet');
  const docModalOpenLink = document.getElementById('doc-modal-open-link');
  const docModalCloseBtn = document.getElementById('doc-modal-close-btn');

  window.openDocumentPreview = function(fileName, page, snippet, filePath) {
    if (!docModal) return;
    docModalFilename.textContent = fileName;
    docModalPagebadge.textContent = `Page ${page}`;
    docModalSnippet.textContent = snippet || "No excerpt text available for this document page.";
    docModalOpenLink.href = filePath ? `${filePath}#page=${page}` : '#';
    docModal.classList.add('show');
  };

  docModalCloseBtn?.addEventListener('click', () => {
    docModal?.classList.remove('show');
  });

  docModal?.addEventListener('click', (e) => {
    if (e.target === docModal) {
      docModal.classList.remove('show');
    }
  });

  // INITIAL LOAD
  loadChatHistory();
});
