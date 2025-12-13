const TOKEN_KEY = 'finance_tutor_token';
let chatWindow = null;

function formatMessage(text) {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  const bolded = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  return bolded.replace(/\n/g, '<br>');
}

function showMessage(text, sender = 'bot') {
  if (!chatWindow) return;
  const wrapper = document.createElement('div');
  wrapper.className = `message ${sender}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = formatMessage(text);
  wrapper.appendChild(bubble);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
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

function initAuthPage() {
  clearToken();
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');

  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('register-email').value;
      const password = document.getElementById('register-password').value;
      try {
        const res = await fetch('/api/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        if (!res.ok) {
          const body = await res.json();
          alert(body.detail || 'Registration failed');
          return;
        }
        const data = await res.json();
        setToken(data.access_token);
        window.location.href = '/static/chat.html';
      } catch (err) {
        alert('Unable to register right now.');
      }
    });
  }

  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('login-email').value;
      const password = document.getElementById('login-password').value;
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      formData.append('grant_type', 'password');
      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData.toString()
        });
        if (!res.ok) {
          const body = await res.json();
          alert(body.detail || 'Login failed');
          return;
        }
        const data = await res.json();
        setToken(data.access_token);
        window.location.href = '/static/chat.html';
      } catch (err) {
        alert('Unable to login right now.');
      }
    });
  }
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

  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      redirectToLogin();
    });
  }

  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const messageInput = document.getElementById('chat-message');
      const topicInput = document.getElementById('topic');
      const knowledgeInput = document.getElementById('knowledge-level');

      const message = messageInput.value;
      const topic = topicInput.value || 'general';
      const knowledge_level = knowledgeInput.value || 'Beginner';

      if (!message.trim()) return;
      showMessage(message, 'user');
      messageInput.value = '';

      const currentToken = getToken();
      if (!currentToken) {
        showMessage('Please login again to continue.', 'bot');
        redirectToLogin();
        return;
      }

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
          },
          body: JSON.stringify({ message, topic, knowledge_level })
        });
        if (!res.ok) {
          if (res.status === 401) {
            showMessage('Session expired. Redirecting to login.', 'bot');
            redirectToLogin();
            return;
          }
          const body = await res.json();
          showMessage(body.detail || 'Tutor unavailable. Try again later.');
          return;
        }
        const data = await res.json();
        showMessage(data.reply, 'bot');
      } catch (err) {
        showMessage('Network issue. Please try again.', 'bot');
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
