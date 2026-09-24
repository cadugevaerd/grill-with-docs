#!/usr/bin/env python3
"""Five offline repetitions against the pre-change source; no runtime processes."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import types
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BASE = 'af0d435'
PREFIX = 'plugin/skills/grill-with-docs/'
SCRIPTS = ROOT / PREFIX / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from grill_core import agent_runtime, partition, step_skills


def historical_bytes(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def historical_module(name):
    module = types.ModuleType('benchmark_old_' + name)
    module.__file__ = str(SCRIPTS/'grill_core'/f'{name}.py')
    sys.modules[module.__name__] = module
    source = historical_bytes(PREFIX + f'scripts/grill_core/{name}.py')
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module


def measure(fn):
    elapsed = []
    for _ in range(5):
        start = time.perf_counter()
        fn()
        elapsed.append((time.perf_counter() - start) * 1000)
    return {'median_ms': round(statistics.median(elapsed), 3), 'samples_ms': [round(n,3) for n in elapsed]}


def main():
    assets = SCRIPTS.parent/'assets'
    registry = (assets/'workflow-step-skills.v4.json').read_bytes()
    catalog = json.loads((assets/'codex-v4-local-skills.catalog.json').read_bytes())
    steps = tuple(json.loads(registry)['steps'])
    output = {'baseline_commit': BASE, 'repetitions': 5, 'limitations':
              'Synthetic offline timings; no LLM sessions, human waiting or live import measured.'}
    for label, resolver in [('before', historical_module('step_skills')), ('after', step_skills)]:
        def resolve():
            return resolver.resolve_shipped_workflow_skills(steps, 'codex', resolver.registry_sha256(registry),
                registry=registry, catalog=catalog, trusted_catalogs_path=assets/'workflow-trusted-catalogs.v4.json')
        with mock.patch.object(resolver, 'parse_and_hash_registry', wraps=resolver.parse_and_hash_registry) as parsed:
            timing = measure(resolve)
        output.setdefault('small_change_resolution', {})[label] = {**timing, 'registry_parses_per_call': parsed.call_count//5}
    text = '<!-- grill-task-files:v1 -->\n## Phase 1: Work\n'
    for i in range(1,7):
        text += f'- [ ] T{i:03} [P] Part {i}\n  Files: ["part{i}.py", "specs/demo/implement/T{i:03}.tasks.json"]\n  Result: "specs/demo/implement/T{i:03}.tasks.json"\n'
    for label, groups in [('before',3), ('after',2)]:
        for scenario, accepted in [('independent_tasks', {}), ('resume_accepted_tasks', {'T001':{}, 'T002':{}})]:
            def run_partition():
                return partition.partition_task_files(text, feature='demo', groups=groups, accepted_tasks=accepted)
            timing = measure(run_partition)
            dag, _ = run_partition()
            pending = {task for node in dag['nodes'] for task in node['task_ids']}
            output.setdefault(scenario, {})[label] = {**timing, 'worker_nodes':len(dag['nodes']),
                'pending_tasks':len(pending), 'accepted_tasks_repeated':len(set(accepted)&pending)}
    events = [({'name':'exec_command','input':{'cmd':'/bin/true'}},str(i),'{}') for i in range(500)]
    for label, runtime in [('before',historical_module('agent_runtime')),('after',agent_runtime)]:
        with mock.patch.object(runtime, '_tool_results', side_effect=lambda _:iter(events)), \
             mock.patch.object(runtime, '_runtime_config_axes', return_value={}), \
             mock.patch.object(runtime.shutil, 'which', return_value='/bin/codex') as which:
            timing = measure(lambda: runtime._orca_presentation_axes({'provider':'codex'}, {}))
        output.setdefault('presentation_scan', {})[label] = {**timing, 'path_resolutions_per_call':which.call_count//5}
    paths = ['SKILL.md','references/session-protocol.md']
    output['startup_context_bytes'] = {
        'before':sum(len(historical_bytes(PREFIX + p)) for p in paths) + len(historical_bytes(PREFIX+'references/agent-orchestration.md')),
        'after':sum((ROOT/PREFIX/p).stat().st_size for p in paths) + (ROOT/PREFIX/'references/agent-orchestration.v2.md').stat().st_size,
        'excludes':'Operation manuals loaded only when needed; policy JSON and upstream reference excluded equally.'}
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
