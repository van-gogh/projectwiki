from pathlib import Path

import pytest

from projectwiki.services.ask import ask_project
from projectwiki.services.ingest import ingest_path
from projectwiki.services.wiki_engine import build_project
from projectwiki.services.workspace import create_project


def build_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTWIKI_DATA_DIR", str(tmp_path / "data"))
    project = create_project("Demo")
    root = Path(__file__).resolve().parents[1] / "examples" / "demo-project"
    ingest_path(project["id"], root)
    build_project(project["id"])
    return project


def test_ask_returns_structured_evidence(tmp_path, monkeypatch):
    project = build_demo(tmp_path, monkeypatch)

    result = ask_project(project["id"], "接口是什么？")

    assert result["evidence"]
    assert {"kind", "id", "path", "score"}.issubset(result["evidence"][0])
    assert "证据" in result["answer"]


def test_ask_returns_evidence_for_exact_docker_term(tmp_path, monkeypatch):
    project = build_demo(tmp_path, monkeypatch)

    result = ask_project(project["id"], "Docker")

    assert result["evidence"]
    assert "证据" in result["answer"]


def test_ask_returns_evidence_for_exact_post_term(tmp_path, monkeypatch):
    project = build_demo(tmp_path, monkeypatch)

    result = ask_project(project["id"], "POST")

    assert result["evidence"]
    assert "证据" in result["answer"]


def test_ask_refuses_method_without_matching_evidence(tmp_path, monkeypatch):
    project = build_demo(tmp_path, monkeypatch)

    result = ask_project(project["id"], "GET")

    assert result["evidence"] == []
    assert "没有找到足够证据" in result["answer"]


def test_ask_refuses_without_evidence(tmp_path, monkeypatch):
    project = build_demo(tmp_path, monkeypatch)

    result = ask_project(project["id"], "火星基地预算是多少？")

    assert result["evidence"] == []
    assert "没有找到足够证据" in result["answer"]


@pytest.mark.parametrize("question", ["用户预算是多少？", "用户收费是多少？", "模型预算是多少？"])
def test_ask_refuses_unsupported_pricing_intent_with_known_terms(tmp_path, monkeypatch, question):
    project = build_demo(tmp_path, monkeypatch)

    result = ask_project(project["id"], question)

    assert result["evidence"] == []
    assert "没有找到足够证据" in result["answer"]
