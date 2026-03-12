const API = '/api';

// ── State ──────────────────────────────────────────────────
let customers = [];
let currentPage = 'dashboard';

// ── Navigation ─────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', e => {
    e.preventDefault();
    navigateTo(el.dataset.page);
  });
});

function navigateTo(page) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector(`[data-page="${page}"]`).classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.add('active');

  const titles = { dashboard: 'ダッシュボード', customers: '顧客管理', deals: '案件管理', activities: '活動履歴' };
  document.getElementById('pageTitle').textContent = titles[page] || page;
  currentPage = page;

  if (page === 'dashboard') loadDashboard();
  else if (page === 'customers') loadCustomers();
  else if (page === 'deals') loadDeals();
  else if (page === 'activities') loadActivities();
}

// ── API helpers ─────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || 'API error');
  }
  return res.json();
}

// ── Dashboard ───────────────────────────────────────────────
async function loadDashboard() {
  const stats = await apiFetch('/stats');

  document.getElementById('stat-customers').textContent = stats.activeCustomers;
  document.getElementById('stat-deals').textContent = stats.totalDeals;
  document.getElementById('stat-amount').textContent = '¥' + stats.totalAmount.toLocaleString();

  // Stage chart
  const stageLabels = { prospect: '見込み', proposal: '提案中', negotiation: '交渉中', closed_won: '受注', closed_lost: '失注' };
  const maxTotal = Math.max(...stats.stageStats.map(s => s.total || 0), 1);
  const chart = document.getElementById('stage-chart');
  chart.innerHTML = stats.stageStats.length ? stats.stageStats.map(s => `
    <div class="stage-bar-item">
      <div class="stage-bar-label">
        <span>${stageLabels[s.stage] || s.stage} (${s.count}件)</span>
        <span>¥${(s.total || 0).toLocaleString()}</span>
      </div>
      <div class="stage-bar-track">
        <div class="stage-bar-fill" style="width:${Math.round((s.total || 0) / maxTotal * 100)}%"></div>
      </div>
    </div>
  `).join('') : '<div class="empty-state">案件データがありません</div>';

  // Recent activities
  const ul = document.getElementById('recent-activities');
  ul.innerHTML = stats.recentActivities.length
    ? stats.recentActivities.map(a => activityItemHTML(a)).join('')
    : '<li class="empty-state">活動記録がありません</li>';
}

// ── Customers ───────────────────────────────────────────────
async function loadCustomers(search = '') {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  customers = await apiFetch(`/customers${query}`);

  const tbody = document.getElementById('customersBody');
  tbody.innerHTML = customers.length ? customers.map(c => `
    <tr>
      <td><a href="#" onclick="showCustomerDetail(${c.id}); return false;" class="link-name">${esc(c.name)}</a></td>
      <td>${esc(c.company || '—')}</td>
      <td>${esc(c.email || '—')}</td>
      <td>${esc(c.phone || '—')}</td>
      <td><span class="badge badge-${c.status}">${c.status === 'active' ? 'アクティブ' : '非アクティブ'}</span></td>
      <td>
        <div class="btn-actions">
          <button class="btn btn-sm" onclick="editCustomer(${c.id})">編集</button>
          <button class="btn btn-sm btn-danger" onclick="deleteCustomer(${c.id})">削除</button>
        </div>
      </td>
    </tr>
  `).join('') : '<tr><td colspan="6" class="empty-state">顧客が登録されていません</td></tr>';
}

document.getElementById('customerSearch').addEventListener('input', e => {
  loadCustomers(e.target.value);
});

// Customer form
document.getElementById('customerForm').addEventListener('submit', async e => {
  e.preventDefault();
  const id = document.getElementById('customerId').value;
  const body = {
    name: document.getElementById('customerName').value,
    company: document.getElementById('customerCompany').value,
    email: document.getElementById('customerEmail').value,
    phone: document.getElementById('customerPhone').value,
    status: document.getElementById('customerStatus').value,
    notes: document.getElementById('customerNotes').value
  };
  try {
    if (id) {
      await apiFetch(`/customers/${id}`, { method: 'PUT', body: JSON.stringify(body) });
    } else {
      await apiFetch('/customers', { method: 'POST', body: JSON.stringify(body) });
    }
    closeModal('customerModal');
    loadCustomers();
  } catch (err) {
    alert(err.message);
  }
});

function editCustomer(id) {
  const c = customers.find(x => x.id === id);
  if (!c) return;
  document.getElementById('customerId').value = c.id;
  document.getElementById('customerName').value = c.name;
  document.getElementById('customerCompany').value = c.company || '';
  document.getElementById('customerEmail').value = c.email || '';
  document.getElementById('customerPhone').value = c.phone || '';
  document.getElementById('customerStatus').value = c.status;
  document.getElementById('customerNotes').value = c.notes || '';
  document.getElementById('customerModalTitle').textContent = '顧客編集';
  openModal('customerModal');
}

async function deleteCustomer(id) {
  if (!confirm('この顧客を削除しますか？関連する案件・活動も削除されます。')) return;
  await apiFetch(`/customers/${id}`, { method: 'DELETE' });
  loadCustomers();
}

async function showCustomerDetail(id) {
  const c = await apiFetch(`/customers/${id}`);
  const stageLabels = { prospect: '見込み', proposal: '提案中', negotiation: '交渉中', closed_won: '受注', closed_lost: '失注' };

  document.getElementById('detailName').textContent = c.name;
  document.getElementById('customerDetailContent').innerHTML = `
    <div class="detail-info">
      <div class="detail-field"><label>会社</label><p>${esc(c.company || '—')}</p></div>
      <div class="detail-field"><label>ステータス</label><p><span class="badge badge-${c.status}">${c.status === 'active' ? 'アクティブ' : '非アクティブ'}</span></p></div>
      <div class="detail-field"><label>メール</label><p>${esc(c.email || '—')}</p></div>
      <div class="detail-field"><label>電話</label><p>${esc(c.phone || '—')}</p></div>
    </div>
    ${c.notes ? `<p style="font-size:13px;color:#64748b;margin-bottom:16px">${esc(c.notes)}</p>` : ''}

    <div class="detail-section-title">案件 (${c.deals.length}件)</div>
    ${c.deals.length ? `<table class="table" style="margin-bottom:16px">
      <thead><tr><th>タイトル</th><th>ステージ</th><th>金額</th></tr></thead>
      <tbody>${c.deals.map(d => `
        <tr>
          <td>${esc(d.title)}</td>
          <td><span class="badge badge-${d.stage}">${stageLabels[d.stage] || d.stage}</span></td>
          <td>¥${(d.amount || 0).toLocaleString()}</td>
        </tr>
      `).join('')}</tbody>
    </table>` : '<p class="empty-state" style="text-align:left">案件なし</p>'}

    <div class="detail-section-title">活動履歴 (${c.activities.length}件)</div>
    <ul class="activity-list">
      ${c.activities.length ? c.activities.map(a => activityItemHTML(a)).join('') : '<li class="empty-state" style="text-align:left">活動記録なし</li>'}
    </ul>
  `;
  openModal('customerDetailModal');
}

// ── Deals ────────────────────────────────────────────────────
let deals = [];

async function loadDeals() {
  deals = await apiFetch('/deals');
  const stages = [
    { key: 'prospect', label: '見込み' },
    { key: 'proposal', label: '提案中' },
    { key: 'negotiation', label: '交渉中' },
    { key: 'closed_won', label: '受注' },
    { key: 'closed_lost', label: '失注' }
  ];

  const board = document.getElementById('kanbanBoard');
  board.innerHTML = stages.map(s => {
    const col = deals.filter(d => d.stage === s.key);
    return `
      <div class="kanban-col">
        <div class="kanban-col-header">
          <span>${s.label}</span>
          <span class="kanban-col-count">${col.length}</span>
        </div>
        ${col.length ? col.map(d => `
          <div class="deal-card" onclick="editDeal(${d.id})">
            <div class="deal-title">${esc(d.title)}</div>
            <div class="deal-customer">${esc(d.customer_name || '')} ${d.company ? `(${esc(d.company)})` : ''}</div>
            <div class="deal-amount">¥${(d.amount || 0).toLocaleString()}</div>
          </div>
        `).join('') : '<div style="font-size:12px;color:#94a3b8;text-align:center;padding:12px">なし</div>'}
      </div>
    `;
  }).join('');
}

// Deal form
document.getElementById('dealForm').addEventListener('submit', async e => {
  e.preventDefault();
  const id = document.getElementById('dealId').value;
  const body = {
    customer_id: document.getElementById('dealCustomer').value,
    title: document.getElementById('dealTitle').value,
    amount: parseFloat(document.getElementById('dealAmount').value) || 0,
    stage: document.getElementById('dealStage').value,
    expected_close: document.getElementById('dealCloseDate').value || null,
    notes: document.getElementById('dealNotes').value
  };
  try {
    if (id) {
      await apiFetch(`/deals/${id}`, { method: 'PUT', body: JSON.stringify(body) });
    } else {
      await apiFetch('/deals', { method: 'POST', body: JSON.stringify(body) });
    }
    closeModal('dealModal');
    loadDeals();
  } catch (err) {
    alert(err.message);
  }
});

function editDeal(id) {
  const d = deals.find(x => x.id === id);
  if (!d) return;
  document.getElementById('dealId').value = d.id;
  document.getElementById('dealCustomer').value = d.customer_id;
  document.getElementById('dealTitle').value = d.title;
  document.getElementById('dealAmount').value = d.amount || 0;
  document.getElementById('dealStage').value = d.stage;
  document.getElementById('dealCloseDate').value = d.expected_close || '';
  document.getElementById('dealNotes').value = d.notes || '';
  document.getElementById('dealModalTitle').textContent = '案件編集';
  openModal('dealModal');
}

// ── Activities ───────────────────────────────────────────────
async function loadActivities() {
  const activities = await apiFetch('/activities');
  const list = document.getElementById('activitiesList');
  list.innerHTML = activities.length
    ? activities.map(a => activityItemHTML(a, true)).join('')
    : '<li class="empty-state">活動記録がありません</li>';
}

document.getElementById('activityForm').addEventListener('submit', async e => {
  e.preventDefault();
  const body = {
    customer_id: document.getElementById('activityCustomer').value || null,
    type: document.getElementById('activityType').value,
    title: document.getElementById('activityTitle').value,
    description: document.getElementById('activityDesc').value,
    date: document.getElementById('activityDate').value || new Date().toISOString()
  };
  try {
    await apiFetch('/activities', { method: 'POST', body: JSON.stringify(body) });
    closeModal('activityModal');
    loadActivities();
  } catch (err) {
    alert(err.message);
  }
});

// ── Helpers ──────────────────────────────────────────────────
function esc(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const typeIcons = { call: '📞', email: '✉️', meeting: '🤝', note: '📝', other: '●' };

function activityItemHTML(a, showDelete = false) {
  const icon = typeIcons[a.type] || '●';
  const date = a.date ? new Date(a.date).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
  return `
    <li class="activity-item">
      <div class="activity-icon">${icon}</div>
      <div class="activity-content">
        <div class="activity-title-row">
          <span class="activity-name">${esc(a.title)}</span>
          <span class="activity-date">${date}</span>
        </div>
        ${a.customer_name ? `<div class="activity-meta">${esc(a.customer_name)}</div>` : ''}
        ${a.description ? `<div class="activity-desc">${esc(a.description)}</div>` : ''}
      </div>
      ${showDelete ? `<button class="btn btn-sm" onclick="deleteActivity(${a.id})" style="flex-shrink:0">削除</button>` : ''}
    </li>
  `;
}

async function deleteActivity(id) {
  if (!confirm('この活動記録を削除しますか？')) return;
  await apiFetch(`/activities/${id}`, { method: 'DELETE' });
  loadActivities();
}

// ── Modal ─────────────────────────────────────────────────────
function openModal(id) {
  if (id === 'customerModal') {
    if (!document.getElementById('customerId').value) {
      document.getElementById('customerForm').reset();
      document.getElementById('customerId').value = '';
      document.getElementById('customerModalTitle').textContent = '顧客追加';
    }
  }
  if (id === 'dealModal') {
    if (!document.getElementById('dealId').value) {
      document.getElementById('dealForm').reset();
      document.getElementById('dealId').value = '';
      document.getElementById('dealModalTitle').textContent = '案件追加';
    }
    // Populate customer dropdown
    const sel = document.getElementById('dealCustomer');
    sel.innerHTML = customers.map(c => `<option value="${c.id}">${esc(c.name)}${c.company ? ` (${esc(c.company)})` : ''}</option>`).join('');
  }
  if (id === 'activityModal') {
    document.getElementById('activityForm').reset();
    // Populate customer dropdown
    const sel = document.getElementById('activityCustomer');
    sel.innerHTML = '<option value="">-- 選択 --</option>' +
      customers.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('');
    // Set default date to now
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById('activityDate').value = now.toISOString().slice(0, 16);
  }
  document.getElementById(id).classList.add('open');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  // Reset deal id so next open is "add"
  if (id === 'dealModal') document.getElementById('dealId').value = '';
  if (id === 'customerModal') document.getElementById('customerId').value = '';
}

// Close on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
  });
});

// ── Init ──────────────────────────────────────────────────────
(async () => {
  await loadCustomers();
  loadDashboard();
})();
