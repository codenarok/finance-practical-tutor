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
  let unchecked = [];

  function handle(line) {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.type === 'token') {
      reply += event.text;
      bubble.classList.remove('typing');
      bubble.innerHTML = formatMessage(reply);
      chatWindow.scrollTop = chatWindow.scrollHeight;
    } else if (event.type === 'calculation') {
      // The app did this sum itself. Show it above the tutor's reply and keep it as a trusted turn.
      const card = showMessage(event.summary, 'bot');
      card.classList.add('calculation');
      chatWindow.insertBefore(card.parentElement, bubble.parentElement);
      conversation.push({ role: 'assistant', content: event.summary, sig: event.sig });
    } else if (event.type === 'caution') {
      unchecked = event.amounts;
    } else if (event.type === 'done') {
      outcome = { ok: true, reply, sig: event.sig, unchecked };
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

  // Fetch JSON with the learner's token. Returns null after sending them to log in again.
  async function authedJson(path, body) {
    const currentToken = getToken();
    if (!currentToken) {
      redirectToLogin();
      return null;
    }
    const headers = { 'Authorization': `Bearer ${currentToken}` };
    if (body) headers['Content-Type'] = 'application/json';
    const res = await fetch(path, {
      method: body ? 'POST' : 'GET',
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
    if (res.status === 401) {
      redirectToLogin();
      return null;
    }
    if (!res.ok) throw new Error(await errorDetail(res, 'Something went wrong. Please try again.'));
    return res.json();
  }

  // Lessons: explanations and marking come from the server. Each explanation and
  // each finished question joins the conversation, so the tutor knows what was taught.
  function addTrustedTurn(signed) {
    conversation.push({ role: 'assistant', content: signed.text, sig: signed.sig });
  }

  function buildQuestionForm(question, progressText) {
    const form = document.createElement('form');
    form.className = 'lesson-question';
    const progress = document.createElement('p');
    progress.className = 'progress';
    progress.textContent = progressText;
    const prompt = document.createElement('p');
    prompt.className = 'prompt';
    prompt.textContent = question.prompt;
    form.append(progress, prompt);

    const check = document.createElement('button');
    check.type = 'submit';
    check.className = 'secondary';
    check.textContent = 'Check';

    if (question.kind === 'choice') {
      question.options.forEach((option) => {
        const label = document.createElement('label');
        label.className = 'option';
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'answer';
        radio.value = option.key;
        radio.required = true;
        label.append(radio, document.createTextNode(option.label));
        form.appendChild(label);
      });
      form.appendChild(check);
    } else {
      const row = document.createElement('div');
      row.className = 'answer-row';
      const input = document.createElement('input');
      input.type = 'text';
      input.name = 'answer';
      input.inputMode = 'decimal';
      input.maxLength = 40;
      const unitName = { pounds: '£', percent: '%' }[question.unit] || question.unit_label;
      const spokenUnit = { pounds: 'pounds', percent: 'percent' }[question.unit] || question.unit_label;
      input.placeholder = `Your answer in ${unitName}`;
      input.setAttribute('aria-label', `Your answer in ${spokenUnit}`);
      input.autocomplete = 'off';
      input.required = true;
      row.append(input, check);
      form.appendChild(row);
    }
    return form;
  }

  function runLesson(lesson) {
    let index = 0;
    let rightFirstTime = 0;

    function finish() {
      const total = lesson.steps.length;
      showMessage(`${lesson.closing.text}\nYou got ${rightFirstTime} of ${total} right first time.`, 'bot')
        .classList.add('calculation');
      addTrustedTurn(lesson.closing);
      messageInput.focus();
    }

    function showStep() {
      const step = lesson.steps[index];
      const bubble = showMessage(step.explanation.text, 'bot');
      bubble.classList.add('calculation');
      addTrustedTurn(step.explanation);
      const form = buildQuestionForm(step.question, `Question ${index + 1} of ${lesson.steps.length}`);
      bubble.appendChild(form);
      chatWindow.scrollTop = chatWindow.scrollHeight;
      const answerBox = form.querySelector('input[type="text"]');
      if (answerBox) answerBox.focus();
      let attempt = 1;

      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const answer = new FormData(form).get('answer');
        const button = form.querySelector('button');
        button.disabled = true;
        try {
          const result = await authedJson(`/api/lessons/${lesson.id}/answer`, {
            question_id: step.question.id, answer, attempt
          });
          if (!result) return;
          const feedback = showMessage(result.feedback, 'bot');
          if (result.correct) feedback.classList.add('correct');
          if (!result.revealed) {
            if (result.counted) attempt += 1;
            button.disabled = false;
            // Select the old answer so the next one typed replaces it.
            if (answerBox) {
              answerBox.focus();
              answerBox.select();
            }
            return;
          }
          form.querySelectorAll('input').forEach((input) => { input.disabled = true; });
          addTrustedTurn(result.record);
          if (result.correct && attempt === 1) rightFirstTime += 1;
          index += 1;
          if (index < lesson.steps.length) showStep(); else finish();
        } catch (err) {
          showMessage(err.message, 'bot').classList.add('failed');
          button.disabled = false;
        }
      });
    }

    showStep();
  }

  async function loadLessons() {
    const list = document.getElementById('lesson-list');
    const panel = document.getElementById('lessons-panel');
    if (!list) return;
    try {
      const lessons = await authedJson('/api/lessons');
      if (!lessons) return;
      let currentTopic = null;
      lessons.sort((a, b) => a.topic.localeCompare(b.topic));
      lessons.forEach((item) => {
        if (item.topic !== currentTopic) {
          currentTopic = item.topic;
          const heading = document.createElement('p');
          heading.className = 'lesson-topic';
          heading.textContent = item.topic;
          list.appendChild(heading);
        }
        const row = document.createElement('div');
        row.className = 'lesson-item';
        const text = document.createElement('div');
        const title = document.createElement('h2');
        title.textContent = item.title;
        const detail = document.createElement('p');
        detail.className = 'note';
        detail.textContent = `${item.summary} ${item.level}, ${item.questions} questions.`;
        text.append(title, detail);
        const start = document.createElement('button');
        start.type = 'button';
        start.className = 'secondary';
        start.textContent = 'Start';
        start.addEventListener('click', async () => {
          start.disabled = true;
          try {
            const lesson = await authedJson(`/api/lessons/${item.id}`);
            if (!lesson) return;
            // The tutor gets the figures for the lesson's topic if the learner asks about it.
            document.getElementById('topic').value = lesson.topic;
            panel.open = false;
            runLesson(lesson);
          } catch (err) {
            showMessage(err.message, 'bot').classList.add('failed');
          } finally {
            start.disabled = false;
          }
        });
        row.append(text, start);
        list.appendChild(row);
      });
    } catch (err) {
      list.textContent = 'Lessons could not be loaded.';
    }
  }
  loadLessons();

  // Calculators: the server does the sums and signs the result, which then joins
  // the conversation so the tutor can explain it.
  document.querySelectorAll('form.calculator').forEach((form) => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const currentToken = getToken();
      if (!currentToken) {
        redirectToLogin();
        return;
      }
      const fields = Object.fromEntries(new FormData(form).entries());
      if (fields.years) fields.years = Number(fields.years);
      const button = form.querySelector('button');
      button.disabled = true;
      try {
        const res = await fetch(`/api/calculate/${form.dataset.endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
          },
          body: JSON.stringify(fields)
        });
        if (res.status === 401) {
          redirectToLogin();
          return;
        }
        if (!res.ok) {
          showMessage(await errorDetail(res, 'That could not be worked out.'), 'bot').classList.add('failed');
          return;
        }
        const result = await res.json();
        showMessage(result.summary, 'bot').classList.add('calculation');
        conversation.push({ role: 'assistant', content: result.summary, sig: result.sig });
        form.closest('details').open = false;
        messageInput.focus();
      } catch (err) {
        showMessage('Network issue. Please try again.', 'bot').classList.add('failed');
      } finally {
        button.disabled = false;
      }
    });
  });

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
        if (outcome.unchecked.length) {
          // The server found amounts in the reply that the app did not supply.
          const note = document.createElement('p');
          note.className = 'unchecked';
          note.textContent = `Not checked by the app: ${outcome.unchecked.join(', ')}. `
            + 'The tutor worked these out itself, so they may be wrong. '
            + 'For exact amounts use the calculators or a lesson\'s working.';
          bubble.appendChild(note);
          chatWindow.scrollTop = chatWindow.scrollHeight;
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
