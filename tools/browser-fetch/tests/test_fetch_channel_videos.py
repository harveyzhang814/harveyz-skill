from browser_fetch.cli import build_parser


def test_fetch_channel_videos_is_registered():
    """No CLI equivalent of MCP's session.list_tools() exists — the closest
    functional analog is checking the subcommand is wired into the argparse
    parser, i.e. `browser-fetch channel ...` is a real, dispatchable command."""
    parser = build_parser()
    command_action = next(
        a for a in parser._subparsers._group_actions if a.dest == "command"
    )
    assert "channel" in command_action.choices


def test_fetch_channel_videos_rejects_non_youtube_url(run_cli):
    proc, _ = run_cli("channel", "https://x.com/mattpocockuk")
    assert proc.returncode == 2
    assert "Not a YouTube channel URL" in proc.stderr


def test_fetch_channel_videos_rejects_watch_url(run_cli):
    """A single video URL is not a channel — this skill never ingests one."""
    proc, _ = run_cli("channel", "https://www.youtube.com/watch?v=gaDdrDdczO4")
    assert proc.returncode == 2
    assert "Not a YouTube channel URL" in proc.stderr


def test_fetch_channel_videos_rejects_file_scheme(run_cli):
    proc, _ = run_cli("channel", "file:///etc/passwd")
    assert proc.returncode == 2
    assert "only http/https allowed" in proc.stderr
