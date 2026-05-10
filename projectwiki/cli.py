from __future__ import annotations

import argparse
import json
import os
import sys

from .db import init_db
from .runtime import (
    PortInUseError,
    append_runtime_log,
    choose_port,
    clear_runtime_state,
    default_runtime_paths,
    read_active_runtime_state,
    read_log_tail,
    write_runtime_state,
)
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

    sub.add_parser("open")
    sub.add_parser("status")

    p_log = sub.add_parser("log")
    p_log.add_argument("--lines", type=int, default=80)

    sub.add_parser("doctor")
    sub.add_parser("stop")

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
        paths = default_runtime_paths()
        active_state = read_active_runtime_state(paths)
        if active_state is not None:
            url = f"http://{active_state['host']}:{active_state['port']}"
            print("ProjectWiki is already running locally.")
            print(f"Open: {url}")
            print("Logs: projectwiki log")
            return 0

        try:
            port = choose_port(args.host, preferred=args.port)
        except PortInUseError:
            print(f"Port {args.host}:{args.port} is already in use.", file=sys.stderr)
            print("ProjectWiki will not choose another port automatically.", file=sys.stderr)
            print("Stop the process using that port, or start ProjectWiki with an explicit --port.", file=sys.stderr)
            append_runtime_log(paths, f"Port {args.host}:{args.port} is already in use; startup aborted.")
            return 2

        import uvicorn

        url = f"http://{args.host}:{port}"
        write_runtime_state(paths, host=args.host, port=port, pid=os.getpid())
        append_runtime_log(paths, f"Starting ProjectWiki on {url}")
        print("ProjectWiki is running locally.")
        print(f"Open: {url}")
        print("Logs: projectwiki log")
        try:
            uvicorn.run("projectwiki.app:app", host=args.host, port=port, reload=False)
            return 0
        finally:
            append_runtime_log(paths, "ProjectWiki server stopped.")
            clear_runtime_state(paths)

    if args.command == "status":
        state = read_active_runtime_state(default_runtime_paths())
        print(json.dumps(state or {"running": False}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "log":
        print(read_log_tail(default_runtime_paths(), args.lines), end="")
        return 0

    if args.command == "doctor":
        paths = default_runtime_paths()
        print(json.dumps({
            "data_dir": str(paths.data_dir),
            "state_file_exists": paths.state_path.exists(),
            "log_file_exists": paths.log_path.exists(),
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "open":
        state = read_active_runtime_state(default_runtime_paths()) or {}
        url = f"http://{state.get('host', '127.0.0.1')}:{state.get('port', 8765)}"
        print(url)
        return 0

    if args.command == "stop":
        print("Stop is not active yet. Use Ctrl+C for foreground serve sessions.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
