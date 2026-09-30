const API_BASE = 'http://localhost:8000';

const AGENT_ORDER = ['planner', 'researcher', 'fact_checker', 'writer', 'editor', 'final_fact_checker'];

let currentRunId = null;
let statusCheckInterval = null;
let elapsedInterval = null;
let startTime = null;

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generateForm');
    const generateBtn = document.getElementById('generateBtn');
    const newContentBtn = document.getElementById('newContentBtn');

    loadProviderInfo();
    form.addEventListener('submit', handleGenerate);
    newContentBtn.addEventListener('click', resetForm);
});

async function loadProviderInfo() {
    try {
        const [configRes, providerRes] = await Promise.all([
            fetch(`${API_BASE}/api/config`),
            fetch(`${API_BASE}/api/content/provider/health`)
        ]);

        const config = configRes.ok ? await configRes.json() : {};
        const provider = providerRes.ok ? await providerRes.json() : {};

        const badge = document.getElementById('providerBadge');
        const providerName = provider.provider || config.llm_provider || 'unknown';
        const modelName = provider.model || config.llm_model || 'unknown';
        badge.textContent = `Provider: ${providerName} · Model: ${modelName}`;
    } catch (error) {
        const badge = document.getElementById('providerBadge');
        badge.textContent = 'Provider: unknown';
    }
}

async function handleGenerate(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const topic = formData.get('topic').trim();
    const platform = formData.get('platform');
    const audience = formData.get('audience').trim();
    const tone = formData.get('tone');
    const posts = parseInt(formData.get('posts')) || 1;
    const length = formData.get('length');
    const keywords = formData.get('keywords').split(',').map(k => k.trim()).filter(k => k);
    const urls = formData.get('urls').split(',').map(u => u.trim()).filter(u => u);

    if (!topic || !audience) {
        showError('Please fill in the topic and audience.');
        return;
    }

    const payload = {
        topic,
        platform,
        audience,
        tone,
        posts,
        length,
        keywords,
        urls,
        provider: formData.get('provider') || undefined,
        model: formData.get('model') || undefined
    };

    const generateBtn = document.getElementById('generateBtn');
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating…';

    try {
        const response = await fetch(`${API_BASE}/api/content/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed to start.');
        }

        const result = await response.json();
        currentRunId = result.run_id;
        startTime = Date.now();

        document.getElementById('formSection').style.display = 'none';
        const statusSection = document.getElementById('statusSection');
        statusSection.style.display = 'block';
        document.getElementById('runId').textContent = currentRunId;
        document.getElementById('status').textContent = 'Starting';
        document.getElementById('qualityScore').textContent = '—';
        document.getElementById('elapsed').textContent = '0s';
        document.getElementById('errorSection').style.display = 'none';
        renderWorkflowSteps([]);

        startStatusCheck();
        startElapsedTimer();
    } catch (error) {
        showError(error.message);
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate';
    }
}

function startStatusCheck() {
    stopStatusCheck();

    statusCheckInterval = setInterval(async () => {
        if (!currentRunId) return;

        try {
            const response = await fetch(`${API_BASE}/api/content/runs/${currentRunId}/status`);
            if (!response.ok) {
                return;
            }

            const status = await response.json();
            updateStatus(status);
        }
    }, 1500);
}

function startElapsedTimer() {
    stopElapsedTimer();

    elapsedInterval = setInterval(() => {
        if (!startTime) return;
        const seconds = Math.floor((Date.now() - startTime) / 1000);
        const el = document.getElementById('elapsed');
        if (el) el.textContent = `${seconds}s`;
    }, 1000);
}

function stopStatusCheck() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

function stopElapsedTimer() {
    if (elapsedInterval) {
        clearInterval(elapsedInterval);
        elapsedInterval = null;
    }
}

async function updateStatus(status) {
    const statusText = document.getElementById('status');
    if (statusText) statusText.textContent = formatStatus(status.status);

    const qualityEl = document.getElementById('qualityScore');
    if (qualityEl) qualityEl.textContent = status.quality_score ? `${status.quality_score}/100` : '—';

    if (['APPROVED', 'NEEDS_HUMAN_REVIEW', 'READY_FOR_REVIEW', 'FAILED'].includes(status.status)) {
        stopStatusCheck();
        stopElapsedTimer();
        await showResults();
    }
}

function formatStatus(status) {
    const map = {
        'CREATED': 'Created',
        'PLANNING': 'Planning',
        'RESEARCHING': 'Researching',
        'FACT_CHECKING': 'Fact checking',
        'WRITING': 'Writing',
        'EDITING': 'Editing',
        'REVISION_REQUIRED': 'Revision required',
        'READY_FOR_REVIEW': 'Ready for review',
        'APPROVED': 'Approved',
        'NEEDS_HUMAN_REVIEW': 'Needs human review',
        'FAILED': 'Failed'
    };
    return map[status] || status;
}

async function showResults() {
    try {
        const [traceResponse, metricsResponse] = await Promise.all([
            fetch(`${API_BASE}/api/content/runs/${currentRunId}/trace`),
            fetch(`${API_BASE}/api/content/runs/${currentRunId}/metrics`)
        ]);

        if (!traceResponse.ok) {
            throw new Error('Failed to load results.');
        }

        const trace = await traceResponse.json();
        const metrics = metricsResponse.ok ? await metricsResponse.json() : null;

        document.getElementById('statusSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'block';

        displayPosts(trace);
        displayMetadata(trace, metrics);
    } catch (error) {
        showError(error.message);
    }
}

function renderWorkflowSteps(agentMetrics) {
    const container = document.getElementById('workflowSteps');
    if (!container) return;

    const completed = new Set();
    const failed = new Set();

    agentMetrics.forEach(m => {
        const name = m.agent;
        if (m.success) completed.add(name);
        else failed.add(name);
    });

    container.innerHTML = AGENT_ORDER.map(name => {
        let cls = 'workflow-step';
        if (completed.has(name)) cls += ' done';
        else if (failed.has(name)) cls += ' failed';

        const icon = failed.has(name) ? '!' : completed.has(name) ? '✓' : '○';
        const label = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        return `<span class="${cls}">${icon} ${label}</span>`;
    }).join('');
}

function displayPosts(trace) {
    const container = document.getElementById('postsContainer');
    container.innerHTML = '';

    let posts = [];
    if (Array.isArray(trace.posts)) {
        posts = trace.posts.filter(Boolean);
    } else {
        const finalContent = (trace.final_content || '').trim();
        try {
            const parsed = JSON.parse(finalContent);
            if (Array.isArray(parsed)) {
                posts = parsed.filter(Boolean);
            }
        } catch {
            posts = finalContent.split('\n\n').filter(Boolean);
        }
    }

    const requestedCount = trace.request?.posts;
    if (requestedCount !== undefined && posts.length !== requestedCount) {
        const warning = document.createElement('p');
        warning.className = 'error-section';
        warning.textContent = `Warning: requested ${requestedCount} posts but received ${posts.length}.`;
        container.appendChild(warning);
    }

    if (posts.length === 0) {
        const errors = (trace.errors && trace.errors.length > 0) ? trace.errors : ['No content generated'];
        container.innerHTML = `<p class="error-section">${errors.map(e => escapeHtml(e)).join('<br>')}</p>`;
        return;
    }

    posts.forEach((post, index) => {
        const card = document.createElement('div');
        card.className = 'post-card';
        card.innerHTML = `
            <div class="post-header">
                <span class="post-number">Post ${index + 1}</span>
                <span class="post-platform">${escapeHtml(trace.request?.platform || 'Unknown')}</span>
            </div>
            <div class="post-content">${escapeHtml(post)}</div>
            <button class="copy-btn" data-copy="${escapeHtml(post)}">Copy</button>
        `;
        container.appendChild(card);
    });

    container.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const text = btn.getAttribute('data-copy');
            try {
                await navigator.clipboard.writeText(text);
                btn.textContent = 'Copied';
                setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
            } catch (e) {
                btn.textContent = 'Copy failed';
            }
        });
    });
}

function displayMetadata(trace, metrics) {
    const sourceCount = document.getElementById('sourceCount');
    if (sourceCount) sourceCount.textContent = (trace.sources?.length || 0).toString();

    const totalTokens = document.getElementById('totalTokens');
    if (totalTokens) totalTokens.textContent = metrics?.total_tokens ? metrics.total_tokens.toString() : '—';

    const totalCost = document.getElementById('totalCost');
    if (totalCost) totalCost.textContent = metrics && metrics.total_cost ? `$${metrics.total_cost.toFixed(4)}` : '—';

    const totalLatency = document.getElementById('totalLatency');
    if (totalLatency) totalLatency.textContent = metrics && metrics.total_latency_ms ? `${metrics.total_latency_ms}ms` : '—';

    const providerEl = document.getElementById('providerBadge');
    if (providerEl && trace.llm_provider) {
        providerEl.textContent = `Provider: ${trace.llm_provider} · Model: ${trace.llm_model || 'unknown'}`;
    }

    const workflowSteps = document.getElementById('workflowSteps');
    if (workflowSteps && trace.metrics) {
        renderWorkflowSteps(trace.metrics);
    }
}

function resetForm() {
    document.getElementById('generateForm').reset();
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('formSection').style.display = 'block';
    document.getElementById('errorSection').style.display = 'none';
    currentRunId = null;
    startTime = null;
    stopStatusCheck();
    stopElapsedTimer();
}

function showError(message) {
    const errorSection = document.getElementById('errorSection');
    const errorList = document.getElementById('errorList');
    errorList.innerHTML = `<li>${escapeHtml(message)}</li>`;
    errorSection.style.display = 'block';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
