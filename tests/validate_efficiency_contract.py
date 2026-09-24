#!/usr/bin/env python3
"""Offline v5 compatibility, risk binding and batching checks."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugin/skills/grill-with-docs/scripts'
sys.path.insert(0, str(SCRIPTS))
import audit_decisions
import ensure_workflow
import grill_workspace as cli
from grill_core import agent_orchestration as core, agent_runtime, gauntlet, partition, step_skills, workflow_v4, workflow_v5
import validate_agent_orchestration_contract as historical

ASSETS = SCRIPTS.parent / 'assets'
POLICY = json.loads((ASSETS / 'agent-orchestration.v2.json').read_bytes())


def assessment(step='tasks', **updates):
    return {'schema': 'grill-step-assessment/v1', 'step': step, 'new_how': False,
            'risks': [], 'justification': 'Mechanically follows the approved plan.',
            'files': [{'path': 'plan.md', 'sha256': 'a' * 64}], **updates}


class Efficiency(unittest.TestCase):
    def test_fresh_bootstrap_and_both_catalogs(self):
        raw, text = ensure_workflow.bootstrap_document()
        self.assertIn('grill-with-docs-workflow:v5', text)
        self.assertEqual(workflow_v5.execution_gate(text).status, 'OK')
        self.assertEqual(gauntlet._document_version(text), 'v5')
        for runtime, filename in [('codex', 'codex-v5-local-skills.catalog.json'), ('claude', 'grill-v5-local-skills.catalog.json')]:
            registry = (ASSETS / 'workflow-step-skills.v5.json').read_bytes()
            catalog = step_skills.parse_strict((ASSETS / filename).read_bytes())
            resolved, _ = step_skills.resolve_shipped_workflow_skills(
                tuple(POLICY['activity_matrix']), runtime, step_skills.registry_sha256(registry),
                registry=registry, catalog=catalog, trusted_catalogs_path=ASSETS/'workflow-trusted-catalogs.v5.json')
            self.assertEqual(len(resolved), 11)

    def test_public_v5_entry_and_checkpoint_enforce_assessment(self):
        fixture = historical.AgentOrchestrationContract()
        temp, root = fixture.fixture()
        (root/'WORKFLOW.md').write_bytes(workflow_v5.render_v5())
        with temp, historical.orchestration_fixture.offline_leader(cli), mock.patch.dict('os.environ', {'GRILL_SKIP_DEPENDENCIES': '1'}):
            code, result = fixture.run_cli('init', str(root), '--type', 'feature', '--slug', 'new',
                '--work-id', 'work-x', '--runtime', 'codex', '--session-ref', historical.orchestration_fixture.SESSION, '--skip-backlog')
            self.assertEqual(code, 0, result)
            state = json.loads((root/'.grill/work-items/work-x/state.json').read_bytes())
            self.assertEqual(state['development']['workflow_version'], 'v5')
            item = cli.grill_core_module('store').read_snapshot(root).document['agent_orchestration']['work_items']['work-x']
            self.assertEqual(item['policy_ref'], 'assets/agent-orchestration.v2.json')
            args = ('gauntlet-step-enter', str(root), '--work-id', 'work-x', '--context-id', item['current_context_id'],
                '--epoch', '1', '--session-ref', historical.orchestration_fixture.SESSION, '--step', 'specify')
            self.assertEqual(fixture.run_cli(*args)[0], 2)
            inputs = root/'.grill/work-items/work-x/step-inputs'; inputs.mkdir()
            doc = assessment('specify', files=[{'path':'README.md', 'sha256':hashlib.sha256((root/'README.md').read_bytes()).hexdigest()}])
            (inputs/'specify.json').write_text(json.dumps(doc))
            code, entered = fixture.run_cli(*args)
            self.assertEqual(code, 0, entered)
            self.assertEqual(entered['invocation_context']['required_activities'], [])
            self.assertIn('v2.md', entered['invocation_context']['supplement']['path'])
            cp = ('checkpoint', str(root), '--work-id', 'work-x', '--step', 'specify', '--state', 'in-progress',
                  '--session-ref', historical.orchestration_fixture.SESSION, '--operation-id', 'first')
            self.assertEqual(fixture.run_cli(*cp)[0], 0)
            doc['risks'] = ['security']; (inputs/'specify.json').write_text(json.dumps(doc))
            code, refused = fixture.run_cli(*cp)
            self.assertEqual((code, refused['code']), (2, 'ACTIVITY-REQUIRED'))

    def test_checkpoint_rejects_old_receipt_after_low_risk_inputs_change(self):
        from validate_attestation_emitter_contract import MintedChainIsAccepted
        MintedChainIsAccepted.setUpClass()
        emitter = MintedChainIsAccepted()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'plan.md').write_text('approved')
            inputs = root/'.grill/work-items/wi-1/step-inputs'; inputs.mkdir(parents=True)
            doc = assessment('specify', files=[{'path': 'plan.md', 'sha256': hashlib.sha256(b'approved').hexdigest()}])
            path = inputs/'specify.json'; path.write_text(json.dumps(doc))
            store = cli.grill_core_module('store')
            with mock.patch.object(cli, '_policy_path', return_value=ASSETS/'agent-orchestration.v2.json'), \
                 mock.patch.object(store, 'project_identity', return_value={'project_id': emitter.project_id}), \
                 mock.patch.object(store, 'read_snapshot', return_value=None):
                fingerprint = lambda: cli._v5_input_fingerprint(root, 'wi-1', 'specify', emitter.fx.head('h1'), emitter.artefact_sha256)
                receipt = root/'receipt.json'
                receipt.write_text(json.dumps(emitter.chain(input_fingerprint=fingerprint())))
                verify = lambda: cli.verify_checkpoint_attestation(root,
                    {'workflow_version': 'v5', 'sequence': list(POLICY['activity_matrix'])},
                    work_id='wi-1', step_id='specify', attestation_path='receipt.json')
                verify()
                (root/'plan.md').write_text('revised')
                doc['files'][0]['sha256'] = hashlib.sha256(b'revised').hexdigest()
                path.write_text(json.dumps(doc))
                with self.assertRaises(cli.CliFailure) as caught:
                    verify()
                self.assertEqual(caught.exception.code, 'STEP-ASSESSMENT-STALE')
                receipt.write_text(json.dumps(emitter.chain(input_fingerprint=fingerprint())))
                verify()

    def test_existing_markerless_v4_keeps_its_policy(self):
        text = workflow_v4.render_v4().decode().replace('<!-- grill-with-docs-workflow:v4 -->', '')
        self.assertEqual(workflow_v4.execution_gate(text).status, 'OK')
        self.assertEqual(gauntlet._document_version(text), 'v4')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'WORKFLOW.md').write_text(text)
            self.assertEqual(cli._policy_path(root).name, 'agent-orchestration.v1.json')
        self.assertEqual(workflow_v5.execution_gate(text).status, 'BLOCKED')

    def test_two_fixed_reviews_and_every_exception(self):
        reviewed = []
        for step in POLICY['activity_matrix']:
            roles = core.activity_requirements(POLICY, step_id=step, activity_scope='cycle', assessment=assessment(step))
            if 'reviewer' in roles: reviewed.append(step)
        self.assertEqual(reviewed, ['plan', 'review'])
        for risk in POLICY['review_risks']:
            self.assertEqual(core.activity_requirements(POLICY, step_id='tasks', activity_scope='cycle',
                assessment=assessment(risks=[risk])), ('reviewer',))
        self.assertEqual(core.activity_requirements(POLICY, step_id='tasks', activity_scope='cycle',
            assessment=assessment(new_how=True)), ('author',))
        with self.assertRaises(core.OrchestrationError):
            core.activity_requirements(POLICY, step_id='tasks', activity_scope='cycle')
        with self.assertRaises(core.OrchestrationError):
            core.activity_requirements(POLICY, step_id='tasks', activity_scope='cycle', frontend=True, assessment=assessment())

    def test_assessment_validation_and_source_changes(self):
        for updates in ({'new_how': 1}, {'risks': ['unknown']}, {'risks': ['security', 'security']},
                        {'justification': ' '}, {'files': []}, {'files': [{'path': '../escape', 'sha256': 'a'*64}]}):
            with self.assertRaises(core.OrchestrationError):
                core.validate_step_assessment(assessment(**updates), POLICY, 'tasks')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'plan.md').write_text('approved')
            doc = assessment(files=[{'path': 'plan.md', 'sha256': hashlib.sha256(b'approved').hexdigest()}])
            inputs = root/'.grill/work-items/w1/step-inputs'; inputs.mkdir(parents=True)
            (inputs/'tasks.json').write_text(json.dumps(doc))
            self.assertEqual(cli._step_assessment(root, 'w1', 'tasks', POLICY), doc)
            (root/'plan.md').write_text('changed')
            with self.assertRaises(cli.CliFailure) as caught:
                cli._step_assessment(root, 'w1', 'tasks', POLICY)
            self.assertEqual(caught.exception.code, 'STEP-ASSESSMENT-STALE')

    def test_final_review_cannot_omit_authors_or_reuse_old_assessment(self):
        fixture = historical.AgentOrchestrationContract()
        a1, *_ = fixture.accepted_specialist('a1')
        a2, *_ = fixture.accepted_specialist('a2')
        reviewer, *_ = fixture.accepted_specialist('review-final', step='review', role='reviewer', author_ids=['a1'])
        doc = assessment('review')
        digest = core.validate_step_assessment(doc, POLICY, 'review')
        reviewer['input_manifest']['assessment_sha256'] = digest
        item = {'activities': {'a1': a1, 'a2': a2, 'review-final': reviewer}}
        coverage = lambda: core.activity_coverage(item, POLICY, context_id='ctx-1', step_id='review', assessment=doc)
        self.assertEqual(coverage()['missing'], ['reviewer'])
        reviewer['author_activity_ids'].append('a2')
        self.assertEqual(coverage()['missing'], [])
        reviewer['input_manifest']['assessment_sha256'] = '0'*64
        self.assertEqual(coverage()['missing'], ['reviewer'])

    def test_partial_batches_count_presented_questions_per_session(self):
        ids = {f'DQ-{i:04}' for i in range(1, 31)}
        records = [{'batch': f'b{i}', 'question_run': 'session1', 'question_id': f'DQ-{3*i+1:04}',
                    'batch_questions': [f'DQ-{3*i+j:04}' for j in (1,2,3)]} for i in range(9)]
        self.assertEqual(audit_decisions.question_batch_findings(records[:1], ids), [])
        self.assertIn('ROUND-LOG: limite de 25 perguntas materiais excedido', audit_decisions.question_batch_findings(records, ids))
        records[-1]['question_run'] = 'session2'
        self.assertEqual(audit_decisions.question_batch_findings(records, ids), [])
        self.assertTrue(audit_decisions.question_batch_findings([records[0], records[0]], ids))
        self.assertTrue(audit_decisions.question_batch_findings([{**records[0], 'batch_questions': list(ids)[:4]}], ids))

    def test_groups_and_phases_keep_grants_and_per_task_results(self):
        text = '<!-- grill-task-files:v1 -->\n## Phase 1: Work\n'
        for i in range(1,5):
            text += f'- [ ] T{i:03} [P] Implement part {i}\n  Files: ["part{i}.py", "specs/demo/implement/T{i:03}.tasks.json"]\n  Result: "specs/demo/implement/T{i:03}.tasks.json"\n'
        dag, report = partition.partition_task_files(text, feature='demo', groups=POLICY['partition_groups'])
        self.assertEqual(len(dag['nodes']), 2)
        self.assertEqual(sum(len(n['task_ids']) for n in dag['nodes']), 4)
        self.assertFalse(set(dag['nodes'][0]['files']) & set(dag['nodes'][1]['files']))
        self.assertEqual(sum(len(n['result_files']) for n in dag['nodes']), 4)

    def test_executable_resolution_is_once_per_transcript(self):
        events = [({'name':'exec_command', 'input':{'cmd':'/bin/true'}}, str(i), '{}') for i in range(50)]
        with mock.patch.object(agent_runtime, '_tool_results', return_value=iter(events)), \
             mock.patch.object(agent_runtime, '_runtime_config_axes', return_value={}), \
             mock.patch.object(agent_runtime.shutil, 'which', return_value='/bin/codex') as which:
            agent_runtime._orca_presentation_axes({'provider':'codex'}, {})
        self.assertEqual(which.call_count, 1)


if __name__ == '__main__':
    unittest.main()
