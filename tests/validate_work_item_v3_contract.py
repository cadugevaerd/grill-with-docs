#!/usr/bin/env python3
"""Contract matrix for grill-work-item/v3: dual-read, qualified ids, preview-first migration."""
import contextlib, importlib.util, io, json, os, shlex, shutil, socket, stat, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path
from unittest import mock

REPO=Path(__file__).resolve().parents[1]
PLUGIN=REPO/'plugin'
SCRIPTS=PLUGIN/'skills/grill-with-docs/scripts'
WORKSPACE=SCRIPTS/'grill_workspace.py'
TEMPLATE=PLUGIN/'skills/grill-with-docs/assets/WORKFLOW.template.md'
V3_TEMPLATE=PLUGIN/'skills/grill-with-docs/assets/WORKFLOW.v3.template.md'
sys.path.insert(0,str(SCRIPTS))
from grill_core import work_item_v3 as M  # noqa: E402
from grill_core import workflow_v3 as WV3  # noqa: E402

WORK_ID='wx'
SOURCE={'kind':'backlog-request','request_key':'a'*64,'relation':'non-blocking','source_ref':'gauntlet/run-1/F-003'}

# Worker for the real-subprocess stale-lock-reclaim race (see
# test_stale_lock_reclaim_never_lets_two_processes_hold_it_at_once). Traces
# the *entire* held duration of _BundleLock around a real migrate_bundle
# call, with an artificial in-critical-section delay so any overlap between
# two racing processes is trivially observable instead of timing luck.
_LOCK_RACE_WORKER = r'''
import json, os, sys, time
from pathlib import Path

scripts_dir, item_dir, parent, record_path, go_path, delay = sys.argv[1:7]
sys.path.insert(0, scripts_dir)
from grill_core import work_item_v3 as M

M.production_reader_accepts_v3 = lambda: True

original_enter = M._BundleLock.__enter__
original_exit = M._BundleLock.__exit__

def traced_enter(self):
    result = original_enter(self)
    with open(record_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"pid": os.getpid(), "event": "enter", "t": time.monotonic()}) + "\n")
    time.sleep(float(delay))
    return result

def traced_exit(self, *args):
    with open(record_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"pid": os.getpid(), "event": "exit", "t": time.monotonic()}) + "\n")
    return original_exit(self, *args)

M._BundleLock.__enter__ = traced_enter
M._BundleLock.__exit__ = traced_exit

while not os.path.exists(go_path):
    time.sleep(0.001)

try:
    result = M.migrate_bundle(Path(item_dir), apply=True, parent_work_id=parent)
    print(json.dumps({"ok": True, "verdict": result["verdict"]}))
except M.WorkItemError as exc:
    print(json.dumps({"ok": False, "code": exc.code}))
'''

# Real, independent OS process for the CAS attack (see
# test_stale_document_between_decision_and_write_is_refused). It never
# touches grill_core.work_item_v3 or its lock at all -- exactly "a writer
# outside this lock's domain" -- and only watches the filesystem for the
# lock directory that _BundleLock creates to know when to strike. It reads
# the real on-disk bytes, mutates one unrelated top-level key, and writes
# back with the same temp-file-same-dir + os.replace pattern production code
# uses, so the race is against a realistic concurrent writer, not a mock.
_EXTERNAL_WRITER = r'''
import json, os, sys, time
from pathlib import Path

path, lock_dir = sys.argv[1:3]
deadline = time.monotonic() + 10.0
while not os.path.isdir(lock_dir):
    if time.monotonic() > deadline:
        print("timeout-waiting-for-lock")
        raise SystemExit(1)
    time.sleep(0.0002)
data = json.loads(Path(path).read_text(encoding="utf-8"))
data["scope"] = {"EXTERNAL_WRITER": "this change must not vanish"}
tmp = Path(path).with_name(Path(path).name + ".external-writer-tmp")
tmp.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
os.replace(tmp, path)
print("written")
'''

def symlink_supported():
 with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
  try: (Path(temporary)/'link').symlink_to(Path(temporary))
  except (OSError,NotImplementedError): return False
  return True
SYMLINKS=symlink_supported()

def build_v2_bundle(destination):
 """Produce a real v2 bundle with the live CLI, then hand it over as a template."""
 with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
  root=Path(temporary)
  subprocess.run(['git','init','-q','-b','main',str(root)],check=True)
  (root/'WORKFLOW.md').write_bytes(TEMPLATE.read_bytes())
  subprocess.run(['git','-C',str(root),'config','user.email','t@e'],check=True)
  subprocess.run(['git','-C',str(root),'config','user.name','t'],check=True)
  subprocess.run(['git','-C',str(root),'add','.'],check=True)
  subprocess.run(['git','-C',str(root),'commit','-qm','init'],check=True)
  done=subprocess.run([sys.executable,str(WORKSPACE),'init',str(root),'--type','feature','--slug','x','--work-id',WORK_ID,'--skip-backlog'],text=True,capture_output=True)
  assert done.returncode==0,done.stdout
  shutil.copytree(root/'.grill/work-items'/WORK_ID,destination)

def build_v2_repo(root):
 """Like build_v2_bundle, but keeps the whole live repo (for CLI round-trips)."""
 subprocess.run(['git','init','-q','-b','main',str(root)],check=True)
 (root/'WORKFLOW.md').write_bytes(TEMPLATE.read_bytes())
 subprocess.run(['git','-C',str(root),'config','user.email','t@e'],check=True)
 subprocess.run(['git','-C',str(root),'config','user.name','t'],check=True)
 subprocess.run(['git','-C',str(root),'add','.'],check=True)
 subprocess.run(['git','-C',str(root),'commit','-qm','init'],check=True)
 done=subprocess.run([sys.executable,str(WORKSPACE),'init',str(root),'--type','feature','--slug','x','--work-id',WORK_ID,'--skip-backlog'],text=True,capture_output=True)
 assert done.returncode==0,done.stdout

def cli_status(root):
 completed=subprocess.run([sys.executable,str(WORKSPACE),'status',str(root),'--work-id',WORK_ID],text=True,capture_output=True)
 return completed.returncode

def snapshot(root):
 return {p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mtime_ns) for p in sorted(root.rglob('*')) if p.is_file()}

def load_workspace_module():
 spec=importlib.util.spec_from_file_location('work_item_v3_contract_workspace',WORKSPACE)
 assert spec is not None and spec.loader is not None
 module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
 spec.loader.exec_module(module)
 # Fault-injection cases call the same public main()/parser boundary as a
 # subprocess, but share this module instance so the already-public
 # descriptor helpers can be patched without a production-only test hook.
 module._GRILL_CORE['work_item_v3']=M
 return module

CLI=load_workspace_module()

def render_v3_workflow_bytes():
 rendered=WV3.render_v3(V3_TEMPLATE.read_text(encoding='utf-8'),WV3.registry_state()['sha256'])
 assert '__REGISTRY_SHA256__' not in rendered
 return rendered.encode('utf-8')

def invoke_workspace(*args):
 completed=subprocess.run([sys.executable,str(WORKSPACE),*(str(value) for value in args)],text=True,capture_output=True)
 lines=completed.stdout.splitlines()
 assert len(lines)==1,f'expected one JSON line: stdout={completed.stdout!r} stderr={completed.stderr!r}'
 return completed,json.loads(lines[0])

def invoke_workspace_in_process(*args):
 output=io.StringIO(); errors=io.StringIO()
 with contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
  returncode=CLI.main([str(value) for value in args])
 lines=output.getvalue().splitlines()
 assert len(lines)==1,f'expected one JSON line: stdout={output.getvalue()!r} stderr={errors.getvalue()!r}'
 return returncode,json.loads(lines[0]),errors.getvalue()

def build_rebind_repo(root):
 """Create the contract's legacy state: V3 item still pinned to V2 workflow."""
 build_v2_repo(root)
 migrated,payload=invoke_workspace('migrate-v3',root,'--work-id',WORK_ID,'--apply')
 assert migrated.returncode==0 and payload.get('verdict')=='APPLIED',payload
 (root/'WORKFLOW.md').write_bytes(render_v3_workflow_bytes())

class WorkItemV3Contract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.template=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); build_v2_bundle(Path(cls.template.name)/'bundle')
 @classmethod
 def tearDownClass(cls): cls.template.cleanup()
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.item=Path(self.t.name)/WORK_ID
  shutil.copytree(Path(self.template.name)/'bundle',self.item); self.path=self.item/'WORK-ITEM.json'
  # Most of this suite exercises v3-specific validation, not the CLI-wiring
  # gate itself: default the capability probe to True so migrate_bundle can
  # actually apply. The gate's own behaviour is tested explicitly below,
  # unpatched or with an explicit override.
  self._reader_patch=mock.patch.object(M,'production_reader_accepts_v3',return_value=True)
  self._reader_patch.start()
 def tearDown(self):
  self._reader_patch.stop()
  self.t.cleanup()
 def document(self): return json.loads(self.path.read_text(encoding='utf-8'))
 def rewrite(self,mutate,*,rehash=True):
  data=self.document(); mutate(data)
  if rehash: data['immutable_sha256']=M.immutable_sha256(data['immutable'])
  self.path.write_bytes(M.document_bytes(data)); return data
 def failure(self,call,*args,**kwargs):
  with self.assertRaises(M.WorkItemError) as caught: call(*args,**kwargs)
  return caught.exception

 # --- dual-read of v2 -------------------------------------------------
 def test_real_v2_bundle_reads_as_v2(self):
  data=self.document(); self.assertEqual(M.schema_of(data),M.SCHEMA_V2)
  self.assertEqual(M.validate_metadata(data,WORK_ID)['work_id'],WORK_ID)
 def test_tracked_repository_bundles_stay_readable(self):
  bundles=sorted((REPO/'.grill/work-items').glob('*/WORK-ITEM.json')) if (REPO/'.grill/work-items').is_dir() else []
  for bundle in bundles:
   with self.subTest(bundle=bundle.parent.name):
    self.assertEqual(M.schema_of(M.read_document(bundle)),M.SCHEMA_V2)
    self.assertEqual(M.validate_metadata(M.read_document(bundle),bundle.parent.name)['work_id'],bundle.parent.name)
 def test_unknown_schema_is_rejected(self):
  self.rewrite(lambda d:(d.__setitem__('schema','grill-work-item/v4'),d['immutable'].__setitem__('schema','grill-work-item/v4')))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'METADATA-SCHEMA')
 def test_divergent_schema_literals_are_rejected(self):
  self.rewrite(lambda d:d.__setitem__('schema',M.SCHEMA_V3))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'METADATA-SCHEMA')
 def test_v2_carrying_v3_fields_is_rejected(self):
  self.rewrite(lambda d:d['immutable'].__setitem__('worktree_key',M.worktree_key_for(WORK_ID)))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'METADATA-SCHEMA')
 def test_immutable_tampering_is_detected(self):
  self.rewrite(lambda d:d['immutable'].__setitem__('slug','other'),rehash=False)
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'IMMUTABLE-TAMPERED')
 def test_work_id_divergence(self):
  self.assertEqual(self.failure(M.validate_metadata,self.document(),'other').code,'WORK-ID-DIVERGENCE')
 def test_missing_v2_field_is_rejected(self):
  self.rewrite(lambda d:d['immutable'].pop('base_commit'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'METADATA-SCHEMA')

 # --- v3 required -- capability gate ------------------------------------
 def test_require_v3_message_does_not_recommend_migration_when_no_reader_accepts_v3(self):
  # Fase 1 / secao 23: while no production reader accepts v3, the payload
  # must not instruct the caller to run migrate_bundle -- doing so would
  # only earn V3_READERS_NOT_WIRED.
  with mock.patch.object(M,'production_reader_accepts_v3',return_value=False):
   error=self.failure(M.require_v3,self.document(),'fanout',WORK_ID)
  self.assertEqual((error.code,error.exit_code,error.verdict),('WORK_ITEM_V3_REQUIRED',2,'BLOCKED'))
  payload=error.payload()
  self.assertIs(payload['v3_readers_wired'],False)
  self.assertNotIn('call ',payload['migration_note'])  # never an instruction to run it -- it would just fail
  self.assertIn('refuses fail-closed',payload['migration_note'])
  self.assertNotIn('migration_command',payload)
  self.assertEqual(payload['migration_capability'],'grill_core.work_item_v3.migrate_bundle')
 def test_require_v3_message_points_to_the_real_migrate_v3_command_once_wired(self):
  # LD-010, peça B's half of the shared defect: migration_wired/migration_command
  # must come from a live, unmocked probe of grill_workspace.py's own CLI --
  # never a hardcoded constant. This tree already wires `migrate-v3` (peça E),
  # so the functional probe below must observe that for real.
  with mock.patch.object(M,'production_reader_accepts_v3',return_value=True):
   error=self.failure(M.require_v3,self.document(),'fanout',WORK_ID)
  payload=error.payload()
  self.assertIs(payload['v3_readers_wired'],True)
  self.assertIs(payload['migration_wired'],True)
  self.assertEqual(payload['migration_command'],'grill_workspace.py migrate-v3 ROOT --work-id ID [--apply]')
  self.assertIn('migrate-v3',payload['migration_note'])
  self.assertEqual((payload['schema'],payload['required_schema'],payload['operation']),(M.SCHEMA_V2,M.SCHEMA_V3,'fanout'))
 def test_require_v3_message_falls_back_to_the_capability_when_cli_probe_reports_unwired(self):
  # The middle rung: a reader accepts v3 but grill_workspace.py's own CLI
  # probe reports no migrate-v3 verb -- forced here since this tree's real
  # CLI *is* wired, so this branch cannot be reached unmocked today. Not an
  # attack on read_document/production_reader_accepts_v3 (LD-010's
  # anti-trap); it only exercises the message-construction branch that a
  # differently-wired tree would hit for real.
  with mock.patch.object(M,'production_reader_accepts_v3',return_value=True), \
       mock.patch.object(M,'production_cli_wires_migrate_v3',return_value=(False,None)):
   error=self.failure(M.require_v3,self.document(),'fanout',WORK_ID)
  payload=error.payload()
  self.assertIs(payload['migration_wired'],False)
  self.assertNotIn('migration_command',payload)
  self.assertIn('migrate_bundle',payload['migration_note'])
 def test_v3_required_error_never_advertises_a_dead_cli_command(self):
  # Regression guard, now with a live branch: builds a real v2 repo through
  # the live CLI, gets the WORK_ITEM_V3_REQUIRED payload unmocked, and -- if
  # migration_wired is true -- substitutes ROOT/ID into the exact command
  # the payload cites and actually runs it (preview, then --apply), both
  # required to exit 0. 'migration_wired' used to be a hardcoded False, so
  # this branch was dead; it must run for real now that grill_workspace.py
  # wires migrate-v3.
  with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
   root=Path(t); build_v2_repo(root)
   item=root/'.grill/work-items'/WORK_ID
   metadata=M.read_document(item/'WORK-ITEM.json')
   error=self.failure(M.require_v3,metadata,'fanout',WORK_ID)
   payload=error.payload()
   if payload.get('migration_wired'):
    template=payload['migration_command']
    self.assertEqual(template,'grill_workspace.py migrate-v3 ROOT --work-id ID [--apply]')
    tokens=template.replace('[--apply]','').split()
    tokens[tokens.index('ROOT')]=str(root)
    tokens[tokens.index('ID')]=WORK_ID
    preview=subprocess.run([sys.executable,str(WORKSPACE),*tokens[1:]],capture_output=True,text=True)
    self.assertEqual(preview.returncode,0,f"{template!r} (preview) -> {preview.returncode}: {preview.stdout}{preview.stderr}")
    applied=subprocess.run([sys.executable,str(WORKSPACE),*tokens[1:],'--apply'],capture_output=True,text=True)
    self.assertEqual(applied.returncode,0,f"{template!r} (--apply) -> {applied.returncode}: {applied.stdout}{applied.stderr}")
   else:
    self.assertNotIn('migration_command',payload)
 def test_require_v3_passes_after_migration(self):
  M.migrate_bundle(self.item,apply=True)
  self.assertEqual(M.require_v3(self.document(),'fanout',WORK_ID)['schema'],M.SCHEMA_V3)

 # --- v3 required -- CLI-wiring gate (real, unmocked) --------------------
 def test_apply_refuses_fail_closed_when_no_production_reader_accepts_v3(self):
  with mock.patch.object(M,'production_reader_accepts_v3',return_value=False):
   before=snapshot(self.item)
   error=self.failure(M.migrate_bundle,self.item,apply=True)
  self.assertEqual(error.code,'V3_READERS_NOT_WIRED')
  self.assertEqual(before,snapshot(self.item))
  self.assertEqual(self.document()['schema'],M.SCHEMA_V2)
 def test_apply_never_makes_the_live_cli_worse_off(self):
  # Fase 1 / secao 23, biggest gap from round 2: applying the only migration
  # this piece offers used to make grill_workspace.py status regress from a
  # working exit code (0) to METADATA-SCHEMA (2). Uses the REAL production
  # reader on disk, no mock: whatever its current wiring state is, the exit
  # code after attempting apply must never be worse than before.
  with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
   root=Path(t); build_v2_repo(root)
   before=cli_status(root)
   self.assertEqual(before,0,'fresh init should report status OK')
   item=root/'.grill/work-items'/WORK_ID
   try:
    M.migrate_bundle(item,apply=True)
   except M.WorkItemError as exc:
    self.assertEqual(exc.code,'V3_READERS_NOT_WIRED')
   after=cli_status(root)
   self.assertEqual(after,before,'grill_workspace.py status regressed after migrate_bundle(apply=True)')

 # --- preview-first ----------------------------------------------------
 def test_preview_writes_nothing(self):
  before=snapshot(self.item); payload=M.migrate_bundle(self.item)
  self.assertEqual((payload['verdict'],payload['from_schema'],payload['to_schema'],payload['writes']),('PREVIEW',M.SCHEMA_V2,M.SCHEMA_V3,[]))
  self.assertEqual(before,snapshot(self.item)); self.assertEqual(self.document()['schema'],M.SCHEMA_V2)
 def test_preview_ignores_the_wiring_gate(self):
  # Previews stay informational even before a production reader exists --
  # only apply=True needs proof (section 22/Core: previews are read-only).
  with mock.patch.object(M,'production_reader_accepts_v3',return_value=False):
   payload=M.migrate_bundle(self.item)
  self.assertEqual(payload['verdict'],'PREVIEW')
 def test_preview_reports_the_next_hash_without_applying_it(self):
  payload=M.migrate_bundle(self.item); current=self.document()['immutable_sha256']
  self.assertEqual(payload['immutable_sha256']['current'],current)
  self.assertNotEqual(payload['immutable_sha256']['next'],current)
  self.assertEqual(payload['adds'],sorted(['parent_work_id','source','worktree_key','orchestration']))
 def test_apply_is_explicit_and_atomic(self):
  payload=M.migrate_bundle(self.item,apply=True)
  self.assertEqual((payload['verdict'],payload['writes']),('APPLIED',['WORK-ITEM.json']))
  data=self.document(); self.assertEqual(data['schema'],M.SCHEMA_V3); self.assertEqual(data['immutable']['schema'],M.SCHEMA_V3)
  self.assertEqual(payload['document_sha256'],M.hash_bytes(self.path.read_bytes()))
  self.assertFalse([p for p in self.item.iterdir() if p.name.startswith('.WORK-ITEM.json')])
 def test_apply_is_idempotent(self):
  M.migrate_bundle(self.item,apply=True); first=self.path.read_bytes()
  payload=M.migrate_bundle(self.item,apply=True)
  self.assertEqual(payload['verdict'],'REUSED'); self.assertEqual(first,self.path.read_bytes())
  self.assertEqual(M.migrate_bundle(self.item)['verdict'],'REUSED')
 def test_migration_preserves_every_v2_field(self):
  before=self.document(); M.migrate_bundle(self.item,apply=True); after=self.document()
  for key,value in before['immutable'].items():
   if key!='schema': self.assertEqual(after['immutable'][key],value,key)
  for key,value in before.items():
   if key not in {'schema','immutable','immutable_sha256'}: self.assertEqual(after[key],value,key)
  self.assertEqual(after['capability'],{'name':'module-decomposition','version':'v1','schema':'v1'})
 def test_migration_only_touches_the_metadata_document(self):
  before={k:v for k,v in snapshot(self.item).items() if k!='WORK-ITEM.json'}
  M.migrate_bundle(self.item,apply=True)
  self.assertEqual(before,{k:v for k,v in snapshot(self.item).items() if k!='WORK-ITEM.json'})
  artifacts=self.document()['initial_artifacts']
  actual={p.relative_to(self.item).as_posix():M.hash_bytes(p.read_bytes()) for p in sorted(self.item.rglob('*')) if p.is_file() and p.name!='WORK-ITEM.json'}
  self.assertEqual(artifacts,actual)
 def test_migrated_bytes_match_the_v2_writer_format(self):
  M.migrate_bundle(self.item,apply=True); data=self.document()
  self.assertEqual(self.path.read_bytes(),(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 def test_hash_covers_the_new_logical_fields(self):
  M.migrate_bundle(self.item,apply=True,parent_work_id='feature-auth-a1b2',source=dict(SOURCE))
  data=self.document(); self.assertEqual(data['immutable_sha256'],M.hash_bytes(M.canonical(data['immutable'])))
  mutated=json.loads(json.dumps(data)); mutated['immutable']['parent_work_id']='feature-other-9999'
  self.assertNotEqual(M.immutable_sha256(mutated['immutable']),data['immutable_sha256'])
  self.assertEqual(self.failure(M.validate_metadata,mutated,WORK_ID).code,'IMMUTABLE-TAMPERED')
 def test_divergent_second_migration_is_blocked(self):
  M.migrate_bundle(self.item,apply=True,parent_work_id='feature-auth-a1b2',source=dict(SOURCE)); before=self.path.read_bytes()
  error=self.failure(M.migrate_bundle,self.item,apply=True,parent_work_id='feature-other-b2c3')
  self.assertEqual(error.code,'MIGRATION_DIVERGENCE'); self.assertEqual(before,self.path.read_bytes())
 def test_rejected_migration_leaves_the_document_untouched(self):
  before=snapshot(self.item)
  self.assertEqual(self.failure(M.migrate_bundle,self.item,apply=True,source=dict(SOURCE)).code,'INVALID_SOURCE')
  self.assertEqual(before,snapshot(self.item))

 # --- v3 extension rules ----------------------------------------------
 def test_child_migration_records_parent_and_source(self):
  M.migrate_bundle(self.item,apply=True,parent_work_id='feature-auth-a1b2',source=dict(SOURCE))
  immutable=M.validate_metadata(self.document(),WORK_ID)
  self.assertEqual(immutable['parent_work_id'],'feature-auth-a1b2'); self.assertEqual(immutable['source'],SOURCE)
  self.assertEqual(immutable['worktree_key'],'wt-'+WORK_ID)
  self.assertEqual(self.document()['orchestration'],{'schema':M.ORCHESTRATION_SCHEMA})
 def test_root_migration_has_null_parent_and_source(self):
  M.migrate_bundle(self.item,apply=True); immutable=M.validate_metadata(self.document(),WORK_ID)
  self.assertIsNone(immutable['parent_work_id']); self.assertIsNone(immutable['source'])
 def test_orchestration_block_is_pinned(self):
  M.migrate_bundle(self.item,apply=True)
  for mutation in ({'schema':'grill-orchestrator/v2'},{'schema':M.ORCHESTRATION_SCHEMA,'extra':1},'text'):
   with self.subTest(mutation=mutation):
    self.rewrite(lambda d,m=mutation:d.__setitem__('orchestration',m))
    self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'INVALID_ORCHESTRATION')
 def test_missing_orchestration_is_rejected(self):
  M.migrate_bundle(self.item,apply=True); self.rewrite(lambda d:d.pop('orchestration'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'INVALID_ORCHESTRATION')
 def test_missing_v3_field_is_rejected(self):
  M.migrate_bundle(self.item,apply=True); self.rewrite(lambda d:d['immutable'].pop('worktree_key'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'METADATA-SCHEMA')
 def test_self_parent_is_rejected(self):
  M.migrate_bundle(self.item,apply=True); self.rewrite(lambda d:d['immutable'].__setitem__('parent_work_id',WORK_ID))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'INVALID_PARENT')
 def test_invalid_parent_shape_is_rejected(self):
  M.migrate_bundle(self.item,apply=True); self.rewrite(lambda d:d['immutable'].__setitem__('parent_work_id','bad id'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'INVALID_PARENT')
 def test_source_matrix_fails_closed(self):
  cases={
   'unknown-kind':{**SOURCE,'kind':'invented'},
   'bad-relation':{**SOURCE,'relation':'maybe'},
   'bad-request-key':{**SOURCE,'request_key':'not-a-digest'},
   'traversal-ref':{**SOURCE,'source_ref':'../escape'},
   'absolute-ref':{**SOURCE,'source_ref':'/etc/passwd'},
   'empty-ref':{**SOURCE,'source_ref':'   '},
   'extra-field':{**SOURCE,'extra':1},
   'missing-field':{k:v for k,v in SOURCE.items() if k!='relation'},
   'not-a-dict':'backlog-request',
  }
  for name,source in cases.items():
   with self.subTest(case=name):
    error=self.failure(M.migrate_bundle,self.item,apply=True,parent_work_id='feature-auth-a1b2',source=source)
    self.assertEqual(error.code,'INVALID_SOURCE'); self.assertEqual(self.document()['schema'],M.SCHEMA_V2)
 def test_source_requires_a_parent(self):
  self.assertEqual(self.failure(M.migrate_bundle,self.item,apply=True,source=dict(SOURCE)).code,'INVALID_SOURCE')
 def test_request_key_accepts_the_prefixed_digest(self):
  M.migrate_bundle(self.item,apply=True,parent_work_id='feature-auth-a1b2',source={**SOURCE,'request_key':'sha256:'+'b'*64})
  self.assertEqual(M.validate_metadata(self.document(),WORK_ID)['source']['request_key'],'sha256:'+'b'*64)

 # --- no absolute worktree path in the versioned bundle ----------------
 def test_absolute_worktree_key_argument_is_refused(self):
  before=snapshot(self.item)
  error=self.failure(M.migrate_bundle,self.item,apply=True,worktree_key=str(self.item))
  self.assertEqual(error.code,'WORKTREE_PATH_FORBIDDEN'); self.assertEqual(before,snapshot(self.item))
 def test_windows_style_absolute_worktree_key_is_refused(self):
  self.assertEqual(self.failure(M.migrate_bundle,self.item,apply=True,worktree_key='C:\\repo\\wt').code,'WORKTREE_PATH_FORBIDDEN')
 def test_relative_path_shaped_worktree_key_is_refused(self):
  M.migrate_bundle(self.item,apply=True); self.rewrite(lambda d:d['immutable'].__setitem__('worktree_key','worktrees/wx'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_PATH_FORBIDDEN')
 def test_forbidden_worktree_path_key_is_refused(self):
  M.migrate_bundle(self.item,apply=True); self.rewrite(lambda d:d['immutable'].__setitem__('worktree_path','/repo-worktrees/wx'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_PATH_FORBIDDEN')
 def test_absolute_value_anywhere_in_immutable_is_refused(self):
  self.rewrite(lambda d:d['immutable']['workflow'].__setitem__('path','/repo/WORKFLOW.md'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_PATH_FORBIDDEN')
 def test_worktree_key_must_derive_from_work_id(self):
  M.migrate_bundle(self.item,apply=True); self.rewrite(lambda d:d['immutable'].__setitem__('worktree_key','wt-somethingelse'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_KEY_DIVERGENCE')
 def test_windows_drive_relative_worktree_key_argument_is_refused(self):
  # Single leading backslash: absolute-from-drive-root on Windows, but the
  # old regex only matched the doubled-backslash UNC form and let this slip.
  self.assertEqual(self.failure(M.migrate_bundle,self.item,apply=True,worktree_key='\\repo\\wt').code,'WORKTREE_PATH_FORBIDDEN')
 def test_windows_drive_relative_value_anywhere_in_immutable_is_refused(self):
  self.rewrite(lambda d:d['immutable']['workflow'].__setitem__('path','\\repo\\WORKFLOW.md'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_PATH_FORBIDDEN')
 def test_home_relative_value_anywhere_in_immutable_is_refused(self):
  self.rewrite(lambda d:d['immutable']['workflow'].__setitem__('path','~/repo/wt'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_PATH_FORBIDDEN')
 def test_file_uri_value_anywhere_in_immutable_is_refused(self):
  self.rewrite(lambda d:d['immutable']['workflow'].__setitem__('path','file:///repo/wt'))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_PATH_FORBIDDEN')
 def test_absolute_worktree_key_argument_is_refused_even_when_already_v3(self):
  # The re-migration branch used to skip shape validation entirely and only
  # compare against the value already on disk, so a malicious/garbage
  # worktree_key surfaced as MIGRATION_DIVERGENCE instead of the specific,
  # correct WORKTREE_PATH_FORBIDDEN.
  M.migrate_bundle(self.item,apply=True); before=self.path.read_bytes()
  error=self.failure(M.migrate_bundle,self.item,apply=True,worktree_key='/repo-worktrees/'+WORK_ID)
  self.assertEqual(error.code,'WORKTREE_PATH_FORBIDDEN'); self.assertNotEqual(error.code,'MIGRATION_DIVERGENCE')
  self.assertEqual(before,self.path.read_bytes())
 def test_traversal_worktree_key_argument_is_refused_even_when_already_v3(self):
  M.migrate_bundle(self.item,apply=True)
  error=self.failure(M.migrate_bundle,self.item,apply=True,worktree_key='../../etc')
  self.assertEqual(error.code,'WORKTREE_PATH_FORBIDDEN'); self.assertNotEqual(error.code,'MIGRATION_DIVERGENCE')
 def test_invalid_parent_argument_is_refused_even_when_already_v3(self):
  M.migrate_bundle(self.item,apply=True)
  error=self.failure(M.migrate_bundle,self.item,apply=True,parent_work_id='bad id')
  self.assertEqual(error.code,'INVALID_PARENT'); self.assertNotEqual(error.code,'MIGRATION_DIVERGENCE')

 # --- absolute paths outside `immutable` too (5.6, round-3 gap) --------
 def test_absolute_top_level_key_is_refused_before_migration(self):
  # Round-2 gap: the sweep only ever looked inside `immutable`. A top-level
  # `worktree_path` sibling of `immutable`/`schema` used to migrate through
  # untouched and be accepted afterwards.
  self.rewrite(lambda d:d.__setitem__('worktree_path','/repo-worktrees/'+WORK_ID))
  before=snapshot(self.item)
  error=self.failure(M.migrate_bundle,self.item,apply=True)
  self.assertEqual(error.code,'WORKTREE_PATH_FORBIDDEN')
  self.assertEqual(before,snapshot(self.item)); self.assertEqual(self.document()['schema'],M.SCHEMA_V2)
 def test_absolute_value_nested_outside_immutable_is_refused(self):
  self.rewrite(lambda d:d.__setitem__('local',{'worktree':{'path':'/home/alice/repo-worktrees/'+WORK_ID}}))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_PATH_FORBIDDEN')
 def test_absolute_top_level_key_is_refused_after_migration_too(self):
  M.migrate_bundle(self.item,apply=True)
  self.rewrite(lambda d:d.__setitem__('worktree_root','/srv/worktrees/'+WORK_ID))
  self.assertEqual(self.failure(M.validate_metadata,self.document(),WORK_ID).code,'WORKTREE_PATH_FORBIDDEN')

 # --- lock, compare-and-swap and file-mode hygiene (5.5 inv.11, 5.5.1) -
 def test_concurrent_divergent_migrations_never_both_apply(self):
  # Biggest gap from round 1: migrate_bundle(apply=True) had no lock, so two
  # racing writers could both observe "not yet migrated" and both return
  # APPLIED, with one parent_work_id silently lost. Real OS-level threads
  # racing on the same bundle directory, not a serialized simulation.
  trials=20
  for trial in range(trials):
   with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
    item=Path(t)/WORK_ID; shutil.copytree(Path(self.template.name)/'bundle',item)
    parents=('feature-auth-a1b2','feature-other-b2c3')
    barrier=threading.Barrier(2); results=[]; guard=threading.Lock()
    def worker(parent):
     barrier.wait()
     try:
      payload=M.migrate_bundle(item,apply=True,parent_work_id=parent)
      with guard: results.append((parent,'APPLIED',payload))
     except M.WorkItemError as exc:
      with guard: results.append((parent,exc.code,None))
    threads=[threading.Thread(target=worker,args=(parent,)) for parent in parents]
    for th in threads: th.start()
    for th in threads: th.join()
    with self.subTest(trial=trial):
     applied=[r for r in results if r[1]=='APPLIED']; errors=[r for r in results if r[1]!='APPLIED']
     self.assertEqual(len(results),2,results)
     self.assertEqual(len(applied),1,f"both threads applied: {results}")
     self.assertEqual(len(errors),1,results)
     self.assertIn(errors[0][1],{'MIGRATION_DIVERGENCE','STATE_DIVERGENCE','LOCK-CONTENTION'},results)
     final=json.loads((item/'WORK-ITEM.json').read_text(encoding='utf-8'))
     self.assertEqual(final['immutable']['parent_work_id'],applied[0][0],
                       f"on-disk parent does not match the sole APPLIED winner: {results}")
 def test_stale_lock_reclaim_never_lets_two_processes_hold_it_at_once(self):
  # Round-2/round-3 critic: with a .migrate.lock left behind by a provably
  # dead PID, two real processes racing to reclaim it both entered the
  # critical section in 1/25 trials (unlink+rmdir of a directory neither
  # process actually owned). Real subprocesses, a genuinely dead PID, and an
  # artificial in-critical-section delay so any overlap is deterministic
  # rather than timing luck.
  helper=subprocess.Popen([sys.executable,'-c','pass']); dead_pid=helper.pid; helper.wait()
  worker_path=Path(self.t.name)/'lock_race_worker.py'; worker_path.write_text(_LOCK_RACE_WORKER,encoding='utf-8')
  trials=5
  for trial in range(trials):
   with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
    item=Path(t)/WORK_ID; shutil.copytree(Path(self.template.name)/'bundle',item)
    lock=M.lock_path(item,WORK_ID); lock.mkdir(parents=True)
    (lock/'owner.json').write_text(json.dumps({'pid':dead_pid,'host':socket.gethostname()}),encoding='utf-8')
    go=Path(t)/'go'; records=[Path(t)/f'record-{i}.jsonl' for i in range(2)]
    for record in records: record.touch()
    procs=[
     subprocess.Popen([sys.executable,str(worker_path),str(SCRIPTS),str(item),parent,str(records[i]),str(go),'0.2'],
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
     for i,parent in enumerate(('feature-auth-a1b2','feature-other-b2c3'))
    ]
    time.sleep(0.2); go.touch()
    outputs=[proc.communicate(timeout=15) for proc in procs]
    with self.subTest(trial=trial):
     for stdout,stderr in outputs: self.assertTrue(stdout.strip(),stderr)
     intervals=[]
     for record in records:
      events=[json.loads(line) for line in record.read_text(encoding='utf-8').splitlines() if line.strip()]
      enters=sorted(e['t'] for e in events if e['event']=='enter')
      exits=sorted(e['t'] for e in events if e['event']=='exit')
      self.assertEqual(len(enters),1,events); self.assertEqual(len(exits),1,events)
      intervals.append((enters[0],exits[0]))
     intervals.sort()
     (a_start,a_end),(b_start,b_end)=intervals
     self.assertGreaterEqual(b_start,a_end,f"critical sections overlapped: {intervals}")
 def test_lock_lives_outside_the_versioned_bundle_in_a_real_repository(self):
  # 5.2 + 5.5 inv.11, round-2 gap: the lock used to be created inside the
  # versioned bundle (.grill/work-items/<id>/.migrate.lock), so `git status`
  # saw it and bundle_fingerprint() would have hashed it. It must live at
  # <git-common-dir>/grill/locks/, entirely outside the working tree.
  with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
   root=Path(t); build_v2_repo(root)
   item=root/'.grill/work-items'/WORK_ID
   def status(): return subprocess.run(['git','-C',str(root),'status','--porcelain'],capture_output=True,text=True,check=True).stdout
   baseline=status()  # .grill/ and .specify/ are untracked-but-expected noise from init, not from the lock
   common=subprocess.run(['git','-C',str(root),'rev-parse','--git-common-dir'],capture_output=True,text=True,check=True).stdout.strip()
   common_dir=(root/common).resolve()
   expected_lock_root=common_dir/'grill'/'locks'
   original_enter=M._BundleLock.__enter__; seen={}
   def paused_enter(self):
    result=original_enter(self)
    seen['status']=status()
    seen['lock_dir']=self._lock.parent
    return result
   with mock.patch.object(M._BundleLock,'__enter__',paused_enter):
    payload=M.migrate_bundle(item,apply=True)
   self.assertEqual(payload['verdict'],'APPLIED')
   self.assertEqual(seen['status'],baseline,f"git status changed while the lock was held: baseline={baseline!r} during={seen['status']!r}")
   self.assertEqual(seen['lock_dir'],expected_lock_root)
   self.assertFalse(any('lock' in p.name.lower() for p in item.rglob('*')),'lock leaked into the versioned bundle')
 def test_stale_document_between_decision_and_write_is_refused(self):
  # Attacks the whole-document CAS with a REAL external process -- not a
  # mock.patch of read_document (the exact function under attack), which is
  # the forbidden technique this test used to use and which the critic
  # flagged: forging the digest on the second call proves nothing about
  # whether a genuine concurrent writer is ever detected.
  #
  # The document is inflated to ~4MB (LD-010 evidence: reproduced 5/5
  # against the old, narrower CAS at this size) so the real, unmocked
  # window between migrate_bundle's two on-disk reads is wide enough for a
  # genuinely independent OS process -- launched ahead of time, polling
  # only for the lock directory's existence, never importing this module --
  # to land a real os.replace() of its own inside it.
  #
  # Against the pre-fix code (CAS anchored on metadata['immutable_sha256']
  # alone) this always silently discarded the external write: APPLIED, no
  # STATE_DIVERGENCE, external 'scope' reverted. The only acceptable
  # outcomes now: the write is caught and refused (STATE_DIVERGENCE, disk
  # keeps the external bytes), or it is preserved through a successful
  # APPLIED -- never silently reverted.
  worker_path=Path(self.t.name)/'external_writer.py'
  worker_path.write_text(_EXTERNAL_WRITER,encoding='utf-8')
  padding='x'*(4*1024*1024)
  trials=5; detected=0
  for trial in range(trials):
   with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
    item=Path(t)/WORK_ID; shutil.copytree(Path(self.template.name)/'bundle',item)
    path=item/'WORK-ITEM.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    data['scope']={'paths':[],'padding':padding}
    path.write_bytes(M.document_bytes(data))
    lock_dir=M.lock_path(item,WORK_ID)
    proc=subprocess.Popen([sys.executable,str(worker_path),str(path),str(lock_dir)],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
     result=M.migrate_bundle(item,apply=True); outcome=('APPLIED',result)
    except M.WorkItemError as exc:
     outcome=(exc.code,None)
    stdout,stderr=proc.communicate(timeout=15)
    with self.subTest(trial=trial):
     self.assertEqual(stdout.strip(),'written',f"external writer failed: {stderr}")
     final=json.loads(path.read_text(encoding='utf-8'))
     if outcome[0]=='STATE_DIVERGENCE':
      detected+=1
      self.assertEqual(final.get('scope'),{'EXTERNAL_WRITER':'this change must not vanish'},
                        'a refused migration must leave the real external write intact')
     elif outcome[0]=='APPLIED':
      self.assertEqual(final.get('scope'),{'EXTERNAL_WRITER':'this change must not vanish'},
                        'APPLIED must never silently revert a real concurrent external write')
     else:
      self.fail(f'unexpected migrate_bundle outcome: {outcome}')
  self.assertGreater(detected,0,'the CAS never once caught the real external writer across all trials')
 def test_lock_directory_is_never_left_behind(self):
  M.migrate_bundle(self.item,apply=True)
  self.assertFalse(M.lock_path(self.item,WORK_ID).exists())
 def test_lock_directory_is_cleaned_up_after_a_rejected_migration(self):
  self.assertEqual(self.failure(M.migrate_bundle,self.item,apply=True,source=dict(SOURCE)).code,'INVALID_SOURCE')
  self.assertFalse(M.lock_path(self.item,WORK_ID).exists())
 @unittest.skipUnless(os.name=='posix','file mode bits are POSIX-only')
 def test_migration_preserves_the_original_file_mode(self):
  os.chmod(self.path,0o640)
  M.migrate_bundle(self.item,apply=True)
  self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode),0o640)
 @unittest.skipUnless(os.name=='posix' and os.rename in os.supports_dir_fd,'descriptor-relative replace unavailable')
 def test_descriptor_replace_interruption_preserves_the_prior_document(self):
  """A failed final rename may not damage either bytes or mode.

  The candidate models a rebind (only workflow identity and its dependent
  immutable hash change), while this focused test stays below CLI policy so
  the fault is injected into the actual atomic primitive.
  """
  os.chmod(self.path,0o640); before=self.path.read_bytes()
  candidate=json.loads(before)
  candidate['immutable']['workflow']['sha256']='f'*64
  candidate['immutable_sha256']=M.immutable_sha256(candidate['immutable'])
  directory_fd=os.open(self.item,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
  try:
   supported=set(M.os.supports_dir_fd)
   with mock.patch.object(M.os,'rename',side_effect=OSError('simulated interrupted rename')) as interrupted_rename:
    # Preserve the platform capability probe while replacing only the call
    # outcome; otherwise the MagicMock itself looks like an unsupported API.
    with mock.patch.object(M.os,'supports_dir_fd',supported|{interrupted_rename}):
     with self.assertRaises(OSError):
      M._atomic_replace_at(directory_fd,'WORK-ITEM.json',M.document_bytes(candidate),mode=0o640)
  finally:
   os.close(directory_fd)
  self.assertEqual(self.path.read_bytes(),before)
  self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode),0o640)
  self.assertFalse(any(p.name.endswith('.tmp') for p in self.item.iterdir()))
 @unittest.skipUnless(os.name=='posix' and hasattr(os,'fchmod') and os.rename in os.supports_dir_fd,
                      'descriptor-relative mode restoration unavailable')
 def test_descriptor_replace_fchmod_failure_is_named_and_writes_nothing(self):
  """Mode restoration is part of the commit, never a best-effort hint."""
  os.chmod(self.path,0o640); before=self.path.read_bytes()
  candidate=json.loads(before)
  candidate['immutable']['workflow']['sha256']='e'*64
  candidate['immutable_sha256']=M.immutable_sha256(candidate['immutable'])
  directory_fd=os.open(self.item,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
  try:
   with mock.patch.object(M.os,'fchmod',side_effect=OSError('simulated fchmod failure')), \
        mock.patch.object(M.os,'fdopen',wraps=M.os.fdopen) as opened:
    error=self.failure(M._atomic_replace_at,directory_fd,'WORK-ITEM.json',M.document_bytes(candidate),mode=0o640)
    opened.assert_not_called()
  finally:
   os.close(directory_fd)
  self.assertEqual(error.code,'MODE-PRESERVATION-FAILED')
  self.assertEqual(self.path.read_bytes(),before)
  self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode),0o640)
  self.assertFalse(any(p.name.endswith('.tmp') for p in self.item.iterdir()))

 # --- structured errors, never raw exceptions (round-3 gap) ------------
 @unittest.skipUnless(os.name=='posix','permission bits are POSIX-only')
 def test_permission_denied_bundle_directory_produces_a_structured_error(self):
  os.chmod(self.item,0o500)
  try:
   error=self.failure(M.migrate_bundle,self.item,apply=True)
   self.assertEqual(error.code,'FILESYSTEM')
   self.assertEqual(error.message,'filesystem-error:PermissionError')
   self.assertEqual(error.details.get('work_id'),WORK_ID)
  finally:
   os.chmod(self.item,0o700)
  self.assertEqual(self.document()['schema'],M.SCHEMA_V2)

 # --- qualified ids (5.1) ----------------------------------------------
 def test_qualified_ids_round_trip(self):
  project='sha256:'+'c'*64
  for local in ('ADR-0001','DQ-0002','BL-0003','FASE-001','R-0004','wt-feature-auth-a1b2'):
   with self.subTest(local=local):
    value=M.qualified_id(project,'feature-auth-a1b2',local)
    self.assertEqual(value,f'{project}/feature-auth-a1b2/{local}')
    self.assertEqual(M.parse_qualified_id(value),(project,'feature-auth-a1b2',local))
 def test_local_ids_do_not_collide_between_projects(self):
  first=M.qualified_id('project-one','feature-auth-a1b2','ADR-0001'); second=M.qualified_id('project-two','feature-auth-a1b2','ADR-0001')
  self.assertNotEqual(first,second)
 def test_qualified_id_matrix_fails_closed(self):
  for value in ('ADR-0001','a/b','a/b/c/d','/a/b/c','a//c','a/b/..','a/b/c/','',' a/b/c'):
   with self.subTest(value=value):
    self.assertEqual(self.failure(M.parse_qualified_id,value).code,'INVALID_QUALIFIED_ID')
  self.assertEqual(self.failure(M.qualified_id,'p','bad id','ADR-0001').code,'INVALID_QUALIFIED_ID')
  self.assertEqual(self.failure(M.qualified_id,'p','feature-auth-a1b2','bad id').code,'INVALID_QUALIFIED_ID')

 # --- fail-closed reads -------------------------------------------------
 def test_invalid_utf8_is_no_go(self):
  self.path.write_bytes(b'{"schema": "\xff\xfe"}')
  error=self.failure(M.read_document,self.path); self.assertEqual((error.code,error.exit_code,error.verdict),('INVALID-UTF8',1,'NO-GO'))
 def test_invalid_json_is_blocked(self):
  self.path.write_bytes(b'{not json')
  self.assertEqual(self.failure(M.read_document,self.path).code,'UNEXPECTED-INPUT')
 def test_missing_document_is_no_go(self):
  self.path.unlink(); self.assertEqual(self.failure(M.migrate_bundle,self.item).code,'WORK-ITEM-MISSING')
 def test_directory_in_place_of_document_is_blocked(self):
  self.path.unlink(); self.path.mkdir()
  self.assertIn(self.failure(M.read_document,self.path).code,{'WORK-ITEM-NOT-REGULAR','UNSAFE-FILE'})
 @unittest.skipUnless(SYMLINKS,'symlinks unsupported on this platform')
 def test_symlinked_document_is_refused_without_reading_it(self):
  outside=Path(self.t.name)/'outside.json'; outside.write_text('{"secret": true}')
  self.path.unlink(); self.path.symlink_to(outside)
  error=self.failure(M.migrate_bundle,self.item,apply=True)
  self.assertEqual(error.code,'WORK-ITEM-SYMLINK'); self.assertEqual(outside.read_text(),'{"secret": true}')
 def test_scalar_document_is_blocked(self):
  self.path.write_bytes(b'[]'); self.assertEqual(self.failure(M.validate_metadata,M.read_document(self.path)).code,'METADATA-SCHEMA')

 # --- module hygiene -----------------------------------------------------
 def test_module_is_stdlib_only_and_offline(self):
  tree=__import__('ast').parse((SCRIPTS/'grill_core/work_item_v3.py').read_text(encoding='utf-8'))
  imported=set()
  for node in __import__('ast').walk(tree):
   if isinstance(node,__import__('ast').Import): imported.update(alias.name.split('.')[0] for alias in node.names)
   elif isinstance(node,__import__('ast').ImportFrom) and node.level==0 and node.module: imported.add(node.module.split('.')[0])
  self.assertEqual(imported-{'__future__','argparse','errno','hashlib','importlib','json','os','re','shutil','socket','stat','subprocess','sys','tempfile','time','dataclasses','pathlib','typing'},set())
 def test_module_never_statically_imports_grill_workspace(self):
  # The dynamic capability probe (production_reader_accepts_v3) is the only
  # sanctioned way this module ever touches grill_workspace.py.
  text=(SCRIPTS/'grill_core/work_item_v3.py').read_text(encoding='utf-8')
  self.assertNotIn('import grill_workspace',text)
 def test_helpers_are_pure_on_the_document(self):
  data=self.document(); frozen=json.dumps(data,sort_keys=True)
  M.upgrade_metadata(data,parent_work_id='feature-auth-a1b2',source=dict(SOURCE))
  self.assertEqual(frozen,json.dumps(data,sort_keys=True))

class RebindWorkflowContract(unittest.TestCase):
 """Public contract for an explicit legacy-V3 workflow authority rebind."""
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.root=Path(self.t.name)
  build_rebind_repo(self.root)
  self.item=self.root/'.grill/work-items'/WORK_ID; self.path=self.item/'WORK-ITEM.json'
  self.current_workflow_sha256=M.hash_bytes((self.root/'WORKFLOW.md').read_bytes())
  self.assertEqual(self.document()['schema'],M.SCHEMA_V3)
  self.assertNotEqual(self.document()['immutable']['workflow']['sha256'],self.current_workflow_sha256)
 def tearDown(self): self.t.cleanup()
 def document(self): return json.loads(self.path.read_text(encoding='utf-8'))
 def invoke(self,*flags): return invoke_workspace('migrate-v3',self.root,'--work-id',WORK_ID,'--rebind-workflow',*flags)
 def in_process(self,*flags):
  CLI._GRILL_CORE['work_item_v3']=M
  return invoke_workspace_in_process('migrate-v3',self.root,'--work-id',WORK_ID,'--rebind-workflow',*flags)
 def without_document(self,value):
  result=dict(value); result.pop('WORK-ITEM.json',None); return result
 def without_root_document(self,value):
  result=dict(value); result.pop(f'.grill/work-items/{WORK_ID}/WORK-ITEM.json',None); return result

 def test_rebind_preview_reports_both_digests_and_writes_nothing(self):
  before=snapshot(self.root); prior=self.document()['immutable']['workflow']['sha256']
  process,payload=self.invoke()
  self.assertEqual(process.stderr,'')
  self.assertEqual((process.returncode,payload.get('verdict'),payload.get('operation')),
                   (0,'PREVIEW','rebind-workflow'),payload)
  self.assertEqual(payload.get('from_workflow_sha256'),prior)
  self.assertEqual(payload.get('to_workflow_sha256'),self.current_workflow_sha256)
  self.assertEqual(snapshot(self.root),before)
  self.assertFalse((self.root/'.grill/locks'/f'{WORK_ID}.lock').exists())

 def test_rebind_apply_reloads_workflow_inside_commit_window_and_never_binds_stale_a(self):
  workflow=self.root/'WORKFLOW.md'
  workflow_a=workflow.read_bytes(); workflow_b=workflow_a+b'\n'
  digest_a=M.hash_bytes(workflow_a); digest_b=M.hash_bytes(workflow_b)
  self.assertNotEqual(digest_a,digest_b)
  self.assertEqual(WV3.execution_gate(workflow_a.decode('utf-8')).status,'OK')
  self.assertEqual(WV3.execution_gate(workflow_b.decode('utf-8')).status,'OK')

  workflow_v3=CLI.grill_core_module('workflow_v3')
  original_load=workflow_v3.load_workflow; observed={'loads':0}
  def publish_b_after_first_load(root):
   loaded=original_load(root); observed['loads']+=1
   if observed['loads']==1:
    self.assertEqual(loaded[1],workflow_a)
    workflow.write_bytes(workflow_b)
   return loaded

  CLI._GRILL_CORE['workflow_v3']=workflow_v3
  with mock.patch.object(workflow_v3,'load_workflow',side_effect=publish_b_after_first_load):
   returncode,payload,stderr=self.in_process('--apply')
  self.assertEqual(stderr,'')
  self.assertEqual(observed['loads'],2)
  self.assertEqual((returncode,payload.get('verdict'),payload.get('operation')),
                   (0,'APPLIED','rebind-workflow'),payload)
  self.assertEqual(payload.get('to_workflow_sha256'),digest_b)
  self.assertNotEqual(payload.get('to_workflow_sha256'),digest_a)
  self.assertEqual(self.document()['immutable']['workflow']['sha256'],digest_b)
  self.assertFalse((self.root/'.grill/locks'/f'{WORK_ID}.lock').exists())

 def test_rebind_v2_workflow_is_blocked_in_preview_and_apply_without_any_write(self):
  (self.root/'WORKFLOW.md').write_bytes(TEMPLATE.read_bytes())
  before=snapshot(self.root)
  for flags in ((),('--apply',)):
   with self.subTest(flags=flags):
    process,payload=self.invoke(*flags)
    self.assertEqual(process.stderr,'')
    self.assertEqual((process.returncode,payload.get('verdict'),payload.get('code')),
                     (2,'BLOCKED','WORKFLOW-INCOMPATIBLE'),payload)
    self.assertEqual(snapshot(self.root),before)
    self.assertFalse((self.root/'.grill/locks'/f'{WORK_ID}.lock').exists())

 def test_rebind_forged_v3_registry_pin_is_blocked_without_any_write(self):
  workflow=self.root/'WORKFLOW.md'; live_pin=WV3.registry_state()['sha256'].encode('ascii')
  forged=workflow.read_bytes().replace(live_pin,b'sha256:'+b'0'*64)
  self.assertNotEqual(forged,workflow.read_bytes())
  workflow.write_bytes(forged); before=snapshot(self.root)
  process,payload=self.invoke('--apply')
  self.assertEqual(process.stderr,'')
  self.assertEqual((process.returncode,payload.get('verdict'),payload.get('code')),
                   (2,'BLOCKED','REGISTRY-PIN-DIVERGENT'),payload)
  self.assertEqual(snapshot(self.root),before)
  self.assertFalse((self.root/'.grill/locks'/f'{WORK_ID}.lock').exists())

 def test_rebind_safe_descriptor_unavailable_is_named_and_root_unchanged(self):
  before=snapshot(self.root)
  def unavailable(*_args,**_kwargs):
   raise CLI.CliFailure(CLI.EXIT_BLOCKED,'BLOCKED','SAFE-DIRECTORY-FD-UNAVAILABLE',WORK_ID)
  with mock.patch.object(CLI,'open_development_item_fd',side_effect=unavailable):
   for flags in ((),('--apply',)):
    with self.subTest(flags=flags):
     returncode,payload,stderr=self.in_process(*flags)
     self.assertEqual(stderr,'')
     self.assertEqual((returncode,payload.get('verdict'),payload.get('code')),
                      (2,'BLOCKED','SAFE-DIRECTORY-FD-UNAVAILABLE'),payload)
     self.assertEqual(snapshot(self.root),before)
     self.assertFalse((self.root/'.grill/locks'/f'{WORK_ID}.lock').exists())

 @unittest.skipUnless(os.name=='posix','file mode bits are POSIX-only')
 def test_rebind_apply_changes_only_binding_and_hash_and_preserves_extension_and_mode(self):
  before=self.document()
  before['consumer_extension']={'owner':'external','nested':{'keep':[1,2,3]}}
  self.path.write_bytes(M.document_bytes(before)); os.chmod(self.path,0o640)
  before=self.document(); before_root=snapshot(self.root)
  process,payload=self.invoke('--apply')
  self.assertEqual(process.stderr,'')
  self.assertEqual((process.returncode,payload.get('verdict'),payload.get('operation')),
                   (0,'APPLIED','rebind-workflow'),payload)
  after=self.document(); M.validate_metadata(after,WORK_ID)
  expected_immutable=json.loads(json.dumps(before['immutable']))
  expected_immutable['workflow']['sha256']=self.current_workflow_sha256
  self.assertEqual(after['immutable'],expected_immutable)
  self.assertEqual(after['immutable_sha256'],M.immutable_sha256(expected_immutable))
  for key,value in before.items():
   if key not in {'immutable','immutable_sha256'}:
    self.assertEqual(after.get(key),value,key)
  self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode),0o640)
  self.assertEqual(self.without_root_document(snapshot(self.root)),self.without_root_document(before_root))

 def test_rebind_apply_is_idempotent_and_second_apply_is_byte_identical(self):
  first_process,first=self.invoke('--apply')
  self.assertEqual((first_process.returncode,first.get('verdict')),(0,'APPLIED'),first)
  after_first=snapshot(self.root)
  second_process,second=self.invoke('--apply')
  self.assertEqual((second_process.returncode,second.get('verdict'),second.get('operation')),
                   (0,'REUSED','rebind-workflow'),second)
  self.assertEqual(snapshot(self.root),after_first)

 def test_rebind_stale_whole_document_cas_is_blocked_without_lost_update(self):
  """Mutate an unrelated field immediately after the decision read."""
  before_root=snapshot(self.root)
  original=M.read_document_with_digest_at; observed={'reads':0}
  def racing_read(directory_fd,name='WORK-ITEM.json'):
   document,digest=original(directory_fd,name); observed['reads']+=1
   if observed['reads']==1:
    external=json.loads(json.dumps(document))
    external['consumer_extension']={'writer':'outside-the-lock-domain'}
    observed['external_bytes']=M.document_bytes(external)
    self.path.write_bytes(observed['external_bytes'])
   return document,digest
  with mock.patch.object(M,'read_document_with_digest_at',side_effect=racing_read):
   returncode,payload,stderr=self.in_process('--apply')
  self.assertEqual(stderr,'')
  self.assertGreaterEqual(observed['reads'],2)
  self.assertEqual((returncode,payload.get('verdict'),payload.get('code')),
                   (2,'BLOCKED','STATE-DIVERGENCE'),payload)
  self.assertEqual(self.path.read_bytes(),observed['external_bytes'])
  self.assertEqual(self.without_root_document(snapshot(self.root)),self.without_root_document(before_root))
  self.assertFalse((self.root/'.grill/locks'/f'{WORK_ID}.lock').exists())

 def test_rebind_interrupted_final_rename_preserves_prior_document(self):
  before_root=snapshot(self.root); before=self.path.read_bytes(); before_mode=stat.S_IMODE(os.stat(self.path).st_mode)
  supported=set(M.os.supports_dir_fd)
  with mock.patch.object(M.os,'rename',side_effect=OSError('simulated interrupted rename')) as interrupted_rename:
   with mock.patch.object(M.os,'supports_dir_fd',supported|{interrupted_rename}):
    returncode,payload,stderr=self.in_process('--apply')
  self.assertEqual(stderr,'')
  self.assertEqual((returncode,payload.get('verdict'),payload.get('code')),
                   (2,'BLOCKED','FILESYSTEM'),payload)
  self.assertEqual(self.path.read_bytes(),before)
  self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode),before_mode)
  self.assertEqual(snapshot(self.root),before_root)
  self.assertFalse(any(p.name.endswith('.tmp') for p in self.item.iterdir()))
  self.assertFalse((self.root/'.grill/locks'/f'{WORK_ID}.lock').exists())

 @unittest.skipUnless(os.name=='posix' and hasattr(os,'fchmod'),'fchmod unavailable')
 def test_rebind_fchmod_failure_is_named_and_preserves_prior_document(self):
  os.chmod(self.path,0o640); before_root=snapshot(self.root); before=self.path.read_bytes()
  with mock.patch.object(M.os,'fchmod',side_effect=OSError('simulated fchmod failure')):
   returncode,payload,stderr=self.in_process('--apply')
  self.assertEqual(stderr,'')
  self.assertEqual((returncode,payload.get('verdict'),payload.get('code')),
                   (2,'BLOCKED','MODE-PRESERVATION-FAILED'),payload)
  self.assertEqual(self.path.read_bytes(),before)
  self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode),0o640)
  self.assertEqual(snapshot(self.root),before_root)
  self.assertFalse(any(p.name.endswith('.tmp') for p in self.item.iterdir()))
  self.assertFalse((self.root/'.grill/locks'/f'{WORK_ID}.lock').exists())

if __name__=='__main__': unittest.main()
