(() => {
  const TRANSCRIPT_KEY = 'contextlens_voice_transcript_v1';
  const SETTINGS_KEY = 'contextlens_voice_settings_v1';
  const appRoot = document.getElementById('app');
  const voice = {
    open: false,
    listening: false,
    speaking: false,
    liveText: '',
    autoSpeak: JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{"autoSpeak":true}').autoSpeak !== false,
    messages: JSON.parse(localStorage.getItem(TRANSCRIPT_KEY) || '[]'),
    recognition: null,
    firstHash: location.hash,
  };

  const escapeHtml = (value = '') => String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  const getTarget = () => document.querySelector('#problem, #answer-detail, #decision-text');
  const targetName = () => {
    const target = getTarget();
    if (!target) return 'the conversation';
    if (target.id === 'problem') return 'your situation';
    if (target.id === 'answer-detail') return 'your clarification answer';
    return 'your decision';
  };
  const persist = () => {
    localStorage.setItem(TRANSCRIPT_KEY, JSON.stringify(voice.messages.slice(-80)));
    localStorage.setItem(SETTINGS_KEY, JSON.stringify({ autoSpeak: voice.autoSpeak }));
  };
  const fallbackMessage = () => ({ kind: 'assistant', text: 'I’m here. Speak or type what you are thinking, and I’ll keep the transcript visible while you work through it.', at: new Date().toISOString(), demo: true });
  const visibleMessages = () => voice.messages.length ? voice.messages : [fallbackMessage()];
  const addMessage = (kind, text) => {
    if (!text || !text.trim()) return;
    voice.messages.push({ kind, text: text.trim(), at: new Date().toISOString() });
    persist();
  };
  const avatarState = () => voice.listening ? 'listening' : voice.speaking ? 'speaking' : 'idle';
  const avatar = (small = false) => `<span class="voice-avatar ${small ? 'small' : ''} ${avatarState()}" aria-hidden="true"><span class="avatar-orbit orbit-one"></span><span class="avatar-orbit orbit-two"></span><span class="avatar-core">⌁</span></span>`;

  function renderDock() {
    let dock = document.getElementById('voice-dock');
    if (!dock) {
      dock = document.createElement('section');
      dock.id = 'voice-dock';
      dock.className = 'voice-dock';
      document.body.appendChild(dock);
    }
    const messages = visibleMessages();
    const priorInput = document.getElementById('voice-text')?.value || '';
    dock.className = `voice-dock ${voice.open ? 'open' : ''}`;
    dock.innerHTML = `<div class="voice-bar"><button class="voice-avatar-button" data-voice-open aria-label="${voice.open ? 'Collapse' : 'Open'} voice room">${avatar()}</button><div class="voice-heading"><strong>Voice companion</strong><span>${voice.listening ? 'Listening…' : voice.speaking ? 'Speaking…' : 'Talk it out with ContextLens'}</span></div><button class="voice-icon-button" data-voice-open aria-label="${voice.open ? 'Collapse voice room' : 'Expand voice room'}">${voice.open ? '⌄' : '↗'}</button></div><div class="voice-room" aria-label="Voice conversation" ${voice.open ? '' : 'hidden'}><div class="voice-room-head"><div><span class="eyebrow">Live transcript</span><h3>Your voice conversation</h3></div><button class="button ghost small" data-voice-read>Read this view aloud</button></div><div class="voice-transcript" id="voice-transcript" role="log" aria-live="polite">${messages.map((message) => `<div class="voice-message ${message.kind === 'user' ? 'user' : 'assistant'}"><div class="voice-message-avatar">${message.kind === 'user' ? 'You' : avatar(true)}</div><div class="voice-bubble"><div class="voice-bubble-label">${message.kind === 'user' ? 'You said' : 'ContextLens'}</div><p>${escapeHtml(message.text)}</p><time>${new Date(message.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div></div>`).join('')}</div>${voice.liveText ? `<div class="voice-live"><span class="live-dot"></span>${escapeHtml(voice.liveText)}</div>` : ''}<div class="voice-controls"><button class="voice-mic-button ${voice.listening ? 'active' : ''}" data-voice-mic>${voice.listening ? '■ Stop listening' : '● Speak'}</button><button class="voice-control-button ${voice.autoSpeak ? 'enabled' : ''}" data-voice-speaker>${voice.autoSpeak ? 'Speaker on' : 'Speaker off'}</button><button class="voice-control-button" data-voice-clear>Clear</button></div><form class="voice-composer" data-voice-form><input id="voice-text" autocomplete="off" value="${escapeHtml(priorInput)}" placeholder="Type or speak your thought…" aria-label="Type a message for ContextLens"><button class="button primary small" type="submit" aria-label="Send message">Send</button></form><p class="voice-hint">Speak into the active field, or use the mic to add a transcript. Your browser controls microphone permission.</p></div>`;
    const transcript = document.getElementById('voice-transcript');
    if (transcript) transcript.scrollTop = transcript.scrollHeight;
  }

  function fillActiveField(text) {
    const target = getTarget();
    if (!target) return false;
    target.value = target.value ? `${target.value.trim()} ${text}` : text;
    target.dispatchEvent(new Event('input', { bubbles: true }));
    target.focus();
    return true;
  }

  function speak(text, options = {}) {
    if (!text || !voice.autoSpeak && !options.force) return;
    if (!('speechSynthesis' in window)) {
      addMessage('assistant', `${text} (Speech output is unavailable in this browser.)`);
      renderDock();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.96;
    utterance.pitch = 1.02;
    utterance.volume = 0.9;
    voice.speaking = true;
    addMessage('assistant', text);
    renderDock();
    utterance.onend = () => { voice.speaking = false; renderDock(); };
    utterance.onerror = () => { voice.speaking = false; renderDock(); };
    window.speechSynthesis.speak(utterance);
  }

  function acknowledge(text, applied) {
    addMessage('user', text);
    if (applied) speak(`I heard you. I added that to ${targetName()}.`);
    else speak('I heard you. Open a case field or use the text composer to keep going.');
  }

  function createRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) return null;
    const recognition = new Recognition();
    recognition.lang = document.documentElement.lang || 'en-US';
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => { voice.listening = true; voice.liveText = ''; renderDock(); };
    recognition.onresult = (event) => {
      let finalText = '';
      let interimText = '';
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const transcript = event.results[index][0].transcript;
        if (event.results[index].isFinal) finalText += transcript;
        else interimText += transcript;
      }
      voice.liveText = interimText || finalText;
      const live = document.querySelector('.voice-live');
      if (live) live.innerHTML = `<span class="live-dot"></span>${escapeHtml(voice.liveText)}`;
      if (finalText.trim()) {
        const applied = fillActiveField(finalText.trim());
        acknowledge(finalText.trim(), applied);
        voice.liveText = '';
      }
    };
    recognition.onerror = (event) => {
      voice.listening = false; voice.liveText = '';
      const detail = event.error === 'not-allowed' ? 'Microphone permission was not granted.' : 'I could not hear that. Please try again.';
      addMessage('assistant', detail); renderDock();
    };
    recognition.onend = () => { voice.listening = false; voice.liveText = ''; renderDock(); };
    return recognition;
  }

  function toggleListening() {
    if (!voice.recognition) voice.recognition = createRecognition();
    if (!voice.recognition) {
      addMessage('assistant', 'Voice input is not available in this browser. You can still type in the transcript composer.');
      renderDock();
      return;
    }
    if (voice.listening) voice.recognition.stop();
    else {
      try { voice.recognition.start(); } catch (error) { voice.listening = false; renderDock(); }
    }
  }

  function sendText(text) {
    const message = text.trim();
    if (!message) return;
    const applied = fillActiveField(message);
    acknowledge(message, applied);
  }

  function readCurrentView() {
    const heading = document.querySelector('.content h1')?.textContent?.trim() || 'ContextLens';
    const prompt = document.querySelector('.question-card .prompt')?.textContent?.trim();
    const goal = document.querySelector('.context-card.wide p')?.textContent?.trim();
    const summary = document.querySelector('.synthesis-item p')?.textContent?.trim();
    speak([heading, prompt || goal || summary].filter(Boolean).join('. '), { force: true });
  }

  function decorateNavigation() {
    const nav = document.querySelector('.sidebar .nav');
    if (nav && !nav.querySelector('[data-voice-open]')) {
      const button = document.createElement('button');
      button.className = 'nav-button voice-nav-button';
      button.setAttribute('data-voice-open', 'true');
      button.innerHTML = '<span class="nav-icon" aria-hidden="true">◉</span><span>Voice room</span>';
      nav.appendChild(button);
    }
  }

  function decorateDashboard() {
    if (location.hash || document.getElementById('voice-intro')) return;
    const hero = document.querySelector('.hero');
    if (!hero || document.getElementById('voice-intro')) return;
    const intro = document.createElement('section');
    intro.id = 'voice-intro';
    intro.className = 'voice-intro card';
    intro.innerHTML = `<div class="voice-intro-art">${avatar()}</div><div class="voice-intro-copy"><div class="eyebrow">New · Voice workspace</div><h3>Talk it out, then see the words.</h3><p>Speak naturally, watch your words become a transcript, and hear ContextLens reflect the wider picture back to you.</p></div><button class="button secondary" data-voice-open>Open voice room <span aria-hidden="true">→</span></button>`;
    hero.insertAdjacentElement('afterend', intro);
  }

  function announceHashChange() {
    if (voice.firstHash === location.hash) return;
    voice.firstHash = location.hash;
    if (!voice.autoSpeak) return;
    window.setTimeout(() => {
      const heading = document.querySelector('.content h1')?.textContent?.trim();
      const prompt = document.querySelector('.question-card .prompt')?.textContent?.trim();
      if (heading) speak([heading, prompt].filter(Boolean).join('. '));
    }, 350);
  }

  document.addEventListener('click', (event) => {
    const openButton = event.target.closest('[data-voice-open]');
    if (openButton) { voice.open = !voice.open; renderDock(); return; }
    if (event.target.closest('[data-voice-mic]')) { toggleListening(); return; }
    if (event.target.closest('[data-voice-speaker]')) { voice.autoSpeak = !voice.autoSpeak; persist(); renderDock(); if (voice.autoSpeak) speak('Speaker is on. I will read key responses aloud.', { force: true }); return; }
    if (event.target.closest('[data-voice-clear]')) { voice.messages = []; persist(); renderDock(); return; }
    if (event.target.closest('[data-voice-read]')) { readCurrentView(); return; }
  });
  document.addEventListener('submit', (event) => {
    if (!event.target.matches('[data-voice-form]')) return;
    event.preventDefault();
    const input = document.getElementById('voice-text');
    if (input) { sendText(input.value); input.value = ''; }
  });
  window.addEventListener('hashchange', announceHashChange);
  if (appRoot) {
    const observer = new MutationObserver(() => { decorateNavigation(); decorateDashboard(); });
    observer.observe(appRoot, { childList: true, subtree: true });
  }
  decorateNavigation();
  decorateDashboard();
  renderDock();
})();
