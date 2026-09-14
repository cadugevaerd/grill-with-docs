#!/usr/bin/env python3
"""Contract smoke matrix for the persistent eleven-step checkpoint ledger."""
import base64, concurrent.futures, hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
PLUGIN=REPO/'plugin'
SCRIPT=PLUGIN/'skills/grill-with-docs/scripts/grill_workspace.py'
TEMPLATE=PLUGIN/'skills/grill-with-docs/assets/WORKFLOW.template.md'
sys.path.insert(0, str(PLUGIN/'skills/grill-with-docs/scripts'))
from grill_core import agent_orchestration as contract
from grill_core import store
STEPS = ["specify", "plan", "checklist", "tasks", "analyze", "partition", "implement-parallel", "converge", "verify", "review", "ship"]

def run(*a):
 a=tuple(a)
 if a and a[0] in {"init","preflight","gauntlet-init"} and "--runtime" not in a: a += ("--runtime","claude")
 if a and a[0] == "init" and "--session-ref" not in a: a += ("--session-ref", "session-1")
 return subprocess.run([sys.executable,str(SCRIPT),*map(str,a)],text=True,capture_output=True)
class CheckpointContract(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.r=Path(self.t.name); subprocess.run(['git','init','-q','-b','main',str(self.r)],check=True); (self.r/'WORKFLOW.md').write_bytes(TEMPLATE.read_bytes())
  subprocess.run(['git','-C',str(self.r),'add','.'],check=True); subprocess.run(['git','-C',str(self.r),'config','user.email','t@e']); subprocess.run(['git','-C',str(self.r),'config','user.name','t']); subprocess.run(['git','-C',str(self.r),'commit','-qm','init']);
  self.assertEqual(run('init',self.r,'--type','feature','--slug','x','--work-id','wx','--skip-backlog').returncode,0); (self.r/'e').write_text('e')
 def tearDown(self): self.t.cleanup()
 def call(self,step,state,**kw):
  a=['checkpoint',self.r,'--work-id','wx','--step',step,'--state',state]
  a += ['--operation-id',f'{step}-{state}','--session-ref','session-1']
  for x in kw.get('evidence',[]): a += ['--evidence',x]
  if 'reason' in kw: a += ['--reason',kw['reason']]
  return run(*a)
 def test_full_matrix_persists(self):
  for s in STEPS:
   self.assertEqual(self.call(s,'in-progress').returncode,0,s)
   self.assertEqual(self.call(s,'complete',evidence=['e']).returncode,0,s)
  d=json.loads((self.r/'.grill/work-items/wx/state.json').read_text()); self.assertTrue(all(d['development']['steps'][s]=='complete' for s in STEPS)); self.assertEqual(d['development']['current_step'],'complete')
 def test_skip_and_evidence_and_block_reason(self):
  self.assertNotEqual(self.call('plan','in-progress').returncode,0); self.assertNotEqual(self.call('specify','complete').returncode,0); self.assertNotEqual(self.call('specify','blocked').returncode,0)
  self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','blocked',reason='wait').returncode,0); self.assertEqual(self.call('specify','in-progress').returncode,0)
 def test_reused_and_divergence(self):
  self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(self.call('specify','in-progress',reason='different').returncode,2)
 def test_skip_is_invalid_transition(self): self.assertEqual(self.call('plan','in-progress').returncode,2)
 def test_complete_without_evidence_is_required(self): self.assertEqual(self.call('specify','in-progress').returncode,0); self.assertEqual(json.loads(self.call('specify','complete').stdout)['code'],'EVIDENCE-REQUIRED')
 def test_missing_evidence_code(self): self.assertEqual(json.loads(self.call('specify','in-progress').stdout)['verdict'],'UPDATED'); self.assertEqual(json.loads(self.call('specify','complete',evidence=['missing']).stdout)['code'],'EVIDENCE-MISSING')
 def test_directory_evidence_rejected(self): (self.r/'dir').mkdir(); self.call('specify','in-progress'); self.assertEqual(json.loads(self.call('specify','complete',evidence=['dir']).stdout)['code'],'EVIDENCE-NOT-REGULAR')
 def test_blocked_requires_reason(self): self.call('specify','in-progress'); self.assertEqual(json.loads(self.call('specify','blocked').stdout)['code'],'REASON-REQUIRED')
 def test_blocked_retry(self): self.call('specify','in-progress'); self.call('specify','blocked',reason='wait'); self.assertEqual(self.call('specify','in-progress').returncode,0)
 def test_bound_branch_rejects_complete_and_blocked_without_writing(self):
  subprocess.run(['git','-C',str(self.r),'checkout','-qb','011-gauntlet-loop'],check=True)
  self.assertEqual(self.call('specify','in-progress').returncode,0)
  subprocess.run(['git','-C',str(self.r),'checkout','-qb','wrong-branch'],check=True)
  state=self.r/'.grill/work-items/wx/state.json'; before=(state.read_bytes(),state.stat().st_mtime_ns)
  for requested in (self.call('specify','complete',evidence=['e']),self.call('specify','blocked',reason='wait')):
   payload=json.loads(requested.stdout)
   self.assertEqual((requested.returncode,payload['verdict'],payload['code']),(2,'BLOCKED','EXECUTION-BRANCH-MISMATCH'))
   self.assertEqual((state.read_bytes(),state.stat().st_mtime_ns),before)
   self.assertFalse((self.r/'.grill/work-items/wx.lock').exists())
 def test_reused_includes_evidence_and_reason(self): self.call('specify','in-progress'); self.call('specify','complete',evidence=['e'],reason='done'); p=self.call('specify','complete',evidence=['e'],reason='done'); self.assertEqual(json.loads(p.stdout)['verdict'],'REUSED')
 def test_divergent_same_state_is_exit_two(self): self.call('specify','in-progress'); p=self.call('specify','in-progress',reason='different'); self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout)['code'],'STATE-DIVERGENCE')
 def test_current_step_first_pending(self): self.call('specify','in-progress'); p=self.call('specify','complete',evidence=['e']); self.assertEqual(json.loads(p.stdout)['current_step'],'plan')
 def test_ship_gate(self):
  for s in STEPS[:-1]: self.call(s,'in-progress'); self.call(s,'complete',evidence=['e'])
  self.assertEqual(json.loads(self.call('ship','complete',evidence=['e']).stdout)['code'],'INVALID-TRANSITION')
 def test_review_blocked_makes_ship_unreachable(self):
  # FASE-004 User Story 2 / plan.md T017: review is dispatched exactly like
  # any other of the eleven macro-steps -- a `blocked` review checkpoint
  # already halts `ship` via this unmodified step-sequence gate, no new
  # mechanism.
  for s in STEPS[:-2]: self.call(s,'in-progress'); self.call(s,'complete',evidence=['e'])
  self.call('review','in-progress'); self.call('review','blocked',reason='reprovado')
  self.assertEqual(json.loads(self.call('ship','in-progress').stdout)['code'],'INVALID-TRANSITION')
 def test_invalid_step_json(self): p=run('checkpoint',self.r,'--work-id','wx','--step','bad','--state','in-progress'); self.assertEqual(len(p.stdout.splitlines()),1); self.assertEqual(p.stderr,'')
 def test_legacy_requires_explicit_initialization(self): (self.r/'.grill/work-items/wx/state.json').write_text('{}'); p=self.call('specify','in-progress'); self.assertEqual(json.loads(p.stdout)['code'],'LEGACY-UNTRACKED')
 def test_legacy_initialization_requires_from_step(self): (self.r/'.grill/work-items/wx/state.json').write_text('{}'); p=run('checkpoint',self.r,'--work-id','wx','--step','specify','--state','in-progress','--initialize-legacy','--evidence','e','--reason','decide'); self.assertEqual(json.loads(p.stdout)['code'],'LEGACY-INITIALIZATION-REQUIRES-DECISION-EVIDENCE')
 def test_state_unchanged_on_evidence_rejection(self): before=(self.r/'.grill/work-items/wx/state.json').read_bytes(); self.call('specify','in-progress'); before=(self.r/'.grill/work-items/wx/state.json').read_bytes(); self.call('specify','complete',evidence=['missing']); self.assertEqual(before,(self.r/'.grill/work-items/wx/state.json').read_bytes())
 def test_complete_terminal_current_step(self):
  for s in STEPS: self.call(s,'in-progress'); self.call(s,'complete',evidence=['e'])
  self.assertEqual(json.loads((self.r/'.grill/work-items/wx/state.json').read_text())['development']['current_step'],'complete')
 def test_output_contract_all_calls(self):
  p=self.call('specify','in-progress'); self.assertEqual(p.stderr,''); self.assertEqual(len(p.stdout.splitlines()),1); self.assertIsInstance(json.loads(p.stdout),dict)
 def test_invalid_work_id_exact(self):
  p=run('checkpoint',self.r,'--work-id','bad id','--step','specify','--state','in-progress'); self.assertEqual(json.loads(p.stdout)['code'],'INVALID-WORK-ID'); self.assertEqual(p.returncode,2); self.assertEqual(p.stderr,'')
 def test_absolute_evidence_path_exact(self):
  self.call('specify','in-progress'); p=self.call('specify','complete',evidence=[str(self.r/'e')]); self.assertEqual(json.loads(p.stdout)['code'],'INVALID-EVIDENCE-PATH')
 def test_parent_evidence_path_exact(self):
  self.call('specify','in-progress'); p=self.call('specify','complete',evidence=['../e']); self.assertEqual(json.loads(p.stdout)['code'],'INVALID-EVIDENCE-PATH')
 def test_invalid_state_is_structured(self):
  p=run('checkpoint',self.r,'--work-id','wx','--step','specify','--state','bogus'); self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout)['code'],'INVALID-ARGUMENTS'); self.assertEqual(p.stderr,'')
 def test_global_snapshot_untouched(self):
  g=self.r/'.grill/global'; g.mkdir(parents=True); q=g/'x'; q.write_text('g'); before=(q.read_bytes(),q.stat().st_mtime_ns); self.call('specify','in-progress'); self.assertEqual(before,(q.read_bytes(),q.stat().st_mtime_ns))
 def test_blocked_requires_exact_reason(self):
  self.call('specify','in-progress'); p=self.call('specify','blocked',reason='   '); self.assertEqual(json.loads(p.stdout)['code'],'REASON-REQUIRED')
 def test_evidence_hash_audited(self):
  self.call('specify','in-progress'); p=self.call('specify','complete',evidence=['e']); self.assertEqual(json.loads(p.stdout)['evidence'][0]['sha256'],__import__('hashlib').sha256(b'e').hexdigest())
 def test_missing_work_item_exact(self):
  p=run('checkpoint',self.r,'--work-id','none','--step','specify','--state','in-progress'); self.assertEqual(json.loads(p.stdout)['code'],'WORK-ITEM-MISSING')
 def test_direct_evidence_symlink_is_blocked_without_state_change(self):
  self.call('specify','in-progress'); state=self.r/'.grill/work-items/wx/state.json'; before=(state.read_bytes(),state.stat().st_mtime_ns)
  outside=Path(self.t.name)/'outside-evidence'; outside.write_text('secret'); (self.r/'e-link').symlink_to(outside)
  p=self.call('specify','complete',evidence=['e-link']); self.assertEqual((p.returncode,json.loads(p.stdout)['code']),(2,'EVIDENCE-SYMLINK')); self.assertEqual(before,(state.read_bytes(),state.stat().st_mtime_ns)); self.assertNotIn('secret',p.stdout)
 def test_broken_evidence_symlink_is_blocked(self):
  self.call('specify','in-progress'); (self.r/'broken').symlink_to('missing'); p=self.call('specify','complete',evidence=['broken']); self.assertEqual((p.returncode,json.loads(p.stdout)['code']),(2,'EVIDENCE-SYMLINK'))
 def test_ancestor_evidence_symlink_is_blocked(self):
  self.call('specify','in-progress'); outside=Path(self.t.name)/'outside-dir'; outside.mkdir(); (outside/'proof').write_text('secret'); (self.r/'linked-dir').symlink_to(outside,target_is_directory=True)
  p=self.call('specify','complete',evidence=['linked-dir/proof']); self.assertEqual(p.returncode,2); self.assertEqual(json.loads(p.stdout)['code'],'SYMLINK-REJECTED'); self.assertNotIn('secret',p.stdout)
 def test_concurrent_identical_transition_serializes(self):
  def invoke(_): return self.call('specify','in-progress')
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(invoke,range(2)))
  payloads=[json.loads(p.stdout) for p in results]; self.assertEqual(sorted(p['verdict'] for p in payloads),['REUSED','UPDATED'])
  state=json.loads((self.r/'.grill/work-items/wx/state.json').read_text()); self.assertEqual(len(state['development']['audit']),1); self.assertFalse((self.r/'.grill/work-items/wx.lock').exists())
 def test_concurrent_divergent_transition_is_deterministic(self):
  def invoke(reason): return self.call('specify','in-progress',reason=reason)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(invoke,['one','two']))
  pairs=sorted((p.returncode,json.loads(p.stdout)['verdict']) for p in results); self.assertEqual(pairs,[(0,'UPDATED'),(2,'BLOCKED')])
  state=json.loads((self.r/'.grill/work-items/wx/state.json').read_text()); self.assertEqual(len(state['development']['audit']),1)
 def test_evidence_content_change_causes_state_divergence(self):
  self.call('specify','in-progress'); self.call('specify','complete',evidence=['e'],reason='done'); (self.r/'e').write_text('changed')
  p=self.call('specify','complete',evidence=['e'],reason='done'); self.assertEqual((p.returncode,json.loads(p.stdout)['code']),(2,'STATE-DIVERGENCE'))
 def test_legacy_explicit_specify_initialization_succeeds_without_inference(self):
  path=self.r/'.grill/work-items/wx/state.json'; path.write_text('{}')
  p=run('checkpoint',self.r,'--work-id','wx','--step','specify','--state','in-progress','--operation-id','specify-in-progress','--session-ref','session-1','--initialize-legacy','--from-step','specify','--evidence','e','--reason','explicit-decision')
  self.assertEqual(p.returncode,0,p.stdout); state=json.loads(path.read_text()); self.assertEqual(state['development']['steps']['specify'],'in-progress'); self.assertTrue(all(state['development']['steps'][s]=='pending' for s in STEPS[1:])); self.assertEqual(len(state['development']['audit']),1)
 def test_legacy_posterior_initialization_is_unsafe(self):
  path=self.r/'.grill/work-items/wx/state.json'; path.write_text('{}'); before=path.read_bytes()
  p=run('checkpoint',self.r,'--work-id','wx','--step','plan','--state','in-progress','--initialize-legacy','--from-step','plan','--evidence','e','--reason','explicit-decision')
  self.assertEqual((p.returncode,json.loads(p.stdout)['code']),(2,'LEGACY-INITIALIZATION-UNSAFE')); self.assertEqual(before,path.read_bytes())
 def test_state_symlink_is_blocked_without_external_read(self):
  state=self.r/'.grill/work-items/wx/state.json'; outside=Path(self.t.name)/'external-state'; outside.write_text('TOP-SECRET'); state.unlink(); state.symlink_to(outside)
  p=self.call('specify','in-progress'); self.assertEqual(p.returncode,2); self.assertNotIn('TOP-SECRET',p.stdout); self.assertEqual(outside.read_text(),'TOP-SECRET')

class CommittedCheckpointContract(CheckpointContract):
 def test_content_wal_recovers_state_and_commits_head(self):
  state_path=self.r/'.grill/work-items/wx/state.json'; before=state_path.read_bytes(); after=b'{"checkpoint":true}\n'
  snapshot=store.read_snapshot(self.r); item=snapshot.document['agent_orchestration']['work_items']['wx']; context_id=item['current_context_id']; context=item['contexts'][context_id]
  request=contract.checkpoint_request(store_origin={'revision':snapshot.revision,'content_sha256':snapshot.content_sha256},work_id='wx',operation_id='op-1',context_id=context_id,step='specify',state='in-progress',evidence=[],reason='',attestation=None,supersedes_attestation=None,initialize_legacy=False,from_step=None)
  checkpoint={'schema':contract.CHECKPOINT_SCHEMA,'checkpoint_id':'cp-op-1','context_id':context_id,'previous_checkpoint_id':None,'worktree_identity':{},'created_at':'2026-01-01T00:00:00Z','store_revision':snapshot.revision+1,'journal_anchor':snapshot.document['journal_head'],'state_sha256':hashlib.sha256(after).hexdigest(),'inputs_manifest':{},'workflow_sha256':'3'*64,'constitution_sha256':'4'*64,'policy_sha256':item['policy_sha256'],'activation':None,'campaign':None,'development_sequence':{},'current_step':'specify','step_states':{},'accepted_outputs':{},'accepted_executions':{},'pending_attempts':{},'scheduler_runs':{},'operations':{},'cleanup_obligations':{},'preserved_resources':{},'blocking_activity':None,'visual_state':{},'presentation':None,'checkpoint_sha256':''}
  checkpoint['checkpoint_sha256']=store.jcs_sha256({k:v for k,v in checkpoint.items() if k!='checkpoint_sha256'})
  state_write={'work_id':'wx','destination':'.grill/work-items/wx/state.json','before_sha256':hashlib.sha256(before).hexdigest(),'after_base64':base64.b64encode(after).decode(),'after_sha256':hashlib.sha256(after).hexdigest(),'expected_store_revision':snapshot.revision,'expected_journal_anchor':snapshot.document['journal_head']}
  result={'work_id':'wx','context_id':context_id,'epoch':context['epoch'],'operation_id':'op-1','checkpoint_id':'cp-op-1','step':'specify','state':'in-progress','evidence':[],'reason':'','execution_branch':'main','supersedes':None,'current_step':'specify'}
  content={'schema':contract.CHECKPOINT_CONTENT_SCHEMA,'work_id':'wx','operation_id':'op-1','request':request,'checkpoint':checkpoint,'before_base64':base64.b64encode(before).decode(),'state_write':state_write,'binding_transition':None,'result':result}
  digest=contract.checkpoint_content_sha256(content); ref='.grill/work-items/wx/agent-orchestration/checkpoints/op-1.json'
  operation={'kind':'checkpoint','context_id':context_id,'fence':context['leader']['fence'],'subject_ids':['state'],'input_sha256':store.jcs_sha256(request),'expected_before':{'state_sha256':state_write['before_sha256']},'intended_after':{'state_sha256':state_write['after_sha256']},'idempotency_key':'op-1','state':'CONFIRMED','result_ref':ref,'result_sha256':digest,'observation_ref':ref,'error':None,'request':request,'content_ref':ref}
  receipt={'schema':'grill-orchestration-receipt/v1','category':'runtime','name':'checkpoint-op-1','work_id':'wx','context_id':context_id,'operation_id':'op-1','input_sha256':operation['input_sha256'],'output_sha256':digest}
  event={'schema':'grill-orchestration-event/v1','event':'agent.orchestration.checkpoint','work_id':'wx','context_id':context_id,'operation_id':'op-1','input_sha256':operation['input_sha256'],'output_sha256':digest,'receipt_sha256':store.jcs_sha256(receipt)}
  def mutate(document):
   target=document['agent_orchestration']['work_items']['wx']; target['operations']['op-1']=operation; target['checkpoints']['cp-op-1']=checkpoint; target['checkpoint_head']='cp-op-1'; return document
  with self.assertRaisesRegex(RuntimeError,'fault'):
   store.transact_checkpoint_with_content(self.r,mutate,event=event,receipt=receipt,content_ref=ref,content=content,fault=lambda point: (_ for _ in ()).throw(RuntimeError('fault')) if point=='after-state' else None)
  recovered=store.recover_pending_transition(self.r)
  self.assertEqual((state_path.read_bytes(),recovered.document['agent_orchestration']['work_items']['wx']['checkpoint_head']),(after,'cp-op-1'))
if __name__=='__main__': unittest.main()
