"""CLI minimale per eseguire orchestrator e agenti.

Uso:

```bash
aiagents list
aiagents run knowledge_base "Aggiorna la KB dai file in ./data/input"
aiagents run-agent indexer "Rigenera INDEX.md"
```
"""

from __future__ import annotations

import argparse
import json
import sys

from rich.console import Console
from rich.table import Table

from ..a2a.server import list_orchestrators
from ..core.registry import AgentRegistry
from ..agents import bootstrap_all

console = Console()


def _cmd_list(_args: argparse.Namespace) -> int:
    bootstrap_all()
    table = Table(title="Agenti registrati")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    for a in AgentRegistry.list():
        table.add_row(a.name, a.description)
    console.print(table)

    table2 = Table(title="Orchestrator")
    table2.add_column("Name", style="magenta")
    table2.add_column("Group")
    table2.add_column("Mission")
    for o in list_orchestrators():
        table2.add_row(o.name, o.group, o.mission[:80])
    console.print(table2)
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    bootstrap_all()
    name: str = args.name
    task: str = args.task
    orch = next((o for o in list_orchestrators() if o.name == name), None)
    if orch is None:
        console.print(f"[red]Orchestrator '{name}' non trovato[/red]")
        return 2
    result = orch.run(task)
    console.rule(f"Output di {name}")
    console.print(result.output_text)
    if args.verbose:
        console.rule("Tool calls")
        console.print(json.dumps(result.tool_calls, ensure_ascii=False, indent=2))
    return 0


def _cmd_run_agent(args: argparse.Namespace) -> int:
    bootstrap_all()
    try:
        agent = AgentRegistry.get(args.name)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2
    result = agent.run(args.task)
    console.rule(f"Output di {args.name}")
    console.print(result.output_text)
    if args.verbose:
        console.rule("Tool calls")
        console.print(json.dumps(result.tool_calls, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aiagents", description="AI Agents Creator CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Elenca agenti e orchestrator").set_defaults(func=_cmd_list)

    p_run = sub.add_parser("run", help="Esegui un orchestrator per nome")
    p_run.add_argument("name")
    p_run.add_argument("task")
    p_run.add_argument("-v", "--verbose", action="store_true")
    p_run.set_defaults(func=_cmd_run)

    p_agent = sub.add_parser("run-agent", help="Esegui un singolo agent per nome")
    p_agent.add_argument("name")
    p_agent.add_argument("task")
    p_agent.add_argument("-v", "--verbose", action="store_true")
    p_agent.set_defaults(func=_cmd_run_agent)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
