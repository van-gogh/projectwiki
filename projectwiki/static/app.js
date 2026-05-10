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
  ["conflicts", "wiki", "handover", "ask", "sources", "facts"].forEach((view) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.nextView = view;
    button.textContent = t(`nav.${view}`);
    button.addEventListener("click", () => loadView(view));
    actions.append(button);
  });
  parent.append(actionsTitle, actions);
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

async function renderWiki(projectId) {
  const pages = await api(`/api/projects/${projectId}/wiki`);
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
  return renderTextPanel(t("view.settings.title"), t("view.noProject"));
}

async function loadView(view) {
  const appNode = appContainer();
  if (!appNode) return;
  setActiveView(view);
  appNode.textContent = t("view.loading");

  try {
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
      sources: renderSources,
      facts: renderFacts,
      wiki: renderWiki,
      conflicts: renderConflicts,
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
