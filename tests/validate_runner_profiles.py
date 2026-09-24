"""Keep CI's bounded profiles explicit and preserve the full local suite."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main, mock
import contextlib
import io

import run_validators


class RunnerProfiles(TestCase):
    def run_suite(self, suite: str, failure: str | None = None) -> tuple[int, list[list[str]]]:
        called = []

        def run(command, **kwargs):
            called.append(command)
            return SimpleNamespace(returncode=7 if Path(command[1]).name == failure else 0)

        with mock.patch.object(run_validators.subprocess, "run", side_effect=run):
            code = run_validators.main(["--suite", suite])
        return code, called

    def test_essential_runs_selected_contracts_and_portability_once(self):
        code, commands = self.run_suite("essential")
        names = [Path(command[1]).name for command in commands]
        self.assertEqual(code, 0)
        self.assertEqual(names, [*run_validators.ESSENTIAL, "validate_workspace_contract.py"])
        self.assertEqual(names.count("validate_distribution.py"), 1)
        self.assertEqual(commands[-1][2:], [f"WorkspaceV2Contract.{name}" for name in run_validators.PORTABILITY_TESTS])

    def test_portability_runs_only_distribution_and_workspace_smoke(self):
        code, commands = self.run_suite("portability")
        names = [Path(command[1]).name for command in commands]
        self.assertEqual((code, names), (0, ["validate_distribution.py", "validate_workspace_contract.py"]))
        self.assertEqual(commands[-1][2:], [f"WorkspaceV2Contract.{name}" for name in run_validators.PORTABILITY_TESTS])

    def test_full_discovers_all_validators_and_failure_stops_the_suite(self):
        code, commands = self.run_suite("full", "validate_backlog_contract.py")
        names = [Path(command[1]).name for command in commands]
        self.assertEqual(code, 7)
        self.assertEqual(names, [path.name for path in run_validators.VALIDATORS if path.name <= "validate_backlog_contract.py"])

    def test_unknown_suite_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
            run_validators.main(["--suite", "unknown"])
        self.assertEqual(failure.exception.code, 2)


if __name__ == "__main__":
    main()
