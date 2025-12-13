const authCard = document.getElementById('auth-card');
const chatCard = document.getElementById('chat-card');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const chatForm = document.getElementById('chat-form');
const chatWindow = document.getElementById('chat-window');
const logoutBtn = document.getElementById('logout-btn');

function formatMessage(text) {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  const bolded = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  return bolded.replace(/\n/g, '<br>');
}

function showMessage(text, sender = 'bot') {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${sender}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = formatMessage(text);
  wrapper.appendChild(bubble);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function switchToChat() {
  authCard.classList.add('hidden');
  chatCard.classList.remove('hidden');
}

function switchToAuth() {
  chatCard.classList.add('hidden');
  authCard.classList.remove('hidden');
  localStorage.removeItem('token');
}

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
    localStorage.setItem('token', data.access_token);
    switchToChat();
  } catch (err) {
    alert('Unable to register right now.');
  }
});

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
    localStorage.setItem('token', data.access_token);
    switchToChat();
  } catch (err) {
    alert('Unable to login right now.');
  }
});

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = document.getElementById('chat-message').value;
  const topic = document.getElementById('topic').value || 'general';
  const knowledge_level = document.getElementById('knowledge-level').value || 'Beginner';
  if (!message.trim()) return;
  showMessage(message, 'user');
  document.getElementById('chat-message').value = '';
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ message, topic, knowledge_level })
    });
    if (!res.ok) {
      const body = await res.json();
      showMessage(body.detail || 'Tutor unavailable. Try again later.');
      return;
    }
    const data = await res.json();
    showMessage(data.reply, 'bot');
  } catch (err) {
    showMessage('Network issue. Please try again.');
  }
});

logoutBtn.addEventListener('click', () => {
  switchToAuth();
});

if (localStorage.getItem('token')) {
  switchToChat();
}
