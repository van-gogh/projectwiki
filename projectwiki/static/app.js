const supportedLanguages = ["zh-CN", "en-US"];
let currentProjectId = storageGet("projectwiki.currentProjectId");

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
  return navigator.language && navigator.language.startsWith("zh") ? "zh-CN" : "en-US";
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
      const panel = createPanel(t("dashboard.title"));
      const message = document.createElement("p");
      message.textContent = t("view.noProject");
      panel.append(message);
      appNode.replaceChildren(panel);
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

const demoButton = document.querySelector('[data-i18n="action.useDemo"]');
if (demoButton) {
  demoButton.addEventListener("click", useDemoProject);
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => loadView(button.dataset.view));
});

translate(initialLanguage());
