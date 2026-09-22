#!/usr/bin/env python3
"""Mixed historical runs, real Git/Store receipts, offline public CLI boundary."""
import contextlib
import concurrent.futures
import copy
import hashlib
import io
import json
import subprocess
import sys
import threading
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

    def race_import_with_local(self, local_kind, *, import_wins, node_id='p03-a',
                               dag_ref=None, expected_code=None):
        preview = runs.import_task_results(self.root, WORK, self.target, self.dag_ref, self.sources, self.admission)
        def importing():
            return runs.import_task_results(self.root, WORK, self.target, self.dag_ref, self.sources,
                self.admission, apply=True, expected_sha256=preview['expected_sha256'])
        def local():
            if local_kind == 'worker':
                return runs.prepare_worker(self.root, WORK, self.target, node_id, ['shared.py'],
                                           self.admission)
            return runs.declare_wave(self.root, WORK, self.target, dag_ref or self.dag_ref, [node_id],
                                    self.admission, activation_max_workers=2, **FLOORS)
        def effects():
            # The paused import owns a temporary work lock; exclude only its
            # owner file, retaining WAL/receipts/journal and all Git resources.
            return ({ref: raw for ref, raw in self.footprint().items() if not ref.endswith('/owner.json')},
                    self.git('worktree', 'list', '--porcelain'), self.git('for-each-ref', 'refs/heads'))
        delayed_event = f'gauntlet.{local_kind}.declared' if import_wins else 'gauntlet.tasks.imported'
        checked, resume = threading.Event(), threading.Event()
        transact = store.transact_with_event
        def paused(root, mutate, **kwargs):
            if kwargs['event']['event'] == delayed_event:
                checked.set()
                self.assertTrue(resume.wait(30), 'winner did not finish')
            return transact(root, mutate, **kwargs)
        with mock.patch.object(store, 'transact_with_event', side_effect=paused):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                loser = pool.submit(local if import_wins else importing)
                try:
                    self.assertTrue(checked.wait(30), 'loser did not reach the precommit boundary')
                    winner = importing() if import_wins else local()
                    before = effects()
                finally:
                    resume.set()
                with self.assertRaises(runs.GauntletRunError) as blocked:
                    loser.result(timeout=30)
        self.assertEqual(blocked.exception.code, expected_code or (
            'TASK-ALREADY-IMPORTED' if import_wins else 'TASK-IMPORT-CAS-CONFLICT'))
        self.assertEqual(effects(), before)
        run = runs._read_runs(self.root, WORK)[self.target]
        if import_wins:
            self.assertEqual(winner['verdict'], 'APPLIED')
            self.assertEqual(run['workers'], {})
            self.assertFalse(runs._workspace_identity(self.root, WORK, self.target, node_id, self.admission)[0].exists())
            self.assertTrue(runs._is_placeholder_wave(run['waves']['wave-0001']))
            self.assertTrue(runs.verified_task_import(self.root, WORK, self.target))
        else:
            self.assertEqual(winner['verdict'], 'WORKER-PREPARED' if local_kind == 'worker' else 'WAVE-DECLARED')
            self.assertNotIn('task_import', run)
            self.assertFalse(Path(preview['receipt_ref']).exists())
            if local_kind == 'worker':
                self.assertEqual(run['workers']['p03-a']['state'], 'PREPARED')
            else:
                self.assertEqual(run['waves']['wave-0001'], {'state': 'ACTIVE', 'node_ids': ['p03-a']})

    def test_import_wins_worker_interleaving_without_local_effects(self):
        self.race_import_with_local('worker', import_wins=True)

    def test_worker_wins_import_interleaving_without_import_effects(self):
        self.race_import_with_local('worker', import_wins=False)

    def test_import_wins_wave_interleaving_without_local_effects(self):
        self.race_import_with_local('wave', import_wins=True)

    def test_wave_wins_import_interleaving_without_import_effects(self):
        self.race_import_with_local('wave', import_wins=False)

    def alternate_dag(self):
        other = copy.deepcopy(self.dag)
        for node in other['nodes']:
            if node['id'] == 'p03-b':
                node['id'] = 'p03-x'
            node['depends_on'] = ['p03-x' if dep == 'p03-b' else dep for dep in node['depends_on']]
        ref = 'specs/demo/execution-dag.r2.json'
        self.write(ref, json.dumps(other))
        self.write('specs/demo/partition-report.r2.json', json.dumps(self.report))
        return ref

    def complete_import_sources(self):
        self.apply()
        source = self.target
        node = self.dag['nodes'][-1]
        runs.declare_wave(self.root, WORK, source, self.dag_ref, ['p04-a'], self.admission,
                          activation_max_workers=2, **FLOORS)
        runs.declare_worker(self.root, WORK, source, 'p04-a', 'wave-0001', 'medium', node['files'],
                            self.dag_ref, self.admission, **FLOORS)
        workspace = runs._workspace_identity(self.root, WORK, source, 'p04-a', self.admission)[0]
        result = dict(schema='grill-task-result/v1', work_id=WORK, scheduler_run_id=source,
                      node_id='p04-a', task_id='T011', attempt_id='attempt-1', status='completed', diagnostic_ref=None)
        path = workspace / self.result('T011')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result))
        subprocess.run(['git', '-C', str(workspace), 'add', '.'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(workspace), 'commit', '-qm', 'last result'], check=True, capture_output=True)
        runs.terminate_worker(self.root, WORK, source, 'p04-a', 'completed', None, self.admission)
        runs.converge_wave(self.root, WORK, source, self.dag_ref, 'wave-0001', self.admission,
                          execution_branch=self.git('branch', '--show-current'), **FLOORS)
        self.sources['T011'] = source
        self.admission = self.identity('4')
        self.target = runs.admit_or_reuse_run(self.root, WORK, self.admission)['run_id']

    def test_import_pins_dag_before_alternate_wave_without_local_effects(self):
        other_ref = self.alternate_dag()
        self.sources = {task: source for task, source in self.sources.items() if task in ('T007', 'T008')}
        self.race_import_with_local('wave', import_wins=True, dag_ref=other_ref, node_id='p03-x',
                                    expected_code='DAG-CONTENT-MISMATCH')

    def test_complete_import_before_generic_prepare_without_local_effects(self):
        self.complete_import_sources()
        cli._require_scheduler_task_phase(self.root, runs,
            SimpleNamespace(work_id=WORK, run_id=self.target), 'generic-worker')
        self.race_import_with_local('worker', import_wins=True, node_id='generic-worker',
                                    expected_code='RUN-NOT-ELIGIBLE')
        self.assertEqual(runs._read_runs(self.root, WORK)[self.target]['state'], 'COMPLETE')

    def test_complete_import_before_alternate_wave_without_local_effects(self):
        self.complete_import_sources()
        self.race_import_with_local('wave', import_wins=True, dag_ref=self.alternate_dag(), node_id='p03-x',
                                    expected_code='RUN-NOT-ELIGIBLE')
        self.assertEqual(runs._read_runs(self.root, WORK)[self.target]['state'], 'COMPLETE')

    def test_import_pins_dag_before_generic_prepare_without_local_effects(self):
        self.race_import_with_local('worker', import_wins=True, node_id='generic-worker',
                                    expected_code='DAG-CONTENT-MISMATCH')

    def wave_after_change(self, change, code):
        transact = store.transact_with_event
        before = None
        def paused(root, mutate, **kwargs):
            nonlocal before
            if kwargs['event']['event'] == 'gauntlet.wave.declared':
                change()
                before = (self.footprint(), self.git('worktree', 'list', '--porcelain'),
                          self.git('for-each-ref', 'refs/heads'))
            return transact(root, mutate, **kwargs)
        with mock.patch.object(store, 'transact_with_event', side_effect=paused):
            with self.assertRaises(runs.GauntletRunError) as blocked:
                runs.declare_wave(self.root, WORK, self.target, self.dag_ref, ['p03-a', 'p03-b'],
                                  self.admission, activation_max_workers=2, **FLOORS)
        self.assertEqual(blocked.exception.code, code)
        self.assertEqual((self.footprint(), self.git('worktree', 'list', '--porcelain'),
                          self.git('for-each-ref', 'refs/heads')), before)

    def test_wave_rechecks_dag_content_before_commit_without_effects(self):
        self.wave_after_change(lambda: self.write(self.dag_ref, json.dumps({**self.dag, 'max_workers': 3})),
                               'DAG-CONTENT-MISMATCH')

    def test_wave_rechecks_current_worker_cap_before_commit_without_effects(self):
        self.wave_after_change(lambda: runs.prepare_worker(self.root, WORK, self.target,
            'generic-worker', ['unrelated.py'], self.admission), 'WAVE-CAP-EXCEEDED')

    def test_legacy_local_conflicts_block_import_consumers_without_writes(self):
        for kind in ('worker', 'wave'):
            with self.subTest(kind=kind):
                if kind == 'wave':
                    self.admission = self.identity('4')
                    self.target = runs.admit_or_reuse_run(self.root, WORK, self.admission)['run_id']
                preview, _ = self.apply()
                lease = runs._new_coordinator_lease(self.target, 'p03-a')
                def legacy_write(document):
                    run = document['work_items'][WORK]['gauntlet']['runs'][self.target]
                    if kind == 'worker':
                        run['workers']['p03-a'] = dict(state='DECLARED', lease=lease, grant=None,
                            workspace=None, node_id='p03-a', remediates=None)
                    else:
                        run['waves']['wave-0001'] = dict(state='ACTIVE', node_ids=['p03-a'])
                    return document
                # Model bytes accepted by 68034c2 using real Store transitions,
                # bypassing only the repaired writer guards, never the reader.
                kwargs = dict(name=f'legacy-{kind}-{self.target}', event_name=f'gauntlet.{kind}.declared',
                              work_id=WORK, run_id=self.target, admission=self.admission)
                receipt, event = (runs._worker_receipt_event(**kwargs, worker_id='p03-a', lease=lease)
                                  if kind == 'worker' else runs._receipt_and_event(**kwargs))
                store.transact_with_event(self.root, legacy_write, event=event, receipt=receipt)
                before = self.footprint()
                for consume in (runs.verified_task_import, runs.run_projection):
                    with self.assertRaises(runs.GauntletRunError) as blocked:
                        consume(self.root, WORK, self.target)
                    self.assertEqual(blocked.exception.code, 'TASK-IMPORT-DIVERGENT')
                for tail, verb in [((), 'gauntlet-tasks-import'),
                        (('--apply', '--expected-sha256', preview['expected_sha256']), 'gauntlet-tasks-import'),
                        (('--apply',), 'gauntlet-tasks-reconcile')]:
                    code, result = self.command(*tail, verb=verb)
                    self.assertEqual((code, result['code']), (2, 'TASK-IMPORT-DIVERGENT'))
                with self.assertRaises(runs.GauntletRunError) as blocked:
                    runs.declare_wave(self.root, WORK, self.target, self.dag_ref, ['p04-a'],
                                     self.admission, activation_max_workers=2, **FLOORS)
                self.assertEqual(blocked.exception.code, 'TASK-IMPORT-DIVERGENT')
                self.assertEqual(self.footprint(), before)

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
