#!/usr/bin/env python3
"""Run the full validator suite or the bounded CI profiles."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parent
VALIDATORS = tuple(sorted(ROOT.glob("validate_*.py")))
PORTABILITY_TESTS = (
    "test_rename_child_moves_directory_and_rejects_preexisting_target",
    "test_init_isolates_same_slug_and_never_writes_global",
    "test_init_reuse_identity_conflict_and_immutable_tamper",
    "test_migrate_preview_apply_preserves_files_directories_and_reuses",
    "test_reconcile_apply_is_byte_idempotent_without_mtime_churn",
    "test_hotfix_fast_is_self_contained_and_feature_remains_plan_only",
    "test_filesystem_json_normalizes_byte_paths_and_native_command_parsing",
    "test_audit_supports_artifact_root_outside_project_root",
)
ESSENTIAL = (
    "validate_agent_orchestration_contract.py",
    "validate_attestation_contract.py",
    "validate_backlog_contract.py",
    "validate_bump_gate_contract.py",
    "validate_contract.py",
    "validate_dependencies_contract.py",
    "validate_distribution.py",
    "validate_efficiency_contract.py",
    "validate_extension_detection.py",
    "validate_orchestrator_store_contract.py",
    "validate_partition_contract.py",
    "validate_publish_contract.py",
    "validate_runner_profiles.py",
    "validate_step_skill_registry_contract.py",
    "validate_tier_model_binding_contract.py",
    "validate_triage_contract.py",
    "validate_workflow_versions_contract.py",
)


# init refuses without OPENROUTER_API_KEY; validators only check presence and
# never reach the network, so a placeholder keeps every init-based test honest.
ENV = {**os.environ, "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY") or "test-placeholder-not-a-key"}


# Parallel mode only: the slowest validators start first so they set the
# critical path, and the single 78-test workspace class is cut into batches.
SLOW_FIRST = (
    "validate_workspace_contract.py",
    "validate_gauntlet_converge_contract.py",
    "validate_checkpoint_contract.py",
    "validate_gauntlet_scheduler_contract.py",
    "validate_gauntlet_activation_contract.py",
)
SPLIT = {"validate_workspace_contract.py": ("WorkspaceV2Contract", 6)}


def split_checks(checks: list[tuple[Path, tuple[str, ...]]]) -> list[tuple[Path, tuple[str, ...]]]:
    out: list[tuple[Path, tuple[str, ...]]] = []
    for path, tests in checks:
        if path.name not in SPLIT or tests:
            out.append((path, tests))
            continue
        cls, batches = SPLIT[path.name]
        names = re.findall(r"^    def (test_\w+)", path.read_text(encoding="utf-8"), re.M)
        out.extend((path, tuple(f"{cls}.{n}" for n in names[i::batches])) for i in range(batches))
    rank = {name: i for i, name in enumerate(SLOW_FIRST)}
    return sorted(out, key=lambda check: rank.get(check[0].name, len(rank)))


def run_parallel(checks: list[tuple[Path, tuple[str, ...]]], jobs: int, started: float) -> int:
    failed = 0

    def run(check: tuple[Path, tuple[str, ...]]) -> tuple[Path, int, str, float]:
        begin = perf_counter()
        result = subprocess.run([sys.executable, str(check[0]), *check[1]], cwd=ROOT.parent, env=ENV,
                                capture_output=True, text=True)
        return check[0], result.returncode, (result.stdout or "") + (result.stderr or ""), perf_counter() - begin

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for future in as_completed([pool.submit(run, check) for check in split_checks(checks)]):
            path, code, output, took = future.result()
            print(f"==> {path.name}\n{output}<== {path.name}: {took:.1f}s", flush=True)
            failed = failed or code
    print(f"Suite duration: {perf_counter() - started:.1f}s", flush=True)
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("full", "essential", "portability"), default="full")
    # 1 keeps CI serial and stop-on-first-failure; 0 means one job per CPU.
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args(argv)
    if args.suite == "full":
        checks = [(validator, ()) for validator in VALIDATORS]
    elif args.suite == "essential":
        checks = [(ROOT / name, ()) for name in ESSENTIAL]
        checks.append((ROOT / "validate_workspace_contract.py", tuple(f"WorkspaceV2Contract.{name}" for name in PORTABILITY_TESTS)))
    else:
        checks = [(ROOT / "validate_distribution.py", ())]
        checks.append((ROOT / "validate_workspace_contract.py", tuple(f"WorkspaceV2Contract.{name}" for name in PORTABILITY_TESTS)))
    if not checks or any(not path.is_file() for path, _ in checks):
        print("No validators found", file=sys.stderr)
        return 2
    started = perf_counter()
    if args.jobs != 1:
        return run_parallel(checks, args.jobs or os.cpu_count() or 1, started)
    for validator, tests in checks:
        print(f"==> {validator.name}", flush=True)
        check_started = perf_counter()
        result = subprocess.run([sys.executable, str(validator), *tests], cwd=ROOT.parent, env=ENV)
        print(f"<== {validator.name}: {perf_counter() - check_started:.1f}s", flush=True)
        if result.returncode:
            print(f"Suite duration: {perf_counter() - started:.1f}s", flush=True)
            return result.returncode
    print(f"Suite duration: {perf_counter() - started:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
