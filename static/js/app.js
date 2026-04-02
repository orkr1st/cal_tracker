'use strict';

// ── Macro definitions (shared) ────────────────────────────────────────────────
const MACRO_DEFS = [
  { key: 'calories',  label: 'kcal',    cls: 'mc-cal',  unit: ''  },
  { key: 'protein_g', label: 'protein', cls: 'mc-prot', unit: 'g' },
  { key: 'carbs_g',   label: 'carbs',   cls: 'mc-carb', unit: 'g' },
  { key: 'fat_g',     label: 'fat',     cls: 'mc-fat',  unit: 'g' },
];

function fmtMacro(val, unit) {
  return (val !== null && val !== undefined)
    ? (Math.round(val * 10) / 10) + unit
    : '—';
}

function round1(v) { return Math.round(v * 10) / 10; }

// ── Portion parser (mirrors services/portion_parser.py) ───────────────────────
const _UNIT_GRAMS = {
  g: 1, gram: 1, grams: 1,
  kg: 1000, kilogram: 1000, kilograms: 1000,
  oz: 28.35, ounce: 28.35, ounces: 28.35,
  lb: 453.59, lbs: 453.59, pound: 453.59, pounds: 453.59,
  ml: 1, milliliter: 1, milliliters: 1, millilitre: 1, millilitres: 1,
  l: 1000, liter: 1000, liters: 1000, litre: 1000, litres: 1000,
  cup: 240, cups: 240,
  tbsp: 15, tablespoon: 15, tablespoons: 15,
  tsp: 5, teaspoon: 5, teaspoons: 5,
  slice: 30, slices: 30,
  piece: 50, pieces: 50,
  serving: 100, servings: 100,
};

function parseQuantity(qty) {
  if (!qty) return 1.0;
  const m = qty.match(/(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)/i);
  if (!m) return 1.0;
  const amount = parseFloat(m[1].replace(',', '.'));
  const unit = m[2].toLowerCase();
  const gramsPerUnit = _UNIT_GRAMS[unit];
  if (!gramsPerUnit) return 1.0;
  return (amount * gramsPerUnit) / 100.0;
}

// ── State ────────────────────────────────────────────────────────────────────
let stream        = null;
let capturedBlob  = null;
let _cardMacros   = []; // live macros for each food card (updated on qty change)

// ── Elements ─────────────────────────────────────────────────────────────────
const body            = document.body;
const video           = document.getElementById('video');
const canvas          = document.getElementById('canvas');
const preview         = document.getElementById('preview');
const fileInput       = document.getElementById('file-input');
const camPlaceholder  = document.getElementById('cam-placeholder');

const btnCamera       = document.getElementById('btn-camera');
const btnUpload       = document.getElementById('btn-upload');
const btnCapture      = document.getElementById('btn-capture');
const btnCancelCam    = document.getElementById('btn-cancel-camera');
const btnAnalyze      = document.getElementById('btn-analyze');
const btnRetake       = document.getElementById('btn-retake');
const btnNew          = document.getElementById('btn-new');

const captureControls = document.getElementById('capture-controls');
const previewControls = document.getElementById('preview-controls');
const actionsDiv      = document.getElementById('actions');

const foodCards       = document.getElementById('food-cards');
const totalsCard      = document.getElementById('totals-card');
const totalsRow       = document.getElementById('totals-row');
const resultsCount    = document.getElementById('results-count');
const noFoodMsg       = document.getElementById('no-food-msg');

const btnOpenDiary        = document.getElementById('btn-open-diary');
const btnDiaryFromResults = document.getElementById('btn-diary-from-results');
const btnBackFromDiary    = document.getElementById('btn-back-from-diary');
const btnPrevDay          = document.getElementById('btn-prev-day');
const btnNextDay          = document.getElementById('btn-next-day');
const diaryDateEl         = document.getElementById('diary-date');
const progressBars        = document.getElementById('progress-bars');
const diaryEntries        = document.getElementById('diary-entries');
const diaryEmptyMsg       = document.getElementById('diary-empty-msg');

// ── State helpers ─────────────────────────────────────────────────────────────
function showState(state) { body.className = 'state-' + state; }

function resetToInput() {
  stopCamera();
  capturedBlob = null;
  video.hidden = true;
  preview.hidden = true;
  preview.src = '';
  camPlaceholder.hidden = false;
  captureControls.hidden = true;
  previewControls.hidden = true;
  actionsDiv.hidden = false;
  showState('input');
}

// ── Camera ────────────────────────────────────────────────────────────────────
btnCamera.addEventListener('click', startCamera);
btnCancelCam.addEventListener('click', resetToInput);
btnCapture.addEventListener('click', captureFrame);

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 960 } },
      audio: false,
    });
    video.srcObject = stream;
    video.hidden = false;
    camPlaceholder.hidden = true;
    preview.hidden = true;
    actionsDiv.hidden = true;
    captureControls.hidden = false;
    previewControls.hidden = true;
  } catch (err) {
    alert('Camera not available: ' + err.message + '\n\nTry uploading a photo instead.');
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  video.srcObject = null;
}

function captureFrame() {
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob(blob => {
    capturedBlob = blob;
    showPreview(URL.createObjectURL(blob));
    stopCamera();
    video.hidden = true;
    captureControls.hidden = true;
    previewControls.hidden = false;
  }, 'image/jpeg', 0.9);
}

// ── File upload ───────────────────────────────────────────────────────────────
btnUpload.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) return;
  capturedBlob = file;
  showPreview(URL.createObjectURL(file));
  actionsDiv.hidden = true;
  previewControls.hidden = false;
  fileInput.value = '';
});

function showPreview(url) {
  camPlaceholder.hidden = true;
  preview.src = url;
  preview.hidden = false;
}

// ── Retake / New ──────────────────────────────────────────────────────────────
btnRetake.addEventListener('click', resetToInput);
btnNew.addEventListener('click', resetToInput);

// ── Analyse ───────────────────────────────────────────────────────────────────
btnAnalyze.addEventListener('click', analyze);

async function analyze() {
  if (!capturedBlob) return;
  showState('loading');

  const fd = new FormData();
  fd.append('image', capturedBlob, 'food.jpg');

  try {
    const resp = await fetch('/api/analyze', { method: 'POST', body: fd });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Server error');
    renderResults(data.foods || []);
  } catch (err) {
    showState('input');
    previewControls.hidden = false;
    actionsDiv.hidden = true;
    alert('Analysis failed: ' + err.message);
  }
}

// ── Render results ────────────────────────────────────────────────────────────
function renderResults(foods) {
  while (foodCards.firstChild) foodCards.removeChild(foodCards.firstChild);
  while (totalsRow.firstChild)  totalsRow.removeChild(totalsRow.firstChild);
  totalsCard.hidden = true;
  noFoodMsg.hidden  = true;
  _cardMacros = [];

  animateCount(0, foods.length);

  if (foods.length === 0) {
    noFoodMsg.hidden = false;
    showState('results');
    return;
  }

  foods.forEach((food, i) => {
    _cardMacros.push({
      calories:  food.calories,
      protein_g: food.protein_g,
      carbs_g:   food.carbs_g,
      fat_g:     food.fat_g,
    });
    foodCards.appendChild(buildFoodCard(food, i, newMacros => {
      _cardMacros[i] = newMacros;
      refreshTotals();
    }));
  });

  refreshTotals();
  showState('results');
}

function refreshTotals() {
  while (totalsRow.firstChild) totalsRow.removeChild(totalsRow.firstChild);
  if (_cardMacros.length <= 1) { totalsCard.hidden = true; return; }

  const totals = { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 };
  let hasCalories = false;
  _cardMacros.forEach(m => {
    if (m.calories  !== null) { totals.calories  += m.calories;  hasCalories = true; }
    if (m.protein_g !== null)   totals.protein_g += m.protein_g;
    if (m.carbs_g   !== null)   totals.carbs_g   += m.carbs_g;
    if (m.fat_g     !== null)   totals.fat_g     += m.fat_g;
  });

  if (!hasCalories) { totalsCard.hidden = true; return; }
  buildMacroCells(totals).forEach(cell => totalsRow.appendChild(cell));
  totalsCard.hidden = false;
}

// ── Build food card ───────────────────────────────────────────────────────────
function buildFoodCard(food, index, onMacrosChanged) {
  const card = document.createElement('div');
  card.className = 'food-card';
  card.style.animationDelay = `${index * 0.07}s`;

  // Name
  const name = document.createElement('div');
  name.className = 'food-name';
  name.textContent = food.name;
  card.appendChild(name);

  // Editable quantity
  const qtyInput = document.createElement('input');
  qtyInput.type = 'text';
  qtyInput.className = 'food-qty-input';
  qtyInput.value = food.quantity || '';
  qtyInput.placeholder = 'e.g. 200g';
  qtyInput.setAttribute('aria-label', 'quantity');
  card.appendChild(qtyInput);

  // AI estimate badge
  if (food.estimated) {
    const badge = document.createElement('span');
    badge.className = 'est-badge';
    badge.textContent = '~ AI estimate';
    card.appendChild(badge);
  }

  // Macro grid with tracked value spans for live updates
  const grid = document.createElement('div');
  grid.className = 'macro-grid';
  const valueEls = {};
  MACRO_DEFS.forEach(def => {
    const cell = document.createElement('div');
    cell.className = 'macro-cell ' + def.cls;

    const lbl = document.createElement('span');
    lbl.className = 'mc-label';
    lbl.textContent = def.label;

    const num = document.createElement('span');
    num.className = 'mc-value';
    num.textContent = fmtMacro(food[def.key], def.unit);

    cell.appendChild(lbl);
    cell.appendChild(num);
    grid.appendChild(cell);
    valueEls[def.key] = num;
  });
  card.appendChild(grid);

  // Track the current (possibly adjusted) macros for this card
  let liveMacros = {
    calories:  food.calories,
    protein_g: food.protein_g,
    carbs_g:   food.carbs_g,
    fat_g:     food.fat_g,
  };

  // Quantity input → recalculate macros from per-100g base
  qtyInput.addEventListener('input', () => {
    const mult = parseQuantity(qtyInput.value.trim()) || 1.0;
    const newMacros = {};
    MACRO_DEFS.forEach(def => {
      const base = food.per_100g ? food.per_100g[def.key] : null;
      newMacros[def.key] = (base !== null && base !== undefined)
        ? round1(base * mult)
        : null;
    });
    MACRO_DEFS.forEach(def => {
      valueEls[def.key].textContent = fmtMacro(newMacros[def.key], def.unit);
    });
    liveMacros = newMacros;
    onMacrosChanged(newMacros);
  });

  // Log to diary — captures the current (adjusted) quantity and macros
  const btnLog = document.createElement('button');
  btnLog.className = 'btn-log';
  btnLog.textContent = '+ log to diary';
  btnLog.addEventListener('click', async () => {
    await logFoodToDiary({
      name:      food.name,
      quantity:  qtyInput.value,
      estimated: food.estimated,
      ...liveMacros,
    }, btnLog);
  });
  card.appendChild(btnLog);

  return card;
}

// ── Build macro cells (used for totals card) ──────────────────────────────────
function buildMacroCells(macros) {
  return MACRO_DEFS.map(def => {
    const cell = document.createElement('div');
    cell.className = 'macro-cell ' + def.cls;

    const lbl = document.createElement('span');
    lbl.className = 'mc-label';
    lbl.textContent = def.label;

    const num = document.createElement('span');
    num.className = 'mc-value';
    num.textContent = fmtMacro(macros[def.key], def.unit);

    cell.appendChild(lbl);
    cell.appendChild(num);
    return cell;
  });
}

// ── Count-up animation ────────────────────────────────────────────────────────
function animateCount(from, to) {
  if (from === to) { resultsCount.textContent = to; return; }
  const duration = 400;
  const start = performance.now();
  function step(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    resultsCount.textContent = Math.round(from + (to - from) * eased);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Diary: log food ───────────────────────────────────────────────────────────
async function logFoodToDiary(food, btn) {
  try {
    const resp = await fetch('/api/diary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name:      food.name,
        quantity:  food.quantity,
        calories:  food.calories,
        protein_g: food.protein_g,
        carbs_g:   food.carbs_g,
        fat_g:     food.fat_g,
        estimated: food.estimated,
      }),
    });
    if (!resp.ok) throw new Error('Failed to save');
    btn.textContent = '✓ logged';
    btn.classList.add('logged');
  } catch (err) {
    alert('Could not save to diary: ' + err.message);
  }
}

// ── Diary state ───────────────────────────────────────────────────────────────
let _diaryPrev        = 'input';
let _diaryDate        = todayISO();
let _historyData      = [];
let _diaryTargets     = {};
let _activeChartMacro = 'calories';

const CHART_COLORS = {
  calories:  { full: '#D07A56', dim: 'rgba(208,122,86,0.28)'  },
  protein_g: { full: '#3DB88A', dim: 'rgba(61,184,138,0.28)'  },
  carbs_g:   { full: '#C4963F', dim: 'rgba(196,150,63,0.28)'  },
  fat_g:     { full: '#8B7EC8', dim: 'rgba(139,126,200,0.28)' },
};
const CHART_UNITS = { calories: ' kcal', protein_g: 'g', carbs_g: 'g', fat_g: 'g' };

function todayISO() {
  const d = new Date();
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0');
}

function shiftDate(iso, delta) {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + delta);
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0');
}

// ── Diary: open / navigate ────────────────────────────────────────────────────
btnOpenDiary.addEventListener('click',        () => openDiary('input'));
btnDiaryFromResults.addEventListener('click', () => openDiary('results'));
btnBackFromDiary.addEventListener('click',    () => showState(_diaryPrev));

btnPrevDay.addEventListener('click', async () => {
  _diaryDate = shiftDate(_diaryDate, -1);
  await loadDiaryForDate();
});
btnNextDay.addEventListener('click', async () => {
  if (_diaryDate >= todayISO()) return;
  _diaryDate = shiftDate(_diaryDate, +1);
  await loadDiaryForDate();
});

async function openDiary(from) {
  _diaryPrev = from;
  _diaryDate = todayISO();
  showState('diary');
  await loadDiaryForDate();
}

// ── Diary: macro chart toggle ─────────────────────────────────────────────────
document.getElementById('macro-toggles').addEventListener('click', e => {
  const btn = e.target.closest('.macro-toggle');
  if (!btn) return;
  document.querySelectorAll('.macro-toggle').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  _activeChartMacro = btn.dataset.macro;
  renderChart();
});

// ── Diary: load for selected date ─────────────────────────────────────────────
async function loadDiaryForDate() {
  // Update nav controls
  const today = todayISO();
  btnNextDay.disabled = _diaryDate >= today;

  const isToday     = _diaryDate === today;
  const isYesterday = _diaryDate === shiftDate(today, -1);
  if (isToday) {
    diaryDateEl.textContent = 'Today';
  } else if (isYesterday) {
    diaryDateEl.textContent = 'Yesterday';
  } else {
    diaryDateEl.textContent = new Date(_diaryDate + 'T12:00:00').toLocaleDateString(
      undefined, { weekday: 'long', month: 'long', day: 'numeric' }
    );
  }

  try {
    const [eRes, hRes, tRes] = await Promise.all([
      fetch('/api/diary?date=' + _diaryDate),
      fetch('/api/diary/history?days=30'),
      fetch('/api/targets'),
    ]);
    const entries = (await eRes.json()).entries || [];
    _historyData  = (await hRes.json()).history  || [];
    _diaryTargets = await tRes.json();

    renderDiaryEntries(entries);
    renderProgressBars(_diaryTargets, entries);
    renderChart();
  } catch (err) {
    console.error('Diary load failed:', err);
  }
}

// ── Diary: entries list ───────────────────────────────────────────────────────
function renderDiaryEntries(entries) {
  while (diaryEntries.firstChild) diaryEntries.removeChild(diaryEntries.firstChild);
  diaryEmptyMsg.hidden = entries.length > 0;
  entries.forEach((entry, i) => diaryEntries.appendChild(buildDiaryCard(entry, i)));
}

function buildDiaryCard(entry, index) {
  const card = document.createElement('div');
  card.className = 'diary-card';
  card.style.animationDelay = `${index * 0.05}s`;

  const info = document.createElement('div');
  info.className = 'diary-card-info';

  const name = document.createElement('div');
  name.className = 'diary-card-name';
  name.textContent = entry.name;
  info.appendChild(name);

  if (entry.quantity) {
    const qty = document.createElement('div');
    qty.className = 'diary-card-qty';
    qty.textContent = entry.quantity;
    info.appendChild(qty);
  }

  const macros = document.createElement('div');
  macros.className = 'diary-card-macros';
  [
    { val: entry.calories,  label: 'kcal', cls: 'dm-cal'  },
    { val: entry.protein_g, label: 'p',    cls: 'dm-prot' },
    { val: entry.carbs_g,   label: 'c',    cls: 'dm-carb' },
    { val: entry.fat_g,     label: 'f',    cls: 'dm-fat'  },
  ].forEach(({ val, label, cls }) => {
    if (val == null) return;
    const span = document.createElement('span');
    span.className = 'diary-macro ' + cls;
    span.textContent = Math.round(val) + (label === 'kcal' ? ' kcal' : label);
    macros.appendChild(span);
  });
  info.appendChild(macros);
  card.appendChild(info);

  const delBtn = document.createElement('button');
  delBtn.className = 'btn-delete';
  delBtn.title = 'Remove entry';
  delBtn.textContent = '×';
  delBtn.addEventListener('click', async () => {
    const resp = await fetch('/api/diary/' + entry.id, { method: 'DELETE' }).catch(() => null);
    if (resp && resp.ok) {
      await loadDiaryForDate();
    } else {
      alert('Could not delete entry.');
    }
  });
  card.appendChild(delBtn);

  return card;
}

// ── Diary: progress bars ──────────────────────────────────────────────────────
function renderProgressBars(targets, entries) {
  while (progressBars.firstChild) progressBars.removeChild(progressBars.firstChild);

  const totals = { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 };
  entries.forEach(e => {
    if (e.calories  != null) totals.calories  += e.calories;
    if (e.protein_g != null) totals.protein_g += e.protein_g;
    if (e.carbs_g   != null) totals.carbs_g   += e.carbs_g;
    if (e.fat_g     != null) totals.fat_g     += e.fat_g;
  });

  [
    { key: 'calories',  label: 'calories', cls: 'pr-cal',  unit: ' kcal', target: targets.calories  },
    { key: 'protein_g', label: 'protein',  cls: 'pr-prot', unit: 'g',     target: targets.protein_g },
    { key: 'carbs_g',   label: 'carbs',    cls: 'pr-carb', unit: 'g',     target: targets.carbs_g   },
    { key: 'fat_g',     label: 'fat',      cls: 'pr-fat',  unit: 'g',     target: targets.fat_g     },
  ].forEach(({ key, label, cls, unit, target }) => {
    const current = Math.round(totals[key]);
    const pct     = target > 0 ? Math.min((current / target) * 100, 100) : 0;

    const row = document.createElement('div');
    row.className = 'progress-row ' + cls;

    const meta = document.createElement('div');
    meta.className = 'progress-meta';

    const lbl = document.createElement('span');
    lbl.className = 'progress-label';
    lbl.textContent = label;

    const val = document.createElement('span');
    val.className = 'progress-value';
    val.textContent = current + unit + ' / ' + Math.round(target) + unit;

    meta.appendChild(lbl);
    meta.appendChild(val);

    const track = document.createElement('div');
    track.className = 'progress-track';
    const fill = document.createElement('div');
    fill.className = 'progress-fill';
    fill.style.width = '0%';
    track.appendChild(fill);

    row.appendChild(meta);
    row.appendChild(track);
    progressBars.appendChild(row);

    requestAnimationFrame(() => { fill.style.width = pct + '%'; });
  });
}

// ── History chart ─────────────────────────────────────────────────────────────
function renderChart() {
  const wrap = document.getElementById('chart-wrap');
  const svg  = document.getElementById('history-chart');
  const W = wrap.clientWidth || 300;
  const H = 80;
  const PL = 4, PR = 4, PT = 14, PB = 6;
  const innerH = H - PT - PB;

  while (svg.firstChild) svg.removeChild(svg.firstChild);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('width', W);
  svg.setAttribute('height', H);

  // Build full 30-day date list (oldest → newest)
  const DAYS = 30;
  const today = todayISO();
  const allDays = [];
  for (let i = DAYS - 1; i >= 0; i--) allDays.push(shiftDate(today, -i));

  const byDate = {};
  _historyData.forEach(d => { byDate[d.date] = d; });

  const macro   = _activeChartMacro;
  const colors  = CHART_COLORS[macro];
  const values  = allDays.map(d => (byDate[d] ? byDate[d][macro] : 0) || 0);
  const target  = _diaryTargets[macro] || 0;
  const maxVal  = Math.max(...values, target, 1);

  const slotW = (W - PL - PR) / DAYS;
  const gap   = Math.max(slotW * 0.18, 1);
  const barW  = slotW - gap;

  // Dashed target line
  if (target > 0) {
    const ty = PT + innerH * (1 - target / maxVal);
    svg.appendChild(_svgEl('line', {
      x1: PL, x2: W - PR, y1: ty, y2: ty,
      stroke: '#C4963F', 'stroke-width': '1',
      'stroke-dasharray': '3 3', opacity: '0.55',
    }));
  }

  // Month boundary lines + labels
  let lastMonth = null;
  allDays.forEach((day, i) => {
    const month = day.slice(0, 7); // "YYYY-MM"
    if (month !== lastMonth) {
      lastMonth = month;
      const x = PL + i * slotW;
      if (i > 0) {
        svg.appendChild(_svgEl('line', {
          x1: x, x2: x, y1: PT, y2: PT + innerH,
          stroke: 'rgba(255,255,255,0.06)', 'stroke-width': '1',
        }));
      }
      // Month label
      const lbl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      lbl.setAttribute('x', x + 2);
      lbl.setAttribute('y', PT - 3);
      lbl.setAttribute('font-size', '7');
      lbl.setAttribute('fill', 'rgba(255,255,255,0.25)');
      lbl.setAttribute('font-family', 'monospace');
      lbl.textContent = new Date(day + 'T12:00:00')
        .toLocaleDateString(undefined, { month: 'short' }).toUpperCase();
      svg.appendChild(lbl);
    }
  });

  // Bars
  allDays.forEach((day, i) => {
    const val       = values[i];
    const x         = PL + i * slotW + gap / 2;
    const isSelected = day === _diaryDate;
    const bh        = val > 0 ? Math.max(innerH * (val / maxVal), 2) : 0;
    const y         = PT + innerH - bh;

    // Invisible click target covering the full slot height
    const hit = _svgEl('rect', {
      x: PL + i * slotW, y: PT, width: slotW, height: innerH,
      fill: 'transparent', style: 'cursor:pointer',
    });
    hit.addEventListener('click', () => {
      _diaryDate = day;
      loadDiaryForDate();
    });
    svg.appendChild(hit);

    // Data bar
    if (bh > 0) {
      const bar = _svgEl('rect', {
        x, y, width: barW, height: bh,
        fill: isSelected ? colors.full : colors.dim,
        rx: '2', style: 'cursor:pointer',
      });
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent =
        new Date(day + 'T12:00:00').toLocaleDateString(undefined,
          { weekday: 'short', month: 'short', day: 'numeric' }) +
        ': ' + Math.round(val) + CHART_UNITS[macro];
      bar.appendChild(title);
      bar.addEventListener('click', () => {
        _diaryDate = day;
        loadDiaryForDate();
      });
      svg.appendChild(bar);
    }

    // Selected-day indicator dot above the bar
    if (isSelected) {
      svg.appendChild(_svgEl('circle', {
        cx: x + barW / 2, cy: PT - 5, r: '2.5',
        fill: colors.full,
      }));
    }
  });
}

function _svgEl(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}

// Re-render chart on resize (orientation change on mobile)
window.addEventListener('resize', () => {
  if (body.classList.contains('state-diary')) renderChart();
});
