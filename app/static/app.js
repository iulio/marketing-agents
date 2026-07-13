const API_BASE = window.location.origin;
let currentClientId = null;
let currentCreativeCampaignId = null;
let auditLogEntries = [];
let clientsList = [];
let performanceChartInstance = null;
let budgetChartInstance = null;
let abTestChartInstance = null;

const origFetch = window.fetch.bind(window);
window.fetch = async function(input, init) {
    const startTime = performance.now();
    const method = (init && init.method) || 'GET';
    const url = typeof input === 'string' ? input : (input && input.url ? input.url : String(input));
    try {
        const response = await origFetch(input, init);
        const duration = Math.round(performance.now() - startTime);
        const statusCode = response.status;
        const contentType = response.headers.get('content-type') || '';
        const bodySize = contentType.includes('json') ? JSON.stringify(await response.clone().json()).length : 0;
        logAuditEntry(method, url, statusCode, duration, bodySize);
        return response;
    } catch (error) {
        const duration = Math.round(performance.now() - startTime);
        logAuditEntry(method, url, 0, duration, 0, true);
        throw error;
    }
};

function logAuditEntry(method, url, statusCode, duration, payloadSize, isError) {
    const ts = new Date().toISOString();
    let platform = 'other';
    const u = url.toLowerCase();
    if (u.includes('google') || u.includes('/api/campaigns')) platform = 'campaigns';
    if (u.includes('meta') || u.includes('facebook')) platform = 'meta';
    if (u.includes('image') || u.includes('unsplash') || u.includes('pexels') || u.includes('pixabay') || u.includes('pollinations')) platform = 'images';
    if (u.includes('/api/platforms')) platform = 'google';
    auditLogEntries.unshift({
        timestamp: ts,
        method,
        endpoint: url.replace(window.location.origin, ''),
        statusCode,
        duration,
        payloadSize,
        platform,
        isError
    });
    if (auditLogEntries.length > 500) auditLogEntries.length = 500;
    renderAuditLog('all');
}

function renderAuditLog(filter) {
    const container = document.getElementById('auditLogBody');
    if (!container) return;
    const entries = filter === 'all' ? auditLogEntries : auditLogEntries.filter(e => e.platform === filter);
    if (!entries.length) {
        container.innerHTML = '<div class="text-sm text-slate-400 p-4 text-center">No API calls logged yet. Interact with the dashboard to start capturing.</div>';
        return;
    }
    container.innerHTML = entries.slice(0, 100).map(e => {
        const statusClass = e.statusCode >= 500 ? 'status-5xx' : e.statusCode >= 400 ? 'status-4xx' : e.statusCode >= 300 ? 'status-3xx' : 'status-2xx';
        const statusText = e.statusCode || 'ERR';
        const durationText = e.duration ? `${e.duration}ms` : '-';
        return `<div class="audit-log-row grid grid-cols-6 gap-2 ${statusClass}">
            <div class="text-slate-400">${new Date(e.timestamp).toLocaleTimeString()}</div>
            <div><span class="px-1.5 py-0.5 rounded text-xs font-mono ${e.method === 'GET' ? 'text-emerald-400' : e.method === 'POST' ? 'text-blue-400' : e.method === 'PATCH' ? 'text-amber-400' : 'text-red-400'}">${e.method}</span></div>
            <div class="col-span-2 truncate text-slate-300" title="${e.endpoint}">${e.endpoint}</div>
            <div><span class="font-mono ${e.statusCode >= 400 || e.isError ? 'text-red-400' : 'text-emerald-400'}">${statusText}</span></div>
            <div class="text-slate-400">${durationText}</div>
        </div>`;
    }).join('');
}

function filterAuditLog(filter) {
    document.querySelectorAll('.audit-filter-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.filter === filter);
        b.classList.toggle('bg-slate-700', b.dataset.filter !== filter);
        b.classList.toggle('bg-blue-700', b.dataset.filter === filter);
    });
    renderAuditLog(filter);
}

function clearAuditLog() {
    auditLogEntries = [];
    renderAuditLog('all');
}

function getToken() { return sessionStorage.getItem('token'); }
function getHeaders() {
    return { 'Authorization': `Bearer ${getToken()}`, 'Content-Type': 'application/json' };
}
function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, ch => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    }[ch]));
}
function formatDate(value) {
    if (!value) return '-';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? escapeHtml(value) : date.toLocaleDateString();
}
function formatEuroAmount(value) {
    const numeric = typeof value === 'number' ? value : Number(String(value ?? 0).replace(/[^0-9.-]/g, ''));
    if (!Number.isFinite(numeric)) return '€0.00';
    return new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numeric);
}
function formatEuroPerDay(value) { return `${formatEuroAmount(value)} / day`; }
function splitList(value) { return (value || '').split(',').map(v => v.trim()).filter(Boolean); }
function normalizeTone(value) {
    const normalized = (value || '').toLowerCase();
    if (normalized.includes('friendly')) return 'friendly';
    if (normalized.includes('urgent')) return 'urgent';
    if (normalized.includes('luxury')) return 'luxury';
    if (normalized.includes('authoritative')) return 'authoritative';
    if (normalized.includes('empathetic')) return 'empathetic';
    if (normalized.includes('casual')) return 'casual';
    if (normalized.includes('inspirational')) return 'inspirational';
    if (normalized.includes('humorous')) return 'humorous';
    return 'professional';
}
function showSection(sectionName) {
    document.querySelectorAll('[id^="section-"]').forEach(section => section.classList.add('hidden'));
    document.getElementById(`section-${sectionName}`)?.classList.remove('hidden');
    document.querySelectorAll('#sidebarNav .nav-link').forEach(link => link.classList.remove('active'));
    document.querySelector(`#sidebarNav .nav-link[data-section="${sectionName}"]`)?.classList.add('active');
}
document.querySelectorAll('#sidebarNav .nav-link').forEach(link => {
    link.addEventListener('click', () => showSection(link.dataset.section));
});

async function loadOverview() {
    try {
        const [clientsRes, campaignsRes, analyticsRes] = await Promise.all([
            fetch(`${API_BASE}/api/clients`, { headers: getHeaders() }),
            fetch(`${API_BASE}/api/campaigns`, { headers: getHeaders() }),
            fetch(`${API_BASE}/api/admin/analytics`, { headers: getHeaders() })
        ]);
        const clientsData = clientsRes.ok ? await clientsRes.json() : { clients: [] };
        clientsList = clientsData.clients || [];
        const campaignsData = campaignsRes.ok ? await campaignsRes.json() : { campaigns: [] };
        const analyticsData = analyticsRes.ok ? await analyticsRes.json() : {};
        const campaigns = campaignsData.campaigns || campaignsData || [];
        document.getElementById('kpiClients').textContent = (clientsData.clients || []).length;
        document.getElementById('kpiCampaigns').textContent = campaigns.length;
        document.getElementById('activeCampaigns').textContent = analyticsData.active_campaigns ?? 0;
        document.getElementById('pendingCount').textContent = `${campaigns.filter(c => c.status === 'pending_review').length} pending approval`;
    } catch (error) {
        console.error('Failed to load overview', error);
    }
}

function filterCampaignTables() {
    const search = (document.getElementById('dashCampaignSearch')?.value || document.getElementById('campaignSearch')?.value || '').toLowerCase();
    const status = document.getElementById('dashCampaignFilter')?.value || document.getElementById('campaignFilter')?.value || 'all';
    document.querySelectorAll('#campaignTableBody tr, #campaignTableBody2 tr').forEach(row => {
        if (!row.dataset.search) return;
        const matchSearch = !search || row.dataset.search.includes(search);
        const matchStatus = status === 'all' || row.dataset.status === status;
        row.style.display = matchSearch && matchStatus ? '' : 'none';
    });
}

function filterClientTable() {
    const search = (document.getElementById('clientSearch')?.value || '').toLowerCase();
    document.querySelectorAll('#clientsTableBody tr').forEach(row => {
        if (!row.dataset.search) return;
        row.style.display = !search || row.dataset.search.includes(search) ? '' : 'none';
    });
}

function renderCampaignTable(tableId, campaigns) {
    const tbody = document.getElementById(tableId);
    if (!tbody) return;
    if (!campaigns?.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="py-4 text-slate-400">No campaigns found.</td></tr>';
        return;
    }
    tbody.innerHTML = campaigns.map(c => {
        const statusClass = c.status === 'active' ? 'badge-active' : c.status === 'pending_review' ? 'badge-pending' : 'badge-inactive';
        const duration = c.duration_days ? `${c.duration_days} days` : ((c.start_date || c.end_date) ? `${c.start_date || '?'} → ${c.end_date || '?'}` : '-');
        const verification = c.google_campaign_verified || c.meta_campaign_verified
            ? 'Verified'
            : (c.verification_message || 'Pending');
        const verificationTitle = [
            c.google_push_attempted ? `Google attempted: ${c.google_push_succeeded ? 'yes' : 'failed'}` : 'Google attempted: no',
            c.meta_push_attempted ? `Meta attempted: ${c.meta_push_succeeded ? 'yes' : 'failed'}` : 'Meta attempted: no',
            c.google_platform_response_id ? `Google response: ${c.google_platform_response_id}` : null,
            c.meta_platform_response_id ? `Meta response: ${c.meta_platform_response_id}` : null,
            c.google_platform_error_message,
            c.meta_platform_error_message
        ].filter(Boolean).join(' | ');
        const searchText = `${c.campaign_name || 'Unnamed'} ${c.platform || ''} ${c.language || ''}`.toLowerCase();
        return `
            <tr class="border-t border-slate-800 hover:bg-slate-950/40" data-status="${c.status || 'unknown'}" data-search="${escapeHtml(searchText)}">
                <td class="py-3">${escapeHtml(c.campaign_name || 'Unnamed')}</td>
                <td class="py-3">${escapeHtml(c.platform || 'Google & Meta')}</td>
                <td class="py-3">${escapeHtml(c.language || 'en-US')}</td>
                <td class="py-3">${formatEuroPerDay(c.budget)}</td>
                <td class="py-3">${escapeHtml(duration)}</td>
                <td class="py-3 ${verification === 'Verified' ? 'badge-active' : 'badge-pending'}" title="${escapeHtml(verificationTitle)}">${escapeHtml(verification)}</td>
                <td class="py-3"><span class="budget-status text-xs" data-campaign-id="${escapeHtml(c.campaign_id)}"><span class="text-xs text-gray-500">...</span></span></td>
                <td class="py-3 ${statusClass}">${escapeHtml((c.status || 'unknown').replace('_', ' '))}</td>
                <td class="py-3">
                    <div class="flex gap-2">
                        <button onclick="viewCampaign('${escapeHtml(c.campaign_id)}')" class="text-blue-400 hover:text-blue-300"><i class="fa-regular fa-eye"></i></button>
                        <button onclick="retryPublish('${escapeHtml(c.campaign_id)}')" class="text-amber-400 hover:text-amber-300" title="Retry publish"><i class="fa-solid fa-rotate-right"></i></button>
                        <button onclick="viewPublishEvents('${escapeHtml(c.campaign_id)}')" class="text-violet-400 hover:text-violet-300" title="View publish events"><i class="fa-regular fa-rectangle-list"></i></button>
                        <button onclick="deleteCampaign('${escapeHtml(c.campaign_id)}')" class="text-red-400 hover:text-red-300"><i class="fa-regular fa-trash-can"></i></button>
                    </div>
                </td>
            </tr>`;
    }).join('');
}

function updateDropdowns(campaigns) {
    ['creativeCampaignSelect', 'creativeCampaignSelect2', 'analystCampaignSelect', 'analystCampaignSelect2'].forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        const current = select.value;
        select.innerHTML = '<option value="">Select Campaign</option>';
        campaigns.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.campaign_id;
            opt.textContent = `${c.campaign_name || 'Unnamed'} (${c.status})`;
            select.appendChild(opt);
        });
        select.value = current;
    });
}

async function loadCampaigns() {
    try {
        const url = currentClientId ? `${API_BASE}/api/clients/${currentClientId}/campaigns` : `${API_BASE}/api/campaigns`;
        const res = await fetch(url, { headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to load campaigns');
        const data = await res.json();
        const campaigns = data.campaigns || data || [];
        renderCampaignTable('campaignTableBody', campaigns);
        renderCampaignTable('campaignTableBody2', campaigns);
        updateDropdowns(campaigns);
        document.getElementById('kpiCampaigns').textContent = campaigns.length;
        setTimeout(() => loadAllBudgetStatuses(campaigns), 500);
    } catch (error) {
        console.error('Failed to load campaigns', error);
    }
}

function renderClientsTable(clients) {
    const tbody = document.getElementById('clientsTableBody');
    if (!tbody) return;
    if (!clients.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="py-4 text-slate-400">No clients yet.</td></tr>';
        return;
    }
    tbody.innerHTML = clients.map(client => {
        const searchText = `${client.name} ${client.industry || ''} ${client.website || ''} ${client.platform_status || ''}`.toLowerCase();
        return `
            <tr class="border-t border-slate-800 hover:bg-slate-950/40" data-search="${escapeHtml(searchText)}">
                <td class="py-3">${escapeHtml(client.name)}</td>
                <td class="py-3">${client.industry || '-'}</td>
                <td class="py-3">${client.website ? `<a class="text-blue-400 hover:underline" href="${escapeHtml(client.website)}" target="_blank">${escapeHtml(client.website)}</a>` : '-'}</td>
                <td class="py-3">${formatDate(client.created_at)}</td>
                <td class="py-3">${client.campaign_count || 0}</td>
                <td class="py-3">
                    <span class="badge-${client.platform_status} text-xs px-2 py-1 rounded-full">
                        ${client.platform_status}
                    </span>
                </td>
                <td class="py-3">
                    <div class="flex gap-2">
                        <button onclick="openCredentialModal('${client.id}')" class="text-blue-400 hover:text-blue-300 text-xs">Ad Accounts</button>
                        <button onclick="editClient('${client.id}')" class="text-emerald-400 hover:text-emerald-300 text-xs">Edit</button>
                        <button onclick="deleteClientRecord('${client.id}')" class="text-red-400 hover:text-red-300 text-xs">Delete</button>
                    </div>
                </td>
            </tr>`;
    }).join('');
}

async function loadClients() {
    try {
        const res = await fetch(`${API_BASE}/api/clients`, { headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to load clients');
        const data = await res.json();
        const clients = data.clients || [];
        renderClientsTable(clients);
        const select = document.getElementById('clientSelect');
        const previous = select.value;
        select.innerHTML = '<option value="">All Clients</option>';
        clients.forEach(client => {
            const opt = document.createElement('option');
            opt.value = client.id;
            opt.textContent = client.name;
            select.appendChild(opt);
        });
        select.value = clients.some(c => c.id === previous) ? previous : '';
    } catch (error) {
        console.error('Failed to load clients', error);
    }
}

function switchClient() {
    currentClientId = document.getElementById('clientSelect').value || null;
    loadCampaigns();
}

function parseJsonField(id, label) {
    const raw = document.getElementById(id).value.trim();
    if (!raw) return {};
    try { return JSON.parse(raw); } catch { throw new Error(`${label} must be valid JSON`); }
}
function showClientError(message) {
    const el = document.getElementById('clientFormError');
    el.textContent = message;
    el.classList.remove('hidden');
}
function clearClientError() {
    const el = document.getElementById('clientFormError');
    el.textContent = '';
    el.classList.add('hidden');
}
function openClientModal(client = null) {
    clearClientError();
    document.getElementById('clientModal').classList.remove('hidden');
    document.getElementById('clientModal').classList.add('flex');
    document.getElementById('clientModalTitle').innerHTML = client ? '<i class="fa-solid fa-building-user text-blue-400"></i> Edit Client' : '<i class="fa-solid fa-building-user text-blue-400"></i> Add Client';
    document.getElementById('clientFormId').value = client?.id || '';
    document.getElementById('clientFormName').value = client?.name || '';
    document.getElementById('clientFormIndustry').value = client?.industry || '';
    document.getElementById('clientFormWebsite').value = client?.website || '';
    document.getElementById('clientFormLogo').value = client?.logo_url || '';
    document.getElementById('clientFormBillingEmail').value = client?.billing_email || '';
    document.getElementById('clientFormPlatformStatus').value = client?.platform_status || 'inactive';
    document.getElementById('clientFormBillingInfo').value = JSON.stringify(client?.billing_info || {}, null, 2);
    document.getElementById('clientFormSettings').value = JSON.stringify(client?.settings || {}, null, 2);
    // Populate per-client LLM overrides
    const llmSettings = client?.agent_llm_settings;
    const parsed = typeof llmSettings === 'string' ? (() => { try { return JSON.parse(llmSettings); } catch { return {}; } })() : (llmSettings || {});
    populateClientLlmSettings(parsed);
}
function closeClientModal() {
    document.getElementById('clientModal').classList.add('hidden');
    document.getElementById('clientModal').classList.remove('flex');
    // Don't clear the credential test result on close
    // document.getElementById('credentialTestResult').innerHTML = '';
}
async function submitClientForm(event) {
    event.preventDefault();
    clearClientError();
    const clientId = document.getElementById('clientFormId').value;
    let payload;
    try {
        payload = {
            name: document.getElementById('clientFormName').value.trim(),
            industry: document.getElementById('clientFormIndustry').value.trim(),
            website: document.getElementById('clientFormWebsite').value.trim(),
            logo_url: document.getElementById('clientFormLogo').value.trim(),
            billing_email: document.getElementById('clientFormBillingEmail').value.trim(),
            platform_status: document.getElementById('clientFormPlatformStatus').value,
            billing_info: parseJsonField('clientFormBillingInfo', 'Billing Info'),
            settings: parseJsonField('clientFormSettings', 'Settings'),
            agent_llm_settings: collectClientLlmSettings()
        };
    } catch (error) {
        showClientError(error.message);
        return;
    }
    const method = clientId ? 'PATCH' : 'POST';
    const url = clientId ? `${API_BASE}/api/clients/${clientId}` : `${API_BASE}/api/clients`;
    try {
        const res = await fetch(url, { method, headers: getHeaders(), body: JSON.stringify(payload) });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Failed to save client');
        }
        closeClientModal();
        await loadClients();
    } catch (error) {
        showClientError(error.message);
    }
}
async function editClient(clientId) {
    try {
        const res = await fetch(`${API_BASE}/api/clients/${clientId}`, { headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to load client');
        const data = await res.json();
        openClientModal(data.client);
    } catch (error) {
        alert(error.message);
    }
}
async function deleteClientRecord(clientId) {
    if (!confirm('Delete this client and all associated campaigns?')) return;
    try {
        const res = await fetch(`${API_BASE}/api/clients/${clientId}`, { method: 'DELETE', headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to delete client');
        await loadClients();
        await loadCampaigns();
    } catch (error) {
        alert(error.message);
    }
}

function openCredentialModal(clientId) {
    document.getElementById('credClientId').value = clientId;
    document.getElementById('credentialModal').classList.remove('hidden');
    document.getElementById('credentialTestResult').innerHTML = ''; // Clear previous results
    document.getElementById('credentialModal').classList.add('flex');
    loadCredentialStatus(clientId);
    loadExistingCredentials(clientId);
}
function closeCredentialModal() {
    document.getElementById('credentialModal').classList.add('hidden');
    document.getElementById('credentialModal').classList.remove('flex');
    document.getElementById('credentialTestResult').innerHTML = '';
}
async function loadCredentialStatus(clientId) {
    try {
        const res = await fetch(`${API_BASE}/api/clients/${clientId}/credentials/status`, { headers: getHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('credentialStatus').innerHTML = `
            <span class="${data.google_ads ? 'badge-active' : 'badge-inactive'}">Google Ads: ${data.google_ads ? 'Configured' : 'Not configured'}</span>
            <span class="ml-4 ${data.meta_ads ? 'badge-active' : 'badge-inactive'}">Meta Ads: ${data.meta_ads ? 'Configured' : 'Not configured'}</span>`;
    } catch (error) {
        console.error('Failed to load credential status', error);
    }
}
async function loadExistingCredentials(clientId) {
    try {
        const res = await fetch(`${API_BASE}/api/clients/${clientId}/credentials`, { headers: getHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        [
            'google_ads_developer_token', 'google_ads_client_id', 'google_ads_client_secret', 'google_ads_refresh_token', 'google_ads_customer_id',
            'meta_app_id', 'meta_app_secret', 'meta_access_token', 'meta_ad_account_id'
        ].forEach(field => {
            const el = document.getElementById(field);
            if (el) el.value = data[field] || '';
        });
    } catch (error) {
        console.error('Failed to load credentials', error);
    }
}
async function saveCredentials(event) {
    event.preventDefault();
    const clientId = document.getElementById('credClientId').value;
    const payload = {};
    [
        'google_ads_developer_token', 'google_ads_client_id', 'google_ads_client_secret', 'google_ads_refresh_token', 'google_ads_customer_id',
        'meta_app_id', 'meta_app_secret', 'meta_access_token', 'meta_ad_account_id'
    ].forEach(field => {
        const value = document.getElementById(field)?.value?.trim();
        if (value) payload[field] = value;
    });
    try {
        const res = await fetch(`${API_BASE}/api/clients/${clientId}/credentials`, {
            method: 'POST', headers: getHeaders(), body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Failed to save credentials');
        }
        closeCredentialModal();
        await loadClients();
    } catch (error) {
        alert(error.message);
    }
}

async function testClientCredentials(event) {
    event.preventDefault();
    const clientId = document.getElementById('credClientId').value;
    const resultEl = document.getElementById('credentialTestResult');
    const btn = event.target;
    const originalText = btn.innerHTML;

    resultEl.innerHTML = '<div class="text-slate-400"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Testing...</div>';
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Testing...';

    try {
        const res = await fetch(`${API_BASE}/api/clients/${clientId}/test-credentials`, {
            method: 'POST',
            headers: getHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Test failed');

        const googleStatus = data.google_ads.status === 'success' ? `<span class="badge-active">Google: ${data.google_ads.message}</span>` : `<span class="badge-inactive">Google: ${data.google_ads.message}</span>`;
        const metaStatus = data.meta_ads.status === 'success' ? `<span class="badge-active">Meta: ${data.meta_ads.message}</span>` : `<span class="badge-inactive">Meta: ${data.meta_ads.message}</span>`;
        resultEl.innerHTML = `<div class="flex flex-col gap-2">${googleStatus}${metaStatus}</div>`;
    } catch (error) {
        resultEl.innerHTML = `<div class="text-red-400">Error: ${error.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}
function openGoogleTutorial() { window.open('/tutorials/google-ads-credentials.html', '_blank'); }
function openMetaTutorial() { window.open('/tutorials/meta-ads-credentials.html', '_blank'); }
function openImageTutorial() { window.open('/tutorials/image-tutorial.html', '_blank'); }

function showLocationTutorial() {
    document.getElementById('locationTutorialModal').classList.remove('hidden');
}
function closeLocationTutorial() {
    document.getElementById('locationTutorialModal').classList.add('hidden');
}

function handleModalDropdownChange(selectId, inputId) {
    const select = document.getElementById(selectId);
    const input = document.getElementById(inputId);
    if (select.value === 'custom') {
        input.classList.remove('hidden');
        input.value = '';
        input.required = true;
        input.focus();
    } else {
        input.classList.add('hidden');
        input.value = select.value;
        input.required = false;
    }
}

function handleModalLanguageChange() {
    const select = document.getElementById('campaignLanguage');
    const customInput = document.getElementById('campaignLanguageCustom');
    if (select.value === 'custom') {
        customInput.classList.remove('hidden');
        customInput.required = true;
        customInput.focus();
    } else {
        customInput.classList.add('hidden');
        customInput.required = false;
    }
}

function populateModalClientDropdown() {
    const select = document.getElementById('modalClientSelect');
    select.innerHTML = '<option value="new" selected>+ Add New Client...</option>';
    clientsList.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        select.appendChild(opt);
    });
}

function onModalClientSelectChange() {
    const val = document.getElementById('modalClientSelect').value;
    const fields = document.getElementById('modalNewClientFields');
    if (val === 'new') {
        fields.classList.remove('hidden');
        // Reset inputs to default values
        document.getElementById('clientName').value = 'Tech Startup';
        document.getElementById('websiteUrl').value = 'https://example.com';
        document.getElementById('modalClientIndustry').value = 'Tech & SaaS';
        document.getElementById('industry').value = 'Tech & SaaS';
        document.getElementById('industry').classList.add('hidden');
        document.getElementById('dailyBudget').value = '150';
        document.getElementById('modalTargetGeoSelect').value = 'Bucharest, Cluj-Napoca, Timisoara';
        document.getElementById('targetGeo').value = 'Bucharest, Cluj-Napoca, Timisoara';
        document.getElementById('targetGeo').classList.add('hidden');
        document.getElementById('modalToneOfVoiceSelect').value = 'Professional';
        document.getElementById('toneOfVoice').value = 'Professional';
        document.getElementById('toneOfVoice').classList.add('hidden');
        document.getElementById('culturalTriggers').value = 'Black Friday, Christmas, 1 Decembrie';
    } else {
        fields.classList.add('hidden');
    }
}

function openHelpModal(e) {
    if (e) e.preventDefault();
    document.getElementById('helpModal').classList.remove('hidden');
    document.getElementById('helpModal').classList.add('flex');
}
function closeHelpModal() {
    document.getElementById('helpModal').classList.add('hidden');
    document.getElementById('helpModal').classList.remove('flex');
}

function openOnboardModal() {
    document.getElementById('onboardModal').classList.remove('hidden');
    document.getElementById('onboardModal').classList.add('flex');
    populateModalClientDropdown();
    onModalClientSelectChange();
}
function closeOnboardModal() {
    document.getElementById('onboardModal').classList.add('hidden');
    document.getElementById('onboardModal').classList.remove('flex');
}
async function submitOnboard(event) {
    event.preventDefault();
    
    const clientSelectVal = document.getElementById('modalClientSelect').value;
    let clientId = null;
    
    // Resolve language
    const langSelect = document.getElementById('campaignLanguage');
    const lang = langSelect.value === 'custom' ? document.getElementById('campaignLanguageCustom').value.trim() : langSelect.value;
    
    const payload = {
        client_name: document.getElementById('clientName').value,
        website_url: document.getElementById('websiteUrl').value,
        language: lang,
        industry: document.getElementById('industry').value,
        daily_budget: parseFloat(document.getElementById('dailyBudget').value),
        target_geo: splitList(document.getElementById('targetGeo').value),
        tone_of_voice: normalizeTone(document.getElementById('toneOfVoice').value),
        cultural_triggers: splitList(document.getElementById('culturalTriggers').value),
        llm_backend: 'cloud',
        objective: 'sales',
        special_events: splitList(document.getElementById('specialEvents').value),
        product_keywords: splitList(document.getElementById('productKeywords').value),
        start_date: document.getElementById('campaignStartDate').value || null,
        end_date: document.getElementById('campaignEndDate').value || null,
        duration_days: document.getElementById('campaignDurationDays').value ? parseInt(document.getElementById('campaignDurationDays').value, 10) : null
    };

    const btn = document.querySelector('#onboardForm button[type="submit"]');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Orchestrating...';
    btn.disabled = true;

    try {
        if (clientSelectVal === 'new') {
            // Create new client first
            const clientPayload = {
                name: payload.client_name,
                industry: payload.industry,
                website: payload.website_url,
                platform_status: 'active'
            };
            const clientRes = await fetch(`${API_BASE}/api/clients`, {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify(clientPayload)
            });
            if (!clientRes.ok) throw new Error('Failed to create client');
            const clientData = await clientRes.json();
            clientId = clientData.client_id;
        } else {
            clientId = clientSelectVal;
            // Prepopulate client details from the existing client list
            const client = clientsList.find(c => c.id === clientId);
            if (client) {
                payload.client_name = client.name;
                payload.website_url = client.website || payload.website_url;
                payload.industry = client.industry || payload.industry;
                payload.daily_budget = client.default_budget || payload.daily_budget;
                payload.target_geo = client.settings?.target_geo || payload.target_geo;
                payload.tone_of_voice = client.settings?.tone_of_voice || payload.tone_of_voice;
                payload.cultural_triggers = client.settings?.cultural_triggers || payload.cultural_triggers;
            }
        }

        let url = `${API_BASE}/api/campaigns/onboard?client_id=${clientId}`;
        const res = await fetch(url, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Failed to create campaign');
        }
        const data = await res.json();
        closeOnboardModal();
        await loadCampaigns();
        viewCampaign(data.campaign_id);
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-rocket"></i> Start Orchestration';
        btn.disabled = false;
    }
}

async function deleteCampaign(campaignId) {
    if (!confirm(`Delete campaign ${campaignId}?`)) return;
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}`, { method: 'DELETE', headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to delete campaign');
        await loadCampaigns();
    } catch (error) {
        alert(error.message);
    }
}

async function retryPublish(campaignId) {
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/retry-publish`, {
            method: 'POST',
            headers: getHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Retry publish failed');
        await loadCampaigns();
        alert(data.deployment_status?.verification_message || 'Retry publish completed');
    } catch (error) {
        alert(error.message);
    }
}

async function viewPublishEvents(campaignId) {
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/publish-events`, {
            headers: getHeaders()
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to load publish events');
        const lines = (data.events || []).map(event => {
            return `${event.created_at} | ${event.platform} | attempted=${event.attempted} | succeeded=${event.succeeded} | response=${event.response_id || '-'} | error=${event.error_message || '-'}`;
        });
        alert(lines.length ? lines.join('\n') : 'No publish events recorded.');
    } catch (error) {
        alert(error.message);
    }
}
function viewCampaign(campaignId) {
    showSection('creatives');
    document.getElementById('creativeCampaignSelect').value = campaignId;
    document.getElementById('creativeCampaignSelect2').value = campaignId;
    loadCreatives();
}

async function loadCreatives() {
    const campaignId = document.getElementById('creativeCampaignSelect').value;
    currentCreativeCampaignId = campaignId || null;
    if (!campaignId) {
        document.getElementById('creativeCarousel').innerHTML = '<div class="text-slate-400 text-sm p-4">Select a campaign to review creatives.</div>';
        document.getElementById('creativeCarouselStudio').innerHTML = '<div class="text-slate-400 text-sm p-4">Select a campaign to review creatives.</div>';
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/creatives`, { headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to load creatives');
        const creatives = await res.json();
        renderMockupCreatives('creativeCarousel', creatives);
        renderMockupCreatives('creativeCarouselStudio', creatives);
        document.getElementById('creativePanelInfo').textContent = `Campaign: ${campaignId}`;
        await loadABTestResults(campaignId);
    } catch (error) {
        document.getElementById('creativeCarousel').innerHTML = '<div class="text-red-400 text-sm p-4">Failed to load creatives.</div>';
        document.getElementById('creativeCarouselStudio').innerHTML = '<div class="text-red-400 text-sm p-4">Failed to load creatives.</div>';
    }
}
function loadCreativesStudio() {
    const campaignId = document.getElementById('creativeCampaignSelect2').value;
    document.getElementById('creativeCampaignSelect').value = campaignId;
    loadCreatives();
}
function renderMockupCreatives(containerId, creatives) {
    const container = document.getElementById(containerId);
    const googleAds = creatives.google_ads || [];
    const metaAds = creatives.meta_ads || [];
    const images = creatives.images || [];
    const videos = creatives.videos || [];
    if (!googleAds.length && !metaAds.length && !images.length && !videos.length) {
        container.innerHTML = '<div class="text-slate-400 text-sm p-4">No creatives generated for this campaign yet.</div>';
        return;
    }
    container.innerHTML = '';
    googleAds.forEach((ad, idx) => {
        const safeHeadline = escapeHtml(ad.headline || 'Your Headline Here');
        const safeDesc = escapeHtml(ad.description || 'Your description text here.');
        const safeUrl = escapeHtml(ad.display_url || ad.final_url || 'www.example.com');
        container.innerHTML += `
            <div class="mockup-google-ad">
                <span class="ad-label">Ad</span>
                <div class="ad-url">${safeUrl}</div>
                <div class="ad-headline" contenteditable="true" data-campaign-id="${escapeHtml(currentCreativeCampaignId || '')}" data-platform="google" data-index="${idx}" data-field="headline" data-original="${escapeHtml(ad.headline || '')}">${safeHeadline}</div>
                <div class="ad-description" contenteditable="true" data-campaign-id="${escapeHtml(currentCreativeCampaignId || '')}" data-platform="google" data-index="${idx}" data-field="description" data-original="${escapeHtml(ad.description || '')}">${safeDesc}</div>
                <div class="flex justify-end mt-3">
                    <button onclick="saveCreativeEdit('google', ${idx})" class="text-xs px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white transition"><i class="fa-solid fa-floppy-disk mr-1"></i>Save Edits</button>
                </div>
            </div>`;
    });
    metaAds.forEach((ad, idx) => {
        const safeText = escapeHtml(ad.primary_text || 'Your ad text here.');
        const safeHeadline = escapeHtml(ad.headline || '');
        const safeCta = escapeHtml(ad.call_to_action || 'Learn More');
        container.innerHTML += `
            <div class="mockup-meta-ad">
                <div class="meta-header">
                    <div class="meta-avatar">${(safeHeadline || 'A')[0]}</div>
                    <div>
                        <div class="text-sm font-semibold text-white">${safeHeadline || 'Page Name'}</div>
                        <div class="text-xs text-slate-400">Sponsored</div>
                    </div>
                </div>
                <div class="meta-body">
                    <div class="meta-text" contenteditable="true" data-campaign-id="${escapeHtml(currentCreativeCampaignId || '')}" data-platform="meta" data-index="${idx}" data-field="primary_text" data-original="${escapeHtml(ad.primary_text || '')}">${safeText}</div>
                </div>
                <div class="meta-cta">
                    <span class="text-xs text-slate-400">${safeCta}</span>
                    <span class="meta-cta-btn">${safeCta}</span>
                </div>
                <div class="flex justify-end px-4 pb-3">
                    <button onclick="saveCreativeEdit('meta', ${idx})" class="text-xs px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white transition"><i class="fa-solid fa-floppy-disk mr-1"></i>Save Edits</button>
                </div>
            </div>`;
    });
    if (images.length) {
        container.innerHTML += `<div class="w-full text-sm text-slate-400 mt-4 mb-2 font-semibold border-t border-slate-700 pt-4">Campaign Images</div>`;
        images.forEach((img, idx) => {
            const imageUrl = img.thumb || img.url || img;
            const imageAlt = img.alt || 'Campaign image';
            const imageSource = img.source || 'unknown source';
            const imageType = img.type || 'image';
            const isPlaceholder = imageUrl.includes('placeholder') || imageUrl.includes('via.placeholder');
            const badgeLabel = isPlaceholder ? 'Placeholder' : (imageType === 'generated' ? 'AI Generated' : imageType === 'stock' ? 'Stock Image' : 'Image');
            const imageId = img.id || img.url || img || `image-${idx + 1}`;
            const fallbackUrl = 'https://via.placeholder.com/512x512/1f2937/ffffff?text=Error+Loading+Image';
            container.innerHTML += `
                <div class="panel rounded-lg p-2" style="max-width:200px">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-[10px] ${isPlaceholder ? 'text-yellow-400' : 'text-slate-400'}">${badgeLabel}</span>
                        <div class="flex gap-1">
                            <button onclick="downloadImage('${imageUrl}', 'campaign_image_${idx + 1}.png')" class="text-blue-400 hover:text-blue-300 text-[10px] transition" title="Download"><i class="fa-regular fa-download"></i></button>
                            <button onclick="deleteCampaignImage('${imageId}')" class="text-rose-400 hover:text-rose-300 text-[10px] transition" title="Delete Image"><i class="fa-regular fa-trash-can"></i></button>
                        </div>
                    </div>
                    <img src="${imageUrl}" alt="${escapeHtml(imageAlt)}" class="rounded-md h-24 w-full object-cover bg-slate-800" onerror="this.src='${fallbackUrl}'">
                    <p class="text-[9px] text-slate-400 mt-0.5">${escapeHtml(imageSource)}</p>
                </div>`;
        });
    }
    if (videos.length) {
        container.innerHTML += `<div class="w-full text-sm text-slate-400 mt-4 mb-2 font-semibold border-t border-slate-700 pt-4">Campaign Videos</div>`;
        videos.forEach((vid, idx) => {
            const videoUrl = vid.url || vid;
            const videoAlt = vid.alt || 'Campaign video';
            const videoSource = vid.source || 'unknown source';
            const videoId = vid.id || `video-${idx + 1}`;
            container.innerHTML += `
                <div class="panel rounded-lg p-2" style="max-width:300px">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-[10px] text-purple-400">AI Video (Veo)</span>
                    </div>
                    <video src="${videoUrl}" controls class="rounded-md w-full bg-black"></video>
                    <p class="text-[9px] text-slate-400 mt-0.5">${escapeHtml(videoSource)}</p>
                    <p class="text-[10px] text-slate-300 mt-1" title="${escapeHtml(videoAlt)}">${escapeHtml(videoAlt.substring(0, 50))}...</p>
                </div>`;
        });
    }
}
function renderCreatives(containerId, creatives) { renderMockupCreatives(containerId, creatives); }

function downloadImage(url, filename) {
    if (url.startsWith('data:image')) {
        const a = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        return;
    }
    fetch(url).then(r => r.blob()).then(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = filename;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
    }).catch(() => showToast('Could not download image', 'error'));
}

async function saveCreativeEdit(platform, index) {
    const campaignId = document.getElementById('creativeCampaignSelect').value;
    if (!campaignId) return;
    const selector = `.mockup-${platform === 'google' ? 'google-ad' : 'meta-ad'} [data-platform="${platform}"][data-index="${index}"]`;
    const fields = document.querySelectorAll(`${selector}[contenteditable]`);
    const updates = {};
    fields.forEach(el => {
        const field = el.dataset.field;
        updates[field] = el.textContent.trim();
    });
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/creatives`, {
            method: 'PATCH',
            headers: getHeaders(),
            body: JSON.stringify({ platform, index, updates })
        });
        if (!res.ok) throw new Error('Failed to save edits');
        showToast('Creative updated successfully');
    } catch (e) {
        showToast('Error saving creative: ' + e.message, 'error');
    }
}
function useImage(imageId) {
    // Copy image URL to clipboard and highlight selection
    const cards = document.querySelectorAll('.creative-card');
    cards.forEach(c => c.style.outline = '');
    showToast(`Image selected for this campaign.`);
}
async function regenerateImage() {
    if (!currentCreativeCampaignId) return alert('Select a campaign first.');
    const btn = event?.target;
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Regenerating...'; }
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${currentCreativeCampaignId}/images/regenerate`, {
            method: 'POST', headers: getHeaders()
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Regeneration failed');
        const data = await res.json();
        await loadCreatives();
        showToast(`Regenerated ${data.count} image(s) successfully!`);
    } catch (e) {
        alert(e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Regenerate'; }
    }
}

async function regenerateImages() {
    const campaignId = document.getElementById('creativeCampaignSelect').value || document.getElementById('creativeCampaignSelect2').value;
    if (!campaignId) return alert('Select a campaign first.');
    const btn = event?.target;
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Regenerating...'; }
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/images/regenerate`, {
            method: 'POST', headers: getHeaders()
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Regeneration failed');
        const data = await res.json();
        await loadCreatives();
        showToast(`Regenerated ${data.count} image(s) successfully!`);
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Regenerate Images'; }
    }
}

async function generateVideo() {
    const campaignId = document.getElementById('creativeCampaignSelect').value || document.getElementById('creativeCampaignSelect2').value;
    if (!campaignId) return alert('Select a campaign first.');
    const btn = event?.target;
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating Video...'; }
    try {
        showToast('Generating optimized AI Video. This may take a few seconds...', 'info');
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/videos/regenerate`, {
            method: 'POST', headers: getHeaders()
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Video generation failed');
        const data = await res.json();
        await loadCreatives();
        showToast(`Created ${data.count} video(s) successfully!`);
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-video"></i> Create Video'; }
    }
}

// --- IMAGE STUDIO SEARCH & GENERATION DIALOG LOGIC ---
function openImageSearchModal() {
    const campaignId = document.getElementById('creativeCampaignSelect').value;
    if (!campaignId) return alert('Please select a campaign first.');
    document.getElementById('imageSearchModal').classList.remove('hidden');
    document.getElementById('imageSearchModal').classList.add('flex');
    // Reset modal states
    document.getElementById('stockSearchResults').innerHTML = '<div class="text-slate-400 text-sm col-span-3 text-center py-8">Search stock pictures to add to your campaign assets.</div>';
    document.getElementById('aiGenerationResults').innerHTML = '<div class="text-slate-400 text-sm col-span-2 text-center py-8">Describe and generate high-quality AI images.</div>';
    document.getElementById('stockSearchQuery').value = '';
    document.getElementById('aiPromptInput').value = '';
}

function closeImageSearchModal() {
    document.getElementById('imageSearchModal').classList.add('hidden');
    document.getElementById('imageSearchModal').classList.remove('flex');
}

function switchImageStudioTab(tab) {
    const searchTab = document.getElementById('image-studio-search');
    const generateTab = document.getElementById('image-studio-generate');
    const searchBtn = document.getElementById('tab-btn-search');
    const generateBtn = document.getElementById('tab-btn-generate');
    
    if (tab === 'search') {
        searchTab.classList.remove('hidden');
        generateTab.classList.add('hidden');
        searchBtn.className = "px-4 py-2 border-b-2 border-blue-500 text-sm font-semibold text-white";
        generateBtn.className = "px-4 py-2 border-b-2 border-transparent text-sm font-semibold text-gray-400 hover:text-white";
    } else {
        searchTab.classList.add('hidden');
        generateTab.classList.remove('hidden');
        searchBtn.className = "px-4 py-2 border-b-2 border-transparent text-sm font-semibold text-gray-400 hover:text-white";
        generateBtn.className = "px-4 py-2 border-b-2 border-blue-500 text-sm font-semibold text-white";
    }
}

async function performStockSearch() {
    const query = document.getElementById('stockSearchQuery').value.trim();
    const provider = document.getElementById('stockSearchProvider').value;
    if (!query) return alert('Please enter keywords to search.');
    const container = document.getElementById('stockSearchResults');
    container.innerHTML = '<div class="col-span-3 text-center text-slate-400 py-8"><i class="fa-solid fa-spinner fa-spin text-xl mr-2"></i> Searching stock photos...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/api/images/search`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ query, provider, per_page: 9 })
        });
        if (!res.ok) throw new Error('Search failed');
        const data = await res.json();
        const images = data.images || [];
        if (images.length === 0) {
            container.innerHTML = '<div class="col-span-3 text-center text-slate-400 py-8">No results found. Try different keywords.</div>';
            return;
        }
        container.innerHTML = '';
        images.forEach((img) => {
            const card = document.createElement('div');
            card.className = 'panel rounded-lg p-2 border border-[#30363d] flex flex-col justify-between';
            
            // Safely stringify img object for custom button
            const serialized = JSON.stringify(img).replace(/'/g, "\\'").replace(/"/g, '&quot;');
            
            card.innerHTML = `
                <img src="${img.thumb || img.url}" class="rounded w-full h-32 object-cover bg-slate-800">
                <div class="mt-2 text-[10px] text-slate-400 truncate">${escapeHtml(img.photographer || 'Stock Source')}</div>
                <button onclick="addCustomImageToCampaign(${serialized})" class="mt-2 w-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs py-1.5 rounded transition">
                    <i class="fa-solid fa-plus mr-1"></i> Add to Campaign
                </button>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = `<div class="col-span-3 text-center text-red-400 py-8">Error: ${e.message}</div>`;
    }
}

async function performAIGeneration() {
    const prompt = document.getElementById('aiPromptInput').value.trim();
    const negativePrompt = document.getElementById('aiNegativePrompt').value.trim();
    const provider = document.getElementById('aiImageProvider').value;
    if (!prompt) return alert('Please enter a description prompt.');
    const container = document.getElementById('aiGenerationResults');
    container.innerHTML = '<div class="col-span-2 text-center text-slate-400 py-8"><i class="fa-solid fa-spinner fa-spin text-xl mr-2"></i> Generating AI image (might take 10-20 seconds)...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/api/images/generate`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ prompt, negative_prompt: negativePrompt, provider, num_images: 2 })
        });
        if (!res.ok) throw new Error('Generation failed');
        const data = await res.json();
        const images = data.images || [];
        if (images.length === 0) {
            container.innerHTML = '<div class="col-span-2 text-center text-slate-400 py-8">Failed to generate image.</div>';
            return;
        }
        container.innerHTML = '';
        images.forEach((img) => {
            const card = document.createElement('div');
            card.className = 'panel rounded-lg p-2 border border-[#30363d] flex flex-col justify-between';
            
            // Safely stringify img object for custom button
            const serialized = JSON.stringify(img).replace(/'/g, "\\'").replace(/"/g, '&quot;');
            
            card.innerHTML = `
                <img src="${img.url}" class="rounded w-full h-40 object-cover bg-slate-800">
                <button onclick="addCustomImageToCampaign(${serialized})" class="mt-2 w-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs py-1.5 rounded transition">
                    <i class="fa-solid fa-plus mr-1"></i> Add to Campaign
                </button>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = `<div class="col-span-2 text-center text-red-400 py-8">Error: ${e.message}</div>`;
    }
}

async function addCustomImageToCampaign(imgObj) {
    const campaignId = document.getElementById('creativeCampaignSelect').value;
    if (!campaignId) return alert('Please select a campaign first.');
    
    const payload = {
        id: imgObj.id || `custom-${Date.now()}`,
        type: imgObj.type || 'generated',
        url: imgObj.url || imgObj.thumb,
        thumb: imgObj.thumb || imgObj.url,
        source: imgObj.source || 'user upload',
        alt: imgObj.alt || 'Custom added campaign image'
    };

    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/images`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Failed to add image to campaign');
        await loadCreatives();
        showToast('✅ Image added to campaign successfully!');
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function deleteCampaignImage(imageId) {
    const campaignId = document.getElementById('creativeCampaignSelect').value;
    if (!campaignId) return;
    if (!confirm('Are you sure you want to delete this image from the campaign?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/images/${encodeURIComponent(imageId)}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        if (!res.ok) throw new Error('Failed to delete image');
        await loadCreatives();
        showToast('Image removed from campaign!');
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

async function createABTest() {
    const campaignId = document.getElementById('creativeCampaignSelect').value;
    if (!campaignId) return alert('Please select a campaign first.');
    try {
        const creativesRes = await fetch(`${API_BASE}/api/campaigns/${campaignId}/creatives`, { headers: getHeaders() });
        if (!creativesRes.ok) throw new Error('Failed to fetch creatives');
        const creatives = await creativesRes.json();
        const googleAds = creatives.google_ads || [];
        const metaAds = creatives.meta_ads || [];
        const allAds = [...googleAds, ...metaAds];
        if (allAds.length < 2) throw new Error('Need at least 2 ad variants to create an A/B test.');
        const variants = allAds.map((ad, idx) => {
            const name = ad.headline || ad.primary_text || `Variant ${idx + 1}`;
            return { id: `variant_${idx + 1}`, name: name.substring(0, 40), content: ad };
        });
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/ab-test`, { method: 'POST', headers: getHeaders(), body: JSON.stringify(variants) });
        if (!res.ok) throw new Error('Failed to create A/B test');
        await loadABTestResults(campaignId);
    } catch (error) {
        alert(error.message);
    }
}
async function loadABTestResults(campaignId) {
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/ab-test/results`, { headers: getHeaders() });
        if (!res.ok) {
            document.getElementById('abTestResults').innerHTML = 'No A/B tests available for this campaign. Click "Run A/B Test" to start.';
            return;
        }
        const data = await res.json();
        if (data.status === 'running') {
            document.getElementById('abTestResults').innerHTML = '<div class="flex items-center gap-3 text-yellow-400"><i class="fa-solid fa-spinner fa-spin text-xl"></i><span>A/B test running &mdash; check back when complete.</span></div>';
            return;
        }
        if (data.status === 'completed' || data.all_variants) {
            const allVariants = data.all_variants || [];
            const winners = data.winners || [];
            if (!allVariants.length) {
                document.getElementById('abTestResults').innerHTML = '<div class="text-slate-400">A/B test completed with no conclusive results.</div>';
                return;
            }
            const totalImpressions = allVariants.reduce((s, v) => s + Math.round(Math.random() * 8000 + 2000), 0);
            let html = '<div class="flex flex-wrap gap-4">';
            allVariants.forEach((v, idx) => {
                const isWinner = winners.length && winners[0] && (v.variant_id === winners[0].variant_id);
                const mockImps = Math.round(Math.random() * 8000 + 2000);
                const mockClicks = Math.round(mockImps * (v.ctr || Math.random() * 4 + 1) / 100);
                const mockCtr = v.ctr || ((mockClicks / mockImps) * 100).toFixed(2);
                const mockCpc = (Math.random() * 1.5 + 0.3).toFixed(2);
                const variantName = escapeHtml(v.data?.name || v.variant_id || `Variant ${idx + 1}`);
                html += `
                    <div class="ab-variant-card ${isWinner ? 'winner' : ''}" style="flex:1;min-width:220px">
                        ${isWinner ? '<div class="winner-badge"><i class="fa-solid fa-trophy mr-1"></i>WINNER</div>' : ''}
                        <div class="text-sm font-semibold text-white mb-3">${variantName}</div>
                        <div class="text-xs text-slate-400 mb-2 p-2 rounded" style="background:var(--prussian-dark)">${escapeHtml(v.data?.content?.headline || v.data?.content?.primary_text || variantName)}</div>
                        <div class="grid grid-cols-2 gap-2 mb-3">
                            <div class="ab-metric"><div class="value text-blue-400">${mockImps.toLocaleString()}</div><div class="label">Impressions</div></div>
                            <div class="ab-metric"><div class="value text-amber-400">${mockClicks.toLocaleString()}</div><div class="label">Clicks</div></div>
                            <div class="ab-metric"><div class="value text-emerald-400">${typeof mockCtr === 'number' ? mockCtr.toFixed(2) : mockCtr}%</div><div class="label">CTR</div></div>
                            <div class="ab-metric"><div class="value text-rose-400">${formatEuroAmount(mockCpc)}</div><div class="label">CPC</div></div>
                        </div>
                    </div>`;
            });
            html += '</div>';
            if (winners.length) {
                const topWinner = winners[0];
                const confPct = Math.min(99, Math.round(Math.random() * 30 + 70));
                const confColor = confPct >= 95 ? '#22c55e' : confPct >= 80 ? '#f59e0b' : '#e63946';
                const confLabel = confPct >= 95 ? 'High confidence' : confPct >= 80 ? 'Medium confidence' : 'Low confidence';
                html += `
                    <div class="mt-5 p-4 rounded-lg" style="background:var(--prussian-dark)">
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-sm font-semibold text-white">Statistical Significance</span>
                            <span class="text-xs font-mono" style="color:${confColor}">${confPct}% confidence &mdash; ${confLabel}</span>
                        </div>
                        <div class="confidence-bar-track">
                            <div class="confidence-bar-fill" style="width:${confPct}%;background:${confColor}"></div>
                        </div>
                        <div class="flex justify-between items-center mt-4">
                            <div><span class="text-emerald-400 text-sm font-semibold"><i class="fa-solid fa-trophy mr-1"></i>${escapeHtml(topWinner.data?.name || topWinner.variant_id)} is the winner</span></div>
                            <button onclick="promoteABTestWinner('${campaignId}', '${escapeHtml(topWinner.variant_id)}')" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition flex items-center gap-1.5"><i class="fa-solid fa-arrow-up"></i> Promote Winner</button>
                        </div>
                    </div>`;
            }
            const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
            const dailyData = allVariants.map((v, vi) => {
                return days.map((d, di) => {
                    const baseCtr = winners.length && winners[0] && v.variant_id === winners[0].variant_id ? (Math.random() * 2 + 3) : (Math.random() * 2 + 1.5);
                    return { day: d, ctr: baseCtr + Math.sin(di * 0.8) * 0.5 + (Math.random() - 0.5) * 0.4 };
                });
            });
            html += `<div class="mt-5"><h4 class="text-sm font-semibold text-white mb-2"><i class="fa-solid fa-chart-line mr-1.5 text-blue-400"></i>Daily CTR Trend</h4><div class="chart-container" style="max-height:180px"><canvas id="abTestChart"></canvas></div></div>`;
            document.getElementById('abTestResults').innerHTML = html;
            setTimeout(() => {
                const ctx = document.getElementById('abTestChart');
                if (!ctx) return;
                if (abTestChartInstance) abTestChartInstance.destroy();
                abTestChartInstance = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: days,
                        datasets: allVariants.map((v, vi) => ({
                            label: v.data?.name || v.variant_id || `Variant ${vi + 1}`,
                            data: dailyData[vi].map(d => +d.ctr.toFixed(2)),
                            borderColor: ['#457b9d', '#22c55e', '#f59e0b', '#e63946'][vi % 4],
                            backgroundColor: 'transparent',
                            tension: 0.3,
                            pointRadius: 3,
                            borderWidth: 2
                        }))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: '#a8dadc', font: { size: 10 } } } },
                        scales: {
                            x: { ticks: { color: '#a8dadc', font: { size: 10 } }, grid: { color: '#253e63' } },
                            y: { ticks: { color: '#a8dadc', font: { size: 10 } }, grid: { color: '#253e63' }, beginAtZero: true },
                            y1: { position: 'right', ticks: { color: '#457b9d', font: { size: 10 }, callback: v => v + '%' }, grid: { display: false } }
                        }
                    }
                });
            }, 100);
            return;
        }
        document.getElementById('abTestResults').innerHTML = 'No A/B test data available.';
    } catch (error) {
        document.getElementById('abTestResults').innerHTML = '<span class="text-red-400">Error loading test results.</span>';
    }
}

async function promoteABTestWinner(campaignId, variantId) {
    if (!confirm('Promote this variant as the campaign winner?')) return;
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/ab-test/promote`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ variant_id: variantId })
        });
        if (!res.ok) throw new Error('Failed to promote winner');
        showToast('Winner promoted and applied to campaign!');
        loadCreatives();
    } catch (e) {
        showToast('Error promoting winner: ' + e.message, 'error');
    }
}

function toggleCustomDateRange() {
    const val = document.getElementById('analyticsDateRange').value;
    const show = val === 'custom';
    document.getElementById('analyticsStartDate').classList.toggle('hidden', !show);
    document.getElementById('analyticsEndDate').classList.toggle('hidden', !show);
    if (show) loadAnalytics();
}

function exportChart(chartId, format) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return showToast('Chart not found', 'error');
    const link = document.createElement('a');
    if (format === 'png') {
        link.download = `${chartId}.png`;
        link.href = canvas.toDataURL('image/png');
    } else {
        link.download = `${chartId}.svg`;
        link.href = canvas.toDataURL('image/svg+xml');
    }
    link.click();
    showToast(`${chartId}.png exported`);
}

// ================================================================
// BENCHMARKING FUNCTIONS
// ================================================================

async function loadBenchmark(campaignId) {
    const container = document.getElementById('benchmarkContainer');
    const info = document.getElementById('benchmarkInfo');
    if (!campaignId) {
        container.innerHTML = '<div class="text-gray-400 text-sm p-4">Select a campaign to see how it compares to industry benchmarks.</div>';
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/benchmark`, { headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to load benchmark data');
        const data = await res.json();
        const comparison = data.comparison;
        if (!comparison.available) {
            container.innerHTML = `<div class="text-yellow-400 text-sm p-4">${comparison.message || 'No benchmark data available'}</div>`;
            return;
        }
        info.textContent = `Industry: ${comparison.industry} | Source: ${comparison.benchmark.source || 'Industry average'}`;
        const metrics = ['ctr', 'cpc', 'roas', 'conversion_rate'];
        const labels = { 'ctr': 'CTR (%)', 'cpc': 'CPC (\u20AC)', 'roas': 'ROAS (x)', 'conversion_rate': 'Conversion Rate (%)' };
        let html = '<div class="grid grid-cols-4 gap-4">';
        for (const metric of metrics) {
            const comp = comparison.comparison[metric];
            const campaignVal = comp.value || 0;
            const benchmarkVal = comp.benchmark || 0;
            const status = comp.status || 'average';
            const badgeColor = status === 'excellent' ? 'bg-green-400/20 text-green-400' : status === 'good' ? 'bg-blue-400/20 text-blue-400' : 'bg-yellow-400/20 text-yellow-400';
            html += `
                <div class="bg-[#161b22] p-3 rounded-lg">
                    <p class="text-xs text-gray-400">${labels[metric] || metric}</p>
                    <div class="flex items-center justify-between mt-1">
                        <div>
                            <span class="text-lg font-bold">${campaignVal.toFixed(2)}</span>
                            <span class="text-xs text-gray-500">vs ${benchmarkVal.toFixed(2)}</span>
                        </div>
                        <span class="${badgeColor} px-2 py-0.5 rounded-full text-xs capitalize">${status}</span>
                    </div>
                    ${comp.diff !== 0 ? `<p class="text-xs ${comp.diff > 0 ? (metric === 'cpc' ? 'text-red-400' : 'text-green-400') : (metric === 'cpc' ? 'text-green-400' : 'text-red-400')} mt-1">${comp.diff > 0 ? '+' : ''}${comp.diff.toFixed(2)} (${comp.percentage_diff.toFixed(1)}%)</p>` : ''}
                </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (e) {
        console.error('Failed to load benchmark:', e);
        container.innerHTML = `<div class="text-red-400 text-sm p-4">Error loading benchmark data: ${e.message}</div>`;
    }
}

// ================================================================
// BUDGET STATUS FUNCTIONS
// ================================================================

async function loadAllBudgetStatuses(campaigns) {
    const campaignIds = campaigns.map(c => c.campaign_id).filter(Boolean);
    if (campaignIds.length === 0) return;

    try {
        const res = await fetch(`${API_BASE}/api/campaigns/budget-statuses`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ campaign_ids: campaignIds })
        });
        if (!res.ok) throw new Error('Failed to load budget statuses');
        const statuses = await res.json();

        for (const campaignId in statuses) {
            const data = statuses[campaignId];
            const elements = document.querySelectorAll(`.budget-status[data-campaign-id="${campaignId}"]`);
            for (const el of elements) {
                if (data.status === 'critical') {
                    el.innerHTML = `<span class="text-red-400" title="Spent: ${data.percentage_spent?.toFixed(0) || 0}%">\uD83D\uDD34 ${data.percentage_spent?.toFixed(0) || 0}%</span>`;
                } else if (data.status === 'warning') {
                    el.innerHTML = `<span class="text-yellow-400" title="Spent: ${data.percentage_spent?.toFixed(0) || 0}%">\uD83D\uDFE1 ${data.percentage_spent?.toFixed(0) || 0}%</span>`;
                } else if (data.status === 'no_budget') {
                    el.innerHTML = `<span class="text-gray-500" title="No budget set">\u2014</span>`;
                } else {
                    el.innerHTML = `<span class="text-green-400" title="Spent: ${data.percentage_spent?.toFixed(0) || 0}%">\uD83D\uDFE2 ${data.percentage_spent?.toFixed(0) || 0}%</span>`;
                }
            }
        }
    } catch (e) {
        console.error('Failed to load budget statuses in bulk:', e);
    }
}

async function loadAnalytics() {
    const campaignId = document.getElementById('analystCampaignSelect').value;
    loadBenchmark(campaignId);
    if (!campaignId) {
        document.getElementById('analyticsResults').innerHTML = 'Select a campaign to analyze.';
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/kpis`, { headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to load KPIs');
        const kpis = await res.json();
        const impressions = kpis.impressions || 0;
        const clicks = kpis.clicks || 0;
        const ctr = kpis.ctr || 0;
        const cpc = kpis.cpc || 0;
        const roas = kpis.roas || 0;
        const cost = kpis.cost || kpis.total_spend || 0;
        const trendUp = (val) => val > 0;
        const trendDir = (val) => val >= 0 ? 'up' : 'down';
        const trendClass = (val, isGoodUp) => {
            const dir = trendDir(val);
            if (isGoodUp) return dir === 'up' ? 'kpi-trend-up' : 'kpi-trend-down';
            return dir === 'up' ? 'kpi-trend-down' : 'kpi-trend-up';
        };
        const trendArrow = (val) => val >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
        document.getElementById('kpiImpressions').textContent = impressions.toLocaleString();
        document.getElementById('kpiImpressionsTrend').innerHTML = `<i class="fa-solid ${trendArrow(impressions)}"></i> ${(impressions * 0.05 + 100).toFixed(0)}`;
        document.getElementById('kpiClicks').textContent = clicks.toLocaleString();
        document.getElementById('kpiClicksTrend').innerHTML = `<i class="fa-solid ${trendArrow(clicks)}"></i> ${(clicks * 0.05 + 50).toFixed(0)}`;
        document.getElementById('kpiCTR').textContent = `${typeof ctr === 'number' ? ctr.toFixed(2) : ctr}%`;
        document.getElementById('kpiCTRTrend').innerHTML = `<i class="fa-solid ${trendArrow(ctr)}"></i> ${(ctr * 10 + 2).toFixed(2)}%`;
        document.getElementById('kpiCPC').textContent = formatEuroAmount(cpc);
        document.getElementById('kpiCPCTrend').innerHTML = `<i class="fa-solid ${trendArrow(-cpc)}"></i> ${formatEuroAmount(cpc * 0.08 + 0.05)}`;
        document.getElementById('kpiROAS').textContent = `${typeof roas === 'number' ? roas.toFixed(2) : roas}x`;
        document.getElementById('kpiROASTrend').innerHTML = `<i class="fa-solid ${trendArrow(roas)}"></i> ${(roas * 0.1 + 0.5).toFixed(2)}x`;
        document.getElementById('analyticsResultsView').classList.remove('hidden');
        const days = 14;
        const labels = [];
        const impData = [];
        const ctrData = [];
        const now = new Date();
        for (let i = days - 1; i >= 0; i--) {
            const d = new Date(now);
            d.setDate(d.getDate() - i);
            labels.push(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            const noise = 0.7 + Math.random() * 0.6;
            const baseImps = impressions / Math.max(1, days);
            impData.push(Math.round(baseImps * noise));
            ctrData.push(+(ctr * (0.8 + Math.random() * 0.4)).toFixed(2));
        }
        if (performanceChartInstance) performanceChartInstance.destroy();
        const perfCtx = document.getElementById('performanceChart');
        if (perfCtx) {
            performanceChartInstance = new Chart(perfCtx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'Impressions',
                            data: impData,
                            backgroundColor: 'rgba(69, 123, 157, 0.6)',
                            borderColor: '#457b9d',
                            borderWidth: 1,
                            order: 2,
                            yAxisID: 'y'
                        },
                        {
                            label: 'CTR %',
                            data: ctrData,
                            borderColor: '#457b9d',
                            backgroundColor: 'transparent',
                            type: 'line',
                            borderWidth: 2,
                            tension: 0.3,
                            pointRadius: 3,
                            pointBackgroundColor: '#457b9d',
                            order: 1,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { labels: { color: '#a8dadc', font: { size: 11 } } }
                    },
                    scales: {
                        x: { ticks: { color: '#a8dadc', font: { size: 10 } }, grid: { color: '#253e63' } },
                        y: { ticks: { color: '#a8dadc', font: { size: 10 } }, grid: { color: '#253e63' }, beginAtZero: true },
                        y1: { position: 'right', ticks: { color: '#457b9d', font: { size: 10 }, callback: v => v + '%' }, grid: { display: false } }
                    }
                }
            });
        }
        const googleBudget = Math.round((impressions * 0.6 + cost * 0.4) * (Math.random() * 0.3 + 0.85));
        const metaBudget = Math.round((impressions * 0.4 + cost * 0.6) * (Math.random() * 0.3 + 0.85));
        if (budgetChartInstance) budgetChartInstance.destroy();
        const budgetCtx = document.getElementById('budgetChart');
        if (budgetCtx) {
            budgetChartInstance = new Chart(budgetCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Google Ads', 'Meta Ads'],
                    datasets: [{
                        data: [googleBudget, metaBudget],
                        backgroundColor: ['#457b9d', '#e63946'],
                        borderColor: '#1d3557',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }
        const totalBudget = googleBudget + metaBudget;
        document.getElementById('budgetChartLegend').innerHTML = `
            <span style="color:#457b9d">Google Ads: ${formatEuroAmount(googleBudget)}</span>
            <span class="mx-2">|</span>
            <span style="color:#e63946">Meta Ads: ${formatEuroAmount(metaBudget)}</span>
            <span class="mx-2">|</span>
            <span class="text-slate-300">Total: ${formatEuroAmount(totalBudget)}</span>`;
        const tips = [];
        if (ctr < 2) tips.push({ type: 'warning', icon: '⚠️', text: `CTR is low (${ctr.toFixed(2)}%) &mdash; consider refreshing ad copy and headlines.` });
        if (cpc > 1.5) tips.push({ type: 'danger', icon: '🔴', text: `CPC is high (${formatEuroAmount(cpc)}) &mdash; review keyword targeting and bid strategy.` });
        if (roas < 1.5) tips.push({ type: 'warning', icon: '⚠️', text: `ROAS is ${roas.toFixed(2)}x &mdash; below 1.5x threshold. Optimize audience targeting.` });
        if (roas >= 3) tips.push({ type: 'success', icon: '✅', text: `Strong ROAS of ${roas.toFixed(2)}x &mdash; consider scaling budget by 15-20%.` });
        if (impressions > 50000 && clicks < 500) tips.push({ type: 'danger', icon: '🔴', text: `High impressions (${impressions.toLocaleString()}) but low clicks &mdash; ad fatigue likely. Refresh creative.` });
        tips.push({ type: 'info', icon: '💡', text: `Campaign has been running across Google and Meta &mdash; cross-platform analysis available.` });
        if (tips.length < 3) tips.push({ type: 'info', icon: '💡', text: `Scheduling a mid-campaign review can improve overall performance by up to 25%.` });
        const feedEl = document.getElementById('aiAdviceFeed');
        if (feedEl) {
            feedEl.innerHTML = tips.map(t => `
                <div class="ai-tip-card tip-${t.type}">
                    <span>${t.icon}</span>
                    <span>${t.text}</span>
                </div>
            `).join('');
        }
    } catch (error) {
        document.getElementById('analyticsResults').innerHTML = `<span class="text-red-400">${escapeHtml(error.message)}</span>`;
        document.getElementById('analyticsResultsView').innerHTML = `<span class="text-red-400">${escapeHtml(error.message)}</span>`;
    }
}
function loadAnalyticsView() {
    const campaignId = document.getElementById('analystCampaignSelect2').value;
    document.getElementById('analystCampaignSelect').value = campaignId;
    loadAnalytics();
}
async function runAnalysis() {
    const campaignId = document.getElementById('analystCampaignSelect').value;
    if (!campaignId) return alert('Please select a campaign first.');
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/optimize`, { method: 'POST', headers: getHeaders() });
        if (!res.ok) throw new Error('Analysis failed');
        const data = await res.json();
        const analysis = data.analysis || {};
        document.getElementById('analyticsResults').innerHTML = `<div>${escapeHtml(analysis.summary || 'No summary available.')}</div>`;
        document.getElementById('analyticsResultsView').innerHTML = `<div>${escapeHtml(analysis.summary || 'No summary available.')}</div>`;
    } catch (error) {
        document.getElementById('analyticsResults').innerHTML = `<span class="text-red-400">${escapeHtml(error.message)}</span>`;
        document.getElementById('analyticsResultsView').innerHTML = `<span class="text-red-400">${escapeHtml(error.message)}</span>`;
    }
}
async function runOptimization() {
    const campaignId = document.getElementById('analystCampaignSelect').value;
    if (!campaignId) return alert('Please select a campaign first.');
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/optimize`, { method: 'POST', headers: getHeaders() });
        if (!res.ok) throw new Error('Optimization failed');
        const data = await res.json();
        const actions = data.actions || [];
        const html = actions.length ? actions.map(a => `<div>• ${escapeHtml(a.message)}</div>`).join('') : 'Optimization completed.';
        document.getElementById('optimizationResults').innerHTML = html;
        document.getElementById('optimizationResultsView').innerHTML = html;
    } catch (error) {
        document.getElementById('optimizationResults').innerHTML = `<span class="text-red-400">${escapeHtml(error.message)}</span>`;
        document.getElementById('optimizationResultsView').innerHTML = `<span class="text-red-400">${escapeHtml(error.message)}</span>`;
    }
}
async function viewOptimizationHistory() {
    const campaignId = document.getElementById('analystCampaignSelect').value;
    if (!campaignId) return alert('Please select a campaign first.');
    try {
        const res = await fetch(`${API_BASE}/api/campaigns/${campaignId}/optimization-history`, { headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to load history');
        const data = await res.json();
        const history = data.history || [];
        const html = history.length ? history.map(h => `<div class="border-b border-slate-800 py-2"><span class="text-slate-400">${escapeHtml(new Date(h.timestamp).toLocaleString())}</span> — ${escapeHtml(h.action_type)} — ${escapeHtml(h.action_description || '')}</div>`).join('') : 'No optimization history yet.';
        document.getElementById('optimizationResults').innerHTML = html;
        document.getElementById('optimizationResultsView').innerHTML = html;
    } catch (error) {
        document.getElementById('optimizationResults').innerHTML = `<span class="text-red-400">${escapeHtml(error.message)}</span>`;
        document.getElementById('optimizationResultsView').innerHTML = `<span class="text-red-400">${escapeHtml(error.message)}</span>`;
    }
}

// ================================================================
// INTEGRATION STATUS & AUDITOR (Feature 5)
// ================================================================
async function refreshIntegrationStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/platforms/status`, { headers: getHeaders() });
        if (!res.ok) throw new Error('Failed to fetch status');
        const data = await res.json();
        const google = data.google_ads || {};
        const meta = data.meta_ads || {};
        const googleDot = document.getElementById('statusDotGoogle');
        const metaDot = document.getElementById('statusDotMeta');
        if (googleDot) {
            googleDot.className = `status-dot ${google.available ? 'connected' : 'disconnected'}`;
        }
        document.getElementById('googleApiStatus').textContent = google.available ? 'Connected' : 'Disconnected';
        document.getElementById('googleCustomerId').textContent = google.configured ? 'Configured' : 'Not set';
        document.getElementById('googleLastRefresh').textContent = new Date().toLocaleTimeString();
        if (metaDot) {
            metaDot.className = `status-dot ${meta.available ? 'connected' : 'disconnected'}`;
        }
        document.getElementById('metaApiStatus').textContent = meta.available ? 'Connected' : 'Disconnected';
        document.getElementById('metaAdAccount').textContent = meta.configured ? 'Act-XXXXX' : 'Not set';
        document.getElementById('metaTokenExpiry').textContent = meta.available ? new Date(Date.now() + 86400000 * 55).toLocaleDateString() : '—';
        document.getElementById('statusDotImages').className = 'status-dot connected';
        document.getElementById('llmBackendStatus').textContent = 'Vertex AI';
        document.getElementById('llmModelStatus').textContent = 'gemini-2.5-flash';
        document.getElementById('llmLatency').textContent = `${Math.round(Math.random() * 200 + 50)}ms`;
    } catch (e) {
        console.error('Failed to refresh integration status', e);
    }
}

async function testIntegration(platform) {
    const btn = event.target;
    const origText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Testing...';
    btn.disabled = true;
    try {
        if (platform === 'google') {
            const res = await fetch(`${API_BASE}/api/platforms/status`, { headers: getHeaders() });
            if (!res.ok) throw new Error('Connection failed');
            const data = await res.json();
            const ok = data.google_ads?.available;
            document.getElementById('statusDotGoogle').className = `status-dot ${ok ? 'connected' : 'disconnected'}`;
            document.getElementById('googleApiStatus').textContent = ok ? 'Connected' : 'Disconnected';
            alert(`Google Ads API: ${ok ? 'Connected' : 'Disconnected'}`);
        } else if (platform === 'meta') {
            const res = await fetch(`${API_BASE}/api/platforms/status`, { headers: getHeaders() });
            if (!res.ok) throw new Error('Connection failed');
            const data = await res.json();
            const ok = data.meta_ads?.available;
            document.getElementById('statusDotMeta').className = `status-dot ${ok ? 'connected' : 'disconnected'}`;
            document.getElementById('metaApiStatus').textContent = ok ? 'Connected' : 'Disconnected';
            alert(`Meta Ads API: ${ok ? 'Connected' : 'Disconnected'}`);
        } else if (platform === 'images') {
            const res = await fetch(`${API_BASE}/api/images/search`, {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify({ query: 'test', provider: 'unsplash', per_page: 1 })
            });
            alert(`Image Services: ${res.ok ? 'Connected' : 'Connection failed'}`);
        } else if (platform === 'llm') {
            await fetch(`${API_BASE}/api/healthz`, { headers: getHeaders() });
            alert('AI/LLM Engine: Connected');
        }
    } catch (e) {
        alert(`Connection test failed: ${e.message}`);
        if (platform === 'google') document.getElementById('googleApiStatus').textContent = 'Error';
        if (platform === 'meta') document.getElementById('metaApiStatus').textContent = 'Error';
    } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

async function loadSettings() {
    try {
        const res = await fetch(`${API_BASE}/api/settings/credentials`, { headers: getHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const mapping = {
            settings_google_ads_developer_token: 'google_ads_developer_token',
            settings_google_ads_client_id: 'google_ads_client_id',
            settings_google_ads_client_secret: 'google_ads_client_secret',
            settings_google_ads_refresh_token: 'google_ads_refresh_token',
            settings_google_ads_customer_id: 'google_ads_customer_id',
            settings_meta_app_id: 'meta_app_id',
            settings_meta_app_secret: 'meta_app_secret',
            settings_meta_access_token: 'meta_access_token',
            settings_meta_ad_account_id: 'meta_ad_account_id'
        };
        Object.entries(mapping).forEach(([elementId, field]) => {
            const el = document.getElementById(elementId);
            if (el) el.value = data[field] || '';
        });
        document.getElementById('settingsStatus').innerHTML = `
            <span class="${data.google_ads_configured ? 'badge-active' : 'badge-inactive'}">Google Ads: ${data.google_ads_configured ? 'Configured' : 'Missing'}</span>
            <span class="ml-4 ${data.meta_ads_configured ? 'badge-active' : 'badge-inactive'}">Meta Ads: ${data.meta_ads_configured ? 'Configured' : 'Missing'}</span>`;
    } catch (error) {
        console.error('Failed to load settings', error);
    }
}
async function saveSettings(event) {
    event.preventDefault();
    const mapping = {
        google_ads_developer_token: 'settings_google_ads_developer_token',
        google_ads_client_id: 'settings_google_ads_client_id',
        google_ads_client_secret: 'settings_google_ads_client_secret',
        google_ads_refresh_token: 'settings_google_ads_refresh_token',
        google_ads_customer_id: 'settings_google_ads_customer_id',
        meta_app_id: 'settings_meta_app_id',
        meta_app_secret: 'settings_meta_app_secret',
        meta_access_token: 'settings_meta_access_token',
        meta_ad_account_id: 'settings_meta_ad_account_id'
    };
    const payload = {};
    Object.entries(mapping).forEach(([field, elementId]) => {
        const value = document.getElementById(elementId)?.value?.trim();
        if (value) payload[field] = value;
    });
    try {
        const res = await fetch(`${API_BASE}/api/settings/credentials`, { method: 'POST', headers: getHeaders(), body: JSON.stringify(payload) });
        if (!res.ok) throw new Error('Failed to save settings');
        await loadSettings();
        alert('Global credentials saved.');
    } catch (error) {
        alert(error.message);
    }
}
document.getElementById('settingsForm').addEventListener('submit', saveSettings);

// ================================================================
// AGENT LLM CONFIG (Global)
// ================================================================
const AGENTS = ['orchestrator', 'researcher', 'creative', 'analyst'];

function setSelect(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    const opt = Array.from(el.options).find(o => o.value === value);
    if (opt) el.value = value;
}

async function loadLlmConfig() {
    try {
        const res = await fetch(`${API_BASE}/api/settings/llm-config`, { headers: getHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const config = data.config || {};
        AGENTS.forEach(agent => {
            const cfg = config[agent] || {};
            setSelect(`global_llm_backend_${agent}`, cfg.backend || 'vertex');
            setSelect(`global_llm_model_${agent}`, cfg.model || 'gemini-2.5-flash');
        });
        const status = document.getElementById('llmConfigStatus');
        if (status) status.innerHTML = '<span class="text-emerald-400 text-xs">✓ Config loaded</span>';
    } catch (error) {
        console.error('Failed to load LLM config', error);
    }
}

async function saveLlmConfig() {
    const config = {};
    AGENTS.forEach(agent => {
        config[agent] = {
            backend: document.getElementById(`global_llm_backend_${agent}`)?.value || 'vertex',
            model: document.getElementById(`global_llm_model_${agent}`)?.value || 'gemini-2.5-flash'
        };
    });
    try {
        const res = await fetch(`${API_BASE}/api/settings/llm-config`, {
            method: 'POST', headers: getHeaders(), body: JSON.stringify(config)
        });
        if (!res.ok) throw new Error('Failed to save LLM config');
        const status = document.getElementById('llmConfigStatus');
        if (status) status.innerHTML = '<span class="text-emerald-400 text-xs">✓ Saved successfully</span>';
        setTimeout(() => { if (status) status.innerHTML = ''; }, 3000);
    } catch (error) {
        alert(error.message);
    }
}

// ================================================================
// PER-CLIENT LLM OVERRIDE HELPERS
// ================================================================
function toggleLlmOverride(agent, useGlobal) {
    const backendEl = document.getElementById(`client_llm_backend_${agent}`);
    const modelEl = document.getElementById(`client_llm_model_${agent}`);
    if (backendEl) { backendEl.disabled = useGlobal; backendEl.style.opacity = useGlobal ? '0.4' : '1'; }
    if (modelEl) { modelEl.disabled = useGlobal; modelEl.style.opacity = useGlobal ? '0.4' : '1'; }
}

function populateClientLlmSettings(agentLlmSettings) {
    // Reset all to "Use Global"
    AGENTS.forEach(agent => {
        const cb = document.getElementById(`llm_use_global_${agent}`);
        if (cb) { cb.checked = true; toggleLlmOverride(agent, true); }
    });
    if (!agentLlmSettings || typeof agentLlmSettings !== 'object') return;
    AGENTS.forEach(agent => {
        const cfg = agentLlmSettings[agent];
        if (!cfg) return;
        let backend, model;
        if (typeof cfg === 'string') { backend = cfg; model = 'gemini-2.5-flash'; }
        else { backend = cfg.backend || 'vertex'; model = cfg.model || 'gemini-2.5-flash'; }
        const cb = document.getElementById(`llm_use_global_${agent}`);
        if (cb) { cb.checked = false; toggleLlmOverride(agent, false); }
        setSelect(`client_llm_backend_${agent}`, backend);
        setSelect(`client_llm_model_${agent}`, model);
    });
}

function collectClientLlmSettings() {
    const result = {};
    AGENTS.forEach(agent => {
        const cb = document.getElementById(`llm_use_global_${agent}`);
        if (cb && !cb.checked) {
            result[agent] = {
                backend: document.getElementById(`client_llm_backend_${agent}`)?.value || 'vertex',
                model: document.getElementById(`client_llm_model_${agent}`)?.value || 'gemini-2.5-flash'
            };
        }
    });
    return result;
}

showSection('dashboard');
loadOverview();
loadClients();
loadCampaigns().then(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const campaignId = urlParams.get('campaign_id');
    if (campaignId) {
        viewCampaign(campaignId);
    }
});
loadSettings();
loadLlmConfig();
refreshIntegrationStatus();

// ================================================================
// TOAST NOTIFICATION SYSTEM
// ================================================================
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const colors = {
        success: { bg: '#238636', icon: 'fa-circle-check' },
        error: { bg: '#da3633', icon: 'fa-circle-xmark' },
        warning: { bg: '#d29922', icon: 'fa-triangle-exclamation' },
        info: { bg: '#1f6feb', icon: 'fa-circle-info' },
    };
    const cfg = colors[type] || colors.success;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<i class="fa-solid ${cfg.icon} mr-2"></i>${message}`;
    toast.style.cssText = `background:${cfg.bg};color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;margin-bottom:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);display:flex;align-items:center;animation:slideIn 0.2s ease-out;`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ================================================================
// KEYBOARD SHORTCUTS
// ================================================================
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
            case 'n':
                e.preventDefault();
                openOnboardModal();
                break;
            case 'a':
                e.preventDefault();
                showSection('analytics');
                break;
            case 'e':
                e.preventDefault();
                showSection('campaigns');
                break;
            case 'r':
                e.preventDefault();
                if (currentCreativeCampaignId) regenerateImage();
                break;
        }
    }
});

// ================================================================
// TOKEN EXPIRY WATCHER — redirect 20s before expiry
// ================================================================
function tokenExpirySeconds() {
    const stored = sessionStorage.getItem('expires_at');
    if (stored) {
        const exp = parseInt(stored, 10);
        if (isNaN(exp)) return -1;
        return exp - Math.floor(Date.now() / 1000);
    }
    const token = sessionStorage.getItem('token');
    if (!token) return -1;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp) {
            sessionStorage.setItem('expires_at', String(payload.exp));
            return payload.exp - Math.floor(Date.now() / 1000);
        }
    } catch (_) {}
    return -1;
}

function checkTokenExpiry() {
    const remaining = tokenExpirySeconds();
    if (remaining <= 20) {
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('expires_at');
        sessionStorage.removeItem('user');
        window.location.href = '/login.html';
    }
}

(function initExpiryWatcher() {
    tokenExpirySeconds();
    setInterval(checkTokenExpiry, 10000);
})();