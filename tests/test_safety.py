from pathlib import Path

import pytest

from atlas.core import SafetyError, safe_output_path, validate_command


@pytest.mark.parametrize(
    "argv",
    [
        ["docker", "restart", "demo-api"],
        ["docker", "compose", "up"],
        ["docker", "network", "rm", "demo_frontend"],
        ["systemctl", "restart", "demo-backup.service"],
        ["sh", "-c", "docker ps"],
        ["docker", "ps", ";", "id"],
        ["docker", "ps", "$(id)"],
        ["docker", "ps", "name|id"],
        ["ss", "-K", "dst", "127.0.0.1"],
    ],
)
def test_destructive_commands_and_shell_injection_are_refused(argv):
    with pytest.raises(SafetyError):
        validate_command(argv)


@pytest.mark.parametrize(
    "argv",
    [
        ["docker", "ps", "--format", "{{.Names}}"],
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        ["systemctl", "list-units", "--type=service"],
        ["systemctl", "list-timers", "--all"],
        ["ss", "-tln"],
    ],
)
def test_documented_read_commands_are_allowed(argv):
    validate_command(argv)


def test_renderer_accepts_only_owned_output(tmp_path: Path):
    repo = tmp_path / "repo"
    allowed = repo / "out" / "atlas.html"
    assert safe_output_path(repo, allowed) == allowed.resolve()
    with pytest.raises(SafetyError):
        safe_output_path(repo, repo / "README.md")
    with pytest.raises(SafetyError):
        safe_output_path(repo, repo / "out" / ".." / "README.md")
    with pytest.raises(SafetyError):
        safe_output_path(repo, repo / "out" / "atlas.sync-conflict-1.html")


def test_renderer_refuses_symlinked_output_root(tmp_path: Path):
    repo = tmp_path / "repo"
    external = tmp_path / "external"
    repo.mkdir()
    external.mkdir()
    (repo / "out").symlink_to(external, target_is_directory=True)
    with pytest.raises(SafetyError):
        safe_output_path(repo, repo / "out" / "atlas.html")
