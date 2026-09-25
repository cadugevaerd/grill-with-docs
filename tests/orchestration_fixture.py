"""Synthetic offline adapter transport; never represents live harness evidence.

The public parser, native session normalization, reference hash checks, request
correlation and Store all run. Only native I/O and the presentation-axis probe
are injected; current configuration and startup trust are unavailable in the live adapter.
"""
from __future__ import annotations

import atexit
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from unittest import mock

# Codex specialists resolve the astra family against the local Codex catalog;
# tests pin it to a fixture so the result never depends on the host's ~/.codex.
os.environ["CODEX_HOME"] = str(Path(__file__).resolve().parent / "fixtures/codex-home")

REFERENCE = Path(__file__).parent / "fixtures/orchestration/SKILL.md"
SESSION = "orca:ctx-fixture"


_GOLDEN: dict[str, object] = {}
_GOLDEN_HOME = Path(tempfile.mkdtemp(prefix="gwd-golden-"))
atexit.register(shutil.rmtree, _GOLDEN_HOME, True)


def _force_remove(function, path, _excinfo):
    os.chmod(path, 0o700)
    function(path)


def golden_repo(key: str, build) -> tuple[Path, object]:
    """Build an expensive repository once per process, hand each test a fresh copy.

    The store records absolute paths (control worktree, git common dir,
    presentation scope), so the copy is restored at the very path it was
    built on -- a copy elsewhere is a different project. ``build(root)``
    runs once; its return value is handed back with every copy.
    """
    root = _GOLDEN_HOME / hashlib.sha256(key.encode()).hexdigest()[:16] / "repo"
    backup = root.with_name("golden")
    if key not in _GOLDEN:
        root.parent.mkdir(parents=True, exist_ok=True)
        _GOLDEN[key] = build(root)
        shutil.copytree(root, backup, symlinks=True)
    else:
        shutil.rmtree(root, onerror=_force_remove)
        shutil.copytree(backup, root, symlinks=True)
    return root, _GOLDEN[key]


def pack(value):
    return json.dumps(value, sort_keys=True).encode()


def native_show(root, runtime, dispatch="ctx-fixture"):
    return {"ok": True, "result": {
        "dispatch": {"id": dispatch, "taskId": "task-fixture", "hostScope": {"hostId": "host-fixture"},
            "processIncarnation": "pty-fixture:inc-fixture", "capabilityRevokedAt": None, "status": "dispatched"},
        "worker": {"dispatchId": dispatch, "state": "ready", "runtimeEpoch": "runtime-fixture", "worktreeId": "worktree-fixture",
            "agentTerminalHandle": "term-fixture", "startOptions": {"launch": {
                "requested": {"agent": runtime, "model": "fixture-model", "effort": "high"},
                "effective": {"agent": runtime, "model": "fixture-model", "effort": "high"}}}},
        "terminal": {"handle": "term-fixture", "ptyId": "pty-fixture", "incarnationId": "inc-fixture",
            "worktreeId": "worktree-fixture", "worktreePath": str(root), "executionHostId": "host-fixture",
            "agentIdentity": runtime, "orphaned": False},
        "terminalResource": {"terminalHandle": "term-fixture", "worktreeId": "worktree-fixture",
            "endpointId": "runtime-fixture", "endpointIncarnation": "pty-fixture:inc-fixture",
            "ownerDispatchId": dispatch, "releaseState": "not_requested"},
        "projection": {"taskId": "task-fixture", "provider": {"id": runtime},
            "liveness": {"verdict": "live", "source": "agent_status"}},
        "observation": {"exactWorker": True}}}


def tool_pair(runtime, command, output, event_id):
    return [{"id": event_id + "-call", "role": "assistant", "blocks": [{"type": "tool-call",
        "name": "Bash" if runtime == "claude" else "exec_command",
        "input": {"command" if runtime == "claude" else "cmd": command}}]},
        {"id": event_id, "role": "tool", "blocks": [{"type": "tool-result", "output": output}]}]


def boundary(module, root, runtime, session_ref, work_id, *, loaded=True):
    core = module.grill_core_module("agent_runtime")
    dispatch = session_ref.removeprefix("orca:")
    show = native_show(root, runtime, dispatch)
    transcript = {"ok": True, "result": {"dispatchId": dispatch, "provider": runtime,
        "source": "transcript", "sourceIdentity": "transcript-fixture", "sourceExact": True,
        "contentComplete": True, "clipping": [], "transcript": {"messages": [], "limited": False}}}
    axes = {"installation": {"status": "present", "version": "0.3.0", "skill_ref": str(REFERENCE)},
        "enablement": {"state": "enabled", "source_ref": "fixture:plugin-list", "source_sha256": "a" * 64},
        "configuration": {"state": "observed", "source_ref": "fixture:session-config", "source_sha256": "c" * 64},
        "trust": {"state": "ready", "source_ref": "fixture:startup", "source_sha256": "b" * 64}}
    def read(argv):
        return pack(show if argv[1] == "worker-show" else transcript)
    adapter = core.LeaderBoundary(session_ref, root, runtime, "term-fixture", read,
                                  lambda observed, source: copy.deepcopy(axes))
    policy_raw = module._policy_path(root, work_id).read_bytes()
    _, pending = core.project_leader_presentation(adapter, policy=json.loads(policy_raw),
        policy_sha256=hashlib.sha256(policy_raw).hexdigest(),
        gwd_skill_sha256=hashlib.sha256((module.ASSETS.parent / "SKILL.md").read_bytes()).hexdigest(),
        runtime=runtime, scope={"kind": "gwd", "root": str(root), "work_id": work_id})
    if loaded:
        import shlex
        script = str(Path(core.__file__).resolve().parents[1] / "grill_workspace.py")
        command = [sys.executable, "-B", script, "preflight" if work_id is None else "init", str(root),
                   "--runtime", runtime, "--session-ref", session_ref]
        if work_id is not None:
            command += ["--work-id", work_id, "--type", "feature", "--slug", "fixture"]
        transcript["result"]["transcript"]["messages"] = (
            tool_pair(runtime, shlex.join(command),
                      json.dumps({"verdict": "BLOCKED", "code": "STYLE-LOAD-UNCONFIRMED", "presentation": pending}), "request")
            + tool_pair(runtime, shlex.join([shutil.which("cat"), "--", str(REFERENCE)]), REFERENCE.read_text(), "read"))
    return adapter, show, transcript


@contextlib.contextmanager
def offline_leader(module):
    with tempfile.TemporaryDirectory() as temporary:
        assets = Path(temporary) / "assets"
        shutil.copytree(module.ASSETS, assets)
        shutil.copyfile(module.ASSETS.parent / "SKILL.md", assets.parent / "SKILL.md")
        for policy_path in assets.glob("agent-orchestration.v*.json"):
            policy = json.loads(policy_path.read_bytes())
            policy["presentation"]["approved"] = [{"version": "0.3.0", "skill_sha256":
                "sha256:" + hashlib.sha256(REFERENCE.read_bytes()).hexdigest()}]
            policy_path.write_bytes(pack(policy))
        native_which = shutil.which
        with mock.patch.object(shutil, "which", side_effect=lambda name, *args, **kwargs:
                (native_which(name, *args, **kwargs) or "/offline/bin/cat") if name == "cat" else native_which(name, *args, **kwargs)), \
                mock.patch.object(module, "ASSETS", assets), mock.patch.object(module, "_leader_boundary",
                side_effect=lambda *args: boundary(module, *args)[0]):
            yield


def command(program, args):
    """Subprocess wrapper keeps argv parsing and process isolation in CLI tests."""
    values = [SESSION if value == "fixture-leader" else str(value) for value in args]
    if Path(program).name != "grill_workspace.py":
        return [sys.executable, "-B", str(program), *values]
    if values and values[0] in {"init", "checkpoint", "attest", "phase-turn", "partition-emit", "gauntlet-tasks-reconcile", "gauntlet-tasks-rebase", "gauntlet-run", "gauntlet-resume", "gauntlet-cleanup",
            "gauntlet-prepare-worker", "gauntlet-wave-declare", "gauntlet-converge", "gauntlet-run-abandon",
            "gauntlet-worker-declare", "gauntlet-progress-record", "gauntlet-worker-terminal", "gauntlet-remediate"} and "--session-ref" not in values:
        values += ["--session-ref", SESSION]
    if values and values[0] == "checkpoint" and "--operation-id" not in values:
        values += ["--operation-id", "cp-" + hashlib.sha256(pack(values)).hexdigest()[:24]]
    return [sys.executable, "-B", str(Path(__file__).resolve()), str(program), *values]


def main():
    program, *args = sys.argv[1:]
    sys.path.insert(0, str(Path(program).parent))
    spec = importlib.util.spec_from_file_location("offline_workspace", program)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    with offline_leader(module):
        return module.main(args)


if __name__ == "__main__":
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    raise SystemExit(main())


def materialize_active_workflow(root):
    """Test setup only: v5 has no consumer migration command."""
    from grill_core import workflow_v5, workflow_versions
    assert workflow_versions.ACTIVE_VERSION == workflow_v5.VERSION
    (root / "WORKFLOW.md").write_bytes(workflow_v5.render_v5())
