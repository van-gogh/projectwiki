from __future__ import annotations

import argparse
import json
import sys

from .db import init_db
from .services.ask import ask_project
from .services.ingest import ingest_path
from .services.wiki_engine import build_project
from .services.workspace import create_project, list_projects


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="projectwiki")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")

    p_create = sub.add_parser("create")
    p_create.add_argument("name")
    p_create.add_argument("--description", default="")

    sub.add_parser("list")

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("project_id")
    p_ingest.add_argument("path")
    p_ingest.add_argument("--source-type", default="local", choices=["local", "git"])

    p_build = sub.add_parser("build")
    p_build.add_argument("project_id")

    p_ask = sub.add_parser("ask")
    p_ask.add_argument("project_id")
    p_ask.add_argument("question")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8080)

    args = parser.parse_args(argv)

    if args.command == "init-db":
        init_db()
        print("ProjectWiki database initialized.")
        return 0

    if args.command == "create":
        print(json.dumps(create_project(args.name, args.description), ensure_ascii=False, indent=2))
        return 0

    if args.command == "list":
        print(json.dumps(list_projects(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "ingest":
        print(json.dumps(ingest_path(args.project_id, args.path, args.source_type), ensure_ascii=False, indent=2))
        return 0

    if args.command == "build":
        print(json.dumps(build_project(args.project_id), ensure_ascii=False, indent=2))
        return 0

    if args.command == "ask":
        result = ask_project(args.project_id, args.question)
        print(result["answer"])
        return 0

    if args.command == "serve":
        import uvicorn
        uvicorn.run("projectwiki.app:app", host=args.host, port=args.port, reload=False)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
