#!/usr/bin/env python3
"""Contract matrix for `workflow-step-skills/v1` and the fail-closed step->skill resolver.

Barra: plan section 4.1 (registry literal, skill_resolution_sha256, skill_invocation_key,
skill-invocation/v1), section 22 "Workflow -> skill canonica", section 23 (canonical
invocation, BLOCKED_CAPABILITY, STALE_SKILL_RESOLUTION, no DIRECT|EMULATED|BEST_EFFORT).

Stdlib only, no network, no real specify/node/backlogctl: the runtime catalogue is a
frozen fixture captured read-only from `.claude/skills` during phase 0.
"""
import ast, contextlib, copy, hashlib, importlib.util, json, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plugin/skills/grill-with-docs/scripts"
MODULE = SCRIPTS / "grill_core/step_skills.py"
REGISTRY = REPO / "plugin/skills/grill-with-docs/assets/workflow-step-skills.json"
TRUSTED_CATALOGS_ASSET = REPO / "plugin/skills/grill-with-docs/assets/workflow-trusted-catalogs.json"
CATALOG = REPO / "tests/fixtures/workflow-step-skills/claude-catalog.json"

# Frozen. Any edit to the registry asset must land here in the same commit.
# LD-001: this is the SHA-256 of the asset's literal on-disk bytes -- the exact
# string `sha256sum workflow-step-skills.json` prints -- never a JCS digest of
# the parsed document. Verified independently in
# Registry.test_registry_sha256_matches_plain_sha256sum_no_jcs_involved.
REGISTRY_SHA256 = "sha256:9a326f32523c926f82b190dd9a08b11341614d112ad92d78c33e59fe015b478e"
STEPS = ("specify", "plan", "checklist", "tasks", "analyze", "agent-assign",
         "agent-execute", "converge", "verify", "review", "ship")
TRUSTED = "claude-code-local-skills"
DIGEST = "sha256:" + "0" * 64


def _load():
    spec = importlib.util.spec_from_file_location("grill_core.step_skills", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ss = _load()


def catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def registry_bytes():
    """LD-001: what the resolver actually hashes -- literal on-disk bytes, never
    a re-parsed/re-serialized document."""
    return REGISTRY.read_bytes()


def trusted(cat=None):
    cat = cat or catalog()
    return {cat["catalog_id"]: cat["catalog_sha256"]}


@contextlib.contextmanager
def trusted_catalogs_file(mapping):
    """Round-3 repair: the production signature only accepts a *path* override
    for the catalogue trust pin, never an in-memory Mapping a caller (or an
    attacker who also controls the catalogue) assembles at call time. Tests
    that need a non-default trust pin write a real `workflow-trusted-
    catalogs/v1` document to disk, exactly like the shipped asset, and pass
    its path -- same as any legitimate caller would have to."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "trusted-catalogs.json"
        path.write_text(
            json.dumps({"schema": ss.TRUSTED_CATALOGS_SCHEMA, "workflow_version": ss.WORKFLOW_VERSION,
                        "catalogs": mapping}),
            encoding="utf-8",
        )
        yield path


class Base(unittest.TestCase):
    def resolve(self, step="verify", runtime="claude", sha=None, **kw):
        cat = kw.pop("catalog", None)
        if cat is None:
            cat = catalog()
        kw.setdefault("registry", registry_bytes())
        if "trusted_catalogs_path" in kw:
            return ss.resolve_workflow_skill(step, runtime, sha or REGISTRY_SHA256, catalog=cat, **kw)
        with trusted_catalogs_file(trusted(cat) if cat else {}) as path:
            kw["trusted_catalogs_path"] = path
            return ss.resolve_workflow_skill(step, runtime, sha or REGISTRY_SHA256, catalog=cat, **kw)

    def blocked(self, reason, **kw):
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.resolve(**kw)
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (ss.BLOCKED_CAPABILITY, reason))
        return ctx.exception

    def stale(self, reason, **kw):
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.resolve(**kw)
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (ss.STALE_SKILL_RESOLUTION, reason))
        return ctx.exception

    def patch_entry(self, entrypoint, recompute=True, **fields):
        """Mutate a catalog entry. ``recompute=True`` (the default) mimics a
        legitimate catalog publisher: it recomputes ``catalog_sha256`` over the
        new entries, same as the fixture always does. ``recompute=False`` mimics
        an attacker who mutates entries but leaves ``catalog_sha256`` at the
        value ``trusted_catalogs`` already authorizes (round-1 finding: probe1)
        -- the digest a legitimate caller would never let drift silently."""
        cat = catalog()
        for entry in cat["entries"]:
            if entry["entrypoint"] == entrypoint:
                entry.update(fields)
        if recompute:
            cat["catalog_sha256"] = ss.sha256_jcs(cat["entries"])
        return cat


# --------------------------------------------------------------------------
# 22: "registry possui exatamente os 11 step_id, identidade logica unica"
# --------------------------------------------------------------------------
class Registry(Base):
    def test_asset_parses_strictly_and_hash_is_frozen(self):
        document, sha = ss.load_registry(REGISTRY)
        self.assertEqual(document["schema"], "workflow-step-skills/v1")
        self.assertEqual(document["workflow_version"], "v3")
        self.assertEqual(sha, REGISTRY_SHA256)
        self.assertEqual(sha, ss.registry_sha256(registry_bytes()))

    def test_registry_sha256_matches_plain_sha256sum_no_jcs_involved(self):
        """LD-001, the two-path check: a human running ``sha256sum`` on the asset
        -- stdlib hashlib directly, no parsing, no JCS, nothing this module
        implements -- must get the exact string the resolver pins to. Before the
        fix this module hashed the JCS re-serialization of the parsed document
        (sha256:39f56f8d...) instead of the file's own bytes (sha256:9a326f32...):
        two different strings for the same asset."""
        raw = registry_bytes()
        plain = "sha256:" + hashlib.sha256(raw).hexdigest()
        self.assertEqual(plain, REGISTRY_SHA256)
        self.assertEqual(plain, ss.registry_sha256(raw))
        self.assertEqual(plain, ss.load_registry(REGISTRY)[1])
        # The old (wrong) JCS-of-the-parsed-document reading must NOT be what
        # registry_sha256 reports any more -- that was the round-1 bug.
        self.assertNotEqual(plain, ss.sha256_jcs(registry()))

    def test_byte_different_registry_never_collapses_to_the_same_pin(self):
        """probe2: JCS canonicalizes away key order and whitespace, so two
        byte-different files could share one JCS digest. The bytes-hash must not
        collapse them, and a pin minted for one file must reject the other."""
        raw = registry_bytes()
        # Re-serialize with different whitespace but the SAME key order (JSON
        # objects preserve insertion order on load/dump) -- the registry's step
        # order is itself normative, so a reordering would fail validation for
        # an unrelated reason (REGISTRY_STEP_SET) and never reach the digest
        # comparison this test targets.
        reordered = json.dumps(json.loads(raw), indent=4).encode("utf-8")
        self.assertNotEqual(raw, reordered)
        self.assertEqual(json.loads(raw), json.loads(reordered))  # same document
        sha_raw = ss.registry_sha256(raw)
        sha_reordered = ss.registry_sha256(reordered)
        self.assertNotEqual(sha_raw, sha_reordered)
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.resolve_workflow_skill("verify", "claude", sha_raw, registry=reordered, catalog=catalog())
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.STALE_SKILL_RESOLUTION, "REGISTRY_SHA256_MISMATCH"))

    def test_registry_param_rejects_a_pre_parsed_mapping(self):
        """LD-001: ``registry=`` takes raw bytes, never an already-parsed dict --
        a Mapping cannot prove what a human would get from ``sha256sum`` on the
        real file, so the resolver must refuse it instead of guessing a digest."""
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.resolve_workflow_skill("verify", "claude", REGISTRY_SHA256, registry=registry(), catalog=catalog())
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.BLOCKED_CAPABILITY, "REGISTRY_INVALID"))

    def test_exactly_eleven_steps_in_sequence_order(self):
        document = registry()
        self.assertEqual(tuple(document["steps"]), STEPS)
        self.assertEqual(STEPS, ss.SEQUENCE)

    def test_sequence_matches_the_live_workspace_and_status_constants(self):
        text = (SCRIPTS / "grill_workspace.py").read_text(encoding="utf-8")
        status = (SCRIPTS / "grill_status.py").read_text(encoding="utf-8")
        literal = "SEQUENCE = " + json.dumps(list(STEPS)).replace('", "', '", "')
        self.assertIn(literal, text)
        self.assertIn(literal, status)
        template = json.loads((REPO / "plugin/skills/grill-with-docs/assets/state.template.json").read_text())
        self.assertEqual(tuple(template["development"]["sequence"]), STEPS)

    def test_logical_identity_is_unique_per_step(self):
        document = registry()
        ids = [document["steps"][s]["skill_id"] for s in STEPS]
        self.assertEqual(len(set(ids)), 11)
        for runtime in ss.RUNTIMES:
            eps = [document["steps"][s]["resolutions"][runtime].get("entrypoint") for s in STEPS]
            eps = [e for e in eps if e]
            self.assertEqual(len(set(eps)), len(eps), runtime)

    def test_every_step_is_required_and_only_ship_needs_human_authorization(self):
        document = registry()
        for step in STEPS:
            entry = document["steps"][step]
            self.assertIs(entry["required"], True, step)
            self.assertIs(entry["human_authorization_required"], step == "ship", step)

    def test_three_runtimes_and_only_claude_is_proven(self):
        document = registry()
        self.assertEqual(document["runtimes"], ["hermes", "claude", "codex"])
        for step in STEPS:
            res = document["steps"][step]["resolutions"]
            self.assertEqual(set(res), set(ss.RUNTIMES))
            self.assertIs(res["claude"]["resolved"], True, step)
            for runtime in ("hermes", "codex"):
                self.assertIs(res[runtime]["resolved"], False, (step, runtime))
                self.assertIn(res[runtime]["unresolved_reason"], ss.UNRESOLVED_REASONS)

    def test_registry_never_freezes_the_unproven_plan_literals_as_entrypoints(self):
        """Plan 4.1 skill ids are the PROPOSED logical contract; phase 0 resolved the real ones."""
        document = registry()
        proposed = {document["steps"][s]["proposed_skill_id"] for s in STEPS}
        self.assertIn("agent-execute", proposed)
        entrypoints = {document["steps"][s]["resolutions"]["claude"]["entrypoint"] for s in STEPS}
        for fiction in ("agent-execute", "agent-assign", "converge", "speckit.specify",
                        "verify-review-ship.verify"):
            self.assertNotIn(fiction, entrypoints)

    def test_every_claude_entrypoint_is_a_real_observed_skill(self):
        document = registry()
        observed = {e["entrypoint"] for e in catalog()["entries"]}
        for step in STEPS:
            self.assertIn(document["steps"][step]["resolutions"]["claude"]["entrypoint"], observed, step)


# --------------------------------------------------------------------------
# 22: "entrada ausente, duplicada, desconhecida ou ambigua falha fechado"
# --------------------------------------------------------------------------
class RegistrySchema(Base):
    def mutate(self, fn):
        document = registry()
        fn(document)
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.validate_registry(document)
        self.assertEqual(ctx.exception.code, ss.BLOCKED_CAPABILITY)
        return ctx.exception.reason

    def test_missing_step_fails_closed(self):
        self.assertEqual(self.mutate(lambda d: d["steps"].pop("ship")), "REGISTRY_STEP_SET")

    def test_unknown_step_fails_closed(self):
        self.assertEqual(self.mutate(lambda d: d["steps"].update({"implement": d["steps"]["plan"]})),
                         "REGISTRY_STEP_SET")

    def test_out_of_order_steps_fail_closed(self):
        def swap(d):
            d["steps"] = {k: d["steps"][k] for k in reversed(STEPS)}
        self.assertEqual(self.mutate(swap), "REGISTRY_STEP_SET")

    def test_duplicate_logical_identity_fails_closed(self):
        def dup(d):
            d["steps"]["review"]["skill_id"] = d["steps"]["verify"]["skill_id"]
        self.assertEqual(self.mutate(dup), "REGISTRY_DUPLICATE_SKILL_ID")

    def test_ambiguous_entrypoint_in_registry_fails_closed(self):
        def dup(d):
            d["steps"]["review"]["resolutions"]["claude"]["entrypoint"] = "speckit-verify-review-ship-verify"
        self.assertEqual(self.mutate(dup), "REGISTRY_DUPLICATE_ENTRYPOINT")

    def test_unknown_top_level_key_fails_closed(self):
        self.assertEqual(self.mutate(lambda d: d.update({"fallback": "DIRECT"})), "REGISTRY_INVALID")

    def test_unknown_step_key_fails_closed(self):
        self.assertEqual(self.mutate(lambda d: d["steps"]["plan"].update({"emulate": True})),
                         "REGISTRY_STEP_INVALID")

    def test_wrong_schema_and_workflow_version_fail_closed(self):
        self.assertEqual(self.mutate(lambda d: d.update({"schema": "workflow-step-skills/v2"})),
                         "REGISTRY_SCHEMA")
        self.assertEqual(self.mutate(lambda d: d.update({"workflow_version": "v2"})),
                         "REGISTRY_WORKFLOW_VERSION")

    def test_runtime_set_is_pinned(self):
        self.assertEqual(self.mutate(lambda d: d.update({"runtimes": ["claude"]})), "REGISTRY_RUNTIMES")
        self.assertEqual(self.mutate(lambda d: d["steps"]["plan"]["resolutions"].pop("codex")),
                         "REGISTRY_RESOLUTIONS")

    def test_optional_step_is_refused(self):
        self.assertEqual(self.mutate(lambda d: d["steps"]["review"].update({"required": False})),
                         "REGISTRY_STEP_NOT_REQUIRED")

    def test_human_authorization_only_on_ship(self):
        self.assertEqual(self.mutate(lambda d: d["steps"]["verify"].update({"human_authorization_required": True})),
                         "REGISTRY_HUMAN_AUTHORIZATION")
        self.assertEqual(self.mutate(lambda d: d["steps"]["ship"].update({"human_authorization_required": False})),
                         "REGISTRY_HUMAN_AUTHORIZATION")

    def test_entrypoint_kind_must_be_allowed(self):
        def bad(d):
            d["steps"]["plan"]["allowed_entrypoints"] = ["command"]
        self.assertEqual(self.mutate(bad), "REGISTRY_ENTRYPOINT_KIND")
        self.assertEqual(self.mutate(lambda d: d["steps"]["plan"].update({"allowed_entrypoints": ["prompt"]})),
                         "REGISTRY_ALLOWED_ENTRYPOINTS")
        self.assertEqual(self.mutate(lambda d: d["steps"]["plan"].update({"allowed_entrypoints": []})),
                         "REGISTRY_ALLOWED_ENTRYPOINTS")

    def test_non_semver_minimum_version_fails_closed(self):
        self.assertEqual(self.mutate(lambda d: d["steps"]["ship"]["resolutions"]["claude"].update(
            {"minimum_version": "latest"})), "INVALID_VERSION")

    def test_resolved_entry_needs_every_field(self):
        self.assertEqual(self.mutate(lambda d: d["steps"]["ship"]["resolutions"]["claude"].pop("source_ref")),
                         "REGISTRY_RESOLUTION_INVALID")

    def test_unresolved_entry_rejects_extra_fields_and_unknown_reasons(self):
        def smuggle(d):
            d["steps"]["ship"]["resolutions"]["codex"]["entrypoint"] = "ship.sh"
        self.assertEqual(self.mutate(smuggle), "REGISTRY_RESOLUTION_INVALID")
        self.assertEqual(self.mutate(lambda d: d["steps"]["ship"]["resolutions"]["codex"].update(
            {"unresolved_reason": "BEST_EFFORT"})), "REGISTRY_UNRESOLVED_REASON")

    def test_duplicate_json_keys_and_bom_are_refused(self):
        with self.assertRaises(ss.CanonicalizationError):
            ss.parse_strict(b'{"schema": "a", "schema": "b"}')
        with self.assertRaises(ss.CanonicalizationError):
            ss.parse_strict(b'\xef\xbb\xbf{}')
        with self.assertRaises(ss.CanonicalizationError):
            ss.parse_strict(b'{"x": NaN}')
        with self.assertRaises(ss.CanonicalizationError):
            ss.parse_strict(b'{"x": 1.5}')


# --------------------------------------------------------------------------
# 22: "hashes JCS estaveis"
# --------------------------------------------------------------------------
class Canonicalization(Base):
    def test_keys_are_sorted_by_utf16_code_units(self):
        # U+10000 encodes as the surrogate pair D800 DC00, so it sorts BEFORE U+E000.
        self.assertEqual(ss.jcs({"": 1, "\U00010000": 2}), '{"\U00010000":2,"":1}'.encode())

    def test_serialization_has_no_whitespace_and_no_trailing_newline(self):
        data = ss.jcs({"b": [1, 2], "a": {"z": None, "y": True}})
        self.assertEqual(data, b'{"a":{"y":true,"z":null},"b":[1,2]}')

    def test_insertion_order_does_not_change_the_digest(self):
        self.assertEqual(ss.sha256_jcs({"a": 1, "b": 2}), ss.sha256_jcs({"b": 2, "a": 1}))

    def test_digest_shape_is_sha256_plus_64_lowercase_hex(self):
        digest = ss.sha256_jcs({})
        self.assertTrue(ss.SHA256_RE.fullmatch(digest), digest)
        self.assertEqual(digest, "sha256:" + hashlib.sha256(b"{}").hexdigest())

    def test_non_ijson_values_are_refused(self):
        for value in (1.5, float("nan"), float("inf"), 2 ** 53, {1: "x"}, {"a": {1, 2}}):
            with self.assertRaises(ss.CanonicalizationError, msg=repr(value)):
                ss.jcs({"v": value} if not isinstance(value, dict) else value)

    def test_unicode_is_not_normalized_and_is_not_escaped(self):
        nfc = "caf\u00e9"
        nfd = "cafe\u0301"
        self.assertEqual(ss.jcs({"k": nfc}), b'{"k":"caf\xc3\xa9"}')
        self.assertNotEqual(ss.sha256_jcs({"k": nfc}), ss.sha256_jcs({"k": nfd}))

    def test_control_characters_use_the_short_escapes(self):
        self.assertEqual(ss.jcs({"k": "a\nb\u0001"}), b'{"k":"a\\nb\\u0001"}')

    def test_lone_surrogate_fails_closed(self):
        with self.assertRaises(ss.CanonicalizationError):
            ss.jcs({"k": "\ud800"})


# --------------------------------------------------------------------------
# 22: "resolucao valida versao minima, source ref, manifest/content hash e entrypoint nativo"
# --------------------------------------------------------------------------
class ResolverHappyPath(Base):
    def test_every_step_resolves_to_its_canonical_skill(self):
        for step in STEPS:
            out = self.resolve(step=step)
            self.assertEqual(out["schema"], "skill-resolution/v1")
            self.assertEqual(out["step_id"], step)
            self.assertEqual(out["execution_mode"], "CANONICAL_SKILL")
            self.assertEqual(out["runtime"], "claude")
            self.assertEqual(out["registry_sha256"], REGISTRY_SHA256)
            self.assertEqual(out["resolver_version"], ss.RESOLVER_VERSION)
            self.assertTrue(out["catalog"]["authorized"])
            self.assertTrue(out["capability_preflight"]["native_invocation"])
            self.assertTrue(ss.verify_resolution_digest(out), step)

    def test_resolution_carries_every_field_section_4_1_demands(self):
        out = self.resolve(step="ship")
        for field in ("skill_id", "runtime", "adapter", "entrypoint", "skill_version", "source_ref",
                      "skill_manifest_sha256", "skill_content_sha256", "registry_sha256",
                      "resolver_version", "catalog", "capability_preflight"):
            self.assertIn(field, out)
        self.assertIs(out["human_authorization_required"], True)
        self.assertEqual(out["entrypoint"], "speckit-verify-review-ship-ship")

    def test_digest_is_deterministic_and_covers_the_body(self):
        first, second = self.resolve(step="verify"), self.resolve(step="verify")
        self.assertEqual(first, second)
        tampered = dict(first, skill_version="9.9.9")
        self.assertFalse(ss.verify_resolution_digest(tampered))

    def test_distinct_steps_never_share_a_resolution_digest(self):
        digests = {self.resolve(step=s)["skill_resolution_sha256"] for s in STEPS}
        self.assertEqual(len(digests), 11)

    def test_no_semantic_fallback_ever_appears_in_a_resolution(self):
        for step in STEPS:
            blob = json.dumps(self.resolve(step=step))
            for mode in ("DIRECT", "EMULATED", "BEST_EFFORT"):
                self.assertNotIn(mode, blob, (step, mode))


# --------------------------------------------------------------------------
# 22/23: fail-closed. BLOCKED_CAPABILITY, never a fallback.
# --------------------------------------------------------------------------
class ResolverFailsClosed(Base):
    def test_unknown_step_and_unknown_runtime(self):
        self.blocked("UNKNOWN_STEP", step="implement")
        self.blocked("UNKNOWN_STEP", step="")
        self.blocked("UNKNOWN_RUNTIME", runtime="cursor")

    def test_runtime_without_a_proven_entrypoint_blocks_every_step(self):
        for runtime in ("hermes", "codex"):
            for step in STEPS:
                self.blocked("RUNTIME_ENTRYPOINT_UNPROVEN", step=step, runtime=runtime)

    def test_absent_catalog_blocks_instead_of_discovering(self):
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.resolve_workflow_skill("verify", "claude", REGISTRY_SHA256, registry=registry_bytes())
        self.assertEqual((ctx.exception.code, ctx.exception.reason), (ss.BLOCKED_CAPABILITY, "CATALOG_ABSENT"))

    def test_bare_three_argument_call_cannot_succeed(self):
        """The plan signature alone must never resolve: no catalogue, no trust, no dispatch."""
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.resolve_workflow_skill("verify", "claude", ss.load_registry(REGISTRY)[1])
        self.assertEqual(ctx.exception.code, ss.BLOCKED_CAPABILITY)

    def test_entrypoint_absent_from_the_catalog(self):
        cat = catalog()
        cat["entries"] = [e for e in cat["entries"] if e["entrypoint"] != "speckit-verify-review-ship-verify"]
        cat["catalog_sha256"] = ss.sha256_jcs(cat["entries"])
        self.blocked("ENTRYPOINT_ABSENT", catalog=cat)

    def test_ambiguous_entrypoint_in_the_catalog(self):
        cat = catalog()
        twin = copy.deepcopy(next(e for e in cat["entries"] if e["entrypoint"] == "speckit-verify-review-ship-verify"))
        twin["content_sha256"] = DIGEST
        cat["entries"].append(twin)
        cat["catalog_sha256"] = ss.sha256_jcs(cat["entries"])
        self.blocked("AMBIGUOUS_ENTRYPOINT", catalog=cat)

    def test_untrusted_catalog_and_divergent_catalog_hash(self):
        cat = catalog()
        # A non-empty trust map (an empty `catalogs` object is itself
        # schema-invalid -- load_trusted_catalogs requires at least one entry)
        # that simply does not mention this catalog_id at all.
        with trusted_catalogs_file({"community-archive": DIGEST}) as path:
            with self.assertRaises(ss.SkillResolutionError) as ctx:
                ss.resolve_workflow_skill("verify", "claude", REGISTRY_SHA256, registry=registry_bytes(),
                                          catalog=cat, trusted_catalogs_path=path)
            self.assertEqual(ctx.exception.reason, "UNTRUSTED_CATALOG")
        with trusted_catalogs_file({TRUSTED: DIGEST}) as path:
            with self.assertRaises(ss.SkillResolutionError) as ctx:
                ss.resolve_workflow_skill("verify", "claude", REGISTRY_SHA256, registry=registry_bytes(),
                                          catalog=cat, trusted_catalogs_path=path)
            self.assertEqual((ctx.exception.code, ctx.exception.reason),
                             (ss.BLOCKED_CAPABILITY, "CATALOG_SHA256_MISMATCH"))

    def test_catalog_from_another_runtime_or_another_id(self):
        cat = catalog()
        cat["runtime"] = "codex"
        self.blocked("CATALOG_RUNTIME_MISMATCH", catalog=cat)
        cat = catalog()
        cat["catalog_id"] = "community-archive"
        self.blocked("CATALOG_MISMATCH", catalog=cat)

    def test_version_below_the_registered_minimum(self):
        cat = self.patch_entry("speckit-verify-review-ship-verify", version="0.4.1")
        self.blocked("VERSION_BELOW_MINIMUM", catalog=cat)

    def test_version_above_the_minimum_is_accepted(self):
        cat = self.patch_entry("speckit-verify-review-ship-verify", version="0.5.0")
        self.assertEqual(self.resolve(catalog=cat)["skill_version"], "0.5.0")

    def test_runtime_without_native_invocation(self):
        cat = self.patch_entry("speckit-verify-review-ship-verify", native_invocation=False)
        self.blocked("NO_NATIVE_ENTRYPOINT", catalog=cat)

    def test_entrypoint_kind_adapter_and_source_ref_must_match(self):
        self.blocked("ENTRYPOINT_KIND_MISMATCH",
                     catalog=self.patch_entry("speckit-verify-review-ship-verify", entrypoint_kind="command"))
        self.blocked("ADAPTER_MISMATCH",
                     catalog=self.patch_entry("speckit-verify-review-ship-verify", adapter="shell/v1"))
        self.blocked("SOURCE_REF_MISMATCH",
                     catalog=self.patch_entry("speckit-verify-review-ship-verify",
                                              source_ref="archive-url:https://example.invalid/vrs.zip"))

    def test_malformed_catalog_digests(self):
        self.blocked("INVALID_DIGEST",
                     catalog=self.patch_entry("speckit-verify-review-ship-verify", content_sha256="deadbeef"))
        self.blocked("INVALID_DIGEST",
                     catalog=self.patch_entry("speckit-verify-review-ship-verify",
                                              manifest_sha256=DIGEST.upper()))

    def test_catalog_schema_is_enforced(self):
        cat = catalog()
        cat["entries"][0]["trust_me"] = True
        cat["catalog_sha256"] = ss.sha256_jcs(cat["entries"])
        self.blocked("CATALOG_ENTRY_INVALID", catalog=cat)
        cat = catalog()
        cat["schema"] = "skill-catalog/v2"
        self.blocked("CATALOG_SCHEMA", catalog=cat)

    def test_catalog_entries_tampered_under_the_authorized_digest_is_blocked(self):
        """probe1: content_sha256, manifest_sha256, version and preflight_ref are
        mutated while catalog_sha256 stays at the value trusted_catalogs already
        authorizes (recompute=False -- the attack the round-1 helper could never
        reach, because it always recomputed the digest after mutating). Before
        the fix this resolved with success, catalog.authorized=True, and the
        attacker's hashes copied straight into the emitted resolution."""
        cat = self.patch_entry(
            "speckit-verify-review-ship-ship",
            recompute=False,
            content_sha256=DIGEST,
            manifest_sha256=DIGEST,
            version="9.9.9",
            preflight_ref="preflight:evil",
        )
        self.blocked("CATALOG_CONTENT_MISMATCH", step="ship", catalog=cat)

    def test_catalog_content_mismatch_blocks_inside_validate_catalog_itself(self):
        """The self-check lives in validate_catalog, not only in the resolver's
        call path -- any direct caller of validate_catalog is protected too, and
        the block happens before a single entry field is read out."""
        cat = self.patch_entry("speckit-verify-review-ship-verify", recompute=False, version="9.9.9")
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.validate_catalog(cat)
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.BLOCKED_CAPABILITY, "CATALOG_CONTENT_MISMATCH"))


# --------------------------------------------------------------------------
# 4.1 / round-2 gaps 1 and 4: "a resolucao usa bytes locais versionados ou
# catalogo previamente autorizado; nao baixa/aceita origem nova
# implicitamente". The digest a catalogue must match to be trusted has to
# come from versioned bytes in the repo, not a Mapping the caller (or an
# attacker who also controls the catalogue) assembles at call time.
# --------------------------------------------------------------------------
class TrustedCatalogDefault(Base):
    def test_asset_exists_and_pins_the_frozen_fixture_digest(self):
        trusted = ss.load_trusted_catalogs()
        self.assertEqual(trusted[TRUSTED], catalog()["catalog_sha256"])

    def test_default_trust_comes_from_the_versioned_asset_with_no_override(self):
        """No `trusted_catalogs_path=` at all -- exercises resolve_workflow_skill's
        own default, not a test-supplied trust map."""
        out = ss.resolve_workflow_skill(
            "verify", "claude", REGISTRY_SHA256, registry=registry_bytes(), catalog=catalog()
        )
        self.assertTrue(out["catalog"]["authorized"])
        self.assertEqual(out["catalog"]["sha256"], catalog()["catalog_sha256"])

    def test_explicit_empty_override_still_blocks_untrusted(self):
        """A path to a `workflow-trusted-catalogs/v1` document whose trust map
        does not mention this catalog_id at all is a deliberate override
        (still supported for tests), not the same as omitting the argument --
        and it still blocks."""
        with trusted_catalogs_file({"community-archive": DIGEST}) as path:
            with self.assertRaises(ss.SkillResolutionError) as ctx:
                ss.resolve_workflow_skill(
                    "verify", "claude", REGISTRY_SHA256, registry=registry_bytes(),
                    catalog=catalog(), trusted_catalogs_path=path,
                )
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.BLOCKED_CAPABILITY, "UNTRUSTED_CATALOG"))

    def test_trusted_catalogs_mapping_override_no_longer_exists_in_the_production_signature(self):
        """The a3.py attack, variant 3b, against the production signature:
        mutate ship's catalogue entry, recompute catalog_sha256 the way a
        legitimate publisher would, and hand the recomputed digest straight
        back in as an "authorized" trust map -- self-authorizing, because
        before this repair BOTH the catalogue and its trust pin were plain
        call-time arguments the same caller controlled. Before the fix this
        resolved successfully with the attacker's content hash and version
        99.0.0. The production signature no longer accepts a Mapping at all:
        passing `trusted_catalogs=` now fails at the call boundary, before a
        single byte of the tampered catalogue is even read."""
        cat = self.patch_entry(
            "speckit-verify-review-ship-ship",
            content_sha256="sha256:" + "9" * 64,
            version="99.0.0",
        )
        with self.assertRaises(TypeError):
            ss.resolve_workflow_skill(
                "ship", "claude", REGISTRY_SHA256, registry=registry_bytes(), catalog=cat,
                trusted_catalogs={TRUSTED: cat["catalog_sha256"]},
            )
        # And the production call -- no trust override at all, exactly what a
        # real caller (and the future wiring) would do -- still blocks: the
        # attacker's recomputed digest is not what assets/workflow-trusted-
        # catalogs.json pins for claude-code-local-skills.
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.resolve_workflow_skill(
                "ship", "claude", REGISTRY_SHA256, registry=registry_bytes(), catalog=cat
            )
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.BLOCKED_CAPABILITY, "CATALOG_SHA256_MISMATCH"))

    def test_content_and_manifest_hash_tamper_is_blocked_under_the_real_default_trust(self):
        """Round-2 finding (gaps 1 and 4): swap content_sha256 and
        manifest_sha256 on ship's entry, recompute catalog_sha256 the way a
        legitimate publisher would (recompute=True) -- and resolve WITHOUT
        overriding trusted_catalogs. Before this repair, the test helper's
        self-authorizing default made this resolve successfully; now the
        catalogue is checked against assets/workflow-trusted-catalogs.json,
        bytes the attacker does not control, and the recomputed digest no
        longer matches what is pinned there."""
        cat = self.patch_entry(
            "speckit-verify-review-ship-ship",
            content_sha256=DIGEST,
            manifest_sha256="sha256:" + "7" * 64,
        )
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.resolve_workflow_skill(
                "ship", "claude", REGISTRY_SHA256, registry=registry_bytes(), catalog=cat
            )
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.BLOCKED_CAPABILITY, "CATALOG_SHA256_MISMATCH"))

    def test_attacker_built_catalog_from_scratch_is_not_self_authorizing(self):
        """The attacker builds an entire catalogue from scratch (arbitrary
        hashes) and computes ITS OWN catalog_sha256 -- internally
        self-consistent, exactly like validate_catalog demands. Without a
        trusted_catalogs override, there is nothing here for the attacker to
        also control: the digest must already be in the versioned asset."""
        cat = catalog()
        for entry in cat["entries"]:
            entry["content_sha256"] = "sha256:" + "9" * 64
            entry["manifest_sha256"] = "sha256:" + "8" * 64
        cat["catalog_sha256"] = ss.sha256_jcs(cat["entries"])
        self.assertNotEqual(cat["catalog_sha256"], catalog()["catalog_sha256"])
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            ss.resolve_workflow_skill(
                "ship", "claude", REGISTRY_SHA256, registry=registry_bytes(), catalog=cat
            )
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.BLOCKED_CAPABILITY, "CATALOG_SHA256_MISMATCH"))

    def test_malformed_trusted_catalogs_asset_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "trusted.json"
            bad.write_text(json.dumps({"schema": "workflow-trusted-catalogs/v2",
                                        "workflow_version": "v3", "catalogs": {}}), encoding="utf-8")
            with self.assertRaises(ss.SkillResolutionError) as ctx:
                ss.load_trusted_catalogs(bad)
            self.assertEqual((ctx.exception.code, ctx.exception.reason),
                             (ss.BLOCKED_CAPABILITY, "TRUSTED_CATALOGS_SCHEMA"))


# --------------------------------------------------------------------------
# 22: "skill alterada depois do preflight retorna STALE_SKILL_RESOLUTION"
# --------------------------------------------------------------------------
class StaleResolution(Base):
    def test_registry_hash_drift_is_stale(self):
        self.stale("REGISTRY_SHA256_MISMATCH", sha=DIGEST)

    def test_caller_pin_must_be_a_well_formed_digest(self):
        self.blocked("INVALID_DIGEST", sha="sha256:nope")

    def test_identical_preflight_pin_still_resolves(self):
        pin = self.resolve(step="verify")
        again = self.resolve(step="verify", pinned_resolution=pin)
        self.assertEqual(again["skill_resolution_sha256"], pin["skill_resolution_sha256"])

    def test_skill_content_changed_after_preflight(self):
        pin = self.resolve(step="verify")
        cat = self.patch_entry("speckit-verify-review-ship-verify", content_sha256=DIGEST)
        exc = self.stale("SKILL_CHANGED_AFTER_PREFLIGHT", catalog=cat, pinned_resolution=pin)
        self.assertEqual(exc.detail["field"], "skill_content_sha256")

    def test_skill_version_bump_after_preflight_is_stale_not_silently_accepted(self):
        pin = self.resolve(step="verify")
        cat = self.patch_entry("speckit-verify-review-ship-verify", version="0.5.0")
        self.stale("SKILL_CHANGED_AFTER_PREFLIGHT", catalog=cat, pinned_resolution=pin)

    def test_pin_from_another_step_is_stale(self):
        pin = self.resolve(step="review")
        self.stale("SKILL_CHANGED_AFTER_PREFLIGHT", step="verify", pinned_resolution=pin)

    def test_tampered_pin_is_rejected(self):
        pin = dict(self.resolve(step="verify"))
        pin["skill_resolution_sha256"] = DIGEST
        self.stale("PINNED_RESOLUTION_TAMPERED", pinned_resolution=pin)
        self.stale("PINNED_RESOLUTION_INVALID", pinned_resolution={"schema": "nope"})

    def test_stale_is_raised_before_the_document_is_produced(self):
        pin = self.resolve(step="verify")
        cat = self.patch_entry("speckit-verify-review-ship-verify", content_sha256=DIGEST)
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.resolve(catalog=cat, pinned_resolution=pin)
        self.assertNotIn("skill_resolution_sha256", ctx.exception.payload().get("detail", {}))


# --------------------------------------------------------------------------
# 4.1: skill_invocation_key + skill-invocation/v1
# --------------------------------------------------------------------------
class InvocationKey(Base):
    ARGS = ("proj-a", "feature-x-0001", "run-7", "verify", "rg-" + "a" * 8, 4,
            "sha256:" + "1" * 64, "sha256:" + "2" * 64)

    def test_matches_the_literal_formula(self):
        canonical = (
            '{"dispatch_key":"sha256:' + "2" * 64 + '",'
            '"plan_revision":4,'
            '"project_id":"proj-a",'
            '"recovery_generation_id":"rg-aaaaaaaa",'
            '"run_id":"run-7",'
            '"skill_resolution_sha256":"sha256:' + "1" * 64 + '",'
            '"step_id":"verify",'
            '"work_item_id":"feature-x-0001"}'
        )
        expected = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.assertEqual(ss.skill_invocation_key(*self.ARGS), expected)

    def test_every_input_is_load_bearing(self):
        base = ss.skill_invocation_key(*self.ARGS)
        variants = [
            ("proj-b",) + self.ARGS[1:],
            self.ARGS[:1] + ("feature-y-0001",) + self.ARGS[2:],
            self.ARGS[:2] + ("run-8",) + self.ARGS[3:],
            self.ARGS[:3] + ("review",) + self.ARGS[4:],
            self.ARGS[:4] + ("rg-" + "b" * 8,) + self.ARGS[5:],
            self.ARGS[:5] + (5,) + self.ARGS[6:],
            self.ARGS[:6] + ("sha256:" + "3" * 64,) + self.ARGS[7:],
            self.ARGS[:7] + ("sha256:" + "4" * 64,),
        ]
        keys = {ss.skill_invocation_key(*v) for v in variants}
        self.assertEqual(len(keys), 8)
        self.assertNotIn(base, keys)

    def test_invalid_inputs_fail_closed(self):
        for index, bad in ((3, "implement"), (5, -1), (5, True), (5, "4"),
                           (6, "1" * 64), (7, "sha256:XYZ"), (0, "")):
            args = list(self.ARGS)
            args[index] = bad
            with self.assertRaises(ss.SkillResolutionError, msg=repr((index, bad))):
                ss.skill_invocation_key(*args)

    def test_key_binds_a_real_resolution(self):
        resolution = self.resolve(step="verify")
        key = ss.skill_invocation_key("proj-a", "feature-x-0001", "run-7", "verify", "rg-1",
                                      1, resolution["skill_resolution_sha256"], "sha256:" + "2" * 64)
        self.assertTrue(ss.SHA256_RE.fullmatch(key))


class InvocationEnvelope(Base):
    #: The receipt's real, legitimate execution context. Tests that want to
    #: prove context correlation forge the ENVELOPE's claimed fields, never
    #: this -- this is what a genuine caller expects.
    CONTEXT = {
        "project_id": "proj-a",
        "work_item_id": "feature-x-0001",
        "run_id": "run-7",
        "attempt_id": "attempt-005",
    }

    def validate(self, doc, resolution=None, cat=None, **context):
        """``ss.validate_skill_invocation`` with the real context and the real
        catalogue by default. Pass ``resolution=`` to swap in a doctored/forged
        one; pass ``cat=`` to swap in a different authorized catalogue (round-3
        repair: the anchor now recomputes the resolution against it); pass a
        context kwarg to simulate the caller expecting a DIFFERENT execution
        than the one on file (the correlation the round-2 repair added)."""
        resolution = self.last_resolution if resolution is None else resolution
        cat = catalog() if cat is None else cat
        ctx = dict(self.CONTEXT, **context)
        return ss.validate_skill_invocation(doc, resolution, catalog=cat, **ctx)

    def envelope(self, **overrides):
        """Build a well-formed envelope for a fixed ``verify``/``claude``
        resolution. ``overrides`` mutate only the OUTPUT envelope dict, after the
        key is computed and before the content hash is -- so a caller can make
        the doc claim something (e.g. ``runtime="codex"``) that no longer
        matches the resolution it was actually built from, and self-consistently
        so (key/content hash still check out). ``self.last_resolution`` is always
        the real (claude, verify) resolution used to build it, exposed so tests
        can pass either it (a correlation attack) or a doctored copy."""
        resolution = self.resolve(step="verify")
        doc = {
            "schema": "skill-invocation/v1",
            "project_id": self.CONTEXT["project_id"],
            "work_item_id": self.CONTEXT["work_item_id"],
            "run_id": self.CONTEXT["run_id"],
            "step_id": "verify",
            "skill_id": resolution["skill_id"],
            "skill_version": resolution["skill_version"],
            "skill_content_sha256": resolution["skill_content_sha256"],
            "registry_sha256": resolution["registry_sha256"],
            "skill_resolution_sha256": resolution["skill_resolution_sha256"],
            "runtime": "claude",
            "adapter": resolution["adapter"],
            "entrypoint": resolution["entrypoint"],
            "dispatch_key": "sha256:" + "2" * 64,
            "attempt_id": self.CONTEXT["attempt_id"],
            "recovery_generation_id": "rg-1",
            "plan_revision": 4,
            "input_fingerprint": "sha256:" + "3" * 64,
            "started_receipt_ref": "receipts/skill-invocation/inv-1.started.json",
            "status": "STARTED",
            "output_manifest_sha256": "sha256:" + "4" * 64,
        }
        doc["skill_invocation_key"] = ss.skill_invocation_key(
            doc["project_id"], doc["work_item_id"], doc["run_id"], doc["step_id"],
            doc["recovery_generation_id"], doc["plan_revision"],
            doc["skill_resolution_sha256"], doc["dispatch_key"])
        doc.update(overrides)
        doc["content_sha256"] = ss.sha256_jcs(doc)
        self.last_resolution = resolution
        return doc

    @staticmethod
    def _reseal(doc):
        """Recompute key + content hash after a caller mutates a key field --
        turns a sloppy forgery into a self-consistent one, so the specific
        check under test is the only thing that can still catch it."""
        doc = dict(doc)
        doc.pop("content_sha256", None)
        doc["skill_invocation_key"] = ss.skill_invocation_key(
            doc["project_id"], doc["work_item_id"], doc["run_id"], doc["step_id"],
            doc["recovery_generation_id"], doc["plan_revision"],
            doc["skill_resolution_sha256"], doc["dispatch_key"])
        doc["content_sha256"] = ss.sha256_jcs(doc)
        return doc

    def _forged_resolution(self, **overrides):
        """A skill-resolution/v1-shaped document built from scratch, not
        derived from a real resolve_workflow_skill call, with a
        skill_resolution_sha256 recomputed so it verifies cleanly. Defaults to
        the exact round-2 attack literal."""
        base = {
            "schema": ss.RESOLUTION_SCHEMA,
            "resolver_version": ss.RESOLVER_VERSION,
            "workflow_version": "v3",
            "registry_sha256": REGISTRY_SHA256,
            "step_id": "ship",
            "skill_id": "totally.made.up",
            "required": True,
            "human_authorization_required": True,
            "runtime": "codex",
            "adapter": "evil-adapter/v1",
            "entrypoint": "rm-rf-slash",
            "entrypoint_kind": "command",
            "execution_mode": "CANONICAL_SKILL",
            "skill_version": "1.0.0",
            "minimum_version": "1.0.0",
            "source_ref": "attacker-controlled",
            "skill_manifest_sha256": DIGEST,
            "skill_content_sha256": DIGEST,
            "catalog": {"catalog_id": "attacker-catalog", "sha256": DIGEST, "authorized": True},
            "capability_preflight": {"native_invocation": True, "preflight_ref": "preflight:evil"},
        }
        base.update(overrides)
        base["skill_resolution_sha256"] = ss.sha256_jcs(base)
        return base

    def _forged_envelope(self, resolution, status="COMPLETED"):
        """A skill-invocation/v1 envelope self-consistently built to attest
        exactly ``resolution`` -- key and content hash both recomputed over
        it, so only the registry anchor can still catch the forgery."""
        doc = {
            "schema": "skill-invocation/v1",
            "project_id": self.CONTEXT["project_id"],
            "work_item_id": self.CONTEXT["work_item_id"],
            "run_id": self.CONTEXT["run_id"],
            "step_id": resolution["step_id"],
            "skill_id": resolution["skill_id"],
            "skill_version": resolution["skill_version"],
            "skill_content_sha256": resolution["skill_content_sha256"],
            "registry_sha256": resolution["registry_sha256"],
            "skill_resolution_sha256": resolution["skill_resolution_sha256"],
            "runtime": resolution["runtime"],
            "adapter": resolution["adapter"],
            "entrypoint": resolution["entrypoint"],
            "dispatch_key": "sha256:" + "2" * 64,
            "attempt_id": self.CONTEXT["attempt_id"],
            "recovery_generation_id": "rg-1",
            "plan_revision": 4,
            "input_fingerprint": "sha256:" + "3" * 64,
            "started_receipt_ref": "receipts/skill-invocation/inv-evil.json",
            "status": status,
            "output_manifest_sha256": "sha256:" + "4" * 64,
        }
        doc["skill_invocation_key"] = ss.skill_invocation_key(
            doc["project_id"], doc["work_item_id"], doc["run_id"], doc["step_id"],
            doc["recovery_generation_id"], doc["plan_revision"],
            doc["skill_resolution_sha256"], doc["dispatch_key"])
        doc["content_sha256"] = ss.sha256_jcs(doc)
        return doc

    def test_well_formed_envelope_validates(self):
        doc = self.envelope()
        self.assertEqual(self.validate(doc)["status"], "STARTED")

    def test_resolution_argument_is_mandatory(self):
        """LD-repair item 3: correlation can't be an opt-in cross-check -- a
        caller that forgets to pass it must get a TypeError, not a silent skip."""
        doc = self.envelope()
        with self.assertRaises(TypeError):
            ss.validate_skill_invocation(doc)

    def test_context_arguments_are_mandatory(self):
        """Round-2 repair: execution-context correlation is not optional
        either -- omitting it is a caller bug, not a silent pass-through."""
        doc = self.envelope()
        with self.assertRaises(TypeError):
            ss.validate_skill_invocation(doc, self.last_resolution)

    def test_key_forgery_is_stale(self):
        doc = self.envelope()
        doc["run_id"] = "run-8"
        doc.pop("content_sha256")
        doc["content_sha256"] = ss.sha256_jcs(doc)
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc)
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.STALE_SKILL_RESOLUTION, "INVOCATION_KEY_MISMATCH"))

    def test_content_hash_must_cover_the_body(self):
        doc = self.envelope()
        doc["attempt_id"] = "attempt-006"
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc)
        self.assertEqual(ctx.exception.reason, "INVOCATION_CONTENT_MISMATCH")

    def test_unknown_or_missing_fields_fail_closed(self):
        doc = self.envelope()
        doc["execution_mode"] = "CANONICAL_SKILL"
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc)
        self.assertEqual(ctx.exception.reason, "INVOCATION_INVALID")
        doc = self.envelope()
        doc.pop("started_receipt_ref")
        with self.assertRaises(ss.SkillResolutionError):
            self.validate(doc)

    def test_fallback_modes_are_refused_anywhere_in_the_envelope(self):
        doc = self.envelope(adapter="BEST_EFFORT-shell")
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc)
        self.assertEqual(ctx.exception.reason, "FORBIDDEN_EXECUTION_MODE")

    def test_status_allowlist(self):
        for status in ("STARTED", "COMPLETED", "FAILED", "BLOCKED"):
            doc = self.envelope(status=status)
            self.assertEqual(self.validate(doc)["status"], status)
        doc = self.envelope(status="ASSUMED")
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc)
        self.assertEqual(ctx.exception.reason, "INVOCATION_STATUS")

    # ----------------------------------------------------------------------
    # 22, bullet 7: "receipt de outro step/skill/work item/run/attempt/runtime
    # ... falha". A self-consistent envelope is not attestation by itself.
    # ----------------------------------------------------------------------
    def test_receipt_claiming_another_steps_resolution_is_unattested(self):
        """probe3: a step_id='ship' envelope carrying verify's skill_id,
        entrypoint and skill_resolution_sha256 used to validate cleanly because
        nothing compared it to what was actually resolved for 'ship'."""
        forged = self._reseal(dict(self.envelope(), step_id="ship"))
        ship_resolution = self.resolve(step="ship")
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(forged, ship_resolution)
        self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.reason, "INVOCATION_RESOLUTION_MISMATCH")
        self.assertEqual(ctx.exception.detail["field"], "skill_id")

    def test_receipt_for_an_unresolved_runtime_cannot_be_attested(self):
        """probe3: runtime='codex' has no resolution at all in this registry --
        nothing can legitimately attest a codex invocation, and an envelope that
        merely claims runtime='codex' while reusing claude's resolution fields
        must be rejected, not accepted for lack of a codex resolution to compare."""
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.resolve(step="verify", runtime="codex")
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.BLOCKED_CAPABILITY, "RUNTIME_ENTRYPOINT_UNPROVEN"))

        doc = self.envelope(runtime="codex")  # self-consistent lie: adapter/entrypoint are claude's
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc)
        self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.reason, "INVOCATION_RESOLUTION_MISMATCH")
        self.assertEqual(ctx.exception.detail["field"], "runtime")

    def test_forged_resolution_pin_cannot_be_used_to_attest(self):
        """A resolution that mutates a field and RE-SEALS its own
        skill_resolution_sha256 (so it verifies against itself) still cannot be
        used to rubber-stamp an envelope. Round-3 repair: before this fix, the
        only thing anchoring a resolution's CONTENT was its own self-digest --
        mutating a field and recomputing the digest over the mutated body was
        the exact bypass (see the a5 attack below). The anchor now recomputes
        the resolution independently from the registry and catalogue and
        requires the presented digest to equal THAT, not merely to verify
        against itself."""
        doc = self.envelope()
        forged_resolution = dict(self.last_resolution, skill_version="9.9.9")
        forged_resolution["skill_resolution_sha256"] = ss.sha256_jcs(
            {k: v for k, v in forged_resolution.items() if k != "skill_resolution_sha256"}
        )
        self.assertTrue(ss.verify_resolution_digest(forged_resolution))
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc, forged_resolution)
        self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.reason, "RESOLUTION_CONTENT_FORGED")

    def test_forged_content_manifest_version_source_ref_and_catalog_are_rejected_even_with_correct_identity(self):
        """The a5 attack, verbatim (round-3 biggest_gap): resolve ship/claude
        honestly, keep step_id/skill_id/runtime/adapter/entrypoint/
        entrypoint_kind correct -- so the identity anchor alone cannot catch
        it -- tamper skill_content_sha256, skill_manifest_sha256, skill_version,
        source_ref, minimum_version and catalog, RE-SEAL skill_resolution_sha256
        over the tampered body, and build a matching COMPLETED envelope for
        step 'ship'. Before this repair this was printed as "SHIP COMPLETED
        RECEIPT ACCEPTED with forged content hash"."""
        honest = self.resolve(step="ship")
        forged_resolution = dict(
            honest,
            skill_content_sha256="sha256:" + "9" * 64,
            skill_manifest_sha256="sha256:" + "8" * 64,
            skill_version="99.0.0",
            source_ref="evil@99.0.0",
            minimum_version="0.0.1",
            catalog={"catalog_id": "attacker-catalog", "sha256": "sha256:" + "7" * 64, "authorized": True},
        )
        forged_resolution["skill_resolution_sha256"] = ss.sha256_jcs(
            {k: v for k, v in forged_resolution.items() if k != "skill_resolution_sha256"}
        )
        self.assertTrue(ss.verify_resolution_digest(forged_resolution))
        self.assertNotEqual(forged_resolution["skill_resolution_sha256"], honest["skill_resolution_sha256"])

        doc = self._forged_envelope(forged_resolution, status="COMPLETED")
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc, forged_resolution)
        self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.reason, "RESOLUTION_CONTENT_FORGED")
        # The honest resolution for the very same (step, runtime) pair carries
        # different, real facts -- proving the forgery, not a fixture gap, is
        # what got caught.
        self.assertNotEqual(honest["skill_content_sha256"], forged_resolution["skill_content_sha256"])
        self.assertNotEqual(honest["skill_version"], forged_resolution["skill_version"])

    # ----------------------------------------------------------------------
    # round-2 repair: the resolution itself must anchor to the registry.
    # Digest that verifies + full internal self-consistency is not proof of
    # anything the registry actually says.
    # ----------------------------------------------------------------------
    def test_registry_anchored_forgery_is_rejected_and_agrees_with_resolve_workflow_skill(self):
        """The round-2 attack, verbatim: skill_id='totally.made.up',
        entrypoint='rm-rf-slash', runtime='codex', a skill_resolution_sha256
        that verifies, and a COMPLETED receipt for step_id='ship' built to
        match it exactly. Also proves the legitimate path agrees: the same
        (step_id, runtime) pair is blocked by resolve_workflow_skill in the
        same process, so there is no divergence between the two paths."""
        forged_resolution = self._forged_resolution()
        self.assertTrue(ss.verify_resolution_digest(forged_resolution))
        doc = self._forged_envelope(forged_resolution)

        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc, forged_resolution)
        self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.reason, "RESOLUTION_SKILL_ID_MISMATCH")

        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.resolve(step="ship", runtime="codex")
        self.assertEqual((ctx.exception.code, ctx.exception.reason),
                         (ss.BLOCKED_CAPABILITY, "RUNTIME_ENTRYPOINT_UNPROVEN"))

    def test_forged_resolution_with_the_real_skill_id_still_blocks_on_unresolved_runtime(self):
        """Fix the skill_id to the registry's real value for 'ship' -- the
        forgery still has to clear runtime resolution, and codex is
        unresolved for every step."""
        real_skill_id = registry()["steps"]["ship"]["skill_id"]
        forged_resolution = self._forged_resolution(skill_id=real_skill_id)
        doc = self._forged_envelope(forged_resolution)
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc, forged_resolution)
        self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.reason, "RUNTIME_ENTRYPOINT_UNPROVEN")

    def test_forged_resolution_with_real_registry_facts_but_wrong_entrypoint_drifts(self):
        """Fix skill_id AND runtime to real, resolved registry values -- only
        the entrypoint itself is forged. The anchor still catches the drift
        between what the resolution claims and what the registry pins."""
        forged_resolution = self._forged_resolution(
            skill_id="speckit.verify-review-ship.ship",
            runtime="claude",
            adapter="claude-code-skill/v1",
            entrypoint="speckit-verify-review-ship-ship-EVIL",
            entrypoint_kind="skill",
        )
        doc = self._forged_envelope(forged_resolution)
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc, forged_resolution)
        self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.reason, "RESOLUTION_REGISTRY_DRIFT")
        self.assertEqual(ctx.exception.detail["field"], "entrypoint")

    def test_resolution_registry_sha256_must_match_the_real_asset(self):
        """A resolution can get everything else right and still lie about
        which registry revision it was resolved against."""
        real = self.resolve(step="verify")
        forged_resolution = dict(real, registry_sha256=DIGEST)
        forged_resolution["skill_resolution_sha256"] = ss.sha256_jcs(
            {k: v for k, v in forged_resolution.items() if k != "skill_resolution_sha256"}
        )
        doc = self._forged_envelope(forged_resolution, status="STARTED")
        with self.assertRaises(ss.SkillResolutionError) as ctx:
            self.validate(doc, forged_resolution)
        self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
        self.assertEqual(ctx.exception.reason, "RESOLUTION_REGISTRY_MISMATCH")

    # ----------------------------------------------------------------------
    # 22, bullet 7: "receipt ... de outro work item/run/attempt" falha.
    # probe2 case 7: work-999/run-999/attempt-001/proj-999 were all accepted
    # because validate_skill_invocation never received any expected execution
    # context to compare the receipt against.
    # ----------------------------------------------------------------------
    def test_receipt_for_another_work_item_run_attempt_or_project_is_unattested(self):
        forged_values = {
            "project_id": "proj-999",
            "work_item_id": "work-999",
            "run_id": "run-999",
            "attempt_id": "attempt-001",
        }
        for field, forged_value in forged_values.items():
            with self.subTest(field=field):
                doc = self._reseal(dict(self.envelope(), **{field: forged_value}))
                with self.assertRaises(ss.SkillResolutionError) as ctx:
                    self.validate(doc)
                self.assertEqual(ctx.exception.code, ss.UNATTESTED_STEP_OUTPUT)
                self.assertEqual(ctx.exception.reason, "INVOCATION_CONTEXT_MISMATCH")
                self.assertEqual(ctx.exception.detail["field"], field)

    def test_matching_context_is_accepted(self):
        """The positive case for the same check: an envelope whose context
        genuinely matches what the caller expects still validates."""
        doc = self.envelope()
        self.assertEqual(self.validate(doc)["status"], "STARTED")


# --------------------------------------------------------------------------
# 4.1: "o core executa resolve_workflow_skill(...) e persiste
# skill-resolution/v1". LD-003 forbids grill_workspace.py/ensure_workflow.py,
# not writing inside grill_core -- this module owns its own atomic persist.
# --------------------------------------------------------------------------
class Persistence(Base):
    def test_persist_writes_atomically_and_round_trips(self):
        resolution = self.resolve(step="verify")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "nested" / "verify.skill-resolution.json"
            out = ss.persist_skill_resolution(resolution, dest)
            self.assertEqual(out, dest)
            self.assertTrue(dest.exists())
            # No leftover temp file: the atomic swap left exactly one entry.
            self.assertEqual(list(dest.parent.iterdir()), [dest])
            reloaded = ss.load_persisted_skill_resolution(dest)
            self.assertEqual(reloaded, resolution)

    def test_persist_refuses_a_document_whose_digest_does_not_verify(self):
        resolution = dict(self.resolve(step="verify"), skill_version="9.9.9")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ss.SkillResolutionError) as ctx:
                ss.persist_skill_resolution(resolution, Path(tmp) / "x.json")
            self.assertEqual((ctx.exception.code, ctx.exception.reason),
                             (ss.BLOCKED_CAPABILITY, "RESOLUTION_INVALID"))

    def test_persist_refuses_a_non_resolution_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ss.SkillResolutionError) as ctx:
                ss.persist_skill_resolution({"schema": "something-else/v1"}, Path(tmp) / "x.json")
            self.assertEqual((ctx.exception.code, ctx.exception.reason),
                             (ss.BLOCKED_CAPABILITY, "RESOLUTION_INVALID"))

    def test_load_persisted_resolution_rejects_hand_edited_bytes(self):
        resolution = self.resolve(step="ship")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ship.json"
            ss.persist_skill_resolution(resolution, dest)
            tampered = json.loads(dest.read_text(encoding="utf-8"))
            tampered["skill_version"] = "9.9.9"
            dest.write_text(json.dumps(tampered, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(ss.SkillResolutionError) as ctx:
                ss.load_persisted_skill_resolution(dest)
            self.assertEqual((ctx.exception.code, ctx.exception.reason),
                             (ss.BLOCKED_CAPABILITY, "RESOLUTION_INVALID"))

    def test_load_persisted_resolution_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "broken.json"
            dest.write_bytes(b'{"schema": "skill-resolution/v1",}')
            with self.assertRaises(ss.SkillResolutionError) as ctx:
                ss.load_persisted_skill_resolution(dest)
            self.assertEqual((ctx.exception.code, ctx.exception.reason),
                             (ss.BLOCKED_CAPABILITY, "RESOLUTION_INVALID"))


# --------------------------------------------------------------------------
# hygiene the round demands
# --------------------------------------------------------------------------
class Hygiene(Base):
    def test_module_is_stdlib_only_and_offline(self):
        text = MODULE.read_text(encoding="utf-8")
        for forbidden in ("import requests", "urllib", "http.client", "socket", "subprocess", "os.system"):
            self.assertNotIn(forbidden, text, forbidden)

    def test_frozen_catalog_fixture_is_self_consistent(self):
        cat = ss.validate_catalog(catalog())
        self.assertEqual(cat["catalog_sha256"], ss.sha256_jcs(cat["entries"]))
        self.assertEqual(len(cat["entries"]), 11)
        self.assertTrue(all(e["native_invocation"] for e in cat["entries"]))

    def test_public_cli_exposes_only_the_approved_gauntlet_bindings(self):
        """Only the closed FASE-001/002 Gauntlet controls may bind its resolver."""
        text = (SCRIPTS / "grill_workspace.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        expected_handlers = {
            "gauntlet-init": "gauntlet_init_command",
            "gauntlet-status": "gauntlet_status_command",
            "gauntlet-run": "gauntlet_run_command",
            "gauntlet-resume": "gauntlet_resume_command",
            "gauntlet-prepare-worker": "gauntlet_prepare_worker_command",
            "gauntlet-cleanup": "gauntlet_cleanup_command",
        }

        parser_commands = {
            call.args[0].value
            for call in ast.walk(functions["build_parser"])
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "add_parser"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        }
        for loop in ast.walk(functions["build_parser"]):
            if not (
                isinstance(loop, ast.For)
                and isinstance(loop.target, ast.Name)
                and isinstance(loop.iter, (ast.Tuple, ast.List))
            ):
                continue
            loop_registers_target = any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "add_parser"
                and call.args
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == loop.target.id
                for statement in loop.body
                for call in ast.walk(statement)
            )
            if loop_registers_target:
                parser_commands.update(
                    item.value
                    for item in loop.iter.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                )
        self.assertTrue(expected_handlers.keys() <= parser_commands)

        handler_bindings = {}
        for node in ast.walk(functions["main"]):
            if not isinstance(node, ast.Dict):
                continue
            candidate = {}
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and isinstance(value, ast.Name)
                ):
                    candidate[key.value] = value.id
            if expected_handlers.keys() <= candidate.keys():
                handler_bindings = candidate
                break
        self.assertEqual(
            {command: handler_bindings.get(command) for command in expected_handlers},
            expected_handlers,
        )

        # FASE-002 repeats the FASE-001 proof at the mutable admission
        # boundary; it is the sole additional approved loader.  Keep this
        # narrow so legacy handlers cannot reach Gauntlet/step-skill state
        # through a newly introduced helper.
        permitted_loaders = {
            "gauntlet_init_command",
            "gauntlet_activation_projection",
            "gauntlet_run_admission",
        }
        sensitive_modules = {"gauntlet", "step_skills"}
        observed_loaders = set()
        for function_name, function in functions.items():
            for call in ast.walk(function):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == "grill_core_module"
                    and call.args
                    and isinstance(call.args[0], ast.Constant)
                    and call.args[0].value in sensitive_modules
                ):
                    observed_loaders.add(function_name)
        self.assertEqual(observed_loaders, permitted_loaders)

        local_calls = {
            function_name: {
                call.func.id
                for call in ast.walk(function)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id in functions
            }
            for function_name, function in functions.items()
        }

        def reachable(function_name):
            seen = set()
            pending = [function_name]
            while pending:
                current = pending.pop()
                if current in seen:
                    continue
                seen.add(current)
                pending.extend(local_calls.get(current, set()) - seen)
            return seen

        for command, handler in handler_bindings.items():
            if command not in expected_handlers:
                self.assertFalse(
                    reachable(handler) & permitted_loaders,
                    f"legacy command {command!r} reaches the Gauntlet resolver",
                )

    def test_trusted_catalogs_asset_exists_and_is_versioned_next_to_the_registry(self):
        self.assertTrue(TRUSTED_CATALOGS_ASSET.is_file())
        document = json.loads(TRUSTED_CATALOGS_ASSET.read_text(encoding="utf-8"))
        self.assertEqual(document["schema"], "workflow-trusted-catalogs/v1")
        self.assertIn(TRUSTED, document["catalogs"])

    def test_fixtures_directory_documents_the_unresolved_runtimes(self):
        readme = REPO / "tests/fixtures/workflow-step-skills/README.md"
        self.assertTrue(readme.is_file())
        text = readme.read_text(encoding="utf-8")
        self.assertIn("hermes", text.lower())
        self.assertIn("codex", text.lower())
        self.assertIn("RUNTIME_ENTRYPOINT_UNPROVEN", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
