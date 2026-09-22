/**
 * AI Mentor Hermes — Frontend Controller
 * Manages Dual-State (50/50 Landing View vs In-Chat View with Collapsible Right Sidebar)
 * Dynamic conversational mentoring, template launchers, and conversation renaming.
 */

class CoachController {
  constructor() {
    this.conversations = [];
    this.activeConversationId = null;
    this.activeConversation = null;
    this.sidebarCollapsed = localStorage.getItem('hermes_sidebar_collapsed') === 'true';
    this.isSending = false;

    this.initElements();
    this.bindEvents();
  }

  initElements() {
    // Views
    this.landingView = document.getElementById('coach-landing-view');
    this.chatView = document.getElementById('coach-chat-view');

    // Landing View Elements
    this.landingHistoryList = document.getElementById('landing-history-list');
    this.landingCountBadge = document.getElementById('landing-count-badge');
    this.btnStartChatMain = document.getElementById('btn-start-chat-main');
    this.templateCards = document.querySelectorAll('.coach-template-card');

    // In-Chat View Elements
    this.btnBackToLanding = document.getElementById('btn-back-to-landing');
    this.btnBurgerMenu = document.getElementById('btn-burger-menu');
    this.chatTitle = document.getElementById('chat-current-title');
    this.btnRenameActiveChat = document.getElementById('btn-rename-active-chat');
    this.chatTopicTag = document.getElementById('chat-topic-tag');
    this.messagesArea = document.getElementById('chat-messages-area');
    this.chatInput = document.getElementById('chat-input-textarea');
    this.btnSendMessage = document.getElementById('btn-send-message');
    
    // Right Sidebar Elements
    this.sidebarRight = document.getElementById('coach-sidebar-right');
    this.sidebarHistoryList = document.getElementById('sidebar-history-list');
    this.btnNewChatSmall = document.getElementById('btn-new-chat-small');
  }

  bindEvents() {
    // Start fresh chat from main landing button
    if (this.btnStartChatMain) {
      this.btnStartChatMain.addEventListener('click', () => this.handleLaunchSession(null));
    }

    // Launch chat from template cards
    if (this.templateCards) {
      this.templateCards.forEach(card => {
        card.addEventListener('click', () => {
          const prompt = card.getAttribute('data-prompt') || card.querySelector('strong')?.textContent.trim();
          this.handleLaunchSession(prompt);
        });
      });
    }

    // Return to 50/50 landing view
    if (this.btnBackToLanding) {
      this.btnBackToLanding.addEventListener('click', () => this.showLandingView());
    }

    // Rename active conversation
    if (this.btnRenameActiveChat) {
      this.btnRenameActiveChat.addEventListener('click', () => {
        if (this.activeConversation) {
          this.handleRenameConversation(this.activeConversation.id, this.activeConversation.title);
        }
      });
    }

    // Toggle collapsible right sidebar (burger menu)
    if (this.btnBurgerMenu) {
      this.btnBurgerMenu.addEventListener('click', () => this.toggleSidebar());
    }

    // New Chat button from in-chat sidebar
    if (this.btnNewChatSmall) {
      this.btnNewChatSmall.addEventListener('click', () => this.showLandingView());
    }

    // Chat input auto-expand & keyboard shortcut
    if (this.chatInput) {
      this.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
        }
      });
      this.chatInput.addEventListener('input', () => {
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 140) + 'px';
      });
    }

    // Send button
    if (this.btnSendMessage) {
      this.btnSendMessage.addEventListener('click', () => this.handleSendMessage());
    }

    // Handle browser back/forward buttons
    window.addEventListener('popstate', () => {
      this.checkUrlState();
    });
  }

  async initialize() {
    // Check authentication
    if (!window.api || !window.api.isAuthenticated()) {
      window.api.showToast('Please log in to consult AI Mentor Hermes.', 'info');
      setTimeout(() => { window.location.href = '/'; }, 1000);
      return;
    }

    // Apply sidebar collapsed preference
    this.updateSidebarUI();

    // Fetch conversation list
    await this.fetchConversations();

    // Route based on URL params
    this.checkUrlState();
  }

  checkUrlState() {
    const params = new URLSearchParams(window.location.search);
    const chatId = params.get('chat_id');
    if (chatId) {
      this.openConversation(chatId, false);
    } else {
      this.showLandingView(false);
    }
  }

  toggleSidebar() {
    this.sidebarCollapsed = !this.sidebarCollapsed;
    localStorage.setItem('hermes_sidebar_collapsed', this.sidebarCollapsed.toString());
    this.updateSidebarUI();
  }

  updateSidebarUI() {
    if (!this.sidebarRight || !this.btnBurgerMenu) return;
    if (this.sidebarCollapsed) {
      this.sidebarRight.classList.add('collapsed');
      this.btnBurgerMenu.classList.remove('active');
      this.btnBurgerMenu.setAttribute('title', 'Open Chat History (☰)');
    } else {
      this.sidebarRight.classList.remove('collapsed');
      this.btnBurgerMenu.classList.add('active');
      this.btnBurgerMenu.setAttribute('title', 'Collapse Chat History (☰)');
    }
  }

  showLandingView(updateUrl = true) {
    this.activeConversationId = null;
    this.activeConversation = null;

    if (updateUrl) {
      window.history.pushState({}, '', '/coach');
    }

    if (this.landingView) this.landingView.classList.remove('hidden');
    if (this.chatView) this.chatView.classList.add('hidden');

    this.renderLandingHistory();
  }

  async fetchConversations() {
    try {
      const res = await window.api.get('/coach/conversations');
      if (res.ok) {
        this.conversations = await res.json();
        this.renderLandingHistory();
        this.renderSidebarHistory();
      } else {
        console.error('Failed to fetch coach conversations:', res.status);
      }
    } catch (err) {
      console.error('Error fetching conversations:', err);
    }
  }

  renderLandingHistory() {
    if (!this.landingHistoryList) return;
    if (this.landingCountBadge) {
      this.landingCountBadge.textContent = `${this.conversations.length} Sessions`;
    }

    if (!this.conversations || this.conversations.length === 0) {
      this.landingHistoryList.innerHTML = `
        <div class="coach-empty-history">
          <div class="coach-empty-icon">🏛️</div>
          <div style="font-weight: 700; color: #0f172a; margin-bottom: 0.35rem;">No Previous Mentorship Chats</div>
          <div style="font-size: 0.88rem; max-width: 320px; margin: 0 auto; line-height: 1.5;">
            Your previous discussions with Hermes will appear here. Choose a template on the right to begin!
          </div>
        </div>
      `;
      return;
    }

    this.landingHistoryList.innerHTML = this.conversations.map(c => {
      const dateStr = this.formatDate(c.updated_at);
      const topicTag = c.topic ? `<span class="coach-topic-tag">${this.escapeHtml(c.topic)}</span>` : '';
      const preview = c.last_message_preview || 'No messages yet';
      const safeTitle = this.escapeHtml(c.title).replace(/'/g, "\\'");

      return `
        <div class="coach-history-item" onclick="window.coachCtrl.openConversation('${c.id}')">
          <div class="coach-history-item-top">
            <div class="coach-history-item-title">${this.escapeHtml(c.title)}</div>
            <div style="display: flex; align-items: center; gap: 0.2rem;" onclick="event.stopPropagation();">
              <button class="btn-history-rename" title="Rename conversation" onclick="window.coachCtrl.handleRenameConversation('${c.id}', '${safeTitle}')">
                ✏️
              </button>
              <button class="btn-history-delete" title="Delete conversation" onclick="window.coachCtrl.handleDeleteConversation('${c.id}')">
                🗑
              </button>
            </div>
          </div>
          <div class="coach-history-item-preview">${this.escapeHtml(preview)}</div>
          <div class="coach-history-item-meta">
            ${topicTag}
            <span>${c.message_count !== undefined ? c.message_count : 0} msgs • ${dateStr}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  renderSidebarHistory() {
    if (!this.sidebarHistoryList) return;

    if (!this.conversations || this.conversations.length === 0) {
      this.sidebarHistoryList.innerHTML = `
        <div style="text-align: center; padding: 2rem 1rem; color: #94a3b8; font-size: 0.85rem;">
          No other chats recorded.
        </div>
      `;
      return;
    }

    this.sidebarHistoryList.innerHTML = this.conversations.map(c => {
      const isActive = c.id === this.activeConversationId;
      const dateStr = this.formatDate(c.updated_at);
      const safeTitle = this.escapeHtml(c.title).replace(/'/g, "\\'");

      return `
        <div class="coach-sidebar-item ${isActive ? 'active' : ''}" onclick="window.coachCtrl.openConversation('${c.id}')">
          <div class="coach-sidebar-item-top">
            <div class="coach-sidebar-item-title">${this.escapeHtml(c.title)}</div>
            <div style="display: flex; align-items: center; gap: 0.2rem;" onclick="event.stopPropagation();">
              <button class="btn-history-rename" title="Rename conversation" onclick="window.coachCtrl.handleRenameConversation('${c.id}', '${safeTitle}')">
                ✏️
              </button>
              <button class="btn-history-delete" title="Delete conversation" onclick="window.coachCtrl.handleDeleteConversation('${c.id}')">
                🗑
              </button>
            </div>
          </div>
          <div class="coach-sidebar-item-bottom">
            <span>${this.escapeHtml(c.topic || 'Mentorship')}</span>
            <span>${dateStr}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  async openConversation(conversationId, updateUrl = true) {
    this.activeConversationId = conversationId;

    if (updateUrl) {
      window.history.pushState({}, '', `/coach?chat_id=${conversationId}`);
    }

    if (this.landingView) this.landingView.classList.add('hidden');
    if (this.chatView) this.chatView.classList.remove('hidden');

    this.renderSidebarHistory();

    // Show loading state
    if (this.messagesArea) {
      this.messagesArea.innerHTML = `
        <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
          <div class="coach-typing-indicator">
            <span class="coach-typing-dot"></span>
            <span class="coach-typing-dot"></span>
            <span class="coach-typing-dot"></span>
          </div>
        </div>
      `;
    }

    try {
      const res = await window.api.get(`/coach/conversations/${conversationId}`);
      if (res.ok) {
        this.activeConversation = await res.json();
        this.renderActiveConversation();
      } else {
        window.api.showToast('Conversation not found or removed.', 'error');
        this.showLandingView();
      }
    } catch (err) {
      console.error('Error loading conversation detail:', err);
      window.api.showToast('Failed to load conversation details.', 'error');
      this.showLandingView();
    }
  }

  renderActiveConversation() {
    if (!this.activeConversation) return;

    // Header updates
    if (this.chatTitle) {
      this.chatTitle.textContent = this.activeConversation.title || 'Mentorship Session';
    }
    if (this.chatTopicTag) {
      this.chatTopicTag.textContent = this.activeConversation.topic || 'DSA Strategy';
    }

    // Render messages
    if (this.messagesArea) {
      this.messagesArea.innerHTML = '';
      const msgs = this.activeConversation.messages || [];
      if (msgs.length === 0) {
        this.messagesArea.innerHTML = `
          <div class="coach-empty-chat-state">
            <div class="coach-empty-chat-icon">⚡</div>
            <h3 class="coach-empty-chat-title">Hermes is ready</h3>
            <p class="coach-empty-chat-desc">
              Ask anything about algorithms, code patterns, time complexity, or your past interview evaluations. Hermes will answer specifically what you ask.
            </p>
            <div class="coach-empty-chat-chips">
              <button type="button" class="coach-empty-chip" onclick="window.coachCtrl.insertExampleQuery('How can I get better at sliding window?')">
                <span>💡</span>
                <span>How can I get better at sliding window?</span>
              </button>
              <button type="button" class="coach-empty-chip" onclick="window.coachCtrl.insertExampleQuery('Talk about my weak areas')">
                <span>📊</span>
                <span>Talk about my weak areas</span>
              </button>
              <button type="button" class="coach-empty-chip" onclick="window.coachCtrl.insertExampleQuery('What was my strong points in the last interview?')">
                <span>🏆</span>
                <span>What was my strong points in the last interview?</span>
              </button>
            </div>
          </div>
        `;
      } else {
        msgs.forEach(msg => {
          this.appendMessageElement(msg, false);
        });
      }
      this.scrollToBottom();
    }

    if (this.chatInput) {
      this.chatInput.focus();
    }
  }

  insertExampleQuery(text) {
    if (!this.chatInput) return;
    this.chatInput.value = text;
    this.chatInput.focus();
    this.handleSendMessage();
  }

  appendMessageElement(msg, scroll = true) {
    if (!this.messagesArea) return;

    // Clear empty chat state placeholder if present
    const emptyState = this.messagesArea.querySelector('.coach-empty-chat-state');
    if (emptyState) {
      emptyState.remove();
    }

    const row = document.createElement('div');
    row.className = `coach-msg-row ${msg.sender}`;

    const timeStr = this.formatTime(msg.created_at);

    if (msg.sender === 'user') {
      row.innerHTML = `
        <div class="coach-bubble-user">${this.escapeHtml(msg.content)}</div>
        <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 0.25rem; align-self: flex-end;">${timeStr}</div>
      `;
    } else {
      // Hermes Message
      let citationsHtml = '';
      if (msg.evaluation_citations && msg.evaluation_citations.length > 0) {
        const badges = msg.evaluation_citations.map(cit => {
          const scorePart = cit.score !== undefined && cit.score !== null ? `(${cit.score.toFixed(1)}/4.0)` : '';
          return `
            <span class="coach-citation-badge">
              <span>📌 Grounded in:</span>
              <strong>${this.escapeHtml(cit.topic || 'Interview')}</strong>
              <span>${scorePart}</span>
            </span>
          `;
        }).join('');
        citationsHtml = `<div class="coach-citations-tray">${badges}</div>`;
      }

      const formattedContent = this.renderMarkdown(msg.content);

      row.innerHTML = `
        <div class="coach-bubble-hermes">
          <div class="coach-hermes-msg-header">
            <span class="coach-hermes-label">
              <span>⚡ Hermes</span>
              <span style="font-weight: 500; font-size: 0.75rem; color: #94a3b8;">• Technical Mentor</span>
            </span>
            <span class="coach-msg-time">${timeStr}</span>
          </div>
          ${citationsHtml}
          <div class="coach-markdown-body">${formattedContent}</div>
        </div>
      `;
    }

    this.messagesArea.appendChild(row);
    if (scroll) {
      this.scrollToBottom();
    }
  }

  showTypingIndicator() {
    this.removeTypingIndicator();
    const indicator = document.createElement('div');
    indicator.id = 'hermes-typing-indicator-row';
    indicator.className = 'coach-msg-row hermes';
    indicator.innerHTML = `
      <div class="coach-typing-indicator">
        <span style="font-size: 0.75rem; font-weight: 700; color: #ea580c; margin-right: 0.35rem;">Hermes thinking...</span>
        <span class="coach-typing-dot"></span>
        <span class="coach-typing-dot"></span>
        <span class="coach-typing-dot"></span>
      </div>
    `;
    this.messagesArea.appendChild(indicator);
    this.scrollToBottom();
  }

  removeTypingIndicator() {
    const existing = document.getElementById('hermes-typing-indicator-row');
    if (existing) existing.remove();
  }

  async handleLaunchSession(initialPrompt = null) {
    if (this.btnStartChatMain) {
      this.btnStartChatMain.disabled = true;
      this.btnStartChatMain.innerHTML = `<span>Starting Mentorship...</span>`;
    }

    try {
      const res = await window.api.post('/coach/conversations', {
        initial_prompt: initialPrompt || null
      });

      if (res.ok) {
        const created = await res.json();
        await this.fetchConversations();
        this.openConversation(created.id);
      } else {
        window.api.showToast('Could not start mentorship session.', 'error');
      }
    } catch (err) {
      console.error('Error starting conversation:', err);
      window.api.showToast('Network error while starting conversation.', 'error');
    } finally {
      if (this.btnStartChatMain) {
        this.btnStartChatMain.disabled = false;
        this.btnStartChatMain.innerHTML = `<span>⚡ Start Fresh Mentorship Chat</span><span>→</span>`;
      }
    }
  }

  async handleSendMessage() {
    if (!this.chatInput || this.isSending || !this.activeConversationId) return;

    const content = this.chatInput.value.trim();
    if (!content) return;

    this.isSending = true;
    this.chatInput.value = '';
    this.chatInput.style.height = 'auto';
    if (this.btnSendMessage) this.btnSendMessage.disabled = true;

    // Optimistically render user message
    const userMsg = {
      sender: 'user',
      content: content,
      created_at: new Date().toISOString()
    };
    this.appendMessageElement(userMsg, true);

    // Show typing indicator
    this.showTypingIndicator();

    try {
      const res = await window.api.post(`/coach/conversations/${this.activeConversationId}/messages`, {
        content: content
      });

      this.removeTypingIndicator();

      if (res.ok) {
        const hermesMsg = await res.json();
        this.appendMessageElement(hermesMsg, true);
        // Refresh conversations list in background to update previews
        this.fetchConversations();
      } else {
        window.api.showToast('Hermes was unable to reply. Please try again.', 'error');
      }
    } catch (err) {
      console.error('Error sending message to Hermes:', err);
      this.removeTypingIndicator();
      window.api.showToast('Network error contacting Hermes.', 'error');
    } finally {
      this.isSending = false;
      if (this.btnSendMessage) this.btnSendMessage.disabled = false;
      if (this.chatInput) this.chatInput.focus();
    }
  }

  async handleRenameConversation(conversationId, currentTitle = '') {
    if (!conversationId) return;
    const promptTitle = currentTitle || (this.activeConversation ? this.activeConversation.title : 'Mentorship Session');
    const newTitle = prompt('Enter a new title for this conversation:', promptTitle);

    if (!newTitle || !newTitle.trim() || newTitle.trim() === promptTitle) {
      return;
    }

    const cleanTitle = newTitle.trim();

    try {
      const res = await window.api.patch(`/coach/conversations/${conversationId}`, {
        title: cleanTitle
      });

      if (res.ok) {
        const updated = await res.json();
        window.api.showToast('Conversation renamed.', 'info');

        if (this.activeConversation && this.activeConversation.id === conversationId) {
          this.activeConversation.title = updated.title;
          if (this.chatTitle) {
            this.chatTitle.textContent = updated.title;
          }
        }

        await this.fetchConversations();
      } else {
        window.api.showToast('Failed to rename conversation.', 'error');
      }
    } catch (err) {
      console.error('Error renaming conversation:', err);
      window.api.showToast('Network error renaming conversation.', 'error');
    }
  }

  async handleDeleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this mentorship conversation? This action cannot be undone.')) {
      return;
    }

    try {
      const res = await window.api.delete(`/coach/conversations/${conversationId}`);
      if (res.ok) {
        window.api.showToast('Conversation deleted.', 'info');
        // If the deleted conversation is currently active, return to landing
        if (this.activeConversationId === conversationId) {
          this.showLandingView();
        }
        await this.fetchConversations();
      } else {
        window.api.showToast('Failed to delete conversation.', 'error');
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
      window.api.showToast('Network error while deleting conversation.', 'error');
    }
  }

  renderMarkdown(text) {
    if (!text) return '';
    if (window.marked && typeof window.marked.parse === 'function') {
      try {
        return window.marked.parse(text);
      } catch (e) {
        console.warn('Marked parse error:', e);
      }
    }
    // Simple fallback if marked is not available
    return this.escapeHtml(text).replace(/\n/g, '<br>');
  }

  escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  formatDate(isoString) {
    if (!isoString) return 'Recent';
    try {
      const d = new Date(isoString);
      const now = new Date();
      const diffMs = now - d;
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return 'Recent';
    }
  }

  formatTime(isoString) {
    if (!isoString) return '';
    try {
      return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  scrollToBottom() {
    if (this.messagesArea) {
      this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
    }
  }
}

// Instantiate on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  // Set avatar initials if present
  if (window.api) {
    const user = window.api.getUser();
    if (user && user.full_name) {
      const initialsEl = document.getElementById('user-avatar-initials');
      if (initialsEl) {
        const parts = user.full_name.trim().split(/\s+/);
        const initials = parts.length > 1
          ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
          : (parts[0] ? parts[0].slice(0, 2).toUpperCase() : 'GM');
        initialsEl.textContent = initials;
      }
    }
  }

  window.coachCtrl = new CoachController();
  window.coachCtrl.initialize();
});
