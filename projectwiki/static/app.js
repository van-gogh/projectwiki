const supportedLanguages = ["zh-CN", "en-US"];
let currentProjectId = storageGet("projectwiki.currentProjectId");
let languageBounceTimer = null;

function dictionary() {
  const dictionaries = window.ProjectWikiI18n || {};
  const lang = normalizeLanguage(document.documentElement.lang);
  return dictionaries[lang] || dictionaries["en-US"] || {};
}

function t(key) {
  return dictionary()[key] || key;
}

function storageGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function storageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    return;
  }
}

function normalizeLanguage(lang) {
  return supportedLanguages.includes(lang) ? lang : "en-US";
}

function initialLanguage() {
  const saved = storageGet("projectwiki.language");
  if (supportedLanguages.includes(saved)) return saved;
  return typeof navigator !== "undefined" && navigator.language && navigator.language.startsWith("zh") ? "zh-CN" : "en-US";
}

function updateLanguageSwitch(lang) {
  const switcher = document.querySelector(".language-switch");
  if (!switcher) return;
  switcher.dataset.activeLang = lang;
  switcher.querySelectorAll("[data-lang]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
  });
  switcher.classList.remove("is-bouncing");
  window.requestAnimationFrame(() => {
    switcher.classList.add("is-bouncing");
    clearTimeout(languageBounceTimer);
    languageBounceTimer = setTimeout(() => switcher.classList.remove("is-bouncing"), 360);
  });
}

function translate(lang) {
  const normalizedLang = normalizeLanguage(lang);
  const dictionaries = window.ProjectWikiI18n || {};
  const dict = dictionaries[normalizedLang] || dictionaries["en-US"] || {};
  document.documentElement.lang = normalizedLang;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = dict[node.dataset.i18n] || node.dataset.i18n;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = dict[node.dataset.i18nPlaceholder] || node.dataset.i18nPlaceholder;
  });
  updateLanguageSwitch(normalizedLang);
  storageSet("projectwiki.language", normalizedLang);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = response.statusText;
    }
    throw new Error(detail);
  }
  return response.json();
}

async function apiText(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = response.statusText;
    }
    throw new Error(detail);
  }
  return response.text();
}

function setCurrentProjectId(projectId) {
  currentProjectId = projectId;
  storageSet("projectwiki.currentProjectId", projectId);
}

function appendField(list, label, value) {
  const row = document.createElement("div");
  const labelNode = document.createElement("strong");
  const valueNode = document.createElement("span");
  labelNode.textContent = `${label}: `;
  valueNode.textContent = String(value);
  row.append(labelNode, valueNode);
  list.append(row);
}

function appContainer() {
  return document.querySelector("#app");
}

function setActiveView(view) {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
}

function fieldValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function appendPre(parent, value) {
  const pre = document.createElement("pre");
  pre.textContent = fieldValue(value);
  parent.append(pre);
}

function parseJsonList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    return [value];
  }
}

function createPanel(titleText) {
  const panel = document.createElement("div");
  panel.className = "panel output-panel";
  const title = document.createElement("h2");
  title.textContent = titleText;
  panel.append(title);
  return panel;
}

function createFormPanel(titleText) {
  const panel = createPanel(titleText);
  panel.classList.add("form-panel");
  return panel;
}

function appendLabeledControl(form, labelText, control) {
  const label = document.createElement("label");
  const text = document.createElement("span");
  text.textContent = labelText;
  label.append(text, control);
  form.append(label);
  return control;
}

function renderProjectReady(project, titleKey = "project.create.ready") {
  const panel = createPanel(t(titleKey));
  appendField(panel, t("field.projectId"), project.id);
  appendField(panel, t("project.create.name"), project.name);
  appendField(panel, t("project.create.description"), project.description || "-");
  appendActionButtons(panel);
  return panel;
}

function renderEmpty(panel) {
  const empty = document.createElement("p");
  empty.className = "muted";
  empty.textContent = t("view.empty");
  panel.append(empty);
  return panel;
}

function renderRecordGrid(rows, fields) {
  const grid = document.createElement("div");
  grid.className = "record-grid";
  rows.forEach((row) => {
    const card = document.createElement("article");
    card.className = "record-card";
    fields.forEach(([key, labelKey]) => {
      if (!(key in row)) return;
      const field = document.createElement("div");
      field.className = "record-field";
      const label = document.createElement("strong");
      label.textContent = `${t(labelKey)}:`;
      const value = document.createElement("span");
      value.textContent = fieldValue(row[key]);
      field.append(label, value);
      card.append(field);
    });
    if ("evidence_json" in row) {
      const evidence = document.createElement("div");
      evidence.className = "record-field stacked";
      const label = document.createElement("strong");
      label.textContent = `${t("field.evidence")}:`;
      evidence.append(label);
      appendPre(evidence, parseJsonList(row.evidence_json));
      card.append(evidence);
    }
    grid.append(card);
  });
  return grid;
}

function renderRecordCards(titleText, rows, fields) {
  const panel = createPanel(titleText);
  if (!rows.length) return renderEmpty(panel);
  panel.append(renderRecordGrid(rows, fields));
  return panel;
}

function renderTextPanel(titleText, text) {
  const panel = createPanel(titleText);
  appendPre(panel, text);
  return panel;
}

function requireProject() {
  if (currentProjectId) return currentProjectId;
  return null;
}

function appendActionButtons(parent) {
  const actionsTitle = document.createElement("h3");
  actionsTitle.textContent = t("demo.nextActions");
  const actions = document.createElement("div");
  actions.className = "actions next-actions";
  ["status", "review", "wiki", "ask", "sources"].forEach((view) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.nextView = view;
    button.textContent = view === "wiki" ? t("nav.wikiIndex") : t(`nav.${view}`);
    button.addEventListener("click", () => loadView(view));
    actions.append(button);
  });
  parent.append(actionsTitle, actions);
}

function appendChip(parent, label, kind = "") {
  const chip = document.createElement("span");
  chip.className = `status-chip ${kind}`.trim();
  chip.textContent = label;
  parent.append(chip);
  return chip;
}

function createMetric(label, value) {
  const card = document.createElement("div");
  card.className = "metric-card";
  const number = document.createElement("strong");
  number.textContent = String(value);
  const text = document.createElement("span");
  text.textContent = label;
  card.append(number, text);
  return card;
}

function createWorkflow() {
  const labels = [
    "workflow.project",
    "workflow.ingest",
    "workflow.build",
    "workflow.review",
    "workflow.use",
  ];
  const workflow = document.createElement("div");
  workflow.className = "workflow";
  labels.forEach((key, index) => {
    const step = document.createElement("div");
    step.className = "workflow-step";
    const number = document.createElement("strong");
    number.textContent = `${index + 1}`;
    const label = document.createElement("span");
    label.textContent = t(key);
    step.append(number, label);
    workflow.append(step);
  });
  return workflow;
}

function renderStart() {
  const panel = createPanel(t("start.title"));
  panel.classList.add("hero-panel");
  const intro = document.createElement("p");
  intro.textContent = t("start.subtitle");
  const actions = document.createElement("div");
  actions.className = "actions";
  const ownProject = document.createElement("button");
  ownProject.type = "button";
  ownProject.className = "primary";
  ownProject.textContent = t("start.primary");
  ownProject.addEventListener("click", showCreateProjectForm);
  const demo = document.createElement("button");
  demo.type = "button";
  demo.textContent = t("start.demo");
  demo.addEventListener("click", useDemoProject);
  actions.append(ownProject, demo);
  panel.append(intro, createWorkflow(), actions);
  if (currentProjectId) {
    const continueButton = document.createElement("button");
    continueButton.type = "button";
    continueButton.textContent = t("nav.status");
    continueButton.addEventListener("click", () => loadView("status"));
    actions.append(continueButton);
  }
  return panel;
}

function renderDemoResult(payload) {
  const container = document.createElement("div");
  container.className = "panel";

  const title = document.createElement("h2");
  title.textContent = t("demo.ready");

  const fields = document.createElement("div");
  appendField(fields, t("demo.projectId"), payload.project.id);
  appendField(fields, t("demo.blocksCreated"), payload.ingest.created_blocks);
  appendField(fields, t("demo.factsCreated"), payload.build.facts_created);

  const nextSteps = document.createElement("p");
  nextSteps.textContent = t("demo.nextSteps");

  container.append(title, fields, nextSteps);
  appendActionButtons(container);
  return container;
}

function showCreateProjectForm() {
  const appNode = appContainer();
  if (!appNode) return;
  setActiveView("");

  const panel = createFormPanel(t("project.create.title"));
  const form = document.createElement("form");
  form.className = "inline-form";
  const nameInput = document.createElement("input");
  nameInput.name = "name";
  nameInput.required = true;
  nameInput.placeholder = t("project.create.namePlaceholder");
  const descriptionInput = document.createElement("textarea");
  descriptionInput.name = "description";
  descriptionInput.placeholder = t("project.create.descriptionPlaceholder");
  const status = document.createElement("p");
  status.className = "status-line";
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "primary";
  submit.textContent = t("project.create.submit");

  appendLabeledControl(form, t("project.create.name"), nameInput);
  appendLabeledControl(form, t("project.create.description"), descriptionInput);
  form.append(submit, status);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = t("view.loading");
    try {
      const project = await api("/api/projects", {
        method: "POST",
        body: JSON.stringify({
          name: nameInput.value.trim(),
          description: descriptionInput.value.trim(),
        }),
      });
      setCurrentProjectId(project.id);
      appNode.replaceChildren(renderProjectReady(project));
    } catch (error) {
      status.textContent = `${t("view.error")}: ${error.message}`;
    }
  });

  panel.append(form);
  appNode.replaceChildren(panel);
  nameInput.focus();
}

function renderNoProjectAction() {
  const panel = createPanel(t("dashboard.title"));
  const message = document.createElement("p");
  message.textContent = t("view.noProject");
  const createButton = document.createElement("button");
  createButton.type = "button";
  createButton.className = "primary";
  createButton.textContent = t("action.createProject");
  createButton.addEventListener("click", showCreateProjectForm);
  panel.append(message, createButton);
  return panel;
}

function showIngestForm() {
  const appNode = appContainer();
  if (!appNode) return;
  setActiveView("");
  const projectId = requireProject();
  if (!projectId) {
    appNode.replaceChildren(renderNoProjectAction());
    return;
  }

  const panel = createFormPanel(t("ingest.title"));
  const form = document.createElement("form");
  form.className = "inline-form";
  const pathInput = document.createElement("input");
  pathInput.name = "path";
  pathInput.required = true;
  pathInput.placeholder = t("ingest.pathPlaceholder");
  const sourceType = document.createElement("select");
  ["local", "git"].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    sourceType.append(option);
  });
  const status = document.createElement("p");
  status.className = "status-line";
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "primary";
  submit.textContent = t("ingest.submit");

  appendLabeledControl(form, t("ingest.path"), pathInput);
  appendLabeledControl(form, t("ingest.sourceType"), sourceType);
  form.append(submit, status);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = t("view.loading");
    try {
      const result = await api(`/api/projects/${projectId}/ingest`, {
        method: "POST",
        body: JSON.stringify({
          path: pathInput.value.trim(),
          source_type: sourceType.value,
        }),
      });
      const resultPanel = createPanel(t("ingest.ready"));
      appendField(resultPanel, t("field.projectId"), result.project_id);
      appendField(resultPanel, t("field.filesSeen"), result.files_seen);
      appendField(resultPanel, t("field.sourcesCreated"), result.created_sources);
      appendField(resultPanel, t("demo.blocksCreated"), result.created_blocks);
      appendField(resultPanel, t("field.skippedFiles"), result.skipped_files);
      if (result.errors && result.errors.length) {
        appendField(resultPanel, t("view.error"), result.errors.length);
        appendPre(resultPanel, result.errors);
      }
      appendActionButtons(resultPanel);
      appNode.replaceChildren(resultPanel);
    } catch (error) {
      status.textContent = `${t("view.error")}: ${error.message}`;
    }
  });

  panel.append(form);
  appNode.replaceChildren(panel);
  pathInput.focus();
}

async function buildCurrentProject() {
  const appNode = appContainer();
  if (!appNode) return;
  setActiveView("");
  const projectId = requireProject();
  if (!projectId) {
    appNode.replaceChildren(renderNoProjectAction());
    return;
  }

  appNode.textContent = t("build.loading");
  try {
    const result = await api(`/api/projects/${projectId}/build`, { method: "POST" });
    const panel = createPanel(t("build.ready"));
    appendField(panel, t("field.projectId"), result.project_id);
    appendField(panel, t("build.factsCreated"), result.facts_created);
    appendField(panel, t("build.conflictsCreated"), result.conflicts_created);
    appendField(panel, t("build.pagesCreated"), result.wiki_pages.length);
    appendActionButtons(panel);
    appNode.replaceChildren(panel);
  } catch (error) {
    appNode.textContent = `${t("view.error")}: ${error.message}`;
  }
}

async function useDemoProject() {
  const appNode = document.querySelector("#app");
  if (!appNode) return;

  appNode.textContent = t("demo.loading");
  try {
    const payload = await api("/api/demo", { method: "POST" });
    setCurrentProjectId(payload.project.id);
    appNode.replaceChildren(renderDemoResult(payload));
  } catch (error) {
    appNode.textContent = `${t("demo.error")}: ${error.message}. ${t("error.readLogs")}`;
  }
}

async function renderProjects() {
  const projects = await api("/api/projects");
  return renderRecordCards(t("view.projects.title"), projects, [
    ["id", "field.id"],
    ["name", "field.title"],
    ["description", "field.statement"],
    ["created_at", "field.updatedAt"],
  ]);
}

async function renderSources(projectId) {
  const sources = await api(`/api/projects/${projectId}/sources`);
  return renderRecordCards(t("view.sources.title"), sources, [
    ["path", "field.path"],
    ["title", "field.title"],
    ["source_type", "field.type"],
    ["updated_at", "field.updatedAt"],
  ]);
}

async function renderFacts(projectId) {
  const facts = await api(`/api/projects/${projectId}/facts`);
  return renderRecordCards(t("view.facts.title"), facts, [
    ["fact_type", "field.type"],
    ["statement", "field.statement"],
    ["confidence", "field.confidence"],
    ["status", "field.status"],
  ]);
}

function factStatusKind(fact) {
  if (fact.validity_status === "conflicting" || fact.status === "needs_review") return "review";
  if (fact.validity_status === "current" || fact.status === "confirmed") return "evidence";
  return "";
}

function factStatusLabel(fact) {
  if (fact.validity_status === "conflicting" || fact.status === "needs_review") return t("status.needsReview");
  if (fact.validity_status === "current" || fact.status === "confirmed") return t("status.evidence");
  return t("status.stable");
}

function renderStateCards(rows, limit = 8) {
  const grid = document.createElement("div");
  grid.className = "state-grid";
  rows.slice(0, limit).forEach((row) => {
    const card = document.createElement("article");
    card.className = "state-card";
    const header = document.createElement("header");
    const title = document.createElement("strong");
    title.textContent = row.fact_type || row.title || row.path || row.id;
    header.append(title);
    appendChip(header, factStatusLabel(row), factStatusKind(row));
    const statement = document.createElement("p");
    statement.textContent = row.statement || row.description || row.path || "-";
    card.append(header, statement);
    if (row.evidence_json) {
      appendChip(card, t("status.evidence"), "evidence");
    }
    grid.append(card);
  });
  return grid;
}

function renderRecentSources(sources) {
  const sorted = [...sources].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
  const grid = document.createElement("div");
  grid.className = "state-grid";
  sorted.slice(0, 6).forEach((source) => {
    const card = document.createElement("article");
    card.className = "state-card";
    const header = document.createElement("header");
    const title = document.createElement("strong");
    title.textContent = source.title || source.path;
    header.append(title);
    appendChip(header, t("status.changed"), "changed");
    const path = document.createElement("p");
    path.textContent = source.path;
    card.append(header, path);
    grid.append(card);
  });
  return grid;
}

function appendSection(parent, titleText, child) {
  const section = document.createElement("section");
  section.className = "state-section";
  const title = document.createElement("h3");
  title.textContent = titleText;
  section.append(title, child);
  parent.append(section);
  return section;
}

function visibleWikiPages(pages) {
  return pages.filter((page) => page.slug !== "handover");
}

async function renderStatus(projectId) {
  const [sources, facts, conflicts, pages] = await Promise.all([
    api(`/api/projects/${projectId}/sources`),
    api(`/api/projects/${projectId}/facts`),
    api(`/api/projects/${projectId}/conflicts`),
    api(`/api/projects/${projectId}/wiki`),
  ]);
  const panel = createPanel(t("status.title"));
  const intro = document.createElement("p");
  intro.className = "status-intro";
  intro.textContent = t("status.subtitle");
  const metrics = document.createElement("div");
  metrics.className = "metric-grid";
  metrics.append(
    createMetric(t("status.metric.sources"), sources.length),
    createMetric(t("status.metric.facts"), facts.length),
    createMetric(t("status.metric.conflicts"), conflicts.length),
    createMetric(t("status.metric.wiki"), visibleWikiPages(pages).length)
  );
  panel.append(intro, metrics);

  if (facts.length) {
    appendSection(panel, t("status.current"), renderStateCards(facts, 8));
  } else {
    appendSection(panel, t("status.current"), renderEmpty(document.createElement("div")));
  }
  if (sources.length) {
    appendSection(panel, t("status.recent"), renderRecentSources(sources));
  }
  if (conflicts.length) {
    const reviewGrid = document.createElement("div");
    reviewGrid.className = "state-grid";
    conflicts.slice(0, 4).forEach((conflict) => {
      const card = document.createElement("article");
      card.className = "state-card";
      const header = document.createElement("header");
      const title = document.createElement("strong");
      title.textContent = conflict.title;
      header.append(title);
      appendChip(header, t("status.needsReview"), "review");
      const description = document.createElement("p");
      description.textContent = conflict.description;
      card.append(header, description);
      reviewGrid.append(card);
    });
    appendSection(panel, t("status.review"), reviewGrid);
  }
  return panel;
}

async function renderConflicts(projectId) {
  const conflicts = await api(`/api/projects/${projectId}/conflicts`);
  return renderRecordCards(t("view.conflicts.title"), conflicts, [
    ["title", "field.title"],
    ["conflict_type", "field.type"],
    ["severity", "field.severity"],
    ["status", "field.status"],
    ["description", "field.statement"],
  ]);
}

async function renderReview(projectId) {
  const [conflicts, facts] = await Promise.all([
    api(`/api/projects/${projectId}/conflicts`),
    api(`/api/projects/${projectId}/facts`),
  ]);
  const panel = createPanel(t("review.title"));
  const intro = document.createElement("p");
  intro.className = "status-intro";
  intro.textContent = t("review.subtitle");
  panel.append(intro);

  if (conflicts.length) {
    appendSection(
      panel,
      t("view.conflicts.title"),
      renderRecordGrid(conflicts, [
        ["title", "field.title"],
        ["conflict_type", "field.type"],
        ["severity", "field.severity"],
        ["status", "field.status"],
        ["description", "field.statement"],
      ])
    );
  }

  const reviewFacts = facts.filter((fact) => fact.status === "needs_review" || fact.validity_status === "conflicting");
  appendSection(
    panel,
    t("view.facts.title"),
    reviewFacts.length ? renderStateCards(reviewFacts, 8) : renderEmpty(document.createElement("div"))
  );
  return panel;
}

async function renderWiki(projectId) {
  const pages = visibleWikiPages(await api(`/api/projects/${projectId}/wiki`));
  const panel = renderRecordCards(t("view.wiki.title"), pages, [
    ["slug", "field.id"],
    ["title", "field.title"],
    ["updated_at", "field.updatedAt"],
  ]);
  if (!pages.length) return panel;

  const first = pages[0];
  const slug = encodeURIComponent(first.slug);
  const content = await apiText(`/api/projects/${projectId}/wiki/${slug}`);
  const page = document.createElement("section");
  page.className = "wiki-page";
  const heading = document.createElement("h3");
  heading.textContent = first.title || first.slug;
  page.append(heading);
  appendPre(page, content);
  panel.append(page);
  return panel;
}

async function renderHandover(projectId) {
  const handover = await apiText(`/api/projects/${projectId}/handover`);
  return renderTextPanel(t("view.handover.title"), handover);
}

async function renderAsk(projectId) {
  const panel = createPanel(t("view.ask.title"));
  const form = document.createElement("form");
  form.className = "ask-form";
  const input = document.createElement("input");
  input.name = "question";
  input.value = t("ask.defaultQuestion");
  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = t("ask.submit");
  const output = document.createElement("div");
  output.className = "ask-output";

  async function ask(question) {
    output.textContent = t("view.loading");
    const result = await api(`/api/projects/${projectId}/ask`, {
      method: "POST",
      body: JSON.stringify({ question }),
    });
    const answer = document.createElement("div");
    appendField(answer, t("field.question"), result.question);
    appendField(answer, t("field.answer"), result.answer);
    output.replaceChildren(answer);
    if (result.evidence && result.evidence.length) {
      const evidenceTitle = document.createElement("h3");
      evidenceTitle.textContent = t("field.evidence");
      output.append(evidenceTitle);
      output.append(
        renderRecordGrid(result.evidence, [
          ["kind", "field.type"],
          ["path", "field.path"],
          ["score", "field.confidence"],
        ])
      );
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    ask(input.value || t("ask.defaultQuestion")).catch((error) => {
      output.textContent = `${t("view.error")}: ${error.message}`;
    });
  });

  form.append(input, button);
  panel.append(form, output);
  ask(input.value).catch((error) => {
    output.textContent = `${t("view.error")}: ${error.message}`;
  });
  return panel;
}

async function renderSettings() {
  const panel = createPanel(t("view.settings.title"));
  const projectId = requireProject();
  const exportButton = document.createElement("button");
  exportButton.type = "button";
  exportButton.textContent = t("settings.export");
  const output = document.createElement("div");
  output.className = "wiki-page";
  exportButton.addEventListener("click", async () => {
    if (!projectId) {
      output.textContent = t("view.noProject");
      return;
    }
    output.textContent = t("view.loading");
    try {
      const handover = await apiText(`/api/projects/${projectId}/handover`);
      const title = document.createElement("h3");
      title.textContent = t("settings.handover");
      const content = document.createElement("div");
      appendPre(content, handover);
      output.replaceChildren(title, content);
    } catch (error) {
      output.textContent = `${t("view.error")}: ${error.message}`;
    }
  });
  panel.append(exportButton, output);
  return panel;
}

async function loadView(view) {
  const appNode = appContainer();
  if (!appNode) return;
  setActiveView(view);
  appNode.textContent = t("view.loading");

  try {
    if (view === "start") {
      appNode.replaceChildren(renderStart());
      return;
    }

    if (view === "projects") {
      appNode.replaceChildren(await renderProjects());
      return;
    }

    const projectId = requireProject();
    if (!projectId) {
      appNode.replaceChildren(renderNoProjectAction());
      return;
    }

    const renderers = {
      status: renderStatus,
      sources: renderSources,
      facts: renderFacts,
      wiki: renderWiki,
      conflicts: renderConflicts,
      review: renderReview,
      handover: renderHandover,
      ask: renderAsk,
      settings: renderSettings,
    };
    const renderer = renderers[view] || renderProjects;
    appNode.replaceChildren(await renderer(projectId));
  } catch (error) {
    appNode.textContent = `${t("view.error")}: ${error.message}`;
  }
}

document.querySelectorAll("[data-lang]").forEach((button) => {
  button.addEventListener("click", () => translate(button.dataset.lang));
});

const actionHandlers = {
  useDemo: useDemoProject,
  createProject: showCreateProjectForm,
  ingest: showIngestForm,
  buildWiki: buildCurrentProject,
};

document.querySelectorAll("[data-action]").forEach((button) => {
  const handler = actionHandlers[button.dataset.action];
  if (handler) {
    button.addEventListener("click", handler);
  }
});

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => loadView(button.dataset.view));
});

translate(initialLanguage());
loadView(currentProjectId ? "status" : "start");
