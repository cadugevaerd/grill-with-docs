#!/usr/bin/env python3
"""Contract matrix for the end-to-end attestation chain (LD-005 / "peca F").

Barra: plan 4.1 (the chain skill-resolution -> dispatch-intent CANONICAL_SKILL
-> invocation STARTED -> invocation terminal -> step-output), 5.5 (dispatch-intent
/v1, the literal dispatch_key formula), 7.1.3 (step-output/v1, terminal
immutability), 22 "Workflow -> skill canonica" (the adversarial fixture, the
STATE_DIVERGENCE|STALE_OUTPUT|UNATTESTED_STEP_OUTPUT taxonomy), 23 (no
DIRECT|EMULATED|BEST_EFFORT fallback for a required step).

Stdlib only, no network, no real specify/node/backlogctl: every document in
the chain (resolution, dispatch intent, invocation envelopes, step output) is
built in-process from the same registry/catalogue fixtures peca C's own
validator uses.
"""
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plugin/skills/grill-with-docs/scripts"
STEP_SKILLS_MODULE = SCRIPTS / "grill_core/step_skills.py"
ATTESTATION_MODULE = SCRIPTS / "grill_core/attestation.py"
REGISTRY = REPO / "plugin/skills/grill-with-docs/assets/workflow-step-skills.json"
CATALOG = REPO / "tests/fixtures/workflow-step-skills/claude-catalog.json"

PROJECT_ID = "proj-demo"
WORK_ITEM_ID = "feature-x-a1b2"
RUN_ID = "run-1"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ss = _load(STEP_SKILLS_MODULE, "grill_core.step_skills")
att = _load(ATTESTATION_MODULE, "grill_core.attestation")


def catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def registry_bytes():
    return REGISTRY.read_bytes()


# Computed at runtime (never frozen): this validator must stay correct even if
# peca C's builder edits the registry asset's bytes in the same round.
REGISTRY_SHA256 = ss.registry_sha256(registry_bytes())


def h(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def rg(label: str) -> str:
    return "rg-" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def head(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:40]


def recompute_content_sha256(document: dict) -> dict:
    """Legitimate re-signing: recompute ``content_sha256`` over everything
    else. Used by attack fixtures that must isolate ONE specific semantic
    check by keeping the document container hash self-consistent -- the
    tamper under test is a field OTHER than content_sha256 itself."""
    mutated = dict(document)
    body = {k: v for k, v in mutated.items() if k != "content_sha256"}
    mutated["content_sha256"] = ss.sha256_jcs(body)
    return mutated


def build_chain(
    step_id: str = "verify",
    runtime: str = "claude",
    *,
    plan_revision: int = 4,
    wave_index: int = 2,
    generation_label: str = "gen-1",
    attempt_id: str = "attempt-001",
    result: str = "COMPLETED",
    project_id: str = PROJECT_ID,
    work_item_id: str = WORK_ITEM_ID,
    run_id: str = RUN_ID,
) -> dict:
    """A fully valid, self-consistent, end-to-end attested chain: resolution
    -> dispatch-intent -> invocation STARTED -> invocation terminal ->
    step-output. Every hash in every document is computed for real (no
    placeholders), so any single-field mutation a test applies afterwards is a
    genuine tamper, not a pre-broken fixture.
    """
    resolution = ss.resolve_workflow_skill(
        step_id, runtime, REGISTRY_SHA256, registry=registry_bytes(), catalog=catalog()
    )

    recovery_generation_id = rg(generation_label)
    worktree_id = f"wt-{work_item_id}"
    worktree_head = head(generation_label + "-head")
    executable_plan_sha256 = h("executable-plan-" + generation_label)
    dispatch_payload_sha256 = h("dispatch-payload-" + generation_label + step_id)

    dkey = att.dispatch_key(
        project_id, work_item_id, run_id, step_id, recovery_generation_id, plan_revision, wave_index,
        executable_plan_sha256, resolution["skill_resolution_sha256"], worktree_id, worktree_head,
        runtime, resolution["adapter"], dispatch_payload_sha256,
    )
    ikey = ss.skill_invocation_key(
        project_id, work_item_id, run_id, step_id, recovery_generation_id, plan_revision,
        resolution["skill_resolution_sha256"], dkey,
    )

    dispatch_body = {
        "schema": att.DISPATCH_INTENT_SCHEMA,
        "dispatch_key": dkey,
        "project_id": project_id, "work_item_id": work_item_id, "run_id": run_id,
        "attempt_id": attempt_id, "step_id": step_id,
        "execution_mode": ss.EXECUTION_MODE,
        "skill_resolution_sha256": resolution["skill_resolution_sha256"],
        "skill_invocation_key": ikey,
        "logical_plan_sha256": h("logical-plan-" + generation_label),
        "executable_plan_sha256": executable_plan_sha256,
        "recovery_generation_id": recovery_generation_id,
        "plan_revision": plan_revision, "wave_index": wave_index,
        "worktree_id": worktree_id, "worktree_head": worktree_head,
        "runtime": runtime, "adapter": resolution["adapter"],
        "dispatch_payload_sha256": dispatch_payload_sha256,
        "dispatcher_epoch": 12, "dispatcher_lease_id": "dispatch-leader-abc123",
        "work_item_revision": 17, "worker_lease_id": "lease-" + attempt_id,
        "worker_fencing_token": 9, "status": "STARTED", "runtime_handle": None,
    }
    dispatch_body["content_sha256"] = ss.sha256_jcs(dispatch_body)
    dispatch_intent = dispatch_body

    def invocation(status: str, manifest_label: str) -> dict:
        body = {
            "schema": ss.INVOCATION_SCHEMA,
            "skill_invocation_key": ikey,
            "project_id": project_id, "work_item_id": work_item_id, "run_id": run_id,
            "step_id": step_id, "skill_id": resolution["skill_id"],
            "skill_version": resolution["skill_version"],
            "skill_content_sha256": resolution["skill_content_sha256"],
            "registry_sha256": resolution["registry_sha256"],
            "skill_resolution_sha256": resolution["skill_resolution_sha256"],
            "runtime": runtime, "adapter": resolution["adapter"],
            "entrypoint": resolution["entrypoint"],
            "dispatch_key": dkey, "attempt_id": attempt_id,
            "recovery_generation_id": recovery_generation_id, "plan_revision": plan_revision,
            "input_fingerprint": h("input-fp-" + generation_label + step_id),
            "started_receipt_ref": f"receipts/skill-invocation/{step_id}-{attempt_id}.started.json",
            "status": status,
            "output_manifest_sha256": h("manifest-" + manifest_label),
        }
        body["content_sha256"] = ss.sha256_jcs(body)
        return body

    invocation_started = invocation("STARTED", "started")
    invocation_terminal = invocation(result, "terminal")

    input_fp = h("step-output-input-fp-" + generation_label + step_id)
    execution_round = 1
    exec_id = att.step_execution_id(recovery_generation_id, plan_revision, wave_index, step_id, execution_round, input_fp)
    step_output_body = {
        "schema": att.STEP_OUTPUT_SCHEMA,
        "recovery_generation_id": recovery_generation_id, "plan_revision": plan_revision,
        "wave_index": wave_index, "step_id": step_id,
        "skill_invocation_receipt_ref": f"receipts/skill-invocation/{step_id}-{attempt_id}.terminal.json",
        "skill_invocation_receipt_sha256": att.receipt_sha256(invocation_terminal),
        "execution_round": execution_round, "step_execution_id": exec_id,
        "supersedes_step_execution_id": None,
        "attempt_id": attempt_id, "supersedes_attempt_id": None,
        "worker_lease_id": "lease-" + attempt_id, "worker_fencing_token": 9,
        "input_fingerprint": input_fp,
        "dependency_outputs": [], "output_sha256": h("output-" + generation_label + step_id),
        "evidence_refs": [], "result": result,
    }
    step_output_body["content_sha256"] = ss.sha256_jcs(step_output_body)

    expected = {
        "project_id": project_id, "work_item_id": work_item_id, "run_id": run_id,
        "step_id": step_id, "runtime": runtime, "adapter": resolution["adapter"],
        "registry_sha256": REGISTRY_SHA256, "recovery_generation_id": recovery_generation_id,
        "plan_revision": plan_revision,
    }
    return {
        "resolution": resolution, "dispatch_intent": dispatch_intent,
        "invocation_started": invocation_started, "invocation_terminal": invocation_terminal,
        "step_output": step_output_body, "expected": expected,
    }


def judge(bundle: dict, **overrides) -> dict:
    kwargs = {
        "step_output": bundle["step_output"], "dispatch_intent": bundle["dispatch_intent"],
        "invocation_started": bundle["invocation_started"], "invocation_terminal": bundle["invocation_terminal"],
        "resolution": bundle["resolution"], "expected": bundle["expected"], "catalog": catalog(),
    }
    kwargs.update(overrides)
    return att.judge_step_output(**kwargs)


class Base(unittest.TestCase):
    def assertRejected(self, code, reason, bundle=None, **overrides):
        with self.assertRaises(att.AttestationError) as ctx:
            judge(bundle, **overrides)
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (code, reason))
        return ctx.exception


# --------------------------------------------------------------------------
# 4.1: the full chain, happy path
# --------------------------------------------------------------------------
class ChainHappyPath(Base):
    def test_full_chain_is_attested_for_every_registry_step(self):
        for step_id in ss.SEQUENCE:
            bundle = build_chain(step_id=step_id)
            verdict = judge(bundle)
            self.assertEqual(verdict["verdict"], "ATTESTED")
            self.assertEqual(verdict["step_id"], step_id)
            self.assertEqual(verdict["step_execution_id"], bundle["step_output"]["step_execution_id"])

    def test_ship_carries_human_authorization_required_true_in_resolution(self):
        bundle = build_chain(step_id="ship")
        self.assertTrue(bundle["resolution"]["human_authorization_required"])
        self.assertEqual(judge(bundle)["verdict"], "ATTESTED")


class CheckpointAttestationContract(Base):
    def checkpoint_bundle(self, bundle, authorization=None):
        result = {
            "schema": att.CHECKPOINT_ATTESTATION_SCHEMA,
            "resolution": bundle["resolution"],
            "dispatch_intent": bundle["dispatch_intent"],
            "invocation_started": bundle["invocation_started"],
            "invocation_terminal": bundle["invocation_terminal"],
            "step_output": bundle["step_output"],
            "catalog": catalog(),
        }
        if authorization is not None:
            result["human_authorization"] = authorization
        return result

    def test_first_checkpoint_establishes_the_campaign_and_returns_output_reference(self):
        project_id = h("project-checkpoint")
        bundle = build_chain(step_id="specify", project_id=project_id, work_item_id="work-checkpoint", run_id="run-checkpoint")
        result = att.judge_checkpoint_attestation(
            self.checkpoint_bundle(bundle), project_id=project_id, work_item_id="work-checkpoint", step_id="specify"
        )
        self.assertEqual(result["verdict"], "ATTESTED")
        self.assertEqual(result["campaign"]["run_id"], "run-checkpoint")
        self.assertEqual(result["output"]["step_id"], "specify")

    def test_ship_requires_human_authorization_and_the_recorded_predecessor(self):
        project_id = h("project-checkpoint")
        bundle = build_chain(step_id="ship", project_id=project_id, work_item_id="work-checkpoint", run_id="run-checkpoint")
        authorization = {
            "schema": "human-authorization/v1", "scope": "ship", "decision": "APPROVED",
            "authorized_by": "owner@example.invalid", "receipt_ref": "receipts/authorization/ship.json",
            "content_sha256": h("ship-authorization"),
        }
        with self.assertRaises(att.AttestationError) as ctx:
            att.judge_checkpoint_attestation(
                self.checkpoint_bundle(bundle), project_id=project_id, work_item_id="work-checkpoint", step_id="ship"
            )
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.UNATTESTED_STEP_OUTPUT, "HUMAN_AUTHORIZATION_MISSING"))
        with self.assertRaises(att.AttestationError) as ctx:
            att.judge_checkpoint_attestation(
                self.checkpoint_bundle(bundle, authorization), project_id=project_id, work_item_id="work-checkpoint", step_id="ship",
                predecessor_output={"step_id": "review", "output_sha256": h("review-output"),
                                    "receipt_ref": "receipts/review.json", "provenance": "current-generation"},
            )
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.STATE_DIVERGENCE, "PREDECESSOR_OUTPUT_MISMATCH"))


# --------------------------------------------------------------------------
# 4.1 requirement 1: every link is mandatory
# --------------------------------------------------------------------------
class ChainMissingLinks(Base):
    def test_missing_resolution_is_unattested(self):
        bundle = build_chain()
        self.assertRejected(att.UNATTESTED_STEP_OUTPUT, "RESOLUTION_MISSING", bundle, resolution=None)

    def test_missing_dispatch_intent_is_unattested(self):
        bundle = build_chain()
        self.assertRejected(att.UNATTESTED_STEP_OUTPUT, "DISPATCH_INTENT_MISSING", bundle, dispatch_intent=None)

    def test_missing_invocation_started_is_unattested(self):
        bundle = build_chain()
        self.assertRejected(att.UNATTESTED_STEP_OUTPUT, "INVOCATION_STARTED_MISSING", bundle, invocation_started=None)

    def test_missing_invocation_terminal_is_unattested(self):
        bundle = build_chain()
        self.assertRejected(att.UNATTESTED_STEP_OUTPUT, "INVOCATION_TERMINAL_MISSING", bundle, invocation_terminal=None)

    def test_missing_step_output_is_unattested(self):
        bundle = build_chain()
        self.assertRejected(att.UNATTESTED_STEP_OUTPUT, "STEP_OUTPUT_MISSING", bundle, step_output=None)

    def test_invocation_terminal_failed_never_backs_a_step_output(self):
        bundle = build_chain(result="FAILED")
        self.assertRejected(att.UNATTESTED_STEP_OUTPUT, "INVOCATION_NOT_COMPLETED", bundle)

    def test_invocation_terminal_blocked_never_backs_a_step_output(self):
        bundle = build_chain(result="BLOCKED")
        self.assertRejected(att.UNATTESTED_STEP_OUTPUT, "INVOCATION_NOT_COMPLETED", bundle)


# --------------------------------------------------------------------------
# 22, verbatim adversarial fixture: verify / review / ship, direct execution
# --------------------------------------------------------------------------
class DirectExecutionFixture(Base):
    """The agent is told 'execute verify', runs the tests directly and writes
    verify.md -- never invokes the skill. Zero receipts exist anywhere in the
    chain: resolution, dispatch-intent and both invocation envelopes are all
    absent. Repeated verbatim for review (a diff/report produced directly)
    and for ship (merge/push/release direct, even under valid human
    authorization)."""

    def _direct_execution(self, step_id: str, **judge_kwargs):
        expected = build_chain(step_id=step_id)["expected"]
        with self.assertRaises(att.AttestationError) as ctx:
            att.judge_step_output(
                step_output=None, dispatch_intent=None, invocation_started=None,
                invocation_terminal=None, resolution=None, expected=expected, catalog=catalog(), **judge_kwargs,
            )
        self.assertEqual(ctx.exception.code, att.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.event, att.EVENT_DIRECT_EXECUTION_REJECTED)
        return ctx.exception

    def test_verify_run_directly_and_verify_md_written_is_rejected(self):
        self._direct_execution("verify")

    def test_review_diff_and_report_produced_directly_is_rejected(self):
        self._direct_execution("review")

    def test_ship_merge_push_release_direct_is_rejected(self):
        self._direct_execution("ship")

    def test_ship_direct_is_rejected_even_under_valid_human_authorization(self):
        """Plan 4.1: authorization permits invoking the ``ship`` skill, but
        never substitutes for it. A fully-formed, well-shaped human
        authorization document must not change the verdict at all."""
        human_authorization = {
            "schema": "human-authorization/v1",
            "scope": "ship",
            "decision": "APPROVED",
            "authorized_by": "carlos.araujo@civilmaster.com.br",
            "receipt_ref": "receipts/human-authorization/ship-1.apply.json",
            "content_sha256": h("human-authorization-ship-1"),
        }
        rejected_without_auth = self._direct_execution("ship")
        rejected_with_auth = self._direct_execution("ship", human_authorization=human_authorization)
        self.assertEqual(
            (rejected_without_auth.code, rejected_without_auth.reason),
            (rejected_with_auth.code, rejected_with_auth.reason),
        )


# --------------------------------------------------------------------------
# 5.5: dispatch_key literal formula
# --------------------------------------------------------------------------
class DispatchKeyFormula(Base):
    def test_formula_matches_manual_jcs_sha256_over_exactly_14_fields(self):
        bundle = build_chain()
        doc = bundle["dispatch_intent"]
        manual = ss.sha256_jcs({field: doc[field] for field in att.DISPATCH_KEY_FIELDS})
        self.assertEqual(manual, doc["dispatch_key"])
        self.assertEqual(att.recompute_dispatch_key(doc), doc["dispatch_key"])

    def test_dispatch_key_excludes_attempt_epoch_lease_fields(self):
        """Real attack: mutate attempt_id, dispatcher_epoch, dispatcher_lease_id,
        worker_lease_id and worker_fencing_token on a genuine document, re-sign
        only content_sha256 (never dispatch_key), and prove the SAME
        dispatch_key still validates -- the plan's 'A chave NAO inclui
        attempt, epoch, lease nem timestamp', exercised over the real
        document->digest pipeline, not asserted by construction."""
        bundle = build_chain()
        original = bundle["dispatch_intent"]
        mutated = dict(original)
        mutated["attempt_id"] = "attempt-999"
        mutated["dispatcher_epoch"] = original["dispatcher_epoch"] + 500
        mutated["dispatcher_lease_id"] = "dispatch-leader-zzz999"
        mutated["worker_lease_id"] = "lease-attempt-999"
        mutated["worker_fencing_token"] = original["worker_fencing_token"] + 500
        mutated["work_item_revision"] = original["work_item_revision"] + 500
        mutated = recompute_content_sha256(mutated)
        self.assertEqual(mutated["dispatch_key"], original["dispatch_key"])
        validated = att.validate_dispatch_intent(mutated)
        self.assertEqual(validated["dispatch_key"], original["dispatch_key"])

    def test_stale_dispatch_key_after_a_covered_field_changes_is_rejected(self):
        """The mirror attack: change a field the formula DOES cover
        (wave_index), re-sign content_sha256 so the container is
        self-consistent, but leave dispatch_key at its old value. This must
        be caught by recomputation, not by the (now-passing) content check."""
        bundle = build_chain()
        mutated = dict(bundle["dispatch_intent"])
        mutated["wave_index"] = mutated["wave_index"] + 1
        mutated = recompute_content_sha256(mutated)
        with self.assertRaises(att.AttestationError) as ctx:
            att.validate_dispatch_intent(mutated)
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.STATE_DIVERGENCE, "DISPATCH_KEY_MISMATCH"))


# --------------------------------------------------------------------------
# 5.5 / 4.1: execution_mode obrigatorio == CANONICAL_SKILL
# --------------------------------------------------------------------------
class ExecutionModeEnforced(Base):
    def test_dispatch_intent_execution_mode_is_canonical_skill(self):
        bundle = build_chain()
        self.assertEqual(bundle["dispatch_intent"]["execution_mode"], "CANONICAL_SKILL")

    def test_forbidden_execution_modes_are_policy_violations_on_dispatch_intent(self):
        for mode in ("DIRECT", "EMULATED", "BEST_EFFORT"):
            with self.subTest(mode=mode):
                bundle = build_chain()
                mutated = dict(bundle["dispatch_intent"])
                mutated["execution_mode"] = mode
                mutated = recompute_content_sha256(mutated)  # isolates the mode check: dispatch_key untouched, still valid
                with self.assertRaises(att.AttestationError) as ctx:
                    att.validate_dispatch_intent(mutated)
                self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.POLICY_VIOLATION, att.DIRECT_STEP_EXECUTION))
                self.assertEqual(ctx.exception.event, att.EVENT_DIRECT_EXECUTION_REJECTED)


# --------------------------------------------------------------------------
# 22, bullet 7: STATE_DIVERGENCE|STALE_OUTPUT|UNATTESTED_STEP_OUTPUT taxonomy
# --------------------------------------------------------------------------
class NoCorrelatedReceipt(Base):
    def test_step_output_with_uncorrelated_receipt_hash_is_unattested(self):
        """'sem receipt assinado/correlacionado': the step-output claims a
        receipt hash that matches nothing real -- an attacker who fabricates
        the output document wholesale."""
        bundle = build_chain()
        mutated = dict(bundle["step_output"])
        mutated["skill_invocation_receipt_sha256"] = h("a-receipt-that-was-never-issued")
        mutated = recompute_content_sha256(mutated)
        self.assertRejected(
            att.UNATTESTED_STEP_OUTPUT, "RECEIPT_NOT_CORRELATED", bundle, step_output=mutated
        )


class ReceiptOfAnotherIdentity(Base):
    def test_receipt_of_another_step_is_state_divergence(self):
        """'receipt de outro step/skill/... falha': a fully valid, internally
        self-consistent 'review' chain presented as evidence for 'verify'."""
        review_bundle = build_chain(step_id="review")
        verify_expected = build_chain(step_id="verify")["expected"]
        self.assertRejected(
            att.STATE_DIVERGENCE, "RESOLUTION_IDENTITY_MISMATCH", review_bundle, expected=verify_expected
        )

    def test_receipt_of_another_work_item_is_state_divergence(self):
        bundle = build_chain()
        forged_expected = dict(bundle["expected"])
        forged_expected["work_item_id"] = "some-other-work-item-zz99"
        self.assertRejected(
            att.STATE_DIVERGENCE, "DISPATCH_IDENTITY_MISMATCH", bundle, expected=forged_expected
        )

    def test_receipt_of_another_run_is_state_divergence(self):
        bundle = build_chain()
        forged_expected = dict(bundle["expected"])
        forged_expected["run_id"] = "run-completely-different"
        self.assertRejected(
            att.STATE_DIVERGENCE, "DISPATCH_IDENTITY_MISMATCH", bundle, expected=forged_expected
        )


class ReplayOfEarlierGeneration(Base):
    def test_step_output_from_older_generation_presented_as_current_is_stale(self):
        """'replay de geracao/revisao anterior falha STALE_OUTPUT': attacker
        takes a real, self-consistent, older-generation step_output and
        re-binds only its receipt correlation to the CURRENT invocation
        terminal (re-signing content_sha256 honestly) -- everything about it
        is individually well-formed; only its generation is stale."""
        current = build_chain(generation_label="gen-current")
        older = build_chain(generation_label="gen-older")
        forged = dict(older["step_output"])
        forged["skill_invocation_receipt_sha256"] = att.receipt_sha256(current["invocation_terminal"])
        forged = recompute_content_sha256(forged)

        self.assertRejected(
            att.STALE_OUTPUT, "STEP_OUTPUT_GENERATION_STALE", current, step_output=forged
        )

    def test_dispatch_intent_from_older_generation_presented_as_current_is_stale(self):
        current_expected = build_chain(generation_label="gen-current-2")["expected"]
        older = build_chain(generation_label="gen-older-2")
        self.assertRejected(
            att.STALE_OUTPUT, "DISPATCH_GENERATION_STALE", older, expected=current_expected
        )


class BytesDivergentUnderSameHash(Base):
    """'bytes divergentes sob o mesmo hash falha STATE_DIVERGENCE': a raw
    tamper test -- mutate a field and do NOT re-sign content_sha256. This is
    the one place a re-sign must be absent, since the whole point is proving
    the content-hash recheck itself catches the tamper."""

    def test_step_output_result_flipped_without_resigning_is_rejected(self):
        bundle = build_chain()
        tampered = dict(bundle["step_output"])
        tampered["result"] = "FAILED"  # content_sha256 left at the COMPLETED value on purpose
        self.assertRejected(
            att.STATE_DIVERGENCE, "STEP_OUTPUT_CONTENT_MISMATCH", bundle, step_output=tampered
        )

    def test_dispatch_intent_runtime_flipped_without_resigning_is_rejected(self):
        bundle = build_chain()
        tampered = dict(bundle["dispatch_intent"])
        tampered["adapter"] = "some-other-adapter/v9"  # content_sha256 left stale on purpose
        self.assertRejected(
            att.STATE_DIVERGENCE, "DISPATCH_INTENT_CONTENT_MISMATCH", bundle, dispatch_intent=tampered
        )

    def test_step_execution_id_forged_to_an_unrelated_value_is_rejected(self):
        bundle = build_chain()
        forged = dict(bundle["step_output"])
        forged["step_execution_id"] = "se-" + hashlib.sha256(b"unrelated").hexdigest()
        forged = recompute_content_sha256(forged)
        with self.assertRaises(att.AttestationError) as ctx:
            att.validate_step_output(forged)
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.STATE_DIVERGENCE, "STEP_EXECUTION_ID_MISMATCH"))


# --------------------------------------------------------------------------
# 23: no DIRECT|EMULATED|BEST_EFFORT fallback for a required=true step
# --------------------------------------------------------------------------
class NoForbiddenFallbackStrings(Base):
    def test_valid_chain_documents_never_contain_forbidden_fallback_words(self):
        for step_id in ss.SEQUENCE:
            bundle = build_chain(step_id=step_id)
            for doc in (
                bundle["dispatch_intent"], bundle["invocation_started"],
                bundle["invocation_terminal"], bundle["step_output"],
            ):
                serialized = json.dumps(doc)
                for word in ("DIRECT", "EMULATED", "BEST_EFFORT"):
                    self.assertNotIn(word, serialized)

    def test_every_registry_step_is_required_true_and_rejects_emulated_dispatch(self):
        for step_id in ss.SEQUENCE:
            with self.subTest(step_id=step_id):
                bundle = build_chain(step_id=step_id)
                self.assertIs(bundle["resolution"]["required"], True)
                mutated = dict(bundle["dispatch_intent"])
                mutated["execution_mode"] = "EMULATED"
                mutated = recompute_content_sha256(mutated)
                with self.assertRaises(att.AttestationError) as ctx:
                    att.validate_dispatch_intent(mutated)
                self.assertEqual(ctx.exception.code, att.POLICY_VIOLATION)


# --------------------------------------------------------------------------
# 4.1 / bullet 5: POLICY_VIOLATION/DIRECT_STEP_EXECUTION capability guard
# --------------------------------------------------------------------------
class CapabilityGuard(Base):
    def test_capability_blocked_without_a_started_receipt(self):
        with self.assertRaises(att.AttestationError) as ctx:
            att.guard_capability_access(None, capability="git.push", step_id="ship")
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.POLICY_VIOLATION, att.DIRECT_STEP_EXECUTION))
        self.assertEqual(ctx.exception.event, att.EVENT_DIRECT_EXECUTION_REJECTED)

    def test_capability_blocked_with_a_non_started_invocation(self):
        bundle = build_chain()
        with self.assertRaises(att.AttestationError) as ctx:
            att.guard_capability_access(bundle["invocation_terminal"], capability="git.push", step_id="verify")
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.POLICY_VIOLATION, att.DIRECT_STEP_EXECUTION))

    def test_capability_allowed_once_started_receipt_exists(self):
        bundle = build_chain()
        att.guard_capability_access(bundle["invocation_started"], capability="fs.write", step_id="verify")


# --------------------------------------------------------------------------
# 7.1.3: terminal receipt immutability + authorized retry
# --------------------------------------------------------------------------
class TerminalReceiptStore(Base):
    def test_record_is_idempotent_on_identical_replay(self):
        bundle = build_chain()
        store: dict = {}
        self.assertEqual(att.record_step_execution(store, bundle["step_output"]), "RECORDED")
        self.assertEqual(att.record_step_execution(store, bundle["step_output"]), "REUSED")
        self.assertEqual(len(store), 1)

    def test_failed_terminal_is_never_overwritten_by_completed_attack(self):
        """Real attack: after a FAILED terminal is recorded, resubmit the
        SAME step_execution_id with result flipped to COMPLETED, re-signing
        content_sha256 honestly (the forged document is internally
        self-consistent -- only the outcome differs). Must be rejected, and
        the store must show the original FAILED terminal untouched
        afterwards -- not just that an exception was raised."""
        failed_bundle = build_chain(result="FAILED")
        store: dict = {}
        att.record_step_execution(store, failed_bundle["step_output"])

        forged = dict(failed_bundle["step_output"])
        forged["result"] = "COMPLETED"
        forged = recompute_content_sha256(forged)

        with self.assertRaises(att.AttestationError) as ctx:
            att.record_step_execution(store, forged)
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.STATE_DIVERGENCE, "TERMINAL_OVERWRITE_REJECTED"))

        exec_id = failed_bundle["step_output"]["step_execution_id"]
        self.assertEqual(store[exec_id]["result"], "FAILED")
        self.assertEqual(store[exec_id]["content_sha256"], failed_bundle["step_output"]["content_sha256"])

    def test_authorized_retry_creates_a_new_linked_execution_id(self):
        failed_bundle = build_chain(result="FAILED", generation_label="gen-retry")
        store: dict = {}
        att.record_step_execution(store, failed_bundle["step_output"])
        failed_output = failed_bundle["step_output"]

        retry_output = dict(failed_output)
        retry_output["execution_round"] = failed_output["execution_round"] + 1
        retry_output["supersedes_step_execution_id"] = failed_output["step_execution_id"]
        retry_output["step_execution_id"] = att.step_execution_id(
            retry_output["recovery_generation_id"], retry_output["plan_revision"], retry_output["wave_index"],
            retry_output["step_id"], retry_output["execution_round"], retry_output["input_fingerprint"],
        )
        retry_output["result"] = "COMPLETED"
        retry_output = recompute_content_sha256(retry_output)

        self.assertEqual(att.retry_step_execution(store, failed_output, retry_output), "RECORDED")
        self.assertEqual(store[failed_output["step_execution_id"]]["result"], "FAILED")
        self.assertEqual(store[retry_output["step_execution_id"]]["result"], "COMPLETED")
        self.assertEqual(len(store), 2)

    def test_retry_cannot_reuse_the_failed_execution_id_attack(self):
        failed_bundle = build_chain(result="FAILED")
        store: dict = {}
        att.record_step_execution(store, failed_bundle["step_output"])
        failed_output = failed_bundle["step_output"]

        sneaky_retry = dict(failed_output)  # same step_execution_id, just flips the result
        sneaky_retry["result"] = "COMPLETED"
        sneaky_retry = recompute_content_sha256(sneaky_retry)

        with self.assertRaises(att.AttestationError) as ctx:
            att.retry_step_execution(store, failed_output, sneaky_retry)
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.STATE_DIVERGENCE, "RETRY_REUSES_FAILED_EXECUTION_ID"))
        self.assertEqual(store[failed_output["step_execution_id"]]["result"], "FAILED")

    def test_retry_must_declare_supersedes_link_to_the_failed_id(self):
        failed_bundle = build_chain(result="FAILED", generation_label="gen-retry-2")
        store: dict = {}
        att.record_step_execution(store, failed_bundle["step_output"])
        failed_output = failed_bundle["step_output"]

        retry_output = dict(failed_output)
        retry_output["execution_round"] = failed_output["execution_round"] + 1
        retry_output["step_execution_id"] = att.step_execution_id(
            retry_output["recovery_generation_id"], retry_output["plan_revision"], retry_output["wave_index"],
            retry_output["step_id"], retry_output["execution_round"], retry_output["input_fingerprint"],
        )
        retry_output["result"] = "COMPLETED"
        # supersedes_step_execution_id left at None: the retry never declares its lineage.
        retry_output = recompute_content_sha256(retry_output)

        with self.assertRaises(att.AttestationError) as ctx:
            att.retry_step_execution(store, failed_output, retry_output)
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (att.UNATTESTED_STEP_OUTPUT, "RETRY_NOT_LINKED_TO_FAILED"))


# --------------------------------------------------------------------------
# cross-module vocabulary drift guard (LD-001-style discipline)
# --------------------------------------------------------------------------
class SharedVocabulary(Base):
    def test_v3_codes_shared_with_step_skills_are_byte_identical(self):
        self.assertEqual(att.BLOCKED_CAPABILITY, ss.BLOCKED_CAPABILITY)
        self.assertEqual(att.STALE_SKILL_RESOLUTION, ss.STALE_SKILL_RESOLUTION)
        self.assertEqual(att.UNATTESTED_STEP_OUTPUT, ss.UNATTESTED_STEP_OUTPUT)

    def test_forbidden_execution_modes_shared_with_step_skills(self):
        self.assertEqual(tuple(ss.FORBIDDEN_EXECUTION_MODES), ("DIRECT", "EMULATED", "BEST_EFFORT"))


# --------------------------------------------------------------------------
# hygiene
# --------------------------------------------------------------------------
class Hygiene(Base):
    def test_module_is_stdlib_only_and_offline(self):
        text = ATTESTATION_MODULE.read_text(encoding="utf-8")
        for forbidden in ("import requests", "urllib", "http.client", "socket", "subprocess", "os.system"):
            self.assertNotIn(forbidden, text, forbidden)

    def test_public_cli_wires_only_the_checkpoint_attestation_boundary(self):
        text = (SCRIPTS / "grill_workspace.py").read_text(encoding="utf-8")
        self.assertIn("verify_checkpoint_attestation", text)
        self.assertNotIn("resolve_workflow_skill(", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
