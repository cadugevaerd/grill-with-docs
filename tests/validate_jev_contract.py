#!/usr/bin/env python3
"""Contract for `grill_core/jev.py` and `grill_workspace.py decide`.

No network: every call goes through a fake opener or a patched Transport.post.
The wire shapes are checked against the OpenRouter OpenAPI example stored in
tests/fixtures/jev/openapi-example.json, which came from the provider, not from
this code.
"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plugin/skills/grill-with-docs/scripts"
SCRIPT = SCRIPTS / "grill_workspace.py"
FIXTURE = json.loads((REPO / "tests/fixtures/jev/openapi-example.json").read_text(encoding="utf-8"))
KEY = "sk-or-test-secret-never-printed"
# grill_core modules import `grill_core.*`; the CLI gets this path as its script dir.
sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


jev = load("jev_under_test", SCRIPTS / "grill_core/jev.py")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def answer_all(questions: dict, noul: float = 0.97, confidence: float = 0.95, pick=None) -> dict:
    """Build a Decisions response in the provider's shape for the questions asked."""
    answers = {}
    for key, question in questions.items():
        local = key.split("__", 1)[-1]  # decide_many namespaces keys by kind
        if question["type"] == "noul":
            answers[key] = {"type": "noul", "noul": noul(local) if callable(noul) else noul}
        else:
            choice = (pick or {}).get(local, next(iter(question["criteria"])))
            answers[key] = {"type": "choice", "choice": choice, "confidence": confidence,
                            "probabilities": {c: 0 for c in question["criteria"]}}
    return {"model": "typesafe/jev-1.13-20260917", "answers": answers,
            "usage": {"input_tokens": 1, "output_tokens": 1}}


class FakeTransport:
    def __init__(self, **kwargs):
        self.kwargs, self.bodies = kwargs, []

    def post(self, url, body):
        self.bodies.append(body)
        return answer_all(body["questions"], **self.kwargs)


class ProviderShape(unittest.TestCase):
    def test_openapi_example_response_is_read_as_the_provider_documents(self):
        questions = FIXTURE["request"]["questions"]
        response = FIXTURE["response"]
        confident = jev.interpret("fixture", questions, response, 0.7, [])
        self.assertEqual(confident["decided_by"], "jev")
        self.assertEqual(confident["model"], "typesafe/jev-1.13-20260917")
        self.assertAlmostEqual(confident["confidence"]["is_bug"], 0.96)
        self.assertAlmostEqual(confident["confidence"]["team"], 0.75)
        partial = jev.interpret("fixture", questions, response, 0.8, [])
        self.assertEqual(partial["decided_by"], "partial")
        self.assertIsNone(partial["result"])
        self.assertEqual(partial["decided"], {"is_bug": True, "urgency": 1.99})
        self.assertEqual(partial["pending"], ["team"])
        self.assertEqual(partial["hint"], {"team": "payments"})
        none = jev.interpret("fixture", questions, response, 0.999, [])
        self.assertEqual((none["decided_by"], none["decided"]), ("agent", {}))

    def test_live_probe_response_is_read_like_the_documented_one(self):
        live = json.loads((REPO / "tests/fixtures/jev/live-response.json").read_text(encoding="utf-8"))["response"]
        decision = jev.interpret("fixture", FIXTURE["request"]["questions"], live, 0.7, [])
        self.assertEqual(decision["decided_by"], "jev")
        self.assertEqual(set(decision["confidence"]), set(FIXTURE["request"]["questions"]))

    def test_catalog_questions_use_the_request_shape_of_the_example(self):
        catalog = jev.load_catalog()
        allowed = {"type", "instructions", "criteria"}
        for kind, spec in catalog["kinds"].items():
            for question in jev.build_questions(spec, ["security"]).values():
                question = jev.wire(question)
                self.assertEqual(set(question), allowed, kind)
                self.assertIn(question["type"], {"noul", "choice", "score"})
                if question["type"] == "noul":
                    self.assertEqual(set(question["criteria"]), {"true", "false"})
                if question["type"] == "choice":
                    self.assertLessEqual(len(question["criteria"]), 255)
        self.assertEqual(catalog["model"], FIXTURE["request"]["model"])

    def test_malformed_answers_fail_closed(self):
        questions = FIXTURE["request"]["questions"]
        for mutate in (
            lambda r: r["answers"].pop("team"),
            lambda r: r["answers"]["team"].update(choice="nobody"),
            lambda r: r["answers"]["is_bug"].update(noul=1.5),
            lambda r: r["answers"]["is_bug"].update(type="choice"),
            lambda r: r.pop("answers"),
        ):
            response = json.loads(json.dumps(FIXTURE["response"]))
            mutate(response)
            with self.assertRaises(jev.JevError) as caught:
                jev.interpret("fixture", questions, response, 0.5, [])
            self.assertEqual(caught.exception.code, "JEV-RESPONSE-INVALID")


class TransportContract(unittest.TestCase):
    def test_missing_key_refuses_before_any_request(self):
        opener = mock.Mock()
        with self.assertRaises(jev.JevError) as caught:
            jev.Transport({}, opener).post("https://x", {})
        self.assertEqual(caught.exception.code, "OPENROUTER-KEY-REQUIRED")
        opener.assert_not_called()

    def test_request_carries_bearer_and_body(self):
        seen = {}

        def opener(request, timeout):
            seen["auth"] = request.get_header("Authorization")
            seen["body"] = json.loads(request.data)
            seen["timeout"] = timeout
            return FakeResponse(json.dumps(FIXTURE["response"]).encode())

        result = jev.Transport({jev.KEY_ENV: KEY}, opener).post("https://x", FIXTURE["request"])
        self.assertEqual(seen["auth"], f"Bearer {KEY}")
        self.assertEqual(seen["body"], FIXTURE["request"])
        self.assertEqual(seen["timeout"], jev.TIMEOUT)
        self.assertEqual(result, FIXTURE["response"])

    def test_failures_map_to_fail_closed_codes_without_leaking_the_key(self):
        def http(code):
            def opener(request, timeout):
                raise urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(b"{}"))
            return opener

        def raising(error):
            def opener(request, timeout):
                raise error
            return opener

        cases = {
            "OPENROUTER-KEY-INVALID": http(401),
            "OPENROUTER-CREDIT-EXHAUSTED": http(402),
            "JEV-UNAVAILABLE": http(503),
        }
        for code, opener in cases.items():
            with self.subTest(code=code), self.assertRaises(jev.JevError) as caught:
                jev.Transport({jev.KEY_ENV: KEY}, opener).post("https://x", {})
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn(KEY, str(caught.exception) + caught.exception.detail)
        for opener in (raising(urllib.error.URLError("down")), raising(TimeoutError()),
                       lambda request, timeout: FakeResponse(b"not json")):
            with self.assertRaises(jev.JevError) as caught:
                jev.Transport({jev.KEY_ENV: KEY}, opener).post("https://x", {})
            self.assertEqual(caught.exception.code, "JEV-UNAVAILABLE")


class KindMapping(unittest.TestCase):
    def test_step_assessment_selects_risks_above_half(self):
        risks = ["security", "frontend"]
        transport = FakeTransport(noul=lambda k: 0.02 if k == "risk_frontend" else 0.98)
        decision = jev.decide("step-assessment", {"files": {}}, risks, transport)
        self.assertEqual(decision["decided_by"], "jev")
        self.assertEqual(decision["result"], {"new_how": True, "risks": ["security"]})
        self.assertEqual(set(transport.bodies[0]["questions"]),
                         {"step_assessment__new_how", "step_assessment__risk_security", "step_assessment__risk_frontend"})

    def test_one_doubtful_question_leaves_only_that_question_to_the_agent(self):
        decision = jev.decide("step-assessment", {"files": {}}, ["security"],
                              FakeTransport(noul=lambda k: 0.6 if k == "new_how" else 0.99))
        self.assertEqual(decision["decided_by"], "partial")
        self.assertIsNone(decision["result"])
        self.assertEqual(decision["decided"], {"risk_security": True})
        self.assertEqual(decision["pending"], ["new_how"])

    def test_one_confident_uncovered_requirement_is_a_no_go_even_when_partial(self):
        probs = {"req_fr_001": 0.001, "req_fr_002": 0.6}
        decision = jev.decide("spec-coverage", {}, ["FR-001", "FR-002"], FakeTransport(noul=probs.get))
        self.assertEqual(decision["decided_by"], "partial")
        self.assertEqual(decision["result"], {"uncovered": ["FR-001"], "verdict": "NO-GO"})
        doubtful = jev.decide("spec-coverage", {}, ["FR-001", "FR-002"],
                              FakeTransport(noul={"req_fr_001": 0.999, "req_fr_002": 0.6}.get))
        self.assertIsNone(doubtful["result"])

    def test_triage_groups_dq_and_coverage(self):
        triage = jev.decide("triage", {}, [], FakeTransport(pick={"route": "bugfix", "severity": "high"}))
        self.assertEqual(triage["result"], {"route": "bugfix", "severity": "high"})
        groups = jev.decide("partition-groups", {}, [], FakeTransport(pick={"groups": "3"}))
        self.assertEqual(groups["result"], {"groups": 3})
        dqs = ["DQ-1", "DQ-2", "DQ-3", "DQ-4", "DQ-5"]
        probs = {"dq_dq_1": 0.9, "dq_dq_2": 0.05, "dq_dq_3": 0.99, "dq_dq_4": 0.95, "dq_dq_5": 0.97}
        batch = jev.decide("dq-batch", {}, dqs, FakeTransport(noul=probs.get))
        self.assertEqual(batch["result"], {"selected": ["DQ-3", "DQ-5", "DQ-4"]})
        reqs = list(jev.requirements("**FR-001** a\n**FR-002** b\nSC-001 c FR-001"))
        self.assertEqual(reqs, ["FR-001", "FR-002", "SC-001"])
        coverage = jev.decide("spec-coverage", {}, reqs,
                              FakeTransport(noul=lambda k: 0.01 if k == "req_fr_002" else 0.99))
        self.assertEqual(coverage["result"], {"uncovered": ["FR-002"], "verdict": "NO-GO"})

    def test_state_budget_and_unknown_kind_are_refused(self):
        with self.assertRaises(jev.JevError) as caught:
            jev.decide("triage", {"files": {"a": "x" * jev.MAX_STATE_CHARS}}, [], FakeTransport())
        self.assertEqual(caught.exception.code, "JEV-STATE-TOO-LARGE")
        with self.assertRaises(jev.JevError) as caught:
            jev.decide("nope", {}, [], FakeTransport())
        self.assertEqual(caught.exception.code, "JEV-KIND-UNKNOWN")
        with self.assertRaises(jev.JevError) as caught:
            jev.decide("dq-batch", {}, [], FakeTransport())
        self.assertEqual(caught.exception.code, "JEV-NO-QUESTIONS")


class NewKinds(unittest.TestCase):
    def test_decide_only_never_lets_jev_loosen_a_gate(self):
        clauses = ["Rastreabilidade", "Fail-closed"]
        passing = jev.decide("constitution-check", {}, clauses, FakeTransport(pick={}, confidence=0.99))
        self.assertEqual(passing["decided"], {})  # PASS is never decided by Jev
        self.assertIsNone(passing["result"])
        violation = jev.decide("constitution-check", {}, clauses,
                               FakeTransport(pick={"clause_fail_closed": "VIOLATION"}, confidence=0.99))
        self.assertEqual(violation["result"], {"violations": ["Fail-closed"], "verdict": "NO-GO"})
        author = jev.decide("human-or-author", {}, ["d1", "d2"],
                            FakeTransport(pick={"decision_d1": "author", "decision_d2": "human"}, confidence=0.99))
        self.assertEqual(author["decided"], {"decision_d2": "human"})
        self.assertEqual(author["result"], {"to_human": ["d2"]})
        hygiene = jev.decide("diff-hygiene", {}, ["a.py", "b.py"],
                             FakeTransport(noul=lambda k: 0.99 if k == "file_a_py" else 0.01))
        self.assertEqual(hygiene["result"], {"flagged": ["a.py"]})
        self.assertEqual(hygiene["pending"], ["file_b_py"])

    def test_finding_severity_only_confirms_or_raises(self):
        state = {"context": {"findings": {"F1": {"text": "x", "proposed": "high"},
                                          "F2": {"text": "y", "proposed": "low"}}}}
        decision = jev.decide("finding-severity", state, ["F1", "F2"],
                              FakeTransport(pick={"finding_f1": "medium", "finding_f2": "critical"}))
        self.assertEqual(decision["decided"], {"finding_f2": "critical"})
        self.assertEqual(decision["pending"], ["finding_f1"])
        self.assertEqual(decision["result"], {"severities": {"F2": "critical"}})

    def test_delivery_classification_cross_checks_the_agent(self):
        agree = {"context": {"proposed": {"development_type": "backend", "module_kind": "domain"}}}
        same = jev.decide("delivery-classification", agree, [],
                          FakeTransport(pick={"development_type": "backend", "module_kind": "domain"}))
        self.assertEqual(same["result"], {"verdict": "CONFIRMED"})
        other = jev.decide("delivery-classification", agree, [],
                           FakeTransport(pick={"development_type": "frontend", "module_kind": "domain"}))
        self.assertEqual(other["result"], {"verdict": "ASK-HUMAN", "disagree": ["development_type"]})

    def test_round_record_learning_route_and_bug_type(self):
        record = jev.decide("round-record", {}, [], FakeTransport(
            noul=lambda k: 0.99 if k in {"progress", "artifact_context_md"} else 0.01,
            pick={"transition": "resolved", "scope_delta": "none"}))
        self.assertEqual(record["result"], {"transition": "resolved", "scope_delta": "none", "progress": True,
                                            "repeat": False, "adr_needed": False, "artifacts": ["CONTEXT.md"]})
        route = jev.decide("learning-route", {}, [], FakeTransport(pick={"destination": "adr-docs"}, noul=0.02))
        self.assertEqual(route["result"], {"destination": "adr-docs", "duplicate": False})
        bug = jev.decide("bug-type", {}, [], FakeTransport(pick={"bug_type": "untested-flow"}))
        self.assertEqual(bug["result"], {"bug_type": "untested-flow"})

    def test_many_kinds_share_one_request_with_session_and_trace(self):
        transport = FakeTransport(pick={"route": "bugfix", "severity": "high", "bug_type": "spec-gap"})
        decisions = jev.decide_many(["triage", "bug-type"], {"files": {}}, {}, transport, session_id="feature-x-1")
        self.assertEqual(len(transport.bodies), 1)
        body = transport.bodies[0]
        self.assertEqual(body["session_id"], "feature-x-1")
        self.assertEqual(body["trace"], {"trace_name": "gwd-decide", "span_name": "triage,bug-type"})
        self.assertEqual(set(body["questions"]), {"triage__route", "triage__severity", "bug_type__bug_type"})
        self.assertEqual(decisions["triage"]["result"], {"route": "bugfix", "severity": "high"})
        self.assertEqual(decisions["bug-type"]["result"], {"bug_type": "spec-gap"})

    def test_per_type_threshold_overrides_the_kind_threshold(self):
        spec = {"threshold": 0.9, "thresholds": {"noul": 0.7}}
        questions = {"a": {"type": "noul", "instructions": "x"}, "b": {"type": "choice", "instructions": "y",
                                                                       "criteria": {"p": "", "q": ""}}}
        response = {"answers": {"a": {"type": "noul", "noul": 0.8},
                                "b": {"type": "choice", "choice": "p", "confidence": 0.8}}}
        decision = jev.interpret("fixture", questions, response, spec, [])
        self.assertEqual(decision["decided"], {"a": True})
        self.assertEqual(decision["pending"], ["b"])

    def test_clauses_and_requirements_become_named_state(self):
        text = "# C\n## Core\n### Rule A\nbody a\n### Rule B\nbody b\n"
        self.assertEqual(jev.clauses(text), {"Core": "", "Rule A": "body a", "Rule B": "body b"})
        self.assertEqual(jev.requirements("- **FR-001**: must x\n"), {"FR-001": "- **FR-001**: must x"})


def git_repo(raw: str) -> Path:
    root = Path(raw)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


class CliContract(unittest.TestCase):
    def run_cli(self, *args: str, env: dict) -> tuple[int, dict]:
        process = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                 env=env, check=False)
        return process.returncode, json.loads(process.stdout)

    def test_init_and_preflight_refuse_without_key(self):
        env = {k: v for k, v in os.environ.items() if k != jev.KEY_ENV}
        env["GRILL_SKIP_DEPENDENCIES"] = "1"
        with tempfile.TemporaryDirectory() as raw:
            root = git_repo(raw)
            code, payload = self.run_cli("init", str(root), "--type", "feature", "--slug", "x",
                                         "--runtime", "claude", "--skip-backlog", env=env)
            self.assertEqual((code, payload["code"]), (2, "OPENROUTER-KEY-REQUIRED"))
            self.assertEqual(payload["verdict"], "BLOCKED")
            code, payload = self.run_cli("preflight", str(root), "--runtime", "claude", "--skip-backlog", env=env)
            self.assertEqual((code, payload["code"]), (2, "OPENROUTER-KEY-REQUIRED"))

    def test_decide_step_assessment_apply_writes_a_valid_fresh_assessment(self):
        workspace = load("grill_workspace_jev", SCRIPT)
        module = workspace.grill_core_module("jev")
        with tempfile.TemporaryDirectory() as raw, \
                mock.patch.object(module.Transport, "post",
                                  lambda self, url, body: answer_all(body["questions"], noul=0.02)), \
                mock.patch.dict(os.environ, {jev.KEY_ENV: KEY}):
            root = git_repo(raw)
            (root / "spec.md").write_text("**FR-001** thing\n", encoding="utf-8")
            work_id = "feature-x-1"
            (root / ".grill/work-items" / work_id).mkdir(parents=True)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = workspace.main(["decide", str(root), "--kind", "step-assessment", "--work-id", work_id,
                                       "--step", "specify", "--file", "spec.md", "--apply"])
            payload = json.loads(out.getvalue())
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["decided_by"], "jev")
            self.assertEqual(payload["result"], {"new_how": False, "risks": []})
            self.assertNotIn(KEY, out.getvalue())
            written = root / payload["written"]
            self.assertNotIn(KEY, written.read_text(encoding="utf-8"))
            policy = json.loads(workspace._policy_path(root, work_id).read_bytes())
            assessment = workspace._step_assessment(root, work_id, "specify", policy)
            self.assertIn("decided_by=jev", assessment["justification"])


class CliLog(unittest.TestCase):
    def test_multi_kind_decide_logs_and_label_appends_without_the_key(self):
        workspace = load("grill_workspace_jev_log", SCRIPT)
        module = workspace.grill_core_module("jev")
        with tempfile.TemporaryDirectory() as raw, \
                mock.patch.object(module.Transport, "post",
                                  lambda self, url, body: answer_all(body["questions"])), \
                mock.patch.dict(os.environ, {jev.KEY_ENV: KEY}):
            root = git_repo(raw)
            (root / "report.md").write_text("# Relatório de debug\n", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = workspace.main(["decide", str(root), "--kind", "triage,bug-type", "--file", "report.md",
                                       "--work-id", "fix-x-1"])
            payload = json.loads(out.getvalue())
            self.assertEqual(code, 0, payload)
            self.assertEqual(set(payload["decisions"]), {"triage", "bug-type"})
            with contextlib.redirect_stdout(io.StringIO()):
                code = workspace.main(["decide-label", str(root), "--work-id", "fix-x-1", "--kind", "triage",
                                       "--answers", '{"route": "bugfix"}'])
            self.assertEqual(code, 0)
            log = root / ".git/grill-telemetry/jev-decisions.jsonl"
            lines = [json.loads(l) for l in log.read_text().splitlines()]
            self.assertFalse((root / ".grill/jev").exists())  # never an untracked file in the worktree
            self.assertEqual([l["event"] for l in lines], ["decision", "label"])
            self.assertEqual(lines[1]["answers"], {"route": "bugfix"})
            self.assertIn("triage", lines[0]["decisions"])
            self.assertNotIn(KEY, log.read_text() + out.getvalue())


if __name__ == "__main__":
    unittest.main()
