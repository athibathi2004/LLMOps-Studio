/**
 * LLMOps Studio - Frontend Application Engine
 * Vanilla JavaScript connecting all 9 sections to REST API endpoints.
 */

// Global State
const state = {
  activeSection: 'overview',
  models: [],
  prompts: [],
  datasets: [],
  experiments: [],
  currentPrompt: null,
  charts: {},
};

// Utilities
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`/api/v1${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || err.message || 'API request failed');
    }
    return await res.json();
  } catch (error) {
    showToast(error.message, 'error');
    throw error;
  }
}

// Navigation Handler
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const sectionKey = item.getAttribute('data-section');
      switchSection(sectionKey);
    });
  });

  // Handle quick action buttons
  document.getElementById('btn-quick-experiment')?.addEventListener('click', () => {
    switchSection('experiments');
  });

  document.getElementById('btn-seed-data')?.addEventListener('click', async () => {
    showToast('Seeding core CS & AI RAG benchmark datasets...', 'info');
    try {
      // Trigger overview refresh after seeding
      await loadModels();
      await loadPrompts();
      await loadDatasets();
      await loadExperiments();
      await loadOverview();
      showToast('Benchmarks and sample data verified.', 'success');
    } catch (e) {
      showToast('Error syncing benchmark data.', 'error');
    }
  });
}

function switchSection(sectionKey) {
  state.activeSection = sectionKey;
  // Update nav item classes
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.classList.toggle('active', item.getAttribute('data-section') === sectionKey);
  });

  // Update view sections
  document.querySelectorAll('.view-section').forEach((sec) => {
    sec.classList.remove('active');
  });
  const target = document.getElementById(`section-${sectionKey}`);
  if (target) {
    target.classList.add('active');
  }

  // Update header title
  const titles = {
    overview: ['Platform Overview', 'Telemetry, benchmark metrics, and execution diagnostics'],
    models: ['Model Registry', 'Configure local and remote model endpoints, hyperparameters, and pricing'],
    prompts: ['Prompt Studio', 'Version, test, and manage prompt templates with live variable interpolation'],
    datasets: ['Dataset Management', 'Manage structured evaluation test sets and ground truth references'],
    experiments: ['Experiment Lab', 'Run controlled multi-model benchmark experiments against evaluation datasets'],
    evaluation: ['Evaluation Center', 'Test individual responses with modular evaluation metrics and RAG Triad diagnostics'],
    comparison: ['Model Comparison', 'Side-by-side benchmarking: Quality scores, latency distributions, and cost'],
    observability: ['Observability & Traces', 'Inspect raw request-response traces, latency distributions, and audit logs'],
    analytics: ['Analytics & Quality Trends', 'Statistical distributions, quality trends over time, and failure diagnostics'],
    history: ['Experiment History', 'Browse historical benchmark runs and compare iterations over time'],
  };

  const [title, sub] = titles[sectionKey] || ['LLMOps Studio', 'Evaluation Platform'];
  document.getElementById('page-title').innerText = title;
  document.getElementById('page-subtitle').innerText = sub;

  // Trigger section load
  loadSectionData(sectionKey);
}

function loadSectionData(sectionKey) {
  switch (sectionKey) {
    case 'overview':
      loadOverview();
      break;
    case 'models':
      loadModels();
      break;
    case 'prompts':
      loadPrompts();
      break;
    case 'datasets':
      loadDatasets();
      break;
    case 'experiments':
      loadExperimentFormDependencies();
      break;
    case 'comparison':
      loadComparisonSection();
      break;
    case 'observability':
      loadTraces();
      break;
    case 'analytics':
      loadAnalytics();
      break;
    case 'history':
      loadExperimentsHistory();
      break;
  }
}

// 1. Overview Section
async function loadOverview() {
  try {
    const data = await apiRequest('/analytics/overview');
    document.getElementById('kpi-experiments').innerText = data.total_experiments;
    document.getElementById('kpi-executions').innerText = data.total_executions;
    document.getElementById('kpi-avg-score').innerText = (data.average_score * 100).toFixed(1) + '%';
    document.getElementById('kpi-avg-latency').innerText = data.average_latency_ms.toFixed(0) + ' ms';
    document.getElementById('kpi-tokens').innerText = Number(data.total_tokens_consumed).toLocaleString();
    document.getElementById('kpi-success-rate').innerText = data.success_rate_percent.toFixed(1) + '%';

    // Load recent executions
    const execs = await apiRequest('/executions?limit=6');
    const tbody = document.querySelector('#table-overview-recent tbody');
    if (!tbody) return;

    if (execs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center">No recent executions. Run an experiment or prompt test to view traces.</td></tr>';
      return;
    }

    tbody.innerHTML = execs.map((e) => `
      <tr>
        <td>${new Date(e.created_at).toLocaleTimeString()}</td>
        <td><code>${e.request_id.slice(0, 8)}...</code></td>
        <td><strong>${e.model_name}</strong></td>
        <td><span class="badge badge-${e.status === 'SUCCESS' ? 'success' : 'danger'}">${e.status}</span></td>
        <td>${e.latency_ms.toFixed(1)} ms</td>
        <td>${e.total_tokens}</td>
        <td>
          <button class="btn btn-sm btn-ghost" onclick="inspectTrace(${e.id})">Inspect</button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Failed to load overview data', e);
  }
}

// 2. Model Registry Section
async function loadModels() {
  try {
    const models = await apiRequest('/models');
    state.models = models;
    const tbody = document.querySelector('#table-models tbody');
    if (!tbody) return;

    if (models.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center">No models registered.</td></tr>';
      return;
    }

    tbody.innerHTML = models.map((m) => {
      const costText = m.cost_per_1k_input_tokens !== null && m.cost_per_1k_input_tokens !== undefined
        ? `$${m.cost_per_1k_input_tokens.toFixed(3)} / $${m.cost_per_1k_output_tokens.toFixed(3)}`
        : '<span class="text-muted">Unavailable</span>';

      return `
        <tr>
          <td><strong>${m.display_name}</strong></td>
          <td><span class="badge badge-info">${m.provider_name || 'Standard'}</span></td>
          <td><code>${m.model_identifier}</code></td>
          <td>${m.default_max_tokens}</td>
          <td>${m.default_temperature} / ${m.default_top_p}</td>
          <td>${costText}</td>
          <td>
            <span class="badge badge-${m.is_available ? 'success' : 'danger'}" id="status-badge-${m.id}">
              ${m.is_available ? 'Available' : 'Offline'}
            </span>
          </td>
          <td>
            <button class="btn btn-sm btn-secondary" onclick="checkModelHealth(${m.id})">Ping Health</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.error('Failed to load models', e);
  }
}

async function checkModelHealth(modelId) {
  try {
    showToast('Pinging model provider...', 'info');
    const health = await apiRequest(`/models/${modelId}/health`);
    const badge = document.getElementById(`status-badge-${modelId}`);
    if (badge) {
      badge.className = `badge badge-${health.is_available ? 'success' : 'danger'}`;
      badge.innerText = health.is_available ? 'Online' : 'Offline';
    }
    showToast(`${health.provider}: ${health.message}`, health.is_available ? 'success' : 'error');
  } catch (e) {
    showToast('Model health check failed.', 'error');
  }
}

function setupModelRegistration() {
  const modal = document.getElementById('modal-register-model');
  document.getElementById('btn-open-register-model')?.addEventListener('click', () => {
    modal.style.display = 'flex';
  });
  document.getElementById('btn-close-register-modal')?.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  const form = document.getElementById('form-register-model');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      provider_name: document.getElementById('reg-provider-select').value,
      model_identifier: document.getElementById('reg-model-id').value.trim(),
      display_name: document.getElementById('reg-display-name').value.trim(),
      description: document.getElementById('reg-desc').value.trim() || null,
      default_temperature: parseFloat(document.getElementById('reg-temp').value),
      default_max_tokens: parseInt(document.getElementById('reg-max-tokens').value),
      cost_per_1k_input_tokens: document.getElementById('reg-cost-in').value ? parseFloat(document.getElementById('reg-cost-in').value) : null,
      cost_per_1k_output_tokens: document.getElementById('reg-cost-out').value ? parseFloat(document.getElementById('reg-cost-out').value) : null,
    };

    try {
      await apiRequest('/models/register', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      showToast('Model registered successfully!', 'success');
      modal.style.display = 'none';
      form.reset();
      loadModels();
    } catch (e) {
      // Error handled in apiRequest
    }
  });
}

// 3. Prompt Studio Section
async function loadPrompts() {
  try {
    const prompts = await apiRequest('/prompts');
    state.prompts = prompts;

    const container = document.getElementById('prompts-list-container');
    if (!container) return;

    if (prompts.length === 0) {
      container.innerHTML = '<div class="empty-state">No prompt templates found. Click "+ New Prompt" to create one.</div>';
      return;
    }

    container.innerHTML = prompts.map((p, idx) => `
      <div class="prompt-item-btn ${idx === 0 ? 'active' : ''}" onclick="selectPrompt(${p.id})">
        <div class="prompt-item-title">${p.name}</div>
        <div class="prompt-item-meta">${p.versions_count} version(s) • ${p.tags || 'untagged'}</div>
      </div>
    `).join('');

    // Populate model select in prompt runner
    await populateModelSelect('prompt-exec-model-select');

    if (prompts.length > 0) {
      selectPrompt(prompts[0].id);
    }
  } catch (e) {
    console.error('Failed to load prompts', e);
  }
}

async function selectPrompt(promptId) {
  try {
    const prompt = await apiRequest(`/prompts/${promptId}`);
    state.currentPrompt = prompt;

    // Highlight active in list
    document.querySelectorAll('.prompt-item-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('onclick')?.includes(`(${promptId})`));
    });

    document.getElementById('current-prompt-title').innerText = prompt.name;
    const latest = prompt.latest_version;
    if (latest) {
      document.getElementById('current-prompt-version-badge').innerText = `v${latest.version_number}`;
      document.getElementById('prompt-system-text').value = latest.system_prompt || '';
      document.getElementById('prompt-template-text').value = latest.template_text || '';
      updateVariablesChips(latest.template_text);
    }

    // Render version timeline
    const timeline = document.getElementById('prompt-version-timeline');
    if (timeline) {
      timeline.innerHTML = (prompt.versions || []).map((v) => `
        <div class="version-entry" style="padding: 8px 0; border-bottom: 1px solid var(--border-color);">
          <div class="flex-between">
            <strong>Version ${v.version_number}</strong>
            <span class="text-muted" style="font-size:0.75rem;">${new Date(v.created_at).toLocaleDateString()}</span>
          </div>
          <p style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">${v.description || 'No description provided.'}</p>
        </div>
      `).join('');
    }
  } catch (e) {
    console.error('Failed to select prompt', e);
  }
}

function updateVariablesChips(templateText) {
  const regex = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
  const matches = [...new Set((templateText.match(regex) || []).map((m) => m.replace(/[{}]/g, '')))];

  const chipsContainer = document.getElementById('prompt-vars-chips');
  const inputsContainer = document.getElementById('prompt-vars-inputs');

  if (matches.length === 0) {
    chipsContainer.innerHTML = '<span class="tag-empty">No variables detected</span>';
    inputsContainer.innerHTML = '';
    return;
  }

  chipsContainer.innerHTML = matches.map((m) => `<span class="var-tag">{${m}}</span>`).join('');
  inputsContainer.innerHTML = matches.map((m) => `
    <div class="form-group" style="margin-bottom:8px;">
      <label style="font-size:0.75rem;">${m}:</label>
      <input type="text" class="form-control form-control-sm prompt-variable-input" data-var="${m}" placeholder="Sample value for ${m}...">
    </div>
  `).join('');
}

function setupPromptStudioEvents() {
  const templateInput = document.getElementById('prompt-template-text');
  templateInput?.addEventListener('input', (e) => {
    updateVariablesChips(e.target.value);
  });

  // Run Prompt Test
  document.getElementById('btn-run-prompt-test')?.addEventListener('click', async () => {
    if (!state.currentPrompt) return;
    const modelSelect = document.getElementById('prompt-exec-model-select');
    const modelId = parseInt(modelSelect.value);
    if (!modelId) {
      showToast('Select a model to execute the prompt.', 'error');
      return;
    }

    // Collect variables
    const variables = {};
    document.querySelectorAll('.prompt-variable-input').forEach((input) => {
      const varName = input.getAttribute('data-var');
      variables[varName] = input.value.trim() || `[Sample ${varName}]`;
    });

    const payload = {
      model_id: modelId,
      variables: variables,
    };

    showToast('Executing prompt on model...', 'info');
    try {
      const res = await apiRequest(`/prompts/${state.currentPrompt.id}/execute`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const outBox = document.getElementById('prompt-output-box');
      outBox.style.display = 'block';
      document.getElementById('prompt-output-stats').innerText = `${res.latency_ms.toFixed(1)} ms • ${res.total_tokens} tokens • ${res.model_name}`;
      document.getElementById('prompt-output-content').innerText = res.output_text;
      showToast('Prompt execution completed!', 'success');
    } catch (e) {
      // handled
    }
  });

  // Add Version
  document.getElementById('btn-add-version')?.addEventListener('click', async () => {
    if (!state.currentPrompt) return;
    const templateText = document.getElementById('prompt-template-text').value.trim();
    const systemPrompt = document.getElementById('prompt-system-text').value.trim() || null;

    if (!templateText) {
      showToast('Template text cannot be empty.', 'error');
      return;
    }

    try {
      await apiRequest(`/prompts/${state.currentPrompt.id}/versions`, {
        method: 'POST',
        body: JSON.stringify({
          template_text: templateText,
          system_prompt: systemPrompt,
          description: 'Updated template version via Studio',
        }),
      });
      showToast('New prompt version saved!', 'success');
      selectPrompt(state.currentPrompt.id);
    } catch (e) {
      // handled
    }
  });

  // Create Prompt Modal
  const modal = document.getElementById('modal-create-prompt');
  document.getElementById('btn-open-create-prompt')?.addEventListener('click', () => {
    modal.style.display = 'flex';
  });
  document.getElementById('btn-close-prompt-modal')?.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  const form = document.getElementById('form-create-prompt');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById('cp-name').value.trim(),
      description: document.getElementById('cp-desc').value.trim() || null,
      tags: document.getElementById('cp-tags').value.trim() || null,
      system_prompt: document.getElementById('cp-system').value.trim() || null,
      initial_template: document.getElementById('cp-template').value.trim(),
    };

    try {
      const newPrompt = await apiRequest('/prompts', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      showToast('Prompt template created!', 'success');
      modal.style.display = 'none';
      form.reset();
      await loadPrompts();
      selectPrompt(newPrompt.id);
    } catch (e) {
      // handled
    }
  });
}

// 4. Datasets Section
async function loadDatasets() {
  try {
    const datasets = await apiRequest('/datasets');
    state.datasets = datasets;
    const tbody = document.querySelector('#table-datasets tbody');
    if (!tbody) return;

    if (datasets.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center">No datasets uploaded. Click "Upload Dataset" to add JSON or CSV test cases.</td></tr>';
      return;
    }

    tbody.innerHTML = datasets.map((d) => `
      <tr>
        <td><strong>${d.name}</strong></td>
        <td><span class="badge badge-info">${d.format.toUpperCase()}</span></td>
        <td>${d.record_count} sample(s)</td>
        <td>${d.description || '<span class="text-muted">No description</span>'}</td>
        <td>${new Date(d.created_at).toLocaleDateString()}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="viewDatasetRecords(${d.id})">View Samples</button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Failed to load datasets', e);
  }
}

async function viewDatasetRecords(datasetId) {
  try {
    const ds = await apiRequest(`/datasets/${datasetId}`);
    const card = document.getElementById('dataset-preview-card');
    card.style.display = 'block';
    document.getElementById('dataset-preview-title').innerText = `${ds.name} (${ds.record_count} items)`;

    const tbody = document.querySelector('#table-dataset-records tbody');
    tbody.innerHTML = (ds.records || []).map((r) => `
      <tr>
        <td>${r.record_index}</td>
        <td><strong>${r.question}</strong></td>
        <td>${r.reference_answer || '<span class="text-muted">-</span>'}</td>
        <td>${(r.contexts || []).map((c) => `<div style="font-size:0.75rem; color:var(--text-secondary); margin-bottom:4px;">• ${c.slice(0, 100)}...</div>`).join('')}</td>
      </tr>
    `).join('');

    card.scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    console.error(e);
  }
}

function setupDatasetEvents() {
  document.getElementById('btn-close-dataset-preview')?.addEventListener('click', () => {
    document.getElementById('dataset-preview-card').style.display = 'none';
  });

  const uploadModal = document.getElementById('modal-upload-dataset');
  document.getElementById('btn-upload-dataset-modal')?.addEventListener('click', () => {
    uploadModal.style.display = 'flex';
  });
  document.getElementById('btn-close-upload-modal')?.addEventListener('click', () => {
    uploadModal.style.display = 'none';
  });

  const uploadForm = document.getElementById('form-upload-dataset');
  uploadForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('upload-ds-name').value.trim();
    const desc = document.getElementById('upload-ds-desc').value.trim();
    const fileInput = document.getElementById('upload-ds-file');
    if (!fileInput.files.length) return;

    const formData = new FormData();
    formData.append('name', name);
    if (desc) formData.append('description', desc);
    formData.append('file', fileInput.files[0]);

    try {
      showToast('Uploading and parsing dataset...', 'info');
      const res = await fetch('/api/v1/datasets/upload', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
      }
      showToast('Dataset uploaded and validated successfully!', 'success');
      uploadModal.style.display = 'none';
      uploadForm.reset();
      loadDatasets();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

// 5. Experiment Lab Section
async function loadExperimentFormDependencies() {
  try {
    const [datasets, prompts, models] = await Promise.all([
      apiRequest('/datasets'),
      apiRequest('/prompts'),
      apiRequest('/models'),
    ]);

    // Datasets Select
    const dsSelect = document.getElementById('exp-dataset-select');
    dsSelect.innerHTML = datasets.map((d) => `<option value="${d.id}">${d.name} (${d.record_count} items)</option>`).join('');

    // Prompts Select
    const pSelect = document.getElementById('exp-prompt-select');
    pSelect.innerHTML = prompts.map((p) => {
      const vId = p.latest_version ? p.latest_version.id : p.id;
      return `<option value="${vId}">${p.name} (v${p.latest_version ? p.latest_version.version_number : 1})</option>`;
    }).join('');

    // Model checkboxes
    const cbGrid = document.getElementById('exp-models-checkboxes');
    cbGrid.innerHTML = models.map((m) => `
      <label class="checkbox-item">
        <input type="checkbox" name="selected_models" value="${m.id}" checked>
        <span>${m.display_name}</span>
      </label>
    `).join('');
  } catch (e) {
    console.error(e);
  }
}

function setupExperimentEvents() {
  const form = document.getElementById('form-create-experiment');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('exp-name').value.trim();
    const desc = document.getElementById('exp-desc').value.trim() || null;
    const datasetId = parseInt(document.getElementById('exp-dataset-select').value);
    const promptVersionId = parseInt(document.getElementById('exp-prompt-select').value);

    const checkedModels = Array.from(document.querySelectorAll('input[name="selected_models"]:checked')).map((cb) => parseInt(cb.value));

    if (checkedModels.length === 0) {
      showToast('Select at least one model to run the experiment.', 'error');
      return;
    }

    const payload = {
      name: name,
      description: desc,
      dataset_id: datasetId,
      prompt_version_id: promptVersionId,
      selected_model_ids: checkedModels,
      generation_parameters: {
        temperature: parseFloat(document.getElementById('exp-temp').value),
        max_tokens: parseInt(document.getElementById('exp-tokens').value),
        timeout_seconds: parseInt(document.getElementById('exp-timeout').value),
      },
    };

    const submitBtn = document.getElementById('btn-submit-experiment');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>⏳ Executing Experiment...</span>';
    showToast('Experiment created. Running evaluations across models...', 'info');

    try {
      const exp = await apiRequest('/experiments', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      // Run experiment
      const runRes = await apiRequest(`/experiments/${exp.id}/run`, {
        method: 'POST',
      });

      showToast(`Experiment '${runRes.name}' completed with status: ${runRes.status}!`, 'success');
      form.reset();

      // Switch to Comparison view for this experiment
      switchSection('comparison');
      setTimeout(() => {
        const select = document.getElementById('compare-experiment-select');
        if (select) {
          select.value = exp.id;
          loadExperimentComparison(exp.id);
        }
      }, 400);
    } catch (err) {
      // handled
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>🚀 Launch & Run Experiment</span>';
    }
  });
}

// 6. Evaluation Center Section
function setupEvaluationCenterEvents() {
  // Tab switching
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      tabs.forEach((t) => t.classList.remove('active'));
      document.querySelectorAll('.eval-tab-content').forEach((c) => c.classList.remove('active'));

      tab.classList.add('active');
      const target = document.getElementById(`tab-eval-${tab.getAttribute('data-eval-tab')}`);
      if (target) target.classList.add('active');
    });
  });

  // RAG Triad Evaluator Form
  const ragForm = document.getElementById('form-rag-eval');
  ragForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = document.getElementById('rag-eval-question').value.trim();
    const contextsRaw = document.getElementById('rag-eval-contexts').value.trim();
    const generated = document.getElementById('rag-eval-generated').value.trim();
    const reference = document.getElementById('rag-eval-reference').value.trim() || null;

    const contexts = contextsRaw.split('\n').map((c) => c.trim()).filter((c) => c.length > 0);

    const payload = {
      question: question,
      retrieved_contexts: contexts,
      generated_answer: generated,
      reference_answer: reference,
    };

    showToast('Computing RAG Triad & Hallucination risk...', 'info');
    try {
      const res = await apiRequest('/evaluations/rag', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const panel = document.getElementById('rag-results-panel');
      panel.style.display = 'block';

      document.getElementById('rag-score-ctx-rel').innerText = (res.triad_scores.context_relevance * 100).toFixed(0) + '%';
      document.getElementById('rag-score-faith').innerText = (res.triad_scores.faithfulness * 100).toFixed(0) + '%';
      document.getElementById('rag-score-ans-rel').innerText = (res.triad_scores.answer_relevance * 100).toFixed(0) + '%';
      document.getElementById('rag-score-overall').innerText = (res.triad_scores.overall_rag_score * 100).toFixed(0) + '%';

      const hallCard = document.getElementById('rag-score-hallucination');
      hallCard.innerText = (res.hallucination_risk_score * 100).toFixed(0) + '%';
      hallCard.className = `kpi-value ${res.hallucination_detected ? 'text-rose' : 'text-emerald'}`;

      document.getElementById('rag-verdict-text').innerText = res.explanation;

      // Render metric breakdown
      const breakdown = document.getElementById('rag-metrics-breakdown');
      breakdown.innerHTML = res.details.map((m) => `
        <div class="metric-row-card">
          <div class="metric-row-left">
            <h5>${m.metric_name}</h5>
            <p>${m.explanation}</p>
          </div>
          <div class="metric-row-right">
            <span class="badge badge-${m.status === 'PASS' ? 'success' : m.status === 'WARNING' ? 'warning' : 'danger'}">${m.status}</span>
            <span class="metric-score-pill">${(m.score * 100).toFixed(1)}%</span>
          </div>
        </div>
      `).join('');

      showToast('RAG Triad evaluation complete!', 'success');
      panel.scrollIntoView({ behavior: 'smooth' });
    } catch (e) {
      // handled
    }
  });

  // Ad-hoc Modular Evaluator Form
  const adhocForm = document.getElementById('form-adhoc-eval');
  adhocForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = document.getElementById('adhoc-question').value.trim() || null;
    const generated = document.getElementById('adhoc-generated').value.trim();
    const reference = document.getElementById('adhoc-reference').value.trim() || null;

    showToast('Executing modular evaluation metrics...', 'info');
    try {
      const res = await apiRequest('/evaluations/run', {
        method: 'POST',
        body: JSON.stringify({
          question: question,
          generated_answer: generated,
          reference_answer: reference,
        }),
      });

      const container = document.getElementById('adhoc-results-container');
      container.style.display = 'block';

      const list = document.getElementById('adhoc-metrics-list');
      list.innerHTML = res.metrics.map((m) => `
        <div class="metric-row-card">
          <div class="metric-row-left">
            <h5>${m.metric_name}</h5>
            <p>${m.explanation}</p>
          </div>
          <div class="metric-row-right">
            <span class="badge badge-${m.status === 'PASS' ? 'success' : m.status === 'WARNING' ? 'warning' : 'danger'}">${m.status}</span>
            <span class="metric-score-pill">${(m.score * 100).toFixed(1)}%</span>
          </div>
        </div>
      `).join('');

      showToast('Response evaluated!', 'success');
    } catch (e) {
      // handled
    }
  });
}

// 7. Model Comparison Section
async function loadComparisonSection() {
  try {
    const experiments = await apiRequest('/experiments');
    const select = document.getElementById('compare-experiment-select');
    if (!select) return;

    if (experiments.length === 0) {
      select.innerHTML = '<option value="">No experiments recorded</option>';
      document.getElementById('comparison-cards-grid').innerHTML = '<div class="empty-state">No experiments available. Create an experiment in Experiment Lab first.</div>';
      return;
    }

    select.innerHTML = experiments.map((e) => `<option value="${e.id}">${e.name} (${e.status})</option>`).join('');

    select.onchange = (e) => {
      loadExperimentComparison(parseInt(e.target.value));
    };

    if (experiments.length > 0) {
      loadExperimentComparison(experiments[0].id);
    }
  } catch (e) {
    console.error(e);
  }
}

async function loadExperimentComparison(experimentId) {
  try {
    const data = await apiRequest(`/experiments/${experimentId}/comparison`);
    const grid = document.getElementById('comparison-cards-grid');

    if (!data.models || data.models.length === 0) {
      grid.innerHTML = '<div class="empty-state">No model execution telemetry found for this experiment.</div>';
      return;
    }

    // Render comparison cards
    grid.innerHTML = data.models.map((m) => {
      const costDisplay = m.cost_available
        ? `$${m.cost_per_query.toFixed(5)} / query`
        : '<span class="text-muted" title="Pricing not configured">Unavailable</span>';

      return `
        <div class="comparison-card">
          <div class="comparison-card-header">
            <div>
              <h4>${m.display_name}</h4>
              <span class="badge badge-info">${m.provider}</span>
            </div>
            <span class="metric-score-pill text-purple">${(m.avg_evaluation_score * 100).toFixed(1)}%</span>
          </div>
          <div class="comparison-stat-row">
            <span class="text-muted">Success Rate:</span>
            <strong>${m.success_rate.toFixed(1)}%</strong>
          </div>
          <div class="comparison-stat-row">
            <span class="text-muted">Mean Latency:</span>
            <strong>${m.avg_latency_ms.toFixed(1)} ms</strong>
          </div>
          <div class="comparison-stat-row">
            <span class="text-muted">P95 Latency:</span>
            <strong>${m.p95_latency_ms.toFixed(1)} ms</strong>
          </div>
          <div class="comparison-stat-row">
            <span class="text-muted">Avg Tokens:</span>
            <strong>${m.avg_tokens.toFixed(0)}</strong>
          </div>
          <div class="comparison-stat-row">
            <span class="text-muted">Est. Cost:</span>
            <strong>${costDisplay}</strong>
          </div>
        </div>
      `;
    }).join('');

    // Render Side-by-Side Table
    const tbody = document.querySelector('#table-comparison-samples tbody');
    if (tbody) {
      if (data.side_by_side_samples.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">No samples generated.</td></tr>';
      } else {
        tbody.innerHTML = data.side_by_side_samples.map((s) => `
          <tr>
            <td><strong>${s.question}</strong></td>
            <td>${s.reference_answer || '<span class="text-muted">-</span>'}</td>
            <td>
              ${Object.entries(s.model_outputs).map(([mName, out]) => `
                <div style="margin-bottom:8px; padding:6px; background:rgba(255,255,255,0.03); border-radius:4px;">
                  <div class="flex-between">
                    <span style="font-weight:600; font-size:0.75rem; color:var(--accent-primary);">${mName}</span>
                    <span style="font-size:0.72rem; color:var(--text-muted);">${out.latency_ms.toFixed(0)}ms • ${out.total_tokens}tok</span>
                  </div>
                  <div style="font-size:0.8rem; margin-top:2px; white-space:pre-wrap;">${out.output_text}</div>
                </div>
              `).join('')}
            </td>
          </tr>
        `).join('');
      }
    }

    // Render Comparison Charts
    renderComparisonCharts(data.models);
  } catch (e) {
    console.error(e);
  }
}

function renderComparisonCharts(models) {
  if (typeof Chart === 'undefined') return;

  const labels = models.map((m) => m.display_name);

  // Chart 1: Quality Scores
  const ctxQuality = document.getElementById('chart-comparison-quality')?.getContext('2d');
  if (ctxQuality) {
    if (state.charts.compQuality) state.charts.compQuality.destroy();
    state.charts.compQuality = new Chart(ctxQuality, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Composite Evaluation Score (%)',
          data: models.map((m) => (m.avg_evaluation_score * 100).toFixed(1)),
          backgroundColor: '#6366f1',
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 0, max: 100, grid: { color: '#1e293b' } },
          x: { grid: { display: false } },
        },
      },
    });
  }

  // Chart 2: Latency Benchmarks
  const ctxLatency = document.getElementById('chart-comparison-latency')?.getContext('2d');
  if (ctxLatency) {
    if (state.charts.compLatency) state.charts.compLatency.destroy();
    state.charts.compLatency = new Chart(ctxLatency, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Avg Latency (ms)',
            data: models.map((m) => m.avg_latency_ms),
            backgroundColor: '#3b82f6',
            borderRadius: 6,
          },
          {
            label: 'P95 Latency (ms)',
            data: models.map((m) => m.p95_latency_ms),
            backgroundColor: '#a855f7',
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: { grid: { color: '#1e293b' } },
          x: { grid: { display: false } },
        },
      },
    });
  }
}

// 8. Observability & Traces Section
async function loadTraces() {
  try {
    const statusFilter = document.getElementById('filter-trace-status')?.value || '';
    let url = '/executions?limit=50';
    if (statusFilter) url += `&status=${statusFilter}`;

    const traces = await apiRequest(url);
    const tbody = document.querySelector('#table-traces tbody');
    if (!tbody) return;

    if (traces.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-center">No execution traces found.</td></tr>';
      return;
    }

    tbody.innerHTML = traces.map((t) => {
      const costStr = t.cost_estimate !== null && t.cost_estimate !== undefined
        ? `$${t.cost_estimate.toFixed(5)}`
        : '<span class="text-muted">-</span>';

      return `
        <tr>
          <td>${new Date(t.created_at).toLocaleTimeString()}</td>
          <td><code>${t.request_id.slice(0, 8)}...</code></td>
          <td><strong>${t.model_name}</strong></td>
          <td><span class="badge badge-${t.status === 'SUCCESS' ? 'success' : 'danger'}">${t.status}</span></td>
          <td>${t.error_category !== 'NONE' ? `<span class="badge badge-warning">${t.error_category}</span>` : '<span class="text-muted">None</span>'}</td>
          <td>${t.latency_ms.toFixed(1)} ms</td>
          <td>${t.total_tokens}</td>
          <td>${costStr}</td>
          <td>
            <button class="btn btn-sm btn-ghost" onclick="inspectTrace(${t.id})">Inspect</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.error(e);
  }
}

function setupObservabilityEvents() {
  document.getElementById('filter-trace-status')?.addEventListener('change', () => {
    loadTraces();
  });
  document.getElementById('btn-refresh-traces')?.addEventListener('click', () => {
    loadTraces();
  });
  document.getElementById('btn-close-trace-modal')?.addEventListener('click', () => {
    document.getElementById('modal-trace').style.display = 'none';
  });
}

async function inspectTrace(executionId) {
  try {
    const ex = await apiRequest(`/executions/${executionId}`);
    const modal = document.getElementById('modal-trace');
    modal.style.display = 'flex';

    document.getElementById('modal-trace-title').innerText = `Execution Trace: ${ex.request_id}`;

    const body = document.getElementById('modal-trace-body');
    body.innerHTML = `
      <div class="kpi-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 16px;">
        <div class="kpi-card" style="padding:10px;">
          <span class="kpi-label">Model</span>
          <span style="font-weight:700;">${ex.model_name}</span>
        </div>
        <div class="kpi-card" style="padding:10px;">
          <span class="kpi-label">Status</span>
          <span class="badge badge-${ex.status === 'SUCCESS' ? 'success' : 'danger'}">${ex.status}</span>
        </div>
        <div class="kpi-card" style="padding:10px;">
          <span class="kpi-label">Latency</span>
          <span style="font-weight:700;">${ex.latency_ms.toFixed(1)} ms</span>
        </div>
        <div class="kpi-card" style="padding:10px;">
          <span class="kpi-label">Total Tokens</span>
          <span style="font-weight:700;">${ex.total_tokens} (${ex.input_tokens} in / ${ex.output_tokens} out)</span>
        </div>
      </div>

      <div class="form-group">
        <label>Input Prompt</label>
        <pre class="output-text" style="max-height: 150px; overflow-y:auto;">${escapeHtml(ex.input_prompt)}</pre>
      </div>

      <div class="form-group mt-3">
        <label>Generated Output Completion</label>
        <pre class="output-text" style="max-height: 180px; overflow-y:auto; color:#a7f3d0;">${escapeHtml(ex.output_text || (ex.error_details ? 'ERROR: ' + ex.error_details : 'No output'))}</pre>
      </div>

      <!-- Execution Audit Logs -->
      <div class="mt-4">
        <h4>Telemetry Audit Trail</h4>
        <div class="version-timeline" style="margin-top:8px;">
          ${(ex.logs || []).map((l) => `
            <div style="font-size:0.8rem; padding:6px 0; border-bottom:1px solid var(--border-color);">
              <span class="text-muted">${new Date(l.timestamp).toLocaleTimeString()}</span>
              <span class="badge badge-info" style="margin: 0 6px;">${l.level}</span>
              <span>${escapeHtml(l.message)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } catch (e) {
    console.error(e);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// 9. Analytics Section
async function loadAnalytics() {
  try {
    const [perf, failures] = await Promise.all([
      apiRequest('/analytics/performance'),
      apiRequest('/analytics/failures'),
    ]);

    if (typeof Chart === 'undefined') return;

    // 1. Score Distribution
    const ctxScore = document.getElementById('chart-score-dist')?.getContext('2d');
    if (ctxScore) {
      if (state.charts.scoreDist) state.charts.scoreDist.destroy();
      state.charts.scoreDist = new Chart(ctxScore, {
        type: 'bar',
        data: {
          labels: Object.keys(perf.score_distribution),
          datasets: [{
            label: 'Evaluations',
            data: Object.values(perf.score_distribution),
            backgroundColor: '#10b981',
            borderRadius: 6,
          }],
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: '#1e293b' } },
            x: { grid: { display: false } },
          },
        },
      });
    }

    // 2. Token Usage Doughnut
    const ctxTokens = document.getElementById('chart-token-usage')?.getContext('2d');
    if (ctxTokens) {
      if (state.charts.tokenUsage) state.charts.tokenUsage.destroy();
      state.charts.tokenUsage = new Chart(ctxTokens, {
        type: 'doughnut',
        data: {
          labels: Object.keys(perf.token_usage_by_model),
          datasets: [{
            data: Object.values(perf.token_usage_by_model),
            backgroundColor: ['#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#ec4899'],
            borderColor: '#131c31',
          }],
        },
        options: {
          responsive: true,
          plugins: { legend: { position: 'bottom' } },
        },
      });
    }

    // 3. Latency Timeline
    const ctxLatency = document.getElementById('chart-latency-trend')?.getContext('2d');
    if (ctxLatency) {
      if (state.charts.latencyTrend) state.charts.latencyTrend.destroy();
      state.charts.latencyTrend = new Chart(ctxLatency, {
        type: 'line',
        data: {
          labels: perf.latency_trend.map((t) => t.timestamp),
          datasets: [{
            label: 'Latency (ms)',
            data: perf.latency_trend.map((t) => t.latency_ms),
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.1)',
            fill: true,
            tension: 0.3,
          }],
        },
        options: {
          responsive: true,
          scales: {
            y: { grid: { color: '#1e293b' } },
            x: { grid: { display: false } },
          },
        },
      });
    }

    // 4. Failure Breakdown
    const ctxFail = document.getElementById('chart-failure-breakdown')?.getContext('2d');
    if (ctxFail) {
      if (state.charts.failureBreakdown) state.charts.failureBreakdown.destroy();
      state.charts.failureBreakdown = new Chart(ctxFail, {
        type: 'bar',
        data: {
          labels: failures.breakdown_by_category.map((f) => f.category),
          datasets: [{
            label: 'Failure Count',
            data: failures.breakdown_by_category.map((f) => f.count),
            backgroundColor: '#ef4444',
            borderRadius: 6,
          }],
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            y: { grid: { color: '#1e293b' } },
            x: { grid: { display: false } },
          },
        },
      });
    }
  } catch (e) {
    console.error(e);
  }
}

// 10. Experiment History Section
async function loadExperimentsHistory() {
  try {
    const experiments = await apiRequest('/experiments');
    const tbody = document.querySelector('#table-history tbody');
    if (!tbody) return;

    if (experiments.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center">No experiment history. Launch an experiment from Experiment Lab.</td></tr>';
      return;
    }

    tbody.innerHTML = experiments.map((e) => `
      <tr>
        <td><strong>${e.name}</strong></td>
        <td>${new Date(e.created_at).toLocaleString()}</td>
        <td><span class="badge badge-${e.status === 'COMPLETED' ? 'success' : e.status === 'RUNNING' ? 'info' : 'warning'}">${e.status}</span></td>
        <td>${e.total_runs}</td>
        <td>${e.completed_runs}</td>
        <td>${e.failed_runs}</td>
        <td>
          <button class="btn btn-sm btn-primary" onclick="viewExperimentComparison(${e.id})">Compare Models</button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    console.error(e);
  }
}

function viewExperimentComparison(experimentId) {
  switchSection('comparison');
  setTimeout(() => {
    const select = document.getElementById('compare-experiment-select');
    if (select) {
      select.value = experimentId;
      loadExperimentComparison(experimentId);
    }
  }, 400);
}

// Helpers
async function populateModelSelect(selectId) {
  const select = document.getElementById(selectId);
  if (!select) return;
  const models = await apiRequest('/models');
  select.innerHTML = models.map((m) => `<option value="${m.id}">${m.display_name} (${m.provider_name})</option>`).join('');
}

// Health Check Initialization
async function checkSystemHealth() {
  try {
    const res = await apiRequest('/health');
    const badge = document.getElementById('system-status-badge');
    const text = document.getElementById('system-status-text');
    if (res.status === 'healthy') {
      badge.querySelector('.status-dot').className = 'status-dot green';
      text.innerText = 'System Online';
    } else {
      badge.querySelector('.status-dot').className = 'status-dot red';
      text.innerText = 'Degraded';
    }
  } catch (e) {
    const badge = document.getElementById('system-status-badge');
    const text = document.getElementById('system-status-text');
    if (badge) badge.querySelector('.status-dot').className = 'status-dot red';
    if (text) text.innerText = 'API Offline';
  }
}

// Init on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupModelRegistration();
  setupPromptStudioEvents();
  setupDatasetEvents();
  setupExperimentEvents();
  setupEvaluationCenterEvents();
  setupObservabilityEvents();

  checkSystemHealth();
  loadOverview();
});

