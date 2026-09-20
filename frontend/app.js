/**
 * VTUva Academic Assistant Frontend Engine
 * Connects to FastAPI Backend RAG API (http://localhost:8000/ask)
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

  // STATE
  let currentView = 'home'; // 'home' | 'chat'
  let isStreaming = false;

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

  // 7. SEND MESSAGE & RAG API INTEGRATION
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

    // Fetch Answer from FastAPI RAG Backend
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

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: promptText }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status ${response.status}`);
      }

      const data = await response.json();
      const answerText = data.answer || "No information returned from VTUva.";
      const sources = data.sources || [];

      // Generate HTML for referenced sources (Collapsible by default)
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

      // Smooth word-by-word streaming effect
      const words = answerText.split(' ');
      let currentWordIndex = 0;
      streamTarget.innerHTML = '';

      function scrollToBottom() {
        if (!chatMessagesContainer) return;
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
      }

      const interval = setInterval(() => {
        if (currentWordIndex < words.length) {
          currentWordIndex += 3;
          const chunk = words.slice(0, currentWordIndex).join(' ');
          streamTarget.innerHTML = renderMarkdown(chunk);
          scrollToBottom();
        } else {
          clearInterval(interval);
          streamTarget.innerHTML = renderMarkdown(answerText) + sourcesHtml;
          scrollToBottom();
          setTimeout(scrollToBottom, 60);
          isStreaming = false;
        }
      }, 30);

    } catch (err) {
      console.error("VTUva RAG API Error:", err);
      streamTarget.innerHTML = `
        <div style="color: #f87171; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); padding: 12px 16px; border-radius: 10px; font-size: 13.5px; line-height: 1.5;">
          <strong>⚠️ Unable to connect to VTUva Backend</strong><br/>
          ${escapeHtml(err.message)}<br/>
          <span style="font-size: 12px; color: #9ca3af; margin-top: 4px; display: inline-block;">
            Make sure the FastAPI server is running: <code>python backend/main.py</code> (or <code>uvicorn backend.main:app --port 8000</code>).
          </span>
        </div>
      `;
      isStreaming = false;
    }
  }

  // 8. MARKDOWN RENDERER
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

  // 9. NEW CHAT RESET
  newChatBtn?.addEventListener('click', () => {
    messagesList.innerHTML = '';
    switchView('home');
    if (chatInput) chatInput.value = '';
    showToast('Started new chat');
  });

  // 10. RECENT ITEM CLICK
  document.querySelectorAll('.recent-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.recent-item').forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      const title = item.querySelector('.recent-title')?.innerText;
      switchView('chat');
      if (messagesList.children.length === 0 && title) {
        fetchRAGAnswer(title);
      }
    });
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
});
