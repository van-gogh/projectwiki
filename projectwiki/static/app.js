const supportedLanguages = ["zh-CN", "en-US"];

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

document.querySelectorAll("[data-lang]").forEach((button) => {
  button.addEventListener("click", () => translate(button.dataset.lang));
});

translate(initialLanguage());
