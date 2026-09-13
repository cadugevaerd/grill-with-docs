#!/usr/bin/env python3
import contextlib, hashlib, io, json, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "plugin/skills/grill-with-docs/scripts"
sys.path.insert(0, str(SCRIPTS))
from grill_core.agent_runtime import RuntimeBoundary, RuntimeError
from grill_core import store
import grill_workspace


def observation(**changes):
    source = b"provider observation"
    data = {"schema":"grill-agent-observation/v1","adapter":"orca","provider":"orca","handle":"h","incarnation":"i","runtime_instance":"r","host":"host","owner_dispatch":"d","source_ref":"source","source_sha256":"","requested_model":"gpt-6-astra","requested_effort":"high","effective_model":"gpt-6-astra","effective_effort":"high","resolved_model_id":"gpt-6-astra","activity":"idle","close":"not_requested"}
    data.update(changes); data["source_sha256"] = hashlib.sha256(source).hexdigest()
    return source, json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


class AgentOrchestrationContract(unittest.TestCase):
    def run_cli(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = grill_workspace.main(list(argv))
        return code, json.loads(output.getvalue())

    def fixture(self):
        temp = tempfile.TemporaryDirectory(); root = Path(temp.name)
        for args in (("init",), ("config", "user.email", "test@example.invalid"), ("config", "user.name", "Test")):
            subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.DEVNULL)
        (root / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-m", "fixture"], check=True, stdout=subprocess.DEVNULL)
        return temp, root

    def test_rollout_and_canonical_pins(self):
        temp, root = self.fixture()
        with temp:
            code, init = self.run_cli("init", str(root), "--type", "feature", "--slug", "x", "--work-id", "work-x", "--runtime", "codex", "--skip-backlog")
            self.assertEqual(code, 0); self.assertEqual(init["orchestration"], "INITIALIZED")
            before = store.read_snapshot(root).content_sha256
            args = ("gauntlet-orchestration-adopt", str(root), "--work-id", "work-x", "--runtime", "codex", "--session-ref", "observed-session", "--scope-file", "src/a.py")
            code, preview = self.run_cli(*args); self.assertEqual(code, 0); self.assertEqual(preview["verdict"], "PREVIEW")
            self.assertEqual(store.read_snapshot(root).content_sha256, before)
            self.assertEqual(self.run_cli(*args, "--apply")[0], 2)
            code, adopted = self.run_cli(*args, "--apply", "--expected-sha256", preview["expected_sha256"])
            self.assertEqual(code, 0); self.assertEqual(adopted["verdict"], "ORCHESTRATION-ADOPTED")
            self.assertEqual(self.run_cli(*args, "--apply", "--expected-sha256", preview["expected_sha256"])[1]["verdict"], "REUSED")
            document = store.read_snapshot(root).document
            context = document["agent_orchestration"]["work_items"]["work-x"]["contexts"][adopted["context_id"]]
            self.assertIsNone(context["activation"]); self.assertIsNone(context["campaign"]); self.assertEqual(context["scheduler_runs"], {})
            stale = self.run_cli(*args, "--scope-file", "src/b.py", "--apply", "--expected-sha256", preview["expected_sha256"])
            self.assertEqual(stale[0], 2)

    def test_runtime_requires_actual_observation_and_full_identity(self):
        raw = observation(); boundary = RuntimeBoundary(lambda:raw, lambda:raw, lambda:raw, lambda:observation(close="closed", activity="exited"))
        self.assertEqual(boundary.verified("gpt-6-astra", "high")["effective_model"], "gpt-6-astra")
        bad = observation(adapter="invented", effective_model="unresolved-alias")
        with self.assertRaises(RuntimeError): RuntimeBoundary(lambda:bad, lambda:bad, lambda:bad, lambda:bad).verified("gpt-6-astra", "high")


if __name__ == "__main__": unittest.main()
