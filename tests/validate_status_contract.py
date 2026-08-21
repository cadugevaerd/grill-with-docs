#!/usr/bin/env python3
"""Matriz pública do contrato grill_workspace.py status (somente interface CLI)."""
from __future__ import annotations
import concurrent.futures, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest
from unittest import mock
from pathlib import Path

PLUGIN=Path(__file__).resolve().parents[1]/"plugin"
WS=PLUGIN/"skills/grill-with-docs/scripts/grill_workspace.py"
WORKFLOW_TEMPLATE=PLUGIN/"skills/grill-with-docs/assets/WORKFLOW.template.md"
STATUS=PLUGIN/"skills/grill-with-docs/scripts/grill_status.py"

def cli(script,*args):
    return subprocess.run([sys.executable,str(script),*(str(x) for x in args)],text=True,capture_output=True,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
def status(root,*args):
    # Exercise the public CORE entry point; direct grill_status invocation
    # would bypass status governance and timeout handling.
    p=cli(WS,"status",root,*args)
    assert len(p.stdout.splitlines())==1,(p.stdout,p.stderr)
    return p,json.loads(p.stdout)
def status_markdown(root,*args):
    return cli(WS,"status",root,"--format","markdown",*args)
class StatusPublicContract(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.r=Path(self.t.name)
        subprocess.run(["git","init","-q","-b","main",str(self.r)],check=True)
        for k,v in (("user.email","t@example.invalid"),("user.name","status tests")): subprocess.run(["git","-C",str(self.r),"config",k,v],check=True)
        # init now pins the project-wide workflow, so the fixture needs the real
        # managed template instead of a placeholder that fails compatibility.
        shutil.copyfile(WORKFLOW_TEMPLATE, self.r/"WORKFLOW.md")
        subprocess.run(["git","-C",str(self.r),"add","."],check=True); subprocess.run(["git","-C",str(self.r),"commit","-qm","init"],check=True)
    def tearDown(self): self.t.cleanup()
    def item(self, wid="work-a", root=None):
        root=root or self.r; p=cli(WS,"init",root,"--type","feature","--slug","alpha","--work-id",wid, "--skip-backlog"); self.assertEqual(p.returncode,0,p.stderr); return root/".grill/work-items"/wid
    def test_core_entrypoint_zero_items_exact_schema(self):
        p,x=status(self.r); self.assertEqual(p.returncode,0)
        self.assertEqual(x["schema"],"grill-status/v1"); self.assertEqual(x["verdict"],"OK")
        self.assertEqual(x["code"],"EMPTY"); self.assertEqual(x["next_action"],"iniciar")
        self.assertEqual(x["summary"],{"total":0,"in_progress":0,"blocked":0,"completed":0})
    def test_one_item_top_level_and_item_schema(self):
        self.item(); p,x=status(self.r); self.assertEqual(p.returncode,0); self.assertEqual(set(x),{"schema","verdict","code","project_root","summary","work_items","next_action"}); item=x["work_items"][0]
        for k in ("work_id","type","slug","fingerprint","locations","recorded","planning","development","governance","blockers","findings","closed","operational_status","pending_reasons","next_gate"): self.assertIn(k,item)
    def test_markdown_empty_workspace_requires_initialization(self):
        p=status_markdown(self.r); self.assertEqual(p.returncode,0); self.assertEqual(p.stderr,"")
        self.assertEqual(p.stdout,"| Item | Status | Pendência |\n|---|---|---|\n| workspace | pending | GWD não inicializado |\n")
    def test_markdown_all_good_only_for_coherently_closed_item(self):
        self.item(); self._terminal(); p=status_markdown(self.r)
        self.assertEqual((p.returncode,p.stderr,p.stdout),(0,"","all good\n"))
    def test_markdown_omits_closed_items_and_reports_pending_stage(self):
        self.item("closed"); self._terminal("closed"); self.item("open")
        p=status_markdown(self.r); self.assertEqual(p.returncode,0); self.assertNotIn("| closed |",p.stdout)
        self.assertIn("| open | pending | etapa GWD pendente: specify |",p.stdout)
    def test_markdown_terminal_contradiction_is_blocked(self):
        self.item(); path=self.r/".grill/work-items/work-a/state.json"; value=json.loads(path.read_text(encoding="utf-8"))
        value["status"]="complete"; value["milestone_status"]="completed"; path.write_text(json.dumps(value),encoding="utf-8")
        p=status_markdown(self.r); self.assertEqual(p.returncode,0); self.assertIn("| work-a | blocked |",p.stdout)
        self.assertIn("fechamento inconsistente: ",p.stdout)
    def test_markdown_in_progress_stage_is_named(self):
        item=self.item(); path=item/"state.json"; value=json.loads(path.read_text(encoding="utf-8"))
        value["development"]["steps"]["specify"]="in-progress"; path.write_text(json.dumps(value),encoding="utf-8")
        p=status_markdown(self.r); self.assertEqual(p.returncode,0); self.assertIn("| work-a | in-progress | etapa GWD em andamento: specify |",p.stdout)
    def test_markdown_escapes_cells_deterministically(self):
        spec=importlib.util.spec_from_file_location("status_markdown_contract",STATUS)
        if spec is None or spec.loader is None: self.fail("unable to load status module")
        module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
        payload={"verdict":"OK","code":"OK","work_items":[{"work_id":"a|b\\c","closed":False,"operational_status":"pending","pending_reasons":["line one\nline|two\\"]}]}
        self.assertEqual(module.render_markdown(payload),"| Item | Status | Pendência |\n|---|---|---|\n| a\\|b\\\\c | pending | line one line\\|two\\\\ |\n")
    def test_missing_work_id_is_one_json_exit1(self):
        p,x=status(self.r,"--work-id","absent"); self.assertEqual(p.returncode,1); self.assertEqual(x["code"],"WORK-ITEM-MISSING"); self.assertEqual(len(p.stdout.splitlines()),1); self.assertEqual(p.stderr,"")
    def test_current_worktree_is_not_cross_worktree(self):
        self.item(); _,b=status(self.r); _,d=status(self.r,"--current-worktree"); self.assertEqual(len(b["work_items"]),1); self.assertEqual(len(d["work_items"]),1)
    def test_repeated_output_is_byte_identical(self):
        self.item(); a,_=status(self.r); b,_=status(self.r); self.assertEqual(a.stdout,b.stdout); self.assertEqual(b.stderr,"")
    def _git(self,*args): subprocess.run(["git","-C",str(self.r),*args],check=True,capture_output=True)
    def _terminal(self, wid="work-a"):
        p=self.r/".grill/work-items"/wid/"state.json"; d=json.loads(p.read_text(encoding="utf-8"))
        d["status"]="complete"; d["milestone_status"]="completed"; d["active_phase"]=None; d["audit_verdict"]="GO"
        d["development"]["steps"]={step:"complete" for step in d["development"]["sequence"]}; d["development"]["current_step"]="complete"
        p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
        roadmap=self.r/".grill/work-items"/wid/"ROADMAP.md"
        roadmap.write_text(roadmap.read_text(encoding="utf-8").replace("- state: planned","- state: complete"),encoding="utf-8")
    def _findings(self, wid="work-a"):
        _,x=status(self.r); return next(w for w in x["work_items"] if w["work_id"]==wid)["findings"]
    def _switch_to_phase_branch(self, name="011-gauntlet-loop"):
        self.item(); self._git("add","."); self._git("commit","-qm","bundle")
        self._git("checkout","-qb",name); return name
    def _checkpoint(self, step, state):
        p=cli(WS,"checkpoint",self.r,"--work-id","work-a","--step",step,
              "--state",state,"--evidence","WORKFLOW.md","--reason",f"contract {step} {state}")
        self.assertEqual(len(p.stdout.splitlines()),1,(p.stdout,p.stderr))
        payload=json.loads(p.stdout); self.assertEqual(p.returncode,0,payload); self.assertEqual(p.stderr,"")
        return payload
    def _development(self):
        path=self.r/".grill/work-items/work-a/state.json"
        return json.loads(path.read_text(encoding="utf-8"))["development"]

    # Branch gravada é provenance do init e também o fallback fail-closed até
    # o primeiro checkpoint specify anexar explicitamente a branch de execução.
    def test_drift_is_silent_on_the_recorded_branch_however_many_commits(self):
        self.item(); self._git("add","."); self._git("commit","-qm","bundle")
        for n in range(3):
            (self.r/f"f{n}.txt").write_text("x",encoding="utf-8"); self._git("add","."); self._git("commit","-qm",f"c{n}")
        self.assertEqual(self._findings(),[])
    def test_phase_branch_switch_without_binding_keeps_live_vs_recorded(self):
        self._switch_to_phase_branch()
        self._git("show-ref","--verify","refs/heads/main")
        _,payload=status(self.r,"--work-id","work-a","--current-worktree")
        item=payload["work_items"][0]; location=item["locations"][0]
        self.assertIn("LIVE-VS-RECORDED",item["findings"])
        self.assertEqual(item["recorded"]["branch"],"main")
        self.assertEqual(location["branch"],"011-gauntlet-loop")
        self.assertEqual(item["development"]["execution_branch"],"main")
        self.assertNotEqual(item["recorded"]["branch"],location["branch"])

    def test_specify_checkpoint_binds_phase_branch_and_status_exposes_it(self):
        self._switch_to_phase_branch()
        self.assertIn("LIVE-VS-RECORDED",self._findings())
        checkpoint=self._checkpoint("specify","in-progress")
        self.assertEqual(checkpoint["verdict"],"UPDATED")
        self.assertEqual(checkpoint["execution_branch"],"011-gauntlet-loop")
        development=self._development()
        self.assertEqual(development["execution_branch"],"011-gauntlet-loop")
        self.assertEqual(development["audit"][-1]["execution_branch"],"011-gauntlet-loop")

        state_path=self.r/".grill/work-items/work-a/state.json"
        before_reuse=state_path.read_bytes(),state_path.stat().st_mtime_ns
        reused=self._checkpoint("specify","in-progress")
        self.assertEqual(reused["verdict"],"REUSED")
        self.assertEqual(reused["execution_branch"],"011-gauntlet-loop")
        self.assertEqual((state_path.read_bytes(),state_path.stat().st_mtime_ns),before_reuse)
        self.assertEqual(self._development()["audit"][-1]["execution_branch"],"011-gauntlet-loop")

        process,payload=status(self.r,"--work-id","work-a","--current-worktree")
        item=payload["work_items"][0]
        self.assertEqual((process.returncode,payload["verdict"]),(0,"OK"),payload)
        self.assertNotIn("LIVE-VS-RECORDED",item["findings"])
        self.assertEqual(item["recorded"]["branch"],"main")
        self.assertEqual(item["locations"][0]["branch"],"011-gauntlet-loop")
        self.assertEqual(item["development"]["execution_branch"],"011-gauntlet-loop")

    def test_phase_turn_archives_and_clears_phase_binding_then_next_specify_binds_new_branch(self):
        self._switch_to_phase_branch(); self._checkpoint("specify","in-progress")
        sequence=self._development()["sequence"]
        self._checkpoint("specify","complete")
        for step in sequence[1:]:
            self._checkpoint(step,"in-progress"); self._checkpoint(step,"complete")
        self.assertEqual(self._development()["execution_branch"],"011-gauntlet-loop")

        turned=cli(WS,"phase-turn",self.r,"--work-id","work-a","--reason","next phase")
        self.assertEqual(len(turned.stdout.splitlines()),1,(turned.stdout,turned.stderr))
        turn_payload=json.loads(turned.stdout)
        self.assertEqual((turned.returncode,turn_payload.get("verdict")),(0,"TURNED"),turn_payload)
        development=self._development()
        self.assertIsNone(development["execution_branch"])
        self.assertEqual(
            development["audit"][-1]["previous_execution_branch"],"011-gauntlet-loop")
        _,payload=status(self.r,"--work-id","work-a","--current-worktree")
        item=payload["work_items"][0]
        self.assertNotIn("LIVE-VS-RECORDED",item["findings"])
        self.assertNotIn("INVALID-DEVELOPMENT-SCHEMA",item["findings"])
        self.assertIsNone(item["development"]["execution_branch"])

        self._git("checkout","-qb","012-next-phase")
        next_phase=self._checkpoint("specify","in-progress")
        self.assertEqual(next_phase["execution_branch"],"012-next-phase")
        development=self._development()
        self.assertEqual(development["execution_branch"],"012-next-phase")
        self.assertEqual(development["audit"][-1]["execution_branch"],"012-next-phase")
        _,payload=status(self.r,"--work-id","work-a","--current-worktree")
        item=payload["work_items"][0]
        self.assertNotIn("LIVE-VS-RECORDED",item["findings"])
        self.assertEqual(item["development"]["execution_branch"],"012-next-phase")

    def test_advanced_legacy_ship_resume_establishes_binding_and_clears_live_finding(self):
        self._switch_to_phase_branch(); state_path=self.r/".grill/work-items/work-a/state.json"
        state=json.loads(state_path.read_text(encoding="utf-8")); development=state["development"]
        self.assertNotIn("execution_branch",development)
        development["steps"]={step:"complete" for step in development["sequence"]}
        development["steps"]["ship"]="blocked"; development["current_step"]="ship"
        development["audit"]=[
            {"step":step,"state":"complete","evidence":[],"reason":"legacy cycle"}
            for step in development["sequence"][:-1]
        ]
        development["audit"].append(
            {"step":"ship","state":"blocked","evidence":[],"reason":"legacy interruption"})
        state_path.write_text(json.dumps(state,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        self.assertIn("LIVE-VS-RECORDED",self._findings())

        resumed=self._checkpoint("ship","in-progress")
        self.assertEqual(resumed["verdict"],"UPDATED")
        self.assertEqual(resumed["execution_branch"],"011-gauntlet-loop")
        after=self._development()
        self.assertEqual(after["execution_branch"],"011-gauntlet-loop")
        self.assertEqual(after["audit"][-1]["execution_branch"],"011-gauntlet-loop")
        self.assertEqual(after["steps"]["ship"],"in-progress")
        _,projected=status(self.r,"--work-id","work-a","--current-worktree")
        item=projected["work_items"][0]
        self.assertNotIn("LIVE-VS-RECORDED",item["findings"])
        self.assertEqual(item["development"]["execution_branch"],"011-gauntlet-loop")

    def test_wrong_live_branch_is_silent_when_the_recorded_branch_is_gone(self):
        self.item(); self._git("add","."); self._git("commit","-qm","bundle")
        self._git("checkout","-qb","fase-dois"); self._git("branch","-D","main")
        self.assertNotIn("LIVE-VS-RECORDED",self._findings())
    def test_terminal_item_without_binding_is_silent_on_another_live_branch(self):
        self.item(); self._git("add","."); self._git("commit","-qm","bundle")
        self._terminal(); self._git("branch","outra"); self._git("checkout","-q","outra")
        self.assertNotIn("LIVE-VS-RECORDED",self._findings())
    def test_incomplete_milestone_without_binding_reports_wrong_live_branch(self):
        self.item(); self._git("add","."); self._git("commit","-qm","bundle")
        p=self.r/".grill/work-items/work-a/state.json"; d=json.loads(p.read_text(encoding="utf-8"))
        d["status"]="complete"
        p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
        self._git("branch","outra"); self._git("checkout","-q","outra")
        self.assertIn("LIVE-VS-RECORDED",self._findings())
    def test_both_heads_stay_visible_for_whoever_needs_the_difference(self):
        self.item(); self._git("add","."); self._git("commit","-qm","bundle")
        _,x=status(self.r); item=x["work_items"][0]
        self.assertTrue(item["recorded"]["head"]); self.assertTrue(item["locations"][0]["head"])
        self.assertNotEqual(item["recorded"]["head"],item["locations"][0]["head"])
        self.assertEqual(item["findings"],[])

    def snapshot_tree(self):
        # `.git/` fica de fora porque o dono dele é o git, não o grill: a
        # manutenção automática cria e remove `.git/objects/maintenance.lock`
        # entre os dois snapshots e reprova um teste que nada escreveu.
        return {p.relative_to(self.r).as_posix():p.read_bytes() for p in self.r.rglob("*")
                if p.is_file() and ".git" not in p.relative_to(self.r).parts}
    def test_read_only_fingerprint(self):
        before=self.snapshot_tree(); status(self.r); after=self.snapshot_tree(); self.assertEqual(before,after)
    def test_markdown_read_only_fingerprint(self):
        before=self.snapshot_tree(); status_markdown(self.r); after=self.snapshot_tree(); self.assertEqual(before,after)
    def test_the_snapshot_still_sees_everything_the_grill_owns(self):
        """Excluir .git/ não pode virar desculpa para o teste não olhar nada."""
        self.item(); tree=self.snapshot_tree()
        self.assertTrue(any(k.startswith(".grill/work-items/") for k in tree))
        self.assertFalse(any(k.startswith(".git/") for k in tree))
    def test_real_worktree_with_spaces_default_aggregates_equal_bundle(self):
        self.item(); secondary=Path(self.t.name)/"secondary worktree"
        subprocess.run(["git","-C",str(self.r),"worktree","add","-b","other",str(secondary)],check=True,capture_output=True)
        target=secondary/".grill/work-items/work-a"; target.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(self.r/".grill/work-items/work-a",target)
        constitution=self.r/".specify/memory/constitution.md"
        if constitution.exists(): (secondary/".specify/memory").mkdir(parents=True,exist_ok=True); shutil.copy2(constitution,secondary/".specify/memory/constitution.md")
        _,x=status(self.r); item=x["work_items"][0]; self.assertEqual(len(item["locations"]),2); self.assertEqual(item["locations"],[*sorted(item["locations"],key=lambda z:(z["worktree"],z["path"]))]); self.assertEqual(len({v["fingerprint"] for v in item.get("variants",[item])}),1)

    def test_current_worktree_excludes_secondary_real_worktree(self):
        self.test_real_worktree_with_spaces_default_aggregates_equal_bundle()
        secondary=Path(self.t.name)/"secondary worktree"; _,main=status(self.r,"--current-worktree"); _,other=status(secondary,"--current-worktree")
        self.assertEqual(len(main["work_items"][0]["locations"]),1); self.assertEqual(len(other["work_items"][0]["locations"]),1); self.assertTrue(other["work_items"][0]["locations"][0]["current"])

    def test_divergent_duplicate_preserves_both_locations(self):
        self.test_real_worktree_with_spaces_default_aggregates_equal_bundle(); secondary=Path(self.t.name)/"secondary worktree"; (secondary/".grill/work-items/work-a/state.json").write_bytes(b'{"status":"divergent"}')
        p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertEqual(x["code"],"DUPLICATE-WORK-ID"); self.assertEqual(len(x["work_items"][0]["locations"]),2); self.assertEqual(len(x["work_items"][0]["variants"]),2)
    def test_live_branch_head_is_reported(self):
        item=self.item(); p,x=status(self.r); loc=x["work_items"][0]["locations"][0]; self.assertEqual(loc["branch"],"main"); self.assertTrue(loc["head"])
    def test_legacy_untracked_is_explicit(self):
        item=self.item(); s=json.loads((item/"state.json").read_text()); s.pop("development",None); (item/"state.json").write_text(json.dumps(s)); p,x=status(self.r); self.assertEqual(x["work_items"][0]["development"]["tracking"],"legacy-untracked")
    def test_development_invalid_is_blocked(self):
        item=self.item(); s=json.loads((item/"state.json").read_text()); s["development"]={"schema":"bad","steps":{}}; (item/"state.json").write_text(json.dumps(s)); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn("INVALID-DEVELOPMENT-SCHEMA",x["work_items"][0]["findings"])
    def test_malformed_state_json_is_exact_exit1(self):
        item=self.item(); (item/"state.json").write_bytes(b"{"); p,x=status(self.r); self.assertEqual(p.returncode,1); self.assertEqual(x["code"],"MALFORMED-JSON"); self.assertEqual(p.stderr,"")

    def test_invalid_utf8_state_is_exact(self):
        item=self.item(); (item/"state.json").write_bytes(b"\xff"); p,x=status(self.r); self.assertEqual(p.returncode,1); self.assertEqual(x["code"],"INVALID-UTF8")

    def test_direct_external_symlink_state_hides_secret(self):
        item=self.item(); secret=Path(self.t.name)/"secret"; secret.write_text("TOP-SECRET"); (item/"state.json").unlink(); (item/"state.json").symlink_to(secret); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-FILE"}); self.assertNotIn("TOP-SECRET",p.stdout)
    def test_broken_symlink_is_rejected(self):
        item=self.item(); (item/"state.json").unlink(); (item/"state.json").symlink_to("missing"); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-FILE"})

    def test_work_item_symlink_is_rejected(self):
        self.item(); outside=Path(self.t.name)/"outside"; outside.mkdir(); d=self.r/".grill/work-items/work-b"; d.symlink_to(outside,target_is_directory=True); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-WORK-ITEM"})

    def test_snapshot_contains_mtimes(self):
        self.item(); _,x=status(self.r); self.assertTrue(x["work_items"][0]["snapshot"]); self.assertIn("mtime_ns",next(iter(x["work_items"][0]["snapshot"].values())))
    def test_concurrent_readers_are_deterministic(self):
        self.item()
        with concurrent.futures.ThreadPoolExecutor(4) as ex: out=list(ex.map(lambda _:status(self.r)[0].stdout,range(8)))
        self.assertEqual(len(set(out)),1)
    def test_fingerprint_is_full_bundle(self):
        item=self.item(); p,x=status(self.r); fp=x["work_items"][0]["fingerprint"]; self.assertEqual(len(fp),64); (item/"extra").write_text("x"); p,y=status(self.r); self.assertNotEqual(fp,y["work_items"][0]["fingerprint"])
    def test_planning_has_public_execution_and_phase_state(self):
        self.item(); _,x=status(self.r); planning=x["work_items"][0]["planning"]; self.assertIn("execution_order",planning); self.assertIn("phases",planning); self.assertIn("phase_state",planning)
    def test_governance_has_receipt_audit_constitution_check(self):
        self.item(); _,x=status(self.r); g=x["work_items"][0]["governance"]; self.assertTrue({"receipt","reconciled"}&set(g)); self.assertIn("audit",g); self.assertIn("constitution",g); self.assertIn("check",g)
    def test_stdout_is_exactly_json_and_stderr_empty(self):
        self.item(); p,_=status(self.r); self.assertEqual(p.stderr,""); json.loads(p.stdout)
    def test_receipt_direct_symlink_is_rejected_without_following(self):
        self.item(); receipts=self.r/".grill/global/receipts"; receipts.mkdir(parents=True,exist_ok=True); secret=Path(self.t.name)/"receipt-secret"; secret.write_text("SECRET"); (receipts/"work-a.json").symlink_to(secret); p,x=status(self.r); self.assertEqual(p.returncode,2); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-FILE"}); self.assertNotIn("SECRET",p.stdout)
    def test_constitution_external_symlink_is_rejected(self):
        self.item(); path=self.r/".specify/memory/constitution.md"; path.parent.mkdir(parents=True,exist_ok=True); secret=Path(self.t.name)/"constitution-secret"; secret.write_text("SECRET"); path.unlink(missing_ok=True); path.symlink_to(secret); p,x=status(self.r); self.assertEqual(p.returncode,3); self.assertIn(x["code"],{"SYMLINK-REJECTED","UNSAFE-FILE"}); self.assertNotIn("SECRET",p.stdout)
    def test_broken_constitution_symlink_reports_security_cause(self):
        self.item(); path=self.r/".specify/memory/constitution.md"; path.unlink(); path.symlink_to("missing-constitution")
        p,x=status(self.r); self.assertEqual(p.returncode,3); self.assertEqual(x["code"],"SYMLINK-REJECTED"); self.assertEqual(p.stderr,"")
    def test_bundle_reader_uses_descriptor_not_path_read_bytes(self):
        item=self.item(); spec=importlib.util.spec_from_file_location("workspace_descriptor_contract",WS)
        if spec is None or spec.loader is None: self.fail("unable to load workspace module")
        module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
        with mock.patch.object(Path,"read_bytes",side_effect=AssertionError("unsafe Path.read_bytes")):
            bundle=module.read_local_bundle(self.r,item)
        self.assertEqual(bundle.work_id,"work-a"); self.assertIn("WORK-ITEM.json",bundle.files)
if __name__=="__main__": unittest.main()
