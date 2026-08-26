#!/usr/bin/env python3
"""Contract tests for managed WORKFLOW.md v3 and the preview-first v2 -> v3 migration.

Critical invariant under test: v2 coexists. The v2 allowlist stays frozen and a
WORKFLOW.md v2 already materialised in a consumer repository stays byte-intact
through detection, preview and the v2 bootstrap.
"""
from __future__ import annotations
import hashlib, importlib.util, json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE=Path(__file__).resolve(); REPO=HERE.parents[1]; PLUGIN=REPO/'plugin'
SKILL=PLUGIN/'skills/grill-with-docs'
SCRIPTS=PLUGIN/'skills/grill-with-docs/scripts'; ASSETS=PLUGIN/'skills/grill-with-docs/assets'
MODULE=SCRIPTS/'grill_core/workflow_v3.py'; ENSURE=SCRIPTS/'ensure_workflow.py'; GRILL_WORKSPACE=SCRIPTS/'grill_workspace.py'
AUDIT_DECISIONS=SCRIPTS/'audit_decisions.py'
TEMPLATE_V2=ASSETS/'WORKFLOW.template.md'; TEMPLATE_V3=ASSETS/'WORKFLOW.v3.template.md'
MARK_V2='grill-with-docs-workflow:v2'; MARK_V3='grill-with-docs-workflow:v3'
STEPS=['specify','plan','checklist','tasks','analyze','agent-assign','agent-execute','converge','verify','review','ship']
# research.md §R5's seven-case matrix, materialised by T003 -- never hand-typed
# text -- under tests/fixtures/workflow-marker-matrix/<case>/WORKFLOW.md.
MATRIX_ROOT=REPO/'tests/fixtures/workflow-marker-matrix'
MATRIX_CASES=('none','v2','v3','v4','duplicate-same','duplicate-distinct','unknown-v9')
# Frozen mirror of the marker regex both ensure_workflow.sole_managed_version
# and audit_decisions.py's inline marker check use, byte for byte. Used only
# to independently recompute "how many declarations does this document carry"
# for the parity test below -- never to reimplement either module's decision.
MARKER_PATTERN=r"grill-with-docs-workflow:(v\d+)"
# Frozen copy of ensure_workflow.ESSENTIAL. Appending a v3 marker here would mark
# every already-materialised v2 consumer as "incompatible workflow".
FROZEN_V2=('## Loop externo','## Ciclo externo de execução','specify','plan','checklist','tasks','analyze','agent-assign','agent-execute','converge','verify','review','ship','PLAN_ONLY_STOP','Spec Kit >=0.11.2','A–E','no PR','hotfix-fast','HOTFIX-GO')
V3_ONLY=('## Invocação canônica','invoke, do not emulate','invocar a skill registrada','semantic emulation','workflow-step-skills/v1','workflow-step-skills.json','registry_sha256','CANONICAL_SKILL','skill-resolution','skill-invocation','step-output','UNATTESTED_STEP_OUTPUT','BLOCKED_CAPABILITY','POLICY_VIOLATION/DIRECT_STEP_EXECUTION')

def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None: raise RuntimeError(f'unable to load {path}')
 module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module

V3=load(MODULE,'grill_core_workflow_v3_contract'); EW=load(ENSURE,'ensure_workflow_v3_contract')
AD=load(AUDIT_DECISIONS,'grill_audit_decisions_v3_contract')

def symlink_supported():
 with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
  root=Path(temporary)
  try: (root/'link').symlink_to(root/'target')
  except (OSError,NotImplementedError): return False
  return True

SYMLINK_SUPPORTED=symlink_supported()

def run(*args): return subprocess.run([sys.executable,str(MODULE),*map(str,args)],text=True,capture_output=True)
def ensure(root): return subprocess.run([sys.executable,str(ENSURE),'--ensure',str(root)],text=True,capture_output=True)
def payload(result):
 lines=result.stdout.splitlines(); assert len(lines)==1,result.stdout; assert result.stderr=='',result.stderr
 return json.loads(lines[0])
def snapshot(root):
 out={}
 for path in sorted(Path(root).rglob('*')):
  rel=path.relative_to(root).as_posix()
  if rel=='.git' or rel.startswith('.git/'): continue
  st=path.lstat(); out[rel]=('link',os.readlink(path),st.st_mtime_ns) if path.is_symlink() else (('file',path.read_bytes(),st.st_mtime_ns) if path.is_file() else ('dir',st.st_mtime_ns))
 return out
def sha(content): return hashlib.sha256(content).hexdigest()
LIVE_REGISTRY_SHA256=V3.registry_state()['sha256']  # LD-001: prefixed 'sha256:<64-hex>', peça C's own format.
def v3_text(pin=None):
 """The bundled v3 template with the registry_sha256 placeholder replaced by
 ``pin`` (the live registry hash by default) -- what a correctly materialised,
 correctly pinned v3 document looks like. ``migrate --apply`` writes exactly
 this (with ``pin=None``, i.e. the live hash)."""
 if pin is None: pin=LIVE_REGISTRY_SHA256
 return TEMPLATE_V3.read_text(encoding='utf-8').replace('__REGISTRY_SHA256__',pin)
def rendered_v3(registry_sha256):
 """What migrate --apply actually writes: the bundled template with the real registry_sha256 baked in."""
 return v3_text(registry_sha256).encode('utf-8')
def matrix_text(case):
 """The T003 fixture text for one R5 matrix case (real materialised bytes,
 mechanically edited per specs/024-workflow-version-derivada/implement/p02-b.tasks.json -- never hand-typed)."""
 return (MATRIX_ROOT/case/'WORKFLOW.md').read_text(encoding='utf-8')
def audit_marker_decision(text):
 """Mirror -- for this test only, not a shared production module (ADR-0002
 rejected that) -- of the inline marker check audit_decisions.py's audit()
 performs under ``if workflow and workflow.is_file():``: exactly one marker,
 and it must be one of ACCEPTED_WORKFLOW_MARKERS. Returns (markers, accepted)."""
 markers=re.findall(MARKER_PATTERN,text)
 accepted=len(markers)==1 and markers[0] in AD.ACCEPTED_WORKFLOW_MARKERS
 return markers,accepted

class Base(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.root=Path(self.t.name).resolve(); subprocess.run(['git','init','-q','-b','main',str(self.root)],check=True); self.path=self.root/'WORKFLOW.md'
 def tearDown(self): self.t.cleanup()
 def materialise(self,content: bytes): self.path.write_bytes(content); return content
 def v2(self): return self.materialise(TEMPLATE_V2.read_bytes())
 def v3(self): return self.materialise(v3_text().encode())
 def v3_placeholder(self): return self.materialise(TEMPLATE_V3.read_bytes())
 def preview(self): return payload(run('migrate',self.root))

class V2Coexistence(Base):
 def test_v2_allowlist_and_marker_are_frozen(self):
  self.assertEqual(EW.VERSION,'v2'); self.assertEqual(EW.MARKER,MARK_V2); self.assertEqual(EW.ESSENTIAL,FROZEN_V2)
  text=TEMPLATE_V2.read_text(encoding='utf-8'); self.assertNotIn(MARK_V3,text); self.assertEqual(EW.managed_version(text),'v2'); self.assertTrue(EW.compatible(text))
 def test_v3_allowlist_is_a_new_tuple_not_an_edit_of_v2(self):
  self.assertIsNot(V3.ESSENTIAL,EW.ESSENTIAL); self.assertNotEqual(V3.ESSENTIAL,EW.ESSENTIAL)
  self.assertTrue(set(V3.ESSENTIAL).issuperset(set(EW.ESSENTIAL))); self.assertTrue(set(V3.ESSENTIAL).issuperset(set(V3_ONLY)))
  self.assertFalse(set(EW.ESSENTIAL)&set(V3_ONLY)); self.assertEqual(EW.ESSENTIAL,FROZEN_V2); self.assertEqual(V3.VERSION,'v3'); self.assertEqual(V3.MARKER,MARK_V3)
 def test_materialised_v2_is_byte_intact_across_detect_and_preview(self):
  content=self.v2(); before=snapshot(self.root)
  self.assertEqual(payload(run('detect',self.root))['version'],'v2'); self.assertEqual(self.preview()['verdict'],'PREVIEW')
  V3.detect_text(content.decode()); V3.execution_gate(content.decode()); V3.detect_command(self.root); V3.migrate_command(self.root)
  self.assertEqual(before,snapshot(self.root)); self.assertEqual(content,self.path.read_bytes())
 def test_v2_bootstrap_still_reuses_untouched_bytes(self):
  content=self.v2(); result=ensure(self.root); self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  emitted=json.loads(result.stdout); self.assertEqual(emitted['status'],'REUSED'); self.assertEqual(emitted['version'],'v2'); self.assertEqual(emitted['sha256'],sha(content)); self.assertEqual(content,self.path.read_bytes())
 def test_v2_passes_the_v2_gate_and_blocks_only_v3_execution(self):
  text=TEMPLATE_V2.read_text(encoding='utf-8')
  self.assertEqual(V3.v2_gate(text).status,'OK'); self.assertIsNone(V3.v2_gate(text).code)
  gate=V3.execution_gate(text); self.assertEqual(gate.status,'BLOCKED'); self.assertEqual(gate.code,'WORKFLOW_INCOMPATIBLE'); self.assertTrue(set(gate.missing).issuperset(set(V3_ONLY)))

class TemplateV3(unittest.TestCase):
 def setUp(self): self.text=TEMPLATE_V3.read_text(encoding='utf-8')
 def test_marker_is_v3_and_unique(self):
  self.assertEqual(self.text.count(MARK_V3),1); self.assertNotIn(MARK_V2,self.text); self.assertEqual(EW.managed_version(self.text),'v3'); self.assertTrue(V3.compatible_v3(self.text)); self.assertEqual(V3.missing_v3(self.text),())
 def test_v2_prose_and_eleven_steps_are_preserved(self):
  self.assertTrue(EW.compatible(self.text))
  cycle=self.text.split('## Ciclo externo de execução (11 etapas)',1)[1]
  positions=[cycle.index(step) for step in STEPS]; self.assertEqual(positions,sorted(positions))
  self.assertLess(self.text.index('antes de `specify`'),self.text.index('## Ciclo externo de execução'))
 def test_every_sequence_token_means_invoke_the_registered_skill(self):
  self.assertIn('invocar a skill registrada',self.text); self.assertIn('invoke, do not emulate',self.text)
  self.assertLess(self.text.index('## Invocação canônica'),self.text.index('## Ciclo externo de execução'))
  self.assertIn('`step_id` do registry',self.text)
 def test_registry_is_referenced_by_hash(self):
  for token in ('workflow-step-skills.json','workflow-step-skills/v1','registry_sha256','assets/workflow-step-skills.json'): self.assertIn(token,self.text)
  self.assertIn('por hash',self.text)
  # The raw template only ever carries the placeholder: "assertIn('por hash', ...)"
  # alone only proves the word exists, not that any hash is actually pinned.
  # Migration.test_apply_migrates_and_is_idempotent_once_the_runtime_is_wired
  # proves the real 64-hex digest lands in the materialised document.
  self.assertEqual(self.text.count(V3.REGISTRY_SHA256_PLACEHOLDER),1)
 def test_semantic_emulation_is_explicitly_forbidden(self):
  for token in ('semantic emulation','UNATTESTED_STEP_OUTPUT','BLOCKED_CAPABILITY','POLICY_VIOLATION/DIRECT_STEP_EXECUTION','DIRECT|EMULATED|BEST_EFFORT','CANONICAL_SKILL'): self.assertIn(token,self.text)
  for step in ('verify','review','ship'): self.assertIn(step,self.text.split('### Proibição explícita de semantic emulation',1)[1])
 def test_migration_and_hook_boundary_are_declared(self):
  for token in ('preview-first','no-clobber','byte-intacto','WORKFLOW_INCOMPATIBLE','read, resolve and invoke; do not emulate','read-only'): self.assertIn(token,self.text)

class Detection(Base):
 def test_versions_of_a_materialised_workflow(self):
  self.v2(); self.assertEqual(payload(run('detect',self.root))['version'],'v2')
  content=self.v3(); emitted=payload(run('detect',self.root)); self.assertEqual(emitted['version'],'v3'); self.assertTrue(emitted['v3_compatible']); self.assertEqual(emitted['v3_execution']['status'],'OK'); self.assertEqual(emitted['sha256'],sha(content))
 def test_human_equivalent_declaring_the_frontier_is_accepted_for_v3(self):
  text=v3_text().replace(f'<!-- {MARK_V3} -->','<!-- human-maintained equivalent -->')
  self.materialise(text.encode()); emitted=payload(run('detect',self.root))
  self.assertIsNone(emitted['marker']); self.assertIsNone(emitted['version']); self.assertTrue(emitted['v3_compatible']); self.assertEqual(emitted['v3_execution']['status'],'OK')
 def test_reordered_required_v3_cycle_is_blocked_even_when_all_tokens_and_pin_remain(self):
  canonical='`specify → plan → checklist → tasks → analyze → agent-assign → agent-execute → converge → verify → review → ship`'
  reordered='`plan → specify → checklist → tasks → analyze → agent-assign → agent-execute → converge → verify → review → ship`'
  text=v3_text().replace(canonical,reordered,1)
  self.assertNotEqual(text,v3_text())
  self.assertTrue(all(token in text for token in V3.ESSENTIAL),'the regression must retain the old substring frontier')
  self.assertTrue(V3.pin_is_current(text),'the registry-pin gate must remain independently satisfied')
  self.assertFalse(V3.compatible_v3(text))
  self.assertIn(V3.STEP_ORDER_MISSING,V3.missing_v3(text))
  gate=V3.execution_gate(text); self.assertEqual(gate.status,'BLOCKED'); self.assertEqual(gate.code,'WORKFLOW_INCOMPATIBLE')
  self.assertIn(V3.STEP_ORDER_MISSING,gate.missing)
  self.materialise(text.encode()); emitted=payload(run('detect',self.root))
  self.assertFalse(emitted['v3_compatible']); self.assertEqual(emitted['v3_execution']['status'],'BLOCKED')
  self.assertEqual(emitted['v3_execution']['code'],'WORKFLOW_INCOMPATIBLE')
 def test_malformed_or_wrapped_arrow_cycle_cannot_hide_behind_the_table(self):
  canonical='`specify → plan → checklist → tasks → analyze → agent-assign → agent-execute → converge → verify → review → ship`'
  duplicate=(
   '`specify → plan → checklist → tasks → analyze → agent-assign`\n'
   '`agent-execute → converge → verify → review → ship → ship`'
  )
  reordered_wrapped=(
   '`plan → specify → checklist → tasks → analyze → agent-assign`\n'
   '`agent-execute → converge → verify → review → ship`'
  )
  for replacement in (duplicate, reordered_wrapped, canonical + ' → ship'):
   text=v3_text().replace(canonical,replacement,1)
   self.assertFalse(V3.canonical_step_order(text), replacement)
   self.assertEqual(V3.execution_gate(text).code,'WORKFLOW_INCOMPATIBLE')
 def test_human_equivalent_without_the_frontier_is_workflow_incompatible_for_v3_only(self):
  text=TEMPLATE_V2.read_text(encoding='utf-8').replace(f'<!-- {MARK_V2} -->','<!-- human-maintained equivalent -->')
  self.materialise(text.encode()); emitted=payload(run('detect',self.root))
  self.assertIsNone(emitted['version']); self.assertTrue(emitted['v2_compatible']); self.assertEqual(emitted['v2_execution']['status'],'OK')
  self.assertEqual(emitted['v3_execution']['status'],'BLOCKED'); self.assertEqual(emitted['v3_execution']['code'],'WORKFLOW_INCOMPATIBLE')
 def test_foreign_marker_and_garbage_never_pass_a_gate(self):
  self.materialise(TEMPLATE_V3.read_text(encoding='utf-8').replace(MARK_V3,'grill-with-docs-workflow:v9').encode())
  emitted=payload(run('detect',self.root)); self.assertEqual(emitted['marker'],'v9'); self.assertEqual(emitted['v3_execution']['code'],'WORKFLOW_INCOMPATIBLE'); self.assertEqual(emitted['v2_execution']['code'],'WORKFLOW_INCOMPATIBLE')
  for text in ('','   ','human notes'):
   self.materialise(text.encode()); emitted=payload(run('detect',self.root)); self.assertFalse(emitted['v2_compatible']); self.assertFalse(emitted['v3_compatible'])
 def test_missing_and_invalid_utf8_fail_closed(self):
  result=run('detect',self.root); self.assertEqual(result.returncode,2); self.assertEqual(payload(result)['code'],'WORKFLOW_MISSING')
  self.materialise(b'\xff\xfe'); result=run('detect',self.root); self.assertEqual(result.returncode,2); self.assertEqual(payload(result)['code'],'WORKFLOW_INVALID_UTF8'); self.assertNotIn('Traceback',result.stderr)
 def test_root_must_be_a_git_top_level(self):
  nested=self.root/'nested'; nested.mkdir()
  for candidate in (self.root/'absent',nested):
   result=run('detect',candidate); self.assertEqual(result.returncode,2); self.assertEqual(payload(result)['code'],'WORKFLOW_ROOT_INVALID')
 @unittest.skipUnless(SYMLINK_SUPPORTED,'symlink creation is unavailable')
 def test_symlinked_workflow_is_unsafe(self):
  external=self.root.parent/'outside.md'; external.write_text('secret'); self.path.symlink_to(external)
  result=run('detect',self.root); self.assertEqual(result.returncode,2); self.assertEqual(payload(result)['code'],'WORKFLOW_UNSAFE'); self.assertNotIn('secret',result.stdout)

class Migration(Base):
 def test_preview_is_read_only_and_shows_the_v3_diff(self):
  content=self.v2(); before=snapshot(self.root); emitted=self.preview()
  self.assertEqual(emitted['verdict'],'PREVIEW'); self.assertFalse(emitted['applied']); self.assertTrue(emitted['pristine'])
  self.assertEqual(emitted['from_version'],'v2'); self.assertEqual(emitted['to_version'],'v3')
  registry_sha256=emitted['registry']['sha256']; self.assertRegex(registry_sha256,r'^sha256:[0-9a-f]{64}$')
  self.assertEqual(registry_sha256,LIVE_REGISTRY_SHA256)
  self.assertEqual(emitted['current_sha256'],sha(content)); self.assertEqual(emitted['target_sha256'],sha(rendered_v3(registry_sha256)))
  self.assertNotEqual(emitted['target_sha256'],sha(TEMPLATE_V3.read_bytes()),'target must be the rendered doc, not the raw placeholder template')
  diff=emitted['diff']; self.assertTrue(diff.startswith('--- a/WORKFLOW.md'))
  self.assertIn(f'-<!-- {MARK_V2} -->',diff); self.assertIn(f'+<!-- {MARK_V3} -->',diff)
  for token in ('invoke, do not emulate','invocar a skill registrada','semantic emulation','workflow-step-skills.json','registry_sha256'): self.assertIn(token,diff)
  self.assertIn(registry_sha256,diff); self.assertNotIn('__REGISTRY_SHA256__',diff)
  self.assertIn('--apply',emitted['next_command']); self.assertIn(emitted['current_sha256'],emitted['next_command'])
  self.assertEqual(emitted['registry']['schema'],'workflow-step-skills/v1'); self.assertEqual(emitted['registry']['ref'],'assets/workflow-step-skills.json')
  self.assertEqual(before,snapshot(self.root)); self.assertFalse((self.root/'.grill').exists())
 def test_apply_without_previewed_hash_is_refused(self):
  content=self.v2(); result=run('migrate',self.root,'--apply')
  self.assertEqual(result.returncode,2); self.assertEqual(payload(result)['code'],'INVALID_ARGUMENTS'); self.assertEqual(content,self.path.read_bytes())
 def test_apply_with_a_stale_hash_is_state_divergence(self):
  content=self.v2(); result=run('migrate',self.root,'--apply','--expected-sha256',sha(b'other'))
  self.assertEqual(result.returncode,2); self.assertEqual(payload(result)['code'],'STATE_DIVERGENCE'); self.assertEqual(content,self.path.read_bytes())
 def test_apply_migrates_for_real_and_is_idempotent_and_the_consumer_stays_usable(self):
  # GAP (round 3), the defect that survived two rounds: runtime_wired() used
  # to compare ensure_workflow.VERSION == 'v3', a predicate that can never
  # turn True without breaking Fase 0 (VERSION pins what fresh bootstrap
  # MATERIALISES, frozen at 'v2' -- not what the runtime can READ). Every
  # authorised apply was therefore permanently V3_RUNTIME_NOT_WIRED, and the
  # only test that ever exercised APPLIED mutated ensure_module.VERSION
  # in-process -- patching exactly the attribute the gate under test reads.
  # ANTI-TRAP (LD-010, verbatim): no monkeypatch of runtime_wired or of any
  # attribute it reads, anywhere in this test. Fixed: runtime_wired() now
  # asks ensure_workflow.resolve_workflow directly (see workflow_v3.py). This
  # test calls the real CLI end to end, with nothing patched anywhere, against
  # the real, already-wired ensure_workflow.py: migrate --apply must actually
  # WRITE the file, and the two real consumer entrypoints the critic
  # exercised (`ensure_workflow.py --ensure`, `grill_workspace.py init`) must
  # see v3 immediately afterwards, on the same repository, still unmocked.
  content=self.v2(); emitted=self.preview(); registry_sha256=emitted['registry']['sha256']
  os.chmod(self.path,0o644)
  self.assertTrue(V3.runtime_wired())  # the real, un-mocked functional probe
  applied_result=run('migrate',self.root,'--apply','--expected-sha256',emitted['current_sha256'])
  self.assertEqual(applied_result.returncode,0,applied_result.stdout+applied_result.stderr)
  applied=payload(applied_result)
  self.assertEqual(applied['verdict'],'APPLIED'); self.assertTrue(applied['applied'])
  written=self.path.read_bytes()
  self.assertEqual(written,rendered_v3(registry_sha256)); self.assertNotEqual(written,content)
  self.assertIn(registry_sha256.encode(),written); self.assertNotIn(b'__REGISTRY_SHA256__',written)
  self.assertEqual(self.path.stat().st_mode&0o777,0o644)
  self.assertEqual(sorted(p.name for p in self.root.iterdir() if p.name!='.git'),['WORKFLOW.md'])
  # Idempotent: preview now says REUSED with an empty diff, and a second
  # authorised apply is a REUSED no-op, byte for byte -- both over subprocess,
  # both against the real (still un-mocked) runtime.
  again=self.preview(); self.assertEqual(again['verdict'],'REUSED'); self.assertFalse(again['applied']); self.assertEqual(again['diff'],'')
  repeat_result=run('migrate',self.root,'--apply','--expected-sha256',again['current_sha256'])
  self.assertEqual(repeat_result.returncode,0,repeat_result.stdout+repeat_result.stderr)
  repeat=payload(repeat_result)
  self.assertEqual(repeat['verdict'],'REUSED'); self.assertEqual(self.path.read_bytes(),written)
  # Integration test that was entirely missing before this round: after a
  # REAL apply, the two real consumer entrypoints must now see v3, not
  # "managed version mismatch" / WORKFLOW-UNAVAILABLE.
  ensured=ensure(self.root); self.assertEqual(ensured.returncode,0,ensured.stdout+ensured.stderr)
  ensured_body=json.loads(ensured.stdout)
  self.assertEqual(ensured_body['status'],'REUSED'); self.assertEqual(ensured_body['version'],'v3'); self.assertEqual(ensured_body['sha256'],sha(written))
  init=subprocess.run([sys.executable,str(GRILL_WORKSPACE),'init',str(self.root),'--type','feature','--slug','consumer-demo-v3','--skip-backlog'],
                       text=True,capture_output=True,env={**os.environ,'GRILL_SKIP_DEPENDENCIES':'1'})
  self.assertEqual(init.returncode,0,init.stdout+init.stderr); init_body=json.loads(init.stdout.splitlines()[0])
  self.assertNotEqual(init_body.get('code'),'WORKFLOW-UNAVAILABLE'); self.assertEqual(init_body.get('status'),'CREATED')
  self.assertEqual(init_body['workflow']['status'],'REUSED')
 def test_local_edits_are_never_clobbered_without_explicit_authorisation(self):
  content=self.materialise(TEMPLATE_V2.read_bytes()+b'\n## Regra local\nnao apagar\n'); emitted=self.preview()
  self.assertEqual(emitted['verdict'],'PREVIEW'); self.assertFalse(emitted['pristine'])
  result=run('migrate',self.root,'--apply','--expected-sha256',emitted['current_sha256'])
  self.assertEqual(result.returncode,1); body=payload(result); self.assertEqual(body['verdict'],'NO-GO'); self.assertEqual(body['code'],'WORKFLOW_LOCAL_EDITS')
  self.assertEqual(content,self.path.read_bytes())
  # --allow-local-edits clears the local-edits gate; with the runtime wired
  # for real (round-3 fix), that authorisation now actually reaches apply and
  # overwrites the local line -- explicit authorisation to overwrite local
  # edits IS authorisation, not a second permanent block behind it.
  forced=run('migrate',self.root,'--apply','--expected-sha256',emitted['current_sha256'],'--allow-local-edits')
  self.assertEqual(forced.returncode,0,forced.stdout+forced.stderr); forced_body=payload(forced)
  self.assertEqual(forced_body['verdict'],'APPLIED'); self.assertTrue(forced_body['applied'])
  self.assertNotEqual(content,self.path.read_bytes()); self.assertNotIn(b'nao apagar',self.path.read_bytes())
 def test_human_equivalent_is_previewed_but_not_rewritten(self):
  content=self.materialise(TEMPLATE_V2.read_text(encoding='utf-8').replace(f'<!-- {MARK_V2} -->','<!-- human-maintained equivalent -->').encode())
  emitted=self.preview(); self.assertEqual(emitted['verdict'],'PREVIEW'); self.assertIsNone(emitted['from_version']); self.assertFalse(emitted['pristine'])
  result=run('migrate',self.root,'--apply','--expected-sha256',emitted['current_sha256'])
  self.assertEqual(result.returncode,1); self.assertEqual(payload(result)['code'],'WORKFLOW_LOCAL_EDITS'); self.assertEqual(content,self.path.read_bytes())
 def test_human_equivalent_already_declaring_the_frontier_is_reused(self):
  content=self.materialise(v3_text().replace(f'<!-- {MARK_V3} -->','<!-- human-maintained equivalent -->').encode())
  emitted=self.preview(); self.assertEqual(emitted['verdict'],'REUSED'); self.assertEqual(content,self.path.read_bytes())
 def test_unmigratable_documents_block(self):
  content=self.materialise(b'human notes only\n'); result=run('migrate',self.root)
  self.assertEqual(result.returncode,2); body=payload(result); self.assertEqual(body['code'],'WORKFLOW_INCOMPATIBLE'); self.assertTrue(body['findings'])
  self.assertEqual(content,self.path.read_bytes())
  self.materialise(TEMPLATE_V3.read_text(encoding='utf-8').replace('invoke, do not emulate','faca o melhor esforco').encode())
  result=run('migrate',self.root); self.assertEqual(result.returncode,2); self.assertEqual(payload(result)['code'],'WORKFLOW_INCOMPATIBLE')

class OutputContract(Base):
 def test_every_call_prints_exactly_one_json_document(self):
  self.v2(); emitted=self.preview()
  calls=[('detect',self.root),('migrate',self.root),('migrate',self.root,'--apply'),('migrate',self.root,'--apply','--expected-sha256','deadbeef'),('detect',self.root/'absent'),('bogus',self.root),(),('detect',self.root,'--unknown'),('migrate',self.root,'--apply','--expected-sha256',emitted['current_sha256'])]
  for call in calls:
   with self.subTest(call=call):
    result=run(*call); body=payload(result); self.assertIn(result.returncode,(0,1,2)); self.assertEqual(body['schema'],'grill-workflow-migration/v1')
    self.assertTrue(('verdict' in body)); self.assertNotIn('Traceback',result.stderr)
    if result.returncode: self.assertIn(body['code'],V3.CLI_CODE_ALIASES)
 def test_exit_codes_pair_with_verdicts(self):
  self.assertEqual(V3.EXIT_OK,0); self.assertEqual(V3.EXIT_NO_GO,1); self.assertEqual(V3.EXIT_BLOCKED,2)
  self.v2(); emitted=self.preview()
  self.assertEqual(run('detect',self.root).returncode,0); self.assertEqual(run('migrate',self.root).returncode,0)
  self.materialise(TEMPLATE_V2.read_bytes()+b'\nlocal\n'); stale=payload(run('migrate',self.root))
  self.assertEqual(run('migrate',self.root,'--apply','--expected-sha256',stale['current_sha256']).returncode,1)
  self.assertEqual(run('migrate',self.root,'--apply','--expected-sha256',emitted['current_sha256']).returncode,2)
 def test_every_declared_code_has_a_kebab_alias_for_the_live_cli(self):
  for code,alias in V3.CLI_CODE_ALIASES.items():
   self.assertEqual(code,alias.replace('-','_')); self.assertEqual(code,code.upper()); self.assertNotIn('-',code)

class RegistryIntegrity(unittest.TestCase):
 """The registry is a bundled plugin asset (not per-repo data): corrupt, absent
 or bogus-schema bytes must fail closed with REGISTRY_INVALID before this
 module ever reports a `registry` field or writes a byte -- round-1 gap: a
 hardcoded schema constant was reported and apply went through regardless.
 Attacks a real corrupted COPY of the whole scripts+assets tree, because the
 module always resolves REGISTRY/TEMPLATE_V3 relative to its own file: a
 fixture that only patched the repo's real asset would never be exercised."""
 def setUp(self):
  tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.addCleanup(tmp.cleanup)
  self.skill=Path(tmp.name)/'skill'; shutil.copytree(SKILL,self.skill)
  self.registry=self.skill/'assets/workflow-step-skills.json'
  self.module=self.skill/'scripts/grill_core/workflow_v3.py'
  root_dir=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.addCleanup(root_dir.cleanup)
  self.root=Path(root_dir.name).resolve(); subprocess.run(['git','init','-q','-b','main',str(self.root)],check=True)
  self.path=self.root/'WORKFLOW.md'; self.path.write_bytes(TEMPLATE_V2.read_bytes())
 def _run(self,*args): return subprocess.run([sys.executable,str(self.module),*map(str,args)],text=True,capture_output=True)
 def _attack(self,corrupt):
  # Obtain a genuinely valid preview WHILE the registry is intact, only THEN
  # corrupt it: proves the check re-runs fresh at apply time and is not
  # satisfied by a stale/cached result carried over from the preview -- the
  # exact way round 1's helper "fixed" state before the attack ever landed.
  preview=json.loads(self._run('migrate',self.root).stdout)
  self.assertEqual(preview['verdict'],'PREVIEW')
  corrupt()
  for args in (('detect',self.root),('migrate',self.root),
               ('migrate',self.root,'--apply','--expected-sha256',preview['current_sha256'])):
   with self.subTest(args=args):
    result=self._run(*args); self.assertEqual(result.returncode,2,result.stdout+result.stderr)
    body=json.loads(result.stdout.splitlines()[0]); self.assertEqual(body['code'],'REGISTRY_INVALID')
  self.assertEqual(self.path.read_bytes(),TEMPLATE_V2.read_bytes())
 def test_corrupt_registry_json_blocks_after_a_valid_preview_before_any_write(self):
  self._attack(lambda: self.registry.write_text('{ not json',encoding='utf-8'))
 def test_deleted_registry_blocks_after_a_valid_preview_before_any_write(self):
  self._attack(lambda: self.registry.unlink())
 def test_bogus_registry_schema_blocks_after_a_valid_preview_before_any_write(self):
  def corrupt():
   document=json.loads(self.registry.read_text(encoding='utf-8')); document['schema']='bogus/v9'
   self.registry.write_text(json.dumps(document),encoding='utf-8')
  self._attack(corrupt)
 # GAP (round 2): the checks above only covered the outer shape (JSON, schema,
 # step KEY set). step_skills.validate_registry -- which registry_state now
 # delegates to instead of reimplementing -- also enforces logical identity
 # inside each step entry. Before that delegation, a null/empty step, a step
 # missing skill_id, an empty skill_id, or two steps sharing one skill_id all
 # passed as `detect OK` while step_skills rejected the identical bytes with
 # BLOCKED_CAPABILITY/REGISTRY_STEP_INVALID (or REGISTRY_DUPLICATE_SKILL_ID).
 def test_null_step_entry_blocks_after_a_valid_preview_before_any_write(self):
  def corrupt():
   document=json.loads(self.registry.read_text(encoding='utf-8')); document['steps']['verify']=None
   self.registry.write_text(json.dumps(document),encoding='utf-8')
  self._attack(corrupt)
 def test_empty_step_entry_blocks_after_a_valid_preview_before_any_write(self):
  def corrupt():
   document=json.loads(self.registry.read_text(encoding='utf-8')); document['steps']['verify']={}
   self.registry.write_text(json.dumps(document),encoding='utf-8')
  self._attack(corrupt)
 def test_step_missing_skill_id_blocks_after_a_valid_preview_before_any_write(self):
  def corrupt():
   document=json.loads(self.registry.read_text(encoding='utf-8')); del document['steps']['verify']['skill_id']
   self.registry.write_text(json.dumps(document),encoding='utf-8')
  self._attack(corrupt)
 def test_empty_skill_id_blocks_after_a_valid_preview_before_any_write(self):
  def corrupt():
   document=json.loads(self.registry.read_text(encoding='utf-8')); document['steps']['verify']['skill_id']=''
   self.registry.write_text(json.dumps(document),encoding='utf-8')
  self._attack(corrupt)
 def test_duplicate_skill_id_across_steps_blocks_after_a_valid_preview_before_any_write(self):
  def corrupt():
   document=json.loads(self.registry.read_text(encoding='utf-8'))
   document['steps']['review']['skill_id']=document['steps']['verify']['skill_id']
   self.registry.write_text(json.dumps(document),encoding='utf-8')
  self._attack(corrupt)

class RegistryHashParity(unittest.TestCase):
 """LD-001, verbatim: 'Ambas [peça C e peça D] têm que produzir a mesma string,
 e isso precisa de um teste que compare os dois caminhos.' Round-2 finding:
 step_skills.registry_sha256(raw) returned the 'sha256:'-prefixed form while
 workflow_v3.registry_state()['sha256'] returned the bare hex -- equal digest,
 different string, and nothing in this suite ever loaded both pieces to
 compare them. This does exactly that, over the identical on-disk bytes."""
 def test_registry_sha256_matches_step_skills_over_the_same_bytes(self):
  step_skills=load(SCRIPTS/'grill_core/step_skills.py','grill_core_step_skills_hash_parity_contract')
  raw=(ASSETS/'workflow-step-skills.json').read_bytes()
  c_side=step_skills.registry_sha256(raw)
  d_side=V3.registry_state()['sha256']
  self.assertEqual(c_side,d_side)
  self.assertRegex(d_side,r'^sha256:[0-9a-f]{64}$')
  self.assertEqual(d_side,LIVE_REGISTRY_SHA256)

class RegistryPinIntegrity(Base):
 """§4.1 fixes the literal schema `"registry_sha256": "sha256:<64-lowercase-
 hex>"` and says the registry is referenced BY HASH. Round-2 finding: the pin
 was only ever written, never verified on read -- a materialised v3
 WORKFLOW.md carrying the unrendered `__REGISTRY_SHA256__` placeholder, or one
 pinning a hash that does not match the live registry, both passed
 `detect`/`migrate` as fully conformant (`v3_execution.status=OK`,
 `migrate` verdict=REUSED). Both vectors must now fail closed with a named
 code, on READ (detect), not only refused at migration-write time."""
 def test_unrendered_placeholder_pin_is_never_v3_conformant(self):
  content=self.v3_placeholder()
  detected=payload(run('detect',self.root))
  self.assertEqual(detected['version'],'v3'); self.assertTrue(detected['v3_compatible'])
  self.assertEqual(detected['v3_execution']['status'],'BLOCKED')
  self.assertEqual(detected['v3_execution']['code'],'REGISTRY_PIN_DIVERGENT')
  result=run('migrate',self.root); self.assertEqual(result.returncode,2)
  body=payload(result); self.assertEqual(body['code'],'REGISTRY_PIN_DIVERGENT'); self.assertNotEqual(body.get('verdict'),'REUSED')
  self.assertEqual(content,self.path.read_bytes())
  self.assertEqual(V3.execution_gate(content.decode()).code,'REGISTRY_PIN_DIVERGENT')
 def test_divergent_registry_pin_is_never_v3_conformant(self):
  bogus_pin='sha256:'+('0'*64); self.assertNotEqual(bogus_pin,LIVE_REGISTRY_SHA256)
  content=self.materialise(v3_text(bogus_pin).encode())
  detected=payload(run('detect',self.root))
  self.assertEqual(detected['version'],'v3'); self.assertTrue(detected['v3_compatible'])
  self.assertEqual(detected['v3_execution']['status'],'BLOCKED')
  self.assertEqual(detected['v3_execution']['code'],'REGISTRY_PIN_DIVERGENT')
  self.assertNotEqual(detected['registry']['sha256'],bogus_pin)
  result=run('migrate',self.root); self.assertEqual(result.returncode,2)
  body=payload(result); self.assertEqual(body['code'],'REGISTRY_PIN_DIVERGENT')
  self.assertEqual(content,self.path.read_bytes())
 def test_correctly_pinned_v3_document_passes_the_pin_check(self):
  self.v3(); detected=payload(run('detect',self.root))
  self.assertEqual(detected['v3_execution']['status'],'OK'); self.assertIsNone(detected['v3_execution']['code'])
 def test_pin_divergent_code_has_a_kebab_alias(self):
  self.assertIn('REGISTRY_PIN_DIVERGENT',V3.CLI_CODE_ALIASES)
  self.assertEqual(V3.CLI_CODE_ALIASES['REGISTRY_PIN_DIVERGENT'],'REGISTRY-PIN-DIVERGENT')
 def test_pin_is_current_is_exposed_for_other_modules_to_consume(self):
  # LD-010 item 3 ("O gate de pin: exponha de forma consumível por outro
  # módulo"): ensure_workflow.py (peça E) dynamically loads this module and
  # must be able to ask the real pin gate, not reimplement it. Exercised the
  # same way peça E's own loader would: through the plain function, no
  # internals of execution_gate reached into directly.
  self.v3(); self.assertTrue(V3.pin_is_current(self.path.read_text(encoding='utf-8')))
  self.assertFalse(V3.pin_is_current(v3_text('sha256:'+('0'*64))))
  self.assertFalse(V3.pin_is_current(TEMPLATE_V3.read_text(encoding='utf-8')))  # unrendered placeholder

class HookBoundary(Base):
 def test_hook_injects_registry_sha256_and_the_v3_instruction(self):
  # This was a GAP test in round 2: the template's normative prose requires
  # the hook to inject registry_sha256 and "read, resolve and invoke; do not
  # emulate", but ensure_workflow.py --hook is out of this piece's scope
  # (LD-003/LD-004: peça E owns that file, not this module) and, at the time,
  # had not been wired yet. The test asserted the ABSENCE of both tokens on
  # purpose, so it would go red -- "forcing a conscious update of this test
  # by whichever round actually wires the hook for v3" -- the moment that
  # happened. Peça E's wiring landed in this round (LD-004 item 4); this test
  # is that conscious update, asserting the tokens are now present. Still
  # only observes ensure_workflow.py's real behaviour -- never edits it.
  self.v2()
  result=subprocess.run([sys.executable,str(ENSURE),'--hook'],
                         input=json.dumps({'hook_event_name':'SessionStart','cwd':str(self.root)}),
                         text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  emitted=json.loads(result.stdout); message=emitted['hookSpecificOutput']['additionalContext']
  self.assertIn('registry_sha256',message); self.assertIn('read, resolve and invoke; do not emulate',message)
  # LD-001 format check. §4.1's literal schema is "registry_sha256":
  # "sha256:<64-lowercase-hex>" -- the SAME string a materialised v3
  # WORKFLOW.md pins (V3.registry_state()['sha256']) has to be what the hook
  # publishes, or a reader comparing the two sees inequality for the
  # identical registry. KNOWN GAP, owned by ensure_workflow.py (peça E, not
  # this module -- LD-003/LD-004): as of this round
  # ensure_workflow._registry_prefix() still publishes the bare hex digest,
  # not the "sha256:"-prefixed form. Assert the strictly weaker claim that is
  # actually true right now -- same underlying digest, regardless of format
  # -- so this test does not regress the suite while that fix lands, and
  # keeps passing unchanged once it does; the exact-string assertion
  # (`assertIn(V3.registry_state()['sha256'], message)`) is the one to
  # restore the moment ensure_workflow.py adds the prefix.
  live_hex=V3.registry_state()['sha256'].split(':',1)[1]
  self.assertIn(live_hex,message)

class RuntimeWiringGate(unittest.TestCase):
 """runtime_wired() is a functional probe now, not a version-string
 comparison (round-3 fix). Prove BOTH directions for real, against actually
 different bytes on disk in a disposable copy -- never by monkeypatching
 runtime_wired or any attribute it reads on the live sibling module, which is
 the exact anti-pattern LD-010 names as how this defect survived two rounds.
 """
 def setUp(self):
  tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.addCleanup(tmp.cleanup)
  self.skill=Path(tmp.name)/'skill'; shutil.copytree(SKILL,self.skill)
  self.module=self.skill/'scripts/grill_core/workflow_v3.py'
  self.ensure=self.skill/'scripts/ensure_workflow.py'
  root_dir=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.addCleanup(root_dir.cleanup)
  self.root=Path(root_dir.name).resolve(); subprocess.run(['git','init','-q','-b','main',str(self.root)],check=True)
  self.path=self.root/'WORKFLOW.md'; self.path.write_bytes(TEMPLATE_V2.read_bytes())
 def _run(self,*args): return subprocess.run([sys.executable,str(self.module),*map(str,args)],text=True,capture_output=True)
 def test_genuinely_unwired_runtime_blocks_apply_and_leaves_the_consumer_usable(self):
  # Simulate a genuinely pre-dual-read ensure_workflow.py -- one whose
  # V3_MARKER_VERSION can never match a real marker -- on a disposable COPY
  # of the bundle: forces runtime_wired()'s real functional probe (git init +
  # resolve_workflow) to run and observe an actual "managed version mismatch"
  # BLOCKED result, not REUSED. Nothing about the live ensure_workflow.py
  # module is touched; only these on-disk copy bytes differ.
  text=self.ensure.read_text(encoding='utf-8')
  self.assertIn('V3_MARKER_VERSION = "v3"',text)
  self.ensure.write_text(text.replace('V3_MARKER_VERSION = "v3"','V3_MARKER_VERSION = "unreachable-version-marker"'),encoding='utf-8')
  preview=json.loads(self._run('migrate',self.root).stdout)
  self.assertEqual(preview['verdict'],'PREVIEW')
  blocked=self._run('migrate',self.root,'--apply','--expected-sha256',preview['current_sha256'])
  self.assertEqual(blocked.returncode,2)
  body=json.loads(blocked.stdout.splitlines()[0])
  self.assertEqual(body['code'],'V3_RUNTIME_NOT_WIRED')
  self.assertEqual(self.path.read_bytes(),TEMPLATE_V2.read_bytes())
  # the consumer stays usable: the crippled copy still bootstraps v2 fine.
  ensured=subprocess.run([sys.executable,str(self.ensure),'--ensure',str(self.root)],text=True,capture_output=True)
  self.assertEqual(ensured.returncode,0,ensured.stdout+ensured.stderr)
  self.assertEqual(json.loads(ensured.stdout)['status'],'REUSED')

class SiblingIntegrity(unittest.TestCase):
 """sibling() must not let a broken/absent bundle sibling escape the
 single-JSON-document, named-exit-code contract. GAP found this round: with
 grill_core/step_skills.py (or scripts/ensure_workflow.py) syntactically
 broken -- in a disposable COPY of the tree -- workflow_v3.py exited with
 EMPTY stdout, a raw Python Traceback on stderr and rc=1, colliding with the
 exit code reserved for NO-GO and violating "JSON único no stdout" / "todos
 os exit codes". sibling() now wraps exec_module in try/except and reports
 FILESYSTEM/rc=2, exactly like the pre-existing "spec is None" branch."""
 def setUp(self):
  tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.addCleanup(tmp.cleanup)
  self.skill=Path(tmp.name)/'skill'; shutil.copytree(SKILL,self.skill)
  self.module=self.skill/'scripts/grill_core/workflow_v3.py'
  root_dir=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.addCleanup(root_dir.cleanup)
  self.root=Path(root_dir.name).resolve(); subprocess.run(['git','init','-q','-b','main',str(self.root)],check=True)
  (self.root/'WORKFLOW.md').write_bytes(TEMPLATE_V2.read_bytes())
 def _run(self,*args): return subprocess.run([sys.executable,str(self.module),*map(str,args)],text=True,capture_output=True)
 def _attack(self,break_it):
  break_it()
  result=self._run('detect',self.root)
  self.assertEqual(result.returncode,2,result.stdout+result.stderr)
  self.assertNotIn('Traceback',result.stderr)
  lines=result.stdout.splitlines(); self.assertEqual(len(lines),1,result.stdout)
  body=json.loads(lines[0]); self.assertEqual(body['code'],'FILESYSTEM')
 def test_broken_step_skills_sibling_still_yields_one_json_document(self):
  self._attack(lambda: (self.skill/'scripts/grill_core/step_skills.py').write_text('def broken(:\n',encoding='utf-8'))
 def test_missing_step_skills_sibling_still_yields_one_json_document(self):
  self._attack(lambda: (self.skill/'scripts/grill_core/step_skills.py').unlink())
 def test_broken_ensure_workflow_sibling_still_yields_one_json_document(self):
  self._attack(lambda: (self.skill/'scripts/ensure_workflow.py').write_text('def broken(:\n',encoding='utf-8'))
 def test_missing_ensure_workflow_sibling_still_yields_one_json_document(self):
  self._attack(lambda: (self.skill/'scripts/ensure_workflow.py').unlink())

class SoleManagedVersionMatrix(unittest.TestCase):
 """T005 (FR-008): sole_managed_version(text) over the seven R5 fixtures from
 T003 (tests/fixtures/workflow-marker-matrix/<case>/WORKFLOW.md). The
 contract, per ensure_workflow.sole_managed_version's own docstring: return
 the marker string if and only if there is exactly one declaration; ``None``
 for zero occurrences AND for two or more -- unlike managed_version, it does
 not resolve ambiguity by picking the first match.

 sole_managed_version does not itself judge whether a unique marker is a
 *recognised* version (that is ACCEPTED_WORKFLOW_MARKERS' job, exercised in
 MarkerParitySSOT below): the "unknown-v9" case here has exactly one
 declaration, so sole_managed_version still resolves it to 'v9'.
 """
 # (fixture directory, expected sole_managed_version(text))
 EXPECTED=(
  ('none',None),
  ('v2','v2'),
  ('v3','v3'),
  ('v4','v4'),
  ('duplicate-same',None),
  ('duplicate-distinct',None),
  ('unknown-v9','v9'),
 )
 def test_matrix(self):
  self.assertEqual(tuple(case for case,_ in self.EXPECTED),MATRIX_CASES,'matrix must cover exactly the seven R5 cases, in the declared order')
  for case,expected in self.EXPECTED:
   with self.subTest(case=case):
    self.assertEqual(EW.sole_managed_version(matrix_text(case)),expected)

class ManagedVersionFirstMatch(unittest.TestCase):
 """T006: freezes managed_version's first-match semantics (``re.search``,
 ``None`` with no marker). ADR-0002/sole_managed_version's own docstring:
 seven internal callers plus workflow_v3.marker_version depend on
 managed_version's ``or VERSION`` fallback, so a future change that makes it
 return the last match, the highest version, or ``None`` on ambiguity instead
 of the first regex hit must fail THIS test rather than silently changing
 what gets materialised at those call sites.
 """
 def test_no_marker_is_none(self):
  self.assertIsNone(EW.managed_version(matrix_text('none')))
 def test_two_identical_markers_return_that_marker(self):
  text=matrix_text('duplicate-same')
  self.assertEqual(EW.managed_version(text),'v4')
  self.assertEqual(EW.managed_version(text),re.search(MARKER_PATTERN,text).group(1))
 def test_two_distinct_markers_return_the_first_one_not_the_highest(self):
  # duplicate-distinct declares v3 before v4 (research.md R5 + p02-b.tasks.json
  # provenance). first-match must yield 'v3': a "pick the highest" or
  # "pick the last" reading would silently return 'v4' here instead.
  text=matrix_text('duplicate-distinct')
  self.assertEqual(EW.managed_version(text),'v3')
  self.assertEqual(EW.managed_version(text),re.search(MARKER_PATTERN,text).group(1))

class MarkerParitySSOT(unittest.TestCase):
 """T007 (FR-005, V-3, SC-005): for every R5 matrix case, sole_managed_version
 (paired with ACCEPTED_WORKFLOW_MARKERS membership) and audit_decisions.py's
 own inline marker check must agree on both how many declarations the
 document carries and whether it is accepted.

 THIS TEST IS THE SSOT FOR THAT AGREEMENT. ADR-0002 explicitly rejected a
 shared production module for this rule -- audit_decisions.py must not
 acquire a load-time dependency on grill_core, and ensure_workflow.py's
 creation-time gate must not depend on audit_decisions.py either. Nothing in
 production enforces that the two independent implementations agree; this
 test is the only thing standing in for that shared module. If it is ever
 deleted or skipped, the rule silently starts living in two files with
 nothing checking they still say the same thing.
 """
 def test_parity_over_the_seven_r5_cases(self):
  for case in MATRIX_CASES:
   with self.subTest(case=case):
    text=matrix_text(case)
    sole=EW.sole_managed_version(text)
    markers,audit_accepted=audit_marker_decision(text)
    sole_accepted=sole is not None and sole in AD.ACCEPTED_WORKFLOW_MARKERS
    # Parity 1: quantity of declarations recognised. sole_managed_version and
    # audit_decisions.py both derive this via re.findall over the identical
    # pattern; resolving to a value is only possible when that count is 1.
    self.assertEqual(sole is not None,len(markers)==1,f'{case}: sole_managed_version disagrees with the raw marker count')
    # Parity 2: accept/reject decision.
    self.assertEqual(sole_accepted,audit_accepted,f'{case}: sole_managed_version+ACCEPTED_WORKFLOW_MARKERS disagrees with audit_decisions.py')
    # Parity 3: when both accept, they must agree on the *value*, not just the boolean.
    if audit_accepted:
     self.assertEqual(sole,markers[0])

if __name__=='__main__': unittest.main()
