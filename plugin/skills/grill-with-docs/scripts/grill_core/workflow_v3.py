#!/usr/bin/env python3
"""Managed WORKFLOW.md v3 ("invoke, do not emulate") plus preview-first v2 -> v3 migration.

Stdlib only, no network, no runtime CLI dependency.

Coexistence contract
--------------------
v3 is a NEW marker with a NEW allowlist. ``ensure_workflow.VERSION``,
``ensure_workflow.MARKER`` and ``ensure_workflow.ESSENTIAL`` are read here and
never modified: appending a v3 substring to the v2 tuple would turn every
WORKFLOW.md v2 already materialised in a consumer repository into
"incompatible workflow" and block ``init``/``preflight``. A v2 workflow stays
byte-intact on read, detection and preview; only an explicitly authorised
mutable command may rewrite it.

Runtime-wiring gate
--------------------
``migrate --apply`` refuses with ``V3_RUNTIME_NOT_WIRED`` (rc=2, no write)
unless ``runtime_wired()`` proves the live ``ensure_workflow.py`` actually
accepts a v3 document. ROUND-3 FIX: this used to be a version-string
comparison (``sibling("ensure_workflow").VERSION == VERSION``) against a
constant that pins what fresh bootstrap MATERIALISES ("v2", frozen by Fase 0
so no v2 consumer regresses) -- not what the runtime can READ. That predicate
could never turn True without breaking Fase 0, so the gate was permanently
closed by construction, independent of whether ``ensure_workflow.py`` could
actually resolve a v3 document (LD-004's dual-read already landed it). Fixed:
``runtime_wired()`` now asks the real production reader --
``ensure_workflow.resolve_workflow``, the exact function ``--ensure`` and
``grill_workspace.py init`` call on every real bundle -- by rendering the
bundled v3 template and materialising it in a throwaway git repository, in
the spirit of ``work_item_v3.production_reader_accepts_v3()``. See
``runtime_wired`` for the full mechanics.
"""
from __future__ import annotations

import argparse
import contextlib
import difflib
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve()
GRILL_CORE = HERE.parent
SCRIPTS = HERE.parents[1]
ASSETS = HERE.parents[2] / "assets"
TEMPLATE_V3 = ASSETS / "WORKFLOW.v3.template.md"
TEMPLATE_V2 = ASSETS / "WORKFLOW.template.md"
REGISTRY = ASSETS / "workflow-step-skills.json"
REGISTRY_REF = "assets/workflow-step-skills.json"
#: Token the bundled v3 template carries in place of the live registry_sha256;
#: ``render_v3`` bakes the real value in at apply time so the materialised
#: document never merely promises a hash without pinning one.
REGISTRY_SHA256_PLACEHOLDER = "__REGISTRY_SHA256__"
#: Anchors the pinned ``registry_sha256`` inside a materialised v3 WORKFLOW.md
#: prose ("... está fixado em `<value>`."). Used to verify the pin on READ, not
#: just to inject it on write -- see ``pinned_registry_sha256``.
PIN_ANCHOR_RE = re.compile(r"está fixado em `([^`]*)`")

VERSION = "v3"
MARKER = "grill-with-docs-workflow:v3"
SCHEMA = "grill-workflow-migration/v1"

# NEW allowlist. Never derived from ensure_workflow.ESSENTIAL at runtime: the two
# tuples must be able to drift without one silently rewriting the other.
ESSENTIAL = (
    "## Loop externo",
    "## Ciclo externo de execução",
    "specify",
    "plan",
    "checklist",
    "tasks",
    "analyze",
    "agent-assign",
    "agent-execute",
    "converge",
    "verify",
    "review",
    "ship",
    "PLAN_ONLY_STOP",
    "Spec Kit >=0.11.2",
    "A–E",
    "no PR",
    "hotfix-fast",
    "HOTFIX-GO",
    "## Invocação canônica",
    "invoke, do not emulate",
    "invocar a skill registrada",
    "semantic emulation",
    "workflow-step-skills/v1",
    "workflow-step-skills.json",
    "registry_sha256",
    "CANONICAL_SKILL",
    "skill-resolution",
    "skill-invocation",
    "step-output",
    "UNATTESTED_STEP_OUTPUT",
    "BLOCKED_CAPABILITY",
    "POLICY_VIOLATION/DIRECT_STEP_EXECUTION",
)

# The registry validates the *set* and order of registered step definitions,
# but a v3 WORKFLOW.md is the human-facing execution contract.  Checking only
# ``ESSENTIAL`` as independent substrings made a document which swapped two
# steps look compatible: every required word was still present.  Keep this
# separate from the v2 allowlist and from the registry pin: it is a v3
# document-contract check and does not change how v2 documents are read.
CANONICAL_STEP_ORDER = (
    "specify",
    "plan",
    "checklist",
    "tasks",
    "analyze",
    "agent-assign",
    "agent-execute",
    "converge",
    "verify",
    "review",
    "ship",
)
STEP_ORDER_MISSING = "canonical-external-step-order"
_CYCLE_HEADING_RE = re.compile(
    r"^## Ciclo externo de execução(?:\s*\([^\n]*\))?\s*$"
    r"(?P<body>.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
_STEP_TOKEN_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(step) for step in CANONICAL_STEP_ORDER) + r")(?![\w-])"
)
_TABLE_STEP_RE = re.compile(r"^\|\s*([a-z][a-z-]*)\s*\|", re.MULTILINE)

EXIT_OK = 0
EXIT_NO_GO = 1
EXIT_BLOCKED = 2

# The v3 plan writes SCREAMING_SNAKE; the live CLI contract is SCREAMING-KEBAB.
# The two vocabularies are reconciled here instead of in each call site, so the
# later wiring round has one table to consult and no code has to guess.
CLI_CODE_ALIASES = {
    "WORKFLOW_ROOT_INVALID": "WORKFLOW-ROOT-INVALID",
    "WORKFLOW_MISSING": "WORKFLOW-MISSING",
    "WORKFLOW_UNSAFE": "WORKFLOW-UNSAFE",
    "WORKFLOW_INVALID_UTF8": "WORKFLOW-INVALID-UTF8",
    "WORKFLOW_INCOMPATIBLE": "WORKFLOW-INCOMPATIBLE",
    "WORKFLOW_LOCAL_EDITS": "WORKFLOW-LOCAL-EDITS",
    "WORKFLOW_TEMPLATE_INVALID": "WORKFLOW-TEMPLATE-INVALID",
    "STATE_DIVERGENCE": "STATE-DIVERGENCE",
    "INVALID_ARGUMENTS": "INVALID-ARGUMENTS",
    "REGISTRY_INVALID": "REGISTRY-INVALID",
    "REGISTRY_PIN_DIVERGENT": "REGISTRY-PIN-DIVERGENT",
    "V3_RUNTIME_NOT_WIRED": "V3-RUNTIME-NOT-WIRED",
    "FILESYSTEM": "FILESYSTEM",
}

_SIBLINGS: dict[str, object] = {}


class Failure(Exception):
    """Any depth of the call stack can still produce exactly one JSON document."""

    def __init__(self, exit_code: int, code: str, message: str, **extra: object) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.verdict = "NO-GO" if exit_code == EXIT_NO_GO else "BLOCKED"
        self.code = code
        self.message = message
        self.extra = extra


class Detection(NamedTuple):
    """Version of a materialised WORKFLOW.md, independent of how it is reported."""

    marker: str | None
    version: str | None
    v2_compatible: bool
    v3_compatible: bool
    missing_v3: tuple[str, ...]


class Gate(NamedTuple):
    status: str
    code: str | None
    missing: tuple[str, ...]


def sibling(name: str, directory: Path = SCRIPTS):
    """Load a sibling script by path; the package has no import-time dependency on it.

    GAP (round 3): a syntactically broken or unreadable sibling module used to
    let ``spec.loader.exec_module`` raise straight through ``main()``'s
    ``Failure``/``OSError``/``UnicodeError`` handlers -- empty stdout, a raw
    Traceback on stderr, rc=1, colliding with the exit code reserved for
    NO-GO. Wrapped the same way ``ensure_workflow._load_grill_core`` already
    protects its one load: any load-time exception, not only ``spec``/
    ``loader`` being ``None``, degrades to one named JSON document instead of
    an unhandled crash.
    """
    key = f"{directory}::{name}"
    cached = _SIBLINGS.get(key)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(f"grill_core._{name}", directory / f"{name}.py")
    if spec is None or spec.loader is None:
        raise Failure(EXIT_BLOCKED, "FILESYSTEM", f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
    except BaseException as error:
        sys.modules.pop(spec.name, None)
        raise Failure(EXIT_BLOCKED, "FILESYSTEM", f"unable to load {name}: {type(error).__name__}") from None
    _SIBLINGS[key] = module
    return module


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def registry_state() -> dict:
    """Parse, schema- and step-set-validate, then hash the registry.

    LD-001: peça C (``grill_core.step_skills``) owns the registry asset and its
    hash/validation functions; this module only consumes them, never
    reimplements them. That is the only way ``registry_sha256`` here and the
    ``registry_sha256`` any ``skill-resolution/v1`` or ``skill-invocation/v1``
    receipt from peça C carries can ever be guaranteed to be the *same string*
    for the same bytes -- ``sha256:<64-lowercase-hex>``, matching plan 4.1's
    literal schema. See ``RegistryHashParity`` in
    ``tests/validate_workflow_v3_contract.py`` for the cross-piece comparison.

    Delegating also means every logical-identity rule peça C enforces (exact
    step set and order, non-duplicate ``skill_id``, non-empty fields, resolved
    runtimes shaped correctly, ...) is enforced here for free: a registry entry
    that is absent, ``null``, empty, missing ``skill_id`` or aliases another
    step's ``skill_id`` fails closed with REGISTRY_INVALID, not a false OK.

    Fails closed with REGISTRY_INVALID before this module ever reports a
    ``registry`` field or performs a write.
    """
    module = sibling("step_skills", GRILL_CORE)
    try:
        document, registry_sha256_value = module.load_registry(REGISTRY)
    except module.SkillResolutionError as error:
        raise Failure(
            EXIT_BLOCKED,
            "REGISTRY_INVALID",
            f"registry failed validation: {error.code}/{error.reason}",
            ref=REGISTRY_REF,
            **error.detail,
        ) from None
    return {"ref": REGISTRY_REF, "schema": document["schema"], "sha256": registry_sha256_value}


def pinned_registry_sha256(text: str) -> str | None:
    """Extract the ``registry_sha256`` a materialised v3 WORKFLOW.md pins, if any.

    Returns ``None`` when the document carries no pin at all (the anchor prose
    is absent). Returns the literal placeholder string when the template was
    materialised without rendering it. Neither case is special-cased further:
    both simply fail the equality check against the live registry hash in
    ``execution_gate``, the same way a wrong hash does.
    """
    match = PIN_ANCHOR_RE.search(text)
    return match.group(1) if match else None


def pin_is_current(text: str) -> bool:
    """Whether the ``registry_sha256`` a v3 document pins matches the live
    registry bytes -- neither the unrendered ``__REGISTRY_SHA256__``
    placeholder nor a stale/forged value.

    Exposed as its own small predicate, not folded only into
    ``execution_gate``, so another module that dynamically loads this one
    (LD-004/peça E: ``ensure_workflow.py``'s ``_execution_ready``) can
    consult the real pin gate instead of only checking substring
    compatibility -- a v3-marked document that declares every ``ESSENTIAL``
    token but pins a divergent or placeholder hash is not execution-ready.
    """
    return pinned_registry_sha256(text) == registry_state()["sha256"]


def render_v3(template_text: str, registry_sha256_value: str) -> str:
    """Bake the live ``registry_sha256`` into the v3 document; never ship a bare promise."""
    if template_text.count(REGISTRY_SHA256_PLACEHOLDER) != 1:
        raise Failure(
            EXIT_BLOCKED,
            "WORKFLOW_TEMPLATE_INVALID",
            "bundled v3 template must declare the registry sha256 placeholder exactly once",
        )
    return template_text.replace(REGISTRY_SHA256_PLACEHOLDER, registry_sha256_value)


def runtime_wired() -> bool:
    """Whether ensure_workflow.py's real production reader already accepts a
    correctly rendered, correctly pinned v3 WORKFLOW.md.

    ROUND-3 GAP, fixed here: this used to be
    ``sibling("ensure_workflow").VERSION == VERSION`` -- comparing the
    version fresh bootstrap MATERIALISES (``ensure_workflow.VERSION``, frozen
    at "v2" by Fase 0 so no v2 consumer regresses) against the version this
    module renders. That predicate can never become True without breaking
    Fase 0, so the gate was permanently closed by construction, independent
    of whether the runtime could actually READ a v3 document -- and by
    LD-004 it already could (``ensure_workflow.resolve_workflow`` grew a v3
    branch that never touches ``VERSION``).

    A functional probe instead, in the spirit of
    ``work_item_v3.production_reader_accepts_v3()``: render the bundled v3
    template with the LIVE registry hash, materialise it as ``WORKFLOW.md``
    in a throwaway git repository, and ask the real reader --
    ``ensure_workflow.resolve_workflow``, the exact function ``--ensure`` and
    ``grill_workspace.py init`` call on every real bundle -- whether it
    resolves the document as a v3 ``REUSED`` with the bytes we wrote read
    back unchanged. Any failure along the way (sibling missing the v3
    surface, sibling unloadable, git/filesystem error, any other verdict)
    means "not wired": ``migrate --apply`` stays fail-closed rather than
    guess.
    """
    module = sibling("ensure_workflow")
    if not hasattr(module, "resolve_workflow") or not hasattr(module, "V3_MARKER_VERSION"):
        return False
    try:
        _, template_text_raw = bundled_template()
        rendered = render_v3(template_text_raw, registry_state()["sha256"])
    except Failure:
        return False
    rendered_bytes = rendered.encode("utf-8")
    try:
        with tempfile.TemporaryDirectory(prefix="grill-v3-runtime-probe-") as probe_dir:
            probe_root = Path(probe_dir).resolve()
            subprocess.run(
                ["git", "init", "-q", "-b", "main", str(probe_root)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            (probe_root / "WORKFLOW.md").write_bytes(rendered_bytes)
            result = module.resolve_workflow(probe_root)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.status == "REUSED" and result.content == rendered_bytes


def marker_version(text: str) -> str | None:
    return sibling("ensure_workflow").managed_version(text)


def compatible_v2(text: str) -> bool:
    return sibling("ensure_workflow").compatible(text)


def canonical_step_order(text: str) -> bool:
    """Whether every explicit full execution sequence is in canonical v3 order.

    A human-maintained v3 document need not retain the managed marker or the
    template's exact whitespace.  It must, however, retain an unambiguous
    declaration of the eleven-step external cycle.  Accept either of the
    template's human-readable forms (an arrow chain or its Step table), while
    refusing a document where either declared form reorders the required
    steps.  Looking only inside the cycle section prevents unrelated examples
    (such as the semantic-emulation prohibition) from being mistaken for the
    execution sequence.
    """
    match = _CYCLE_HEADING_RE.search(text)
    if match is None:
        return False
    cycle = match.group("body")
    found_sequence = False

    # An arrow in this section is an explicit execution declaration.  It may
    # wrap across adjacent Markdown lines, but it may never be silently
    # ignored: accepting only a well-shaped 11-token line allowed a duplicate
    # or wrapped/reordered declaration to hide behind the canonical table.
    # Every contiguous arrow block must itself be the one canonical sequence.
    arrow_block: list[str] = []
    for line in [*cycle.splitlines(), ""]:
        if "→" in line:
            arrow_block.append(line)
            continue
        if not arrow_block:
            continue
        steps = tuple(_STEP_TOKEN_RE.findall("\n".join(arrow_block)))
        if steps != CANONICAL_STEP_ORDER:
            return False
        found_sequence = True
        arrow_block = []

    # The table is a second declaration in the managed template.  If a
    # human-maintained equivalent keeps that table, it cannot silently
    # contradict the canonical arrow chain.
    table_steps = tuple(step for step in _TABLE_STEP_RE.findall(cycle) if step in CANONICAL_STEP_ORDER)
    if table_steps:
        if len(table_steps) != len(CANONICAL_STEP_ORDER) or set(table_steps) != set(CANONICAL_STEP_ORDER):
            return False
        found_sequence = True
        if table_steps != CANONICAL_STEP_ORDER:
            return False

    return found_sequence


def compatible_v3(text: str) -> bool:
    return bool(text.strip()) and all(item in text for item in ESSENTIAL) and canonical_step_order(text)


def missing_v3(text: str) -> tuple[str, ...]:
    missing = [item for item in ESSENTIAL if item not in text]
    if not canonical_step_order(text):
        missing.append(STEP_ORDER_MISSING)
    return tuple(missing)


def detect_text(text: str) -> Detection:
    """Classify one workflow document. Pure, so callers can gate without touching disk."""
    marker = marker_version(text)
    v2 = compatible_v2(text)
    v3 = compatible_v3(text)
    version = marker if marker else None
    return Detection(marker, version, v2, v3, missing_v3(text))


def execution_gate(text: str) -> Gate:
    """v3 execution gate. A human equivalent is accepted only if it declares the
    frontier AND pins the live registry hash -- a materialised document that
    still carries the unrendered ``__REGISTRY_SHA256__`` placeholder, or that
    pins a hash that does not match the registry's current bytes, is rejected
    here on READ, not only refused at migration-write time.
    """
    detection = detect_text(text)
    if detection.marker not in (None, VERSION):
        return Gate("BLOCKED", "WORKFLOW_INCOMPATIBLE", detection.missing_v3)
    if not detection.v3_compatible:
        return Gate("BLOCKED", "WORKFLOW_INCOMPATIBLE", detection.missing_v3)
    if not pin_is_current(text):
        return Gate("BLOCKED", "REGISTRY_PIN_DIVERGENT", ())
    return Gate("OK", None, ())


def v2_gate(text: str) -> Gate:
    """v2 stays valid for v2 regardless of the v3 allowlist."""
    detection = detect_text(text)
    if detection.marker not in (None, "v2"):
        return Gate("BLOCKED", "WORKFLOW_INCOMPATIBLE", ())
    if not detection.v2_compatible:
        return Gate("BLOCKED", "WORKFLOW_INCOMPATIBLE", ())
    return Gate("OK", None, ())


def resolve_root(root_argument: str | Path) -> Path:
    candidate = Path(root_argument).expanduser()
    if not candidate.is_dir():
        raise Failure(EXIT_BLOCKED, "WORKFLOW_ROOT_INVALID", "ROOT must be existing Git top-level")
    root = candidate.resolve()
    if sibling("ensure_workflow").git_root(root) != root:
        raise Failure(EXIT_BLOCKED, "WORKFLOW_ROOT_INVALID", "ROOT must be existing Git top-level")
    return root


def load_workflow(root: Path) -> tuple[Path, bytes, str]:
    target = root / "WORKFLOW.md"
    if target.is_symlink() or target.resolve(strict=False).parent != root:
        raise Failure(EXIT_BLOCKED, "WORKFLOW_UNSAFE", "unsafe workflow target")
    if not target.exists():
        raise Failure(EXIT_BLOCKED, "WORKFLOW_MISSING", "WORKFLOW.md is absent")
    try:
        content, text = sibling("ensure_workflow").read_regular(target)
    except UnicodeError:
        raise Failure(EXIT_BLOCKED, "WORKFLOW_INVALID_UTF8", "workflow is not valid UTF-8") from None
    except OSError as error:
        raise Failure(EXIT_BLOCKED, "FILESYSTEM", f"filesystem-error:{type(error).__name__}") from None
    return target, content, text


def bundled_template() -> tuple[bytes, str]:
    try:
        content, text = sibling("ensure_workflow").read_regular(TEMPLATE_V3)
    except (OSError, UnicodeError):
        raise Failure(EXIT_BLOCKED, "WORKFLOW_TEMPLATE_INVALID", "bundled v3 template unreadable") from None
    if marker_version(text) != VERSION or not compatible_v3(text):
        raise Failure(EXIT_BLOCKED, "WORKFLOW_TEMPLATE_INVALID", "bundled v3 template is not v3")
    return content, text


def unified_diff(current: str, target: str) -> str:
    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            target.splitlines(keepends=True),
            fromfile="a/WORKFLOW.md",
            tofile="b/WORKFLOW.md",
            n=3,
        )
    )


def fsync_directory(directory: Path) -> None:
    try:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        descriptor = os.open(directory, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        # Directory fsync is unavailable on some supported filesystems.
        pass


def atomic_replace(target: Path, content: bytes, expected: bytes) -> None:
    """Replace target only while it still holds the previewed bytes (CAS, no clobber)."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    moved = False
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(os.stat(target).st_mode))
        if target.is_symlink() or target.resolve(strict=False).parent != target.parent:
            raise Failure(EXIT_BLOCKED, "WORKFLOW_UNSAFE", "workflow became unsafe before apply")
        current, _ = sibling("ensure_workflow").read_regular(target)
        if current != expected:
            raise Failure(EXIT_BLOCKED, "STATE_DIVERGENCE", "workflow changed since preview")
        os.replace(temporary, target)
        moved = True
        fsync_directory(target.parent)
    except (OSError, UnicodeError) as error:
        raise Failure(EXIT_BLOCKED, "FILESYSTEM", f"filesystem-error:{type(error).__name__}") from None
    finally:
        if not moved:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def apply_command_line(root: Path, current_sha256: str) -> str:
    return f"python3 {HERE} migrate {root} --apply --expected-sha256 {current_sha256}"


def detect_command(root_argument: str | Path) -> tuple[dict, int]:
    """Read-only. Reports the materialised version and both gates."""
    root = resolve_root(root_argument)
    target, content, text = load_workflow(root)
    detection = detect_text(text)
    v3 = execution_gate(text)
    v2 = v2_gate(text)
    payload = {
        "schema": SCHEMA,
        "verdict": "OK",
        "path": str(target),
        "sha256": digest(content),
        "marker": detection.marker,
        "version": detection.version,
        "v2_compatible": detection.v2_compatible,
        "v3_compatible": detection.v3_compatible,
        "v2_execution": {"status": v2.status, "code": v2.code},
        "v3_execution": {"status": v3.status, "code": v3.code, "missing": sorted(set(v3.missing))},
        "registry": registry_state(),
        "runtime_wired": runtime_wired(),
    }
    return payload, EXIT_OK


def migrate_command(
    root_argument: str | Path,
    *,
    apply: bool = False,
    expected_sha256: str | None = None,
    allow_local_edits: bool = False,
) -> tuple[dict, int]:
    """Preview-first v2 -> v3. Apply is a distinct, authorised, CAS-guarded mutation."""
    root = resolve_root(root_argument)
    target, content, text = load_workflow(root)
    detection = detect_text(text)
    template_content_raw, template_text_raw = bundled_template()
    registry = registry_state()
    template_text = render_v3(template_text_raw, registry["sha256"])
    template_content = template_text.encode("utf-8")
    current_sha256 = digest(content)
    target_sha256 = digest(template_content)
    base = {
        "schema": SCHEMA,
        "path": str(target),
        "from_version": detection.version,
        "to_version": VERSION,
        "current_sha256": current_sha256,
        "target_sha256": target_sha256,
        "registry": registry,
    }

    if detection.marker == VERSION and not detection.v3_compatible:
        raise Failure(
            EXIT_BLOCKED,
            "WORKFLOW_INCOMPATIBLE",
            "workflow claims v3 but does not declare the v3 frontier",
            findings=sorted(set(detection.missing_v3)),
        )
    gate = execution_gate(text)
    if detection.marker == VERSION and gate.status != "OK":
        # Declares v3 and the frontier prose, but its pinned registry_sha256 is
        # the unrendered placeholder or does not match the live registry bytes.
        # Never REUSED, never silently re-migrated over -- fail closed and name
        # the exact reason instead of falling through to a generic
        # "not a migratable v2 document".
        raise Failure(
            EXIT_BLOCKED,
            gate.code,
            "workflow claims v3 but its pinned registry_sha256 does not match the live registry",
        )
    if gate.status == "OK":
        # Managed v3 or a human equivalent that already declares the frontier
        # and pins the live registry hash: nothing to migrate, and a human
        # document is never clobbered.
        return {**base, "verdict": "REUSED", "applied": False, "diff": ""}, EXIT_OK

    if detection.marker not in (None, "v2") or not detection.v2_compatible:
        raise Failure(
            EXIT_BLOCKED,
            "WORKFLOW_INCOMPATIBLE",
            "workflow is not a migratable managed v2 document",
            findings=sorted(set(detection.missing_v3)),
        )

    pristine = content == read_v2_template()
    diff = unified_diff(text, template_text)
    if not apply:
        return (
            {
                **base,
                "verdict": "PREVIEW",
                "applied": False,
                "pristine": pristine,
                "diff": diff,
                "next_command": apply_command_line(root, current_sha256),
            },
            EXIT_OK,
        )

    if not expected_sha256:
        raise Failure(
            EXIT_BLOCKED,
            "INVALID_ARGUMENTS",
            "--apply requires --expected-sha256 from a preview",
        )
    if expected_sha256 != current_sha256:
        raise Failure(
            EXIT_BLOCKED,
            "STATE_DIVERGENCE",
            "expected sha256 does not match the current workflow",
        )
    if not pristine and not allow_local_edits:
        raise Failure(
            EXIT_NO_GO,
            "WORKFLOW_LOCAL_EDITS",
            "workflow diverges from the bundled v2 template; migrate manually or pass --allow-local-edits",
        )
    if not runtime_wired():
        raise Failure(
            EXIT_BLOCKED,
            "V3_RUNTIME_NOT_WIRED",
            "ensure_workflow.py does not accept a v3 marker yet; migration stays "
            "fail-closed until a CLI-wiring round teaches the runtime about v3",
        )

    atomic_replace(target, template_content, content)
    _, written, written_text = load_workflow(root)
    if digest(written) != target_sha256 or marker_version(written_text) != VERSION:
        raise Failure(EXIT_BLOCKED, "STATE_DIVERGENCE", "read-back after apply failed")
    return (
        {
            **base,
            "verdict": "APPLIED",
            "applied": True,
            "pristine": pristine,
            "diff": diff,
        },
        EXIT_OK,
    )


def read_v2_template() -> bytes:
    try:
        content, _ = sibling("ensure_workflow").read_regular(TEMPLATE_V2)
    except (OSError, UnicodeError):
        raise Failure(EXIT_BLOCKED, "WORKFLOW_TEMPLATE_INVALID", "bundled v2 template unreadable") from None
    return content


class JsonParser(argparse.ArgumentParser):
    """argparse never writes usage text: bad arguments stay one JSON document on stdout."""

    def error(self, message: str):  # type: ignore[override]
        raise Failure(EXIT_BLOCKED, "INVALID_ARGUMENTS", message)

    def exit(self, status: int = 0, message: str | None = None):  # type: ignore[override]
        if status:
            raise Failure(EXIT_BLOCKED, "INVALID_ARGUMENTS", message or "invalid arguments")
        raise SystemExit(status)


def build_parser() -> JsonParser:
    parser = JsonParser(add_help=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    detect = subparsers.add_parser("detect", add_help=False)
    detect.add_argument("root")
    migrate = subparsers.add_parser("migrate", add_help=False)
    migrate.add_argument("root")
    migrate.add_argument("--apply", action="store_true")
    migrate.add_argument("--expected-sha256", dest="expected_sha256")
    migrate.add_argument("--allow-local-edits", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = build_parser().parse_args(argv)
        if arguments.command == "detect":
            payload, code = detect_command(arguments.root)
        else:
            payload, code = migrate_command(
                arguments.root,
                apply=arguments.apply,
                expected_sha256=arguments.expected_sha256,
                allow_local_edits=arguments.allow_local_edits,
            )
    except Failure as failure:
        payload = {
            "schema": SCHEMA,
            "verdict": failure.verdict,
            "code": failure.code,
            "error": failure.message,
            **failure.extra,
        }
        code = failure.exit_code
    except OSError as error:
        payload = {
            "schema": SCHEMA,
            "verdict": "BLOCKED",
            "code": "FILESYSTEM",
            "error": f"filesystem-error:{type(error).__name__}",
        }
        code = EXIT_BLOCKED
    except (UnicodeError, json.JSONDecodeError) as error:
        payload = {
            "schema": SCHEMA,
            "verdict": "BLOCKED",
            "code": "WORKFLOW_INVALID_UTF8",
            "error": type(error).__name__,
        }
        code = EXIT_BLOCKED
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
