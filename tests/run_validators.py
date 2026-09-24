#!/usr/bin/env python3
"""Run the full validator suite or the bounded CI profiles."""
from __future__ import annotations

import argparse
from pathlib import Path
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("full", "essential", "portability"), default="full")
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
    for validator, tests in checks:
        print(f"==> {validator.name}", flush=True)
        check_started = perf_counter()
        result = subprocess.run([sys.executable, str(validator), *tests], cwd=ROOT.parent)
        print(f"<== {validator.name}: {perf_counter() - check_started:.1f}s", flush=True)
        if result.returncode:
            print(f"Suite duration: {perf_counter() - started:.1f}s", flush=True)
            return result.returncode
    print(f"Suite duration: {perf_counter() - started:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
