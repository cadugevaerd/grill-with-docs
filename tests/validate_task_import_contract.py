#!/usr/bin/env python3
"""Mixed historical runs, real Git/Store receipts, offline public CLI boundary."""
import contextlib
import copy
import hashlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugin/skills/grill-with-docs/scripts'))
import grill_workspace as cli
from grill_core import partition
import validate_agent_orchestration_contract as fixtures

runs = cli.grill_core_module('gauntlet_runs')
store = runs.store
WORK = 'mixed-import'
FLOORS = dict(agent_execute_floor='medium', markdown_floor='medium')


class TaskImportContract(unittest.TestCase):
    def setUp(self):
        self.temp, self.root = fixtures.AgentOrchestrationContract().fixture()
        self.addCleanup(self.temp.cleanup)
        self.dag_ref = 'specs/demo/execution-dag.json'
        self.tasks_ref = 'specs/demo/tasks.md'
        self.result = lambda task: f'specs/demo/implement/{task}.tasks.json'
        text = '<!-- grill-task-files:v1 -->\n## Phase 3: Existing work\n'
        for task, path in [('T007', 'shared.py'), ('T008', 'shared.py'), ('T009', 'other.py')]:
            text += f'- [ ] {task} Work\n  Files: ["{path}", "{self.result(task)}"]\n  Result: "{self.result(task)}"\n'
        text += f'## Phase 4: Remaining work\n- [ ] T011 Later\n  Files: ["later.py", "{self.result("T011")}"]\n  Result: "{self.result("T011")}"\n'
        self.write(self.tasks_ref, text)
        self.dag, self.report = partition.partition_task_files(text, feature='demo', groups=2, root=self.root)
        self.write(self.dag_ref, json.dumps(self.dag))
        self.write('specs/demo/partition-report.json', json.dumps(self.report))
        self.git('add', '.')
        self.git('commit', '-qm', 'task contract')
        self.identities = []
        self.source_runs = []
        for number, node_id in enumerate(('p03-a', 'p03-b'), 1):
            identity = self.identity(str(number))
            source = runs.admit_or_reuse_run(self.root, WORK, identity)['run_id']
            self.identities.append(identity)
            self.source_runs.append(source)
            runs.declare_wave(self.root, WORK, source, self.dag_ref, [node_id], identity, activation_max_workers=2, **FLOORS)
            node = next(node for node in self.dag['nodes'] if node['id'] == node_id)
            runs.declare_worker(self.root, WORK, source, node_id, 'wave-0001', 'medium', node['files'], self.dag_ref, identity, **FLOORS)
            target = runs._workspace_identity(self.root, WORK, source, node_id, identity)[0]
            for task in node['task_ids']:
                result = dict(schema='grill-task-result/v1', work_id=WORK, scheduler_run_id=source,
                              node_id=node_id, task_id=task, attempt_id='attempt-1', status='completed', diagnostic_ref=None)
                path = target / self.result(task)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(result))
            subprocess.run(['git', '-C', str(target), 'add', '.'], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(target), 'commit', '-qm', 'results'], check=True, capture_output=True)
            runs.terminate_worker(self.root, WORK, source, node_id, 'completed', None, identity)
            runs.converge_wave(self.root, WORK, source, self.dag_ref, 'wave-0001', identity,
                              execution_branch=self.git('branch', '--show-current'), **FLOORS)
        self.admission = self.identity('3')
        self.target = runs.admit_or_reuse_run(self.root, WORK, self.admission)['run_id']
        self.sources = {'T007': self.source_runs[0], 'T008': self.source_runs[0], 'T009': self.source_runs[1]}

    def write(self, ref, text):
        path = self.root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def identity(self, char):
        return dict(activation_sha256=char * 64, work_item_sha256='a' * 64,
                    workflow_sha256='b' * 64, config_sha256=char * 64, base_commit=self.git('rev-parse', 'HEAD'))

    def command(self, *tail, sources=None, verb='gauntlet-tasks-import'):
        args = [verb, str(self.root), '--work-id', WORK, '--run-id', self.target, '--dag', self.dag_ref]
        if verb == 'gauntlet-tasks-import':
            for task, source in (self.sources if sources is None else sources).items():
                args += ['--source-task', f'{task}={source}']
        record = {'tier_policy': {'agent_execute_floor': 'medium', 'markdown_floor': 'medium'}}
        with mock.patch.object(cli, 'gauntlet_run_admission', return_value=(self.root, runs, self.admission, record)), \
             mock.patch.object(cli, '_tier_floors', return_value=('medium', 'medium')), \
             mock.patch.object(cli, 'resolve_gauntlet_subject'):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cli.main(args + list(tail))
            return code, json.loads(output.getvalue())

    def footprint(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*')
                if p.is_file() and ('.git/grill/' in str(p.relative_to(self.root)) or '.git' not in p.parts)}

    def apply(self):
        code, preview = self.command()
        self.assertEqual(code, 0, preview)
        code, result = self.command('--apply', '--expected-sha256', preview['expected_sha256'])
        self.assertEqual((code, result.get('verdict')), (0, 'APPLIED'), result)
        return preview, result

    def test_public_mixed_import_reconcile_barrier_scheduler_and_idempotence(self):
        before = self.footprint()
        code, preview = self.command()
        self.assertEqual((code, preview.get('verdict')), (0, 'PREVIEW'), preview)
        self.assertEqual(self.footprint(), before)
        historical = copy.deepcopy(runs._read_runs(self.root, WORK))
        _, applied = self.apply()
        current = runs._read_runs(self.root, WORK)
        for source in self.source_runs:
            self.assertEqual(current[source], historical[source])
        self.assertEqual(current[self.target]['workers'], {})
        self.assertTrue(runs._is_placeholder_wave(current[self.target]['waves']['wave-0001']))
        self.assertEqual(set(applied['import']['tasks']), {'T007', 'T008', 'T009'})
        accepted = applied['import']['tasks']
        barrier = runs.task_phase_barrier(self.dag, self.report, target_phase=4,
            dag_content_sha256=applied['import']['dag_sha256'], accepted_tasks=accepted)
        self.assertEqual(barrier['pending'], [])
        self.assertEqual(self.command(verb='gauntlet-tasks-reconcile')[1]['completed'], ['T007', 'T008', 'T009'])
        after = self.footprint()
        self.assertEqual(self.command('--apply', '--expected-sha256', preview['expected_sha256'])[1]['verdict'], 'REUSED')
        self.assertEqual(self.footprint(), after)
        # The scheduler projection reads the run-specific import as well as
        # accepted specialist activities; only the unrelated authority seam is synthetic.
        snapshot = store.read_snapshot(self.root)
        document = copy.deepcopy(snapshot.document)
        document['agent_orchestration'] = {'work_items': {WORK: {'current_context_id': 'ctx',
            'contexts': {'ctx': {'predecessor_context_id': None}}, 'activities': {}}}}
        with mock.patch.object(store, 'read_snapshot', return_value=SimpleNamespace(document=document)):
            projected = cli._scheduler_accepted_tasks(self.root, WORK, self.dag, applied['import']['dag_sha256'], run_id=self.target)
        self.assertEqual(set(projected), set(accepted))
        runs.declare_wave(self.root, WORK, self.target, self.dag_ref, ['p04-a'], self.admission, activation_max_workers=2, **FLOORS)
        self.assertTrue(runs._all_converged(runs._read_runs(self.root, WORK)[self.target], ['p03-a', 'p03-b']))
        self.assertEqual(self.command('--apply', '--expected-sha256', preview['expected_sha256'])[1]['verdict'], 'REUSED')
        node = self.dag['nodes'][-1]
        runs.declare_worker(self.root, WORK, self.target, 'p04-a', 'wave-0001', 'medium', node['files'],
                            self.dag_ref, self.admission, **FLOORS)
        runs.terminate_worker(self.root, WORK, self.target, 'p04-a', 'completed', None, self.admission)
        result = runs.converge_wave(self.root, WORK, self.target, self.dag_ref, 'wave-0001', self.admission,
                                   execution_branch=self.git('branch', '--show-current'), **FLOORS)
        self.assertEqual(result['run_state'], 'COMPLETE')
        self.assertEqual(self.command('--apply', '--expected-sha256', preview['expected_sha256'])[1]['verdict'], 'REUSED')
        for ref, raw in before.items():
            if not ref.startswith('.git/'):
                self.assertEqual((self.root / ref).read_bytes(), raw)
        code, reconciled = self.command('--apply', verb='gauntlet-tasks-reconcile')
        self.assertEqual((code, reconciled.get('marked')), (0, ['T007', 'T008', 'T009']), reconciled)
        self.assertEqual(self.command('--apply', '--expected-sha256', preview['expected_sha256'])[1]['verdict'], 'REUSED')

    def test_cas_and_divergent_retry_are_no_write(self):
        preview, _ = self.apply()
        before = self.footprint()
        code, result = self.command('--apply', '--expected-sha256', '0' * 64)
        self.assertEqual((code, result['code']), (2, 'TASK-IMPORT-CAS-CONFLICT'))
        sources = {**self.sources, 'T009': self.source_runs[0]}
        self.assertEqual(self.command(sources=sources)[1]['code'], 'TASK-IMPORT-DIVERGENT')
        self.assertEqual(self.footprint(), before)
        with self.assertRaisesRegex(runs.GauntletRunError, 'already accepted'):
            runs.declare_wave(self.root, WORK, self.target, self.dag_ref, ['p03-a'], self.admission, activation_max_workers=2, **FLOORS)
        with self.assertRaisesRegex(runs.GauntletRunError, 'already accepted'):
            runs.prepare_worker(self.root, WORK, self.target, 'p03-a', ['shared.py'], self.admission)

    def test_preview_apply_rechecks_store_and_files(self):
        preview = self.command()[1]
        runs.admit_or_reuse_run(self.root, WORK, self.identity('4'))
        before = self.footprint()
        self.assertEqual(self.command('--apply', '--expected-sha256', preview['expected_sha256'])[1]['code'], 'TASK-IMPORT-CAS-CONFLICT')
        self.assertEqual(self.footprint(), before)
        path = self.root / self.result('T007')
        path.write_bytes(path.read_bytes() + b' ')
        self.assertEqual(self.command()[1]['code'], 'TASK-RESULT-DIVERGENT')

    def test_mismatch_tamper_and_missing_evidence_fail_closed(self):
        path = self.root / self.result('T009')
        original = path.read_bytes()
        for field, value in [('work_id', 'other'), ('node_id', 'p03-a'), ('task_id', 'T007'),
                             ('attempt_id', 'attempt-2'), ('scheduler_run_id', self.source_runs[0]), ('status', 'failed')]:
            document = json.loads(original); document[field] = value
            path.write_text(json.dumps(document))
            before = self.footprint()
            code, result = self.command()
            self.assertEqual((code, result['code']), (2, 'TASK-RESULT-DIVERGENT'), (field, result))
            self.assertEqual(self.footprint(), before)
        path.write_bytes(original)
        path.unlink()
        self.assertEqual(self.command()[1]['code'], 'TASK-IMPORT-EVIDENCE-MISSING')
        path.write_bytes(original)
        self.assertEqual(self.command(sources={'T007': self.source_runs[0]})[1]['code'], 'TASK-IMPORT-DIVERGENT')
        for suffix in ('terminal', 'converged', 'cleaned'):
            receipt = store.receipt_path(self.root, 'runtime', f'gauntlet-worker-{suffix}-{self.source_runs[1]}-p03-b')
            original_receipt = receipt.read_bytes()
            receipt.unlink()
            self.assertEqual(self.command()[1]['code'], 'TASK-IMPORT-EVIDENCE-MISSING')
            receipt.write_bytes(original_receipt + b' ')
            self.assertEqual(self.command()[1]['code'], 'TASK-IMPORT-EVIDENCE-MISSING')
            receipt.write_bytes(original_receipt)
        dag_path = self.root / self.dag_ref
        original_dag = dag_path.read_bytes()
        altered = copy.deepcopy(self.dag); altered['max_workers'] = 3
        dag_path.write_text(json.dumps(altered))
        self.assertEqual(self.command()[1]['code'], 'DAG-CONTENT-MISMATCH')
        dag_path.write_bytes(original_dag)
        altered = copy.deepcopy(self.dag); altered['accepted_tasks']['T007'] = {'state': 'ACCEPTED'}
        dag_path.write_text(json.dumps(altered))
        self.assertEqual(self.command()[1]['code'], 'TASK-IMPORT-DIVERGENT')
        dag_path.write_bytes(original_dag)
        task_path = self.root / self.tasks_ref
        task_path.write_text(task_path.read_text().replace('Existing work', 'Changed work'))
        self.assertEqual(self.command()[1]['code'], 'TASKS-SOURCE-STALE')

    def test_consumers_revalidate_import_receipt_and_result_hash(self):
        _, applied = self.apply()
        receipt = Path(applied['receipt_ref'])
        original = receipt.read_bytes()
        receipt.unlink()
        self.assertEqual(self.command(verb='gauntlet-tasks-reconcile')[1]['code'], 'TASK-IMPORT-EVIDENCE-MISSING')
        receipt.write_bytes(original)
        path = self.root / self.result('T007')
        path.write_bytes(path.read_bytes() + b' ')
        self.assertEqual(self.command(verb='gauntlet-tasks-reconcile')[1]['code'], 'TASK-RESULT-DIVERGENT')
        with self.assertRaises(runs.GauntletRunError):
            runs.declare_wave(self.root, WORK, self.target, self.dag_ref, ['p04-a'], self.admission, activation_max_workers=2, **FLOORS)

    def test_interrupted_apply_recovers_same_receipt_without_reexecution(self):
        transact = store.transact_with_event
        for index, point in enumerate(('after-receipt', 'after-event', 'after-anchor', 'after-snapshot')):
            if index:
                self.admission = self.identity(str(index + 3))
                self.target = runs.admit_or_reuse_run(self.root, WORK, self.admission)['run_id']
            preview = self.command()[1]
            def interrupted(*args, **kwargs):
                def fault(observed):
                    if observed == point:
                        raise RuntimeError('interrupted import')
                return transact(*args, **kwargs, fault=fault)
            with mock.patch.object(store, 'transact_with_event', side_effect=interrupted):
                code, interrupted_result = self.command('--apply', '--expected-sha256', preview['expected_sha256'])
                self.assertEqual((code, interrupted_result['code']), (2, 'UNEXPECTED-FAILURE'))
            self.assertEqual(self.command('--apply', '--expected-sha256', '0' * 64)[1]['code'], 'TASK-IMPORT-CAS-CONFLICT')
            code, replay = self.command('--apply', '--expected-sha256', preview['expected_sha256'])
            expected = 'APPLIED' if point == 'after-receipt' else 'REUSED'
            self.assertEqual((code, replay.get('verdict')), (0, expected), (point, replay))
            self.assertEqual(self.command('--apply', '--expected-sha256', preview['expected_sha256'])[1]['verdict'], 'REUSED')
            self.assertEqual(replay['receipt_sha256'], preview['receipt_sha256'])
            self.assertEqual(runs._read_runs(self.root, WORK)[self.target]['workers'], {})

    def test_nonterminal_cleanup_wave_and_symlink_evidence_are_rejected(self):
        original = runs._read_runs(self.root, WORK)
        source = self.source_runs[0]
        for target, key, value in [('worker', 'state', 'TERMINAL'), ('workspace', 'converged', False),
                                   ('wave', 'state', 'ACTIVE'), ('wave', 'converged', False)]:
            changed = copy.deepcopy(original)
            worker = changed[source]['workers']['p03-a']
            record = {'worker': worker, 'workspace': worker['workspace'],
                      'wave': changed[source]['waves']['wave-0001']}[target]
            record[key] = value
            with mock.patch.object(runs, '_read_runs', return_value=changed):
                self.assertEqual(self.command()[1]['code'], 'TASK-IMPORT-EVIDENCE-MISSING')
        path = self.root / self.result('T007')
        original_bytes = path.read_bytes()
        path.unlink()
        try:
            path.symlink_to('T008.tasks.json')
        except OSError:
            path.write_bytes(original_bytes)
            return  # Windows without symlink privilege; other evidence cases still ran.
        self.assertEqual(self.command()[1]['code'], 'TASK-SCOPE-VIOLATION')


if __name__ == '__main__':
    unittest.main()
