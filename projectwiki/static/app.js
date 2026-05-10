const supportedLanguages = ["zh-CN", "en-US"];

function initialLanguage() {
  const saved = localStorage.getItem("projectwiki.language");
  if (supportedLanguages.includes(saved)) return saved;
  return navigator.language && navigator.language.startsWith("zh") ? "zh-CN" : "en-US";
}

function translate(lang) {
  const dict = window.ProjectWikiI18n[lang];
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = dict[node.dataset.i18n] || node.dataset.i18n;
  });
  localStorage.setItem("projectwiki.language", lang);
}

document.querySelectorAll("[data-lang]").forEach((button) => {
  button.addEventListener("click", () => translate(button.dataset.lang));
});

translate(initialLanguage());
