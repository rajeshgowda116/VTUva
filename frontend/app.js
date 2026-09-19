/**
 * VTUva Frontend Application Engine
 * Pure ES6 JS for state management, streaming typing, code execution simulation, and UI actions.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM ELEMENTS
  const sidebar = document.getElementById('sidebar');
  const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
  const openSidebarBtn = document.getElementById('open-sidebar-btn');
  const newChatBtn = document.getElementById('new-chat-btn');
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const sendIcon = sendBtn.querySelector('.send-icon');
  const stopIcon = sendBtn.querySelector('.stop-icon');
  const messagesContainer = document.getElementById('messages-container');
  const messagesList = document.getElementById('messages-list');
  const toast = document.getElementById('toast');
  const attachBtn = document.getElementById('attach-btn');
  const attachmentMenu = document.getElementById('attachment-menu');
  const attachFileOpt = document.getElementById('attach-file-opt');
  const attachImgOpt = document.getElementById('attach-img-opt');
  const fileInputElement = document.getElementById('file-input-element');
  const contextTag = document.getElementById('context-tag');
  const thinkToggle = document.getElementById('think-toggle');

  // STATE
  let isStreaming = false;
  let currentStreamingInterval = null;
  let isThinkingActive = false;
  let currentChatId = 'r1';

  // 1. SIDEBAR TOGGLE & SHORTCUTS
  function toggleSidebar() {
    if (window.innerWidth <= 768) {
      sidebar.classList.toggle('open');
    } else {
      sidebar.classList.toggle('collapsed');
    }
  }

  toggleSidebarBtn?.addEventListener('click', toggleSidebar);
  openSidebarBtn?.addEventListener('click', toggleSidebar);

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'S' || e.key === 's')) {
      e.preventDefault();
      toggleSidebar();
    }
  });

  // 2. AUTO-RESIZING TEXTAREA INPUT
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 180) + 'px';
  });

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  sendBtn.addEventListener('click', () => {
    if (isStreaming) {
      stopStreaming();
    } else {
      handleSend();
    }
  });

  // 3. TOAST NOTIFICATION
  function showToast(message = 'Copied to clipboard') {
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2200);
  }

  // 4. ATTACHMENT MENU MODAL
  attachBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    attachmentMenu.classList.toggle('show');
  });

  document.addEventListener('click', () => {
    attachmentMenu.classList.remove('show');
  });

  attachFileOpt?.addEventListener('click', () => {
    fileInputElement.click();
  });
  attachImgOpt?.addEventListener('click', () => {
    fileInputElement.click();
  });

  fileInputElement?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      contextTag.textContent = `Attached: ${file.name}`;
      contextTag.style.display = 'block';
      showToast(`Attached ${file.name}`);
    }
  });

  // 5. THINK TOGGLE BUTTON
  thinkToggle?.addEventListener('click', () => {
    isThinkingActive = !isThinkingActive;
    thinkToggle.classList.toggle('active', isThinkingActive);
    showToast(isThinkingActive ? 'Think mode enabled' : 'Think mode disabled');
  });

  // 6. CODE BLOCK COPY & RUN ACTIONS
  document.addEventListener('click', (e) => {
    // Copy Code Button
    const copyBtn = e.target.closest('.copy-code-btn');
    if (copyBtn) {
      const codeBlock = copyBtn.closest('.code-block');
      const codeText = codeBlock.querySelector('code').innerText;
      navigator.clipboard.writeText(codeText).then(() => {
        showToast('Code copied to clipboard');
      });
      return;
    }

    // Run Code Button
    const runBtn = e.target.closest('.run-code-btn');
    if (runBtn) {
      const targetId = runBtn.getAttribute('data-target');
      const codeBlock = document.getElementById(targetId) || runBtn.closest('.code-block');
      simulateCodeExecution(codeBlock);
      return;
    }

    // Output Copy Button
    const outputCopyBtn = e.target.closest('.output-copy-btn');
    if (outputCopyBtn) {
      const outputText = outputCopyBtn.previousElementSibling.innerText;
      navigator.clipboard.writeText(outputText).then(() => {
        showToast('Output copied to clipboard');
      });
      return;
    }

    // Chat Item Click (Sidebar)
    const chatItem = e.target.closest('.chat-item');
    if (chatItem) {
      document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
      chatItem.classList.add('active');
      currentChatId = chatItem.getAttribute('data-id');
    }
  });

  // 7. SIMULATE CODE EXECUTION (RUN BUTTON)
  function simulateCodeExecution(codeBlock) {
    if (!codeBlock) return;
    
    const codeText = codeBlock.querySelector('code').innerText;
    let existingOutputContainer = codeBlock.querySelector('.code-output-container');
    
    if (!existingOutputContainer) {
      existingOutputContainer = document.createElement('div');
      existingOutputContainer.className = 'code-output-container';
      existingOutputContainer.innerHTML = `
        <div class="output-header">Output</div>
        <div class="output-box">
          <span class="output-text">Running code...</span>
          <button class="output-copy-btn" title="Copy output">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
          </button>
        </div>
      `;
      codeBlock.appendChild(existingOutputContainer);
    } else {
      existingOutputContainer.querySelector('.output-text').textContent = 'Running code...';
    }

    // Simulate stdout response
    setTimeout(() => {
      let resultText = '';
      if (codeText.includes('file.exists()')) {
        resultText = 'data/pdf/frist_sem\nTrue';
      } else if (codeText.includes('file')) {
        resultText = 'data/pdf/frist_sem';
      } else {
        resultText = '[Executed successfully]';
      }
      existingOutputContainer.querySelector('.output-text').textContent = resultText;
      showToast('Execution finished');
    }, 600);
  }

  // 8. SEND MESSAGE & STREAMING TYPING ANIMATION
  function handleSend() {
    const text = chatInput.value.trim();
    if (!text || isStreaming) return;

    // Append User Bubble
    const userWrapper = document.createElement('div');
    userWrapper.className = 'message-wrapper user';
    userWrapper.innerHTML = `
      <div class="user-bubble">
        <pre><code>${escapeHtml(text)}</code></pre>
      </div>
    `;
    messagesList.appendChild(userWrapper);

    // Reset Input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Start AI Response Stream
    startAIResponseStream(text);
  }

  async function startAIResponseStream(userPrompt) {
    isStreaming = true;
    sendIcon.style.display = 'none';
    stopIcon.style.display = 'block';

    const assistantWrapper = document.createElement('div');
    assistantWrapper.className = 'message-wrapper assistant';
    
    const blockId = 'code-block-' + Date.now();

    let responseHTML = ``;
    if (isThinkingActive) {
      responseHTML += `
        <div class="thinking-accordion" style="background:#1a1a1e; border:1px solid #2d2d35; border-radius:8px; padding:10px 14px; margin-bottom:12px; font-size:13px; color:#a1a1aa;">
          <div style="display:flex; align-items:center; gap:6px; font-weight:500;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
            <span>Searching documents & generating answer...</span>
          </div>
        </div>
      `;
    }

    responseHTML += `<div class="assistant-content"><div class="text-stream"></div><span class="streaming-dot" id="active-streaming-dot">•••</span></div>`;
    assistantWrapper.innerHTML = responseHTML;
    messagesList.appendChild(assistantWrapper);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    const streamTarget = assistantWrapper.querySelector('.text-stream');

    let answerText = "";
    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: userPrompt })
      });

      if (response.ok) {
        const data = await response.json();
        answerText = data.answer || "No answer returned.";
      } else {
        const errData = await response.json().catch(() => ({}));
        answerText = errData.detail || `Error ${response.status}: Failed to retrieve answer.`;
      }
    } catch (err) {
      answerText = "⚠️ Unable to connect to backend server. Make sure FastAPI server is running.";
    }

    // Typewriter effect to display answer on screen
    let charIndex = 0;
    currentStreamingInterval = setInterval(() => {
      if (charIndex < answerText.length) {
        charIndex += 4;
        const currentChunk = answerText.substring(0, charIndex);
        streamTarget.innerHTML = renderMarkdown(currentChunk, blockId);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      } else {
        streamTarget.innerHTML = renderMarkdown(answerText, blockId);
        stopStreaming();
      }
    }, 20);
  }

  function stopStreaming() {
    if (currentStreamingInterval) clearInterval(currentStreamingInterval);
    isStreaming = false;
    sendIcon.style.display = 'block';
    stopIcon.style.display = 'none';
    const activeDot = document.getElementById('active-streaming-dot');
    if (activeDot) activeDot.remove();
  }

  // 9. SIMPLE MARKDOWN & CODE BLOCK PARSER
  function renderMarkdown(str, blockId) {
    let html = str;
    
    // Code block parser ```python ... ```
    html = html.replace(/```(python|js|json|html|bash)?\n([\s\S]*?)```/g, (match, lang, code) => {
      const language = lang || 'python';
      return `
        <div class="code-block" id="${blockId}">
          <div class="code-header">
            <div class="code-lang">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
              <span>${language.toUpperCase()}</span>
            </div>
            <div class="code-actions">
              <button class="code-btn copy-code-btn" title="Copy code">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
              </button>
              <button class="code-btn run-code-btn" data-target="${blockId}" title="Run code">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                <span>Run</span>
              </button>
            </div>
          </div>
          <div class="code-content">
            <pre><code class="language-${language}">${highlightSyntax(code)}</code></pre>
          </div>
        </div>
      `;
    });

    // Bold text **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    return html;
  }

  function highlightSyntax(code) {
    return escapeHtml(code)
      .replace(/\b(from|import|def|return|if|else|for|while|in|as|class|True|False)\b/g, '<span class="kw">$1</span>')
      .replace(/(".*?"|'.*? me')/g, '<span class="str">$1</span>')
      .replace(/\b(print|Path|exists|is_dir|open)\b/g, '<span class="fn">$1</span>');
  }

  function escapeHtml(string) {
    return String(string)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // 10. NEW CHAT CREATION
  newChatBtn?.addEventListener('click', () => {
    messagesList.innerHTML = '';
    const newChatId = 'r' + Date.now();
    const recentList = document.getElementById('recent-chats');
    
    const newLi = document.createElement('li');
    newLi.className = 'chat-item active';
    newLi.setAttribute('data-id', newChatId);
    newLi.innerHTML = `<span class="chat-title">New Conversation</span>`;
    
    document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
    recentList.prepend(newLi);
    
    showToast('Created new chat');
  });
});
