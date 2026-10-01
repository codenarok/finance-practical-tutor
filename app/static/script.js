const TOKEN_KEY = 'finance_tutor_token';
let chatWindow = null;
// The conversation so far. Kept in this tab only and sent with each message;
// tutor replies carry the server's signature so they are trusted on the way back.
const conversation = [];

function formatMessage(text) {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  const bolded = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  const bulleted = bolded.replace(/^(\s*)[*+-] /gm, '$1• ');
  return bulleted.replace(/\n/g, '<br>');
}

function showMessage(text, sender = 'bot') {
  if (!chatWindow) return null;
  const wrapper = document.createElement('div');
  wrapper.className = `message ${sender}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = formatMessage(text);
  wrapper.appendChild(bubble);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return bubble;
}

function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

function redirectToLogin() {
  clearToken();
  window.location.href = '/static/index.html';
}

// FastAPI sends a string for most errors and a list of problems for invalid input.
async function errorDetail(res, fallback) {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail) && body.detail.length) {
      return body.detail.map((problem) => problem.msg).join(' ');
    }
  } catch (err) {
    // not JSON; use the fallback
  }
  return fallback;
}

function initAuthPage() {
  clearToken();
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const errorBox = document.getElementById('auth-error');

  function showError(text) {
    errorBox.textContent = text;
    errorBox.classList.remove('hidden');
  }

  async function submitAuth(url, options, fallback) {
    errorBox.classList.add('hidden');
    try {
      const res = await fetch(url, { method: 'POST', ...options });
      if (!res.ok) {
        showError(await errorDetail(res, fallback));
        return;
      }
      const data = await res.json();
      setToken(data.access_token);
      window.location.href = '/static/chat.html';
    } catch (err) {
      showError('Unable to reach the server right now.');
    }
  }

  if (registerForm) {
    registerForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = document.getElementById('register-email').value;
      const password = document.getElementById('register-password').value;
      submitAuth('/api/register', {
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      }, 'Registration failed');
    });
  }

  if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const formData = new URLSearchParams();
      formData.append('username', document.getElementById('login-email').value);
      formData.append('password', document.getElementById('login-password').value);
      formData.append('grant_type', 'password');
      submitAuth('/api/login', {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      }, 'Login failed');
    });
  }
}

// Read the reply stream: one JSON event per line (token, done or error).
async function readReply(res, bubble) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let reply = '';
  let outcome = { ok: false, detail: 'The reply was cut short. Please try again.' };

  function handle(line) {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.type === 'token') {
      reply += event.text;
      bubble.classList.remove('typing');
      bubble.innerHTML = formatMessage(reply);
      chatWindow.scrollTop = chatWindow.scrollHeight;
    } else if (event.type === 'done') {
      outcome = { ok: true, reply, sig: event.sig };
    } else if (event.type === 'error') {
      outcome = { ok: false, detail: event.detail };
    }
  }

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    lines.forEach(handle);
  }
  handle(buffer);
  return outcome;
}

function initChatPage() {
  const token = getToken();
  if (!token) {
    redirectToLogin();
    return;
  }

  chatWindow = document.getElementById('chat-window');
  const chatForm = document.getElementById('chat-form');
  const logoutBtn = document.getElementById('logout-btn');
  const messageInput = document.getElementById('chat-message');
  const sendBtn = document.getElementById('send-btn');

  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      redirectToLogin();
    });
  }

  function setBusy(busy) {
    sendBtn.disabled = busy;
    messageInput.disabled = busy;
    if (!busy) messageInput.focus();
  }

  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const message = messageInput.value.trim();
      const topic = document.getElementById('topic').value;
      const knowledge_level = document.getElementById('knowledge-level').value;

      if (!message) return;

      const currentToken = getToken();
      if (!currentToken) {
        redirectToLogin();
        return;
      }

      showMessage(message, 'user');
      messageInput.value = '';
      setBusy(true);
      const bubble = showMessage('Thinking…', 'bot');
      bubble.classList.add('typing');

      function fail(text) {
        bubble.classList.remove('typing');
        bubble.classList.add('failed');
        bubble.textContent = text;
      }

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
          },
          body: JSON.stringify({ message, topic, knowledge_level, history: conversation })
        });
        if (res.status === 401) {
          fail('Session expired. Redirecting to login.');
          redirectToLogin();
          return;
        }
        if (!res.ok) {
          fail(await errorDetail(res, 'Tutor unavailable. Try again later.'));
          return;
        }
        const outcome = await readReply(res, bubble);
        if (!outcome.ok) {
          fail(outcome.detail);
          return;
        }
        conversation.push({ role: 'user', content: message });
        conversation.push({ role: 'assistant', content: outcome.reply, sig: outcome.sig });
        // The server only reads the newest turns that fit its budget; keep the list short.
        while (conversation.length > 20) conversation.shift();
      } catch (err) {
        fail('Network issue. Please try again.');
      } finally {
        setBusy(false);
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.page || 'auth';
  if (page === 'chat') {
    initChatPage();
  } else {
    initAuthPage();
  }
});
