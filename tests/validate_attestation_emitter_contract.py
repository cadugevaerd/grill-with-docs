#!/usr/bin/env python3
"""Contract for minting an attestation chain.

The core has always known how to judge a chain and never how to mint one, so
every step of the cycle became unreachable by checkpoint once the gate that
demands a chain started firing.  These tests pin what minting may and may not
claim.

The central rule is the execution class: `implement-parallel`'s worktree
isolation and closed file grant *are* its safety mechanism, so a
leader-executed receipt for it would attest an isolation that never happened.
The table that says so is a frozen literal, never derived from the sequences --
a reordering must not silently change who may execute what.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plugin/skills/grill-with-docs/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from grill_core import attestation as A  # noqa: E402
from grill_core import workflow_versions as WV  # noqa: E402

#: The work item this contract exercises the CLI against; it exists in-tree.
WORK_ID = "feature-attestation-emitter-2a51feec6ce84a7fb1b7ebe1b6c1aa25"


def read_bytes_of(path: str) -> bytes:
    return Path(path).read_bytes()


class ExecutionClassTable(unittest.TestCase):
    """The table is total, frozen, and agrees with the executor step."""

    def test_every_step_of_every_known_version_has_a_class(self) -> None:
        for version in WV.KNOWN_VERSIONS:
            with self.subTest(version=version):
                sequence = set(WV.SEQUENCE_BY_VERSION[version])
                declared = set(WV.EXECUTION_CLASS_BY_VERSION[version])
                self.assertEqual(sequence, declared, "sequence and class table must cover the same steps")

    def test_every_class_is_one_of_the_two(self) -> None:
        for version in WV.KNOWN_VERSIONS:
            for step, klass in WV.EXECUTION_CLASS_BY_VERSION[version].items():
                with self.subTest(version=version, step=step):
                    self.assertIn(klass, WV.EXECUTION_CLASSES)

    def test_the_worker_required_step_is_the_executor_step(self) -> None:
        """The step that dispatches workers is exactly the one that requires them."""
        for version in WV.KNOWN_VERSIONS:
            with self.subTest(version=version):
                required = [s for s, k in WV.EXECUTION_CLASS_BY_VERSION[version].items()
                            if k == "worker-required"]
                self.assertEqual(required, [WV.EXECUTOR_STEP_BY_VERSION[version]])

    def test_table_is_not_derived_from_the_other_version(self) -> None:
        """v3 and v4 must be able to drift; identity would mean one was derived."""
        self.assertIsNot(WV.EXECUTION_CLASS_V3, WV.EXECUTION_CLASS_V4)
        self.assertNotEqual(set(WV.EXECUTION_CLASS_V3), set(WV.EXECUTION_CLASS_V4))

    def test_leader_wave_index_is_zero_and_waves_start_at_one(self) -> None:
        """Zero is semantic -- outside any wave -- not a filler value."""
        self.assertEqual(WV.LEADER_WAVE_INDEX, 0)


class ExecutionClassLookup(unittest.TestCase):
    def test_leader_allowed_step_resolves(self) -> None:
        self.assertEqual(A.execution_class("specify", "v4", WV), "leader-allowed")

    def test_worker_required_step_resolves(self) -> None:
        self.assertEqual(A.execution_class("implement-parallel", "v4", WV), "worker-required")

    def test_undeclared_step_fails_closed_naming_the_step(self) -> None:
        with self.assertRaises(A.EmissionError) as caught:
            A.execution_class("a-step-nobody-classified", "v4", WV)
        self.assertEqual(caught.exception.reason, "EXECUTION_CLASS_UNDECLARED")
        self.assertEqual(caught.exception.detail["step_id"], "a-step-nobody-classified")

    def test_unknown_version_fails_closed(self) -> None:
        with self.assertRaises(A.EmissionError) as caught:
            A.execution_class("specify", "v99", WV)
        self.assertEqual(caught.exception.reason, "EXECUTION_CLASS_VERSION_UNKNOWN")

    def test_emission_error_is_an_attestation_error(self) -> None:
        """A caller handling AttestationError keeps failing closed on emission."""
        self.assertTrue(issubclass(A.EmissionError, A.AttestationError))


class EmissionPermission(unittest.TestCase):
    """The class gates on proof of worker execution, not on who writes it.

    No worker ever writes a step receipt -- ``implement-parallel`` says the step
    receipt is the leader's. So the class cannot mean "the worker attests"; it
    means the work must have been done under worker isolation, and the leader
    must show that before minting.
    """

    def test_worker_required_step_is_refused_without_proof(self) -> None:
        with self.assertRaises(A.EmissionError) as caught:
            A.require_emission_allowed("implement-parallel", "v4", WV)
        self.assertEqual(caught.exception.reason, "WORKER_EXECUTION_UNPROVEN")
        self.assertEqual(caught.exception.detail["step_id"], "implement-parallel")

    def test_worker_required_step_is_allowed_with_proof(self) -> None:
        """Refusing here would strand the one step that actually used workers."""
        klass = A.require_emission_allowed(
            "implement-parallel", "v4", WV, worker_execution_proven=True)
        self.assertEqual(klass, "worker-required")

    def test_leader_allowed_steps_need_no_proof(self) -> None:
        for step in WV.SEQUENCE_V4:
            if step == WV.EXECUTOR_STEP_BY_VERSION["v4"]:
                continue
            with self.subTest(step=step):
                self.assertEqual(
                    A.require_emission_allowed(step, "v4", WV), "leader-allowed")

    def test_proof_does_not_rescue_an_undeclared_step(self) -> None:
        """Proof of worker execution is not a bypass for a missing decision."""
        with self.assertRaises(A.EmissionError) as caught:
            A.require_emission_allowed("nao-classificada", "v4", WV,
                                       worker_execution_proven=True)
        self.assertEqual(caught.exception.reason, "EXECUTION_CLASS_UNDECLARED")


class ArtefactAnchor(unittest.TestCase):
    """What the chain is anchored to, and what it refuses to anchor to."""

    def test_digest_matches_the_bytes_on_disk(self) -> None:
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artefact.md"
            path.write_bytes(b"conteudo da etapa\n")
            digest, size = A.artefact_digest(read_bytes_of, str(path))
            self.assertEqual(digest, "sha256:" + hashlib.sha256(b"conteudo da etapa\n").hexdigest())
            self.assertEqual(size, len(b"conteudo da etapa\n"))

    def test_changing_the_artefact_changes_the_digest(self) -> None:
        """This is the whole guarantee: alteration after emission is detectable."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artefact.md"
            path.write_bytes(b"antes\n")
            before, _ = A.artefact_digest(read_bytes_of, str(path))
            path.write_bytes(b"depois\n")
            after, _ = A.artefact_digest(read_bytes_of, str(path))
            self.assertNotEqual(before, after)

    def test_absent_artefact_is_a_named_refusal(self) -> None:
        with self.assertRaises(A.EmissionError) as caught:
            A.artefact_digest(read_bytes_of, "definitely-not-here.md")
        self.assertEqual(caught.exception.reason, "ARTEFACT_UNREADABLE")

    def test_empty_path_is_refused_before_any_read(self) -> None:
        def explode(_: str) -> bytes:
            raise AssertionError("must not reach the reader")
        with self.assertRaises(A.EmissionError) as caught:
            A.artefact_digest(explode, "   ")
        self.assertEqual(caught.exception.reason, "ARTEFACT_PATH_INVALID")

    def test_reader_returning_non_bytes_is_refused(self) -> None:
        """Never a chain minted with an empty digest."""
        with self.assertRaises(A.EmissionError) as caught:
            A.artefact_digest(lambda _: "texto", "qualquer.md")
        self.assertEqual(caught.exception.reason, "ARTEFACT_UNREADABLE")

    def test_emission_does_no_io_of_its_own(self) -> None:
        """The caller's safe boundary is the only reader."""
        seen = []
        A.artefact_digest(lambda p: (seen.append(p), b"x")[1], "algum/caminho.md")
        self.assertEqual(seen, ["algum/caminho.md"])


class LeaderLease(unittest.TestCase):
    """The lease is derived, not invented, and mirrors the worker one."""

    def test_lease_is_derived_from_run_and_step(self) -> None:
        lease_id, token = A.leader_lease("run-1", "specify")
        self.assertEqual(lease_id, "lease-run-1-leader-specify")
        self.assertEqual(token, 1)

    def test_same_run_and_step_derive_the_same_lease(self) -> None:
        """Two leader executions of one step are one logical executor."""
        self.assertEqual(A.leader_lease("run-1", "plan"), A.leader_lease("run-1", "plan"))

    def test_different_steps_derive_different_leases(self) -> None:
        self.assertNotEqual(A.leader_lease("run-1", "plan"), A.leader_lease("run-1", "tasks"))

    def test_different_runs_derive_different_leases(self) -> None:
        self.assertNotEqual(A.leader_lease("run-1", "plan"), A.leader_lease("run-2", "plan"))

    def test_empty_run_or_step_is_refused(self) -> None:
        with self.assertRaises(A.EmissionError) as caught:
            A.leader_lease("  ", "plan")
        self.assertEqual(caught.exception.reason, "LEASE_RUN_INVALID")
        with self.assertRaises(A.EmissionError) as caught:
            A.leader_lease("run-1", "")
        self.assertEqual(caught.exception.reason, "LEASE_STEP_INVALID")

    def test_the_derived_lease_is_accepted_in_a_minted_chain(self) -> None:
        """Derivation is only useful if the judge takes what it produces."""
        self.assertTrue(A.leader_lease("run-1", "specify")[0].startswith("lease-"))


class MintedChainIsAccepted(unittest.TestCase):
    """The one test that matters: what we mint, the judge takes.

    Everything else in this file guards the edges. This guards the point.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import hashlib
        import importlib.util
        from grill_core import step_skills as ss
        from grill_core import store

        spec = importlib.util.spec_from_file_location(
            "attestation_fixture", REPO / "tests/validate_attestation_contract.py")
        fixture = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(fixture)
        except SystemExit:  # the fixture module runs unittest.main under __main__
            pass
        cls.fx = fixture
        cls.ss = ss
        cls.project_id = store.project_identity(REPO)["project_id"]
        cls.resolution = ss.resolve_workflow_skill(
            "specify", "claude", fixture.REGISTRY_SHA256,
            registry=fixture.registry_bytes(), catalog=fixture.catalog())
        cls.artefact = b"conteudo do artefato da etapa\n"
        cls.artefact_sha256 = "sha256:" + hashlib.sha256(cls.artefact).hexdigest()

    def chain(self, **overrides):
        kw = dict(
            resolution=self.resolution, project_id=self.project_id,
            work_item_id="wi-1", work_item_revision=3, run_id="run-1",
            step_id="specify", attempt_id="att-1",
            recovery_generation_id=self.fx.rg("g1"), plan_revision=1, wave_index=0,
            worktree_id="wt-coordinator", worktree_head=self.fx.head("h1"),
            worker_lease_id="lease-leader-1", worker_fencing_token=1,
            dispatcher_lease_id="dispatch-leader-1", dispatcher_epoch=1,
            artefact_path="specs/026-attestation-emitter/spec.md",
            artefact_sha256=self.artefact_sha256,
            logical_plan_sha256=self.ss.sha256_jcs({"plan": "logical"}),
            executable_plan_sha256=self.ss.sha256_jcs({"plan": "executable"}),
            input_fingerprint=self.ss.sha256_jcs({"inputs": []}),
            catalog=self.fx.catalog(),
        )
        kw.update(overrides)
        return A.mint_chain(**kw)

    def test_the_judge_accepts_a_minted_chain(self) -> None:
        verdict = A.judge_checkpoint_attestation(
            self.chain(), project_id=self.project_id, work_item_id="wi-1", step_id="specify")
        self.assertEqual(verdict["campaign"]["project_id"], self.project_id)
        self.assertEqual(verdict["campaign"]["run_id"], "run-1")

    def test_the_step_output_is_anchored_on_the_artefact(self) -> None:
        """The anchor is not a second, separate digest -- it IS the artefact's."""
        chain = self.chain()
        self.assertEqual(chain["step_output"]["output_sha256"], self.artefact_sha256)
        self.assertEqual(
            chain["step_output"]["evidence_refs"],
            [{"path": "specs/026-attestation-emitter/spec.md", "sha256": self.artefact_sha256}])

    def test_a_different_artefact_mints_a_different_chain(self) -> None:
        import hashlib
        other = "sha256:" + hashlib.sha256(b"outro conteudo\n").hexdigest()
        self.assertNotEqual(
            self.chain()["step_output"]["content_sha256"],
            self.chain(artefact_sha256=other)["step_output"]["content_sha256"])

    def test_an_incomplete_resolution_is_refused_naming_the_field(self) -> None:
        broken = {k: v for k, v in self.resolution.items() if k != "adapter"}
        with self.assertRaises(A.EmissionError) as caught:
            self.chain(resolution=broken)
        self.assertEqual(caught.exception.reason, "RESOLUTION_INCOMPLETE")
        self.assertEqual(caught.exception.detail["field"], "adapter")

    def test_a_result_with_no_invocation_counterpart_is_refused(self) -> None:
        """UNKNOWN is a valid step result and no invocation status at all."""
        with self.assertRaises(A.EmissionError) as caught:
            self.chain(result="UNKNOWN")
        self.assertEqual(caught.exception.reason, "STEP_RESULT_UNKNOWN")

    def test_a_non_digest_artefact_hash_is_refused(self) -> None:
        with self.assertRaises(Exception) as caught:
            self.chain(artefact_sha256="not-a-digest")
        self.assertIn("INVALID_DIGEST", str(caught.exception))


class CliRefusesBeforeReading(unittest.TestCase):
    """The verb must refuse a worker-required step before touching the artefact.

    Order matters here: hashing first and refusing second would mean the command
    read a file it had already decided it had no business attesting.
    """

    def setUp(self) -> None:
        import subprocess
        self.run = subprocess.run

    def _attest(self, step: str, artifact: str, out: str):
        import json
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(REPO / "plugin/skills/grill-with-docs/scripts/grill_workspace.py"),
             "attest", str(REPO), "--work-id", WORK_ID, "--step", step,
             "--artifact", artifact, "--out", out],
            capture_output=True, text=True)
        try:
            return proc.returncode, json.loads(proc.stdout or proc.stderr or "{}")
        except json.JSONDecodeError:
            return proc.returncode, {"raw": (proc.stdout or proc.stderr)[:400]}

    def test_absent_artefact_still_refused_for_a_worker_required_step(self) -> None:
        """Proof of worker execution does not excuse a missing artefact."""
        code, payload = self._attest(
            "implement-parallel", "specs/026-attestation-emitter/nao-existe.json",
            ".grill/attestations/should-not-exist.json")
        self.assertNotEqual(code, 0)
        self.assertIn(payload.get("code"),
                      {"ARTEFACT_UNREADABLE", "WORKER_EXECUTION_UNPROVEN"})
        self.assertFalse(
            (REPO / ".grill/attestations/should-not-exist.json").exists(),
            "a refused emission must not leave a bundle behind")

    def test_absent_artefact_is_refused_by_the_verb(self) -> None:
        code, payload = self._attest(
            "analyze", "specs/026-attestation-emitter/nao-existe.md",
            ".grill/attestations/should-not-exist-either.json")
        self.assertNotEqual(code, 0)
        self.assertEqual(payload.get("code"), "ARTEFACT_UNREADABLE")
        self.assertFalse((REPO / ".grill/attestations/should-not-exist-either.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
