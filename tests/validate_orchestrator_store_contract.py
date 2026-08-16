#!/usr/bin/env python3
"""Contract matrix for the shared orchestrator store at <git-common-dir>/grill.

Plan clauses under test: 5.2, 5.4, 5.5 invariants 10-14, 5.5.1 (seven bootstrap
steps) and 22/Core (lock, CAS, revision, hash, fsync, rename, re-read, UTF-8,
symlink/traversal, event journal, read-only status/preview, exit codes).
"""
import concurrent.futures, hashlib, json, multiprocessing, os, subprocess, sys, tempfile, threading, unittest
from pathlib import Path
from unittest import mock
REPO=Path(__file__).resolve().parents[1]
SCRIPTS=REPO/'plugin/skills/grill-with-docs/scripts'
sys.path.insert(0,str(SCRIPTS))
from grill_core import store
POSIX=os.name=='posix'
LINUX=sys.platform.startswith('linux')
CLOCK=lambda: '2026-01-01T00:00:00Z'
def WORK_ITEM(lifecycle='ACTIVE',slug='auth',type_='feature',worktree=None,monitoring=None):
 return {'type':type_,'slug':slug,'lifecycle':lifecycle,'worktree':worktree,'monitoring':monitoring}
def GAUNTLET_RECEIPT(input_sha256='1'*64,name='gauntlet-run-alpha-1',base_commit='e'*40,wave_id='wave-0001'):
 return {
  'category':'runtime','name':name,
  'work_id':'gauntlet-work','run_id':'run-alpha-1','wave_id':wave_id,
  'base_commit':base_commit,'input_sha256':input_sha256,'output_sha256':None,
 }
def GAUNTLET_EVENT(receipt=None):
 receipt=GAUNTLET_RECEIPT() if receipt is None else receipt
 return {
  'event':'gauntlet.run.admitted','work_id':'gauntlet-work','run_id':'run-alpha-1',
  'wave_id':receipt['wave_id'],'base_commit':receipt['base_commit'],'input_sha256':receipt['input_sha256'],
  'output_sha256':None,'receipt_sha256':store.jcs_sha256(receipt),
 }
# FASE-003 (B5): wave-0001's default node_ids -- a real, required Store
# field as of the B5 fix (reverting the journal-scan substitution).  Kept as
# a fixed constant so every call to GAUNTLET_RUN(waves=None) across this
# file produces byte-identical wave-0001 records, satisfying the Store's
# node_ids-is-immutable-once-set rule across successive transitions.
DEFAULT_WAVE_NODE_IDS = ['n1']
def GAUNTLET_RUN(state='ADMITTED',recovery_count=0,workers=None,waves=None):
 return {
  'admission':{
   'activation_sha256':'a'*64,'work_item_sha256':'b'*64,
   'workflow_sha256':'c'*64,'config_sha256':'d'*64,'base_commit':'e'*40,
  },
  'state':state,'recovery_count':recovery_count,
  'waves':{'wave-0001':{'state':'DECLARED','node_ids':list(DEFAULT_WAVE_NODE_IDS)}} if waves is None else waves,
  'workers':{} if workers is None else workers,
  'last_transition':{'event_sequence':1,'receipt_sha256':GAUNTLET_EVENT()['receipt_sha256']},
 }
def GAUNTLET_BLOCK(runs=None):
 return {'schema':'grill-gauntlet-runs/v1','runs':{'run-alpha-1':GAUNTLET_RUN()} if runs is None else runs}
# FASE-003 (T001): worker records now require node_id/remediates too -- these
# two helpers build the six-key worker shape and its lease without repeating
# the boilerplate at every call site.
def GAUNTLET_WORKER(worker_id='worker-a',state='DECLARED',lease=None,grant=None,workspace=None,node_id=None,remediates=None):
 return {'state':state,'lease':lease,'grant':grant,'workspace':workspace,'node_id':worker_id if node_id is None else node_id,'remediates':remediates}
def GAUNTLET_LEASE(lease_id='lease-a',fencing_token=1,state='ACTIVE',recovery_count=0):
 return {'lease_id':lease_id,'fencing_token':fencing_token,'acquired_at':CLOCK(),'expires_at':CLOCK(),'state':state,'recovery_count':recovery_count}
# FASE-004 (T001): the run's two new optional write-once fields and the wave's
# own optional conflict record.  The bundle is stored verbatim by the Store;
# its own six-key validation lives in attestation.py, at the CLI boundary.
def HUMAN_AUTHORIZATION(scope='run-alpha-1',decision='APPROVED',authorized_by='operator@example.invalid'):
 return {'schema':'human-authorization/v1','scope':scope,'decision':decision,'authorized_by':authorized_by,'receipt_ref':'receipts/abandon.json','content_sha256':'f'*64}
def LAST_CONFLICT(node_ids=None,reason='content-conflict',execution_branch_head='1'*40,worker_heads=None):
 return {
  'node_ids':['n1'] if node_ids is None else node_ids,'reason':reason,
  'execution_branch_head':execution_branch_head,
  'worker_heads':{'n1':'2'*40} if worker_heads is None else worker_heads,
 }
def _mp_append_events(root,count,tag):
 sys.path.insert(0,str(SCRIPTS))
 from grill_core import store as _store
 return [_store.append_event(root,{'event':f'{tag}-{i}'})['sequence'] for i in range(count)]

def git(root,*a): subprocess.run(['git','-C',str(root),*map(str,a)],check=True,capture_output=True)
def make_repo(path):
 subprocess.run(['git','init','-q','-b','main',str(path)],check=True,capture_output=True)
 git(path,'config','user.email','t@e'); git(path,'config','user.name','t')
 (path/'seed').write_text('seed'); git(path,'add','.'); git(path,'commit','-qm','init'); return path
def tree(root):
 root=Path(root); out={}
 if not root.exists(): return out
 for p in sorted(root.rglob('*')):
  key=str(p.relative_to(root))
  if p.is_symlink(): out[key]='@link'
  elif p.is_dir(): out[key]=('@dir',p.stat().st_mtime_ns)
  else: out[key]=(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns)
 return out

class Canonicalization(unittest.TestCase):
 def test_rfc8785_member_order_is_utf16_code_unit(self):
  document={'\u20ac':'E','\r':'CR','\ufb33':'D','1':'One','\u0080':'C1','\u00f6':'o','\U0001f600':'S','\U0001d11e':'G'}
  self.assertEqual(store.jcs(document).decode(),'{"\\r":"CR","1":"One","\u0080":"C1","\u00f6":"o","\u20ac":"E","\U0001d11e":"G","\U0001f600":"S","\ufb33":"D"}')
 def test_escapes_only_json_mandated_code_points(self):
  self.assertEqual(store.jcs({'k':'\b\t\n\f\r"\\\u0000\u001f'}).decode(),'{"k":"\\b\\t\\n\\f\\r\\"\\\\\\u0000\\u001f"}')
 def test_numbers_follow_ecmascript_tostring(self):
  self.assertEqual(store.jcs([0,-1,10**20,1.0,-0.0,5.5,1e21,1e-7]).decode(),'[0,-1,100000000000000000000,1,0,5.5,1e+21,1e-7]')
 def test_non_finite_number_fails_closed(self):
  with self.assertRaises(store.StoreError) as ctx: store.jcs({'k':float('inf')})
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
 def test_unsupported_type_fails_closed(self):
  with self.assertRaises(store.StoreError): store.jcs({'k':{1,2}})
  with self.assertRaises(store.StoreError): store.jcs({1:'k'})
 def test_insertion_order_and_whitespace_are_irrelevant(self):
  a=store.jcs_sha256({'b':1,'a':{'d':2,'c':[1,2]}}); b=store.jcs_sha256(json.loads('{\n "a": {\n  "c": [1, 2],\n  "d": 2\n },\n "b": 1\n}'))
  self.assertEqual(a,b); self.assertEqual(len(a),64)
 def test_content_hash_excludes_own_field(self):
  document={'schema':store.SCHEMA,'revision':1,'content_sha256':'x'*64}
  self.assertEqual(store.content_hash(document),store.jcs_sha256({'schema':store.SCHEMA,'revision':1}))
 def test_duplicate_keys_are_rejected(self):
  with self.assertRaises(store.StoreError) as ctx: store.loads('{"a":1,"a":2}')
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('duplicate',ctx.exception.message)
 def test_error_codes_map_to_blocked_exit(self):
  self.assertEqual(set(store.EXIT_BY_CODE),set(store.KEBAB_ALIASES))
  self.assertEqual(set(store.EXIT_BY_CODE.values()),{2})
  error=store.StoreError('STATE_DIVERGENCE','x'); self.assertEqual(error.payload(),{'verdict':'BLOCKED','code':'STATE_DIVERGENCE','error':'x'}); self.assertEqual(error.exit_code,2)

class StoreContract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name); self.r=make_repo(self.base/'repo')
 def tearDown(self): self.tmp.cleanup()
 def paths(self): return store.store_paths(self.r)
 def register(self,**kw): return store.bootstrap(self.r,now=CLOCK,**kw)
 def rewrite(self,mutate,rehash=True):
  path=self.paths().orchestrator; document=json.loads(path.read_text(encoding='utf-8')); document=mutate(document)
  if rehash: document.pop('content_sha256',None); document['content_sha256']=store.content_hash(document)
  path.write_bytes(store.jcs(document)+b'\n'); return path

 # --- 5.5.1 bootstrap -------------------------------------------------
 def test_bootstrap_writes_revision_one_under_git_common_dir(self):
  payload=self.register(); paths=self.paths()
  self.assertEqual((payload['verdict'],payload['revision'],payload['schema']),('CREATED',1,store.SCHEMA))
  self.assertEqual(Path(payload['store_root']),paths.root); self.assertEqual(paths.root.parent.name,'.git')
  snapshot=store.read_snapshot(self.r); self.assertEqual(snapshot.revision,1)
  self.assertEqual(snapshot.content_sha256,store.content_hash(snapshot.document))
  self.assertTrue(snapshot.project_id.startswith('sha256:')); self.assertFalse((self.r/'.grill').exists())
 def test_bootstrap_creates_the_declared_layout(self):
  payload=self.register(); paths=self.paths()
  for directory in (paths.locks,paths.receipts,paths.policies): self.assertTrue(directory.is_dir(),directory)
  self.assertEqual(sorted(p.name for p in paths.root.iterdir()),['events-head.json','events.jsonl','locks','orchestrator.json','policies','receipts'])
  # §22/Core anchoring: bootstrap's revision-1 commit is journaled before it is visible.
  genesis=store.read_events(self.r); self.assertEqual(len(genesis),1)
  self.assertEqual(genesis[0]['event'],store.COMMIT_EVENT); self.assertEqual(genesis[0]['revision'],1)
  self.assertEqual(genesis[0]['snapshot_sha256'],payload['content_sha256']); self.assertEqual(genesis[0]['sequence'],1)
  head=json.loads(paths.events_head.read_text(encoding='utf-8'))
  self.assertEqual(head,{'sequence':1,'content_sha256':genesis[0]['content_sha256']})
  document=store.read_snapshot(self.r).document
  self.assertEqual(document['journal_head'],{'sequence':1,'record_sha256':genesis[0]['content_sha256']})
 def test_bootstrap_creates_the_declared_receipt_categories(self):
  self.register(); paths=self.paths()
  self.assertEqual(sorted(p.name for p in paths.receipts.iterdir()),sorted(store.RECEIPT_CATEGORIES))
  for category in store.RECEIPT_CATEGORIES: self.assertTrue((paths.receipts/category).is_dir())
  self.assertTrue(store.receipt_path(self.r,'dispatch','d-1').parent.is_dir())
 def test_document_matches_the_minimum_schema(self):
  self.register(); document=store.read_snapshot(self.r).document
  self.assertEqual(sorted(document),['backlog_links','content_sha256','dispatch_control','journal_head','project','revision','schema','updated_at','work_items'])
  self.assertEqual(sorted(document['project']),['control_worktree','git_common_dir','integration_branch','project_id'])
  self.assertEqual(document['project']['integration_branch'],'main'); self.assertEqual(document['updated_at'],CLOCK())
 def test_bootstrap_is_idempotent(self):
  first=self.register(); before=self.paths().orchestrator.read_bytes(); second=self.register()
  self.assertEqual((first['verdict'],second['verdict']),('CREATED','REUSED'))
  self.assertEqual(second['revision'],1); self.assertEqual(first['project_id'],second['project_id']); self.assertEqual(before,self.paths().orchestrator.read_bytes())
 def test_concurrent_initialisers_produce_one_creator(self):
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(lambda _: self.register(),range(4)))
  self.assertEqual(sorted(r['verdict'] for r in results),['CREATED','REUSED','REUSED','REUSED'])
  self.assertEqual({r['revision'] for r in results},{1}); self.assertEqual(len({r['project_id'] for r in results}),1)
 def test_divergent_identity_fails_closed(self):
  # A direct rewrite (bypassing transact/write_snapshot) recomputes a *self*-consistent
  # hash, but the journal anchor from bootstrap still names the original hash for
  # revision 1 -- so this is now caught earlier, as STATE_DIVERGENCE, than the
  # project-identity comparison inside bootstrap ever runs.
  self.register(); self.rewrite(lambda d: {**d,'project':{**d['project'],'project_id':'sha256:'+'0'*64}})
  with self.assertRaises(store.StoreError) as ctx: self.register()
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertIn('journal-anchored',ctx.exception.message)
 def test_explicit_divergent_content_fails_closed(self):
  self.register(); self.assertEqual(self.register(integration_branch='main')['verdict'],'REUSED')
  with self.assertRaises(store.StoreError) as ctx: self.register(integration_branch='release')
  self.assertEqual(ctx.exception.code,'PROJECT_IDENTITY_DIVERGENCE')
 def test_non_git_and_non_toplevel_roots_fail_closed(self):
  outside=self.base/'plain'; outside.mkdir(); nested=self.r/'nested'; nested.mkdir()
  for candidate in (outside,nested,self.base/'missing'):
   with self.assertRaises(store.StoreError) as ctx: store.bootstrap(candidate,now=CLOCK)
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
 def test_relative_common_dir_resolves_against_the_worktree(self):
  elsewhere=self.base/'cwd'; elsewhere.mkdir(); previous=os.getcwd(); os.chdir(elsewhere)
  try: payload=self.register()
  finally: os.chdir(previous)
  self.assertEqual(Path(payload['store_root']),Path(os.path.realpath(self.r/'.git'))/'grill'); self.assertFalse((elsewhere/'grill').exists())
 def test_linked_worktree_shares_one_store(self):
  self.register(); worktree=self.base/'wt'; git(self.r,'worktree','add','-q','-b','side',str(worktree))
  self.assertEqual(store.store_paths(worktree).root,self.paths().root)
  self.assertEqual(store.read_snapshot(worktree).content_sha256,store.read_snapshot(self.r).content_sha256)
  self.assertEqual(store.bootstrap(worktree,now=CLOCK)['verdict'],'REUSED')

 # --- invariants 10 and 11: revision, CAS, atomic write ---------------
 def test_compare_and_swap_increments_revision(self):
  self.register(); snapshot=store.read_snapshot(self.r); document=dict(snapshot.document); document['work_items']={'feature-a1':WORK_ITEM()}
  written=store.write_snapshot(self.r,document,snapshot.revision,now=CLOCK)
  self.assertEqual(written.revision,2); self.assertEqual(store.read_snapshot(self.r).document['work_items'],{'feature-a1':WORK_ITEM()})
  self.assertEqual(written.content_sha256,store.content_hash(written.document))
 def test_stale_revision_is_state_divergence_without_write(self):
  self.register(); snapshot=store.read_snapshot(self.r); store.write_snapshot(self.r,dict(snapshot.document),1,now=CLOCK)
  before=self.paths().orchestrator.read_bytes()
  for stale in (1,0,99,'2',None):
   with self.assertRaises(store.StoreError) as ctx: store.write_snapshot(self.r,dict(snapshot.document),stale,now=CLOCK)
   self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE')
  self.assertEqual(before,self.paths().orchestrator.read_bytes())
 def test_transact_serialises_concurrent_writers(self):
  self.register()
  def add(name):
   return store.transact(self.r,lambda d: {**d,'work_items':{**d['work_items'],name:WORK_ITEM()}},now=CLOCK)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(add,['work-a','work-b']))
  snapshot=store.read_snapshot(self.r); self.assertEqual(snapshot.revision,3); self.assertEqual(sorted(snapshot.document['work_items']),['work-a','work-b'])
 def test_transact_rejects_a_stale_document(self):
  self.register()
  with self.assertRaises(store.StoreError) as ctx: store.transact(self.r,lambda d: {**d,'revision':d['revision']-1},now=CLOCK)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(store.read_snapshot(self.r).revision,1)
 def test_project_block_is_immutable_after_registration(self):
  self.register(); snapshot=store.read_snapshot(self.r)
  document={**snapshot.document,'project':{**snapshot.document['project'],'integration_branch':'other'}}
  with self.assertRaises(store.StoreError) as ctx: store.write_snapshot(self.r,document,snapshot.revision,now=CLOCK)
  self.assertEqual(ctx.exception.code,'PROJECT_IDENTITY_DIVERGENCE'); self.assertEqual(store.read_snapshot(self.r).revision,1)
 def test_write_leaves_no_temporary_file(self):
  self.register(); snapshot=store.read_snapshot(self.r); store.write_snapshot(self.r,dict(snapshot.document),1,now=CLOCK)
  self.assertEqual([p.name for p in self.paths().root.iterdir() if p.name.startswith('.orchestrator-')],[])
 def test_failed_replace_leaves_the_snapshot_intact(self):
  self.register(); before=self.paths().orchestrator.read_bytes(); snapshot=store.read_snapshot(self.r)
  with mock.patch.object(store.os,'replace',side_effect=OSError('disk')):
   with self.assertRaises(OSError): store.write_snapshot(self.r,dict(snapshot.document),1,now=CLOCK)
  self.assertEqual(before,self.paths().orchestrator.read_bytes())
  self.assertEqual([p.name for p in self.paths().root.iterdir() if p.name.startswith('.orchestrator-')],[])
  self.assertFalse((self.paths().locks/store.ORCHESTRATOR_LOCK).exists())

 # --- invariant 12: fail-closed, never recreated ----------------------
 def test_hash_divergence_fails_closed_without_recreation(self):
  self.register(); path=self.rewrite(lambda d: {**d,'work_items':{'tampered-wi':WORK_ITEM()}},rehash=False); before=path.read_bytes()
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('content hash mismatch',ctx.exception.message); self.assertEqual(before,path.read_bytes())
 def test_invalid_json_fails_closed_without_recreation(self):
  self.register(); path=self.paths().orchestrator; path.write_bytes(b'{"schema":');
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertEqual(path.read_bytes(),b'{"schema":')
 def test_invalid_utf8_fails_closed(self):
  self.register(); path=self.paths().orchestrator; path.write_bytes(b'{"schema":"\xff\xfe"}')
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('invalid utf-8',ctx.exception.message)
 def test_unknown_schema_fails_closed(self):
  self.register(); self.rewrite(lambda d: {**d,'schema':'grill-orchestrator/v2'})
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('unknown schema',ctx.exception.message)
 def test_duplicate_keys_in_the_snapshot_fail_closed(self):
  self.register(); path=self.paths().orchestrator; text=path.read_text(encoding='utf-8').rstrip('\n')
  path.write_bytes((text[:-1]+',"revision":1}\n').encode('utf-8'))
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('duplicate JSON key: revision',ctx.exception.message)
 def test_structural_fields_are_validated(self):
  self.register()
  for mutation in (lambda d: {**d,'revision':0},lambda d: {**d,'revision':True},lambda d: {**d,'work_items':[]},lambda d: {**d,'updated_at':'yesterday'},lambda d: {**d,'project':{**d['project'],'project_id':'nope'}}):
   self.rewrite(mutation)
   with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
 def test_missing_store_is_named_not_recreated(self):
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('project-register',ctx.exception.message); self.assertFalse(self.paths().root.exists())
 def test_store_root_that_is_not_a_directory_fails_closed(self):
  self.paths().root.write_text('not a store')
  for call in (lambda: self.register(),lambda: store.read_snapshot(self.r)):
   with self.assertRaises(store.StoreError) as ctx: call()
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('not a directory',ctx.exception.message)
 @unittest.skipUnless(POSIX,'symlink semantics are POSIX only')
 def test_symlinked_store_root_is_rejected(self):
  outside=self.base/'external-store'; outside.mkdir(); os.symlink(outside,self.paths().root,target_is_directory=True)
  with self.assertRaises(store.StoreError) as ctx: self.register()
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('symlink rejected',ctx.exception.message); self.assertEqual(list(outside.iterdir()),[])
 @unittest.skipUnless(POSIX,'symlink semantics are POSIX only')
 def test_symlinked_snapshot_is_rejected_without_reading_the_target(self):
  self.register(); secret=self.base/'external.json'; secret.write_text('TOP-SECRET'); path=self.paths().orchestrator; path.unlink(); os.symlink(secret,path)
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertNotIn('TOP-SECRET',ctx.exception.message); self.assertEqual(secret.read_text(),'TOP-SECRET')
 @unittest.skipUnless(POSIX,'permission policy is POSIX only')
 def test_permissions_wider_than_policy_block_initialisation(self):
  self.register(); os.chmod(self.paths().root,0o777)
  for call in (lambda: self.register(),lambda: store.read_snapshot(self.r)):
   with self.assertRaises(store.StoreError) as ctx: call()
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('permissions wider',ctx.exception.message)

 # --- traversal and lock paths ----------------------------------------
 def test_receipt_paths_reject_traversal_and_unknown_categories(self):
  self.register()
  for name in ('../escape','a/b','..','.hidden','',' x',None,'x'*200):
   with self.assertRaises(store.StoreError) as ctx: store.receipt_path(self.r,'dispatch',name)
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  with self.assertRaises(store.StoreError): store.receipt_path(self.r,'unknown','x')
  self.assertEqual(store.receipt_path(self.r,'dispatch','d-1'),self.paths().receipts/'dispatch/d-1.json')
 def test_work_lock_validates_the_identifier_before_opening_a_path(self):
  self.register()
  for work_id in ('../evil','a/b','x','bad id',None):
   with self.assertRaises(store.StoreError) as ctx:
    with store.work_lock(self.r,work_id,timeout=0.2): pass
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  with store.work_lock(self.r,'feature-a1b2',timeout=0.2) as lock: self.assertEqual(lock.name,'work-feature-a1b2.lock')
  self.assertEqual(sorted(p.name for p in self.paths().locks.iterdir()),[])
 def test_lock_contention_is_named_and_bounded(self):
  self.register(); lock=self.paths().locks/store.ORCHESTRATOR_LOCK; lock.mkdir()
  # A remote owner cannot be reclaimed; this proves bounded contention on every
  # runner.  Do not infer capability from the OS name: recent macOS runners can
  # expose /proc and therefore exercise Linux-style stale-lock recovery.
  (lock/'owner.json').write_text(json.dumps({'pid':os.getpid(),'host':'other-host'},sort_keys=True))
  snapshot=store.read_snapshot(self.r)
  with self.assertRaises(store.StoreError) as ctx: store.write_snapshot(self.r,dict(snapshot.document),1,now=CLOCK,timeout=0.2)
  self.assertEqual(ctx.exception.code,'LOCK_CONTENTION'); self.assertEqual(store.read_snapshot(self.r).revision,1)
 @unittest.skipUnless(LINUX,'start-token reclaim is Linux only')
 def test_stale_lock_is_reclaimed(self):
  self.register(); lock=self.paths().locks/store.ORCHESTRATOR_LOCK; lock.mkdir()
  (lock/'owner.json').write_text(json.dumps({'pid':os.getpid(),'host':__import__('socket').gethostname(),'process_start':'linux:1'},sort_keys=True))
  snapshot=store.read_snapshot(self.r); self.assertEqual(store.write_snapshot(self.r,dict(snapshot.document),1,now=CLOCK,timeout=1.0).revision,2)
  self.assertFalse(lock.exists())
 def test_lock_is_released_after_success(self):
  self.register(); snapshot=store.read_snapshot(self.r); store.write_snapshot(self.r,dict(snapshot.document),1,now=CLOCK)
  self.assertEqual(sorted(p.name for p in self.paths().locks.iterdir()),[])

 # --- invariant 13: read-only status and preview -----------------------
 def test_reads_before_bootstrap_create_nothing(self):
  common=Path(os.path.realpath(self.r/'.git')); before=tree(common)
  self.assertIsNone(store.read_snapshot(self.r,required=False)); self.assertFalse(store.store_exists(self.r))
  store.store_paths(self.r); store.project_identity(self.r); store.receipt_path(self.r,'dispatch','d-1')
  self.assertFalse((common/'grill').exists()); self.assertEqual(before,tree(common))
 def test_reads_after_bootstrap_do_not_touch_the_store(self):
  self.register(); before=tree(self.paths().root)
  store.read_snapshot(self.r); store.read_events(self.r); store.store_exists(self.r); store.store_paths(self.r); store.receipt_path(self.r,'worktree','wt-a')
  self.assertEqual(before,tree(self.paths().root))

 # --- append-only journal ----------------------------------------------
 def test_events_are_appended_and_verified(self):
  self.register(); genesis=store.read_events(self.r); self.assertEqual(len(genesis),1)
  first=store.append_event(self.r,{'event':'project.registered'},now=CLOCK)
  before=self.paths().events.read_bytes(); second=store.append_event(self.r,{'event':'work.created','work_id':'a'},now=CLOCK)
  data=self.paths().events.read_bytes(); self.assertTrue(data.startswith(before)); self.assertEqual(len(data.splitlines()),3)
  self.assertEqual(store.read_events(self.r),genesis+[first,second]); self.assertEqual(first['recorded_at'],CLOCK())
  self.assertEqual(first['sequence'],2); self.assertEqual(first['previous_sha256'],genesis[0]['content_sha256'])
  self.assertEqual(second['sequence'],3); self.assertEqual(second['previous_sha256'],first['content_sha256'])
  self.assertEqual(first['content_sha256'],store.jcs_sha256({'event':'project.registered','recorded_at':CLOCK(),'sequence':2,'previous_sha256':genesis[0]['content_sha256']}))
 def test_events_journal_is_never_recreated(self):
  self.register(); self.paths().events.unlink()
  for call in (lambda: store.append_event(self.r,{'event':'x'},now=CLOCK),lambda: store.read_events(self.r)):
   with self.assertRaises(store.StoreError) as ctx: call()
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertFalse(self.paths().events.exists())
 def test_tampered_record_fails_closed(self):
  self.register(); record=store.append_event(self.r,{'event':'x'},now=CLOCK); record['event']='y'
  self.paths().events.write_bytes(store.jcs(record)+b'\n')
  with self.assertRaises(store.StoreError) as ctx: store.read_events(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('hash mismatch',ctx.exception.message)
 def test_journal_never_replaces_the_snapshot(self):
  self.register(); store.append_event(self.r,{'event':'x'},now=CLOCK); self.assertEqual(store.read_snapshot(self.r).revision,1)
  with self.assertRaises(store.StoreError): store.append_event(self.r,['not','an','object'],now=CLOCK)

 # --- journal anchoring: the real attacks, not the disarmed one ---------
 # A hash chain (sequence + previous_sha256) alone can only ever prove that
 # what remains is a valid *prefix*: a valid chain of length N is always a
 # valid prefix of a chain of length N+k, so cutting whole records off the
 # *end* is undetectable by chain validation in isolation, no matter how the
 # chain is built. Deleting a *middle* record or reordering two records both
 # break the chain at that point and are fully closed by read_events() alone.
 # Cutting the end is closed a different way: every successful snapshot
 # commit journals a record naming its own revision+hash *before* that
 # revision becomes visible (see store._check_revision_anchor), so read_snapshot
 # fails STATE_DIVERGENCE when the tail record anchoring the *current*
 # revision has been removed. Both are ORCHESTRATOR_INVALID/STATE_DIVERGENCE
 # BLOCKED failures (EXIT_BY_CODE maps both to exit 2); the point is that
 # neither attack silently succeeds any more.
 def test_journal_rejects_a_deleted_middle_record(self):
  self.register()
  for i in range(4): store.append_event(self.r,{'event':f'e{i}'},now=CLOCK)
  path=self.paths().events; lines=path.read_bytes().splitlines(keepends=True); self.assertEqual(len(lines),5)
  path.write_bytes(b''.join(lines[:2]+lines[3:]))  # drop one whole record from the middle
  with self.assertRaises(store.StoreError) as ctx: store.read_events(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertTrue('sequence' in ctx.exception.message or 'chain' in ctx.exception.message,ctx.exception.message)
 def test_journal_rejects_reordered_records(self):
  self.register()
  for i in range(3): store.append_event(self.r,{'event':f'e{i}'},now=CLOCK)
  path=self.paths().events; lines=path.read_bytes().splitlines(keepends=True); self.assertEqual(len(lines),4)
  path.write_bytes(b''.join([lines[0],lines[1],lines[3],lines[2]]))  # swap the last two whole records
  with self.assertRaises(store.StoreError) as ctx: store.read_events(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertTrue('sequence' in ctx.exception.message or 'chain' in ctx.exception.message,ctx.exception.message)
 def test_journal_rejects_whole_records_cut_from_the_end(self):
  # A pure tail-cut -- of a commit record or a domain event alike -- no
  # longer relies solely on the revision-anchor point lookup: the events-head
  # witness (persisted on every append, see _check_events_head) catches any
  # tail-cut directly, because the file's actual last record stops matching
  # what was last durably appended.
  self.register()
  store.transact(self.r,lambda d: {**d,'work_items':{'work-a':WORK_ITEM()}},now=CLOCK)
  store.transact(self.r,lambda d: {**d,'work_items':{**d['work_items'],'work-b':WORK_ITEM()}},now=CLOCK)
  self.assertEqual(store.read_snapshot(self.r).revision,3)
  path=self.paths().events; lines=path.read_bytes().splitlines(keepends=True); self.assertEqual(len(lines),3)
  path.write_bytes(b''.join(lines[:-1]))  # cut the whole trailing commit record (revision 3's anchor)
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('head',ctx.exception.message)
 def test_snapshot_rollback_with_recomputed_hash_fails_closed(self):
  # The exact attack the critic demonstrated: roll orchestrator.json back to
  # an earlier revision with a *self-consistent* recomputed hash. Invariant
  # 10 requires this to fail even though the document is internally valid.
  self.register()
  for name in ('work-a','work-b','work-c','work-d'):
   store.transact(self.r,lambda d,n=name: {**d,'work_items':{**d['work_items'],n:WORK_ITEM()}},now=CLOCK)
  snapshot=store.read_snapshot(self.r); self.assertEqual(snapshot.revision,5)
  forged={**snapshot.document,'revision':2,'work_items':{}}; forged.pop('content_sha256',None)
  forged['content_sha256']=store.content_hash(forged)
  before=self.paths().orchestrator.read_bytes(); self.paths().orchestrator.write_bytes(store.jcs(forged)+b'\n')
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertIn('journal-anchored',ctx.exception.message)
  self.assertNotEqual(before,self.paths().orchestrator.read_bytes())  # forged bytes sit there; nothing auto-repairs them
 def test_concurrent_processes_never_repeat_journal_sequence(self):
  # Real OS processes (not threads): each opens its own interpreter and races
  # every other one to append through the same global write lock.
  self.register()
  with multiprocessing.Pool(processes=5) as pool:
   results=pool.starmap(_mp_append_events,[(self.r,6,f'w{i}') for i in range(5)])
  flat=[seq for group in results for seq in group]
  self.assertEqual(len(flat),30); self.assertEqual(len(flat),len(set(flat)),'duplicate sequence assigned under concurrency')
  records=store.read_events(self.r)  # re-validates hash+sequence+chain end to end
  self.assertEqual(len(records),1+len(flat)); self.assertEqual([r['sequence'] for r in records],list(range(1,len(records)+1)))

 # --- §5.5.1 step 6: derived (not just explicit) identity must match ----
 def test_bootstrap_detects_branch_drift_without_explicit_argument(self):
  self.register(); git(self.r,'checkout','-q','-b','release')
  with self.assertRaises(store.StoreError) as ctx: self.register()  # no integration_branch kwarg
  self.assertEqual(ctx.exception.code,'PROJECT_IDENTITY_DIVERGENCE'); self.assertIn('integration_branch',ctx.exception.message)

 # --- §5.4: work_items / dispatch_control shape ---------------------------
 def test_work_items_with_unsafe_key_or_non_object_value_are_rejected(self):
  self.register()
  for bad in ({'../../etc':{'not':'a work item'},'x':12345},{'ok-id':{'lifecycle':'ACTIVE'}},{'ok-id':WORK_ITEM(lifecycle='NOT-A-REAL-STATE')}):
   with self.assertRaises(store.StoreError) as ctx:
    store.transact(self.r,lambda d,wi=bad: {**d,'work_items':wi},now=CLOCK)
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertEqual(store.read_snapshot(self.r).document['work_items'],{})
 def test_dispatch_control_shape_is_validated(self):
  self.register()
  for bad in ({'leader_epoch':-7,'leader_lease':'nope'},{'leader_epoch':1,'leader_lease':{'lease_id':'l','owner_id':'o','runtime':'not-a-runtime','fencing_token':1,'acquired_at':CLOCK(),'expires_at':CLOCK()}}):
   with self.assertRaises(store.StoreError) as ctx:
    store.transact(self.r,lambda d,dc=bad: {**d,'dispatch_control':dc},now=CLOCK)
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertEqual(store.read_snapshot(self.r).document['dispatch_control'],{'leader_epoch':0,'leader_lease':None})

 # --- invariant 14: ORPHANED is representable once the store validates
 # worktree shape; *detecting* an orphaned worktree (comparing the registry
 # against `git worktree list`) is reconcile/worktree-piece work this module
 # does not own -- see gaps_deferred in the round report.
 def test_worktree_orphaned_state_round_trips(self):
  self.register()
  item=WORK_ITEM(worktree={'worktree_id':'wt-orphan-1','path':'/tmp/x','branch':'grill/x','base_commit':None,'state':'ORPHANED','lease_id':None})
  written=store.transact(self.r,lambda d: {**d,'work_items':{'orphan-wi':item}},now=CLOCK)
  self.assertEqual(written.document['work_items']['orphan-wi']['worktree']['state'],'ORPHANED')
  self.assertEqual(store.read_snapshot(self.r).document['work_items']['orphan-wi']['worktree']['state'],'ORPHANED')
 def test_worktree_state_enum_and_base_commit_format_are_validated(self):
  self.register()
  for worktree in (
   {'worktree_id':'wt-1','path':'/tmp/x','branch':'grill/x','base_commit':None,'state':'NOPE'},
   {'worktree_id':'wt-1','path':'/tmp/x','branch':'grill/x','base_commit':'z','state':'READY'},
   {'worktree_id':'wt-1','path':'/tmp/x','branch':'grill/x','base_commit':'0'*39,'state':'READY'},
   {'worktree_id':'wt-1','path':'/tmp/x','branch':'grill/x','state':'READY'},  # base_commit missing entirely
  ):
   with self.assertRaises(store.StoreError) as ctx:
    store.transact(self.r,lambda d,wt=worktree: {**d,'work_items':{'wi':WORK_ITEM(worktree=wt)}},now=CLOCK)
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertEqual(store.read_snapshot(self.r).document['work_items'],{})
  ok={'worktree_id':'wt-1','path':'/tmp/x','branch':'grill/x','base_commit':'a'*40,'state':'CREATING'}
  store.transact(self.r,lambda d: {**d,'work_items':{'wi':WORK_ITEM(worktree=ok)}},now=CLOCK)
  self.assertEqual(store.read_snapshot(self.r).document['work_items']['wi']['worktree']['state'],'CREATING')

 # --- §5.4: backlog_links shape ------------------------------------------
 def test_backlog_links_shape_is_validated(self):
  self.register()
  for bad in (
   {'k':5},
   {'../x':{'state':'TRACKED','relation':'informational'}},
   {'k':{'state':'NOPE','relation':'informational'}},
   {'k':{'state':'TRACKED','relation':'not-a-relation'}},
  ):
   with self.assertRaises(store.StoreError) as ctx:
    store.transact(self.r,lambda d,bl=bad: {**d,'backlog_links':bl},now=CLOCK)
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertEqual(store.read_snapshot(self.r).document['backlog_links'],{})
  ok={'k':{'state':'CHILD_READY_FOR_GRILL','relation':'non-blocking'}}
  store.transact(self.r,lambda d: {**d,'backlog_links':ok},now=CLOCK)
  self.assertEqual(store.read_snapshot(self.r).document['backlog_links'],ok)

 # --- §5.4: unknown top-level keys ----------------------------------------
 def test_unknown_top_level_key_is_rejected(self):
  self.register()
  with self.assertRaises(store.StoreError) as ctx:
   store.transact(self.r,lambda d: {**d,'extra_key':'nope'},now=CLOCK)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertIn('unknown top-level key',ctx.exception.message)

 # --- invariant 10, round 3: bidirectional / head-of-journal anchor -------
 # The round-2 fix was a POINT lookup: "does some commit record for MY
 # revision have a matching hash?" -- never "is my revision the journal's
 # LAST one?". Two attacks defeated it with the journal fully intact; both
 # must now fail via the rewritten _check_revision_anchor.
 def test_byte_exact_rollback_with_intact_journal_fails_closed(self):
  # Not a forged document: the *actual* bytes legitimately written for
  # revision 3, restored verbatim after the store has moved on to revision 5,
  # with events.jsonl and events-head.json completely untouched.
  self.register()
  for name in ('work-a','work-b'):
   store.transact(self.r,lambda d,n=name: {**d,'work_items':{**d['work_items'],n:WORK_ITEM()}},now=CLOCK)
  self.assertEqual(store.read_snapshot(self.r).revision,3)
  historical=self.paths().orchestrator.read_bytes()
  for name in ('work-c','work-d'):
   store.transact(self.r,lambda d,n=name: {**d,'work_items':{**d['work_items'],n:WORK_ITEM()}},now=CLOCK)
  self.assertEqual(store.read_snapshot(self.r).revision,5)
  events_before=self.paths().events.read_bytes(); head_before=self.paths().events_head.read_bytes()
  self.paths().orchestrator.write_bytes(historical)  # roll back to the real, once-valid revision-3 bytes
  self.assertEqual(self.paths().events.read_bytes(),events_before)  # journal genuinely untouched
  self.assertEqual(self.paths().events_head.read_bytes(),head_before)
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertIn('journal-anchored',ctx.exception.message)
  # the store must stay fail-closed, not silently re-mint revision 4
  with self.assertRaises(store.StoreError):
   store.transact(self.r,lambda d: {**d,'work_items':{**d['work_items'],'work-e':WORK_ITEM()}},now=CLOCK)
 def test_journal_anchored_future_revision_is_a_named_error_not_ignored(self):
  # A phantom commit record for a revision *ahead* of the honest snapshot
  # must be refused by name, not silently ignored because the point lookup
  # for the snapshot's own (lower) revision still succeeds.
  self.register()
  store.transact(self.r,lambda d: {**d,'work_items':{'work-a':WORK_ITEM()}},now=CLOCK)
  self.assertEqual(store.read_snapshot(self.r).revision,2)
  path=self.paths().events; last=json.loads(path.read_bytes().splitlines()[-1])
  phantom={'event':store.COMMIT_EVENT,'revision':3,'snapshot_sha256':'1'*64,'recorded_at':CLOCK(),
           'sequence':last['sequence']+1,'previous_sha256':last['content_sha256']}
  phantom['content_sha256']=store.jcs_sha256(phantom)
  path.write_bytes(path.read_bytes()+store.jcs(phantom)+b'\n')
  self.paths().events_head.write_bytes(store.jcs({'sequence':phantom['sequence'],'content_sha256':phantom['content_sha256']})+b'\n')
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)  # orchestrator.json is honestly still at revision 2
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE')
  self.assertIn('journal-anchored',ctx.exception.message); self.assertIn('3',ctx.exception.message)

 # --- append_event must not be able to forge the commit anchor ------------
 def test_append_event_refuses_the_reserved_commit_event(self):
  self.register()
  before=self.paths().events.read_bytes()
  for bad_revision,bad_hash in ((1,'a'*64),(99,'b'*64)):
   with self.assertRaises(store.StoreError) as ctx:
    store.append_event(self.r,{'event':store.COMMIT_EVENT,'revision':bad_revision,'snapshot_sha256':bad_hash},now=CLOCK)
   self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertEqual(before,self.paths().events.read_bytes())  # nothing was appended
 def test_append_event_blocks_forged_commit_after_direct_snapshot_rewrite(self):
  # The exact two-step round-2 PoC: forge orchestrator.json in place at the
  # current revision with a self-consistent recomputed hash, then try to
  # mint the matching commit record through the public API alone.
  self.register()
  store.transact(self.r,lambda d: {**d,'work_items':{'work-a':WORK_ITEM()}},now=CLOCK)
  snapshot=store.read_snapshot(self.r); self.assertEqual(snapshot.revision,2)
  forged={**snapshot.document,'work_items':{}}; forged.pop('journal_head',None); forged.pop('content_sha256',None)
  forged['content_sha256']=store.content_hash(forged)
  self.paths().orchestrator.write_bytes(store.jcs(forged)+b'\n')
  events_before=self.paths().events.read_bytes()
  with self.assertRaises(store.StoreError) as ctx:
   store.append_event(self.r,{'event':store.COMMIT_EVENT,'revision':2,'snapshot_sha256':forged['content_sha256']},now=CLOCK)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')  # fails AT the append call itself
  self.assertEqual(events_before,self.paths().events.read_bytes())  # journal never got the forged anchor
  with self.assertRaises(store.StoreError):  # so the forged snapshot never became legible either
   store.read_snapshot(self.r)

 # --- §22/Core: journal tail-cut of pure domain events, no reissue --------
 def test_journal_rejects_tail_cut_domain_events_and_never_reissues_sequence(self):
  self.register()
  for i in range(5): store.append_event(self.r,{'event':f'domain.e{i}'},now=CLOCK)
  path=self.paths().events; lines=path.read_bytes().splitlines(keepends=True); self.assertEqual(len(lines),6)
  path.write_bytes(b''.join(lines[:-3]))  # cut the last 3 domain events -- no commit record involved
  with self.assertRaises(store.StoreError) as ctx: store.read_events(self.r)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertIn('head',ctx.exception.message)
  with self.assertRaises(store.StoreError) as ctx2:
   store.append_event(self.r,{'event':'domain.after-cut'},now=CLOCK)
  self.assertEqual(ctx2.exception.code,'ORCHESTRATOR_INVALID')
  self.assertEqual(len(self.paths().events.read_bytes().splitlines()),3)  # nothing appended; no sequence reissued

 # --- §22/Core: cross-check against a receipt, not just the journal -------
 def test_receipt_for_unknown_work_item_fails_closed(self):
  self.register()
  store.transact(self.r,lambda d: {**d,'work_items':{'work-a':WORK_ITEM()}},now=CLOCK)
  receipt=self.paths().receipts/'worktree'/'work-a.json'; self.assertTrue(receipt.is_file())
  store.transact(self.r,lambda d: {**d,'work_items':{}},now=CLOCK)  # work-a legitimately removed from the snapshot
  self.assertTrue(receipt.is_file())  # the receipt is durable; the snapshot does not own deleting it
  with self.assertRaises(store.StoreError) as ctx: store.read_snapshot(self.r)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertIn('work-a',ctx.exception.message)

 # --- FASE-002: optional durable Gauntlet run block ----------------------
 # These cases deliberately exercise Store validation directly.  The public
 # CLI may project these records later, but it must never be the validator of
 # coordinator-owned durable state.
 def test_gauntlet_block_is_optional_and_a_valid_closed_record_round_trips(self):
  self.register()
  plain=store.transact(self.r,lambda d: {**d,'work_items':{'plain-work':WORK_ITEM()}},now=CLOCK)
  self.assertNotIn('gauntlet',plain.document['work_items']['plain-work'])
  before=self.paths().orchestrator.read_bytes()
  with self.assertRaises(store.StoreError) as ctx:
   store.transact(self.r,lambda d: {**d,'work_items':{**d['work_items'],'gauntlet-work':{**WORK_ITEM(slug='gauntlet'),'gauntlet':GAUNTLET_BLOCK()}}},now=CLOCK)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  written=self._gauntlet_transition()
  block=written.document['work_items']['gauntlet-work']['gauntlet']
  self.assertEqual(block['schema'],'grill-gauntlet-runs/v1')
  self.assertEqual(store.read_snapshot(self.r).document['work_items']['gauntlet-work']['gauntlet'],block)

 def test_gauntlet_block_rejects_unknown_keys_and_malformed_run_shape_without_write(self):
  self.register(); before=self.paths().orchestrator.read_bytes()
  cases=(
   {'schema':'grill-gauntlet-runs/v1','runs':{},'extra':True},
   {'schema':'grill-gauntlet-runs/v2','runs':{}},
   {'schema':'grill-gauntlet-runs/v1','runs':[]},
   {'schema':'grill-gauntlet-runs/v1','runs':{'../run':GAUNTLET_RUN()}},
   {'schema':'grill-gauntlet-runs/v1','runs':{'run-alpha-1':{'state':'ADMITTED'}}},
   {'schema':'grill-gauntlet-runs/v1','runs':{'run-alpha-1':{**GAUNTLET_RUN(),'unknown':True}}},
  )
  for bad in cases:
   with self.subTest(bad=bad):
    try: self._gauntlet_transition(block=bad)
    except store.StoreError as exc: self.assertEqual(exc.code,'ORCHESTRATOR_INVALID')
    else: self.fail('malformed gauntlet block was accepted')
    self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_gauntlet_block_rejects_invalid_enums_hashes_and_worker_authority_without_write(self):
  self.register(); before=self.paths().orchestrator.read_bytes(); good=GAUNTLET_RUN()
  bad_runs=(
   {**good,'state':'RUNNING'},
   {**good,'recovery_count':2},
   {**good,'recovery_count':True},
   {**good,'admission':{**good['admission'],'activation_sha256':'not-a-hash'}},
   {**good,'admission':{**good['admission'],'base_commit':'f'*39}},
   {**good,'waves':{'wave-0001':{'state':'SCHEDULED','node_ids':DEFAULT_WAVE_NODE_IDS}}},
   {**good,'workers':{'worker-a':GAUNTLET_WORKER('worker-a',state='EXECUTING')}},
   {**good,'workers':{'../worker':GAUNTLET_WORKER('../worker')}},
   {**good,'workers':{'worker-a':GAUNTLET_WORKER('worker-a',grant={'scope_paths':['../escape'],'capabilities':['store-write']})}},
  )
  for run in bad_runs:
   with self.subTest(run=run):
    try: self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':run}))
    except store.StoreError as exc: self.assertEqual(exc.code,'ORCHESTRATOR_INVALID')
    else: self.fail('invalid gauntlet run was accepted')
    self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_gauntlet_enum_fields_reject_unhashable_values_as_named_no_write_failures(self):
  self.register(); before=self.paths().orchestrator.read_bytes(); valid=GAUNTLET_RUN()
  lease={'lease_id':'lease-a','fencing_token':1,'acquired_at':CLOCK(),'expires_at':CLOCK(),'state':{},'recovery_count':0}
  malformed=(
   {**valid,'state':[]},
   {**valid,'waves':{'wave-0001':{'state':[],'node_ids':DEFAULT_WAVE_NODE_IDS}}},
   {**valid,'workers':{'worker-a':GAUNTLET_WORKER('worker-a',lease=lease)}},
   {**valid,'workers':{'worker-a':GAUNTLET_WORKER('worker-a',grant={'scope_paths':['plugin'],'capabilities':[[]]})}},
  )
  for run in malformed:
   with self.subTest(run=run):
    try: self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':run}))
    except store.StoreError as exc: self.assertEqual(exc.code,'ORCHESTRATOR_INVALID')
    else: self.fail('unhashable gauntlet enum value was accepted')
    self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_gauntlet_worker_count_scopes_and_workspace_branch_fail_closed_without_write(self):
  self.register(); before=self.paths().orchestrator.read_bytes(); valid=GAUNTLET_RUN()
  six_workers={f'worker-{n}':GAUNTLET_WORKER(f'worker-{n}') for n in range(6)}
  bad_runs=(
   {**valid,'workers':six_workers},
   {**valid,'workers':{'worker-a':GAUNTLET_WORKER('worker-a',grant={'scope_paths':['safe\x00path'],'capabilities':['git-local']})}},
   {**valid,'workers':{'worker-a':GAUNTLET_WORKER('worker-a',grant={'scope_paths':['safe\x1fpath'],'capabilities':['git-local']})}},
   *({**valid,'workers':{'worker-a':GAUNTLET_WORKER('worker-a',workspace={'worktree_key':'wt-a','branch':branch,'base_commit':'e'*40,'clean':False,'converged':False,'cleanup_eligible':False})}} for branch in ('bad\x00branch','bad\x1fbranch','/host/path','../escape','nested/path')),
  )
  for run in bad_runs:
   with self.subTest(run=run):
    try: self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':run}))
    except store.StoreError as exc: self.assertEqual(exc.code,'ORCHESTRATOR_INVALID')
    else: self.fail('unsafe worker declaration was accepted')
    self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_state_machine_rejects_direct_run_and_worker_jumps_without_write(self):
  self.register(); absent_complete=GAUNTLET_RUN(state='COMPLETE')
  before=self.paths().orchestrator.read_bytes()
  with self.assertRaises(store.StoreError) as ctx:
   store.transact(self.r,lambda d: {**d,'work_items':{'gauntlet-work':{**WORK_ITEM(slug='gauntlet'),'gauntlet':GAUNTLET_BLOCK({'run-alpha-1':absent_complete})}}},now=CLOCK)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  admitted=GAUNTLET_RUN(workers={'worker-a':GAUNTLET_WORKER('worker-a')})
  self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':admitted}))
  before=self.paths().orchestrator.read_bytes()
  def jump_run(d):
   d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['state']='COMPLETE'; return d
  with self.assertRaises(store.StoreError) as ctx: store.transact(self.r,jump_run,now=CLOCK)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  def jump_worker(d):
   d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['workers']['worker-a']['state']='PREPARED'; return d
  with self.assertRaises(store.StoreError) as ctx: store.transact(self.r,jump_worker,now=CLOCK)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_generic_transact_cannot_drop_or_rename_existing_gauntlet_entities(self):
  self.register(); workers={'worker-a':GAUNTLET_WORKER('worker-a')}
  self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=workers)}))
  before=self.paths().orchestrator.read_bytes()
  def drop_block(d): d['work_items']['gauntlet-work'].pop('gauntlet'); return d
  def remove_run(d): d['work_items']['gauntlet-work']['gauntlet']['runs'].clear(); return d
  def rename_run(d):
   runs=d['work_items']['gauntlet-work']['gauntlet']['runs']; runs['run-renamed']=runs.pop('run-alpha-1'); return d
  def remove_wave(d): d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['waves'].clear(); return d
  def remove_worker(d): d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['workers'].clear(); return d
  for mutate in (drop_block,remove_run,rename_run,remove_wave,remove_worker):
   with self.subTest(mutate=mutate.__name__), self.assertRaises(store.StoreError) as ctx: store.transact(self.r,mutate,now=CLOCK)
   self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_generic_transact_cannot_bypass_existing_run_state_admission_or_evidence(self):
  self.register(); self._gauntlet_transition()
  before=self.paths().orchestrator.read_bytes()
  def alter_state(d): d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['state']='RECOVERY_ELIGIBLE'; return d
  def alter_admission(d): d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['admission']['config_sha256']='9'*64; return d
  def alter_evidence(d): d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['last_transition']={'event_sequence':2,'receipt_sha256':'8'*64}; return d
  for mutate in (alter_state,alter_admission,alter_evidence):
   with self.subTest(mutate=mutate.__name__), self.assertRaises(store.StoreError) as ctx: store.transact(self.r,mutate,now=CLOCK)
   self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def _gauntlet_transition(self,*,event=None,receipt=None,fault=None,block=None,mutate=None):
  receipt=GAUNTLET_RECEIPT() if receipt is None else receipt
  event=GAUNTLET_EVENT(receipt) if event is None else event
  block=GAUNTLET_BLOCK() if block is None else block
  def add_block(d):
   d={**d,'work_items':{**d['work_items'],'gauntlet-work':{**WORK_ITEM(slug='gauntlet'),'gauntlet':block}}}
   return mutate(d) if mutate is not None else d
  return store.transact_with_event(
   self.r,
   add_block,
   event=event,receipt=receipt,now=CLOCK,fault=fault,
  )

 def _run(self,snapshot=None):
  document=(store.read_snapshot(self.r) if snapshot is None else snapshot).document
  return document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']

 # FASE-003 (T001): advance run-alpha-1's worker map by one legal transition,
 # under a fresh receipt name so the call is free to actually commit.
 def _advance_workers(self,workers,name,waves=None):
  run=GAUNTLET_RUN(workers=workers,waves=waves)
  return self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=name),block=GAUNTLET_BLOCK({'run-alpha-1':run}))

 def test_transact_with_event_commits_one_correlated_receipt_event_anchor_and_snapshot(self):
  self.register(); snapshot=self._gauntlet_transition()
  self.assertEqual(snapshot.revision,2)
  self.assertIn('gauntlet-work',snapshot.document['work_items'])
  receipt=self.paths().receipts/'runtime'/'gauntlet-run-alpha-1.json'
  self.assertTrue(receipt.is_file())
  recorded=json.loads(receipt.read_text(encoding='utf-8'))
  event=GAUNTLET_EVENT(GAUNTLET_RECEIPT())
  self.assertEqual(recorded,GAUNTLET_RECEIPT())
  self.assertEqual(event['receipt_sha256'],store.jcs_sha256(recorded))
  events=store.read_events(self.r)
  semantic=[record for record in events if record.get('event')=='gauntlet.run.admitted']
  self.assertEqual(len(semantic),1)
  for field,value in event.items(): self.assertEqual(semantic[0][field],value)
  self.assertEqual(store.read_snapshot(self.r).document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['last_transition']['event_sequence'],semantic[0]['sequence'])

 # FASE-004 (T006) opened ADMITTED -> COMPLETE and RECOVERY_ELIGIBLE ->
 # COMPLETE, so the illegal edge this case pins is now the one out of the
 # absorbing BLOCKED state -- the property under test (an illegal run-state
 # jump through transact_with_event blocks and writes nothing) is unchanged.
 def test_transact_with_event_rejects_blocked_to_complete_jump_without_write(self):
  self.register()
  self._gauntlet_transition()
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-blocked'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(state='BLOCKED')}))
  before=tree(self.paths().root)
  def jump(d):
   d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['state']='COMPLETE'; return d
  receipt=GAUNTLET_RECEIPT(name='gauntlet-run-complete-jump')
  with self.assertRaises(store.StoreError) as ctx:
   store.transact_with_event(self.r,jump,event=GAUNTLET_EVENT(receipt),receipt=receipt,now=CLOCK)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE')
  self.assertEqual(tree(self.paths().root),before)

 def test_transition_rejects_forged_receipt_digest_without_any_write(self):
  self.register(); before=tree(self.paths().root); receipt=GAUNTLET_RECEIPT(); event=GAUNTLET_EVENT(receipt)
  event['receipt_sha256']='0'*64
  with self.assertRaises(store.StoreError) as ctx: self._gauntlet_transition(event=event,receipt=receipt)
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
  self.assertEqual(tree(self.paths().root),before)

 def test_receipt_name_collision_with_different_bytes_blocks_and_preserves_first_evidence(self):
  self.register(); self._gauntlet_transition()
  receipt_path=self.paths().receipts/'runtime'/'gauntlet-run-alpha-1.json'
  before=tree(self.paths().root); before_receipt=receipt_path.read_bytes(); before_snapshot=self.paths().orchestrator.read_bytes(); before_events=self.paths().events.read_bytes()
  conflicting=GAUNTLET_RECEIPT(input_sha256='2'*64); event=GAUNTLET_EVENT(conflicting)
  with self.assertRaises(store.StoreError) as ctx: self._gauntlet_transition(event=event,receipt=conflicting)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE')
  self.assertEqual(tree(self.paths().root),before)
  self.assertEqual(receipt_path.read_bytes(),before_receipt)
  self.assertEqual(self.paths().orchestrator.read_bytes(),before_snapshot)
  self.assertEqual(self.paths().events.read_bytes(),before_events)
  next_receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-2')
  self.assertEqual(self._gauntlet_transition(receipt=next_receipt).revision,3)

 def test_concurrent_receipt_collision_has_one_winner_and_leaves_no_wal_residue(self):
  self.register(); barrier=threading.Barrier(2)
  def contend(input_sha256):
   receipt=GAUNTLET_RECEIPT(input_sha256=input_sha256,name='gauntlet-race-receipt')
   event=GAUNTLET_EVENT(receipt)
   def admit(d):
    return {**d,'work_items':{**d['work_items'],'gauntlet-work':{**WORK_ITEM(slug='gauntlet'),'gauntlet':GAUNTLET_BLOCK()}}}
   barrier.wait(timeout=2)
   try: return store.transact_with_event(self.r,admit,event=event,receipt=receipt,now=CLOCK,timeout=2)
   except store.StoreError as exc: return exc
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   results=[future.result(timeout=5) for future in (pool.submit(contend,'3'*64),pool.submit(contend,'4'*64))]
  winners=[result for result in results if isinstance(result,store.Snapshot)]
  losers=[result for result in results if isinstance(result,store.StoreError)]
  self.assertEqual(len(winners),1); self.assertEqual(len(losers),1); self.assertEqual(losers[0].code,'STATE_DIVERGENCE')
  self.assertEqual(winners[0].revision,2)
  paths=self.paths(); after_race=tree(paths.root)
  self.assertFalse((paths.locks/store.PENDING_TRANSITION_NAME).exists())
  self.assertEqual(list(paths.locks.iterdir()),[])
  snapshot=store.read_snapshot(self.r)
  self.assertEqual(snapshot.revision,2); self.assertEqual(tree(paths.root),after_race)
  semantic=[event for event in store.read_events(self.r) if event.get('event')=='gauntlet.run.admitted']
  self.assertEqual(len(semantic),1)
  self.assertIn(json.loads((paths.receipts/'runtime'/'gauntlet-race-receipt.json').read_text(encoding='utf-8')), [GAUNTLET_RECEIPT(input_sha256='3'*64,name='gauntlet-race-receipt'),GAUNTLET_RECEIPT(input_sha256='4'*64,name='gauntlet-race-receipt')])
  next_receipt=GAUNTLET_RECEIPT(input_sha256='5'*64,name='gauntlet-race-after')
  self.assertEqual(self._gauntlet_transition(receipt=next_receipt).revision,3)
  self.assertFalse((paths.locks/store.PENDING_TRANSITION_NAME).exists())
  self.assertEqual(list(paths.locks.iterdir()),[])

 def test_recovery_rejects_pending_candidate_with_transition_sequence_not_owned_by_semantic_event(self):
  class InjectedFault(RuntimeError): pass
  self.register(); before_snapshot=self.paths().orchestrator.read_bytes()
  def interrupt(point):
   if point=='after-event': raise InjectedFault(point)
  with self.assertRaises(InjectedFault): self._gauntlet_transition(fault=interrupt)
  pending=self.paths().locks/store.PENDING_TRANSITION_NAME
  intent=json.loads(pending.read_text(encoding='utf-8'))
  run=intent['candidate']['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']
  run['last_transition']['event_sequence']+=1
  intent['candidate'].pop('content_sha256',None)
  intent['candidate']['content_sha256']=store.content_hash(intent['candidate'])
  pending.write_bytes(store.jcs(intent)+b'\n')
  before_events=self.paths().events.read_bytes()
  with self.assertRaises(store.StoreError) as ctx: store.recover_pending_transition(self.r,now=CLOCK)
  self.assertEqual(ctx.exception.code,'STORE_RECOVERY_REQUIRED')
  self.assertEqual(self.paths().orchestrator.read_bytes(),before_snapshot)
  self.assertEqual(self.paths().events.read_bytes(),before_events)
  self.assertEqual(store.read_snapshot(self.r).revision,1)

 def test_recovery_rejects_pending_candidate_with_illegal_admitted_to_complete_jump(self):
  class InjectedFault(RuntimeError): pass
  self.register(); before_snapshot=self.paths().orchestrator.read_bytes()
  def interrupt(point):
   if point=='after-event': raise InjectedFault(point)
  with self.assertRaises(InjectedFault): self._gauntlet_transition(fault=interrupt)
  pending=self.paths().locks/store.PENDING_TRANSITION_NAME; intent=json.loads(pending.read_text(encoding='utf-8'))
  intent['candidate']['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['state']='COMPLETE'
  intent['candidate'].pop('content_sha256',None); intent['candidate']['content_sha256']=store.content_hash(intent['candidate'])
  pending.write_bytes(store.jcs(intent)+b'\n'); before_events=self.paths().events.read_bytes()
  with self.assertRaises(store.StoreError) as ctx: store.recover_pending_transition(self.r,now=CLOCK)
  self.assertEqual(ctx.exception.code,'STORE_RECOVERY_REQUIRED')
  self.assertEqual(self.paths().orchestrator.read_bytes(),before_snapshot)
  self.assertEqual(self.paths().events.read_bytes(),before_events)
  self.assertEqual(store.read_snapshot(self.r).revision,1)

 def test_transact_with_event_rejects_existing_admission_config_and_base_drift_without_write(self):
  self.register(); self._gauntlet_transition()
  before=tree(self.paths().root)
  def config_drift(d):
   d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['admission']['config_sha256']='9'*64; return d
  config_receipt=GAUNTLET_RECEIPT(name='gauntlet-config-drift')
  with self.assertRaises(store.StoreError) as ctx:
   store.transact_with_event(self.r,config_drift,event=GAUNTLET_EVENT(config_receipt),receipt=config_receipt,now=CLOCK)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(tree(self.paths().root),before)
  def base_drift(d):
   d['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['admission']['base_commit']='9'*40; return d
  base_receipt=GAUNTLET_RECEIPT(name='gauntlet-base-drift',base_commit='9'*40)
  with self.assertRaises(store.StoreError) as ctx:
   store.transact_with_event(self.r,base_drift,event=GAUNTLET_EVENT(base_receipt),receipt=base_receipt,now=CLOCK)
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(tree(self.paths().root),before)

 def test_recovery_of_malformed_pending_wal_is_named_and_never_rewrites_evidence(self):
  class InjectedFault(RuntimeError): pass
  self.register()
  def interrupt(point):
   if point=='after-intent': raise InjectedFault(point)
  with self.assertRaises(InjectedFault): self._gauntlet_transition(fault=interrupt)
  pending=self.paths().locks/store.PENDING_TRANSITION_NAME
  pending.write_bytes(b'{"schema":')
  before=tree(self.paths().root)
  with self.assertRaises(store.StoreError) as ctx: store.recover_pending_transition(self.r,now=CLOCK)
  self.assertEqual(ctx.exception.code,'STORE_RECOVERY_REQUIRED')
  self.assertEqual(tree(self.paths().root),before)
  self.assertEqual(pending.read_bytes(),b'{"schema":')

 def test_wal_recovery_is_deterministic_at_every_receipt_event_anchor_snapshot_and_intent_boundary(self):
  class InjectedFault(RuntimeError): pass
  # Before semantic evidence exists, recovery may only abandon the intent;
  # after it exists, it must finish the exact candidate rather than creating a
  # second event/receipt/revision.  Receipt-before-event is intentionally
  # non-authoritative diagnostic residue.
  expected_published={'after-intent':False,'after-receipt':False,'after-event':True,'after-anchor':True,'after-snapshot':True,'after-intent-removal':True}
  for boundary,published in expected_published.items():
   with self.subTest(boundary=boundary):
    self.tearDown(); self.setUp(); self.register(); before=self.paths().orchestrator.read_bytes()
    def interrupt(reached,b=boundary):
     if reached==b: raise InjectedFault(b)
    with self.assertRaises(InjectedFault): self._gauntlet_transition(fault=interrupt)
    recovered=store.recover_pending_transition(self.r,now=CLOCK)
    snapshot=store.read_snapshot(self.r)
    self.assertEqual(snapshot.revision,2 if published else 1)
    self.assertEqual('gauntlet-work' in snapshot.document['work_items'],published)
    semantic=[event for event in store.read_events(self.r) if event.get('event')=='gauntlet.run.admitted']
    self.assertEqual(len(semantic),1 if published else 0)
    if not published: self.assertEqual(self.paths().orchestrator.read_bytes(),before)
    # Recovery is idempotent and cannot manufacture another transition.
    again=store.recover_pending_transition(self.r,now=CLOCK)
    self.assertEqual((again.revision,store.read_snapshot(self.r).revision),(snapshot.revision,snapshot.revision))

 # --- FASE-003 Phase 1 (T001): per-wave lifecycle -------------------------
 def test_wave_lifecycle_declared_active_complete_is_accepted(self):
  self.register(); self._gauntlet_transition()
  active=GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':DEFAULT_WAVE_NODE_IDS}})
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-2'),block=GAUNTLET_BLOCK({'run-alpha-1':active}))
  complete=GAUNTLET_RUN(waves={'wave-0001':{'state':'COMPLETE','node_ids':DEFAULT_WAVE_NODE_IDS}})
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-3'),block=GAUNTLET_BLOCK({'run-alpha-1':complete}))
  self.assertEqual(written.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['waves']['wave-0001']['state'],'COMPLETE')

 def test_wave_skip_or_backward_transition_is_rejected(self):
  self.register(); self._gauntlet_transition(); before=self.paths().orchestrator.read_bytes()
  skip=GAUNTLET_RUN(waves={'wave-0001':{'state':'COMPLETE','node_ids':DEFAULT_WAVE_NODE_IDS}})
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-skip'),block=GAUNTLET_BLOCK({'run-alpha-1':skip}))
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  active=GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':DEFAULT_WAVE_NODE_IDS}})
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-active'),block=GAUNTLET_BLOCK({'run-alpha-1':active}))
  complete=GAUNTLET_RUN(waves={'wave-0001':{'state':'COMPLETE','node_ids':DEFAULT_WAVE_NODE_IDS}})
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-complete'),block=GAUNTLET_BLOCK({'run-alpha-1':complete}))
  before2=self.paths().orchestrator.read_bytes()
  backward=GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':DEFAULT_WAVE_NODE_IDS}})
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-backward'),block=GAUNTLET_BLOCK({'run-alpha-1':backward}))
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before2)

 def test_wave_map_growth_adds_a_new_wave_id(self):
  self.register(); self._gauntlet_transition()
  grown=GAUNTLET_RUN(waves={'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS},'wave-0002':{'state':'DECLARED','node_ids':['n2']}})
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-grow'),block=GAUNTLET_BLOCK({'run-alpha-1':grown}))
  self.assertEqual(sorted(written.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['waves']),['wave-0001','wave-0002'])

 def test_removing_an_existing_wave_id_is_rejected(self):
  self.register(); self._gauntlet_transition()
  grown=GAUNTLET_RUN(waves={'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS},'wave-0002':{'state':'DECLARED','node_ids':['n2']}})
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-grow'),block=GAUNTLET_BLOCK({'run-alpha-1':grown}))
  before=self.paths().orchestrator.read_bytes()
  shrunk=GAUNTLET_RUN(waves={'wave-0002':{'state':'DECLARED','node_ids':['n2']}})
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-shrink',wave_id='wave-0002'),block=GAUNTLET_BLOCK({'run-alpha-1':shrunk}))
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_wave_other_than_newest_is_immutable_even_if_not_complete(self):
  # "Superseded" means "not the run's current/newest wave," not "not
  # COMPLETE": wave-0001 stays immutable the moment wave-0002 exists, even
  # though wave-0001 -> COMPLETE is, on its own, a perfectly legal edge.
  self.register(); self._gauntlet_transition()
  active=GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':DEFAULT_WAVE_NODE_IDS}})
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-active'),block=GAUNTLET_BLOCK({'run-alpha-1':active}))
  grown=GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':DEFAULT_WAVE_NODE_IDS},'wave-0002':{'state':'DECLARED','node_ids':['n2']}})
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-grow'),block=GAUNTLET_BLOCK({'run-alpha-1':grown}))
  before=self.paths().orchestrator.read_bytes()
  superseded_touch=GAUNTLET_RUN(waves={'wave-0001':{'state':'COMPLETE','node_ids':DEFAULT_WAVE_NODE_IDS},'wave-0002':{'state':'DECLARED','node_ids':['n2']}})
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-superseded'),block=GAUNTLET_BLOCK({'run-alpha-1':superseded_touch}))
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  newest_advances=GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':DEFAULT_WAVE_NODE_IDS},'wave-0002':{'state':'ACTIVE','node_ids':['n2']}})
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-newest-advance'),block=GAUNTLET_BLOCK({'run-alpha-1':newest_advances}))
  self.assertEqual(written.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['waves']['wave-0002']['state'],'ACTIVE')

 # --- FASE-003 (B5 fix): wave node_ids is a real, required, immutable -----
 # field -- reverting the journal-scan substitution that made a wave member
 # with no worker declared yet invisible to wave-completion detection.
 def test_wave_node_ids_is_required(self):
  self.register(); before=self.paths().orchestrator.read_bytes()
  missing=GAUNTLET_RUN(waves={'wave-0001':{'state':'DECLARED'}})
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':missing}))
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_wave_node_ids_must_be_non_empty_unique_and_safe(self):
  self.register(); before=self.paths().orchestrator.read_bytes()
  bad=(
   {'wave-0001':{'state':'DECLARED','node_ids':[]}},
   {'wave-0001':{'state':'DECLARED','node_ids':['n1','n1']}},
   {'wave-0001':{'state':'DECLARED','node_ids':['../escape']}},
   {'wave-0001':{'state':'DECLARED','node_ids':[1]}},
   {'wave-0001':{'state':'DECLARED','node_ids':'n1'}},
  )
  for waves in bad:
   with self.subTest(waves=waves):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves)}))
    self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_wave_declared_placeholder_node_ids_may_change_once_on_its_own_activation(self):
  # The coordinator mints wave-0001 as a DECLARED placeholder with no real
  # membership at admission (every store.transact_with_event call, this
  # one included, must name an existing wave_id to correlate to); the one
  # legitimate node_ids change is exactly this DECLARED -> * transition,
  # when a wave's real membership becomes known for the first time.
  self.register(); self._gauntlet_transition()
  activated=GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':['real-member']}})
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-activate'),block=GAUNTLET_BLOCK({'run-alpha-1':activated}))
  self.assertEqual(written.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['waves']['wave-0001']['node_ids'],['real-member'])

 def test_wave_node_ids_is_immutable_once_activated(self):
  self.register(); self._gauntlet_transition()
  activated=GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':['real-member']}})
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-activate'),block=GAUNTLET_BLOCK({'run-alpha-1':activated}))
  before=self.paths().orchestrator.read_bytes()
  # A legal state edge (ACTIVE -> COMPLETE) paired with a changed node_ids
  # list must still be rejected: node_ids is immutable once a wave has left
  # the DECLARED placeholder state.
  changed=GAUNTLET_RUN(waves={'wave-0001':{'state':'COMPLETE','node_ids':['different']}})
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-node-ids-changed'),block=GAUNTLET_BLOCK({'run-alpha-1':changed}))
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 # --- FASE-003 Phase 1 (T001): non-terminal worker-cap counting -----------
 def test_worker_cap_counts_only_non_terminal_workers(self):
  self.register()
  five={f'worker-{i}':GAUNTLET_WORKER(f'worker-{i}') for i in range(5)}
  self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=five)}))
  preparing={**five,'worker-3':GAUNTLET_WORKER('worker-3',state='PREPARING'),'worker-4':GAUNTLET_WORKER('worker-4',state='PREPARING')}
  self._advance_workers(preparing,'gauntlet-run-alpha-2')
  prepared={**preparing,'worker-3':GAUNTLET_WORKER('worker-3',state='PREPARED'),'worker-4':GAUNTLET_WORKER('worker-4',state='PREPARED')}
  self._advance_workers(prepared,'gauntlet-run-alpha-3')
  terminal={**prepared,'worker-3':GAUNTLET_WORKER('worker-3',state='TERMINAL'),'worker-4':GAUNTLET_WORKER('worker-4',state='FAILED')}
  self._advance_workers(terminal,'gauntlet-run-alpha-4')
  # worker-0,1,2 DECLARED (non-terminal); worker-3 TERMINAL, worker-4 FAILED
  # (terminal) -- 3 of 5 are non-terminal, so a 6th non-terminal worker still
  # fits under the cap even though the total worker count becomes 6.
  grown={**terminal,'worker-5':GAUNTLET_WORKER('worker-5')}
  written=self._advance_workers(grown,'gauntlet-run-alpha-5')
  self.assertEqual(len(written.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['workers']),6)

 def test_worker_cap_rejects_a_sixth_when_five_are_non_terminal(self):
  self.register()
  five={f'worker-{i}':GAUNTLET_WORKER(f'worker-{i}') for i in range(5)}
  self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=five)}))
  before=self.paths().orchestrator.read_bytes()
  six={**five,'worker-5':GAUNTLET_WORKER('worker-5')}
  with self.assertRaises(store.StoreError) as ctx:
   self._advance_workers(six,'gauntlet-run-alpha-2')
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 # --- FASE-003 Phase 1 (T001): node_id/remediates schema and budget -------
 def test_worker_record_requires_node_id_and_remediates_keys(self):
  self.register(); before=self.paths().orchestrator.read_bytes()
  missing_both={'worker-a':{'state':'DECLARED','lease':None,'grant':None,'workspace':None}}
  missing_remediates={'worker-a':{'state':'DECLARED','lease':None,'grant':None,'workspace':None,'node_id':'worker-a'}}
  missing_node_id={'worker-a':{'state':'DECLARED','lease':None,'grant':None,'workspace':None,'remediates':None}}
  for workers in (missing_both,missing_remediates,missing_node_id):
   with self.subTest(workers=workers):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=workers)}))
    self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_node_id_must_match_worker_id_with_remediation_suffix_stripped(self):
  self.register(); before=self.paths().orchestrator.read_bytes()
  bad=(
   {'worker-a':GAUNTLET_WORKER('worker-a',node_id='worker-b')},
   {'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-a-r1')},
   {'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-b')},
  )
  for workers in bad:
   with self.subTest(workers=workers):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=workers)}))
    self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  ok={'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-a')}
  written=self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=ok)}))
  self.assertEqual(written.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['workers']['worker-a-r1']['node_id'],'worker-a')

 def test_remediates_must_name_an_existing_sibling(self):
  self.register(); before=self.paths().orchestrator.read_bytes()
  workers={'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-a',lease=GAUNTLET_LEASE(recovery_count=1),remediates='worker-a')}
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=workers)}))
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_remediates_sibling_node_id_must_match(self):
  self.register(); before=self.paths().orchestrator.read_bytes()
  workers={
   'worker-a':GAUNTLET_WORKER('worker-a'),
   'worker-b-r1':GAUNTLET_WORKER('worker-b-r1',node_id='worker-b',lease=GAUNTLET_LEASE(lease_id='lease-b',recovery_count=1),remediates='worker-a'),
  }
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=workers)}))
  self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_remediates_and_recovery_count_must_agree(self):
  self.register(); before=self.paths().orchestrator.read_bytes()
  null_remediates_spent_lease={'worker-a':GAUNTLET_WORKER('worker-a',lease=GAUNTLET_LEASE(recovery_count=1),remediates=None)}
  set_remediates_fresh_lease={
   'worker-a':GAUNTLET_WORKER('worker-a'),
   'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-a',lease=GAUNTLET_LEASE(lease_id='lease-b',recovery_count=0),remediates='worker-a'),
  }
  for workers in (null_remediates_spent_lease,set_remediates_fresh_lease):
   with self.subTest(workers=workers):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=workers)}))
    self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_remediates_and_recovery_count_valid_pairs_are_accepted(self):
  self.register()
  fresh={'worker-a':GAUNTLET_WORKER('worker-a',lease=GAUNTLET_LEASE(recovery_count=0),remediates=None)}
  written=self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=fresh)}))
  self.assertIsNone(written.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['workers']['worker-a']['remediates'])
  remediated={
   'worker-a':GAUNTLET_WORKER('worker-a',lease=GAUNTLET_LEASE(recovery_count=0),remediates=None),
   'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-a',lease=GAUNTLET_LEASE(lease_id='lease-b',recovery_count=1),remediates='worker-a'),
  }
  written2=self._advance_workers(remediated,'gauntlet-run-alpha-2')
  self.assertEqual(written2.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['workers']['worker-a-r1']['remediates'],'worker-a')
  self.assertEqual(written2.document['work_items']['gauntlet-work']['gauntlet']['runs']['run-alpha-1']['workers']['worker-a-r1']['lease']['recovery_count'],1)

 # --- FASE-003 (B6 fix, FR-008(e)): Store-level defense-in-depth for the
 # shared per-node remediation budget -- independent of remediate_node's own
 # application-level scan, and independent of what a caller's `remediates`
 # value claims.  Both cases go through raw store.transact_with_event calls,
 # exactly the "bypassing remediate_node entirely" reproduction the review
 # used, never through gauntlet_runs.remediate_node itself.
 def test_store_rejects_fresh_budget_mint_for_an_already_seen_node_id(self):
  self.register()
  original={'worker-a':GAUNTLET_WORKER('worker-a',lease=GAUNTLET_LEASE(recovery_count=0),remediates=None)}
  self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=original)}))
  before=self.paths().orchestrator.read_bytes()
  # worker-a-r1 satisfies every PER-RECORD check in isolation (remediates
  # names a real sibling with a matching node_id) but is minted with a
  # FRESH budget (recovery_count=0) for a node_id ("worker-a") that already
  # has a worker record -- exactly the Store-level gap B6 closes.
  fresh_mint={
   **original,
   'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-a',lease=GAUNTLET_LEASE(lease_id='lease-fresh',recovery_count=0),remediates=None),
  }
  with self.assertRaises(store.StoreError) as ctx:
   self._advance_workers(fresh_mint,'gauntlet-run-alpha-fresh-mint')
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_store_rejects_chained_second_remediation_for_an_already_spent_node_id(self):
  self.register()
  spent={
   'worker-a':GAUNTLET_WORKER('worker-a',lease=GAUNTLET_LEASE(recovery_count=0),remediates=None),
   'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-a',lease=GAUNTLET_LEASE(lease_id='lease-b',recovery_count=1),remediates='worker-a'),
  }
  self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=spent)}))
  before=self.paths().orchestrator.read_bytes()
  # worker-a-r2 remediates worker-a-r1 (a real sibling with a matching
  # node_id) and is itself minted already-spent (recovery_count=1) -- every
  # PER-RECORD check passes.  The node's one shared budget (FR-007/ADR-0015)
  # was already spent by worker-a-r1; a chained second remediation must
  # still be refused by the Store itself, regardless of what remediates
  # claims and regardless of remediate_node's own application-level scan
  # (bypassed here entirely via a raw transact_with_event call).
  chained={
   **spent,
   'worker-a-r2':GAUNTLET_WORKER('worker-a-r2',node_id='worker-a',lease=GAUNTLET_LEASE(lease_id='lease-c',recovery_count=1),remediates='worker-a-r1'),
  }
  with self.assertRaises(store.StoreError) as ctx:
   self._advance_workers(chained,'gauntlet-run-alpha-chained')
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 # --- F3 fix: the B6 budget-lineage scan must also see NEW worker records
 # added together in the SAME transaction, not only already-committed
 # (old_workers) siblings -- otherwise two remediation-shaped records for
 # one node minted in a single transact_with_event call each see only the
 # pre-transaction state and never each other, double-spending the node's
 # one shared budget within one commit.
 def test_store_rejects_two_new_remediation_records_for_the_same_node_in_one_transaction(self):
  self.register()
  original={'worker-a':GAUNTLET_WORKER('worker-a',lease=GAUNTLET_LEASE(recovery_count=0),remediates=None)}
  self._gauntlet_transition(block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(workers=original)}))
  before=self.paths().orchestrator.read_bytes()
  # worker-a-r1 (remediates worker-a) and worker-a-r2 (remediates
  # worker-a-r1) are BOTH introduced together in this one transaction.
  # Each is individually valid against the pre-transaction (old_workers)
  # state alone -- neither is already committed -- so a scan scoped to
  # old_workers only would miss that the two new siblings jointly spend
  # the node's one shared budget twice.
  double_spend={
   **original,
   'worker-a-r1':GAUNTLET_WORKER('worker-a-r1',node_id='worker-a',lease=GAUNTLET_LEASE(lease_id='lease-b',recovery_count=1),remediates='worker-a'),
   'worker-a-r2':GAUNTLET_WORKER('worker-a-r2',node_id='worker-a',lease=GAUNTLET_LEASE(lease_id='lease-c',recovery_count=1),remediates='worker-a-r1'),
  }
  with self.assertRaises(store.StoreError) as ctx:
   self._advance_workers(double_spend,'gauntlet-run-alpha-double-spend')
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 # --- F4 fix: a wave_id present only in the candidate (never in
 # old_waves) must be rejected unless it is exactly the run's current
 # newest wave's immediate sequential successor -- otherwise an injected
 # wave whose id sorts higher than any real wave corrupts every
 # max(waves)-style "newest wave" computation, wedging the real sequence.
 def test_wave_out_of_order_id_injection_is_rejected(self):
  self.register(); self._gauntlet_transition()
  before=self.paths().orchestrator.read_bytes()
  # Only wave-0001 exists; wave-0003 skips ahead of the real next id
  # (wave-0002), exactly the gap/out-of-order injection this closes.
  injected=GAUNTLET_RUN(waves={'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS},'wave-0003':{'state':'DECLARED','node_ids':['n2']}})
  with self.assertRaises(store.StoreError) as ctx:
   self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-alpha-injected'),block=GAUNTLET_BLOCK({'run-alpha-1':injected}))
  self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE'); self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 # --- FASE-004 Phase 1 (T001): the run's terminal lifecycle, its two new
 # optional write-once fields, and the wave's conflict/convergence records --
 def test_run_admitted_to_complete_is_accepted(self):
  self.register(); self._gauntlet_transition()
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-admitted-complete'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(state='COMPLETE')}))
  self.assertEqual(self._run(written)['state'],'COMPLETE')

 def test_run_recovery_eligible_to_complete_is_accepted(self):
  self.register(); self._gauntlet_transition()
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-eligible'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(state='RECOVERY_ELIGIBLE')}))
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-run-eligible-complete'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(state='COMPLETE')}))
  self.assertEqual(self._run(written)['state'],'COMPLETE')

 def test_run_dag_content_sha256_is_optional_and_hex64(self):
  self.register(); self._gauntlet_transition(); before=self.paths().orchestrator.read_bytes()
  # Bare 64-hex, the same shape every other *_sha256 field of this block
  # already carries -- never the "sha256:" prefixed form project_id uses.
  for index,pin in enumerate(('not-a-hash','sha256:'+'a'*64,'A'*64,'a'*63,123,None)):
   with self.subTest(pin=pin):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-pin-bad-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':{**GAUNTLET_RUN(),'dag_content_sha256':pin}}))
    self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-pin'),block=GAUNTLET_BLOCK({'run-alpha-1':{**GAUNTLET_RUN(),'dag_content_sha256':'a'*64}}))
  self.assertEqual(self._run(written)['dag_content_sha256'],'a'*64)

 def test_run_dag_content_sha256_is_write_once(self):
  self.register(); self._gauntlet_transition()
  pinned={**GAUNTLET_RUN(),'dag_content_sha256':'a'*64}
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-pin'),block=GAUNTLET_BLOCK({'run-alpha-1':pinned}))
  carried=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-pin-carried'),block=GAUNTLET_BLOCK({'run-alpha-1':pinned}))
  self.assertEqual(self._run(carried)['dag_content_sha256'],'a'*64)
  before=self.paths().orchestrator.read_bytes()
  for index,run in enumerate(({**GAUNTLET_RUN(),'dag_content_sha256':'b'*64},GAUNTLET_RUN())):
   with self.subTest(run=run):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-pin-rewrite-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':run}))
    self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_run_abandon_authorization_is_optional_and_write_once(self):
  self.register(); self._gauntlet_transition(); before=self.paths().orchestrator.read_bytes()
  for index,bad in enumerate(('not-an-object',[],None)):
   with self.subTest(bad=bad):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-abandon-bad-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':{**GAUNTLET_RUN(),'abandon_authorization':bad}}))
    self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  bundle=HUMAN_AUTHORIZATION()
  abandoned={**GAUNTLET_RUN(state='BLOCKED'),'abandon_authorization':bundle}
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-abandon'),block=GAUNTLET_BLOCK({'run-alpha-1':abandoned}))
  self.assertEqual(self._run(written)['abandon_authorization'],bundle)
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-abandon-carried'),block=GAUNTLET_BLOCK({'run-alpha-1':abandoned}))
  before=self.paths().orchestrator.read_bytes()
  divergent={**GAUNTLET_RUN(state='BLOCKED'),'abandon_authorization':HUMAN_AUTHORIZATION(authorized_by='someone-else@example.invalid')}
  for index,run in enumerate((divergent,GAUNTLET_RUN(state='BLOCKED'))):
   with self.subTest(run=run):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-abandon-rewrite-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':run}))
    self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_wave_last_conflict_is_optional_and_round_trips(self):
  self.register(); self._gauntlet_transition()
  for index,reason in enumerate(('scope-overlap','content-conflict')):
   conflict=LAST_CONFLICT(reason=reason)
   waves={'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS,'last_conflict':conflict}}
   written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-conflict-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves)}))
   self.assertEqual(self._run(written)['waves']['wave-0001']['last_conflict'],conflict)
  # Absence is the "resolved" signal (FR-011), so the field must be removable.
  cleared=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-conflict-cleared'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN()}))
  self.assertNotIn('last_conflict',self._run(cleared)['waves']['wave-0001'])

 def test_wave_last_conflict_shape_is_validated(self):
  self.register(); self._gauntlet_transition(); before=self.paths().orchestrator.read_bytes()
  bad=(
   'not-an-object',
   {key:value for key,value in LAST_CONFLICT().items() if key!='reason'},
   {**LAST_CONFLICT(),'unknown':True},
   LAST_CONFLICT(node_ids=[]),
   LAST_CONFLICT(node_ids=['../escape']),
   LAST_CONFLICT(node_ids=['n1','n1']),
   LAST_CONFLICT(node_ids='n1'),
   LAST_CONFLICT(reason='merge-conflict'),
   LAST_CONFLICT(execution_branch_head='1'*39),
   LAST_CONFLICT(execution_branch_head=None),
   LAST_CONFLICT(worker_heads={'n1':'2'*39}),
   LAST_CONFLICT(worker_heads=['n1']),
  )
  for index,conflict in enumerate(bad):
   with self.subTest(conflict=conflict):
    waves={'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS,'last_conflict':conflict}}
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-conflict-bad-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves)}))
    self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_wave_converged_is_a_strict_boolean(self):
  self.register(); self._gauntlet_transition(); before=self.paths().orchestrator.read_bytes()
  for index,value in enumerate((1,0,'true',None,[])):
   with self.subTest(value=value):
    waves={'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS,'converged':value}}
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-converged-bad-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves)}))
    self.assertEqual(ctx.exception.code,'ORCHESTRATOR_INVALID')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)
  waves={'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS,'converged':True}}
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-converged'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves)}))
  self.assertIs(self._run(written)['waves']['wave-0001']['converged'],True)

 def test_wave_converged_is_write_once(self):
  self.register(); self._gauntlet_transition()
  converged={'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS,'converged':True}}
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-converged'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=converged)}))
  carried=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-converged-carried'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=converged)}))
  self.assertIs(self._run(carried)['waves']['wave-0001']['converged'],True)
  before=self.paths().orchestrator.read_bytes()
  rewrites=(
   {'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS,'converged':False}},
   {'wave-0001':{'state':'DECLARED','node_ids':DEFAULT_WAVE_NODE_IDS}},
  )
  for index,waves in enumerate(rewrites):
   with self.subTest(waves=waves):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-converged-rewrite-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves)}))
    self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)

 def test_superseded_wave_permits_only_last_conflict_and_converged_to_differ(self):
  # ADR-0022: wave N+1 may legitimately be declared while wave N's conflict
  # is still open, so those two fields -- and only those two -- stay mutable
  # on a wave the run has already superseded.
  self.register(); self._gauntlet_transition()
  def waves(first,second={'state':'ACTIVE','node_ids':['n2']}): return {'wave-0001':first,'wave-0002':second}
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-superseded-activate'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves={'wave-0001':{'state':'ACTIVE','node_ids':['n1']}})}))
  self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-superseded-grow'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves({'state':'ACTIVE','node_ids':['n1']}))}))
  conflict=LAST_CONFLICT()
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-superseded-conflict'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves({'state':'ACTIVE','node_ids':['n1'],'last_conflict':conflict}))}))
  self.assertEqual(self._run(written)['waves']['wave-0001']['last_conflict'],conflict)
  written=self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name='gauntlet-superseded-resolved'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=waves({'state':'ACTIVE','node_ids':['n1'],'converged':True}))}))
  superseded=self._run(written)['waves']['wave-0001']
  self.assertNotIn('last_conflict',superseded); self.assertIs(superseded['converged'],True)
  before=self.paths().orchestrator.read_bytes()
  rejected=(
   waves({'state':'COMPLETE','node_ids':['n1'],'converged':True}),
   waves({'state':'ACTIVE','node_ids':['different'],'converged':True}),
  )
  for index,candidate in enumerate(rejected):
   with self.subTest(candidate=candidate):
    with self.assertRaises(store.StoreError) as ctx:
     self._gauntlet_transition(receipt=GAUNTLET_RECEIPT(name=f'gauntlet-superseded-bad-{index}'),block=GAUNTLET_BLOCK({'run-alpha-1':GAUNTLET_RUN(waves=candidate)}))
    self.assertEqual(ctx.exception.code,'STATE_DIVERGENCE')
   self.assertEqual(self.paths().orchestrator.read_bytes(),before)

if __name__=='__main__': unittest.main()
