const SCRAMBLE_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
function runScramble(el) {
  const finalText = el.textContent.trim();
  let frame = 0;
  const queue = [];
  for (let i = 0; i < finalText.length; i++) {
    const ch = finalText[i];
    const isFixed = ch === ' ' || /[^a-zA-Z0-9]/.test(ch);
    const start = Math.floor(Math.random() * 14);
    const end = start + 6 + Math.floor(Math.random() * 6);
    queue.push({ ch, isFixed, start, end });
  }
  function update() {
    let out = '', done = 0;
    for (const q of queue) {
      if (q.isFixed) { out += q.ch; done++; continue; }
      if (frame >= q.end) { out += q.ch; done++; }
      else if (frame >= q.start) { out += SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)]; }
      else { out += ''; }
    }
    el.textContent = out;
    if (done < queue.length) { frame++; requestAnimationFrame(update); }
  }
  update();
}
function initDecode() {
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('[data-decode]').forEach(el => {
    if (prefersReduced) return;
    setTimeout(() => runScramble(el), 100);
  });
}
function initHoverScramble() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('[data-hover-decode]').forEach(el => {
    let running = false;
    el.addEventListener('mouseenter', () => {
      if (running) return;
      running = true;
      runScramble(el);
      setTimeout(() => { running = false; }, 800);
    });
  });
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { initDecode(); initHoverScramble(); });
} else { initDecode(); initHoverScramble(); }
