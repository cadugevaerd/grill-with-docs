import hashlib, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
REAL = Path('/home/carlosaraujo/orca/workspaces/grill-with-docs/feat-new-subagents')
OUT = Path(__file__).parent
TOOLCHAIN = REAL / '.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/cycle-toolchain-5.4.1.json'
manifest = json.loads(TOOLCHAIN.read_bytes())
HIST = Path(manifest['root'])
sha = lambda b: hashlib.sha256(b).hexdigest()
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'GIT_OPTIONAL_LOCKS':'0', 'GIT_CONFIG_NOSYSTEM':'1', 'GIT_CONFIG_GLOBAL':'/dev/null'}
def git(root, *args, check=True):
    p = subprocess.run(['git', '-C', str(root), *args], text=True, capture_output=True, env=env)
    if check and p.returncode: raise AssertionError((args,p.returncode,p.stdout,p.stderr))
    return p.stdout.strip() if check else p

def real_snapshot():
    paths = git(REAL, 'ls-files', '-co', '--exclude-standard', '-z').split('\0')
    files = {p:sha((REAL/p).read_bytes()) for p in paths if p and (REAL/p).is_file()}
    index = Path(git(REAL,'rev-parse','--path-format=absolute','--git-path','index'))
    return {'HEAD':git(REAL,'rev-parse','HEAD'), 'refs':git(REAL,'show-ref'), 'index_sha256':sha(index.read_bytes()), 'status':git(REAL,'status','--porcelain=v1','--untracked-files=all'), 'files_sha256':files, 'worktrees':git(REAL,'worktree','list','--porcelain')}
before = real_snapshot()
(OUT/'real-before.json').write_text(json.dumps(before, indent=2))
for name, digest in manifest['files_sha256'].items():
    assert sha((HIST/name).read_bytes()) == digest, name
sys.path.insert(0, str(HIST/'skills/grill-with-docs/scripts'))
from grill_core import gauntlet_runs as g, store
assert Path(g.__file__).is_relative_to(HIST)
result = {'historical_bundle_files_verified':len(manifest['files_sha256']), 'historical_module':g.__file__, 'historical_sha256':sha(Path(g.__file__).read_bytes()), 'checks':[]}
def passed(name, **data): result['checks'].append({'check':name, **data})
def denied(name, fn, code):
    try: fn()
    except (g.GauntletRunError, store.StoreError) as exc:
        assert exc.code == code, (exc.code,code)
        passed(name, code=code)
    else: raise AssertionError('expected '+code)
with tempfile.TemporaryDirectory(prefix='git-', dir=OUT) as d:
    root = Path(d)
    git(root,'init','-q','-b','execution')
    git(root,'config','user.name','Disposable HOW proof')
    git(root,'config','user.email','how@example.invalid')
    def write(rel, content, where=root):
        p=where/rel; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content,bytes) else content.encode())
    def commit(where, message):
        git(where,'add','--all'); git(where,'commit','-qm',message)
        return git(where,'rev-parse','HEAD')
    for name in ('common.sh','check-prerequisites.sh'):
        write('.specify/scripts/bash/'+name, (REAL/'.specify/scripts/bash'/name).read_bytes())
    write('.specify/feature.json','{"feature_directory":"specs/029-old"}\n')
    write('specs/029-old/plan.md','old plan\n'); write('specs/029-old/tasks.md','old tasks\n')
    write('.gitignore','ignored-output\n')
    base = commit(root,'historical B')
    pid = store.project_identity(root)['project_id']
    admission = {k: str(i)*64 for i,k in enumerate(g._ADMISSION_IDENTITY_KEYS,1)}
    admission['base_commit']=base
    work_id='how-proof'
    run_id=g.admit_or_reuse_run(root,work_id,admission)['run_id']
    dag={'schema':'grill-gauntlet-execution-dag/v1','feature':'030-agent-orchestration','max_workers':1,'nodes':[
        {'id':'p01-a','depends_on':[],'files':['src/a.py','specs/030-agent-orchestration/implement/p01-a.tasks.json'],'parallel':True,'tier':'medium'},
        {'id':'p02-a','depends_on':['p01-a'],'files':['src/b.py','specs/030-agent-orchestration/implement/p02-a.tasks.json'],'parallel':True,'tier':'medium'}]}
    for p in (REAL/'specs/030-agent-orchestration').rglob('*'):
        if p.is_file(): write(str(p.relative_to(REAL)),p.read_bytes())
    write('.specify/feature.json',(REAL/'.specify/feature.json').read_bytes())
    write('.grill/context.md','pre-existing leader planning input\n')
    write('dag.json',json.dumps(dag))
    planning=commit(root,'leader planning P')
    assert git(root,'merge-base','--is-ancestor',base,planning,check=False).returncode==0
    floors={'agent_execute_floor':'medium','markdown_floor':'small'}
    def live_admission(): return {**admission,'base_commit':git(root,'rev-parse','HEAD')}
    def run(): return g._read_runs(root,work_id)[run_id]
    def declare(i):
        node=dag['nodes'][i-1]
        wave=g.declare_wave(root,work_id,run_id,'dag.json',[node['id']],live_admission(),activation_max_workers=1,**floors)['wave_id']
        def invoke(): return g.declare_worker(root,work_id,run_id,node['id'],wave,'medium',node['files'],'dag.json',live_admission(),runtime='codex',**floors)
        prepared=invoke(); target, workspace=g._workspace_identity(root,work_id,run_id,node['id'],admission)
        assert prepared['verdict']=='WORKER-PREPARED' and git(target,'rev-parse','HEAD')==base
        assert invoke()['verdict']=='REUSED'
        return node,wave,target,workspace,invoke
    def prerequisites(where, extra=None, paths_only=False):
        e={k:v for k,v in env.items() if not k.startswith('SPECIFY_')}; e['SPECIFY_INIT_DIR']=str(where)
        e.update(extra or {})
        args=['bash',str(where/'.specify/scripts/bash/check-prerequisites.sh'),'--json']
        args += ['--paths-only'] if paths_only else ['--require-tasks','--include-tasks']
        p=subprocess.run(args,cwd=where,env=e,text=True,capture_output=True)
        assert p.returncode==0,(p.stdout,p.stderr)
        return json.loads(p.stdout)
    node,wave,w1,ws1,redeclare=declare(1)
    assert prerequisites(w1)['FEATURE_DIR']==str(w1/'specs/029-old')
    passed('historical base resolves obsolete 029 without bootstrap')
    git(w1,'merge','--ff-only',planning)
    assert git(w1,'rev-parse','HEAD')==planning
    assert not g._branch_changed_paths(root,ws1['branch'])
    assert g._workspace_git_state(root,w1,ws1)=='DIVERGENT'
    denied('declare replay after FF is preserved',redeclare,'WORKSPACE-PRESERVED')
    assert run()['workers']['p01-a']['state']=='PREPARED'
    assert g._exact_worktree_is_clean(root,w1)
    feature_before=sha((w1/'.specify/feature.json').read_bytes())
    assert prerequisites(w1)['FEATURE_DIR']==str(w1/'specs/030-agent-orchestration')
    assert feature_before==sha((w1/'.specify/feature.json').read_bytes())
    assert not git(w1,'status','--porcelain=v1')
    passed('FF planning: own diff empty; correct 030 prerequisites clean', base=base, planning=planning)
    # No-persist path resolution is insufficient: it skips required-file validation.
    missing=str(w1/'specs/missing')
    assert prerequisites(w1,{'SPECIFY_FEATURE_DIRECTORY':missing},True)['FEATURE_DIR']==missing
    assert feature_before==sha((w1/'.specify/feature.json').read_bytes())
    passed('paths-only resolves missing dir with success and no validation')
    # Demonstrate the historical write side effect, then restore only in disposable Git.
    assert prerequisites(w1,{'SPECIFY_FEATURE_DIRECTORY':'specs/029-old'})['FEATURE_DIR']==str(w1/'specs/029-old')
    assert feature_before!=sha((w1/'.specify/feature.json').read_bytes())
    git(w1,'restore','--','.specify/feature.json')
    passed('divergent feature override writes tracked file')
    write('src/a.py','DEPENDENCY = 1\n',w1)
    write(node['files'][1],'{"completed":["T001"]}\n',w1)
    head1=commit(w1,'phase 1 worker own output')
    assert g._branch_changed_paths(root,ws1['branch'])==set(node['files'])
    g.record_progress(root,work_id,run_id,node['id'],live_admission())
    g.terminate_worker(root,work_id,run_id,node['id'],'completed',None,live_admission())
    conv1=g.converge_wave(root,work_id,run_id,'dag.json',wave,live_admission(),execution_branch='execution',**floors)
    integrated1=git(root,'rev-parse','HEAD')
    assert conv1['wave_converged'] and (root/'src/a.py').read_text()=='DEPENDENCY = 1\n'
    assert g.cleanup_worker(root,work_id,run_id,node['id'],live_admission())['verdict']=='PRESERVED'
    assert run()['workers']['p01-a']['workspace']['base_commit']==base
    passed('phase 1 terminate/converge accepts original admission, cleanup preserves', worker=head1,integrated=integrated1,own_paths=node['files'])
    node,wave,w2,ws2,redeclare2=declare(2)
    assert not (w2/'src/a.py').exists()
    git(w2,'merge','--ff-only',integrated1)
    assert (w2/'src/a.py').read_text()=='DEPENDENCY = 1\n'
    assert g._branch_changed_paths(root,ws2['branch'])==set()
    assert g._workspace_git_state(root,w2,ws2)=='DIVERGENT'
    assert prerequisites(w2)['FEATURE_DIR']==str(w2/'specs/030-agent-orchestration')
    write('src/b.py','from a import DEPENDENCY\nRESULT = DEPENDENCY + 1\n',w2)
    write(node['files'][1],'{"completed":["T002"]}\n',w2)
    head2=commit(w2,'phase 2 worker own output')
    assert git(root,'merge-base','HEAD',ws2['branch'])==integrated1
    assert g._branch_changed_paths(root,ws2['branch'])==set(node['files'])
    passed('phase 2 inherits phase 1; own diff excludes all inherited paths', worker=head2,input=integrated1,own_paths=node['files'])
    # A clean branch with out-of-grant edits still fails real convergence.
    write('.grill/context.md','unauthorized worker rewrite\n',w2)
    bad=commit(w2,'out-of-grant negative control')
    g.terminate_worker(root,work_id,run_id,node['id'],'completed',None,live_admission())
    denied('worker own protected-path change is not inheritance',lambda:g.converge_wave(root,work_id,run_id,'dag.json',wave,live_admission(),execution_branch='execution',**floors),'GRANT-SCOPE-VIOLATION')
    assert git(root,'rev-parse','HEAD')==integrated1
    # Revert is confined to the disposable negative control, never proposed for real campaign.
    git(w2,'revert','--no-edit',bad)
    # Historical helper examines net tree diff, not every commit's effects.
    assert g._branch_changed_paths(root,ws2['branch'])==set(node['files'])
    assert '.grill/context.md' in git(w2,'log','--format=','--name-only',integrated1+'..HEAD').splitlines()
    passed('net diff alone misses changed-then-reverted protected file; per-commit guard catches it')
    # Legitimate local commits do not change project identity, unlike orphan roots.
    assert store.project_identity(root)['project_id']==pid
    assert store.project_identity(w2)['project_id']==pid
    own_before=git(w2,'rev-parse','HEAD')
    assert git(w2,'merge','--ff-only',integrated1,check=False).returncode==0
    assert git(w2,'rev-parse','HEAD')==own_before!=integrated1
    passed('ff-only after payload can succeed as no-op; exact HEAD precondition mandatory')
    # Tracked dirt at coordinator blocks even with legitimate worker own diff.
    write('.specify/feature.json','{"feature_directory":"specs/029-old"}\n')
    denied('tracked control dirt blocks convergence',lambda:g.converge_wave(root,work_id,run_id,'dag.json',wave,live_admission(),execution_branch='execution',**floors),'EXECUTION-TREE-DIRTY')
    git(root,'restore','--','.specify/feature.json')
    result2=g.converge_wave(root,work_id,run_id,'dag.json',wave,live_admission(),execution_branch='execution',**floors)
    assert result2['run_state']=='COMPLETE'
    assert run()['admission']==admission
    assert all(ev['base_commit']==base for ev in store.read_events(root) if ev.get('event','').startswith('gauntlet.'))
    denied('cleanup on completed run blocked',lambda:g.cleanup_worker(root,work_id,run_id,node['id'],live_admission()),'RUN-NOT-ELIGIBLE')
    passed('phase 2 real convergence completes; every event retains historical base', final_head=git(root,'rev-parse','HEAD'),project_identity=pid)
    # Ignored artifacts are invisible to the old helper; require explicit ignored inventory.
    write('ignored-output','evidence hidden by ignore\n',w2)
    assert g._exact_worktree_is_clean(root,w2)
    assert git(w2,'ls-files','--others','--ignored','--exclude-standard')=='ignored-output'
    passed('historical clean check omits ignored paths')
after=real_snapshot()
(OUT/'real-after.json').write_text(json.dumps(after,indent=2))
assert before==after,'real workspace changed during proof; inspect snapshots'
result['real_workspace_unchanged']=True
result['temporary_git_removed']=True
result['limitations']=['Core functions use synthetic admission in disposable repository; no real activation, macrostep, worker or wave executed.','Negative control reverted only inside disposable Git; final synthetic merge intentionally demonstrates net-diff limitation, not accepted real-worker conduct.']
(OUT/'proof-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
