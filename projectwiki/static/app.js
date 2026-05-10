const supportedLanguages = ["zh-CN", "en-US"];

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

function appendField(list, label, value) {
  const row = document.createElement("div");
  const labelNode = document.createElement("strong");
  const valueNode = document.createElement("span");
  labelNode.textContent = `${label}: `;
  valueNode.textContent = String(value);
  row.append(labelNode, valueNode);
  list.append(row);
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
  return container;
}

async function useDemoProject() {
  const appNode = document.querySelector("#app");
  if (!appNode) return;

  appNode.textContent = t("demo.loading");
  try {
    const payload = await api("/api/demo", { method: "POST" });
    appNode.replaceChildren(renderDemoResult(payload));
  } catch (error) {
    appNode.textContent = `${t("demo.error")}: ${error.message}. ${t("error.readLogs")}`;
  }
}

document.querySelectorAll("[data-lang]").forEach((button) => {
  button.addEventListener("click", () => translate(button.dataset.lang));
});

const demoButton = document.querySelector('[data-i18n="action.useDemo"]');
if (demoButton) {
  demoButton.addEventListener("click", useDemoProject);
}

translate(initialLanguage());
