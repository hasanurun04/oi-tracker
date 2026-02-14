/* ═══════════════════════════════════════════
   OI TRACKER — Frontend Logic v2
═══════════════════════════════════════════ */

const API          = '';
const MAX_CARDS    = 4;
const REFRESH_SEC  = 30;
const CIRCUMFERENCE = 94.25;

/* ── STATE ──────────────────────────────── */
let allSymbols  = [];   // [{ symbol, supported }]
let tracked     = [];   // [{ symbol, supported }]
let selectedSym = null;
let countdown   = REFRESH_SEC;

/* ── DOM — sayfa yüklenince al ─────────── */
let $search, $dropdown, $btnAdd, $slotUsed,
    $grid, $empty, $cdNum, $ring, $statusDot, $statusLbl;

document.addEventListener('DOMContentLoaded', () => {
  $search    = document.getElementById('searchInput');
  $dropdown  = document.getElementById('searchDropdown');
  $btnAdd    = document.getElementById('btnAdd');
  $slotUsed  = document.getElementById('slotUsed');
  $grid      = document.getElementById('cardsGrid');
  $empty     = document.getElementById('emptyState');
  $cdNum     = document.getElementById('countdownNum');
  $ring      = document.getElementById('ringFill');
  $statusDot = document.getElementById('statusDot');
  $statusLbl = document.getElementById('statusLabel');

  init();
});

/* ══════════════════════════════════════════
   INIT
══════════════════════════════════════════ */
async function init() {
  setStatus('loading', 'YÜKLENIYOR');
  await loadSymbols();
  setupSearch();
  await restoreTracked();
  startCountdown();
  setStatus('active', 'CANLI');
}

function saveTracked() {
  try { localStorage.setItem('oi_tracked', JSON.stringify(tracked)); } catch(e) {}
}

async function restoreTracked() {
  try {
    const saved = JSON.parse(localStorage.getItem('oi_tracked') || '[]');
    for (const t of saved) {
      if (tracked.length >= MAX_CARDS) break;
      tracked.push(t);
      createCard(t.symbol);
      await fetchCard(t.symbol);
    }
    updateSlotCounter();
    updateEmptyState();
  } catch(e) {}
}

/* ══════════════════════════════════════════
   SYMBOLS
══════════════════════════════════════════ */
async function loadSymbols() {
  try {
    const res   = await fetch(`${API}/api/symbols`);
    const data  = await res.json();
    allSymbols  = data;
  } catch (e) {
    setStatus('error', 'BAĞLANTI HATASI');
    console.error('Sembol listesi yüklenemedi:', e);
  }
}

/* ══════════════════════════════════════════
   SEARCH
══════════════════════════════════════════ */
function setupSearch() {
  $search.addEventListener('input',   onSearchInput);
  $search.addEventListener('keydown', onSearchKeydown);
  $search.addEventListener('focus',   () => {
    if ($search.value.trim()) renderDropdown($search.value.trim().toUpperCase());
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-field-wrap')) closeDropdown();
  });

  $btnAdd.addEventListener('click', addSelected);
}

function onSearchInput() {
  const q = $search.value.trim().toUpperCase();
  selectedSym      = null;
  $btnAdd.disabled = true;
  if (!q) { closeDropdown(); return; }
  renderDropdown(q);
}

function renderDropdown(q) {
  const filtered = allSymbols.filter(s => s.symbol.includes(q)).slice(0, 30);

  if (!filtered.length) {
    $dropdown.innerHTML = `<div class="dd-empty">Sonuç yok: ${q}</div>`;
    $dropdown.classList.add('open');
    return;
  }

  $dropdown.innerHTML = filtered.map(s => `
    <div class="dd-item" data-sym="${s.symbol}" data-sup="${s.supported}">
      <span class="dd-sym">${s.symbol}</span>
      <span class="dd-badge ${s.supported ? '' : 'unsupported'}">
        ${s.supported ? 'OI/SUPPLY' : 'SADECE OI'}
      </span>
    </div>
  `).join('');

  $dropdown.classList.add('open');

  $dropdown.querySelectorAll('.dd-item').forEach(el => {
    el.addEventListener('click', () => selectSymbol(el.dataset.sym, el.dataset.sup === 'true'));
  });
}

function selectSymbol(sym, supported) {
  selectedSym      = { symbol: sym, supported };
  $search.value    = sym;
  closeDropdown();

  const alreadyTracked = tracked.some(t => t.symbol === sym);
  const full           = tracked.length >= MAX_CARDS;
  $btnAdd.disabled     = alreadyTracked || full;
}

function onSearchKeydown(e) {
  const items   = $dropdown.querySelectorAll('.dd-item');
  const current = $dropdown.querySelector('.dd-item.selected');

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (!current && items[0]) items[0].classList.add('selected');
    else if (current?.nextElementSibling) {
      current.classList.remove('selected');
      current.nextElementSibling.classList.add('selected');
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (current?.previousElementSibling) {
      current.classList.remove('selected');
      current.previousElementSibling.classList.add('selected');
    }
  } else if (e.key === 'Enter') {
    const sel = $dropdown.querySelector('.dd-item.selected');
    if (sel) selectSymbol(sel.dataset.sym, sel.dataset.sup === 'true');
    else if (selectedSym && !$btnAdd.disabled) addSelected();
  } else if (e.key === 'Escape') {
    closeDropdown();
  }
}

function closeDropdown() {
  $dropdown.classList.remove('open');
}

/* ══════════════════════════════════════════
   ADD / REMOVE
══════════════════════════════════════════ */
function addSelected() {
  if (!selectedSym) return;
  if (tracked.length >= MAX_CARDS) return;
  if (tracked.some(t => t.symbol === selectedSym.symbol)) return;

  tracked.push(selectedSym);
  $search.value    = '';
  selectedSym      = null;
  $btnAdd.disabled = true;

  saveTracked();
  updateSlotCounter();
  updateEmptyState();
  createCard(tracked[tracked.length - 1].symbol);
  fetchCard(tracked[tracked.length - 1].symbol);
}

function removeCard(symbol) {
  tracked = tracked.filter(t => t.symbol !== symbol);
  saveTracked();
  const el = document.getElementById(`card-${symbol}`);
  if (el) {
    el.style.opacity   = '0';
    el.style.transform = 'translateY(-8px)';
    el.style.transition = 'opacity .25s, transform .25s';
    setTimeout(() => el.remove(), 260);
  }
  updateSlotCounter();
  updateEmptyState();
}

function updateSlotCounter() {
  $slotUsed.textContent = tracked.length;
}

function updateEmptyState() {
  if (tracked.length === 0) $empty.classList.remove('hidden');
  else $empty.classList.add('hidden');
}

/* ══════════════════════════════════════════
   CARD RENDER
══════════════════════════════════════════ */
function createCard(symbol) {
  const el       = document.createElement('div');
  el.className   = 'card';
  el.id          = `card-${symbol}`;
  el.innerHTML   = `
    <div class="card-head">
      <span class="card-symbol">${symbol}</span>
      <span class="card-badge">FUTURES</span>
      <button class="card-close" title="Kaldır">&#x2715;</button>
    </div>
    <div class="card-loader">
      <div class="loader-dots"><span></span><span></span><span></span></div>
    </div>
  `;
  el.querySelector('.card-close').addEventListener('click', () => removeCard(symbol));
  $grid.appendChild(el);
}

function renderCardData(symbol, data) {
  const el = document.getElementById(`card-${symbol}`);
  if (!el) return;

  const price    = formatPrice(data.price);
  const chgSign  = data.change_pct >= 0 ? '+' : '';
  const chgCls   = data.change_pct >= 0 ? 'up' : 'down';
  const oi       = formatNumber(data.open_interest);
  const oiUSDT   = formatUSDT(data.open_interest_usdt);
  const supply   = data.circulating_supply ? formatNumber(data.circulating_supply) : '—';
  const vol24    = formatUSDT(data.volume_usdt);
  const now      = new Date().toLocaleTimeString('tr-TR');

  const { ratioText, ratioClass, barClass, barWidth, signalClass, signalText } = calcRatio(data.oi_supply_ratio);

  el.innerHTML = `
    <div class="card-head">
      <span class="card-symbol">${symbol}</span>
      <span class="card-badge">FUTURES</span>
      <button class="card-close" title="Kaldır">&#x2715;</button>
    </div>

    <div class="card-price-row">
      <span class="card-price">$${price}</span>
      <span class="card-change ${chgCls}">${chgSign}${data.change_pct.toFixed(2)}%</span>
    </div>

    <div class="card-metrics">
      <div class="metric">
        <span class="metric-label">OPEN INTEREST</span>
        <span class="metric-value cyan">${oi}</span>
      </div>
      <div class="metric">
        <span class="metric-label">OI (USDT)</span>
        <span class="metric-value">${oiUSDT}</span>
      </div>
      <div class="metric">
        <span class="metric-label">CIRC. SUPPLY</span>
        <span class="metric-value">${supply}</span>
      </div>
      <div class="metric">
        <span class="metric-label">24H HACIM</span>
        <span class="metric-value dim">${vol24}</span>
      </div>
    </div>

    <div class="card-ratio">
      <div class="ratio-header">
        <span class="ratio-label">OI / SUPPLY ORANI</span>
        <span class="ratio-number ${ratioClass}">${ratioText}</span>
      </div>
      <div class="ratio-bar">
        <div class="ratio-bar-fill ${barClass}" style="width:${barWidth}%"></div>
      </div>
      <div class="ratio-ticks">
        <span class="ratio-tick">0%</span>
        <span class="ratio-tick">1%</span>
        <span class="ratio-tick">2%</span>
        <span class="ratio-tick">3%</span>
        <span class="ratio-tick">5%+</span>
      </div>
    </div>

    <div class="card-signal ${signalClass}">
      <span class="signal-dot"></span>
      <span class="signal-text">${signalText}</span>
    </div>

    <div class="card-foot">
      <span class="card-updated">SON: <span>${now}</span></span>
      <button class="card-refresh" data-sym="${symbol}" title="Yenile">&#x21BB;</button>
    </div>
  `;

  el.querySelector('.card-close').addEventListener('click', () => removeCard(symbol));
  el.querySelector('.card-refresh').addEventListener('click', () => fetchCard(symbol));
  el.classList.remove('flash');
  void el.offsetWidth;
  el.classList.add('flash');
}

function renderCardError(symbol, msg) {
  const el = document.getElementById(`card-${symbol}`);
  if (!el) return;
  el.innerHTML = `
    <div class="card-head">
      <span class="card-symbol">${symbol}</span>
      <span class="card-badge">FUTURES</span>
      <button class="card-close" title="Kaldır">&#x2715;</button>
    </div>
    <div class="card-error-msg">Veri alinamadi<br/><small>${msg}</small></div>
    <div class="card-foot"><span class="card-updated">HATA</span></div>
  `;
  el.querySelector('.card-close').addEventListener('click', () => removeCard(symbol));
}

/* ══════════════════════════════════════════
   FETCH
══════════════════════════════════════════ */
async function fetchCard(symbol) {
  try {
    const res = await fetch(`${API}/api/coin/${symbol}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      renderCardError(symbol, err.detail || `HTTP ${res.status}`);
      return;
    }
    const data = await res.json();
    renderCardData(symbol, data);
  } catch (e) {
    renderCardError(symbol, 'Sunucuya bağlanılamadı');
  }
}

async function refreshAll() {
  if (!tracked.length) return;
  setStatus('loading', 'YENİLENİYOR');
  await Promise.all(tracked.map(t => fetchCard(t.symbol)));
  setStatus('active', 'CANLI');
}

/* ══════════════════════════════════════════
   COUNTDOWN
══════════════════════════════════════════ */
function startCountdown() {
  setInterval(async () => {
    countdown--;
    const offset = CIRCUMFERENCE * (1 - countdown / REFRESH_SEC);
    $ring.style.strokeDashoffset = offset;
    $cdNum.textContent = countdown;
    if (countdown <= 5) $ring.classList.add('urgent');
    else $ring.classList.remove('urgent');

    if (countdown <= 0) {
      countdown = REFRESH_SEC;
      $ring.style.strokeDashoffset = 0;
      await refreshAll();
    }
  }, 1000);
}

/* ══════════════════════════════════════════
   STATUS
══════════════════════════════════════════ */
function setStatus(state, label) {
  $statusDot.className  = `status-dot ${state}`;
  $statusLbl.textContent = label;
}

/* ══════════════════════════════════════════
   RATIO
══════════════════════════════════════════ */
function calcRatio(ratio) {
  if (ratio == null) return {
    ratioText: 'N/A', ratioClass: 'na', barClass: '',
    barWidth: 0, signalClass: 'signal-na', signalText: 'Supply verisi yok',
  };

  const ratioText = '%' + ratio.toFixed(3);
  const barWidth  = Math.min((ratio / 5) * 100, 100);

  if (ratio < 1)  return { ratioText, ratioClass: '',     barClass: '',     barWidth, signalClass: 'signal-low',  signalText: 'Düşük kaldıraç — piyasa sakin' };
  if (ratio < 3)  return { ratioText, ratioClass: 'warn', barClass: 'warn', barWidth, signalClass: 'signal-mid',  signalText: 'Orta kaldıraç — dikkatli ol' };
  return            { ratioText, ratioClass: 'hot',  barClass: 'hot',  barWidth, signalClass: 'signal-high', signalText: 'Yüksek kaldıraç — squeeze riski!' };
}

/* ══════════════════════════════════════════
   FORMAT
══════════════════════════════════════════ */
function formatPrice(n) {
  if (n >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (n >= 1)    return n.toFixed(4);
  return n.toFixed(6);
}

function formatNumber(n) {
  if (n == null) return '—';
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatUSDT(n) {
  if (n == null) return '—';
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}