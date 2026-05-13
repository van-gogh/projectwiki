from pathlib import Path
from html.parser import HTMLParser
import re


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "whywiki" / "static"


class DashboardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.i18n_keys = set()
        self.placeholder_keys = set()
        self.stylesheets = []
        self.icons = []
        self.scripts = []
        self.button_stack = []
        self.i18n_buttons = []
        self.action_buttons = set()
        self.language_switches = []

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        if "data-i18n" in attr_map:
            self.i18n_keys.add(attr_map["data-i18n"])
        if "data-i18n-placeholder" in attr_map:
            self.placeholder_keys.add(attr_map["data-i18n-placeholder"])
        if tag == "link" and attr_map.get("rel") == "stylesheet":
            self.stylesheets.append(attr_map["href"])
        if tag == "link" and attr_map.get("rel") == "icon":
            self.icons.append(attr_map["href"])
        if tag == "script" and "src" in attr_map:
            self.scripts.append(attr_map["src"])
        if "data-action" in attr_map:
            self.action_buttons.add(attr_map["data-action"])
        if "data-active-lang" in attr_map:
            self.language_switches.append(attr_map["data-active-lang"])
        if tag == "button":
            self.button_stack.append(
                {
                    "data_i18n": attr_map.get("data-i18n"),
                    "data_view": attr_map.get("data-view"),
                    "data_action": attr_map.get("data-action"),
                    "text": "",
                }
            )

    def handle_data(self, data):
        if self.button_stack:
            self.button_stack[-1]["text"] += data

    def handle_endtag(self, tag):
        if tag == "button" and self.button_stack:
            button = self.button_stack.pop()
            if button["data_i18n"]:
                self.i18n_buttons.append(button)


def parse_dashboard():
    parser = DashboardParser()
    parser.feed((STATIC / "index.html").read_text(encoding="utf-8"))
    return parser


def parse_i18n_keys():
    content = (STATIC / "i18n.js").read_text(encoding="utf-8")
    languages = {}
    for language in ("zh-CN", "en-US"):
        match = re.search(rf'"{re.escape(language)}":\s*\{{(?P<body>.*?)\n  \}}', content, re.S)
        assert match, f"Missing {language} dictionary"
        languages[language] = set(re.findall(r'"([^"]+)":', match.group("body")))
    return languages


def static_url_exists(url):
    assert url.startswith("/static/")
    return (STATIC / url.removeprefix("/static/")).exists()


def test_dashboard_asset_references_exist():
    parser = parse_dashboard()

    assert (STATIC / "index.html").exists()
    assert (STATIC / "styles.css").exists()
    assert (STATIC / "app.js").exists()
    assert (STATIC / "i18n.js").exists()
    assert parser.icons == ["data:,"]
    assert parser.stylesheets == ["/static/styles.css"]
    assert parser.scripts == ["/static/i18n.js", "/static/app.js"]
    for href in parser.stylesheets:
        assert static_url_exists(href)
    for src in parser.scripts:
        assert static_url_exists(src)


def test_i18n_contains_all_dashboard_keys_for_each_language():
    parser = parse_dashboard()
    keys = parser.i18n_keys | parser.placeholder_keys
    languages = parse_i18n_keys()

    assert "nav.start" in keys
    assert "nav.status" in keys
    assert "nav.review" in keys
    assert "nav.wikiIndex" in keys
    assert "action.buildWiki" in keys
    assert "search.placeholder" in keys
    assert "dashboard.title" in keys
    for language, language_keys in languages.items():
        assert not keys - language_keys, f"{language} missing keys: {sorted(keys - language_keys)}"


def test_sidebar_buttons_expose_view_hooks():
    parser = parse_dashboard()
    views = {
        button["data_view"]
        for button in parser.i18n_buttons
        if button["data_i18n"] and button["data_i18n"].startswith("nav.")
    }

    assert {"start", "status", "sources", "review", "ask", "settings", "wiki"} <= views
    assert "handover" not in views


def test_top_action_buttons_expose_action_hooks():
    parser = parse_dashboard()

    assert {"useDemo", "createProject", "ingest", "buildWiki"} <= parser.action_buttons


def test_i18n_contains_chinese_and_english_dictionaries():
    content = (STATIC / "i18n.js").read_text(encoding="utf-8")

    assert "zh-CN" in content
    assert "en-US" in content
    assert "error.readLogs" in content


def test_sidebar_exposes_collaboration_status_targets():
    content = (STATIC / "index.html").read_text(encoding="utf-8")

    assert 'id="accountStatus"' in content
    assert 'id="loginGithubButton"' in content
    assert 'id="loginGiteaButton"' in content
    assert 'id="workspaceStatus"' in content
    assert 'id="linkedRepoStatus"' in content


def test_login_provider_placeholders_are_disabled():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    css = (STATIC / "styles.css").read_text(encoding="utf-8")

    for button_id in ("loginGithubButton", "loginGiteaButton"):
        pattern = rf'<button[^>]*id="{button_id}"[^>]*disabled[^>]*aria-disabled="true"'
        assert re.search(pattern, html), f"{button_id} must be visibly disabled until OAuth exists"
    assert ".secondary-action:disabled" in css
    assert '[aria-disabled="true"]' in css


def test_i18n_includes_git_provider_collaboration_copy():
    content = (STATIC / "i18n.js").read_text(encoding="utf-8")

    assert "Login with GitHub" in content
    assert "Login with Gitea" in content
    assert "缺少代码仓库访问权限" in content


def test_app_js_fetches_collaboration_status_endpoints():
    content = (STATIC / "app.js").read_text(encoding="utf-8")

    assert "/api/auth/accounts" in content
    assert "/api/workspace/status" in content


def test_app_js_rerenders_active_view_after_language_change():
    content = (STATIC / "app.js").read_text(encoding="utf-8")

    assert "activeView" in content
    assert "rerenderActiveViewAfterLanguageChange" in content
    assert "function translate(lang, { rerender = false } = {})" in content
    assert 'translate(button.dataset.lang, { rerender: true })' in content


def test_i18n_buttons_have_english_fallback_labels():
    parser = parse_dashboard()

    assert parser.i18n_buttons
    for button in parser.i18n_buttons:
        assert button["text"].strip(), f"Missing fallback label for {button['data_i18n']}"


def test_app_js_handles_unavailable_storage_and_bad_language_data():
    content = (STATIC / "app.js").read_text(encoding="utf-8")

    assert "function storageGet" in content
    assert "function storageSet" in content
    assert "try {" in content
    assert "catch" in content
    assert "function normalizeLanguage" in content
    assert 'dictionaries["en-US"] || {}' in content
    assert "data-i18n-placeholder" in content


def test_app_js_persists_demo_project_and_wires_dashboard_endpoints():
    content = (STATIC / "app.js").read_text(encoding="utf-8")

    assert "currentProjectId" in content
    assert 'storageSet("whywiki.currentProjectId"' in content
    assert 'storageGet("whywiki.currentProjectId")' in content
    assert "function visibleWikiPages" in content
    assert 'page.slug !== "handover"' in content
    assert 'document.querySelectorAll("[data-view]")' in content
    assert 'document.querySelectorAll("[data-action]")' in content
    for endpoint in (
        "/api/projects",
        "/api/projects/${projectId}/ingest",
        "/api/projects/${projectId}/build",
        "/api/projects/${projectId}/conflicts",
        "/api/projects/${projectId}/wiki",
        "/api/projects/${projectId}/wiki/${slug}",
        "/api/projects/${projectId}/handover",
        "/api/projects/${projectId}/ask",
        "/api/projects/${projectId}/sources",
        "/api/projects/${projectId}/facts",
    ):
        assert endpoint in content


def test_i18n_contains_dynamic_dashboard_keys_for_each_language():
    languages = parse_i18n_keys()
    dynamic_keys = {
        "demo.nextActions",
        "start.title",
        "start.subtitle",
        "workflow.project",
        "workflow.ingest",
        "workflow.build",
        "workflow.review",
        "workflow.use",
        "status.title",
        "status.subtitle",
        "status.current",
        "status.recent",
        "status.review",
        "status.stable",
        "status.changed",
        "status.evidence",
        "status.needsReview",
        "review.title",
        "review.subtitle",
        "settings.export",
        "settings.handover",
        "project.create.title",
        "project.create.name",
        "project.create.description",
        "project.create.submit",
        "project.create.ready",
        "ingest.title",
        "ingest.path",
        "ingest.sourceType",
        "ingest.submit",
        "ingest.ready",
        "build.loading",
        "build.ready",
        "build.factsCreated",
        "build.conflictsCreated",
        "build.pagesCreated",
        "view.noProject",
        "view.loading",
        "view.error",
        "view.sources.title",
        "view.facts.title",
        "view.wiki.title",
        "view.conflicts.title",
        "view.handover.title",
        "view.ask.title",
        "view.empty",
        "ask.defaultQuestion",
        "ask.submit",
        "field.path",
        "field.title",
        "field.type",
        "field.statement",
        "field.confidence",
        "field.status",
        "field.severity",
        "field.evidence",
        "field.projectId",
        "field.sourcesCreated",
        "field.filesSeen",
        "field.skippedFiles",
    }

    for language, language_keys in languages.items():
        assert not dynamic_keys - language_keys, f"{language} missing keys: {sorted(dynamic_keys - language_keys)}"


def test_styles_include_mobile_overflow_guards():
    content = (STATIC / "styles.css").read_text(encoding="utf-8")

    assert "@media (max-width: 720px)" in content
    assert "min-width: 0;" in content
    assert "flex-wrap: wrap;" in content
    assert "display: block;" in content


def test_language_switch_has_bouncing_bubble_state():
    parser = parse_dashboard()
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")

    assert parser.language_switches == ["en-US"]
    assert ".language-switch::before" in css
    assert "language-bubble-hop" in css
    assert "[data-active-lang=\"en-US\"]" in css
    assert "function updateLanguageSwitch" in js
    assert "aria-pressed" in js
    assert "is-bouncing" in js
