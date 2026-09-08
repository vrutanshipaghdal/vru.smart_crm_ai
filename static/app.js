// Smart CRM AI - Client Application Logic (Light Modern SaaS Theme)

let allLeads = [];
let currentLead = null;
let debounceTimer = null;
let charts = { pipeline: null, sources: null, sentiment: null };

// Keep lead-entered text safe when it is inserted into the dashboard markup.
// This function is used by both pipeline cards and table rows.
function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  // Use the row-based table as the default display, even if an older cached
  // page initially marks the pipeline tab as active.
  switchTab('table');
  refreshAllData();
  [['metric-total', 'total'], ['metric-priority', 'priority'], ['metric-followups', 'followups'], ['metric-won', 'won'], ['metric-conversion', 'conversion'], ['metric-forecast', 'forecast']]
    .forEach(([id, metric]) => document.getElementById(id)?.addEventListener('click', () => showMetricDetail(metric)));
  setInterval(loadFollowUps, 60000);
});

function formatCurrency(value) {
  return '₹' + Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function formatCompactCurrency(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', notation: 'compact', maximumFractionDigits: 2 }).format(Number(value || 0));
}

async function refreshAllData() {
  await Promise.all([loadStats(), loadLeads(), loadFollowUps()]);
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-view').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

  const view = document.getElementById('tab-view-' + tabId);
  const btn = document.getElementById('tab-btn-' + tabId);
  if (view) view.classList.remove('hidden');
  if (btn) btn.classList.add('active');

  if (tabId === 'analytics') {
    renderCharts();
  }
  if (window.lucide) lucide.createIcons();
}

async function loadStats() {
  try {
    const res = await fetch('/api/dashboard/stats');
    const data = await res.json();
    document.getElementById('stat-total-leads').innerText = data.total_leads;
    document.getElementById('stat-high-priority').innerText = data.high_priority_leads;
    document.getElementById('stat-pending-followups').innerText = data.pending_followups;
    document.getElementById('stat-won-deals').innerText = data.won_deals;
    document.getElementById('stat-active-customers').innerText = data.active_customers + ' Customers';
    document.getElementById('stat-conversion-rate').innerText = data.conversion_rate + '%';
    document.getElementById('stat-sales-forecast').innerText = formatCompactCurrency(data.sales_forecast);

    window.latestStats = data;
    if (!document.getElementById('tab-view-analytics').classList.contains('hidden')) {
      renderCharts();
    }
  } catch (err) {
    console.error('Failed to load stats', err);
  }
}

function showMetricDetail(metric) {
  const stats = window.latestStats;
  if (!stats) return;
  const details = {
    total: ['Total Leads', `<p class="text-3xl font-extrabold text-indigo-600">${stats.total_leads}</p><p class="mt-2">All customer and prospect records currently in the CRM.</p>`],
    priority: ['High-Priority Leads', `<p class="text-3xl font-extrabold text-amber-600">${stats.high_priority_leads}</p><p class="mt-2">Leads marked <b>Urgent</b> or <b>High</b> by AI or sales selection.</p>`],
    followups: ['Pending Follow-ups', `<p class="text-3xl font-extrabold text-rose-600">${stats.pending_followups}</p><p class="mt-2">Open reminders that still need sales action.</p>`],
    won: ['Deals Won', `<p class="text-3xl font-extrabold text-emerald-600">${stats.won_deals}</p><p class="mt-2">Closed leads converted to customers.</p>`],
    conversion: ['Conversion Rate', `<p class="text-3xl font-extrabold text-cyan-600">${stats.conversion_rate}%</p><p class="mt-2">Won deals divided by total leads.</p>`],
    forecast: ['Sales Forecast', `<p class="text-3xl font-extrabold text-purple-600 break-all">${formatCurrency(stats.sales_forecast)}</p><p class="mt-2">Weighted forecast from active pipeline stages. Click values are shown in full here.</p><div class="mt-3 grid grid-cols-2 gap-2 text-xs">${Object.entries(stats.pipeline_counts || {}).map(([stage, count]) => `<div class="rounded-lg bg-slate-50 p-2"><b>${escapeHtml(stage)}</b>: ${count} lead(s)</div>`).join('')}</div>`]
  };
  const [title, content] = details[metric];
  document.getElementById('metric-detail-title').textContent = title;
  document.getElementById('metric-detail-content').innerHTML = content;
  openModal('modal-metric-detail');
}

async function loadLeads() {
  try {
    const search = document.getElementById('filter-search').value.trim();
    const priority = document.getElementById('filter-priority').value;
    let url = '/api/leads?';
    if (search) url += 'search=' + encodeURIComponent(search) + '&';
    if (priority && priority !== 'All') url += 'priority=' + encodeURIComponent(priority) + '&';

    const res = await fetch(url);
    allLeads = await res.json();
    renderKanban();
    renderPipelineTable();
    renderTable();
  } catch (err) {
    console.error('Failed to load leads', err);
  }
}

function debounceFetch() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    loadLeads();
  }, 300);
}

function renderCharts() {
  if (!window.Chart || !window.latestStats) return;
  const stats = window.latestStats;
  const makeChart = (key, elementId, config) => {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;
    if (charts[key]) charts[key].destroy();
    charts[key] = new Chart(canvas, config);
  };
  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } } }
  };

  makeChart('pipeline', 'chart-pipeline', {
    type: 'bar',
    data: {
      labels: Object.keys(stats.pipeline_counts || {}),
      datasets: [{ label: 'Leads', data: Object.values(stats.pipeline_counts || {}), backgroundColor: '#6366f1', borderRadius: 7 }]
    },
    options: { ...commonOptions, scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } } }
  });

  makeChart('sources', 'chart-sources', {
    type: 'doughnut',
    data: {
      labels: Object.keys(stats.source_counts || {}),
      datasets: [{ data: Object.values(stats.source_counts || {}), backgroundColor: ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'] }]
    },
    options: commonOptions
  });

  makeChart('sentiment', 'chart-sentiment', {
    type: 'pie',
    data: {
      labels: Object.keys(stats.sentiment_counts || {}),
      datasets: [{ data: Object.values(stats.sentiment_counts || {}), backgroundColor: ['#10b981', '#94a3b8', '#f43f5e'] }]
    },
    options: commonOptions
  });
}

// Render Pipeline Kanban
function renderKanban() {
  const stages = ['New', 'Contacted', 'Qualified', 'Demo', 'Proposal', 'Won', 'Lost'];
  const stageCounts = {};
  stages.forEach(s => {
    stageCounts[s] = 0;
    const colEl = document.getElementById('stage-' + s);
    if (colEl) colEl.innerHTML = '';
  });

  allLeads.forEach(lead => {
    const stage = stages.includes(lead.status) ? lead.status : 'New';
    stageCounts[stage]++;
    const container = document.getElementById('stage-' + stage);
    if (!container) return;

    const ai = lead.latest_analysis || {};
    const score = ai.lead_score || 50;
    const priority = ai.priority || 'Medium';
    const sentiment = ai.sentiment || 'Neutral';

    let priorityBadge = 'bg-slate-100 text-slate-700 border border-slate-200';
    if (priority === 'Urgent') priorityBadge = 'bg-rose-50 text-rose-700 border border-rose-200 font-bold';
    else if (priority === 'High') priorityBadge = 'bg-amber-50 text-amber-700 border border-amber-200 font-semibold';
    else if (priority === 'Low') priorityBadge = 'bg-slate-50 text-slate-500 border border-slate-200';

    let sentimentIcon = 'meh';
    let sentimentColor = 'text-slate-500';
    if (sentiment === 'Positive') { sentimentIcon = 'smile'; sentimentColor = 'text-emerald-600 font-semibold'; }
    else if (sentiment === 'Negative') { sentimentIcon = 'frown'; sentimentColor = 'text-rose-600 font-semibold'; }

    const card = document.createElement('div');
    card.className = 'pipeline-card p-3.5 space-y-2.5';
    card.onclick = () => openLeadDetailModal(lead.id);

    card.innerHTML = `
      <div class="flex items-start justify-between gap-1">
        <div class="min-w-0 flex-1">
          <h4 class="font-bold text-xs text-slate-900 hover:text-indigo-600 transition-colors line-clamp-1">${escapeHtml(lead.name)}</h4>
          <p class="text-[11px] font-medium text-slate-500 line-clamp-1">${escapeHtml(lead.company || 'Direct Contact')}</p>
        </div>
        <span class="shrink-0 text-[10px] px-1.5 py-0.5 rounded-md ${score >= 75 ? 'bg-indigo-50 text-indigo-700 border border-indigo-200 font-extrabold' : 'bg-slate-100 text-slate-700 font-bold'}">
          ${score}
        </span>
      </div>

      <div class="flex items-center justify-between text-[11px] pt-1 border-t border-slate-100">
        <span class="font-extrabold text-emerald-600">₹${lead.budget ? lead.budget.toLocaleString() : '0'}</span>
        <span class="text-[10px] px-1.5 py-0.5 rounded-md ${priorityBadge}">${priority}</span>
      </div>

      <div class="flex items-center justify-between text-[10px] text-slate-500 pt-0.5">
        <span class="bg-slate-100 font-medium px-1.5 py-0.5 rounded-md text-slate-600">${lead.source || 'Website'}</span>
        <span class="flex items-center space-x-1 ${sentimentColor}">
          <i data-lucide="${sentimentIcon}" class="w-3.5 h-3.5"></i>
          <span>${sentiment}</span>
        </span>
      </div>
    `;
    container.appendChild(card);
  });

  stages.forEach(s => {
    const parent = document.querySelector('.pipeline-col[data-stage="' + s + '"] .col-count');
    if (parent) parent.innerText = stageCounts[s];
  });

  if (window.lucide) lucide.createIcons();
}

// Compact pipeline view: every lead is one horizontal row instead of a tall Kanban column.
function renderPipelineTable() {
  const tbody = document.getElementById('pipeline-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  allLeads.forEach(lead => {
    const ai = lead.latest_analysis || {};
    const priority = ai.priority || 'Medium';
    const sentiment = ai.sentiment || 'Neutral';
    const row = document.createElement('tr');
    row.className = 'hover:bg-indigo-50/40 transition-colors';
    row.innerHTML = `
      <td class="px-6 py-3.5"><div class="font-bold text-slate-900 text-xs">${escapeHtml(lead.name)}</div><div class="text-[11px] text-slate-500">${escapeHtml(lead.company || 'Direct contact')}</div></td>
      <td class="px-5 py-3.5"><span class="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">${escapeHtml(lead.status)}</span></td>
      <td class="px-5 py-3.5"><span class="px-2.5 py-1 rounded-full text-[11px] font-semibold ${priority === 'Urgent' ? 'bg-rose-50 text-rose-700' : priority === 'High' ? 'bg-amber-50 text-amber-700' : priority === 'Low' ? 'bg-slate-100 text-slate-600' : 'bg-blue-50 text-blue-700'}">${escapeHtml(priority)}</span></td>
      <td class="px-5 py-3.5 font-black text-indigo-600 text-xs">${ai.lead_score ?? 50}/100</td>
      <td class="px-5 py-3.5 text-xs font-semibold ${sentiment === 'Positive' ? 'text-emerald-600' : sentiment === 'Negative' ? 'text-rose-600' : 'text-slate-500'}">${escapeHtml(sentiment)}</td>
      <td class="px-5 py-3.5 text-right"><button onclick="openLeadDetailModal(${lead.id})" class="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-xl text-xs font-semibold border border-indigo-200">AI Hub</button></td>`;
    tbody.appendChild(row);
  });
}

// Render Table View
function renderTable() {
  const tbody = document.getElementById('leads-table-body');
  const emptyState = document.getElementById('table-empty-state');
  tbody.innerHTML = '';

  if (!allLeads || allLeads.length === 0) {
    emptyState.classList.remove('hidden');
    return;
  }
  emptyState.classList.add('hidden');

  allLeads.forEach(lead => {
    const ai = lead.latest_analysis || {};
    const score = ai.lead_score || 50;
    const sentiment = ai.sentiment || 'Neutral';
    const action = ai.suggested_action || 'Review requirements';

    let stageBadge = 'bg-slate-100 text-slate-700 border border-slate-200';
    if (lead.status === 'Won') stageBadge = 'bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold';
    else if (lead.status === 'Lost') stageBadge = 'bg-rose-50 text-rose-700 border border-rose-200 font-bold';
    else if (lead.status === 'Proposal') stageBadge = 'bg-indigo-50 text-indigo-700 border border-indigo-200 font-bold';
    else if (lead.status === 'Qualified') stageBadge = 'bg-purple-50 text-purple-700 border border-purple-200 font-bold';

    const tr = document.createElement('tr');
    tr.className = 'hover:bg-indigo-50/40 transition-colors cursor-pointer';
    tr.onclick = () => openLeadDetailModal(lead.id);

    tr.innerHTML = `
      <td class="px-6 py-3.5">
        <div class="font-bold text-slate-900 text-xs">${escapeHtml(lead.name)}</div>
        <div class="text-[11px] font-medium text-slate-500">${escapeHtml(lead.company || 'N/A')}</div>
      </td>
      <td class="px-5 py-3.5 text-xs">
        <div class="font-medium text-slate-800">${escapeHtml(lead.phone || '-')}</div>
        <div class="text-[11px] text-slate-400">${escapeHtml(lead.email || '-')}</div>
      </td>
      <td class="px-5 py-3.5 text-xs">
        <div class="font-extrabold text-emerald-600">₹${lead.budget ? lead.budget.toLocaleString() : '0'}</div>
        <div class="text-[11px] text-slate-500 font-medium">${escapeHtml(lead.source)}</div>
      </td>
      <td class="px-5 py-3.5 text-xs">
        <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold ${stageBadge}">${lead.status}</span>
      </td>
      <td class="px-5 py-3.5 text-xs">
        <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold ${ai.priority === 'Urgent' ? 'bg-rose-50 text-rose-700' : ai.priority === 'High' ? 'bg-amber-50 text-amber-700' : ai.priority === 'Low' ? 'bg-slate-100 text-slate-600' : 'bg-blue-50 text-blue-700'}">${escapeHtml(ai.priority || 'Medium')}</span>
      </td>
      <td class="px-5 py-3.5 text-xs">
        <span class="font-black text-indigo-600 mr-1.5">${score}/100</span>
        <span class="text-[11px] font-semibold ${sentiment === 'Positive' ? 'text-emerald-600' : sentiment === 'Negative' ? 'text-rose-600' : 'text-slate-500'}">(${sentiment})</span>
      </td>
      <td class="px-5 py-3.5 text-xs text-slate-600 font-medium max-w-xs truncate">
        ${escapeHtml(action)}
      </td>
      <td class="px-5 py-3.5 text-right text-xs">
        <div class="flex justify-end gap-2">
          <button onclick="event.stopPropagation(); scheduleFollowUpForLead(${lead.id})" class="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-700 rounded-xl font-semibold border border-amber-200 transition-all">
            Follow-up
          </button>
          <button onclick="event.stopPropagation(); openLeadDetailModal(${lead.id})" class="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-xl font-semibold border border-indigo-200 transition-all">
            AI Hub &rarr;
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Render Follow-ups & Due Date Reminders
async function loadFollowUps() {
  try {
    const res = await fetch('/api/follow-ups/pending');
    const list = await res.json();
    const container = document.getElementById('followups-list');
    const emptyState = document.getElementById('followups-empty-state');
    const headerBadge = document.getElementById('header-alert-badge');
    const urgentBanner = document.getElementById('urgent-alert-banner');
    container.innerHTML = '';

    if (!list || list.length === 0) {
      emptyState.classList.remove('hidden');
      headerBadge.classList.add('hidden');
      urgentBanner.classList.add('hidden');
      return;
    }

    emptyState.classList.add('hidden');
    headerBadge.innerText = list.length;
    headerBadge.classList.remove('hidden');

    const now = new Date();
    let hasOverdueOrToday = false;

    list.forEach(fu => {
      const dueDate = new Date(fu.due_date);
      const isOverdue = dueDate < now;
      if (isOverdue) hasOverdueOrToday = true;

      const card = document.createElement('div');
      card.className = 'p-4 rounded-2xl border transition-all ' + (isOverdue ? 'bg-rose-50/70 border-rose-200' : 'bg-white border-slate-200 shadow-xs hover:shadow-md') + ' space-y-3';

      card.innerHTML = `
        <div class="flex items-start justify-between">
          <div>
            <h4 class="font-bold text-sm text-slate-900">${escapeHtml(fu.lead_name || 'Lead')}</h4>
            <p class="text-xs font-medium text-slate-500">${escapeHtml(fu.company || '')}</p>
          </div>
          <span class="text-[11px] font-bold px-2.5 py-0.5 rounded-full ${isOverdue ? 'bg-rose-100 text-rose-800 border border-rose-300' : 'bg-amber-50 text-amber-800 border border-amber-200'}">
            ${isOverdue ? 'Overdue' : 'Scheduled'}
          </span>
        </div>

        <p class="text-xs text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-100 font-medium">${escapeHtml(fu.reminder_note || 'Follow-up with customer')}</p>

        <div class="flex items-center justify-between text-xs pt-1">
          <span class="text-slate-500 font-medium flex items-center space-x-1.5">
            <i data-lucide="calendar" class="w-3.5 h-3.5 text-slate-400"></i>
            <span>${dueDate.toLocaleString()}</span>
          </span>
          <button onclick="completeFollowUp(${fu.id})" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-xs transition-all flex items-center space-x-1">
            <i data-lucide="check" class="w-3.5 h-3.5"></i>
            <span>Done</span>
          </button>
        </div>
      `;
      container.appendChild(card);
    });

    if (hasOverdueOrToday) {
      urgentBanner.classList.remove('hidden');
    } else {
      urgentBanner.classList.add('hidden');
    }

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Failed to load follow-ups', err);
  }
}

async function completeFollowUp(fuId) {
  try {
    const response = await fetch('/api/follow-ups/' + fuId + '/complete', { method: 'PATCH' });
    if (!response.ok) throw new Error('Unable to complete reminder');
    showToast('Follow-up marked completed!', 'success');
    await Promise.all([loadFollowUps(), loadStats()]);
  } catch (err) {
    showToast('Error completing reminder: ' + err.message, 'error');
  }
}

// Modal Controls
function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) {
    m.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
  }
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.add('hidden');
}

function openNewLeadModal() {
  const form = document.getElementById('form-new-lead');
  if (form) form.reset();
  openModal('modal-new-lead');
}

// Step 2 & 3: Save Lead & Auto-trigger AI Analysis
async function handleCreateLead(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-save-lead');
  btn.disabled = true;
  btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Analyzing with AI...</span>';
  if (window.lucide) lucide.createIcons();

  const payload = {
    name: document.getElementById('nl-name').value.trim(),
    company: document.getElementById('nl-company').value.trim(),
    phone: document.getElementById('nl-phone').value.trim(),
    email: document.getElementById('nl-email').value.trim(),
    budget: parseFloat(document.getElementById('nl-budget').value) || 0,
    source: document.getElementById('nl-source').value,
    requirement: document.getElementById('nl-requirement').value.trim(),
    priority: document.getElementById('nl-priority').value || null,
    sentiment: document.getElementById('nl-sentiment').value || null
  };

  try {
    const res = await fetch('/api/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to create lead');
    }
    const newLead = await res.json();
    closeModal('modal-new-lead');
    showToast('Lead created and analyzed by AI!', 'success');

    // A saved lead can otherwise be hidden by a search or priority filter that
    // was left active before opening the form.  Reset those filters and wait
    // until the pipeline has reloaded before showing the new lead's details.
    document.getElementById('filter-search').value = '';
    document.getElementById('filter-priority').value = 'All';
    switchTab('table');
    await refreshAllData();
    openLeadDetailModal(newLead.id);
  } catch (err) {
    showToast('Error creating lead: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="sparkles" class="w-4 h-4"></i><span>Save & Run AI</span>';
    if (window.lucide) lucide.createIcons();
  }
}

let followUpLeadId = null;

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `rounded-xl px-4 py-3 text-xs font-semibold text-white shadow-lg ${type === 'error' ? 'bg-rose-600' : 'bg-emerald-600'}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

async function openLeadDetailModal(leadId) {
  try {
    const response = await fetch(`/api/leads/${leadId}`);
    if (!response.ok) throw new Error('Unable to load lead details');
    currentLead = await response.json();
    const lead = currentLead;
    const ai = lead.latest_analysis || {};
    const setText = (id, value) => { document.getElementById(id).textContent = value || '-'; };

    setText('modal-lead-avatar', (lead.name || 'L').charAt(0).toUpperCase());
    setText('modal-lead-name', lead.name);
    setText('modal-lead-company-source', `${lead.company || 'Direct contact'} • ${lead.source || 'Website'}`);
    setText('modal-lead-phone', lead.phone);
    setText('modal-lead-email', lead.email);
    setText('modal-lead-budget', `₹${(lead.budget || 0).toLocaleString()}`);
    setText('modal-lead-requirement', lead.requirement || 'No requirement provided.');
    setText('modal-ai-score', ai.lead_score ?? 50);
    setText('modal-ai-category', ai.score_category || 'Medium');
    setText('modal-ai-sentiment', ai.sentiment || 'Neutral');
    setText('modal-ai-priority', ai.priority || 'Medium');
    setText('modal-ai-action', ai.suggested_action || 'Review lead requirements.');
    setText('modal-ai-summary', ai.summary || 'No AI summary available yet.');
    document.getElementById('modal-ai-draft-reply').value = ai.draft_reply || '';
    document.getElementById('modal-lead-stage-badge').textContent = lead.status || 'New';
    document.getElementById('modal-select-stage').value = lead.status || 'New';
    document.getElementById('modal-lead-customer-badge').classList.toggle('hidden', !lead.is_customer);

    const emailBody = encodeURIComponent(ai.draft_reply || 'Hello,\n\nFollowing up on our conversation.');
    document.getElementById('btn-email-lead').href = lead.email
      ? `mailto:${encodeURIComponent(lead.email)}?subject=${encodeURIComponent('Following up with Smart CRM')}&body=${emailBody}`
      : '#';
    document.getElementById('btn-call-lead').href = lead.phone ? `tel:${lead.phone}` : '#';
    document.getElementById('btn-whatsapp-lead').href = lead.phone
      ? `https://wa.me/${lead.phone.replace(/\D/g, '')}?text=${emailBody}`
      : '#';

    const timeline = document.getElementById('modal-lead-timeline');
    timeline.innerHTML = '';
    if (!lead.interactions?.length) {
      timeline.textContent = 'No conversations recorded yet.';
      timeline.className = 'text-xs text-slate-500 p-3 bg-slate-50 rounded-xl';
    } else {
      timeline.className = 'space-y-2 max-h-56 overflow-y-auto pr-1';
      lead.interactions.forEach(item => {
        const row = document.createElement('div');
        row.className = 'p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs';
        row.textContent = `${item.type} (${item.direction}): ${item.content}`;
        timeline.appendChild(row);
      });
    }
    openModal('modal-lead-detail');
  } catch (error) {
    showToast(`Unable to open AI Hub: ${error.message}`, 'error');
  }
}

function scheduleFollowUpForLead(leadId) {
  const lead = allLeads.find(item => item.id === leadId);
  followUpLeadId = leadId;

  // Default to tomorrow at the current local time, while allowing the user to
  // choose the exact time before saving.
  const due = new Date();
  due.setDate(due.getDate() + 1);
  due.setSeconds(0, 0);
  document.getElementById('fu-date').value = due.toISOString().slice(0, 16);
  document.getElementById('fu-note').value = lead
    ? `Follow up with ${lead.name}${lead.company ? ` at ${lead.company}` : ''}.`
    : '';
  openModal('modal-schedule-followup');
}

function openScheduleFollowUpModal() {
  if (!currentLead) {
    showToast('Select a lead before scheduling a follow-up.', 'error');
    return;
  }
  scheduleFollowUpForLead(currentLead.id);
}

async function handleCreateFollowUp(event) {
  event.preventDefault();
  if (!followUpLeadId) {
    showToast('Select a lead before scheduling a follow-up.', 'error');
    return;
  }

  const dueDate = document.getElementById('fu-date').value;
  const reminderNote = document.getElementById('fu-note').value.trim();
  try {
    const response = await fetch(`/api/leads/${followUpLeadId}/follow-ups`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ due_date: new Date(dueDate).toISOString(), reminder_note: reminderNote })
    });
    if (!response.ok) throw new Error('Unable to save follow-up');

    closeModal('modal-schedule-followup');
    followUpLeadId = null;
    showToast('Follow-up reminder scheduled.', 'success');
    await Promise.all([loadFollowUps(), loadStats()]);
  } catch (error) {
    showToast(`Error scheduling follow-up: ${error.message}`, 'error');
  }
}

async function refreshCurrentLead() {
  if (!currentLead) return;
  await openLeadDetailModal(currentLead.id);
  await Promise.all([loadLeads(), loadStats()]);
}

async function changeLeadStageFromModal() {
  if (!currentLead) return;
  try {
    const status = document.getElementById('modal-select-stage').value;
    const response = await fetch(`/api/leads/${currentLead.id}/status`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status })
    });
    if (!response.ok) throw new Error('Unable to update stage');
    showToast('Lead stage updated.', 'success');
    await refreshCurrentLead();
  } catch (error) { showToast(error.message, 'error'); }
}

async function triggerManualReanalyze() {
  if (!currentLead) return;
  try {
    const response = await fetch(`/api/leads/${currentLead.id}/analyze`, { method: 'POST' });
    if (!response.ok) throw new Error('AI analysis failed');
    showToast('AI analysis updated.', 'success');
    await refreshCurrentLead();
  } catch (error) { showToast(error.message, 'error'); }
}

async function submitInteractionNote() {
  if (!currentLead) return;
  const content = document.getElementById('note-content').value.trim();
  if (!content) { showToast('Enter a note first.', 'error'); return; }
  try {
    const response = await fetch(`/api/leads/${currentLead.id}/interactions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: document.getElementById('note-type').value, direction: document.getElementById('note-direction').value, content })
    });
    if (!response.ok) throw new Error('Unable to save note');
    document.getElementById('note-content').value = '';
    showToast('Note saved and AI re-analyzed.', 'success');
    await refreshCurrentLead();
  } catch (error) { showToast(error.message, 'error'); }
}

async function copyDraftToClipboard() {
  const draft = document.getElementById('modal-ai-draft-reply').value;
  try { await navigator.clipboard.writeText(draft); showToast('Draft copied.', 'success'); }
  catch { showToast('Unable to copy draft.', 'error'); }
}

async function sendDraftViaEmail() {
  if (!currentLead?.email) { showToast('This lead has no email address.', 'error'); return; }
  try {
    const response = await fetch(`/api/leads/${currentLead.id}/send-email`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject: 'Following up from Smart CRM', body: document.getElementById('modal-ai-draft-reply').value })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Unable to send email');
    showToast(`Email sent to ${data.recipient}.`, 'success');
  } catch (error) {
    showToast(error.message, 'error');
  }
}

function sendDraftViaWhatsApp() {
  const phone = currentLead?.phone?.replace(/\D/g, '');
  if (!phone) { showToast('This lead has no phone number.', 'error'); return; }
  window.open(`https://wa.me/${phone}?text=${encodeURIComponent(document.getElementById('modal-ai-draft-reply').value)}`, '_blank');
}

let dealOutcome = 'Won';
function openCloseDealModal() {
  if (!currentLead) return;
  document.getElementById('cd-deal-value').value = currentLead.deal_value || currentLead.budget || '';
  selectOutcome(currentLead.status === 'Lost' ? 'Lost' : 'Won');
  openModal('modal-close-deal');
}

function selectOutcome(outcome) {
  dealOutcome = outcome;
  document.getElementById('section-deal-won').classList.toggle('hidden', outcome !== 'Won');
  document.getElementById('section-deal-lost').classList.toggle('hidden', outcome !== 'Lost');
  document.getElementById('btn-outcome-won').className = `p-3 rounded-xl border text-center font-bold text-xs transition-all ${outcome === 'Won' ? 'border-emerald-500 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-slate-50 text-slate-500'}`;
  document.getElementById('btn-outcome-lost').className = `p-3 rounded-xl border text-center font-bold text-xs transition-all ${outcome === 'Lost' ? 'border-rose-500 bg-rose-50 text-rose-800' : 'border-slate-200 bg-slate-50 text-slate-500'}`;
}

async function handleCloseDeal(event) {
  event.preventDefault();
  if (!currentLead) return;
  try {
    const response = await fetch(`/api/leads/${currentLead.id}/close-deal`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: dealOutcome, deal_value: Number(document.getElementById('cd-deal-value').value) || 0, lost_reason: document.getElementById('cd-lost-reason').value })
    });
    if (!response.ok) throw new Error('Unable to close deal');
    closeModal('modal-close-deal'); showToast(`Deal marked ${dealOutcome}.`, 'success');
    await refreshCurrentLead();
  } catch (error) { showToast(error.message, 'error'); }
}
