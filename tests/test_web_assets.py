from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "projectwiki" / "static"


def test_dashboard_assets_exist():
    assert (STATIC / "index.html").exists()
    assert (STATIC / "styles.css").exists()
    assert (STATIC / "app.js").exists()
    assert (STATIC / "i18n.js").exists()


def test_i18n_contains_chinese_and_english_keys():
    content = (STATIC / "i18n.js").read_text(encoding="utf-8")

    assert "zh-CN" in content
    assert "en-US" in content
    assert "nav.projects" in content
    assert "action.buildWiki" in content
    assert "error.readLogs" in content
