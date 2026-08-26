#!/usr/bin/env python3
"""Executable contract matrix for isolated grill workspaces v2."""
from __future__ import annotations

import concurrent.futures
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path
from datetime import date

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
SCRIPT = PLUGIN / "skills/grill-with-docs/scripts/grill_workspace.py"
WORKFLOW_TEMPLATE = PLUGIN / "skills/grill-with-docs/assets/WORKFLOW.template.md"
CHECK_START = "<!-- grill-constitution-check:start -->"
CHECK_END = "<!-- grill-constitution-check:end -->"


def symlink_supported() -> bool:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        target = root / "target"
        target.mkdir()
        try:
            (root / "link").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
        return True


SYMLINK_SUPPORTED = symlink_supported()


def python_test_command(code: str) -> str:
    return subprocess.list2cmdline([sys.executable, "-c", code])


def load_workspace_module():
    name = "grill_workspace_contract_module"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def invoke(*args: object) -> tuple[subprocess.CompletedProcess[str], dict]:
    process = subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    lines = process.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError(f"expected one JSON line, got stdout={process.stdout!r} stderr={process.stderr!r}")
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise AssertionError(process.stdout) from exc
    return process, payload


SEQUENCE = tuple(load_workspace_module().SEQUENCE)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True).stdout.strip()


def snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


class WorkspaceV2Contract(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temporary.name)
        self.extra: list[tempfile.TemporaryDirectory] = []
        self._init_repo(self.root)

    def tearDown(self) -> None:
        for temporary in self.extra:
            temporary.cleanup()
        self.temporary.cleanup()

    def _init_repo(self, root: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
        git(root, "config", "user.email", "tests@example.invalid")
        git(root, "config", "user.name", "Contract Tests")
        (root / "WORKFLOW.md").write_bytes(WORKFLOW_TEMPLATE.read_bytes())
        git(root, "add", "WORKFLOW.md")
        git(root, "commit", "-q", "-m", "initial workflow")

    def _new_repo(self) -> Path:
        temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.extra.append(temporary)
        root = Path(temporary.name)
        self._init_repo(root)
        return root

    def _init_item(self, root: Path | None = None, work_id: str = "work-a", kind: str = "feature", slug: str = "alpha") -> Path:
        root = root or self.root
        process, payload = invoke("init", root, "--type", kind, "--slug", slug, "--work-id", work_id, '--skip-backlog')
        self.assertEqual(process.returncode, 0, (payload, process.stderr))
        self.assertEqual(payload["status"], "CREATED")
        item = root / ".grill" / "work-items" / work_id
        # Normal lifecycle fixtures represent an already reviewed work item;
        # dedicated constitutional tests deliberately overwrite this receipt.
        self._approve_check(item)
        return item

    def _metadata(self, item: Path) -> dict:
        return json.loads((item / "WORK-ITEM.json").read_text(encoding="utf-8"))

    def _write_metadata(self, item: Path, value: dict) -> None:
        (item / "WORK-ITEM.json").write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def _mark_complete(self, item: Path) -> None:
        path = item / "state.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["status"] = "complete"
        value["milestone_status"] = "completed"
        value["active_phase"] = None
        value["audit_verdict"] = "GO"
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        roadmap = item / "ROADMAP.md"
        roadmap.write_text(
            re.sub(r"(?m)^- state: (?:planned|ready-for-specify|blocked)$", "- state: complete", roadmap.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
        frontier = item / "DECISION-FRONTIER.md"
        frontier.write_text(frontier.read_text(encoding="utf-8").replace("- state: open", "- state: resolved"), encoding="utf-8")

    def _constitution(self, root: Path | None = None) -> Path:
        root = root or self.root
        path = root / ".specify/memory/constitution.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Constitution\n\n"
            "## Core Principles\n\n"
            "### I. Safety First\nAll work MUST fail closed.\n\n"
            "### II. Evidence\nEvery claim MUST have evidence.\n\n"
            "## Governance\nThe constitution is NON-NEGOTIABLE.\n",
            encoding="utf-8",
        )
        return path

    def _read_check(self, item: Path) -> dict:
        text = (item / "CONSTITUTION-CHECK.md").read_text(encoding="utf-8")
        block = text.split(CHECK_START, 1)[1].split(CHECK_END, 1)[0]
        match = re.search(r"```json\s*(\{.*\})\s*```", block, re.DOTALL)
        assert match is not None
        return json.loads(match.group(1))

    def _write_check(self, item: Path, value: dict) -> None:
        text = (
            "# Constitution Check\n\n"
            + CHECK_START
            + "\n```json\n"
            + json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n```\n"
            + CHECK_END
            + "\n"
        )
        (item / "CONSTITUTION-CHECK.md").write_text(text, encoding="utf-8")

    def _approve_check(self, item: Path, status: str = "PASS") -> dict:
        value = self._read_check(item)
        for entry in value["clauses"]:
            entry["status"] = status
            entry["evidence"] = ["tests/evidence.md"]
            entry["justification"] = "verified against the work-item scope"
        self._write_check(item, value)
        return value

    def test_rename_child_fallback_does_not_open_when_capability_is_unavailable(self):
        module = load_workspace_module()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
            parent = Path(temporary); source = parent / "source"; target = parent / "target"
            source.mkdir()
            with mock.patch.object(module.os, "supports_dir_fd", set()), mock.patch.object(module.os, "open", side_effect=AssertionError("open called")):
                module.rename_child(parent, source, target)
            self.assertTrue(target.is_dir())

    def test_rename_child_moves_directory_and_rejects_preexisting_target(self):
        module = load_workspace_module()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
            parent = Path(temporary); source = parent / "source"; target = parent / "target"
            source.mkdir(); module.rename_child(parent, source, target)
            self.assertFalse(source.exists()); self.assertTrue(target.is_dir())
            source.mkdir(); (target / "keep").write_text("keep")
            with self.assertRaises(OSError): module.rename_child(parent, source, target)
            self.assertTrue(source.is_dir()); self.assertEqual((target / "keep").read_text(), "keep")

    def test_rename_child_protected_branch_uses_dirfd_and_flags(self):
        module = load_workspace_module()
        if not hasattr(module.os, "O_DIRECTORY") or not hasattr(module.os, "O_NOFOLLOW"): self.skipTest("unsupported")
        original_supports = module.os.supports_dir_fd
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
            parent = Path(temporary); source = parent / "source"; target = parent / "target"; source.mkdir()
            real_open = module.os.open
            with mock.patch.object(module, "_rename_dirfd_capable", return_value=True), mock.patch.object(module.os, "open", wraps=real_open) as opened, mock.patch.object(module.os, "rename", wraps=module.os.rename) as renamed:
                module.rename_child(parent, source, target)
            self.assertTrue(opened.call_args.args[1] & module.os.O_DIRECTORY); self.assertTrue(opened.call_args.args[1] & module.os.O_NOFOLLOW)
            self.assertEqual(renamed.call_args.kwargs["src_dir_fd"], renamed.call_args.kwargs["dst_dir_fd"])

    def test_unexpected_permission_error_is_filesystem_json_with_context(self):
        module = load_workspace_module(); error = PermissionError(13, "denied", "source"); error.filename2 = "target"
        with mock.patch.object(module, "init_command", side_effect=error), mock.patch.object(module, "build_parser") as parser:
            parser.return_value.parse_args.return_value.command = "init"
            with mock.patch("builtins.print") as output:
                self.assertEqual(module.main(["init", str(self.root), "--type", "feature", "--slug", "alpha", "--skip-backlog"]), module.EXIT_BLOCKED)
            payload = json.loads(output.call_args.args[0])
        self.assertEqual(payload, {"verdict": "BLOCKED", "code": "FILESYSTEM", "error": "[Errno 13] denied: 'source' -> 'target'", "errno": 13, "path": "source", "path2": "target"})

    def test_filesystem_json_normalizes_byte_paths_and_native_command_parsing(self):
        module = load_workspace_module()
        error = OSError(5, "io", b"\xffsource"); error.filename2 = b"\xfetarget"
        with mock.patch.object(module, "init_command", side_effect=error), mock.patch.object(module, "build_parser") as parser:
            parser.return_value.parse_args.return_value.command = "init"
            with mock.patch("builtins.print") as output:
                self.assertEqual(module.main(["init", str(self.root), "--type", "feature", "--slug", "alpha", "--skip-backlog"]), module.EXIT_BLOCKED)
            line = output.call_args.args[0]
        payload = json.loads(line)
        self.assertEqual(payload["path"], "\\xffsource")
        self.assertEqual(payload["path2"], "\\xfetarget")
        windows = r'"C:\Program Files\Python\python.exe" -c "pass"'
        self.assertEqual(module.parse_test_command(windows, platform="nt"), windows)
        self.assertEqual(module.parse_test_command("python -c 'pass'", platform="posix"), ["python", "-c", "pass"])

    def _set_scope(self, item: Path, paths: list[str]) -> None:
        value = self._metadata(item)
        value["scope"] = {"paths": paths}
        self._write_metadata(item, value)

    def _set_dependencies(self, item: Path, dependencies: list[str]) -> None:
        value = self._metadata(item)
        value["depends-on-work"] = dependencies
        self._write_metadata(item, value)

    def _set_adr_conflicts(self, item: Path, references: list[str]) -> None:
        value = self._metadata(item)
        value["conflicts-with-adrs"] = references
        self._write_metadata(item, value)

    def _commit_all(self, root: Path, message: str = "work item") -> None:
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", message)

    def test_init_isolates_same_slug_and_never_writes_global(self) -> None:
        first = self._init_item(work_id="feature-one", slug="same")
        second = self._init_item(work_id="fix-two", kind="fix", slug="same")
        self.assertNotEqual(first, second)
        self.assertTrue((first / "docs/adr").is_dir())
        self.assertTrue((second / "handoffs").is_dir())
        self.assertFalse((self.root / ".grill/global").exists())
        self.assertEqual((self.root / "WORKFLOW.md").read_bytes(), WORKFLOW_TEMPLATE.read_bytes())
        state = json.loads((first / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["workflow"]["schema"], "v2")

    def test_v2_item_rejects_durable_worker_controls_without_workspace_mutation(self) -> None:
        """New FASE-002 controls must not upgrade or otherwise disturb V2 items."""
        self._init_item(work_id="v2-durable-controls")
        before = snapshot(self.root)
        head_before = git(self.root, "rev-parse", "HEAD")
        branch_before = git(self.root, "branch", "--show-current")
        status_before = git(self.root, "status", "--porcelain=v1", "--untracked-files=all")
        worktrees_before = git(self.root, "worktree", "list", "--porcelain")
        commands = (
            ("gauntlet-run", ()),
            ("gauntlet-resume", ("--run-id", "run-v2-control-a1b2")),
            (
                "gauntlet-prepare-worker",
                ("--run-id", "run-v2-control-a1b2", "--worker-id", "worker-v2", "--scope", "plugin"),
            ),
            (
                "gauntlet-cleanup",
                ("--run-id", "run-v2-control-a1b2", "--worker-id", "worker-v2"),
            ),
        )
        for command, arguments in commands:
            with self.subTest(command=command):
                process, payload = invoke(command, self.root, "--work-id", "v2-durable-controls", *arguments)
                self.assertEqual(process.stderr, "")
                self.assertEqual(
                    (process.returncode, payload.get("verdict"), payload.get("code")),
                    (2, "BLOCKED", "WORKFLOW-INCOMPATIBLE"),
                    payload,
                )
                self.assertEqual(snapshot(self.root), before)
                self.assertEqual(git(self.root, "rev-parse", "HEAD"), head_before)
                self.assertEqual(git(self.root, "branch", "--show-current"), branch_before)
                self.assertEqual(git(self.root, "status", "--porcelain=v1", "--untracked-files=all"), status_before)
                self.assertEqual(git(self.root, "worktree", "list", "--porcelain"), worktrees_before)

    def test_init_reuse_identity_conflict_and_immutable_tamper(self) -> None:
        item = self._init_item(work_id="stable-id")
        process, payload = invoke("init", self.root, "--type", "feature", "--slug", "alpha", "--work-id", "stable-id", '--skip-backlog')
        self.assertEqual((process.returncode, payload["status"]), (0, "REUSED"))
        process, payload = invoke("init", self.root, "--type", "fix", "--slug", "alpha", "--work-id", "stable-id", '--skip-backlog')
        self.assertEqual((process.returncode, payload["code"]), (2, "IDENTITY-DIVERGENCE"))
        metadata = self._metadata(item)
        metadata["immutable"]["slug"] = "tampered"
        self._write_metadata(item, metadata)
        process, payload = invoke("init", self.root, "--type", "feature", "--slug", "alpha", "--work-id", "stable-id", '--skip-backlog')
        self.assertEqual((process.returncode, payload["code"]), (2, "IMMUTABLE-TAMPERED"))

    def test_init_rejects_type_slug_and_work_id(self) -> None:
        for args in (
            ("--type", "task", "--slug", "alpha", "--work-id", "valid-id"),
            ("--type", "feature", "--slug", "../escape", "--work-id", "valid-id"),
            ("--type", "feature", "--slug", "alpha", "--work-id", "../escape"),
        ):
            process, _payload = invoke("init", self.root, *args, '--skip-backlog')
            self.assertEqual(process.returncode, 2)
    @unittest.skipUnless(SYMLINK_SUPPORTED, "symlink creation is unavailable")
    def test_init_rejects_symlink_root(self) -> None:
        outside = self._new_repo()
        (self.root / ".grill").symlink_to(outside, target_is_directory=True)
        process, payload = invoke("init", self.root, "--type", "feature", "--slug", "alpha", "--work-id", "safe-id", '--skip-backlog')
        self.assertEqual((process.returncode, payload["code"]), (2, "SYMLINK-REJECTED"))

    def test_concurrent_same_id_and_automatic_ids_do_not_corrupt(self) -> None:
        command = ("init", self.root, "--type", "feature", "--slug", "parallel", "--work-id", "parallel-id", "--skip-backlog")
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _index: invoke(*command), range(6)))
        failures = [(process.returncode, payload) for process, payload in results if process.returncode != 0]
        self.assertFalse(failures, failures)
        statuses = [payload["status"] for _process, payload in results]
        self.assertEqual(statuses.count("CREATED"), 1)
        self.assertEqual(statuses.count("REUSED"), 5)
        self.assertEqual(len(list((self.root / ".grill/work-items").glob("parallel-id"))), 1)
        automatic = [invoke("init", self.root, "--type", "fix", "--slug", "automatic", '--skip-backlog')[1]["work_id"] for _ in range(4)]
        self.assertEqual(len(set(automatic)), 4)

    def test_audit_without_constitution_is_read_only_and_uses_real_auditor(self) -> None:
        item = self._init_item()
        constitution = self.root / ".specify/memory/constitution.md"
        constitution.unlink()
        before = snapshot(item)
        process, payload = invoke("audit", self.root, "--work-id", "work-a")
        self.assertIn(process.returncode, {0, 1, 2})
        self.assertNotEqual(process.returncode, 3)
        self.assertIsNone(payload["constitutional"])
        self.assertIsInstance(payload["audit"], dict)
        self.assertEqual(before, snapshot(item))

    def test_audit_supports_artifact_root_outside_project_root(self) -> None:
        item = self._init_item(work_id="external-artifacts")
        temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.extra.append(temporary)
        external = Path(temporary.name).resolve() / "arbitrary-directory-name"
        shutil.copytree(item, external)
        before = snapshot(external)
        process, payload = invoke(
            "audit", self.root, "--artifact-root", external, "--project-root", self.root
        )
        self.assertIn(process.returncode, {0, 1, 2})
        self.assertNotEqual(process.returncode, 3)
        self.assertEqual(payload["work_id"], "external-artifacts")
        self.assertEqual(before, snapshot(external))

    def test_audit_without_work_id_or_artifact_root_is_a_named_usage_error(self) -> None:
        """A guarda tem de correr antes de montar o caminho: `root / ... / None`
        levanta TypeError, e um traceback não diz qual argumento faltou."""
        self._init_item(work_id="named-usage-error")
        process, payload = invoke("audit", self.root)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(payload["code"], "INVALID-ARGUMENTS")
        self.assertEqual(payload["verdict"], "BLOCKED")
        self.assertNotIn("Traceback", process.stderr)

    def _run_full_cycle(self, work_id: str, tag: str) -> None:
        """Drive the 11 steps to complete, using one evidence file per step."""
        evidence = Path("evidence") / f"{tag}.md"
        (self.root / evidence).parent.mkdir(parents=True, exist_ok=True)
        (self.root / evidence).write_text(f"evidencia {tag}\n", encoding="utf-8")
        for step in SEQUENCE:
            for state in ("in-progress", "complete"):
                arguments = ["checkpoint", self.root, "--work-id", work_id, "--step", step,
                             "--state", state, "--reason", f"{tag} {step}"]
                if state == "complete":
                    arguments += ["--evidence", evidence.as_posix()]
                process, payload = invoke(*arguments)
                self.assertEqual(process.returncode, 0, payload)

    def _development(self, work_id: str) -> dict:
        state = json.loads((self.root / ".grill/work-items" / work_id / "state.json").read_text(encoding="utf-8"))
        return state["development"]

    def test_phase_turn_reopens_the_matrix_and_records_the_reason(self) -> None:
        self._init_item(work_id="turning")
        self._run_full_cycle("turning", "fase-um")
        before = self._development("turning")
        self.assertTrue(all(before["steps"][s] == "complete" for s in SEQUENCE))

        process, payload = invoke("phase-turn", self.root, "--work-id", "turning",
                                  "--reason", "FASE-001 entregue, abrindo FASE-002")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "TURNED"))
        after = self._development("turning")
        self.assertTrue(all(after["steps"][s] == "pending" for s in SEQUENCE))
        self.assertEqual(after["current_step"], SEQUENCE[0])
        turn = after["audit"][-1]
        self.assertEqual((turn["step"], turn["state"]), ("phase-turn", "turned"))
        self.assertEqual(turn["reason"], "FASE-001 entregue, abrindo FASE-002")
        # O binding é específico da fase: o turn arquiva sua origem e deixa a
        # próxima fase sem binding até o novo specify canônico.
        self.assertEqual(set(after), set(before))
        self.assertIsNone(after["execution_branch"])
        self.assertEqual(turn["previous_execution_branch"], before["execution_branch"])

    def test_phase_turn_rejects_the_wrong_execution_branch_without_writing(self) -> None:
        self._init_item(work_id="wrong-turn")
        git(self.root, "checkout", "-qb", "011-gauntlet-loop")
        self._run_full_cycle("wrong-turn", "bound-cycle")
        self.assertEqual(self._development("wrong-turn")["execution_branch"], "011-gauntlet-loop")
        git(self.root, "checkout", "-qb", "wrong-branch")
        path = self.root / ".grill/work-items/wrong-turn/state.json"
        before = path.read_bytes(), path.stat().st_mtime_ns

        process, payload = invoke(
            "phase-turn", self.root, "--work-id", "wrong-turn", "--reason", "wrong checkout"
        )

        self.assertEqual(
            (process.returncode, payload["verdict"], payload["code"]),
            (2, "BLOCKED", "EXECUTION-BRANCH-MISMATCH"),
        )
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        self.assertFalse((self.root / ".grill/work-items/wrong-turn.lock").exists())

    def test_phase_turn_is_idempotent_and_writes_nothing_on_reuse(self) -> None:
        self._init_item(work_id="reuse")
        self._run_full_cycle("reuse", "ciclo")
        invoke("phase-turn", self.root, "--work-id", "reuse", "--reason", "primeira virada")
        path = self.root / ".grill/work-items/reuse/state.json"
        before = path.read_bytes()
        process, payload = invoke("phase-turn", self.root, "--work-id", "reuse", "--reason", "de novo")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "REUSED"))
        self.assertEqual(path.read_bytes(), before)

    def test_phase_turn_refuses_an_unfinished_phase_without_touching_state(self) -> None:
        self._init_item(work_id="partial")
        invoke("checkpoint", self.root, "--work-id", "partial", "--step", "specify",
               "--state", "in-progress", "--reason", "comecando")
        path = self.root / ".grill/work-items/partial/state.json"
        before = path.read_bytes()
        process, payload = invoke("phase-turn", self.root, "--work-id", "partial", "--reason", "cedo demais")
        self.assertEqual((process.returncode, payload["code"]), (2, "PHASE-INCOMPLETE"))
        self.assertIn("plan", payload["error"])
        self.assertEqual(path.read_bytes(), before)

    def test_phase_turn_requires_a_reason(self) -> None:
        self._init_item(work_id="mute")
        self._run_full_cycle("mute", "ciclo")
        path = self.root / ".grill/work-items/mute/state.json"
        before = path.read_bytes()
        process, payload = invoke("phase-turn", self.root, "--work-id", "mute", "--reason", "   ")
        self.assertEqual((process.returncode, payload["code"]), (2, "REASON-REQUIRED"))
        self.assertEqual(path.read_bytes(), before)

    def test_phase_turn_refuses_an_untracked_work_item(self) -> None:
        item = self._init_item(work_id="legacy-turn")
        state = json.loads((item / "state.json").read_text(encoding="utf-8"))
        state.pop("development", None)
        (item / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        process, payload = invoke("phase-turn", self.root, "--work-id", "legacy-turn", "--reason", "x")
        self.assertEqual((process.returncode, payload["code"]), (2, "LEGACY-UNTRACKED"))

    def _corrupt_audit(self, work_id: str) -> Path:
        path = self.root / ".grill/work-items" / work_id / "state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["development"]["audit"] = {"nao": "e lista"}
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return path

    def test_a_trail_that_is_not_a_list_is_named_not_a_traceback(self) -> None:
        """Ambos os escritores de estado tocam a trilha; nenhum pode estourar nela."""
        self._init_item(work_id="badtrail")
        self._run_full_cycle("badtrail", "ciclo")
        self._corrupt_audit("badtrail")
        process, payload = invoke("phase-turn", self.root, "--work-id", "badtrail", "--reason", "virando")
        self.assertEqual((process.returncode, payload["code"]), (2, "DEVELOPMENT-SCHEMA"))
        self.assertNotIn("Traceback", process.stderr)

    def test_checkpoint_also_names_a_trail_that_is_not_a_list(self) -> None:
        self._init_item(work_id="badtrail2")
        self._corrupt_audit("badtrail2")
        process, payload = invoke("checkpoint", self.root, "--work-id", "badtrail2", "--step", "specify",
                                  "--state", "in-progress", "--reason", "comecando")
        self.assertEqual((process.returncode, payload["code"]), (2, "DEVELOPMENT-SCHEMA"))
        self.assertNotIn("Traceback", process.stderr)

    def test_a_finished_phase_names_the_turn_instead_of_invalid_transition(self) -> None:
        """A recusa precisa ensinar: foi por não ensinar que duas fases ficaram sem trilha."""
        self._init_item(work_id="teaching")
        self._run_full_cycle("teaching", "ciclo")
        process, payload = invoke("checkpoint", self.root, "--work-id", "teaching", "--step", "specify",
                                  "--state", "in-progress", "--reason", "proxima fase")
        self.assertEqual((process.returncode, payload["code"]), (2, "PHASE-TURN-REQUIRED"))

    def test_a_genuinely_invalid_transition_still_says_so(self) -> None:
        self._init_item(work_id="skipping")
        process, payload = invoke("checkpoint", self.root, "--work-id", "skipping", "--step", "tasks",
                                  "--state", "in-progress", "--reason", "pulando specify e plan")
        self.assertEqual((process.returncode, payload["code"]), (2, "INVALID-TRANSITION"))

    def test_three_phases_leave_three_trails_in_one_work_item(self) -> None:
        self._init_item(work_id="three")
        for index, tag in enumerate(("fase-1", "fase-2", "fase-3"), start=1):
            self._run_full_cycle("three", tag)
            if index < 3:
                _, payload = invoke("phase-turn", self.root, "--work-id", "three",
                                    "--reason", f"encerrando {tag}")
                self.assertEqual(payload["verdict"], "TURNED")
        audit = self._development("three")["audit"]
        turns = [entry for entry in audit if entry["step"] == "phase-turn"]
        self.assertEqual(len(turns), 2)
        self.assertEqual([t["reason"] for t in turns], ["encerrando fase-1", "encerrando fase-2"])
        # 3 fases x 11 passos x 2 transições, mais as 2 viradas.
        self.assertEqual(len(audit), 3 * len(SEQUENCE) * 2 + 2)
        for tag in ("fase-1", "fase-2", "fase-3"):
            self.assertTrue(any(entry["reason"].startswith(tag) for entry in audit), tag)

    def test_phase_turn_refuses_to_disturb_the_global_projection(self) -> None:
        self._init_item(work_id="guarded")
        self._run_full_cycle("guarded", "ciclo")
        global_file = self.root / ".grill/global/ROADMAP.md"
        global_file.parent.mkdir(parents=True, exist_ok=True)
        global_file.write_text("# Global\n", encoding="utf-8")
        before = global_file.read_bytes()
        process, payload = invoke("phase-turn", self.root, "--work-id", "guarded", "--reason", "virando")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "TURNED"))
        self.assertEqual(global_file.read_bytes(), before)

    def test_phase_turn_refuses_a_symlinked_work_item(self) -> None:
        if not symlink_supported():
            self.skipTest("host cannot create symlinks")
        self._init_item(work_id="real-one")
        link = self.root / ".grill/work-items/linked"
        link.symlink_to(self.root / ".grill/work-items/real-one", target_is_directory=True)
        process, payload = invoke("phase-turn", self.root, "--work-id", "linked", "--reason", "x")
        self.assertEqual((process.returncode, payload["code"]), (2, "WORK-ITEM-SYMLINK"))

    def test_constitution_pass_and_not_applicable_are_accepted(self) -> None:
        self._constitution()
        item = self._init_item(work_id="constitutional")
        for status in ("PASS", "NOT-APPLICABLE"):
            self._approve_check(item, status)
            process, payload = invoke("audit", self.root, "--work-id", "constitutional")
            self.assertNotEqual(process.returncode, 3, payload)
            self.assertEqual(payload["constitutional"]["clauses"], 3)

    def test_constitution_rejects_pending_unmapped_blocked_and_violation(self) -> None:
        self._constitution()
        item = self._init_item(work_id="status-gate")
        for status in ("PENDING", "UNMAPPED", "BLOCKED", "VIOLATION"):
            value = self._approve_check(item)
            value["clauses"][0]["status"] = status
            self._write_check(item, value)
            process, payload = invoke("audit", self.root, "--work-id", "status-gate")
            self.assertEqual((process.returncode, payload["verdict"]), (3, "BLOCKED-CONSTITUTION"))

    def test_constitution_rejects_duplicate_missing_evidence_and_justification(self) -> None:
        self._constitution()
        item = self._init_item(work_id="coverage-gate")
        valid = self._approve_check(item)
        variants: list[dict] = []
        duplicate = json.loads(json.dumps(valid)); duplicate["clauses"].append(dict(duplicate["clauses"][0])); variants.append(duplicate)
        missing = json.loads(json.dumps(valid)); missing["clauses"].pop(); variants.append(missing)
        no_evidence = json.loads(json.dumps(valid)); no_evidence["clauses"][0]["evidence"] = []; variants.append(no_evidence)
        no_justification = json.loads(json.dumps(valid)); no_justification["clauses"][0]["justification"] = ""; variants.append(no_justification)
        for value in variants:
            self._write_check(item, value)
            process, _payload = invoke("audit", self.root, "--work-id", "coverage-gate")
            self.assertEqual(process.returncode, 3)

    def test_constitution_rejects_stale_hash_utf8_and_placeholders(self) -> None:
        constitution = self._constitution()
        item = self._init_item(work_id="stale-gate")
        self._approve_check(item)
        constitution.write_text(constitution.read_text(encoding="utf-8") + "\n### III. New Rule\nMUST revalidate.\n", encoding="utf-8")
        process, payload = invoke("audit", self.root, "--work-id", "stale-gate")
        self.assertEqual((process.returncode, payload["code"]), (3, "CONSTITUTION-STALE"))
        other = self._new_repo(); path = other / ".specify/memory/constitution.md"; path.parent.mkdir(parents=True); path.write_bytes(b"\xff")
        process, _payload = invoke("init", other, "--type", "feature", "--slug", "utf", "--work-id", "utf-id", '--skip-backlog')
        self.assertEqual(process.returncode, 3)
        third = self._new_repo(); path = third / ".specify/memory/constitution.md"; path.parent.mkdir(parents=True); path.write_text("# C\n## [PROJECT_PRINCIPLE]\n", encoding="utf-8")
        process, _payload = invoke("init", third, "--type", "feature", "--slug", "placeholder", "--work-id", "placeholder-id", '--skip-backlog')
        self.assertEqual(process.returncode, 3)

    def test_reconcile_source_root_and_real_qualified_ids(self) -> None:
        source = self._new_repo()
        item = self._init_item(source, "source-one")
        self._mark_complete(item)
        (item / "docs/adr/ADR-0042.md").write_text("# ADR-0042\n", encoding="utf-8")
        with (item / "ROUND-LOG.jsonl").open("a", encoding="utf-8") as handle:
            handle.write('{"round_id":"R-0042"}\n')
        process, payload = invoke("reconcile", self.root, "--source-root", source)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW"))
        for qualified in ("source-one/ADR-0042", "source-one/R-0042", "source-one/DQ-0001", "source-one/FASE-001"):
            self.assertIn(qualified, payload["qualified_ids"])
        self.assertNotIn("source-one/BL-0001", payload["qualified_ids"])
        self.assertNotIn("source-one/source-one", payload["qualified_ids"])

    def test_reconcile_source_ref_is_real_repeatable_and_read_only(self) -> None:
        item = self._init_item(work_id="ref-item")
        self._mark_complete(item)
        self._commit_all(self.root, "ref work item")
        shutil.rmtree(self.root / ".grill")
        before = git(self.root, "status", "--porcelain=v1")
        first_process, first = invoke("reconcile", self.root, "--source-ref", "HEAD")
        second_process, second = invoke("reconcile", self.root, "--source-ref", "HEAD")
        self.assertEqual((first_process.returncode, second_process.returncode), (0, 0))
        self.assertEqual(first, second)
        self.assertIn("ref-item", first["work_ids"])
        self.assertFalse((self.root / ".grill").exists())
        self.assertEqual(before, git(self.root, "status", "--porcelain=v1"))

    def test_reconcile_detects_duplicate_divergent_bundle(self) -> None:
        local = self._init_item(work_id="duplicate")
        self._mark_complete(local)
        source = self._new_repo(); remote = self._init_item(source, "duplicate"); self._mark_complete(remote)
        (remote / "ROADMAP.md").write_text("# divergent\n", encoding="utf-8")
        process, payload = invoke("reconcile", self.root, "--source-root", source)
        self.assertEqual(process.returncode, 1)
        self.assertIn("DUPLICATE-WORK-ID:duplicate", payload["conflicts"])

    def test_reconcile_detects_scope_overlap(self) -> None:
        first = self._init_item(work_id="scope-a"); second = self._init_item(work_id="scope-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("SCOPE-OVERLAP:") for conflict in payload["conflicts"]))

    def test_reconcile_detects_missing_dependency_and_cycle(self) -> None:
        missing = self._init_item(work_id="missing-dep"); self._mark_complete(missing); self._set_dependencies(missing, ["does-not-exist"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn("DEPENDENCY-MISSING:missing-dep->does-not-exist", payload["conflicts"])
        shutil.rmtree(self.root / ".grill")
        first = self._init_item(work_id="cycle-a"); second = self._init_item(work_id="cycle-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_dependencies(first, ["cycle-b"]); self._set_dependencies(second, ["cycle-a"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("DEPENDENCY-CYCLE:") for conflict in payload["conflicts"]))

    def test_reconcile_detects_adr_conflict_invalid_state_and_constitution_stale(self) -> None:
        owner = self._init_item(work_id="adr-owner"); consumer = self._init_item(work_id="adr-consumer", slug="consumer")
        for item in (owner, consumer): self._mark_complete(item)
        (owner / "docs/adr/ADR-0099.md").write_text("# ADR-0099\n", encoding="utf-8")
        self._set_adr_conflicts(consumer, ["adr-owner/ADR-0099"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn("ADR-CONFLICT:adr-consumer->adr-owner/ADR-0099", payload["conflicts"])
        state = json.loads((owner / "state.json").read_text(encoding="utf-8")); state["status"] = "in-progress"; (owner / "state.json").write_text(json.dumps(state), encoding="utf-8")
        process, payload = invoke("reconcile", self.root)
        self.assertIn("STATE-NOT-RECONCILABLE:adr-owner", payload["conflicts"])
        self._mark_complete(owner); self._constitution()
        process, payload = invoke("reconcile", self.root)
        self.assertTrue(any(conflict.startswith("CONSTITUTION-STALE:") for conflict in payload["conflicts"]))

    def test_reconcile_requires_terminal_milestone_contract(self) -> None:
        item = self._init_item(work_id="terminal-contract")
        state_path = item / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.update(status="complete", audit_verdict="GO")
        state.pop("milestone_status", None)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn("STATE-NOT-RECONCILABLE:terminal-contract", payload["conflicts"])

        self._mark_complete(item)
        roadmap = item / "ROADMAP.md"
        roadmap.write_text(roadmap.read_text(encoding="utf-8").replace("- state: complete", "- state: ready-for-specify", 1), encoding="utf-8")
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn("ROADMAP-NOT-TERMINAL:terminal-contract", payload["conflicts"])

        self._mark_complete(item)
        process, payload = invoke("reconcile", self.root)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW"))

    def test_reconcile_apply_rejects_wrong_branch_and_dirty_tree(self) -> None:
        item = self._init_item(); self._mark_complete(item); self._commit_all(self.root)
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "wrong")
        self.assertEqual((process.returncode, payload["code"]), (2, "WRONG-INTEGRATION-BRANCH"))
        (self.root / "dirty.txt").write_text("dirty", encoding="utf-8")
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["code"]), (2, "DIRTY-WORKTREE"))

    def test_reconcile_apply_is_byte_idempotent_without_mtime_churn(self) -> None:
        item = self._init_item(); self._mark_complete(item); self._commit_all(self.root)
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        global_dir = self.root / ".grill/global"
        before = snapshot(global_dir); before_mtime = {path.name: path.stat().st_mtime_ns for path in global_dir.iterdir()}
        time.sleep(0.02)
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "REUSED"))
        self.assertEqual(before, snapshot(global_dir))
        self.assertEqual(before_mtime, {path.name: path.stat().st_mtime_ns for path in global_dir.iterdir()})
        self.assertNotIn(b"\\n", (global_dir / "ROADMAP.md").read_bytes())

    def test_targeted_reconcile_admits_terminal_target_beside_pending_sibling(self) -> None:
        target = self._init_item(work_id="target"); self._mark_complete(target)
        self._init_item(work_id="pending", slug="pending")
        self._commit_all(self.root)
        process, payload = invoke("reconcile", self.root, "--work-id", "target", "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        self.assertEqual([p.name for p in (self.root / ".grill/global/receipts").iterdir()], ["target.json"])

    def test_targeted_reconcile_rejects_pending_target_and_unreceived_dependency(self) -> None:
        pending = self._init_item(work_id="pending")
        process, payload = invoke("reconcile", self.root, "--work-id", "pending")
        self.assertEqual(process.returncode, 1); self.assertIn("STATE-NOT-RECONCILABLE", payload["code"])
        target = self._init_item(work_id="dependent", slug="dependent"); self._mark_complete(target); self._set_dependencies(target, ["missing"])
        process, payload = invoke("reconcile", self.root, "--work-id", "dependent")
        self.assertEqual(process.returncode, 1); self.assertTrue(any(c.startswith("DEPENDENCY-NOT-RECONCILED:") for c in payload["conflicts"]))

    def test_targeted_reconcile_rejects_scope_and_adr_against_receipt(self) -> None:
        owner = self._init_item(work_id="owner"); self._mark_complete(owner); self._set_scope(owner, ["src/api"]); self._commit_all(self.root)
        process, _ = invoke("reconcile", self.root, "--work-id", "owner", "--apply", "--integration-branch", "main"); self.assertEqual(process.returncode, 0)
        consumer = self._init_item(work_id="consumer", slug="consumer"); self._mark_complete(consumer); self._set_scope(consumer, ["src/api/x.py"]); self._set_adr_conflicts(consumer, ["owner/ADR-1"])
        process, payload = invoke("reconcile", self.root, "--work-id", "consumer")
        self.assertEqual(process.returncode, 1); self.assertTrue(any("SCOPE-OVERLAP" in c or "ADR-CONFLICT" in c for c in payload["conflicts"]))

    def test_targeted_preview_is_read_only_and_parser_exposes_work_id(self) -> None:
        item = self._init_item(work_id="preview"); self._mark_complete(item); before = snapshot(self.root)
        process, payload = invoke("reconcile", self.root, "--work-id", "preview")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW")); self.assertEqual(before, snapshot(self.root))
        module = load_workspace_module(); self.assertIn("work_id", vars(module.build_parser().parse_args(["reconcile", str(self.root)])))

    def test_targeted_apply_blocks_legacy_global_and_full_apply_never_drops_receipts(self) -> None:
        item = self._init_item(work_id="legacy"); self._mark_complete(item); self._commit_all(self.root)
        (self.root / ".grill/global").mkdir(parents=True); (self.root / ".grill/global/ROADMAP.md").write_text("legacy\n"); (self.root / ".grill/global/AUDIT.md").write_text("legacy\n")
        process, payload = invoke("reconcile", self.root, "--work-id", "legacy", "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["code"]), (2, "GLOBAL-BASELINE-UNVERIFIED"))

    def test_receipt_reapply_is_reused_without_mtime_churn(self) -> None:
        item = self._init_item(work_id="reuse"); self._mark_complete(item); self._commit_all(self.root)
        args = ("reconcile", self.root, "--work-id", "reuse", "--apply", "--integration-branch", "main")
        first, p1 = invoke(*args); self.assertEqual(p1["verdict"], "APPLIED"); receipt = self.root / ".grill/global/receipts/reuse.json"; mtime = receipt.stat().st_mtime_ns
        time.sleep(.02); second, p2 = invoke(*args); self.assertEqual((second.returncode, p2["verdict"]), (0, "REUSED")); self.assertEqual(receipt.stat().st_mtime_ns, mtime)

    def test_targeted_concurrent_distinct_receipts_are_preserved(self) -> None:
        first = self._init_item(work_id="race-a"); second = self._init_item(work_id="race-b", slug="race-b")
        self._mark_complete(first); self._mark_complete(second); self._commit_all(self.root)
        commands = [("reconcile", self.root, "--work-id", work_id, "--apply", "--integration-branch", "main") for work_id in ("race-a", "race-b")]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda command: invoke(*command), commands))
        self.assertTrue(all(process.returncode == 0 for process, _payload in results))
        self.assertEqual({path.name for path in (self.root / ".grill/global/receipts").iterdir()}, {"race-a.json", "race-b.json"})
        roadmap = (self.root / ".grill/global/ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("race-a", roadmap); self.assertIn("race-b", roadmap)

    def test_broken_receipts_symlink_is_rejected(self) -> None:
        receipts = self.root / ".grill/global/receipts"; receipts.parent.mkdir(parents=True)
        receipts.symlink_to("missing-receipts", target_is_directory=True)
        process, payload = invoke("reconcile", self.root)
        self.assertEqual((process.returncode, payload["code"]), (2, "SYMLINK-REJECTED"))

    def test_targeted_apply_releases_lock_when_receipt_is_invalid(self) -> None:
        item = self._init_item(work_id="receipt-lock"); self._mark_complete(item); self._commit_all(self.root)
        receipts = self.root / ".grill/global/receipts"; receipts.mkdir(parents=True)
        (receipts / "broken.json").write_text("{invalid", encoding="utf-8")
        process, payload = invoke("reconcile", self.root, "--work-id", "receipt-lock", "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["code"]), (2, "RECEIPT-INVALID"))
        self.assertFalse((self.root / ".grill/locks/global-reconciliation.lock").exists())

    def test_reconcile_succession_targeted_dependency_authorizes_scope_overlap(self) -> None:
        owner = self._init_item(work_id="owner"); self._mark_complete(owner); self._set_scope(owner, ["src/api"]); self._commit_all(self.root)
        process, _payload = invoke("reconcile", self.root, "--work-id", "owner", "--apply", "--integration-branch", "main")
        self.assertEqual(process.returncode, 0)
        successor = self._init_item(work_id="successor", slug="successor"); self._mark_complete(successor)
        self._set_scope(successor, ["src/api/x.py"]); self._set_dependencies(successor, ["owner"])
        # Commit before --apply: a dirty tree is refused as DIRTY-WORKTREE long
        # before the scope rule is consulted, so without this the case proves
        # nothing about succession.
        self._commit_all(self.root, "successor work item")
        process, payload = invoke("reconcile", self.root, "--work-id", "successor", "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        self.assertEqual(payload["conflicts"], [])

    def test_reconcile_succession_full_dependency_authorizes_scope_overlap_both_directions(self) -> None:
        first = self._init_item(work_id="succ-a"); second = self._init_item(work_id="succ-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"])
        self._set_dependencies(second, ["succ-a"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW"))
        self.assertFalse(any(conflict.startswith("SCOPE-OVERLAP") for conflict in payload["conflicts"]))

        shutil.rmtree(self.root / ".grill")
        first = self._init_item(work_id="succ-a"); second = self._init_item(work_id="succ-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"])
        self._set_dependencies(first, ["succ-b"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW"))
        self.assertFalse(any(conflict.startswith("SCOPE-OVERLAP") for conflict in payload["conflicts"]))

    def test_reconcile_succession_negative_cases_still_flag_scope_overlap(self) -> None:
        # No dependency at all: overlap stays fail-closed.
        first = self._init_item(work_id="scope-a"); second = self._init_item(work_id="scope-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("SCOPE-OVERLAP:") for conflict in payload["conflicts"]))

        # A dependency on an unrelated third work item does not authorize the pair.
        shutil.rmtree(self.root / ".grill")
        first = self._init_item(work_id="scope-a"); second = self._init_item(work_id="scope-b", slug="beta")
        third = self._init_item(work_id="scope-c", slug="gamma")
        for item in (first, second, third): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"])
        self._set_dependencies(first, ["scope-c"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("SCOPE-OVERLAP:") for conflict in payload["conflicts"]))

        # A transitive chain A->B->C never authorizes the A<->C overlap.
        shutil.rmtree(self.root / ".grill")
        first = self._init_item(work_id="chain-a"); second = self._init_item(work_id="chain-b", slug="beta")
        third = self._init_item(work_id="chain-c", slug="gamma")
        for item in (first, second, third): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(third, ["src/service/api.py"])
        self._set_dependencies(first, ["chain-b"]); self._set_dependencies(second, ["chain-c"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("SCOPE-OVERLAP:") for conflict in payload["conflicts"]))

    def test_reconcile_succession_preserves_full_path_refusals(self) -> None:
        # Malformed depends-on-work grants no authorization: overlap stays flagged too.
        first = self._init_item(work_id="schema-a"); second = self._init_item(work_id="schema-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"])
        value = self._metadata(first); value["depends-on-work"] = "schema-b"; self._write_metadata(first, value)
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn("DEPENDENCY-SCHEMA:schema-a", payload["conflicts"])
        self.assertTrue(any(conflict.startswith("SCOPE-OVERLAP:") for conflict in payload["conflicts"]))

        shutil.rmtree(self.root / ".grill")
        missing = self._init_item(work_id="missing-dep"); self._mark_complete(missing); self._set_dependencies(missing, ["does-not-exist"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn("DEPENDENCY-MISSING:missing-dep->does-not-exist", payload["conflicts"])

        # Cycle detection is a full-path invariant untouched by direct-dependency authorization.
        shutil.rmtree(self.root / ".grill")
        first = self._init_item(work_id="cycle-a"); second = self._init_item(work_id="cycle-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_dependencies(first, ["cycle-b"]); self._set_dependencies(second, ["cycle-a"])
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("DEPENDENCY-CYCLE:") for conflict in payload["conflicts"]))

    def test_reconcile_succession_preserves_targeted_path_refusals(self) -> None:
        target = self._init_item(work_id="dependent"); self._mark_complete(target); self._set_dependencies(target, ["missing"])
        process, payload = invoke("reconcile", self.root, "--work-id", "dependent")
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("DEPENDENCY-NOT-RECONCILED:") for conflict in payload["conflicts"]))

        shutil.rmtree(self.root / ".grill")
        self_dep = self._init_item(work_id="self-dep"); self._mark_complete(self_dep); self._set_dependencies(self_dep, ["self-dep"])
        process, payload = invoke("reconcile", self.root, "--work-id", "self-dep")
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("DEPENDENCY-SELF:") for conflict in payload["conflicts"]))

        # A direct dependency authorizes the scope overlap but never waives ADR-CONFLICT.
        shutil.rmtree(self.root / ".grill")
        owner = self._init_item(work_id="owner"); self._mark_complete(owner); self._set_scope(owner, ["src/api"])
        (owner / "docs/adr/ADR-0001.md").write_text("# ADR-0001\n", encoding="utf-8")
        self._commit_all(self.root)
        process, _payload = invoke("reconcile", self.root, "--work-id", "owner", "--apply", "--integration-branch", "main")
        self.assertEqual(process.returncode, 0)
        consumer = self._init_item(work_id="consumer", slug="consumer"); self._mark_complete(consumer)
        self._set_scope(consumer, ["src/api/x.py"]); self._set_adr_conflicts(consumer, ["owner/ADR-0001"]); self._set_dependencies(consumer, ["owner"])
        process, payload = invoke("reconcile", self.root, "--work-id", "consumer")
        self.assertEqual(process.returncode, 1)
        self.assertFalse(any(conflict.startswith("SCOPE-OVERLAP") for conflict in payload["conflicts"]))
        self.assertIn("ADR-CONFLICT:consumer->owner/ADR-0001", payload["conflicts"])

    def test_reconcile_succession_multi_id_dependency_authorizes_only_the_declared_prior(self) -> None:
        """A multi-id list authorizes the prior it names, and only that one.

        The contract says the target must declare *exactly* the prior whose
        receipt overlaps. With a single-id list that is indistinguishable from
        "declares anything at all", so the discriminating case is a list that
        names several ids: it must authorize when the prior is among them and
        refuse when it is not.
        """
        owner = self._init_item(work_id="owner"); self._mark_complete(owner); self._set_scope(owner, ["src/api"])
        self._commit_all(self.root)
        process, _payload = invoke("reconcile", self.root, "--work-id", "owner", "--apply", "--integration-branch", "main")
        self.assertEqual(process.returncode, 0)
        successor = self._init_item(work_id="successor", slug="successor"); self._mark_complete(successor)
        self._set_scope(successor, ["src/api/x.py"])
        self._set_dependencies(successor, ["owner", "unrelated-one", "unrelated-two"])
        self._commit_all(self.root, "successor declaring several dependencies")
        process, payload = invoke("reconcile", self.root, "--work-id", "successor")
        self.assertEqual((process.returncode, payload["verdict"]), (1, "NO-GO"))
        self.assertFalse(any(conflict.startswith("SCOPE-OVERLAP") for conflict in payload["conflicts"]))
        # The two undeclared-elsewhere ids are still unreconciled dependencies;
        # authorizing the overlap never waives that.
        self.assertIn("DEPENDENCY-NOT-RECONCILED:successor->unrelated-one", payload["conflicts"])

        # Control: the same multi-id shape without the prior authorizes nothing.
        self._set_dependencies(successor, ["unrelated-one", "unrelated-two"])
        self._commit_all(self.root, "successor no longer declaring the prior")
        process, payload = invoke("reconcile", self.root, "--work-id", "successor")
        self.assertEqual(process.returncode, 1)
        self.assertTrue(any(conflict.startswith("SCOPE-OVERLAP:successor:") for conflict in payload["conflicts"]))

    def test_reconcile_succession_full_apply_is_byte_idempotent_with_authorized_overlap(self) -> None:
        """The full path keeps atomicity and idempotence once an overlap is authorized.

        The pre-existing idempotence case has no overlap at all, and the
        succession idempotence case is targeted-only; neither exercises the full
        path with the rule actually firing, which is what FR-008 makes symmetric.
        """
        first = self._init_item(work_id="succ-a"); second = self._init_item(work_id="succ-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"])
        self._set_dependencies(second, ["succ-a"])
        self._commit_all(self.root)
        args = ("reconcile", self.root, "--apply", "--integration-branch", "main")
        process, payload = invoke(*args)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        self.assertFalse(any(conflict.startswith("SCOPE-OVERLAP") for conflict in payload["conflicts"]))
        global_dir = self.root / ".grill/global"
        before = snapshot(global_dir)
        before_mtime = {path.name: path.stat().st_mtime_ns for path in global_dir.iterdir()}
        time.sleep(.02)
        process, payload = invoke(*args)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "REUSED"))
        self.assertEqual(snapshot(global_dir), before)
        self.assertEqual(before_mtime, {path.name: path.stat().st_mtime_ns for path in global_dir.iterdir()})

    def test_reconcile_succession_preview_is_read_only_with_authorized_overlap(self) -> None:
        first = self._init_item(work_id="succ-a"); second = self._init_item(work_id="succ-b", slug="beta")
        for item in (first, second): self._mark_complete(item)
        self._set_scope(first, ["src/service"]); self._set_scope(second, ["src/service/api.py"]); self._set_dependencies(second, ["succ-a"])
        before = snapshot(self.root)
        process, payload = invoke("reconcile", self.root)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW"))
        self.assertFalse(any(conflict.startswith("SCOPE-OVERLAP") for conflict in payload["conflicts"]))
        self.assertEqual(before, snapshot(self.root))

    def test_reconcile_succession_targeted_apply_is_byte_idempotent_and_reuses_prior_receipt(self) -> None:
        owner = self._init_item(work_id="owner"); self._mark_complete(owner); self._set_scope(owner, ["src/api"]); self._commit_all(self.root)
        process, _payload = invoke("reconcile", self.root, "--work-id", "owner", "--apply", "--integration-branch", "main")
        self.assertEqual(process.returncode, 0)
        owner_receipt = self.root / ".grill/global/receipts/owner.json"; owner_receipt_before = owner_receipt.read_bytes()
        successor = self._init_item(work_id="successor", slug="successor"); self._mark_complete(successor)
        self._set_scope(successor, ["src/api/x.py"]); self._set_dependencies(successor, ["owner"]); self._commit_all(self.root, "successor work item")
        args = ("reconcile", self.root, "--work-id", "successor", "--apply", "--integration-branch", "main")
        first, p1 = invoke(*args)
        self.assertEqual((first.returncode, p1["verdict"]), (0, "APPLIED"))
        # The owner receipt written before this succession was reconciled is read as-is, byte for byte.
        self.assertEqual(owner_receipt.read_bytes(), owner_receipt_before)
        successor_receipt = self.root / ".grill/global/receipts/successor.json"; mtime = successor_receipt.stat().st_mtime_ns
        before = snapshot(self.root / ".grill/global")
        time.sleep(.02)
        second, p2 = invoke(*args)
        self.assertEqual((second.returncode, p2["verdict"]), (0, "REUSED"))
        self.assertEqual(successor_receipt.stat().st_mtime_ns, mtime)
        self.assertEqual(snapshot(self.root / ".grill/global"), before)

    def test_full_apply_blocks_before_dropping_existing_receipts(self) -> None:
        item = self._init_item(work_id="full-safe"); self._mark_complete(item); self._commit_all(self.root)
        process, _payload = invoke("reconcile", self.root, "--work-id", "full-safe", "--apply", "--integration-branch", "main")
        self.assertEqual(process.returncode, 0)
        receipt = self.root / ".grill/global/receipts/full-safe.json"; before = receipt.read_bytes()
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["code"]), (2, "RECEIPTS-WOULD-BE-DROPPED"))
        self.assertEqual(before, receipt.read_bytes())

    def test_full_apply_receipt_guard_runs_under_released_lock(self) -> None:
        item = self._init_item(work_id="lock-safe"); self._mark_complete(item); self._commit_all(self.root)
        first, _payload = invoke("reconcile", self.root, "--work-id", "lock-safe", "--apply", "--integration-branch", "main")
        self.assertEqual(first.returncode, 0)
        receipt = self.root / ".grill/global/receipts/lock-safe.json"; before = receipt.read_bytes()
        process, payload = invoke("reconcile", self.root, "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["code"]), (2, "RECEIPTS-WOULD-BE-DROPPED"))
        self.assertEqual(before, receipt.read_bytes())
        self.assertFalse((self.root / ".grill/locks/global-reconciliation.lock").exists())

    def test_reconcile_concurrent_apply_is_serialized(self) -> None:
        item = self._init_item(); self._mark_complete(item); self._commit_all(self.root)
        command = ("reconcile", self.root, "--apply", "--integration-branch", "main")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _index: invoke(*command), range(4)))
        self.assertTrue(all(process.returncode == 0 for process, _payload in results))
        verdicts = [payload["verdict"] for _process, payload in results]
        self.assertEqual(verdicts.count("APPLIED"), 1)
        self.assertEqual(verdicts.count("REUSED"), 3)
        self.assertEqual(set(snapshot(self.root / ".grill/global")), {"AUDIT.md", "ROADMAP.md"})

    @unittest.skipUnless(sys.platform.startswith("linux"), "requires Linux /proc process identity")
    def test_reconcile_concurrent_waiters_recover_one_orphan_lock(self) -> None:
        item = self._init_item(); self._mark_complete(item); self._commit_all(self.root)
        lock = self.root / ".grill/locks/global-reconciliation.lock"
        lock.mkdir(parents=True)
        (lock / "owner.json").write_text(
            json.dumps({"pid": 999_999_999, "host": socket.gethostname(), "process_start": "linux:0"}),
            encoding="utf-8",
        )
        command = ("reconcile", self.root, "--apply", "--integration-branch", "main")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _index: invoke(*command), range(4)))
        self.assertTrue(all(process.returncode == 0 for process, _payload in results))
        verdicts = [payload["verdict"] for _process, payload in results]
        self.assertEqual(verdicts.count("APPLIED"), 1)
        self.assertEqual(verdicts.count("REUSED"), 3)
        self.assertFalse(lock.exists())

    def test_unavailable_process_identity_never_marks_live_lock_stale(self) -> None:
        module = load_workspace_module()
        lock = self.root / "identity.lock"
        lock.mkdir()
        (lock / "owner.json").write_text(
            json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "process_start": "linux:recorded"}),
            encoding="utf-8",
        )
        original = getattr(module, "process_start_observation")
        try:
            setattr(module, "process_start_observation", lambda _pid: ("unavailable", None))
            self.assertFalse(module.stale_local_lock(lock))
            setattr(module, "process_start_observation", lambda _pid: ("found", "linux:reused"))
            self.assertTrue(module.stale_local_lock(lock))
        finally:
            setattr(module, "process_start_observation", original)
            sys.modules.pop("grill_workspace_contract_module", None)

    def test_migrate_preview_apply_preserves_files_directories_and_reuses(self) -> None:
        originals = {
            "CONTEXT.md": b"legacy context\n",
            "ROADMAP.md": b"legacy roadmap\n",
            "docs/adr/ADR-0001.md": b"adr one\n",
            "adrs/ADR-0002.md": b"adr two\n",
            "handoffs/FASE-001.md": b"handoff\n",
        }
        for relative, data in originals.items():
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        process, payload = invoke("migrate", self.root, "--type", "feature", "--slug", "legacy", "--work-id", "migration")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "PREVIEW"))
        self.assertFalse((self.root / ".grill").exists())
        process, payload = invoke("migrate", self.root, "--type", "feature", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        item = self.root / ".grill/work-items/migration"
        expected_destinations = {
            "CONTEXT.md": originals["CONTEXT.md"],
            "ROADMAP.md": originals["ROADMAP.md"],
            "docs/adr/ADR-0001.md": originals["docs/adr/ADR-0001.md"],
            "docs/adr/ADR-0002.md": originals["adrs/ADR-0002.md"],
            "handoffs/FASE-001.md": originals["handoffs/FASE-001.md"],
        }
        for relative, data in expected_destinations.items():
            self.assertEqual((item / relative).read_bytes(), data)
        for relative, data in originals.items():
            self.assertEqual((self.root / relative).read_bytes(), data)
        process, payload = invoke("migrate", self.root, "--type", "feature", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "REUSED"))

    def test_migrate_blocks_divergence_and_invalid_utf8_without_partial_target(self) -> None:
        (self.root / "CONTEXT.md").write_text("legacy\n", encoding="utf-8")
        process, _payload = invoke("migrate", self.root, "--type", "fix", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual(process.returncode, 0)
        (self.root / ".grill/work-items/migration/CONTEXT.md").write_text("diverged\n", encoding="utf-8")
        process, payload = invoke("migrate", self.root, "--type", "fix", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual((process.returncode, payload["code"]), (2, "TARGET-DIVERGES"))
        invalid = self._new_repo(); (invalid / "CONTEXT.md").write_bytes(b"\xff")
        process, _payload = invoke("migrate", invalid, "--type", "fix", "--slug", "utf", "--work-id", "utf-migration", "--apply")
        self.assertEqual(process.returncode, 1)
        self.assertFalse((invalid / ".grill/work-items/utf-migration").exists())
    @unittest.skipUnless(SYMLINK_SUPPORTED, "symlink creation is unavailable")
    def test_migrate_blocks_symlink_without_partial_target(self) -> None:
        linked = self._new_repo(); target = linked / "actual.md"; target.write_text("actual", encoding="utf-8"); (linked / "CONTEXT.md").symlink_to(target)
        process, _payload = invoke("migrate", linked, "--type", "fix", "--slug", "link", "--work-id", "link-migration", "--apply")
        self.assertEqual(process.returncode, 2)
        self.assertFalse((linked / ".grill/work-items/link-migration").exists())

    def test_core_validation_rejects_invalid_metadata_migration_and_adr_reference(self) -> None:
        item = self._init_item(work_id="validation")
        metadata = self._metadata(item)
        metadata["immutable"]["type"] = "task"
        metadata["immutable_sha256"] = "bad"
        self._write_metadata(item, metadata)
        process, payload = invoke("reconcile", self.root)
        self.assertEqual(process.returncode, 2)
        self.assertIn(payload["code"], {"IMMUTABLE-TAMPERED", "METADATA-SCHEMA"})

        other = self._new_repo()
        (other / "CONTEXT.md").write_text("legacy\n", encoding="utf-8")
        process, _payload = invoke("migrate", other, "--type", "feature", "--slug", "legacy", "--work-id", "migration", "--apply")
        self.assertEqual(process.returncode, 0)
        migrated = other / ".grill/work-items/migration/WORK-ITEM.json"
        value = json.loads(migrated.read_text(encoding="utf-8"))
        value["migration"]["source_hashes"]["CONTEXT.md"] = "not-a-sha256"
        migrated.write_text(json.dumps(value), encoding="utf-8")
        process, payload = invoke("reconcile", other)
        self.assertEqual((process.returncode, payload["code"]), (2, "MIGRATION-SCHEMA"))

    def test_constitution_repeated_headings_get_unique_ids(self) -> None:
        constitution = self._constitution()
        constitution.write_text("# C\n## Rules\na\n## Rules\nb\n## Rules\nc\n", encoding="utf-8")
        process, payload = invoke("init", self.root, "--type", "feature", "--slug", "repeat", "--work-id", "repeat", '--skip-backlog')
        self.assertEqual(process.returncode, 0, payload)
        check = self._read_check(self.root / ".grill/work-items/repeat")
        self.assertEqual([entry["id"] for entry in check["clauses"]], ["rules", "rules-2", "rules-3"])

    def test_migrate_does_not_replace_generated_state(self) -> None:
        (self.root / "state.json").write_text('{"status":"legacy"}\n', encoding="utf-8")
        arguments = ("migrate", self.root, "--type", "fix", "--slug", "state", "--work-id", "state-migration", "--apply")
        process, payload = invoke(*arguments)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        target = self.root / ".grill/work-items/state-migration/state.json"
        state = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(state["work_id"], "state-migration")
        self.assertEqual(state["workflow"]["schema"], "v2")
        generated = target.read_bytes()
        process, payload = invoke(*arguments)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "REUSED"))
        self.assertEqual(target.read_bytes(), generated)
        self.assertIn("constitution", state)

    @unittest.skipUnless(SYMLINK_SUPPORTED, "symlink creation is unavailable")
    def test_migrate_rejects_broken_file_and_directory_symlinks(self) -> None:
        broken_file = self._new_repo()
        (broken_file / "CONTEXT.md").symlink_to(broken_file / "does-not-exist")
        process, payload = invoke(
            "migrate", broken_file, "--type", "fix", "--slug", "broken", "--work-id", "broken-file", "--apply"
        )
        self.assertEqual((process.returncode, payload["code"]), (2, "LEGACY-SYMLINK"))
        self.assertFalse((broken_file / ".grill/work-items/broken-file").exists())
        broken_directory = self._new_repo()
        (broken_directory / "docs").mkdir()
        (broken_directory / "docs/adr").symlink_to(broken_directory / "missing-directory", target_is_directory=True)
        process, payload = invoke(
            "migrate", broken_directory, "--type", "fix", "--slug", "broken", "--work-id", "broken-dir", "--apply"
        )
        self.assertEqual((process.returncode, payload["code"]), (2, "LEGACY-SYMLINK"))
        self.assertFalse((broken_directory / ".grill/work-items/broken-dir").exists())


    def test_hotfix_fast_is_self_contained_and_feature_remains_plan_only(self) -> None:
        args = ("hotfix", self.root, "--slug", "incident", "--scope", "src/auth.py",
                "--reproduction", "curl /login => 500", "--evidence", "incident.log",
                "--correction-test", "tests/auth.py::test_timeout", "--rollback", "revert abc",
                "--constitution-evidence", "not-applicable", "--test-command", python_test_command("pass"),
                "--work-id", "hotfix-incident")
        process, payload = invoke(*args)
        self.assertEqual((process.returncode, payload["verdict"]), (0, "HOTFIX-PREPARED"))
        item = self.root / ".grill/work-items/hotfix-incident"
        self.assertTrue((item / "HOTFIX.md").is_file())
        audit, audited = invoke("audit", self.root, "--work-id", "hotfix-incident")
        self.assertEqual((audit.returncode, audited["verdict"]), (0, "HOTFIX-PREPARED"))
        go, released = invoke("hotfix-go", self.root, "--work-id", "hotfix-incident")
        self.assertEqual((go.returncode, released["verdict"]), (0, "HOTFIX-GO"))
        self.assertFalse((self.root / ".grill/global").exists())
        bad, bad_payload = invoke("hotfix", self.root, "--slug", "bad", "--scope", "../escape",
                                  "--reproduction", "r", "--evidence", "e", "--correction-test", "t",
                                  "--rollback", "b", "--constitution-evidence", "c", "--test-command", "true")
        self.assertEqual((bad.returncode, bad_payload["code"]), (1, "SCOPE-NOT-CLOSED"))


    def test_hotfix_fast_rejects_failed_test_timeout_and_tampered_bundle(self) -> None:
        base = ("hotfix", self.root, "--slug", "failure", "--scope", "src/api.py",
                "--reproduction", "500", "--evidence", "incident.log", "--correction-test", "tests/test_api.py",
                "--rollback", "git revert", "--constitution-evidence", "not-applicable", "--work-id", "hotfix-failure")
        failed, _ = invoke(*base, "--test-command", python_test_command("import sys; sys.exit(7)"))
        self.assertEqual(failed.returncode, 0)
        go_failed, failed_payload = invoke("hotfix-go", self.root, "--work-id", "hotfix-failure")
        self.assertEqual((go_failed.returncode, failed_payload["code"]), (1, "CORRECTION-TEST-FAILED"))
        timeout_root = self._new_repo()
        timeout, _ = invoke("hotfix", timeout_root, "--slug", "timeout", "--scope", "src/timeout.py",
                            "--reproduction", "500", "--evidence", "incident.log", "--correction-test", "tests/test_timeout.py",
                            "--rollback", "git revert", "--constitution-evidence", "not-applicable", "--work-id", "hotfix-timeout",
                            "--test-command", python_test_command("import time; time.sleep(2)"), "--test-timeout", "1")
        self.assertEqual(timeout.returncode, 0)
        go_timeout, timeout_payload = invoke("hotfix-go", timeout_root, "--work-id", "hotfix-timeout")
        self.assertEqual((go_timeout.returncode, timeout_payload["code"]), (1, "CORRECTION-TEST-TIMEOUT"))
        newline, newline_payload = invoke("hotfix", self.root, "--slug", "newline", "--scope", "src/api.py\nother.py",
                                          "--reproduction", "500", "--evidence", "incident.log", "--correction-test", "t",
                                          "--rollback", "git revert", "--constitution-evidence", "not-applicable", "--test-command", "true")
        self.assertEqual((newline.returncode, newline_payload["code"]), (1, "SCOPE-NOT-CLOSED"))
        item = self.root / ".grill/work-items/hotfix-failure/WORK-ITEM.json"
        data = json.loads(item.read_text(encoding="utf-8"))
        data["hotfix"]["test-command"] = python_test_command("pass")
        item.write_text(json.dumps(data), encoding="utf-8")
        tampered, tampered_payload = invoke("hotfix-go", self.root, "--work-id", "hotfix-failure")
        self.assertEqual((tampered.returncode, tampered_payload["code"]), (2, "HOTFIX-METADATA-TAMPERED"))

    def test_v23_decomposition_persistence_and_hotfix_exclusion(self) -> None:
        for kind, work_id in (("feature", "decomp-feature"), ("fix", "decomp-fix")):
            item = self._init_item(work_id=work_id, kind=kind, slug=work_id)
            self.assertTrue((item / "DELIVERY-MAP.md").is_file())
            self.assertEqual(self._metadata(item)["capability"], {"name": "module-decomposition", "version": "v1", "schema": "v1"})
        args = ("hotfix", self.root, "--slug", "incident", "--scope", "src/a.py", "--reproduction", "r", "--evidence", "e", "--correction-test", "t", "--rollback", "b", "--constitution-evidence", "not-applicable", "--test-command", python_test_command("pass"), "--work-id", "decomp-hotfix")
        process, _ = invoke(*args)
        self.assertEqual(process.returncode, 0)
        hotfix = self.root / ".grill/work-items/decomp-hotfix"
        self.assertFalse((hotfix / "DELIVERY-MAP.md").exists())
        self.assertNotIn("capability", self._metadata(hotfix))

    def _valid_v23_item(self, work_id: str = "matrix") -> Path:
        item = self._init_item(work_id=work_id)
        (item / "CONTEXT.md").write_text("# Context\n\n| Termo canônico | Definição |\n|---|---|\n| API | Contrato externo |\n", encoding="utf-8")
        frontier = item / "DECISION-FRONTIER.md"
        frontier.write_text(frontier.read_text(encoding="utf-8").replace("- state: open", "- state: resolved"), encoding="utf-8")
        (item / "DELIVERY-MAP.md").write_text("""# DELIVERY-MAP\n\ndecomposition-schema: v1\n\n## MOD-001 — Web delivery\n- module-kind: cross-cutting\n- responsibility: Deliver the web contract\n- boundary: Browser and API boundary\n- depends-on: none\n\n### DU-001 — Frontend\n- development-type: frontend\n- phase: FASE-001\n- scope-in: Browser UI\n- scope-out: Backend internals\n- depends-on: none\n- acceptance: frontend contract\n\n### DU-002 — Backend\n- development-type: backend\n- phase: FASE-001\n- scope-in: HTTP API\n- scope-out: Browser rendering\n- depends-on: none\n- acceptance: backend contract\n\n### DU-003 — IaC\n- development-type: infra-iac\n- phase: FASE-001\n- scope-in: Deployment resources\n- scope-out: Product behavior\n- depends-on: none\n- acceptance: IaC contract\n""", encoding="utf-8")
        (item / "ROADMAP.md").write_text((item / "ROADMAP.md").read_text(encoding="utf-8").replace("<!-- nome estável da fase -->", "Web delivery").replace("planned", "ready-for-specify").replace("<!-- resultado observável -->", "Ship the web contract").replace("<!-- incluído -->", "Web stack").replace("<!-- excluído -->", "Future work").replace("<!-- termos canônicos de CONTEXT.md -->", "API").replace("- delivery-units: DU-001", "- delivery-units: DU-001, DU-002, DU-003"), encoding="utf-8")
        handoff = item / "handoffs/FASE-001-SPECIFY-HANDOFF.md"
        handoff.write_text(handoff.read_text(encoding="utf-8").replace("<!-- nome -->", "Web delivery").replace("<!-- termos canônicos -->", "API").replace("- delivery-units: DU-001", "- delivery-units: DU-001, DU-002, DU-003").replace("- development-type: documentation", "- development-type: frontend, backend, infra-iac"), encoding="utf-8")
        plan = item / "PLAN-CONTEXT.md"
        plan.write_text(plan.read_text(encoding="utf-8").replace("<!-- nome -->", "Web delivery").replace("- delivery-units: DU-001", "- delivery-units: DU-001, DU-002, DU-003").replace("- development-type: documentation", "- development-type: frontend, backend, infra-iac").replace("<!-- decisões técnicas cumulativas, dependências, lock-in, riscos e restrições consumíveis pelo plan -->", "HOW: implement DU-001 frontend, DU-002 backend, and DU-003 infra-iac."), encoding="utf-8")
        return item

    def _audit_v23(self, item: Path, expected: int = 0) -> dict:
        process, payload = invoke("audit", self.root, "--work-id", item.name)
        self.assertEqual(process.returncode, expected, payload)
        self.assertEqual(payload["verdict"], "GO" if expected == 0 else "NO-GO", payload)
        return payload

    def test_v23_auditor_read_only_and_persistent_matrix(self) -> None:
        item = self._valid_v23_item()
        before = snapshot(item)
        self._audit_v23(item)
        self.assertEqual(before, snapshot(item))
        map_path = item / "DELIVERY-MAP.md"; original = map_path.read_text(encoding="utf-8")
        cases = {
            "unknown-development-type": original.replace("frontend", "unknown", 1),
            "missing-mod-field": original.replace("- boundary: Browser and API boundary", "- absent: Browser and API boundary"),
            "missing-du-field": original.replace("- acceptance: frontend contract", "- absent: frontend contract"),
            "du-missing-dependency": original.replace("### DU-001 — Frontend\n- development-type: frontend\n- phase: FASE-001\n- scope-in: Browser UI\n- scope-out: Backend internals\n- depends-on: none", "### DU-001 — Frontend\n- development-type: frontend\n- phase: FASE-001\n- scope-in: Browser UI\n- scope-out: Backend internals\n- depends-on: DU-999"),
            "du-cycle": original.replace("DU-001 — Frontend\n- development-type: frontend\n- phase: FASE-001\n- scope-in: Browser UI\n- scope-out: Backend internals\n- depends-on: none", "DU-001 — Frontend\n- development-type: frontend\n- phase: FASE-001\n- scope-in: Browser UI\n- scope-out: Backend internals\n- depends-on: DU-002").replace("DU-002 — Backend\n- development-type: backend\n- phase: FASE-001\n- scope-in: HTTP API\n- scope-out: Browser rendering\n- depends-on: none", "DU-002 — Backend\n- development-type: backend\n- phase: FASE-001\n- scope-in: HTTP API\n- scope-out: Browser rendering\n- depends-on: DU-001"),
            "mod-cycle": original.replace("- depends-on: none", "- depends-on: MOD-002", 1) + "\n## MOD-002 — Platform\n- module-kind: platform\n- responsibility: duplicate\n- boundary: duplicate\n- depends-on: MOD-001\n",
            "mod-missing-dependency": original.replace("- depends-on: none", "- depends-on: MOD-999", 1),
            "orphan-du": original + "\n### DU-999 — Orphan\n- development-type: frontend\n- phase: FASE-001\n- scope-in: orphan\n- scope-out: orphan\n- depends-on: none\n- acceptance: orphan\n",
            "invalid-module-kind": original.replace("module-kind: cross-cutting", "module-kind: invalid"),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                map_path.write_text(text, encoding="utf-8")
                self._audit_v23(item, 1)
        map_path.write_text(original, encoding="utf-8")
        roadmap = item / "ROADMAP.md"; r = roadmap.read_text(encoding="utf-8"); roadmap.write_text(r.replace("DU-001, DU-002, DU-003", "DU-001"), encoding="utf-8"); self._audit_v23(item, 1); roadmap.write_text(r, encoding="utf-8")
        handoff = item / "handoffs/FASE-001-SPECIFY-HANDOFF.md"; h = handoff.read_text(encoding="utf-8"); handoff.write_text(h.replace("DU-001, DU-002, DU-003", "DU-001"), encoding="utf-8"); self._audit_v23(item, 1); handoff.write_text(h, encoding="utf-8")
        plan = item / "PLAN-CONTEXT.md"; p = plan.read_text(encoding="utf-8"); plan.write_text(p.replace("DU-001, DU-002, DU-003", "DU-001"), encoding="utf-8"); self._audit_v23(item, 1); plan.write_text(p, encoding="utf-8")

    def test_reject_symlink_chain_accepts_macos_var_root_alias(self) -> None:
        module = load_workspace_module()
        if not (module.os.path.islink("/var") and module.os.readlink("/var") in {"private/var", "/private/var"}):
            self.skipTest("host has no /var -> /private/var alias")
        private_var = Path("/private/var")
        if not private_var.is_dir():
            self.skipTest("host has no /private/var directory")
        with tempfile.TemporaryDirectory(dir=private_var / "tmp") as temporary:
            root = Path(temporary).resolve()
            lexical = Path("/var") / root.relative_to(private_var)
            module.reject_symlink_chain(root, lexical / "new-receipt.json")

    def test_v23_receipt_legacy_dual_read_is_deterministic(self) -> None:
        item = self._init_item(work_id="receipt-legacy"); self._mark_complete(item); self._commit_all(self.root)
        process, payload = invoke("reconcile", self.root, "--work-id", "receipt-legacy", "--apply", "--integration-branch", "main")
        self.assertEqual((process.returncode, payload["verdict"]), (0, "APPLIED"))
        receipt = self.root / ".grill/global/receipts/receipt-legacy.json"; value = json.loads(receipt.read_text())
        for key in ("decomposition_schema", "modules", "modules_justification", "development_types", "delivery_units"): value.pop(key, None)
        receipt.write_text(json.dumps(value))
        module = load_workspace_module(); read = module.read_receipts(self.root)
        self.assertEqual(read["receipt-legacy"]["modules"], "none")
        self.assertEqual(read["receipt-legacy"]["modules_justification"], "legacy-unclassified")
        value["modules"] = ["inferred"]; receipt.write_text(json.dumps(value))
        with self.assertRaises(Exception): module.read_receipts(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
