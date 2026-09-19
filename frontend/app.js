/**
 * VTUva Academic Assistant Frontend Engine
 * Pure ES6 JS for state management, view switching, prompt triggers, quick filter chips, and AI streaming.
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
    searchModal.classList.add('show');
    modalSearchField.focus();
  }

  function closeSearchModal() {
    searchModal.classList.remove('show');
    modalSearchField.value = '';
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
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
  });

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  sendBtn.addEventListener('click', handleSend);

  // 7. SEND MESSAGE & STREAMING ENGINE
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

    // Trigger AI Stream
    startAISolutionStream(text);
  }

  function startAISolutionStream(promptText) {
    isStreaming = true;

    const assistantWrapper = document.createElement('div');
    assistantWrapper.className = 'message-wrapper assistant';
    
    assistantWrapper.innerHTML = `
      <div class="assistant-content">
        <div class="text-stream"></div>
        <span class="streaming-dot" style="display:inline-block; font-size:18px; color:#818cf8; animation:pulse 1.2s infinite;">•••</span>
      </div>
    `;
    messagesList.appendChild(assistantWrapper);
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;

    const streamTarget = assistantWrapper.querySelector('.text-stream');

    // Generate Smart Academic Answer tailored to VTU
    const sampleAnswer = `Here is the comprehensive explanation for **"${escapeHtml(promptText)}"** based on the official **VTU Syllabus**:

### 📌 Overview & Concept
In **VTU Academic Curriculum**, understanding key concepts with clear diagrams and structured answers is vital for securing high marks.

\`\`\`python
# VTU Solution Code Snippet
def calculate_complexity(n):
    # Time Complexity: O(N log N)
    return [i ** 2 for i in range(n)]

print("VTU Solution Output:", calculate_complexity(5))
\`\`\`

### 💡 Key Points for Exam (5-10 Marks Format):
1. **Definition & Core Principle**: State the exact textbook definition first.
2. **Architecture / Diagram**: Always draw neat block diagrams.
3. **Step-by-Step Explanation**: Use bullet points and mathematical equations where required.
4. **Time & Space Complexity**: Mention algorithmic complexity if applicable.

Feel free to ask follow-up questions or request Previous Year Questions (PYQs) for this topic!`;

    let index = 0;
    const interval = setInterval(() => {
      if (index < sampleAnswer.length) {
        index += 3;
        streamTarget.innerHTML = renderMarkdown(sampleAnswer.substring(0, index));
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
      } else {
        clearInterval(interval);
        isStreaming = false;
        const dot = assistantWrapper.querySelector('.streaming-dot');
        if (dot) dot.remove();
      }
    }, 25);
  }

  // 8. MARKDOWN RENDERER
  function renderMarkdown(str) {
    let html = str;
    // Code blocks
    html = html.replace(/```(python|js|json|html)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `
        <div class="code-block" style="background:#111115; border:1px solid #1a1a22; border-radius:10px; margin:14px 0; overflow:hidden;">
          <div style="background:#1a1a22; padding:6px 14px; display:flex; justify-content:space-between; font-size:12px; color:#9ca3af;">
            <span>${(lang || 'code').toUpperCase()}</span>
            <button class="copy-code-btn" style="background:transparent; border:none; color:#9ca3af; cursor:pointer;" onclick="navigator.clipboard.writeText(\`${escapeHtml(code)}\`); alert('Copied!');">Copy</button>
          </div>
          <pre style="padding:14px; font-family:var(--font-mono); font-size:13px; color:#e2e8f0; overflow-x:auto;"><code>${escapeHtml(code)}</code></pre>
        </div>
      `;
    });
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Headings ###
    html = html.replace(/### (.*?)\n/g, '<h3 style="font-size:16px; margin:12px 0 6px 0; color:#f3f4f6;">$1</h3>');
    
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
    chatInput.value = '';
    showToast('Started new chat');
  });

  // 10. RECENT ITEM CLICK
  document.querySelectorAll('.recent-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.recent-item').forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      const title = item.querySelector('.recent-title')?.innerText;
      switchView('chat');
      if (messagesList.children.length === 0) {
        startAISolutionStream(title);
      }
    });
  });
});
