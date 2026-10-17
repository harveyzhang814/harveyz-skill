#!/usr/bin/env python3
"""Run one scripted user turn against the worktree skill in Claude Code."""
import json
import os
import pathlib
import subprocess
import sys
import uuid

BASE = pathlib.Path(__file__).resolve().parent
SKILL = pathlib.Path(os.environ.get("BRAINSKILL_SOURCE", BASE.parents[2] / "skills/superpowers-rewrite/brainstorming-zh/SKILL.md"))

def main():
    scenario, message = sys.argv[1], sys.argv[2]
    root = BASE / "scenarios" / scenario
    project = root / "project"
    project.mkdir(parents=True, exist_ok=True)
    logs = root / "logs"
    logs.mkdir(exist_ok=True)
    state_path = root / "session.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"session_id": str(uuid.uuid4()), "turns": []}
    turn = len(state["turns"]) + 1
    args = ["claude", "-p", "--model", "sonnet", "--output-format", "stream-json", "--verbose",
            "--permission-mode", "bypassPermissions", "--setting-sources", "",
            "--append-system-prompt-file", str(SKILL),
            "--tools", "Read,Glob,Grep,Bash,Write,Edit"]
    if turn == 1:
        args += ["--session-id", state["session_id"]]
    else:
        args += ["--resume", state["session_id"]]
    args += [message]
    run = subprocess.run(args, cwd=project, capture_output=True, text=True, timeout=600)
    (logs / f"turn-{turn:02d}.jsonl").write_text(run.stdout)
    (logs / f"turn-{turn:02d}.stderr").write_text(run.stderr)
    (logs / f"turn-{turn:02d}.user.txt").write_text(message + "\n")
    events = [json.loads(line) for line in run.stdout.splitlines() if line.startswith("{")]
    result = next((event for event in reversed(events) if event.get("type") == "result"), {})
    uses = []
    for event in events:
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    uses.append({"name": block.get("name"), "input": block.get("input")})
    summary = {"turn": turn, "user": message, "assistant": result.get("result"), "exit_code": run.returncode,
               "terminal_reason": result.get("terminal_reason"), "tool_uses": uses,
               "cost_usd": result.get("total_cost_usd")}
    (logs / f"turn-{turn:02d}.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    state["turns"].append({"turn": turn, "exit_code": run.returncode})
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    display = {**summary, "tool_uses": [{"name": use["name"], "path": use["input"].get("file_path", use["input"].get("command", ""))} for use in uses]}
    print(json.dumps(display, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
