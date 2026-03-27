'use strict';

// ── State ────────────────────────────────────────────────────────────────────
let stream = null;
let capturedBlob = null;

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

  animateCount(0, foods.length);

  if (foods.length === 0) {
    noFoodMsg.hidden = false;
    showState('results');
    return;
  }

  let totals = { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 };
  let hasCalories = false;

  foods.forEach((food, i) => {
    foodCards.appendChild(buildFoodCard(food, i));
    if (food.calories  !== null) { totals.calories  += food.calories;  hasCalories = true; }
    if (food.protein_g !== null)   totals.protein_g += food.protein_g;
    if (food.carbs_g   !== null)   totals.carbs_g   += food.carbs_g;
    if (food.fat_g     !== null)   totals.fat_g     += food.fat_g;
  });

  if (foods.length > 1 && hasCalories) {
    buildMacroCells(totals).forEach(cell => totalsRow.appendChild(cell));
    totalsCard.hidden = false;
  }

  showState('results');
}

// ── Build DOM ─────────────────────────────────────────────────────────────────
function buildFoodCard(food, index) {
  const card = document.createElement('div');
  card.className = 'food-card';
  card.style.animationDelay = `${index * 0.07}s`;

  const name = document.createElement('div');
  name.className = 'food-name';
  name.textContent = food.name;
  card.appendChild(name);

  const qty = document.createElement('div');
  qty.className = 'food-qty';
  qty.textContent = food.quantity;
  card.appendChild(qty);

  if (food.estimated) {
    const badge = document.createElement('span');
    badge.className = 'est-badge';
    badge.textContent = '~ AI estimate';
    card.appendChild(badge);
  }

  const grid = document.createElement('div');
  grid.className = 'macro-grid';
  buildMacroCells(food).forEach(cell => grid.appendChild(cell));
  card.appendChild(grid);

  return card;
}

function buildMacroCells(food) {
  const defs = [
    { key: 'calories',  label: 'kcal',    cls: 'mc-cal',  unit: ''  },
    { key: 'protein_g', label: 'protein', cls: 'mc-prot', unit: 'g' },
    { key: 'carbs_g',   label: 'carbs',   cls: 'mc-carb', unit: 'g' },
    { key: 'fat_g',     label: 'fat',     cls: 'mc-fat',  unit: 'g' },
  ];

  return defs.map(({ key, label, cls, unit }) => {
    const cell = document.createElement('div');
    cell.className = 'macro-cell ' + cls;

    const val = food[key];
    const formatted = (val !== null && val !== undefined)
      ? String(Math.round(val * 10) / 10) + unit
      : '—';

    const lbl = document.createElement('span');
    lbl.className = 'mc-label';
    lbl.textContent = label;

    const num = document.createElement('span');
    num.className = 'mc-value';
    num.textContent = formatted;

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
