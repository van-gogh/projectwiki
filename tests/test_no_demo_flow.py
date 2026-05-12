from fastapi.testclient import TestClient

import whywiki.app as app_module
from whywiki.app import app


def test_app_does_not_use_python_311_only_resources_import():
    app_source = app_module.Path(app_module.__file__).read_text(encoding="utf-8")

    assert "importlib.resources.abc" not in app_source


def test_pyproject_packages_only_product_assets():
    pyproject = app_module.Path(app_module.__file__).resolve().parents[1] / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")

    assert "[tool.setuptools.packages.find]" in content
    assert 'include = ["whywiki*"]' in content
    assert '"static/*.html"' in content
    assert '"static/*.css"' in content
    assert '"static/*.js"' in content
    assert "demo_project" not in content


def test_demo_api_is_not_a_product_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))

    client = TestClient(app)
    response = client.post("/api/demo")

    assert response.status_code == 404


def test_app_has_no_packaged_demo_project_helper():
    assert not hasattr(app_module, "demo_project_root")
