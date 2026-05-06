const state = {
  running: false,
};

const elements = {
  query: document.getElementById("query-input"),
  runLive: document.getElementById("run-live"),
  loadLast: document.getElementById("load-last"),
  status: document.getElementById("connection-status"),
  baselineAnswer: document.getElementById("baseline-answer"),
  multiAnswer: document.getElementById("multi-answer"),
  baselineRoute: document.getElementById("baseline-route"),
  multiRoute: document.getElementById("multi-route"),
  baselineFlow: document.getElementById("baseline-flow"),
  multiFlow: document.getElementById("multi-flow"),
  toolGrid: document.getElementById("tool-grid"),
  sourcesList: document.getElementById("sources-list"),
  artifactLinks: document.getElementById("artifact-links"),
  reportPreview: document.getElementById("report-preview"),
  baselineLatency: document.getElementById("metric-baseline-latency"),
  multiLatency: document.getElementById("metric-multi-latency"),
  citation: document.getElementById("metric-citation"),
  sources: document.getElementById("metric-sources"),
};

elements.runLive.addEventListener("click", () => runComparison());
elements.loadLast.addEventListener("click", () => loadLastRun());

async function runComparison() {
  if (state.running) return;
  setRunning(true);
  setProgress(["baseline"]);
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: elements.query.value }),
    });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(payload.error || "Run failed");
    setProgress(["baseline", "researcher", "analyst", "writer", "report"]);
    renderPayload(payload);
    setStatus("Run complete");
  } catch (error) {
    setStatus("Error");
    elements.reportPreview.textContent = String(error.message || error);
    elements.reportPreview.classList.add("error");
  } finally {
    setRunning(false);
  }
}

async function loadLastRun() {
  setStatus("Loading last run");
  try {
    const response = await fetch("/api/last");
    const payload = await readJson(response);
    if (!response.ok) throw new Error(payload.error || "No last run");
    renderPayload(payload);
    setProgress(["baseline", "researcher", "analyst", "writer", "report"]);
    setStatus("Last run loaded");
  } catch (error) {
    setStatus("No last run");
    elements.reportPreview.textContent = String(error.message || error);
    elements.reportPreview.classList.add("error");
  }
}

async function readJson(response) {
  const text = await response.text();
  return text ? JSON.parse(text) : {};
}

function renderPayload(payload) {
  const baseline = payload.runs.baseline;
  const multi = payload.runs.multi_agent;
  elements.query.value = payload.query;
  elements.baselineAnswer.textContent = baseline.answer || "No baseline answer returned.";
  elements.multiAnswer.textContent = multi.answer || "No multi-agent answer returned.";
  elements.baselineRoute.textContent = "direct";
  elements.multiRoute.textContent = multi.route_history.join(" -> ") || "no route";
  elements.baselineLatency.textContent = formatSeconds(baseline.metrics.latency_seconds);
  elements.multiLatency.textContent = formatSeconds(multi.metrics.latency_seconds);
  elements.citation.textContent = formatPercent(multi.metrics.citation_coverage);
  elements.sources.textContent = String(multi.metrics.source_count);
  renderFlow(elements.baselineFlow, baseline.flow);
  renderFlow(elements.multiFlow, multi.flow);
  renderTools([...baseline.tools, ...multi.tools]);
  renderSources(multi.sources);
  renderArtifacts(payload);
  elements.reportPreview.classList.remove("error");
  elements.reportPreview.textContent = payload.report_markdown || "No report returned.";
}

function renderFlow(container, flow) {
  container.replaceChildren();
  flow.nodes.forEach((node, index) => {
    if (index > 0) {
      const edge = flow.edges[index - 1];
      const edgeEl = document.createElement("div");
      edgeEl.className = "flow-edge";
      edgeEl.textContent = `downstream: ${edge.label}`;
      container.appendChild(edgeEl);
    }
    const nodeEl = document.createElement("div");
    nodeEl.className = `flow-node ${node.kind}`;
    nodeEl.textContent = node.label;
    container.appendChild(nodeEl);
  });
}

function renderTools(tools) {
  elements.toolGrid.replaceChildren();
  tools.forEach((tool) => {
    const card = document.createElement("div");
    card.className = "tool-card";
    card.innerHTML = `
      <strong>${escapeHtml(tool.owner)}: ${escapeHtml(tool.name)}</strong>
      <span>${escapeHtml(tool.purpose)}</span>
      <div class="metadata">${escapeHtml(JSON.stringify(tool.metadata, null, 2))}</div>
    `;
    elements.toolGrid.appendChild(card);
  });
}

function renderSources(sources) {
  elements.sourcesList.replaceChildren();
  if (!sources.length) {
    elements.sourcesList.textContent = "No sources collected.";
    return;
  }
  sources.forEach((source, index) => {
    const card = document.createElement("div");
    card.className = "source-card";
    const link = source.url
      ? `<a href="${escapeAttribute(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.url)}</a>`
      : "No URL";
    card.innerHTML = `
      <strong>[${index + 1}] ${escapeHtml(source.title)}</strong>
      <div>${link}</div>
      <p>${escapeHtml(source.snippet || "")}</p>
      <div class="metadata">${escapeHtml(JSON.stringify(source.metadata || {}, null, 2))}</div>
    `;
    elements.sourcesList.appendChild(card);
  });
}

function renderArtifacts(payload) {
  elements.artifactLinks.replaceChildren();
  const local = document.createElement("div");
  local.className = "metadata";
  local.textContent = JSON.stringify(payload.artifacts, null, 2);
  elements.artifactLinks.appendChild(local);
  payload.hosted_exports.forEach((item) => {
    const row = document.createElement("div");
    row.className = "tool-card";
    const url = item.url
      ? `<a href="${escapeAttribute(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a>`
      : "No hosted URL";
    row.innerHTML = `
      <strong>${escapeHtml(item.run_name)} - ${escapeHtml(item.provider)} - ${escapeHtml(item.status)}</strong>
      <div>${url}</div>
      <div class="metadata">${escapeHtml(item.message || "")}</div>
    `;
    elements.artifactLinks.appendChild(row);
  });
}

function setRunning(running) {
  state.running = running;
  elements.runLive.disabled = running;
  elements.loadLast.disabled = running;
  setStatus(running ? "Running" : "Ready");
}

function setStatus(label) {
  elements.status.textContent = label;
}

function setProgress(doneSteps) {
  document.querySelectorAll(".step").forEach((step) => {
    const active = doneSteps.includes(step.dataset.step);
    step.classList.toggle("done", active);
  });
}

function formatSeconds(value) {
  if (typeof value !== "number") return "-";
  return `${value.toFixed(2)}s`;
}

function formatPercent(value) {
  if (typeof value !== "number") return "-";
  return `${Math.round(value * 100)}%`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

loadLastRun();

