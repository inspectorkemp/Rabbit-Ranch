const toastEl = document.getElementById('toast');

function toast(msg, ok=true) {
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.className = ok ? 'toast ok' : 'toast bad';
  toastEl.hidden = false;
  setTimeout(() => { toastEl.hidden = true; }, 2500);
}

async function api(path, opts={}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts
  });

  let data = null;
  try { data = await res.json(); } catch {}

  if (!res.ok) {
    const detail = (data && data.detail) ? data.detail : res.statusText;
    throw new Error(detail);
  }
  return data;
}

function fmt(x) {
  if (x === null || x === undefined) return '—';
  if (typeof x === 'number') return Number.isInteger(x) ? String(x) : x.toFixed(2);
  return String(x);
}

function fmtCurrency(x) {
  if (x === null || x === undefined) return '—';
  return '$' + Number(x).toFixed(2);
}

// ----------------------------------------
// Modal
// ----------------------------------------
const modalBackdrop = document.getElementById('editModal');

function openModal() {
  if (modalBackdrop) modalBackdrop.classList.add('open');
}

function closeModal() {
  if (modalBackdrop) modalBackdrop.classList.remove('open');
}

// Close on backdrop click or close/cancel buttons
if (modalBackdrop) {
  modalBackdrop.addEventListener('click', (e) => {
    if (e.target === modalBackdrop) closeModal();
  });
}

document.getElementById('modalClose')?.addEventListener('click', closeModal);
document.getElementById('modalCancel')?.addEventListener('click', closeModal);

// Close on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

// ----------------------------------------
// Shared helpers
// ----------------------------------------
function setMetrics(m) {
  const el = (id) => document.getElementById(id);
  if (!el('m_total_litters')) return;

  el('m_total_litters').textContent = fmt(m.total_litters);
  el('m_avg_litter_size').textContent = fmt(m.average_litter_size);
  el('m_survival').textContent = m.kit_survival_rate == null
    ? '—'
    : (m.kit_survival_rate * 100).toFixed(1) + '%';
  el('m_days_to_harvest').textContent = fmt(m.average_days_to_harvest);
  el('m_harvested').textContent = fmt(m.harvested_rabbits);
}

function filterRows(rows, q, cols) {
  const s = String(q || '').trim().toLowerCase();
  if (!s) return rows;
  return rows.filter(r => cols.some(c => String(r[c] ?? '').toLowerCase().includes(s)));
}

function populateSelect(selectEl, options, placeholder) {
  if (!selectEl) return;
  const current = selectEl.value;
  selectEl.innerHTML = '';

  const ph = document.createElement('option');
  ph.value = '';
  ph.textContent = placeholder;
  selectEl.appendChild(ph);

  for (const o of options) {
    const opt = document.createElement('option');
    opt.value = o.id;
    opt.textContent = o.label;
    selectEl.appendChild(opt);
  }

  if (current && [...selectEl.options].some(o => o.value === current)) {
    selectEl.value = current;
  }
}

function populateSelectBySex(selectEl, animals, sex, placeholder) {
  if (!selectEl) return;
  const current = selectEl.value;
  selectEl.innerHTML = '';

  const ph = document.createElement('option');
  ph.value = '';
  ph.textContent = placeholder;
  selectEl.appendChild(ph);

  const filtered = animals
    .filter(a => a.sex === sex)
    .sort((a, b) => String(a.tattoo).localeCompare(String(b.tattoo)));

  for (const a of filtered) {
    const opt = document.createElement('option');
    opt.value = a.animal_id;
    opt.textContent = a.tattoo;
    selectEl.appendChild(opt);
  }

  if (current && [...selectEl.options].some(o => o.value === current)) {
    selectEl.value = current;
  }
}

function populateBreedingDropdowns(animals) {
  populateSelectBySex(document.getElementById('doeSelect'), animals, 'F', 'Select a doe…');
  populateSelectBySex(document.getElementById('buckSelect'), animals, 'M', 'Select a buck…');
}

// ----------------------------------------
// Theme toggle
// ----------------------------------------
function getCurrentTheme() {
  const saved = localStorage.getItem('theme');
  if (saved) return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);

  const btn = document.getElementById('themeToggle');
  if (btn) {
    btn.textContent = theme === 'dark' ? '☀️' : '🌙';
    btn.title = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
  }
}

function initThemeToggle() {
  // Sync button icon with current theme on load
  applyTheme(getCurrentTheme());

  const btn = document.getElementById('themeToggle');
  if (btn) {
    btn.onclick = () => {
      const next = getCurrentTheme() === 'dark' ? 'light' : 'dark';
      applyTheme(next);
    };
  }
}

async function loadCommon() {
  initThemeToggle();

  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) {
    refreshBtn.onclick = () => {
      initPage().then(() => toast('Refreshed')).catch(e => toast(e.message, false));
    };
  }
}

function renderTodoList(listEl, items, emptyText) {
  if (!listEl) return;
  listEl.innerHTML = '';

  if (!items || items.length === 0) {
    const li = document.createElement('li');
    li.className = 'todo-empty';
    li.textContent = emptyText;
    listEl.appendChild(li);
    return;
  }

  for (const it of items) {
    const li = document.createElement('li');
    li.className = 'todo-item';
    const a = document.createElement('a');
    a.href = it.link || '#';
    a.textContent = it.label || JSON.stringify(it);
    li.appendChild(a);
    listEl.appendChild(li);
  }
}

// ----------------------------------------
// Dashboard
// ----------------------------------------
async function initDashboardTodo() {
  const kindSel = document.getElementById('todo_kindling_window');
  const weanSel = document.getElementById('todo_wean_age');
  const harvSel = document.getElementById('todo_harvest_age');
  const applyBtn = document.getElementById('todoApplyBtn');

  const fetchAndRender = async () => {
    const kind = kindSel ? Number(kindSel.value) : 7;
    const wean = weanSel ? Number(weanSel.value) : 42;
    const harv = harvSel ? Number(harvSel.value) : 84;

    const todo = await api(`/dashboard/todo?kindling_window_days=${kind}&wean_age_days=${wean}&harvest_age_days=${harv}`);

    const k = todo.kindlings_due || [];
    const w = todo.weanings_due || [];
    const h = todo.harvest_ready || [];

    const kCount = document.getElementById('todo_kindlings_count');
    const wCount = document.getElementById('todo_weanings_count');
    const hCount = document.getElementById('todo_harvest_count');
    if (kCount) kCount.textContent = String(k.length);
    if (wCount) wCount.textContent = String(w.length);
    if (hCount) hCount.textContent = String(h.length);

    renderTodoList(document.getElementById('todo_kindlings'), k, 'No kindlings due.');
    renderTodoList(document.getElementById('todo_weanings'), w, 'No weanings due.');
    renderTodoList(document.getElementById('todo_harvest'), h, 'No harvest-ready growouts.');

    const asof = document.getElementById('todo_asof');
    if (asof) {
      const p = todo.params || {};
      asof.textContent = `As of ${todo.as_of} • kindling window ${p.kindling_window_days}d • wean ${p.wean_age_days}d • harvest ${p.harvest_age_days}d`;
    }
  };

  if (applyBtn) applyBtn.onclick = () => fetchAndRender().catch(e => toast(e.message, false));
  await fetchAndRender();
}

async function initDashboard() {
  const [m, animals, breedings, litters, harvests] = await Promise.all([
    api('/metrics'),
    api('/animals/'),
    api('/breedings/'),
    api('/litters/'),
    api('/harvests/'),
  ]);

  setMetrics(m);

  renderSimpleTable('animalsTable',   animals.slice().reverse(), ['animal_id','tattoo','sex','status','birth_date','breed','litter_id'], 10);
  renderSimpleTable('breedingsTable', breedings, ['breeding_id','doe_id','buck_id','bred_date','expected_kindling','result'], 10);
  renderSimpleTable('littersTable',   litters,   ['litter_id','breeding_id','kindling_date','born_alive','born_dead','weaned_count'], 10);
  renderSimpleTable('harvestsTable',  harvests,  ['harvest_id','animal_id','harvest_date','live_weight_grams','carcass_weight_grams'], 10);

  await initDashboardTodo();
}

// Plain table render (no edit button) — used on dashboard previews
function renderSimpleTable(tableId, rows, cols, limit=null) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  if (!tbody) return;
  tbody.innerHTML = '';
  const slice = limit ? rows.slice(0, limit) : rows;
  for (const r of slice) {
    const tr = document.createElement('tr');
    for (const c of cols) {
      const td = document.createElement('td');
      td.textContent = (r[c] === null || r[c] === undefined) ? '—' : r[c];
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

// ----------------------------------------
// Animals
// ----------------------------------------
async function initAnimals() {
  const animals = await api('/animals/');
  let activeStatus = '';

  const tabs     = document.getElementById('animalStatusTabs');
  const countsEl = document.getElementById('animalCounts');
  const filterEl = document.getElementById('animalFilter');
  const cols = ['animal_id','tattoo','sex','status','birth_date','breed','litter_id'];

  const computeCounts = () => {
    const by = (st) => animals.filter(a => a.status === st).length;
    return { total: animals.length, breeder: by('breeder'), growout: by('growout'), sold: by('sold'), harvested: by('harvested'), deceased: by('deceased') };
  };

  const applyFilters = () => {
    let rows = activeStatus ? animals.filter(a => a.status === activeStatus) : animals;
    const q = filterEl ? filterEl.value : '';
    const filtered = filterRows(rows, q, ['animal_id','tattoo','sex','status','birth_date','breed','color','litter_id']);
    renderSimpleTable('animalsTable', filtered, cols);
    if (countsEl) {
      const c = computeCounts();
      const label = activeStatus || 'all';
      countsEl.textContent = `Showing ${filtered.length} (${label}). Totals — all ${c.total}, breeders ${c.breeder}, growouts ${c.growout}, sold ${c.sold}, harvested ${c.harvested}, deceased ${c.deceased}.`;
    }
  };

  if (tabs) {
    tabs.onclick = (e) => {
      const btn = e.target.closest('button[data-status]');
      if (!btn) return;
      activeStatus = btn.getAttribute('data-status') || '';
      for (const b of tabs.querySelectorAll('button[data-status]')) b.classList.toggle('active', b === btn);
      applyFilters();
    };
  }
  if (filterEl) filterEl.oninput = applyFilters;
  applyFilters();

  const mortalitySelect = document.getElementById('mortalityAnimal');
  if (mortalitySelect) {
    const eligible = animals
      .filter(a => a.status !== 'harvested' && a.status !== 'deceased')
      .sort((a, b) => String(a.tattoo).localeCompare(String(b.tattoo)))
      .map(a => ({ id: a.animal_id, label: `${a.tattoo} (ID ${a.animal_id}, ${a.sex}, ${a.status})` }));
    populateSelect(mortalitySelect, eligible, 'Select animal…');
  }

  const mortalityForm = document.getElementById('mortalityForm');
  if (mortalityForm) {
    mortalityForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      if (!f.animal_id.value) { toast('Select an animal', false); return; }
      try {
        await api(`/animals/${Number(f.animal_id.value)}`, { method: 'PATCH', body: JSON.stringify({ status: 'deceased', death_date: f.death_date.value || null, death_reason: f.death_reason.value || null }) });
        toast('Animal marked deceased');
        f.reset();
        await initAnimals();
      } catch (err) { toast(err.message, false); }
    };
  }

  const animalForm = document.getElementById('animalForm');
  if (animalForm) {
    animalForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      try {
        const a = await api('/animals/', { method: 'POST', body: JSON.stringify({ tattoo: f.tattoo.value, sex: f.sex.value, status: f.status.value, breed: f.breed.value || null, color: f.color.value || null, birth_date: f.birth_date.value || null, source: f.source.value || null, litter_id: null, notes: f.notes.value || null }) });
        toast(`Animal saved (ID ${a.animal_id})`);
        f.reset();
        await initAnimals();
      } catch (err) { toast(err.message, false); }
    };
  }
}

// ----------------------------------------
// Breedings
// ----------------------------------------
async function initBreedings() {
  const [animals, breedings] = await Promise.all([api('/animals/'), api('/breedings/')]);

  populateBreedingDropdowns(animals);

  const tattoo_by_id = Object.fromEntries(animals.map(a => [a.animal_id, a.tattoo]));
  const breedingOptions = breedings.map(b => ({
    id: b.breeding_id,
    label: `#${b.breeding_id} ${tattoo_by_id[b.doe_id] ?? b.doe_id} x ${tattoo_by_id[b.buck_id] ?? b.buck_id} (${b.bred_date}) — ${b.result}`,
  }));
  populateSelect(document.getElementById('breedingSelect'), breedingOptions, 'Select breeding…');

  const cols = ['breeding_id','doe_id','buck_id','bred_date','expected_kindling','result','notes'];
  const filterEl = document.getElementById('breedingFilter');
  const render = (data) => {
    const filtered = filterRows(data, filterEl ? filterEl.value : '', cols);
    renderSimpleTable('breedingsTable', filtered, cols);
  };
  if (filterEl) filterEl.oninput = () => render(breedings);
  render(breedings);

  const breedingForm = document.getElementById('breedingForm');
  if (breedingForm) {
    breedingForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      if (!f.doe_id.value || !f.buck_id.value) { toast('Select both a doe and a buck', false); return; }
      try {
        const b = await api('/breedings/', { method: 'POST', body: JSON.stringify({ doe_id: Number(f.doe_id.value), buck_id: Number(f.buck_id.value), bred_date: f.bred_date.value }) });
        toast(`Breeding saved (ID ${b.breeding_id})`);
        f.reset();
        await initBreedings();
      } catch (err) { toast(err.message, false); }
    };
  }

  const breedingUpdateForm = document.getElementById('breedingUpdateForm');
  if (breedingUpdateForm) {
    breedingUpdateForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      if (!f.breeding_id.value) { toast('Select a breeding', false); return; }
      if (!f.result.value) { toast('Select a result', false); return; }
      try {
        const b = await api(`/breedings/${Number(f.breeding_id.value)}`, { method: 'PATCH', body: JSON.stringify({ result: f.result.value, notes: f.notes.value || null }) });
        toast(`Breeding #${b.breeding_id} updated to "${b.result}"`);
        f.reset();
        await initBreedings();
      } catch (err) { toast(err.message, false); }
    };
  }
}

// ----------------------------------------
// Kindlings — with edit modal
// ----------------------------------------
async function initKindlings() {
  const breedingOptions = await api('/options/breedings');
  populateSelect(document.getElementById('breedingForLitter'), breedingOptions, 'Select breeding…');

  let litters = await api('/litters/');

  const cols = ['litter_id','breeding_id','kindling_date','born_alive','born_dead','weaned_count'];
  const filterEl = document.getElementById('litterFilter');

  const renderLitters = (data) => {
    const tbody = document.querySelector('#littersTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const filtered = filterRows(data, filterEl ? filterEl.value : '', cols);
    for (const r of filtered) {
      const tr = document.createElement('tr');
      for (const c of cols) {
        const td = document.createElement('td');
        td.textContent = (r[c] === null || r[c] === undefined) ? '—' : r[c];
        tr.appendChild(td);
      }
      // Edit button
      const tdEdit = document.createElement('td');
      const btn = document.createElement('button');
      btn.className = 'btn-edit';
      btn.textContent = 'Edit';
      btn.onclick = () => openLitterModal(r);
      tdEdit.appendChild(btn);
      tr.appendChild(tdEdit);
      tbody.appendChild(tr);
    }
  };

  if (filterEl) filterEl.oninput = () => renderLitters(litters);
  renderLitters(litters);

  // Create litter form
  const litterForm = document.getElementById('litterForm');
  if (litterForm) {
    litterForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      const payload = {
        breeding_id: Number(f.breeding_id.value),
        kindling_date: f.kindling_date.value,
        born_alive: Number(f.born_alive.value),
        born_dead: Number(f.born_dead.value || 0),
        weaned_count: f.weaned_count.value ? Number(f.weaned_count.value) : null,
        notes: f.notes.value || null,
      };
      try {
        const l = await api('/litters/', { method: 'POST', body: JSON.stringify(payload) });
        toast(`Litter saved (ID ${l.litter_id})`);
        f.reset();
        litters = await api('/litters/');
        renderLitters(litters);
      } catch (err) { toast(err.message, false); }
    };
  }

  // --- Litter edit modal wiring ---
  function openLitterModal(litter) {
    document.getElementById('modalLitterId').value  = litter.litter_id;
    document.getElementById('modalKindlingDate').value = litter.kindling_date || '';
    document.getElementById('modalBornAlive').value    = litter.born_alive ?? '';
    document.getElementById('modalBornDead').value     = litter.born_dead ?? '';
    document.getElementById('modalWeanedCount').value  = litter.weaned_count ?? '';
    document.getElementById('modalNotes').value        = litter.notes ?? '';
    openModal();
  }

  const saveBtn = document.getElementById('modalSave');
  if (saveBtn) {
    // Replace any previous handler (page may reinitialise)
    saveBtn.onclick = async () => {
      const id = Number(document.getElementById('modalLitterId').value);

      const payload = {};
      const kd = document.getElementById('modalKindlingDate').value;
      const ba = document.getElementById('modalBornAlive').value;
      const bd = document.getElementById('modalBornDead').value;
      const wc = document.getElementById('modalWeanedCount').value;
      const nt = document.getElementById('modalNotes').value;

      if (kd) payload.kindling_date  = kd;
      if (ba !== '') payload.born_alive    = Number(ba);
      if (bd !== '') payload.born_dead     = Number(bd);
      if (wc !== '') payload.weaned_count  = Number(wc);
      payload.notes = nt || null;

      try {
        await api(`/litters/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
        toast('Litter updated');
        closeModal();
        litters = await api('/litters/');
        renderLitters(litters);
      } catch (err) { toast(err.message, false); }
    };
  }
}

// ----------------------------------------
// Weanings
// ----------------------------------------
async function initWeanings() {
  const litterOptions = await api('/options/litters?only_not_weaned=false');
  populateSelect(document.getElementById('litterForWeaning'), litterOptions, 'Select litter…');

  const animals = await api('/animals/');
  const growouts = animals.filter(a => a.status === 'growout');
  const cols = ['animal_id','tattoo','sex','status','birth_date','litter_id'];
  const filterEl = document.getElementById('growoutFilter');

  const render = () => {
    const filtered = filterRows(growouts, filterEl ? filterEl.value : '', cols);
    renderSimpleTable('growoutsTable', filtered, cols);
  };
  if (filterEl) filterEl.oninput = render;
  render();

  const generateForm = document.getElementById('generateKitsForm');
  if (generateForm) {
    generateForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      if (!f.litter_id.value) { toast('Select a litter', false); return; }
      const litterId = Number(f.litter_id.value);
      const payload = {
        weaned_count: Number(f.weaned_count.value),
        male_count: f.male_count.value === '' ? null : Number(f.male_count.value),
        female_count: f.female_count.value === '' ? null : Number(f.female_count.value),
        tattoo_prefix: f.tattoo_prefix.value || null,
      };
      try {
        const r = await api(`/litters/${litterId}/generate-kits`, { method: 'POST', body: JSON.stringify(payload) });
        toast(`Generated ${r.created} kits`);
        f.reset();
        await initWeanings();
      } catch (err) { toast(err.message, false); }
    };
  }
}

// ----------------------------------------
// Harvests — with edit modal
// ----------------------------------------
async function initHarvests() {
  const animalOptions = await api('/options/animals?status=growout');
  populateSelect(document.getElementById('animalForHarvest'), animalOptions, 'Select animal…');

  let harvests = await api('/harvests/');

  const cols = ['harvest_id','animal_id','harvest_date','live_weight_grams','carcass_weight_grams'];
  const filterEl = document.getElementById('harvestFilter');

  const renderHarvests = (data) => {
    const tbody = document.querySelector('#harvestsTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const filtered = filterRows(data, filterEl ? filterEl.value : '', cols);
    for (const r of filtered) {
      const tr = document.createElement('tr');
      for (const c of cols) {
        const td = document.createElement('td');
        td.textContent = (r[c] === null || r[c] === undefined) ? '—' : r[c];
        tr.appendChild(td);
      }
      // Edit button
      const tdEdit = document.createElement('td');
      const btn = document.createElement('button');
      btn.className = 'btn-edit';
      btn.textContent = 'Edit';
      btn.onclick = () => openHarvestModal(r);
      tdEdit.appendChild(btn);
      tr.appendChild(tdEdit);
      tbody.appendChild(tr);
    }
  };

  if (filterEl) filterEl.oninput = () => renderHarvests(harvests);
  renderHarvests(harvests);

  // Create harvest form
  const harvestForm = document.getElementById('harvestForm');
  if (harvestForm) {
    harvestForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      if (!f.animal_id.value) { toast('Select an animal', false); return; }
      const payload = {
        animal_id: Number(f.animal_id.value),
        harvest_date: f.harvest_date.value,
        live_weight_grams: f.live_weight_grams.value ? Number(f.live_weight_grams.value) : null,
        carcass_weight_grams: f.carcass_weight_grams.value ? Number(f.carcass_weight_grams.value) : null,
        notes: f.notes.value || null,
      };
      try {
        const h = await api('/harvests/', { method: 'POST', body: JSON.stringify(payload) });
        toast(`Harvest saved (ID ${h.harvest_id})`);
        f.reset();
        harvests = await api('/harvests/');
        renderHarvests(harvests);
      } catch (err) { toast(err.message, false); }
    };
  }

  // --- Harvest edit modal wiring ---
  function openHarvestModal(harvest) {
    document.getElementById('modalHarvestId').value      = harvest.harvest_id;
    document.getElementById('modalHarvestDate').value    = harvest.harvest_date || '';
    document.getElementById('modalLiveWeight').value     = harvest.live_weight_grams ?? '';
    document.getElementById('modalCarcassWeight').value  = harvest.carcass_weight_grams ?? '';
    document.getElementById('modalNotes').value          = harvest.notes ?? '';
    openModal();
  }

  const saveBtn = document.getElementById('modalSave');
  if (saveBtn) {
    saveBtn.onclick = async () => {
      const id = Number(document.getElementById('modalHarvestId').value);

      const payload = {};
      const hd = document.getElementById('modalHarvestDate').value;
      const lw = document.getElementById('modalLiveWeight').value;
      const cw = document.getElementById('modalCarcassWeight').value;
      const nt = document.getElementById('modalNotes').value;

      if (hd) payload.harvest_date         = hd;
      if (lw !== '') payload.live_weight_grams    = Number(lw);
      if (cw !== '') payload.carcass_weight_grams = Number(cw);
      payload.notes = nt || null;

      try {
        await api(`/harvests/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
        toast('Harvest updated');
        closeModal();
        harvests = await api('/harvests/');
        renderHarvests(harvests);
      } catch (err) { toast(err.message, false); }
    };
  }
}

// ----------------------------------------
// Feed Costs
// ----------------------------------------
async function initFeedCosts() {
  let feedCosts = await api('/feed-costs/');

  const filterEl = document.getElementById('feedCostFilter');
  const countEl  = document.getElementById('feedCostCount');
  const totalEl  = document.getElementById('fc_total');

  const renderFeedTable = (rows) => {
    const tbody = document.querySelector('#feedCostsTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    for (const r of rows) {
      const tr = document.createElement('tr');
      const fields = [r.feed_cost_id, r.date, r.description ?? '—', r.cost_per_unit != null ? fmtCurrency(r.cost_per_unit) : '—', fmtCurrency(r.total_cost)];
      for (const val of fields) {
        const td = document.createElement('td');
        td.textContent = val;
        tr.appendChild(td);
      }
      const tdDel = document.createElement('td');
      const btn = document.createElement('button');
      btn.textContent = '✕';
      btn.title = 'Delete';
      btn.style.cssText = 'padding:2px 8px; border-radius:8px; border:1px solid #d7d7dc; background:#fff; cursor:pointer; font-size:11px;';
      btn.onclick = async () => {
        if (!confirm(`Delete entry #${r.feed_cost_id}?`)) return;
        try {
          await fetch(`/feed-costs/${r.feed_cost_id}`, { method: 'DELETE' });
          toast('Entry deleted');
          feedCosts = feedCosts.filter(x => x.feed_cost_id !== r.feed_cost_id);
          applyFeedFilters();
        } catch { toast('Delete failed', false); }
      };
      tdDel.appendChild(btn);
      tr.appendChild(tdDel);
      tbody.appendChild(tr);
    }
  };

  const applyFeedFilters = () => {
    const q = filterEl ? filterEl.value : '';
    const filtered = filterRows(feedCosts, q, ['date','description','total_cost','cost_per_unit']);
    renderFeedTable(filtered);
    const grandTotal = feedCosts.reduce((s, r) => s + (r.total_cost || 0), 0);
    if (totalEl)  totalEl.textContent  = fmtCurrency(grandTotal);
    if (countEl)  countEl.textContent  = `${filtered.length} of ${feedCosts.length} entries`;
  };

  if (filterEl) filterEl.oninput = applyFeedFilters;
  applyFeedFilters();

  const feedCostForm = document.getElementById('feedCostForm');
  if (feedCostForm) {
    feedCostForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      const payload = { date: f.date.value, description: f.description.value || null, cost_per_unit: f.cost_per_unit.value ? Number(f.cost_per_unit.value) : null, total_cost: Number(f.total_cost.value) };
      try {
        const fc = await api('/feed-costs/', { method: 'POST', body: JSON.stringify(payload) });
        toast(`Feed cost saved (ID ${fc.feed_cost_id})`);
        f.reset();
        feedCosts = await api('/feed-costs/');
        applyFeedFilters();
      } catch (err) { toast(err.message, false); }
    };
  }
}

// ----------------------------------------
// Sales
// ----------------------------------------
async function initSales() {
  const [animals, litters, sales] = await Promise.all([
    api('/animals/'),
    api('/litters/'),
    api('/sales/'),
  ]);

  // Build label maps
  const animalById = Object.fromEntries(animals.map(a => [a.animal_id, a]));
  const litterById  = Object.fromEntries(litters.map(l => [l.litter_id, l]));

  // Populate animal dropdown — any status except harvested/deceased
  const saleAnimalSelect = document.getElementById('saleAnimalSelect');
  const saleLitterSelect = document.getElementById('saleLitterSelect');

  if (saleAnimalSelect) {
    saleAnimalSelect.innerHTML = '<option value="">Select animal…</option>';
    animals
      .filter(a => !['harvested','deceased'].includes(a.status))
      .sort((a,b) => a.tattoo.localeCompare(b.tattoo))
      .forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.animal_id;
        opt.textContent = `${a.tattoo} (${a.sex}, ${a.status})`;
        saleAnimalSelect.appendChild(opt);
      });
  }

  // Populate litter dropdown — litters that have kits
  if (saleLitterSelect) {
    saleLitterSelect.innerHTML = '<option value="">Select litter…</option>';
    litters
      .sort((a,b) => b.litter_id - a.litter_id)
      .forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.litter_id;
        opt.textContent = `L${l.litter_id} (kindled ${l.kindling_date}, alive ${l.born_alive})`;
        saleLitterSelect.appendChild(opt);
      });
  }

  // Mode toggle: individual vs litter
  let saleMode = 'animal';
  const modeToggle  = document.getElementById('saleModeToggle');
  const animalWrap  = document.getElementById('animalSelectWrap');
  const litterWrap  = document.getElementById('litterSelectWrap');
  const modeHint    = document.getElementById('saleModeHint');

  if (modeToggle) {
    modeToggle.onclick = (e) => {
      const btn = e.target.closest('button[data-mode]');
      if (!btn) return;
      saleMode = btn.getAttribute('data-mode');
      for (const b of modeToggle.querySelectorAll('button[data-mode]')) {
        b.classList.toggle('active', b === btn);
      }
      if (animalWrap) animalWrap.style.display = saleMode === 'animal' ? '' : 'none';
      if (litterWrap) litterWrap.style.display = saleMode === 'litter' ? '' : 'none';
      if (modeHint) {
        modeHint.textContent = saleMode === 'animal'
          ? 'Selling an individual animal marks it as sold.'
          : 'Selling a whole litter marks all kits in that litter as sold.';
      }
    };
  }

  // Helper: describe what was sold
  const saleSubject = (s) => {
    if (s.animal_id != null) {
      const a = animalById[s.animal_id];
      return a ? `${a.tattoo} (${a.sex})` : `Animal #${s.animal_id}`;
    }
    if (s.litter_id != null) {
      return `Litter L${s.litter_id}`;
    }
    return '—';
  };

  // Render sales table
  let currentSales = [...sales];
  const filterEl  = document.getElementById('saleFilter');
  const countEl   = document.getElementById('saleCount');

  const renderSalesTable = (rows) => {
    const tbody = document.querySelector('#salesTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    for (const s of rows) {
      const tr = document.createElement('tr');
      const cells = [
        s.sale_id,
        s.sale_date,
        saleSubject(s),
        fmtCurrency(s.sale_price),
        s.buyer_name ?? '—',
        s.buyer_contact ?? '—',
        s.notes ?? '—',
      ];
      for (const val of cells) {
        const td = document.createElement('td');
        td.textContent = val;
        tr.appendChild(td);
      }
      // Delete button
      const tdDel = document.createElement('td');
      const btn = document.createElement('button');
      btn.textContent = '✕';
      btn.title = 'Delete sale (reverts animal status)';
      btn.style.cssText = 'padding:2px 8px; border-radius:8px; border:1px solid var(--border-input); background:var(--bg-surface); color:var(--link); cursor:pointer; font-size:11px;';
      btn.onclick = async () => {
        if (!confirm(`Delete sale #${s.sale_id}? This will revert the animal's status.`)) return;
        try {
          await fetch(`/sales/${s.sale_id}`, { method: 'DELETE' });
          toast('Sale deleted');
          currentSales = currentSales.filter(x => x.sale_id !== s.sale_id);
          applyFilters();
          renderKPIs(currentSales);
          renderBuyerSummary(currentSales);
        } catch { toast('Delete failed', false); }
      };
      tdDel.appendChild(btn);
      tr.appendChild(tdDel);
      tbody.appendChild(tr);
    }
  };

  const applyFilters = () => {
    const q = filterEl ? filterEl.value.toLowerCase() : '';
    const filtered = q
      ? currentSales.filter(s =>
          (s.buyer_name ?? '').toLowerCase().includes(q) ||
          (s.buyer_contact ?? '').toLowerCase().includes(q) ||
          (s.sale_date ?? '').includes(q) ||
          saleSubject(s).toLowerCase().includes(q) ||
          (s.notes ?? '').toLowerCase().includes(q)
        )
      : currentSales;

    renderSalesTable(filtered);
    if (countEl) countEl.textContent = `${filtered.length} of ${currentSales.length} sales`;
  };

  if (filterEl) filterEl.oninput = applyFilters;

  // KPI tiles
  const renderKPIs = (rows) => {
    const total    = rows.reduce((s, r) => s + (r.sale_price || 0), 0);
    const avg      = rows.length ? total / rows.length : null;
    const countEl2 = document.getElementById('s_count');
    const revEl    = document.getElementById('s_revenue');
    const avgEl    = document.getElementById('s_avg');
    if (countEl2) countEl2.textContent = fmt(rows.length);
    if (revEl)    revEl.textContent    = fmtCurrency(total);
    if (avgEl)    avgEl.textContent    = avg == null ? '—' : fmtCurrency(avg);
  };

  // Buyer summary table
  const renderBuyerSummary = (rows) => {
    const byBuyer = {};
    for (const s of rows) {
      const key = s.buyer_name || '(no buyer recorded)';
      if (!byBuyer[key]) byBuyer[key] = { count: 0, revenue: 0 };
      byBuyer[key].count++;
      byBuyer[key].revenue += s.sale_price || 0;
    }
    const tbody = document.querySelector('#buyerSummaryTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    const sorted = Object.entries(byBuyer).sort((a,b) => b[1].revenue - a[1].revenue);
    for (const [buyer, data] of sorted) {
      const tr = document.createElement('tr');
      [buyer, data.count, fmtCurrency(data.revenue)].forEach(val => {
        const td = document.createElement('td');
        td.textContent = val;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    }
    if (!sorted.length) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 3;
      td.textContent = 'No sales yet.';
      td.style.color = 'var(--text-label)';
      tr.appendChild(td);
      tbody.appendChild(tr);
    }
  };

  renderKPIs(currentSales);
  renderBuyerSummary(currentSales);
  applyFilters();

  // Sale form submit
  const saleForm = document.getElementById('saleForm');
  if (saleForm) {
    saleForm.onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;

      const payload = {
        sale_date:     f.sale_date.value,
        sale_price:    Number(f.sale_price.value),
        buyer_name:    f.buyer_name.value    || null,
        buyer_contact: f.buyer_contact.value || null,
        notes:         f.notes.value         || null,
      };

      if (saleMode === 'animal') {
        if (!saleAnimalSelect?.value) { toast('Select an animal', false); return; }
        payload.animal_id = Number(saleAnimalSelect.value);
      } else {
        if (!saleLitterSelect?.value) { toast('Select a litter', false); return; }
        payload.litter_id = Number(saleLitterSelect.value);
      }

      try {
        const s = await api('/sales/', { method: 'POST', body: JSON.stringify(payload) });
        toast(`Sale #${s.sale_id} recorded`);
        f.reset();
        currentSales = await api('/sales/');
        renderKPIs(currentSales);
        renderBuyerSummary(currentSales);
        applyFilters();
        // Refresh animal dropdown since status changed
        await initSales();
      } catch (err) { toast(err.message, false); }
    };
  }
}


function svgBarChart(containerId, series, opts={}) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const points = (series && series.points) ? series.points : [];
  const maxBars = opts.maxBars || 24;
  const slice = points.length > maxBars ? points.slice(points.length - maxBars) : points;
  const w=720, h=160, padL=36, padR=12, padT=10, padB=28;
  const vals = slice.map(p => Number(p.value || 0));
  const maxV = Math.max(1, ...vals);
  const innerW = w - padL - padR, innerH = h - padT - padB;
  const n = slice.length || 1, gap = 4;
  const barW = Math.max(2, (innerW - gap * (n - 1)) / n);
  const y  = (v) => padT + (innerH - (v / maxV) * innerH);
  const bh = (v) => (v / maxV) * innerH;
  let grid = '';
  for (let i = 0; i <= 3; i++) { const gy = padT + (innerH / 3) * i; grid += `<line class="gridline" x1="${padL}" y1="${gy}" x2="${w-padR}" y2="${gy}" />`; }
  let bars = '';
  for (let i = 0; i < slice.length; i++) {
    const p = slice[i], v = Number(p.value || 0), x = padL + i * (barW + gap);
    bars += `<rect class="bar" x="${x}" y="${y(v)}" width="${barW}" height="${bh(v)}"><title>${p.month}: ${v}</title></rect>`;
  }
  const step = Math.max(1, Math.floor(slice.length / 6));
  let xlabels = '';
  for (let i = 0; i < slice.length; i += step) {
    const x = padL + i * (barW + gap) + barW / 2;
    xlabels += `<text class="axis" x="${x}" y="${h-10}" text-anchor="middle">${slice[i].month}</text>`;
  }
  el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${series.name}">${grid}${bars}${xlabels}<text class="axis" x="${padL}" y="${padT+10}" text-anchor="start">${series.name}</text></svg>`;
}

function svgLineChart(containerId, series, opts={}) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const points = (series && series.points) ? series.points : [];
  const maxPts = opts.maxBars || 24;
  const slice = points.length > maxPts ? points.slice(points.length - maxPts) : points;
  const w=720, h=160, padL=36, padR=12, padT=10, padB=28;
  const vals = slice.map(p => Number(p.value || 0));
  const maxV = Math.max(1e-9, ...vals);
  const innerW = w - padL - padR, innerH = h - padT - padB;
  const n = slice.length || 1;
  const x = (i) => padL + (n === 1 ? 0 : (i / (n - 1)) * innerW);
  const y = (v) => padT + (innerH - (v / maxV) * innerH);
  let grid = '';
  for (let i = 0; i <= 3; i++) { const gy = padT + (innerH / 3) * i; grid += `<line class="gridline" x1="${padL}" y1="${gy}" x2="${w-padR}" y2="${gy}" />`; }
  let d = '';
  for (let i = 0; i < slice.length; i++) { const v = Number(slice[i].value || 0); d += (i === 0 ? `M ${x(i)} ${y(v)}` : ` L ${x(i)} ${y(v)}`); }
  const step = Math.max(1, Math.floor(slice.length / 6));
  let xlabels = '';
  for (let i = 0; i < slice.length; i += step) { xlabels += `<text class="axis" x="${x(i)}" y="${h-10}" text-anchor="middle">${slice[i].month}</text>`; }
  el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${series.name}">${grid}<path d="${d}" fill="none" stroke="#0b66c3" stroke-width="2" />${xlabels}<text class="axis" x="${padL}" y="${padT+10}" text-anchor="start">${series.name}</text></svg>`;
}

// ----------------------------------------
// Reports
// ----------------------------------------
async function initReports() {
  const startEl = document.getElementById('vr_start');
  const endEl   = document.getElementById('vr_end');
  const form    = document.getElementById('visualReportsForm');

  const load = async () => {
    const qs = new URLSearchParams();
    if (startEl && startEl.value) qs.set('start_date', startEl.value);
    if (endEl   && endEl.value)   qs.set('end_date',   endEl.value);
    const data = await api(`/reports/summary${qs.toString() ? `?${qs.toString()}` : ''}`);
    const r = data.range || {}, k = data.kpis || {};

    const rangeEl = document.getElementById('vr_range');
    if (rangeEl) rangeEl.textContent = `Range: ${r.start_date || '—'} to ${r.end_date || '—'} (blank = all-time)`;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('k_litters',         fmt(k.total_litters));
    set('k_avg_litter',      k.avg_litter_size == null        ? '—' : Number(k.avg_litter_size).toFixed(2));
    set('k_survival',        k.survival_to_wean == null       ? '—' : (Number(k.survival_to_wean) * 100).toFixed(1) + '%');
    set('k_harvests',        fmt(k.harvested_count));
    set('k_days',            k.avg_days_to_harvest == null    ? '—' : Number(k.avg_days_to_harvest).toFixed(1));
    set('k_yield',           k.avg_yield == null              ? '—' : (Number(k.avg_yield) * 100).toFixed(1) + '%');
    set('k_mortality',       fmt(k.mortality_count));
    set('k_feed_total',      k.total_feed_cost == null        ? '—' : fmtCurrency(k.total_feed_cost));
    set('k_feed_per_month',  k.avg_feed_cost_per_month == null ? '—' : fmtCurrency(k.avg_feed_cost_per_month));
    set('k_feed_per_rabbit', k.cost_per_harvested_rabbit == null ? '—' : fmtCurrency(k.cost_per_harvested_rabbit));

    const sers = data.series || {};
    svgBarChart('chart_litters',   sers.litters    || {name:'Litters',       points:[]});
    svgBarChart('chart_weaned',    sers.weaned     || {name:'Weaned',        points:[]});
    svgBarChart('chart_harvests',  sers.harvests   || {name:'Harvests',      points:[]});
    svgLineChart('chart_yield',    sers.avg_yield  || {name:'Avg Yield',     points:[]});
    svgBarChart('chart_feed_cost', sers.feed_cost  || {name:'Feed Cost ($)', points:[]});
  };

  if (form) {
    form.onsubmit = async (e) => {
      e.preventDefault();
      try { await load(); toast('Reports updated'); } catch (err) { toast(err.message, false); }
    };
  }

  await load();
}

// ----------------------------------------
// Router
// ----------------------------------------
async function initPage() {
  const page = document.body.getAttribute('data-page');
  await loadCommon();
  if (page === 'dashboard')   return initDashboard();
  if (page === 'animals')     return initAnimals();
  if (page === 'breedings')   return initBreedings();
  if (page === 'kindlings')   return initKindlings();
  if (page === 'weanings')    return initWeanings();
  if (page === 'harvests')    return initHarvests();
  if (page === 'feed-costs')  return initFeedCosts();
  if (page === 'sales')       return initSales();
  if (page === 'reports')     return initReports();
}

initPage().catch(e => toast(e.message, false));
