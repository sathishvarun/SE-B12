// Beldex AI — shared helpers (API, session, toasts, formatting)
const Auth = {
  get token() { return localStorage.getItem('bx_token'); },
  get user() { try { return JSON.parse(localStorage.getItem('bx_user')); } catch { return null; } },
  save(res) { localStorage.setItem('bx_token', res.token); localStorage.setItem('bx_user', JSON.stringify(res.user)); },
  setUser(u) { localStorage.setItem('bx_user', JSON.stringify(u)); },
  clear() { localStorage.removeItem('bx_token'); localStorage.removeItem('bx_user'); },
};

// Picks the Tamil or English text for messages, following the page language.
const L = (en, ta) => document.documentElement.lang === 'ta' ? ta : en;

async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && Auth.token) headers.Authorization = 'Bearer ' + Auth.token;
  let res;
  try {
    res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error(L('Cannot reach the server. Check that the app is running.', 'சர்வரை அணுக முடியவில்லை. சிறிது நேரம் கழித்து முயற்சிக்கவும்.'));
  }
  let data = null;
  try { data = await res.json(); } catch {}
  if (res.status === 401 && auth) { Auth.clear(); location.href = 'index.html?expired=1'; throw new Error('Session ended'); }
  if (!res.ok) {
    let msg = data && data.detail;
    if (Array.isArray(msg)) msg = msg.map(d => (d.loc ? d.loc[d.loc.length - 1] + ': ' : '') + d.msg).join(' · ');
    throw new Error(msg || L('Something went wrong. Please try again.', 'ஏதோ தவறு நடந்தது. மீண்டும் முயற்சிக்கவும்.'));
  }
  return data;
}

function requireLogin(role) {
  const u = Auth.user;
  if (!Auth.token || !u) { location.href = 'index.html'; return null; }
  if (role === 'admin' && u.role !== 'admin') { location.href = 'app.html'; return null; }
  return u;
}

async function signOut() {
  try { await api('/auth/logout', { method: 'POST' }); } catch {}
  Auth.clear();
  location.href = 'index.html';
}

// Keeps "time used" accurate: a light ping every minute while the tab is visible.
function startHeartbeat() {
  setInterval(() => { if (document.visibilityState === 'visible') api('/me').catch(() => {}); }, 60000);
}

function toast(msg, isErr = false) {
  let box = document.querySelector('.toast-box');
  if (!box) { box = document.createElement('div'); box.className = 'toast-box'; document.body.appendChild(box); }
  const t = document.createElement('div');
  t.className = 'toast' + (isErr ? ' err' : '');
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function md(text) {
  const html = window.marked ? marked.parse(text || '', { breaks: true }) : esc(text).replace(/\n/g, '<br>');
  return window.DOMPurify ? DOMPurify.sanitize(html) : html;
}

const PALETTE = ['#E2531D', '#11704A', '#3B5BDB', '#8A5A00', '#7C3AED', '#0E7490', '#BE185D', '#121318'];
function avatarColor(s) { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return PALETTE[h % PALETTE.length]; }
function initials(name) { return String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join(''); }
function avatar(name, size = 34) {
  return `<span class="avatar" style="width:${size}px;height:${size}px;background:${avatarColor(name)}">${esc(initials(name))}</span>`;
}

function utc(iso) { return new Date(iso.endsWith('Z') ? iso : iso + 'Z'); }
function ago(iso) {
  if (!iso) return '—';
  const s = Math.max(0, (Date.now() - utc(iso)) / 1000);
  if (s < 60) return L('just now', 'இப்போது');
  if (s < 3600) return Math.floor(s / 60) + L(' min ago', ' நிமிடம் முன்');
  if (s < 86400) return Math.floor(s / 3600) + L(' h ago', ' மணி நேரம் முன்');
  if (s < 86400 * 7) return Math.floor(s / 86400) + L(' d ago', ' நாள் முன்');
  return utc(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}
function fmtDate(iso) { return iso ? utc(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'; }
function fmtMin(m) { m = Number(m) || 0; return m >= 60 ? (m / 60).toFixed(1) + ' h' : Math.round(m) + ' min'; }
function compact(n) { n = Number(n) || 0; return n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e4 ? (n / 1e3).toFixed(1) + 'k' : n.toLocaleString('en-IN'); }

// Animated number counter for KPI cards
function countUp(el, to, { dec = 0, prefix = '', suffix = '', ms = 900 } = {}) {
  const start = performance.now();
  const step = now => {
    const p = Math.min(1, (now - start) / ms), e = 1 - Math.pow(1 - p, 3);
    el.textContent = prefix + (to * e).toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suffix;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

const ICON = {
  key: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M15 8l2 2"/></svg>',
  send: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  plus: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  out: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10"/></svg>',
  eye: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
  copy: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
  up: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10v11H3V10zM7 10l5-7a2 2 0 0 1 3 2l-1 5h6a2 2 0 0 1 2 2l-2 8a2 2 0 0 1-2 1H7"/></svg>',
  down: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 14V3h4v11zM17 14l-5 7a2 2 0 0 1-3-2l1-5H4a2 2 0 0 1-2-2l2-8a2 2 0 0 1 2-1h11"/></svg>',
  check: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-10"/></svg>',
  x: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
};

ICON.mic = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>';
ICON.stop = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
ICON.arrow = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M9 7h8v8"/></svg>';

// ===================================================== Voice
// Server voice (OpenAI) when available, otherwise the browser's own speech features.
const Voice = {
  server: null, rec: null, stream: null, chunks: [], ctx: null, raf: 0, started: 0, audio: null, playingBtn: null,

  async init() {
    if (this.server !== null) return this.server;
    try { this.server = (await api('/voice/status')).server; } catch { this.server = false; }
    return this.server;
  },
  canListen() { return !!(navigator.mediaDevices && window.MediaRecorder) || !!(window.SpeechRecognition || window.webkitSpeechRecognition); },

  // Start recording. draw(canvas) shows a live waveform; returns when recording has started.
  async start(canvas, lang) {
    await this.init();
    this.lang = lang;
    this.started = Date.now();
    if (this.server && navigator.mediaDevices && window.MediaRecorder) {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const type = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'].find(t => MediaRecorder.isTypeSupported(t)) || '';
      this.rec = new MediaRecorder(this.stream, type ? { mimeType: type } : undefined);
      this.chunks = [];
      this.rec.ondataavailable = e => e.data.size && this.chunks.push(e.data);
      this.rec.start(250);
      this._wave(canvas, this.stream);
      return 'server';
    }
    // browser fallback (Chrome / Edge / Safari)
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) throw new Error(L('Voice input is not supported in this browser. Please use Chrome.', 'இந்த browser-இல் குரல் உள்ளீடு இல்லை. Chrome பயன்படுத்தவும்.'));
    this.sr = new SR();
    this.sr.lang = lang === 'ta' ? 'ta-IN' : 'en-IN';
    this.sr.interimResults = true; this.sr.continuous = true;
    this.srText = '';
    this.sr.onresult = e => { this.srText = Array.from(e.results).map(r => r[0].transcript).join(' '); };
    this.sr.start();
    try { this.stream = await navigator.mediaDevices.getUserMedia({ audio: true }); this._wave(canvas, this.stream); } catch { this._wave(canvas, null); }
    return 'browser';
  },

  _wave(canvas, stream) {
    const g = canvas.getContext('2d'), dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * dpr; canvas.height = canvas.clientHeight * dpr;
    let analyser = null, data = null;
    if (stream) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = this.ctx.createAnalyser(); analyser.fftSize = 256;
      this.ctx.createMediaStreamSource(stream).connect(analyser);
      data = new Uint8Array(analyser.frequencyBinCount);
    }
    const bars = 48;
    const draw = () => {
      g.clearRect(0, 0, canvas.width, canvas.height);
      if (analyser) analyser.getByteFrequencyData(data);
      const w = canvas.width / bars;
      for (let i = 0; i < bars; i++) {
        const v = data ? data[Math.floor(i * data.length / bars / 1.6)] / 255 : (0.25 + 0.25 * Math.sin(Date.now() / 180 + i / 2));
        const h = Math.max(3 * dpr, v * canvas.height * 0.95);
        g.fillStyle = i % 7 === 0 ? '#E2531D' : '#121318';
        g.globalAlpha = 0.35 + v * 0.65;
        g.beginPath(); g.roundRect ? g.roundRect(i * w + w * 0.2, (canvas.height - h) / 2, w * 0.6, h, 2 * dpr) : g.rect(i * w + w * 0.2, (canvas.height - h) / 2, w * 0.6, h);
        g.fill();
      }
      g.globalAlpha = 1;
      this.raf = requestAnimationFrame(draw);
    };
    draw();
  },
  elapsed() { return Math.floor((Date.now() - this.started) / 1000); },
  _cleanup() {
    cancelAnimationFrame(this.raf);
    this.stream?.getTracks().forEach(t => t.stop()); this.stream = null;
    this.ctx?.close().catch(() => {}); this.ctx = null;
  },
  cancel() {
    try { this.rec?.state !== 'inactive' && this.rec?.stop(); } catch {}
    try { this.sr?.abort(); } catch {}
    this.rec = null; this.sr = null; this._cleanup();
  },
  // Stop and return the text that was said.
  async finish() {
    const secs = this.elapsed();
    if (this.rec) {
      const rec = this.rec;
      await new Promise(res => { rec.onstop = res; rec.stop(); });
      this._cleanup();
      const blob = new Blob(this.chunks, { type: rec.mimeType || 'audio/webm' });
      this.rec = null;
      if (blob.size < 1500) throw new Error(L('I could not hear anything. Please try again and speak a little longer.', 'எதுவும் கேட்கவில்லை. இன்னும் கொஞ்சம் நேரம் பேசி மீண்டும் முயற்சிக்கவும்.'));
      const res = await fetch(`/voice/transcribe?lang=${this.lang}&secs=${secs}`, { method: 'POST', headers: { 'Content-Type': blob.type, Authorization: 'Bearer ' + Auth.token }, body: blob });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(L(data.detail || 'Could not understand the recording.', 'பதிவைப் புரிந்துகொள்ள முடியவில்லை. மீண்டும் முயற்சிக்கவும்.'));
      return data.text;
    }
    const sr = this.sr;
    await new Promise(res => { sr.onend = res; sr.stop(); setTimeout(res, 1500); });
    this.sr = null; this._cleanup();
    if (!this.srText.trim()) throw new Error(L('I could not hear anything. Please try again.', 'எதுவும் கேட்கவில்லை. மீண்டும் முயற்சிக்கவும்.'));
    return this.srText.trim();
  },

  // ---- read an answer aloud
  stopSpeaking() {
    if (this.audio) { this.audio.pause(); this.audio = null; }
    if (window.speechSynthesis) speechSynthesis.cancel();
    this.playingBtn?.classList.remove('playing', 'loading'); this.playingBtn = null;
  },
  clean(text) { return String(text).replace(/\[\d{1,2}\]/g, '').replace(/[*_`#>]/g, '').replace(/^\s*[-•]\s*/gm, '').trim(); },
  async speak(text, lang, btn) {
    if (btn && this.playingBtn === btn) { this.stopSpeaking(); return; }
    this.stopSpeaking();
    await this.init();
    this.playingBtn = btn; btn?.classList.add('loading');
    const done = () => { if (this.playingBtn === btn) { btn?.classList.remove('playing', 'loading'); this.playingBtn = null; } };
    if (this.server) {
      try {
        const res = await fetch('/voice/speak', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + Auth.token }, body: JSON.stringify({ text, lang }) });
        if (!res.ok) throw new Error(L((await res.json().catch(() => ({}))).detail || 'Audio failed', 'குரல் பதில் இயங்கவில்லை.'));
        if (this.playingBtn !== btn) return;
        this.audio = new Audio(URL.createObjectURL(await res.blob()));
        this.audio.onended = done; this.audio.onerror = done;
        btn?.classList.remove('loading'); btn?.classList.add('playing');
        await this.audio.play();
        return;
      } catch (e) { console.warn('server voice failed, using browser voice', e); }
    }
    if (!window.speechSynthesis) { done(); throw new Error(L('Spoken answers are not supported in this browser.', 'இந்த browser-இல் குரல் பதில் இல்லை.')); }
    const u = new SpeechSynthesisUtterance(this.clean(text));
    u.lang = lang === 'ta' ? 'ta-IN' : 'en-IN';
    const v = speechSynthesis.getVoices().find(x => x.lang.toLowerCase().startsWith(lang === 'ta' ? 'ta' : 'en-in')) || speechSynthesis.getVoices().find(x => x.lang.startsWith(lang === 'ta' ? 'ta' : 'en'));
    if (v) u.voice = v;
    u.onend = done; u.onerror = done;
    btn?.classList.remove('loading'); btn?.classList.add('playing');
    speechSynthesis.speak(u);
  },
};

// Moving "privacy network" animation (used on the sign-in page)
function networkCanvas(canvas) {
  const g = canvas.getContext('2d'), dpr = window.devicePixelRatio || 1;
  let W, H, pts;
  const resize = () => {
    W = canvas.width = canvas.clientWidth * dpr; H = canvas.height = canvas.clientHeight * dpr;
    pts = Array.from({ length: Math.round(W * H / (dpr * dpr * 9000)) }, () => ({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * .35 * dpr, vy: (Math.random() - .5) * .35 * dpr, hot: Math.random() < .12 }));
  };
  resize(); addEventListener('resize', resize);
  let mx = -1e4, my = -1e4;
  canvas.parentElement.addEventListener('mousemove', e => { const r = canvas.getBoundingClientRect(); mx = (e.clientX - r.left) * dpr; my = (e.clientY - r.top) * dpr; });
  const link = 120 * dpr;
  (function frame() {
    g.clearRect(0, 0, W, H);
    for (const p of pts) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H) p.vy *= -1;
      const dm = Math.hypot(p.x - mx, p.y - my);
      if (dm < 140 * dpr) { p.x += (p.x - mx) / dm * .6; p.y += (p.y - my) / dm * .6; }
    }
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
      const a = pts[i], b = pts[j], d = Math.hypot(a.x - b.x, a.y - b.y);
      if (d < link) { g.strokeStyle = (a.hot || b.hot) ? `rgba(226,83,29,${(1 - d / link) * .55})` : `rgba(255,255,255,${(1 - d / link) * .16})`; g.lineWidth = dpr; g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke(); }
    }
    for (const p of pts) { g.fillStyle = p.hot ? '#E2531D' : 'rgba(255,255,255,.55)'; g.beginPath(); g.arc(p.x, p.y, (p.hot ? 2.6 : 1.6) * dpr, 0, 6.3); g.fill(); }
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) requestAnimationFrame(frame);
  })();
}
function bgFx() { const d = document.createElement('div'); d.className = 'bg-fx'; d.setAttribute('aria-hidden', 'true'); d.innerHTML = '<i></i><i></i><i></i>'; document.body.prepend(d); }

// ---- small dialog used by "Change password" (app + admin) and the admin's reset-link box
function modal(html) {
  const root = document.createElement('div');
  root.innerHTML = `<div class="drawer-bg"></div><div class="modal" role="dialog" aria-modal="true">${html}</div>`;
  document.body.appendChild(root);
  const close = () => { root.remove(); document.removeEventListener('keydown', onKey); };
  const onKey = e => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', onKey);
  root.querySelector('.drawer-bg').onclick = close;
  root.querySelectorAll('[data-close]').forEach(b => b.onclick = close);
  return { el: root.querySelector('.modal'), close };
}

function passwordDialog() {
  const pwOk = v => v.length >= 8 && /[A-Za-z]/.test(v) && /\d/.test(v);
  const m = modal(`
    <h3>${L('Change password', 'கடவுச்சொல்லை மாற்று')}</h3>
    <p class="muted" style="margin:0 0 14px;font-size:13.5px">${L('Your other devices will be signed out.', 'உங்கள் மற்ற சாதனங்களிலிருந்து வெளியேற்றப்படும்.')}</p>
    <form id="pwForm" novalidate>
      <div class="field"><label for="pwCur">${L('Current password', 'தற்போதைய கடவுச்சொல்')}</label><input class="input" id="pwCur" type="password" autocomplete="current-password"></div>
      <div class="field"><label for="pwNew">${L('New password', 'புதிய கடவுச்சொல்')}</label><input class="input" id="pwNew" type="password" autocomplete="new-password">
        <div class="hint">${L('8+ characters, with a letter and a number', '8+ எழுத்துகள், ஒரு எழுத்து மற்றும் ஒரு எண்ணுடன்')}</div></div>
      <div class="field"><label for="pwNew2">${L('Repeat new password', 'புதிய கடவுச்சொல்லை மீண்டும்')}</label><input class="input" id="pwNew2" type="password" autocomplete="new-password"></div>
      <div class="form-error hidden" id="pwErr" role="alert"></div>
      <div class="row"><button type="button" class="btn btn-ghost" data-close>${L('Cancel', 'ரத்து')}</button>
        <button class="btn btn-primary" id="pwSave" type="submit">${L('Save new password', 'புதிய கடவுச்சொல்லை சேமி')}</button></div>
    </form>`);
  const $m = id => m.el.querySelector('#' + id), err = t => { $m('pwErr').textContent = t; $m('pwErr').classList.remove('hidden'); };
  $m('pwCur').focus();
  $m('pwForm').onsubmit = async e => {
    e.preventDefault(); $m('pwErr').classList.add('hidden');
    const cur = $m('pwCur').value, nw = $m('pwNew').value;
    if (!cur) return err(L('Enter your current password.', 'தற்போதைய கடவுச்சொல்லை உள்ளிடுங்கள்.'));
    if (!pwOk(nw)) return err(L('New password needs 8+ characters with a letter and a number.', 'புதிய கடவுச்சொல்லில் 8+ எழுத்துகள், ஒரு எழுத்து, ஒரு எண் வேண்டும்.'));
    if (nw !== $m('pwNew2').value) return err(L('The two new passwords do not match.', 'இரண்டு புதிய கடவுச்சொற்களும் ஒன்றாக இல்லை.'));
    $m('pwSave').disabled = true;
    try {
      await api('/me/password', { method: 'POST', body: { current: cur, new: nw } });
      m.close(); toast(L('Password changed.', 'கடவுச்சொல் மாற்றப்பட்டது.'));
    } catch (ex) {
      const ta = { 'Your current password is not correct.': 'தற்போதைய கடவுச்சொல் தவறு.', 'Choose a password different from the current one.': 'தற்போதையதிலிருந்து வேறு கடவுச்சொல்லைத் தேர்ந்தெடுங்கள்.' };
      err(L(ex.message, ta[ex.message] || ex.message)); $m('pwSave').disabled = false;
    }
  };
}
