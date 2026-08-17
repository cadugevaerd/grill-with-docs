#!/usr/bin/env python3
"""Public CLI contract for FASE-001 Gauntlet activation.

The fixture is self-contained: it creates a Git repository, initializes a V2
work item through the shipped CLI, migrates both authorities to V3, and
explicitly rebinds the work item before exercising ``gauntlet-init``.  No test
module or test-only fixture is imported by production code.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "plugin/skills/grill-with-docs"
SCRIPTS = SKILL / "scripts"
ASSETS = SKILL / "assets"
WORKSPACE = SCRIPTS / "grill_workspace.py"
WORKFLOW_MIGRATOR = SCRIPTS / "grill_core/workflow_v3.py"
WORKFLOW_V2_TEMPLATE = ASSETS / "WORKFLOW.template.md"
REGISTRY = ASSETS / "workflow-step-skills.json"
CATALOG = ASSETS / "claude-code-local-skills.catalog.json"
TRUSTED_CATALOGS = ASSETS / "workflow-trusted-catalogs.json"
WORK_ID = "gauntlet-ready-a1b2"
SECOND_WORK_ID = "gauntlet-second-b2c3"
CONFIG_RELATIVE = ".grill/gauntlet.yaml"

# FASE-002 admission is the first command allowed to materialize coordinator
# state.  Import the Store only to inspect that public durable boundary; all
# transitions below still enter through the CLI.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from grill_core import store

ADAPTER = "claude-code-skill/v1"
MINIMUM_BY_STEP = {
    "specify": "large",
    "plan": "large",
    "checklist": "small",
    "tasks": "medium",
    "analyze": "large",
    "agent-assign": "large",
    "agent-execute": "medium",
    "converge": "medium",
    "verify": "medium",
    "review": "large",
    "ship": "large",
}
MAPPED_SKILL_REASONS = (
    "INVALID_DIGEST", "INVALID_RESOLVER_VERSION", "INVALID_VERSION", "UNKNOWN_RUNTIME", "UNKNOWN_STEP",
    "RUNTIME_UNSUPPORTED", "RUNTIME_ENTRYPOINT_UNPROVEN", "ADAPTER_MISMATCH", "ENTRYPOINT_ABSENT",
    "ENTRYPOINT_KIND_MISMATCH", "AMBIGUOUS_ENTRYPOINT", "NO_NATIVE_ENTRYPOINT", "SOURCE_REF_MISMATCH",
    "VERSION_BELOW_MINIMUM", "REGISTRY_SHA256_MISMATCH", "SKILL_NOT_PUBLISHED", "SKILL_CHANGED_AFTER_PREFLIGHT",
    "PINNED_RESOLUTION_INVALID", "PINNED_RESOLUTION_TAMPERED", "REGISTRY_ADAPTER",
    "REGISTRY_ALLOWED_ENTRYPOINTS", "REGISTRY_CATALOG_ID", "REGISTRY_DUPLICATE_ENTRYPOINT",
    "REGISTRY_DUPLICATE_SKILL_ID", "REGISTRY_ENTRYPOINT", "REGISTRY_ENTRYPOINT_KIND",
    "REGISTRY_HUMAN_AUTHORIZATION", "REGISTRY_INVALID", "REGISTRY_PROPOSED_SKILL_ID",
    "REGISTRY_RESOLUTIONS", "REGISTRY_RESOLUTION_INVALID", "REGISTRY_RUNTIMES", "REGISTRY_SCHEMA",
    "REGISTRY_SKILL_ID", "REGISTRY_SOURCE_REF", "REGISTRY_STEPS", "REGISTRY_STEP_INVALID",
    "REGISTRY_STEP_NOT_REQUIRED", "REGISTRY_STEP_SET", "REGISTRY_UNREADABLE", "REGISTRY_UNRESOLVED_REASON",
    "REGISTRY_VERSION", "REGISTRY_WORKFLOW_VERSION", "CATALOG_ABSENT", "CATALOG_CONTENT_MISMATCH",
    "CATALOG_DIGEST", "CATALOG_ENTRIES", "CATALOG_ENTRY_INVALID", "CATALOG_ID", "CATALOG_INVALID",
    "CATALOG_MISMATCH", "CATALOG_RUNTIME", "CATALOG_RUNTIME_MISMATCH", "CATALOG_SCHEMA",
    "CATALOG_SHA256_MISMATCH", "UNTRUSTED_CATALOG", "TRUSTED_CATALOGS_INVALID",
    "TRUSTED_CATALOGS_SCHEMA", "TRUSTED_CATALOGS_UNREADABLE", "TRUSTED_CATALOGS_WORKFLOW_VERSION",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json_bytes(value: bytes, *, source: str) -> dict:
    """Parse one closed JSON object and reject duplicate keys in fixtures too."""

    def unique(pairs: list[tuple[str, object]]) -> dict:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise AssertionError(f"duplicate key {key!r} in {source}")
            result[key] = item
        return result

    parsed = json.loads(value.decode("utf-8"), object_pairs_hook=unique)
    if not isinstance(parsed, dict):
        raise AssertionError(f"expected JSON object in {source}")
    return parsed


def invoke(program: Path, *args: object) -> tuple[subprocess.CompletedProcess[str], dict]:
    process = subprocess.run(
        [sys.executable, str(program), *(str(value) for value in args)],
        text=True,
        capture_output=True,
        check=False,
    )
    lines = process.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError(
            f"expected exactly one JSON line from {program.name}: "
            f"stdout={process.stdout!r} stderr={process.stderr!r}"
        )
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise AssertionError(process.stdout) from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"expected JSON object, got {payload!r}")
    return process, payload


def load_workspace_module(
    workspace: Path = WORKSPACE,
    module_name: str = "gauntlet_contract_workspace",
):
    spec = importlib.util.spec_from_file_location(module_name, workspace)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load public workspace module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CLI = load_workspace_module()


def invoke_module_in_process(module, *args: object) -> tuple[int, dict, str]:
    """Exercise the public parser/main boundary while deterministic faults are patched."""
    output = io.StringIO()
    errors = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        returncode = module.main([str(value) for value in args])
    lines = output.getvalue().splitlines()
    if len(lines) != 1:
        raise AssertionError(
            f"expected exactly one JSON line: stdout={output.getvalue()!r} stderr={errors.getvalue()!r}"
        )
    payload = json.loads(lines[0])
    if not isinstance(payload, dict):
        raise AssertionError(payload)
    return returncode, payload, errors.getvalue()


def invoke_in_process(*args: object) -> tuple[int, dict, str]:
    return invoke_module_in_process(CLI, *args)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], text=True, capture_output=True, check=True
    ).stdout.strip()


def require_success(process: subprocess.CompletedProcess[str], payload: dict, verdict: str) -> None:
    if process.returncode != 0 or payload.get("verdict") != verdict or process.stderr:
        raise AssertionError(
            f"fixture command failed: rc={process.returncode} payload={payload!r} stderr={process.stderr!r}"
        )


def build_v2_repository(root: Path) -> None:
    """Create one public-CLI initialized V2 work item and V2 workflow."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    git(root, "config", "user.email", "gauntlet-contract@example.invalid")
    git(root, "config", "user.name", "Gauntlet Contract")
    (root / "WORKFLOW.md").write_bytes(WORKFLOW_V2_TEMPLATE.read_bytes())
    git(root, "add", "WORKFLOW.md")
    git(root, "commit", "-qm", "fixture workflow v2")

    process, payload = invoke(
        WORKSPACE,
        "init",
        root,
        "--type",
        "feature",
        "--slug",
        "gauntlet-ready",
        "--work-id",
        WORK_ID,
        "--skip-backlog",
    )
    if process.returncode != 0 or payload.get("status") != "CREATED" or process.stderr:
        raise AssertionError(
            f"fixture init failed: rc={process.returncode} payload={payload!r} stderr={process.stderr!r}"
        )


def migrate_fixture_workflow(root: Path) -> None:
    process, preview = invoke(WORKFLOW_MIGRATOR, "migrate", root)
    require_success(process, preview, "PREVIEW")
    process, payload = invoke(
        WORKFLOW_MIGRATOR,
        "migrate",
        root,
        "--apply",
        "--expected-sha256",
        preview["current_sha256"],
    )
    require_success(process, payload, "APPLIED")


def build_rebound_v3_repository(root: Path) -> None:
    """Build the exact eligible authority chain required before activation."""
    build_v2_repository(root)
    process, payload = invoke(WORKSPACE, "migrate-v3", root, "--work-id", WORK_ID, "--apply")
    require_success(process, payload, "APPLIED")
    migrate_fixture_workflow(root)
    process, payload = invoke(
        WORKSPACE,
        "migrate-v3",
        root,
        "--work-id",
        WORK_ID,
        "--rebind-workflow",
        "--apply",
    )
    require_success(process, payload, "APPLIED")

    item = strict_json_bytes(
        (root / ".grill/work-items" / WORK_ID / "WORK-ITEM.json").read_bytes(),
        source="WORK-ITEM.json",
    )
    workflow_sha256 = sha256_bytes((root / "WORKFLOW.md").read_bytes())
    if item.get("schema") != "grill-work-item/v3":
        raise AssertionError(item)
    if item["immutable"]["workflow"]["sha256"] != workflow_sha256:
        raise AssertionError("fixture work item was not rebound to current WORKFLOW.md")


def build_v2_item_v3_workflow_repository(root: Path) -> None:
    build_v2_repository(root)
    migrate_fixture_workflow(root)


def add_rebound_v3_work_item(root: Path, work_id: str) -> None:
    """Create another eligible item through public commands in the same V3 project."""
    process, payload = invoke(
        WORKSPACE,
        "init",
        root,
        "--type",
        "feature",
        "--slug",
        "gauntlet-second",
        "--work-id",
        work_id,
        "--skip-backlog",
    )
    if process.returncode != 0 or payload.get("status") != "CREATED" or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))
    process, payload = invoke(WORKSPACE, "migrate-v3", root, "--work-id", work_id, "--apply")
    require_success(process, payload, "APPLIED")
    process, payload = invoke(
        WORKSPACE,
        "migrate-v3",
        root,
        "--work-id",
        work_id,
        "--rebind-workflow",
        "--apply",
    )
    if process.returncode != 0 or payload.get("verdict") not in {"APPLIED", "REUSED"} or process.stderr:
        raise AssertionError((process.returncode, payload, process.stderr))


def copy_skill(parent: Path, name: str = "copied-skill") -> Path:
    target = parent / name
    shutil.copytree(SKILL, target)
    return target


def symlink_supported() -> bool:
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / "target"
        target.mkdir()
        try:
            (Path(temporary) / "link").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
    return True


SYMLINKS = symlink_supported()


def file_snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


class GauntletInitContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = tempfile.TemporaryDirectory()
        cls.template_root = Path(cls.template.name) / "ready"
        build_rebound_v3_repository(cls.template_root)
        cls.v2_item_template_root = Path(cls.template.name) / "v2-item"
        build_v2_item_v3_workflow_repository(cls.v2_item_template_root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.template.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        shutil.copytree(self.template_root, self.root)
        self.config = self.root / CONFIG_RELATIVE

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fresh_copy(self, parent: Path, suffix: str) -> Path:
        root = parent / suffix
        shutil.copytree(self.template_root, root)
        return root

    def activate(
        self,
        max_workers: object,
        *,
        root: Path | None = None,
        work_id: str = WORK_ID,
        program: Path = WORKSPACE,
        extra_args: tuple[object, ...] = (),
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        target = root or self.root
        return invoke(
            program,
            "gauntlet-init",
            target,
            "--work-id",
            work_id,
            "--max-workers",
            max_workers,
            *extra_args,
        )

    def control(
        self,
        command: str,
        *,
        root: Path | None = None,
        work_id: str = WORK_ID,
        program: Path = WORKSPACE,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        return invoke(program, command, root or self.root, "--work-id", work_id)

    def read_config(self, root: Path | None = None) -> dict:
        target = root or self.root
        return strict_json_bytes((target / CONFIG_RELATIVE).read_bytes(), source=CONFIG_RELATIVE)

    def assert_activation_output(
        self,
        process: subprocess.CompletedProcess[str],
        payload: dict,
        verdict: str,
        workers: int,
        *,
        work_id: str = WORK_ID,
    ) -> None:
        self.assertEqual(process.stderr, "")
        self.assertEqual(process.returncode, 0, payload)
        self.assertEqual(
            payload,
            {
                "verdict": verdict,
                "work_id": work_id,
                "config": CONFIG_RELATIVE,
                "max_workers": workers,
                "stall_minutes": 15,
                "runtime": "claude",
            },
        )

    def assert_blocked_unchanged(
        self,
        root: Path,
        before: dict[str, tuple[bytes, int]],
        process: subprocess.CompletedProcess[str],
        payload: dict,
        code: str,
        *,
        owned_config_lock: bool = False,
    ) -> None:
        self.assertEqual(process.stderr, "")
        self.assertEqual(process.returncode, 2, payload)
        self.assertEqual((payload.get("verdict"), payload.get("code")), ("BLOCKED", code), payload)
        self.assertEqual(file_snapshot(root), before)
        self.assertEqual((root / ".grill/.gauntlet-config.lock").exists(), owned_config_lock)
        self.assertFalse((root / ".grill/locks" / f"{WORK_ID}.lock").exists())
        self.assertFalse(any(path.name.endswith(".tmp") for path in (root / ".grill").iterdir()))

    def assert_control_read_only(
        self,
        root: Path,
        before: dict[str, tuple[bytes, int]],
    ) -> None:
        self.assertEqual(file_snapshot(root), before)
        self.assertFalse((root / ".grill/.gauntlet-config.lock").exists())
        self.assertFalse((root / ".grill/locks" / f"{WORK_ID}.lock").exists())

    def assert_status_projection(
        self,
        process: subprocess.CompletedProcess[str],
        payload: dict,
        state: str,
    ) -> None:
        self.assertEqual(process.stderr, "")
        self.assertEqual(process.returncode, 0, payload)
        self.assertEqual(payload.get("verdict"), "STATUS", payload)
        self.assertEqual(payload.get("work_id"), WORK_ID, payload)
        self.assertEqual(payload.get("activation_state"), state, payload)
        self.assertNotIn("code", payload)
        if state in {"STALE", "BLOCKED"}:
            self.assertIsInstance(payload.get("reason"), str)
            self.assertTrue(payload["reason"].strip())
        else:
            self.assertNotIn("reason", payload)

    def assert_control_blocked(
        self,
        process: subprocess.CompletedProcess[str],
        payload: dict,
        code: str,
    ) -> None:
        self.assertEqual(process.stderr, "")
        self.assertEqual(process.returncode, 2, payload)
        self.assertEqual(
            (payload.get("verdict"), payload.get("code"), payload.get("work_id")),
            ("BLOCKED", code, WORK_ID),
            payload,
        )

    def test_first_activation_is_exact_and_only_writes_the_gauntlet_config(self) -> None:
        before = file_snapshot(self.root)
        process, payload = self.activate(3)
        self.assert_activation_output(process, payload, "ACTIVATED", 3)
        after = file_snapshot(self.root)
        self.assertEqual(set(after) - set(before), {CONFIG_RELATIVE})
        for relative, state in before.items():
            self.assertEqual(after.get(relative), state, relative)

    def test_every_selected_worker_limit_from_one_through_five_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for workers in range(1, 6):
                with self.subTest(max_workers=workers):
                    root = self.fresh_copy(parent, f"workers-{workers}")
                    process, payload = self.activate(workers, root=root)
                    self.assert_activation_output(process, payload, "ACTIVATED", workers)
                    stored = self.read_config(root)["activations"][WORK_ID]["limits"]["max_workers"]
                    self.assertIs(type(stored), int)
                    self.assertEqual(stored, workers)

    def test_activation_record_has_closed_schema_fixed_stall_and_exact_tier_policy(self) -> None:
        process, payload = self.activate(5)
        self.assert_activation_output(process, payload, "ACTIVATED", 5)
        config = self.read_config()
        self.assertEqual(set(config), {"schema", "activations"})
        self.assertEqual(config["schema"], "grill-gauntlet/v1")
        self.assertEqual(set(config["activations"]), {WORK_ID})
        record = config["activations"][WORK_ID]
        self.assertEqual(
            set(record),
            {"work_item_id", "work_item", "workflow", "runtime", "catalog", "limits", "tier_policy"},
        )
        self.assertEqual(record["work_item_id"], WORK_ID)
        self.assertEqual(set(record["work_item"]), {"document_sha256"})
        self.assertEqual(set(record["workflow"]), {"version", "sha256", "registry_sha256"})
        self.assertEqual(set(record["runtime"]), {"id", "adapter"})
        self.assertEqual(
            set(record["catalog"]),
            {"id", "document_sha256", "resolution_sha256", "trusted_asset_document_sha256"},
        )
        self.assertEqual(set(record["limits"]), {"max_workers", "stall_minutes"})
        self.assertEqual(
            set(record["tier_policy"]),
            {"adapter", "minimum_by_step", "supplemental", "promotions"},
        )
        self.assertEqual(record["limits"], {"max_workers": 5, "stall_minutes": 15})
        self.assertEqual(
            record["tier_policy"],
            {
                "adapter": ADAPTER,
                "minimum_by_step": MINIMUM_BY_STEP,
                "supplemental": {"markdown-maintenance": "small"},
                "promotions": [],
            },
        )
        self.assertEqual(len(record["tier_policy"]["minimum_by_step"]), 11)

    def test_record_binds_current_work_item_workflow_registry_and_bundled_catalog_trust(self) -> None:
        process, payload = self.activate(2)
        self.assert_activation_output(process, payload, "ACTIVATED", 2)
        record = self.read_config()["activations"][WORK_ID]
        item_bytes = (self.root / ".grill/work-items" / WORK_ID / "WORK-ITEM.json").read_bytes()
        workflow_bytes = (self.root / "WORKFLOW.md").read_bytes()
        catalog_bytes = CATALOG.read_bytes()
        trusted_bytes = TRUSTED_CATALOGS.read_bytes()
        catalog = strict_json_bytes(catalog_bytes, source=str(CATALOG))
        trusted = strict_json_bytes(trusted_bytes, source=str(TRUSTED_CATALOGS))

        self.assertEqual(record["work_item"], {"document_sha256": sha256_bytes(item_bytes)})
        self.assertEqual(
            record["workflow"],
            {
                "version": "v3",
                "sha256": sha256_bytes(workflow_bytes),
                "registry_sha256": "sha256:" + sha256_bytes(REGISTRY.read_bytes()),
            },
        )
        self.assertEqual(record["runtime"], {"id": "claude", "adapter": ADAPTER})
        self.assertEqual(catalog["schema"], "skill-catalog/v1")
        self.assertEqual(catalog["runtime"], "claude")
        self.assertEqual(catalog["catalog_id"], "claude-code-local-skills")
        self.assertEqual(len(catalog["entries"]), 11)
        self.assertEqual(trusted["catalogs"][catalog["catalog_id"]], catalog["catalog_sha256"])
        self.assertEqual(
            record["catalog"],
            {
                "id": catalog["catalog_id"],
                "document_sha256": sha256_bytes(catalog_bytes),
                "resolution_sha256": catalog["catalog_sha256"],
                "trusted_asset_document_sha256": sha256_bytes(trusted_bytes),
            },
        )

    def test_trust_swap_between_capture_and_resolver_uses_one_authorized_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            skill = copy_skill(parent, "trust-snapshot-skill")
            root = self.fresh_copy(parent, "trust-snapshot-root")
            program = skill / "scripts/grill_workspace.py"
            copied_cli = load_workspace_module(program, "gauntlet_trust_snapshot_workspace")
            copied_step_skills = copied_cli.grill_core_module("step_skills")
            # Prime the exact Gauntlet module the copied public CLI will call.
            copied_cli.grill_core_module("gauntlet")

            trust_path = skill / "assets/workflow-trusted-catalogs.json"
            authorized_bytes = trust_path.read_bytes()
            authorized_document = strict_json_bytes(authorized_bytes, source=str(trust_path))
            authorized_catalog_sha256 = authorized_document["catalogs"][
                "claude-code-local-skills"
            ]
            tampered_document = json.loads(json.dumps(authorized_document))
            tampered_document["catalogs"]["claude-code-local-skills"] = "sha256:" + "0" * 64
            tampered_bytes = (
                json.dumps(tampered_document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            ).encode("utf-8")
            self.assertNotEqual(tampered_bytes, authorized_bytes)

            original_snapshot = copied_step_skills._load_trusted_catalogs_snapshot
            observations = {"snapshots": 0}

            def swapping_snapshot(*args, **kwargs):
                snapshot = original_snapshot(*args, **kwargs)
                observations["snapshots"] += 1
                self.assertEqual(snapshot[0], authorized_bytes)
                self.assertEqual(
                    snapshot[1]["claude-code-local-skills"],
                    authorized_catalog_sha256,
                )
                if observations["snapshots"] == 1:
                    # The shipped batch has captured and parsed its one trust
                    # snapshot. Change the asset before its internal resolver
                    # consumes that snapshot; no public caller supplies trust.
                    trust_path.write_bytes(tampered_bytes)
                return snapshot

            with mock.patch.object(
                copied_step_skills,
                "_load_trusted_catalogs_snapshot",
                side_effect=swapping_snapshot,
            ):
                returncode, payload, stderr = invoke_module_in_process(
                    copied_cli,
                    "gauntlet-init",
                    root,
                    "--work-id",
                    WORK_ID,
                    "--max-workers",
                    3,
                )
            self.assertEqual(stderr, "")
            self.assertEqual((returncode, payload.get("verdict")), (0, "ACTIVATED"), payload)
            self.assertEqual(observations["snapshots"], 1)
            record = self.read_config(root)["activations"][WORK_ID]
            self.assertEqual(
                record["catalog"]["trusted_asset_document_sha256"],
                sha256_bytes(authorized_bytes),
            )
            self.assertNotEqual(
                record["catalog"]["trusted_asset_document_sha256"],
                sha256_bytes(tampered_bytes),
            )
            self.assertEqual(trust_path.read_bytes(), tampered_bytes)

            before = file_snapshot(root)
            process, status = self.control("gauntlet-status", root=root, program=program)
            self.assert_status_projection(process, status, "STALE")
            self.assertEqual(status.get("reason"), "IDENTITY-STALE")
            self.assert_control_read_only(root, before)

    def test_equivalent_activation_returns_reused_without_rewriting_the_record(self) -> None:
        first_process, first = self.activate(4)
        self.assert_activation_output(first_process, first, "ACTIVATED", 4)
        before = self.config.read_bytes(), self.config.stat().st_mtime_ns
        second_process, second = self.activate(4)
        self.assert_activation_output(second_process, second, "REUSED", 4)
        self.assertEqual((self.config.read_bytes(), self.config.stat().st_mtime_ns), before)

    def test_different_worker_limit_is_activation_conflict_and_preserves_record(self) -> None:
        first_process, first = self.activate(2)
        self.assert_activation_output(first_process, first, "ACTIVATED", 2)
        before = self.config.read_bytes(), self.config.stat().st_mtime_ns
        process, payload = self.activate(3)
        self.assertEqual(process.stderr, "")
        self.assertEqual(process.returncode, 2, payload)
        self.assertEqual((payload.get("verdict"), payload.get("code")), ("BLOCKED", "ACTIVATION-CONFLICT"))
        self.assertEqual(payload.get("work_id"), WORK_ID)
        self.assertIsInstance(payload.get("remediation"), str)
        self.assertTrue(payload["remediation"].strip())
        self.assertEqual((self.config.read_bytes(), self.config.stat().st_mtime_ns), before)

    def test_global_lock_serializes_two_work_ids_and_retry_preserves_both_records(self) -> None:
        add_rebound_v3_work_item(self.root, SECOND_WORK_ID)
        gauntlet = CLI.grill_core_module("gauntlet")
        original_acquire = gauntlet.acquire_config_lock
        acquired = threading.Event()
        release = threading.Event()
        first: dict[str, object] = {}

        def held_acquire(root: Path) -> int:
            descriptor = original_acquire(root)
            acquired.set()
            release.wait(10)
            return descriptor

        def activate_first() -> None:
            try:
                first["result"] = CLI.gauntlet_init_command(
                    SimpleNamespace(root=self.root, work_id=WORK_ID, max_workers=2)
                )
            except BaseException as exc:  # surfaced in the main test thread
                first["error"] = exc

        with mock.patch.object(gauntlet, "acquire_config_lock", side_effect=held_acquire):
            worker = threading.Thread(target=activate_first, daemon=True)
            worker.start()
            try:
                self.assertTrue(acquired.wait(5), "first activation never acquired the global lock")
                self.assertTrue((self.root / ".grill/.gauntlet-config.lock").is_dir())
                # The command contract requires global-before-item ordering.
                self.assertFalse((self.root / ".grill/locks" / f"{WORK_ID}.lock").exists())

                before = file_snapshot(self.root)
                process, payload = self.activate(3, work_id=SECOND_WORK_ID)
                self.assertEqual(process.stderr, "")
                self.assertEqual(
                    (process.returncode, payload.get("verdict"), payload.get("code")),
                    (2, "BLOCKED", "CONFIG-LOCK-CONTENTION"),
                    payload,
                )
                self.assertEqual(file_snapshot(self.root), before)
                self.assertTrue((self.root / ".grill/.gauntlet-config.lock").is_dir())
                self.assertFalse((self.root / ".grill/locks" / f"{SECOND_WORK_ID}.lock").exists())
            finally:
                release.set()
                worker.join(10)
            self.assertFalse(worker.is_alive(), "first activation did not release its locks")

        self.assertNotIn("error", first)
        first_payload, first_returncode = first["result"]
        self.assertEqual((first_returncode, first_payload.get("verdict")), (0, "ACTIVATED"), first_payload)
        self.assertFalse((self.root / ".grill/.gauntlet-config.lock").exists())
        self.assertFalse((self.root / ".grill/locks" / f"{WORK_ID}.lock").exists())

        process, payload = self.activate(3, work_id=SECOND_WORK_ID)
        self.assert_activation_output(process, payload, "ACTIVATED", 3, work_id=SECOND_WORK_ID)
        config = self.read_config()
        self.assertEqual(set(config["activations"]), {WORK_ID, SECOND_WORK_ID})
        self.assertEqual(config["activations"][WORK_ID]["limits"]["max_workers"], 2)
        self.assertEqual(config["activations"][SECOND_WORK_ID]["limits"]["max_workers"], 3)
        self.assertFalse((self.root / ".grill/.gauntlet-config.lock").exists())
        for work_id in (WORK_ID, SECOND_WORK_ID):
            self.assertFalse((self.root / ".grill/locks" / f"{work_id}.lock").exists())
        self.assertFalse(any(path.name.endswith(".tmp") for path in (self.root / ".grill").iterdir()))

    def test_config_cas_detects_external_change_and_preserves_external_bytes(self) -> None:
        gauntlet = CLI.grill_core_module("gauntlet")
        original_read = gauntlet._read_regular_at
        external_bytes = b'{"schema":"grill-gauntlet/v1","activations":{}}\n'
        observations = {"config_reads": 0}
        before = file_snapshot(self.root)

        def racing_read(directory_fd: int, name: str):
            result = original_read(directory_fd, name)
            if name == gauntlet.CONFIG_NAME:
                observations["config_reads"] += 1
                if observations["config_reads"] == 1:
                    self.config.write_bytes(external_bytes)
            return result

        with mock.patch.object(gauntlet, "_read_regular_at", side_effect=racing_read):
            returncode, payload, stderr = invoke_in_process(
                "gauntlet-init", self.root, "--work-id", WORK_ID, "--max-workers", 3
            )
        self.assertEqual(stderr, "")
        self.assertEqual(observations["config_reads"], 2)
        self.assertEqual(
            (returncode, payload.get("verdict"), payload.get("code")),
            (2, "BLOCKED", "CONFIG-CHANGED"),
            payload,
        )
        self.assertEqual(self.config.read_bytes(), external_bytes)
        after = file_snapshot(self.root)
        after.pop(CONFIG_RELATIVE)
        self.assertEqual(after, before)
        self.assertFalse((self.root / ".grill/.gauntlet-config.lock").exists())
        self.assertFalse((self.root / ".grill/locks" / f"{WORK_ID}.lock").exists())
        self.assertFalse(any(path.name.endswith(".tmp") for path in (self.root / ".grill").iterdir()))

    def test_interrupted_config_atomic_replace_is_one_json_and_cleans_locks_and_temp(self) -> None:
        work_item_v3 = CLI.grill_core_module("work_item_v3")
        original_atomic = work_item_v3._atomic_replace_at
        supported = set(work_item_v3.os.supports_dir_fd)
        before = file_snapshot(self.root)

        def interrupted_atomic(directory_fd: int, name: str, data: bytes, *, mode: int | None = None):
            with mock.patch.object(
                work_item_v3.os, "rename", side_effect=OSError("simulated interrupted config rename")
            ) as interrupted_rename:
                with mock.patch.object(
                    work_item_v3.os, "supports_dir_fd", supported | {interrupted_rename}
                ):
                    return original_atomic(directory_fd, name, data, mode=mode)

        with mock.patch.object(work_item_v3, "_atomic_replace_at", side_effect=interrupted_atomic):
            returncode, payload, stderr = invoke_in_process(
                "gauntlet-init", self.root, "--work-id", WORK_ID, "--max-workers", 3
            )
        self.assertEqual(stderr, "")
        self.assertEqual(
            (returncode, payload.get("verdict"), payload.get("code")),
            (2, "BLOCKED", "FILESYSTEM"),
            payload,
        )
        self.assertEqual(file_snapshot(self.root), before)
        self.assertFalse(self.config.exists())
        self.assertFalse((self.root / ".grill/.gauntlet-config.lock").exists())
        self.assertFalse((self.root / ".grill/locks" / f"{WORK_ID}.lock").exists())
        self.assertFalse(any(path.name.endswith(".tmp") for path in (self.root / ".grill").iterdir()))

    def test_owner_write_and_fsync_failures_clean_both_lock_levels(self) -> None:
        gauntlet = CLI.grill_core_module("gauntlet")
        original_write = gauntlet.os.write
        original_fsync = gauntlet.os.fsync
        cases = (
            ("config-write", "write", 1, ".grill/.gauntlet-config.lock"),
            ("config-fsync", "fsync", 1, ".grill/.gauntlet-config.lock"),
            ("item-write", "write", 2, f".grill/locks/{WORK_ID}.lock"),
            ("item-fsync", "fsync", 2, f".grill/locks/{WORK_ID}.lock"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for name, operation, fail_at, lock_relative in cases:
                with self.subTest(case=name):
                    root = self.fresh_copy(parent, name)
                    before = file_snapshot(root)
                    calls = {"count": 0}
                    lock_path = root / lock_relative

                    def injected_write(descriptor: int, data: bytes) -> int:
                        calls["count"] += 1
                        if operation == "write" and calls["count"] == fail_at:
                            self.assertTrue(lock_path.is_dir())
                            self.assertTrue((lock_path / gauntlet.CONFIG_LOCK_OWNER).is_file())
                            raise OSError(f"simulated {name} owner write failure")
                        return original_write(descriptor, data)

                    def injected_fsync(descriptor: int) -> None:
                        calls["count"] += 1
                        if operation == "fsync" and calls["count"] == fail_at:
                            self.assertTrue(lock_path.is_dir())
                            self.assertTrue((lock_path / gauntlet.CONFIG_LOCK_OWNER).is_file())
                            raise OSError(f"simulated {name} owner fsync failure")
                        original_fsync(descriptor)

                    target = "write" if operation == "write" else "fsync"
                    replacement = injected_write if operation == "write" else injected_fsync
                    with mock.patch.object(gauntlet.os, target, side_effect=replacement):
                        returncode, payload, stderr = invoke_in_process(
                            "gauntlet-init",
                            root,
                            "--work-id",
                            WORK_ID,
                            "--max-workers",
                            3,
                        )

                    self.assertEqual(stderr, "")
                    self.assertEqual(calls["count"], fail_at)
                    self.assertEqual(
                        (returncode, payload.get("verdict"), payload.get("code")),
                        (2, "BLOCKED", "SAFE-PATH-UNAVAILABLE"),
                        payload,
                    )
                    self.assertFalse((root / CONFIG_RELATIVE).exists())
                    self.assertFalse((root / ".grill/.gauntlet-config.lock").exists())
                    self.assertFalse((root / ".grill/locks" / f"{WORK_ID}.lock").exists())
                    self.assertFalse(
                        any(path.name.endswith(".tmp") for path in (root / ".grill").rglob("*"))
                    )
                    self.assertEqual(file_snapshot(root), before)

    def test_owner_open_failures_clean_lock_directories_without_an_owner_file(self) -> None:
        gauntlet = CLI.grill_core_module("gauntlet")
        original_open = gauntlet.os.open
        supported_dir_fd = set(gauntlet.os.supports_dir_fd)
        cases = (
            ("config-owner-open", 1, ".grill/.gauntlet-config.lock"),
            ("item-owner-open", 2, f".grill/locks/{WORK_ID}.lock"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for name, fail_at, lock_relative in cases:
                with self.subTest(case=name):
                    root = self.fresh_copy(parent, name)
                    before = file_snapshot(root)
                    owner_opens = {"count": 0, "failures": 0}
                    lock_path = root / lock_relative

                    def failing_owner_open(
                        path: object,
                        flags: int,
                        mode: int = 0o777,
                        *,
                        dir_fd: int | None = None,
                    ) -> int:
                        if path == gauntlet.CONFIG_LOCK_OWNER:
                            owner_opens["count"] += 1
                            if owner_opens["count"] == fail_at:
                                self.assertTrue(lock_path.is_dir())
                                self.assertFalse(
                                    (lock_path / gauntlet.CONFIG_LOCK_OWNER).exists()
                                )
                                owner_opens["failures"] += 1
                                raise OSError(f"simulated {name} owner open failure")
                        return original_open(path, flags, mode, dir_fd=dir_fd)

                    with mock.patch.object(
                        gauntlet.os, "open", side_effect=failing_owner_open
                    ) as patched_open:
                        with mock.patch.object(
                            gauntlet.os,
                            "supports_dir_fd",
                            supported_dir_fd | {patched_open},
                        ):
                            returncode, payload, stderr = invoke_in_process(
                                "gauntlet-init",
                                root,
                                "--work-id",
                                WORK_ID,
                                "--max-workers",
                                3,
                            )

                    self.assertEqual(stderr, "")
                    self.assertEqual(owner_opens["failures"], 1)
                    self.assertEqual(
                        (returncode, payload.get("verdict"), payload.get("code")),
                        (2, "BLOCKED", "SAFE-PATH-UNAVAILABLE"),
                        payload,
                    )
                    self.assertFalse((root / CONFIG_RELATIVE).exists())
                    self.assertFalse((root / ".grill/.gauntlet-config.lock").exists())
                    self.assertFalse((root / ".grill/locks" / f"{WORK_ID}.lock").exists())
                    self.assertFalse(
                        any(path.name.endswith(".tmp") for path in (root / ".grill").rglob("*"))
                    )
                    self.assertEqual(file_snapshot(root), before)

    def test_incomplete_short_owner_writes_fail_closed_and_clean_both_lock_levels(self) -> None:
        gauntlet = CLI.grill_core_module("gauntlet")
        original_write = gauntlet.os.write
        cases = (
            ("config-short-write", 1, ".grill/.gauntlet-config.lock"),
            ("item-short-write", 2, f".grill/locks/{WORK_ID}.lock"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for name, short_at, lock_relative in cases:
                with self.subTest(case=name):
                    root = self.fresh_copy(parent, name)
                    before = file_snapshot(root)
                    calls = {"count": 0, "short_writes": 0}
                    lock_path = root / lock_relative

                    def short_write(descriptor: int, data: bytes) -> int:
                        calls["count"] += 1
                        if calls["count"] == short_at:
                            self.assertEqual(len(data), 32)
                            self.assertTrue(lock_path.is_dir())
                            self.assertTrue((lock_path / gauntlet.CONFIG_LOCK_OWNER).is_file())
                            calls["short_writes"] += 1
                            return original_write(descriptor, data[:1])
                        if calls["count"] == short_at + 1:
                            self.assertEqual(len(data), 31)
                            return 0
                        return original_write(descriptor, data)

                    with mock.patch.object(gauntlet.os, "write", side_effect=short_write):
                        returncode, payload, stderr = invoke_in_process(
                            "gauntlet-init",
                            root,
                            "--work-id",
                            WORK_ID,
                            "--max-workers",
                            3,
                        )

                    self.assertEqual(stderr, "")
                    self.assertEqual(calls["short_writes"], 1)
                    self.assertEqual(
                        (returncode, payload.get("verdict"), payload.get("code")),
                        (2, "BLOCKED", "SAFE-PATH-UNAVAILABLE"),
                        payload,
                    )
                    self.assertFalse((root / CONFIG_RELATIVE).exists())
                    self.assertFalse((root / ".grill/.gauntlet-config.lock").exists())
                    self.assertFalse((root / ".grill/locks" / f"{WORK_ID}.lock").exists())
                    self.assertFalse(
                        any(path.name.endswith(".tmp") for path in (root / ".grill").rglob("*"))
                    )
                    self.assertEqual(file_snapshot(root), before)

    def test_v2_workflow_is_blocked_without_activation_state(self) -> None:
        (self.root / "WORKFLOW.md").write_bytes(WORKFLOW_V2_TEMPLATE.read_bytes())
        before = file_snapshot(self.root)
        process, payload = self.activate(3)
        self.assert_blocked_unchanged(self.root, before, process, payload, "WORKFLOW-INCOMPATIBLE")

    def test_v2_item_under_v3_workflow_requires_explicit_item_migration(self) -> None:
        shutil.rmtree(self.root)
        shutil.copytree(self.v2_item_template_root, self.root)
        before = file_snapshot(self.root)
        process, payload = self.activate(3)
        self.assert_blocked_unchanged(self.root, before, process, payload, "WORK-ITEM-V3-REQUIRED")

    def test_codex_and_hermes_are_not_accepted_or_fallen_back_to_claude(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for runtime in ("codex", "hermes"):
                with self.subTest(runtime=runtime):
                    root = self.fresh_copy(parent, runtime)
                    before = file_snapshot(root)
                    process, payload = self.activate(3, root=root, extra_args=("--runtime", runtime))
                    self.assert_blocked_unchanged(root, before, process, payload, "INVALID-ARGUMENTS")
                    self.assertNotIn(payload.get("runtime"), {"claude", runtime})

    def test_invalid_max_workers_inputs_are_one_json_and_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for index, value in enumerate((0, -1, 6, "1.0", "true", "3e0")):
                with self.subTest(value=value):
                    root = self.fresh_copy(parent, f"invalid-{index}")
                    before = file_snapshot(root)
                    process, payload = self.activate(value, root=root)
                    self.assert_blocked_unchanged(root, before, process, payload, "INVALID-ARGUMENTS")
            for index, tail in enumerate(((), ("--max-workers",))):
                with self.subTest(arguments=tail):
                    root = self.fresh_copy(parent, f"missing-{index}")
                    before = file_snapshot(root)
                    process, payload = invoke(
                        WORKSPACE, "gauntlet-init", root, "--work-id", WORK_ID, *tail
                    )
                    self.assert_blocked_unchanged(root, before, process, payload, "INVALID-ARGUMENTS")

    def test_malformed_unknown_and_duplicate_config_are_rejected_unchanged(self) -> None:
        cases = {
            "malformed": b"{not-json\n",
            "bom": b'\xef\xbb\xbf{"schema":"grill-gauntlet/v1","activations":{}}\n',
            "non-utf8": b'{"schema":"grill-gauntlet/v1","activations":{"bad":"\xff"}}\n',
            "scalar-root": b"true\n",
            "list-root": b"[]\n",
            "unknown": (
                json.dumps(
                    {"schema": "grill-gauntlet/v1", "activations": {}, "unknown": True},
                    sort_keys=True,
                ) + "\n"
            ).encode("utf-8"),
            "duplicate": (
                b'{"schema":"grill-gauntlet/v1","schema":"grill-gauntlet/v1","activations":{}}\n'
            ),
        }
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for name, raw in cases.items():
                with self.subTest(case=name):
                    root = self.fresh_copy(parent, name)
                    config = root / CONFIG_RELATIVE
                    config.write_bytes(raw)
                    before = file_snapshot(root)
                    process, payload = self.activate(3, root=root)
                    self.assert_blocked_unchanged(root, before, process, payload, "GAUNTLET-CONFIG-INVALID")
                    self.assertEqual(config.read_bytes(), raw)

    def test_existing_record_rejects_wrong_types_enums_and_forbidden_fields_unchanged(self) -> None:
        def nested_unknown(document: dict) -> None:
            document["activations"][WORK_ID]["limits"]["unknown"] = 1

        def boolean_worker(document: dict) -> None:
            document["activations"][WORK_ID]["limits"]["max_workers"] = True

        def float_worker(document: dict) -> None:
            document["activations"][WORK_ID]["limits"]["max_workers"] = 3.5

        def wrong_activations_type(document: dict) -> None:
            document["activations"] = []

        def unrecognized_runtime(document: dict) -> None:
            document["activations"][WORK_ID]["runtime"]["id"] = "codex"

        def forbidden_path(document: dict) -> None:
            document["activations"][WORK_ID]["path"] = "/tmp/host-controlled"

        def forbidden_credentials(document: dict) -> None:
            document["activations"][WORK_ID]["credentials"] = {"token": "not-allowed"}

        def forbidden_budget(document: dict) -> None:
            document["activations"][WORK_ID]["budget"] = {"usd": 1}

        cases = (
            ("nested-unknown", nested_unknown),
            ("boolean-worker", boolean_worker),
            ("float-worker", float_worker),
            ("wrong-activations-type", wrong_activations_type),
            ("unrecognized-runtime", unrecognized_runtime),
            ("forbidden-path", forbidden_path),
            ("forbidden-credentials", forbidden_credentials),
            ("forbidden-budget", forbidden_budget),
        )
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for name, mutate in cases:
                with self.subTest(case=name):
                    root = self.fresh_copy(parent, name)
                    process, payload = self.activate(3, root=root)
                    self.assert_activation_output(process, payload, "ACTIVATED", 3)
                    config = root / CONFIG_RELATIVE
                    document = strict_json_bytes(config.read_bytes(), source=str(config))
                    mutate(document)
                    raw = (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
                    config.write_bytes(raw)
                    before = file_snapshot(root)
                    process, payload = self.activate(3, root=root)
                    self.assert_blocked_unchanged(
                        root, before, process, payload, "GAUNTLET-CONFIG-INVALID"
                    )
                    self.assertEqual(config.read_bytes(), raw)

    @unittest.skipUnless(SYMLINKS, "symlinks unavailable")
    def test_symlinked_config_never_redirects_activation_write(self) -> None:
        outside = self.root.parent / "outside-gauntlet.json"
        outside.write_bytes(b'{"outside":"must stay unchanged"}\n')
        self.config.symlink_to(outside)
        before = file_snapshot(self.root); outside_before = outside.read_bytes()
        process, payload = self.activate(3)
        self.assert_blocked_unchanged(self.root, before, process, payload, "SAFE-PATH-UNAVAILABLE")
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(outside.read_bytes(), outside_before)

    @unittest.skipUnless(SYMLINKS, "symlinks unavailable")
    def test_symlinked_grill_ancestor_is_rejected_before_any_lock_or_write(self) -> None:
        outside = self.root.parent / "outside-grill"
        shutil.move(str(self.root / ".grill"), outside)
        (self.root / ".grill").symlink_to(outside, target_is_directory=True)
        before = file_snapshot(self.root); outside_before = file_snapshot(outside)
        process, payload = self.activate(3)
        self.assert_blocked_unchanged(self.root, before, process, payload, "WORK-ITEM-SYMLINK")
        self.assertEqual(file_snapshot(outside), outside_before)

    def test_existing_config_lock_is_contention_and_is_never_removed_by_waiter(self) -> None:
        config_lock = self.root / ".grill/.gauntlet-config.lock"
        config_lock.mkdir()
        before = file_snapshot(self.root)
        process, payload = self.activate(3)
        self.assert_blocked_unchanged(
            self.root, before, process, payload, "CONFIG-LOCK-CONTENTION", owned_config_lock=True
        )
        self.assertTrue(config_lock.is_dir())

    def test_releasing_owner_a_never_removes_successor_b_recreated_at_same_name(self) -> None:
        gauntlet = CLI.grill_core_module("gauntlet")
        lock_path = self.root / ".grill/.gauntlet-config.lock"
        owner_path = lock_path / gauntlet.CONFIG_LOCK_OWNER
        lock_a = gauntlet.acquire_config_lock(self.root)
        original_read = gauntlet._read_regular_at
        successor: dict[str, object] = {}
        swapped = {"done": False}

        def recreate_after_owner_snapshot(directory_fd: int, name: str):
            result = original_read(directory_fd, name)
            if name == gauntlet.CONFIG_LOCK_OWNER and not swapped["done"]:
                swapped["done"] = True
                # A has already read and matched its token. Replace the named
                # directory before its inode check, exactly where an unsafe
                # path-only release could delete successor B.
                gauntlet.os.unlink(gauntlet.CONFIG_LOCK_OWNER, dir_fd=directory_fd)
                gauntlet.os.rmdir(gauntlet.CONFIG_LOCK, dir_fd=lock_a.grill_fd)
                lock_b = gauntlet.acquire_config_lock(self.root)
                successor["lock"] = lock_b
                successor["inode"] = gauntlet.os.stat(
                    gauntlet.CONFIG_LOCK,
                    dir_fd=lock_b.grill_fd,
                    follow_symlinks=False,
                ).st_ino
                successor["owner"] = owner_path.read_bytes()
            return result

        try:
            with mock.patch.object(
                gauntlet, "_read_regular_at", side_effect=recreate_after_owner_snapshot
            ):
                gauntlet.release_config_lock(lock_a)

            self.assertTrue(swapped["done"])
            lock_b = successor["lock"]
            self.assertTrue(lock_path.is_dir())
            self.assertEqual(owner_path.read_bytes(), successor["owner"])
            self.assertEqual(
                gauntlet.os.stat(
                    gauntlet.CONFIG_LOCK,
                    dir_fd=lock_b.grill_fd,
                    follow_symlinks=False,
                ).st_ino,
                successor["inode"],
            )
            with self.assertRaises(gauntlet.GauntletError) as blocked:
                gauntlet.acquire_config_lock(self.root)
            self.assertEqual(blocked.exception.code, "CONFIG-LOCK-CONTENTION")
        finally:
            lock_b = successor.get("lock")
            if lock_b is not None:
                gauntlet.release_config_lock(lock_b)
        self.assertFalse(lock_path.exists())

    def test_catalog_registry_and_trust_asset_failures_are_precise_and_non_mutating(self) -> None:
        def catalog_content_tamper(skill: Path) -> None:
            path = skill / "assets/claude-code-local-skills.catalog.json"
            document = strict_json_bytes(path.read_bytes(), source=str(path))
            document["entries"][0]["content_sha256"] = "sha256:" + "0" * 64
            path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        def catalog_missing(skill: Path) -> None:
            (skill / "assets/claude-code-local-skills.catalog.json").unlink()

        def registry_byte_drift(skill: Path) -> None:
            path = skill / "assets/workflow-step-skills.json"
            path.write_bytes(path.read_bytes() + b"\n")

        def trust_pin_tamper(skill: Path) -> None:
            path = skill / "assets/workflow-trusted-catalogs.json"
            document = strict_json_bytes(path.read_bytes(), source=str(path))
            document["catalogs"]["claude-code-local-skills"] = "sha256:" + "0" * 64
            path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        def trust_schema_tamper(skill: Path) -> None:
            path = skill / "assets/workflow-trusted-catalogs.json"
            document = strict_json_bytes(path.read_bytes(), source=str(path))
            document["schema"] = "workflow-trusted-catalogs/tampered"
            path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        def trust_missing(skill: Path) -> None:
            (skill / "assets/workflow-trusted-catalogs.json").unlink()

        cases = (
            ("catalog-content", catalog_content_tamper, "CATALOG-CONTENT-MISMATCH"),
            ("catalog-missing", catalog_missing, "CATALOG-ABSENT"),
            ("registry-drift", registry_byte_drift, "REGISTRY-PIN-DIVERGENT"),
            ("trust-pin", trust_pin_tamper, "CATALOG-SHA256-MISMATCH"),
            ("trust-schema", trust_schema_tamper, "TRUSTED-CATALOGS-SCHEMA"),
            ("trust-missing", trust_missing, "TRUSTED-CATALOGS-UNREADABLE"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for name, mutate, expected_code in cases:
                with self.subTest(case=name):
                    skill = copy_skill(parent, f"skill-{name}")
                    mutate(skill)
                    root = self.fresh_copy(parent, f"root-{name}")
                    before = file_snapshot(root)
                    process, payload = self.activate(
                        3, root=root, program=skill / "scripts/grill_workspace.py"
                    )
                    self.assert_blocked_unchanged(root, before, process, payload, expected_code)

    def test_every_closed_skill_reason_and_stale_code_cross_public_boundary_without_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            skill = copy_skill(parent)
            step_skills = skill / "scripts/grill_core/step_skills.py"
            production_source = step_skills.read_text(encoding="utf-8")
            program = skill / "scripts/grill_workspace.py"

            cases = [
                ("BLOCKED_CAPABILITY", reason, reason.replace("_", "-"))
                for reason in MAPPED_SKILL_REASONS
            ]
            cases.append(("STALE_SKILL_RESOLUTION", "UNLISTED-STALE-DETAIL", "STALE-SKILL-RESOLUTION"))
            for index, (internal_code, reason, expected_code) in enumerate(cases):
                with self.subTest(internal_code=internal_code, reason=reason):
                    injection = (
                        "\n# Contract-only copied-plugin fault injection.\n"
                        "def resolve_shipped_workflow_skills(\n"
                        "    step_ids, runtime, registry_sha256_expected, *, registry, catalog\n"
                        "):\n"
                        f"    raise SkillResolutionError({internal_code}, {reason!r})\n"
                    )
                    step_skills.write_text(production_source + injection, encoding="utf-8")
                    shutil.rmtree(step_skills.parent / "__pycache__", ignore_errors=True)
                    root = self.fresh_copy(parent, f"mapped-{index}")
                    before = file_snapshot(root)
                    process, payload = self.activate(3, root=root, program=program)
                    self.assert_blocked_unchanged(root, before, process, payload, expected_code)

    def test_unknown_skill_reason_uses_closed_fallback_and_never_reaches_stdout(self) -> None:
        secret_reason = "FUTURE_INTERNAL_REASON_WITH_SECRET_DETAIL"
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            skill = copy_skill(parent)
            step_skills = skill / "scripts/grill_core/step_skills.py"
            step_skills.write_text(
                step_skills.read_text(encoding="utf-8")
                + "\n# Contract-only copied-plugin fault injection.\n"
                + "def resolve_shipped_workflow_skills(\n"
                + "    step_ids, runtime, registry_sha256_expected, *, registry, catalog\n"
                + "):\n"
                + f"    raise SkillResolutionError(BLOCKED_CAPABILITY, {secret_reason!r})\n",
                encoding="utf-8",
            )
            shutil.rmtree(step_skills.parent / "__pycache__", ignore_errors=True)
            root = self.fresh_copy(parent, "fallback")
            before = file_snapshot(root)
            process, payload = self.activate(
                3, root=root, program=skill / "scripts/grill_workspace.py"
            )
            self.assert_blocked_unchanged(root, before, process, payload, "BLOCKED-CAPABILITY")
            self.assertNotIn(secret_reason, json.dumps(payload, sort_keys=True))

    def test_unavailable_safe_directory_descriptors_stay_one_json_and_no_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            skill = copy_skill(parent)
            gauntlet = skill / "scripts/grill_core/gauntlet.py"
            gauntlet.write_text(
                gauntlet.read_text(encoding="utf-8")
                + "\n# Contract-only copied-plugin platform fault.\n"
                + "def acquire_config_lock(root):\n"
                + "    raise _fail('SAFE-PATH-UNAVAILABLE', 'dir-fd unavailable')\n",
                encoding="utf-8",
            )
            root = self.fresh_copy(parent, "unsafe-dirfd")
            before = file_snapshot(root)
            process, payload = self.activate(
                3, root=root, program=skill / "scripts/grill_workspace.py"
            )
            self.assert_blocked_unchanged(root, before, process, payload, "SAFE-PATH-UNAVAILABLE")

    def test_status_projects_eligible_without_creating_activation_or_locks(self) -> None:
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-status")
        self.assert_status_projection(process, payload, "ELIGIBLE")
        self.assert_control_read_only(self.root, before)
        self.assertFalse(self.config.exists())

    def test_status_projects_activated_for_current_matching_record_read_only(self) -> None:
        activated_process, activated = self.activate(3)
        self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-status")
        self.assert_status_projection(process, payload, "ACTIVATED")
        self.assert_control_read_only(self.root, before)

    def test_status_stale_identity_takes_precedence_over_blocked_current_proof(self) -> None:
        activated_process, activated = self.activate(3)
        self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
        item_path = self.root / ".grill/work-items" / WORK_ID / "WORK-ITEM.json"
        item = strict_json_bytes(item_path.read_bytes(), source=str(item_path))
        item["external_identity_change"] = {"preserve": True}
        item_path.write_text(json.dumps(item, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        # The recorded work-item digest is now stale, while V2 also makes the
        # live eligibility proof fail. STALE must win over BLOCKED.
        (self.root / "WORKFLOW.md").write_bytes(WORKFLOW_V2_TEMPLATE.read_bytes())
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-status")
        self.assert_status_projection(process, payload, "STALE")
        self.assert_control_read_only(self.root, before)

    def test_status_malformed_current_work_item_is_identity_stale_after_activation(self) -> None:
        activated_process, activated = self.activate(3)
        self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
        item_path = self.root / ".grill/work-items" / WORK_ID / "WORK-ITEM.json"
        item_path.write_bytes(b'{"malformed":')
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-status")
        self.assert_status_projection(process, payload, "STALE")
        self.assertEqual(payload.get("reason"), "IDENTITY-STALE")
        self.assert_control_read_only(self.root, before)

    def test_status_projects_isolated_workflow_drift_as_identity_stale(self) -> None:
        activated_process, activated = self.activate(3)
        self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
        (self.root / "WORKFLOW.md").write_bytes((self.root / "WORKFLOW.md").read_bytes() + b"\n")
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-status")
        self.assert_status_projection(process, payload, "STALE")
        self.assertEqual(payload.get("reason"), "IDENTITY-STALE")
        self.assert_control_read_only(self.root, before)

    def test_status_projects_each_shipped_registry_catalog_and_trust_drift_as_stale(self) -> None:
        mutations = (
            ("registry", "assets/workflow-step-skills.json"),
            ("catalog", "assets/claude-code-local-skills.catalog.json"),
            ("trust", "assets/workflow-trusted-catalogs.json"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for name, relative in mutations:
                with self.subTest(identity=name):
                    skill = copy_skill(parent, f"skill-{name}")
                    root = self.fresh_copy(parent, f"root-{name}")
                    program = skill / "scripts/grill_workspace.py"
                    activated_process, activated = self.activate(3, root=root, program=program)
                    self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
                    identity_path = skill / relative
                    identity_path.write_bytes(identity_path.read_bytes() + b"\n")
                    before = file_snapshot(root)
                    process, payload = self.control("gauntlet-status", root=root, program=program)
                    self.assert_status_projection(process, payload, "STALE")
                    self.assertEqual(payload.get("reason"), "IDENTITY-STALE")
                    self.assert_control_read_only(root, before)

    def test_status_projects_valid_subject_proof_failure_as_status_blocked_with_reason(self) -> None:
        (self.root / "WORKFLOW.md").write_bytes(WORKFLOW_V2_TEMPLATE.read_bytes())
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-status")
        self.assert_status_projection(process, payload, "BLOCKED")
        self.assert_control_read_only(self.root, before)

    def test_status_invalid_root_and_item_remain_top_level_command_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid_root = Path(temporary) / "not-a-repository"
            invalid_root.mkdir()
            invalid_before = file_snapshot(invalid_root)
            process, payload = self.control("gauntlet-status", root=invalid_root)
            self.assertEqual(process.stderr, "")
            self.assertEqual(process.returncode, 2, payload)
            self.assertEqual((payload.get("verdict"), payload.get("code")), ("BLOCKED", "INVALID-ROOT"))
            self.assertNotIn("activation_state", payload)
            self.assertEqual(file_snapshot(invalid_root), invalid_before)

        for work_id, code in (("bad/id", "INVALID-WORK-ID"), ("missing-item-a1b2", "WORK-ITEM-MISSING")):
            with self.subTest(work_id=work_id):
                before = file_snapshot(self.root)
                process, payload = self.control("gauntlet-status", work_id=work_id)
                self.assertEqual(process.stderr, "")
                self.assertNotEqual(process.returncode, 0, payload)
                self.assertEqual((payload.get("verdict"), payload.get("code")), ("BLOCKED", code), payload)
                self.assertNotIn("activation_state", payload)
                self.assert_control_read_only(self.root, before)

    def test_status_loader_failure_before_projection_is_top_level_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            skill = copy_skill(parent)
            gauntlet = skill / "scripts/grill_core/gauntlet.py"
            gauntlet.write_text("def broken(:\n", encoding="utf-8")
            shutil.rmtree(gauntlet.parent / "__pycache__", ignore_errors=True)
            before = file_snapshot(self.root)
            process, payload = self.control(
                "gauntlet-status", program=skill / "scripts/grill_workspace.py"
            )
            self.assertEqual(process.stderr, "")
            self.assertEqual(process.returncode, 2, payload)
            self.assertEqual(
                (payload.get("verdict"), payload.get("code")),
                ("BLOCKED", "GRILL-CORE-UNAVAILABLE"),
                payload,
            )
            self.assertNotIn("activation_state", payload)
            self.assert_control_read_only(self.root, before)

    def test_all_controls_validate_missing_work_item_before_status_or_phase_boundary(self) -> None:
        missing_id = "missing-item-a1b2"
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for command in ("gauntlet-status", "gauntlet-run", "gauntlet-resume", "gauntlet-cleanup"):
                with self.subTest(command=command):
                    root = self.fresh_copy(parent, command)
                    before = file_snapshot(root)
                    process, payload = self.control(command, root=root, work_id=missing_id)
                    self.assertEqual(process.stderr, "")
                    self.assertEqual(process.returncode, 2, payload)
                    self.assertEqual(
                        (payload.get("verdict"), payload.get("code")),
                        ("BLOCKED", "WORK-ITEM-MISSING"),
                        payload,
                    )
                    self.assertNotIn("activation_state", payload)
                    self.assertEqual(file_snapshot(root), before)
                    self.assertFalse((root / ".grill/.gauntlet-config.lock").exists())
                    self.assertFalse((root / ".grill/locks" / f"{missing_id}.lock").exists())

    def test_run_requires_activation_and_never_infers_or_creates_one(self) -> None:
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-run")
        self.assert_control_blocked(process, payload, "ACTIVATION-REQUIRED")
        self.assert_control_read_only(self.root, before)
        self.assertFalse(self.config.exists())

    def test_run_creates_durable_admission_without_worker_or_worktree_artifacts(self) -> None:
        activated_process, activated = self.activate(3)
        self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
        branch_before = git(self.root, "branch", "--show-current")
        worktrees_before = git(self.root, "worktree", "list", "--porcelain")
        status_before = git(self.root, "status", "--porcelain")
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-run")
        self.assertEqual(process.stderr, "")
        self.assertEqual(process.returncode, 0, payload)
        self.assertEqual(payload.get("verdict"), "RUN-CREATED", payload)
        self.assertEqual(payload.get("work_id"), WORK_ID, payload)
        self.assertRegex(payload.get("run_id", ""), r"^run-[A-Za-z0-9][A-Za-z0-9._-]*$")
        self.assertRegex(payload.get("base_commit", ""), r"^[0-9a-f]{40}$")

        # V2's activation/configuration contract remains unchanged: admission
        # must not create a worker, worktree, or project-side execution file.
        # Its sole intentional mutation is the common-Git durable Store.
        after = file_snapshot(self.root)
        self.assertEqual(
            {path: value for path, value in after.items() if not path.startswith(".git/grill/")},
            before,
        )
        self.assertFalse((self.root / ".grill" / "workers").exists())
        self.assertFalse((self.root / ".grill" / "runs").exists())
        self.assertEqual(git(self.root, "branch", "--show-current"), branch_before)
        self.assertEqual(git(self.root, "worktree", "list", "--porcelain"), worktrees_before)
        self.assertEqual(git(self.root, "status", "--porcelain"), status_before)

        paths = store.store_paths(self.root)
        snapshot = store.read_snapshot(self.root)
        run = snapshot.document["work_items"][WORK_ID]["gauntlet"]["runs"][payload["run_id"]]
        self.assertEqual(run["state"], "ADMITTED")
        self.assertEqual(run["workers"], {})
        self.assertEqual(run["admission"]["base_commit"], payload["base_commit"])

        admitted = [event for event in store.read_events(self.root) if event.get("event") == "gauntlet.run.admitted"]
        self.assertEqual(len(admitted), 1)
        event = admitted[0]
        self.assertEqual((event["work_id"], event["run_id"], event["base_commit"]), (WORK_ID, payload["run_id"], payload["base_commit"]))
        receipt = store.receipt_path(self.root, "runtime", f"gauntlet-run-admit-{payload['run_id']}")
        self.assertTrue(receipt.is_file())
        receipt_payload = strict_json_bytes(receipt.read_bytes(), source=str(receipt))
        self.assertEqual(receipt_payload["run_id"], payload["run_id"])
        self.assertEqual(store.jcs_sha256(receipt_payload), event["receipt_sha256"])
        self.assertFalse((paths.locks / store.PENDING_TRANSITION_NAME).exists())

    def test_run_revalidates_and_blocks_stale_activation_without_artifacts(self) -> None:
        activated_process, activated = self.activate(3)
        self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
        (self.root / "WORKFLOW.md").write_bytes((self.root / "WORKFLOW.md").read_bytes() + b"\n")
        branch_before = git(self.root, "branch", "--show-current")
        worktrees_before = git(self.root, "worktree", "list", "--porcelain")
        status_before = git(self.root, "status", "--porcelain")
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-run")
        self.assert_control_blocked(process, payload, "IDENTITY-STALE")
        self.assert_control_read_only(self.root, before)
        self.assertEqual(git(self.root, "branch", "--show-current"), branch_before)
        self.assertEqual(git(self.root, "worktree", "list", "--porcelain"), worktrees_before)
        self.assertEqual(git(self.root, "status", "--porcelain"), status_before)

    def test_cleanup_without_activation_always_stops_at_scheduler_boundary(self) -> None:
        before = file_snapshot(self.root)
        process, payload = self.control("gauntlet-cleanup")
        self.assert_control_blocked(process, payload, "SCHEDULING-NOT-AVAILABLE")
        self.assert_control_read_only(self.root, before)
        self.assertFalse(self.config.exists())

    def test_resume_absent_and_stale_activation_both_require_current_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            absent_root = self.fresh_copy(parent, "absent")
            absent_before = file_snapshot(absent_root)
            process, payload = self.control("gauntlet-resume", root=absent_root)
            self.assert_control_blocked(process, payload, "ACTIVATION-REQUIRED")
            self.assert_control_read_only(absent_root, absent_before)

            stale_root = self.fresh_copy(parent, "stale")
            activated_process, activated = self.activate(3, root=stale_root)
            self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
            (stale_root / "WORKFLOW.md").write_bytes(WORKFLOW_V2_TEMPLATE.read_bytes())
            stale_before = file_snapshot(stale_root)
            process, payload = self.control("gauntlet-resume", root=stale_root)
            self.assert_control_blocked(process, payload, "ACTIVATION-REQUIRED")
            self.assert_control_read_only(stale_root, stale_before)

    def test_resume_current_and_cleanup_stop_at_scheduler_boundary_without_deleting(self) -> None:
        activated_process, activated = self.activate(3)
        self.assert_activation_output(activated_process, activated, "ACTIVATED", 3)
        sentinels = {
            self.root / ".grill/runs/existing-run.json": b'{"preserve":true}\n',
            self.root / ".grill/workers/existing-worker.json": b'{"preserve":true}\n',
            self.root / "unrelated-user-file.txt": b"must not be deleted\n",
        }
        for path, data in sentinels.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        branch_before = git(self.root, "branch", "--show-current")
        worktrees_before = git(self.root, "worktree", "list", "--porcelain")

        for command in ("gauntlet-resume", "gauntlet-cleanup"):
            with self.subTest(command=command):
                before = file_snapshot(self.root)
                process, payload = self.control(command)
                self.assert_control_blocked(process, payload, "SCHEDULING-NOT-AVAILABLE")
                self.assert_control_read_only(self.root, before)
                for path, data in sentinels.items():
                    self.assertEqual(path.read_bytes(), data)
                self.assertEqual(git(self.root, "branch", "--show-current"), branch_before)
                self.assertEqual(git(self.root, "worktree", "list", "--porcelain"), worktrees_before)


if __name__ == "__main__":
    unittest.main()
