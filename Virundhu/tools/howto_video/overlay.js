window.__demo = {
  ensure() {
    if (document.getElementById('demo-cap')) return;
    const st = document.createElement('style');
    st.textContent = `
      [data-sonner-toaster]{top:auto!important;bottom:28px!important}
      #demo-cap{position:fixed;left:50%;top:14px;transform:translateX(-50%);z-index:99999;width:min(760px,64vw);margin-left:130px;
        background:#11132a;color:#fbf6ec;border-radius:18px;padding:14px 20px 15px 20px;box-shadow:0 14px 40px rgba(17,19,42,.35);
        border-left:6px solid #f6b93b;transition:opacity .35s, transform .35s;font-family:'Hind Madurai',system-ui}
      #demo-cap.public{margin-left:0}
      #demo-cap .k{font:700 13px/1 'Hind Madurai',system-ui;color:#f6b93b;letter-spacing:.02em}
      #demo-cap .t{font:800 24px/1.15 'Anek Tamil Variable','Anek Tamil',system-ui;font-variation-settings:'wdth' 110;margin-top:6px}
      #demo-cap .b{font:500 17px/1.45 'Hind Madurai',system-ui;color:#d9dbef;margin-top:5px}
      #demo-dot{position:fixed;z-index:99998;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;background:rgba(246,185,59,.35);
        border:3px solid #f6b93b;box-shadow:0 0 0 0 rgba(246,185,59,.6);transition:left .7s cubic-bezier(.2,.8,.2,1),top .7s cubic-bezier(.2,.8,.2,1),transform .15s;
        left:50%;top:50%;pointer-events:none;opacity:0}
      #demo-dot.on{opacity:1;animation:dp 1.6s infinite}
      @keyframes dp{0%{box-shadow:0 0 0 0 rgba(246,185,59,.55)}100%{box-shadow:0 0 0 18px rgba(246,185,59,0)}}
      #demo-title{position:fixed;inset:0;z-index:100000;background:#11132a;color:#fbf6ec;display:flex;align-items:center;justify-content:center;gap:48px;
        font-family:'Anek Tamil Variable',system-ui;transition:opacity .5s}
      #demo-title img{width:190px;height:190px;border-radius:50%;object-fit:cover;object-position:50% 30%;border:6px solid #f6b93b}
      #demo-title h1{font-size:60px;font-weight:800;font-variation-settings:'wdth' 115;margin:0;line-height:1}
      #demo-title p{color:#f6b93b;font-size:24px;margin:14px 0 0;font-family:'Hind Madurai'}
      #demo-title small{display:block;color:#a9acd0;font-size:18px;margin-top:22px;font-family:'Hind Madurai'}`;
    document.head.appendChild(st);
    const c = document.createElement('div'); c.id = 'demo-cap'; c.style.opacity = 0; document.body.appendChild(c);
    const d = document.createElement('div'); d.id = 'demo-dot'; document.body.appendChild(d);
  },
  cap(k, t, b) {
    this.ensure(); const c = document.getElementById('demo-cap');
    c.classList.toggle('public', !document.querySelector('aside nav, aside a[href="/app"]'));
    if (!t) { c.style.opacity = 0; return; }
    c.innerHTML = `<div class="k">${k}</div><div class="t">${t}</div><div class="b">${b}</div>`; c.style.opacity = 1;
  },
  dot(x, y, press) { this.ensure(); const d = document.getElementById('demo-dot'); d.classList.add('on'); d.style.left = x + 'px'; d.style.top = y + 'px';
    if (press) { d.style.transform = 'scale(.65)'; setTimeout(() => d.style.transform = 'scale(1)', 200); } },
  hideDot() { const d = document.getElementById('demo-dot'); if (d) d.classList.remove('on'); },
  title(h, p, small, img) { this.ensure(); const el = document.createElement('div'); el.id = 'demo-title';
    el.innerHTML = (img ? `<img src="${img}">` : '') + `<div><h1>${h}</h1><p>${p}</p>${small ? `<small>${small}</small>` : ''}</div>`; document.body.appendChild(el); },
  untitle() { const el = document.getElementById('demo-title'); if (el) { el.style.opacity = 0; setTimeout(() => el.remove(), 500); } },
};
