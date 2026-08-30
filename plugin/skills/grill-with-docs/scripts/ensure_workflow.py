#!/usr/bin/env python3
"""Safe workflow bootstrap plus a read-only lifecycle hook (stdlib only)."""
from __future__ import annotations

import argparse
import contextlib
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

VERSION = "v2"
MARKER = "grill-with-docs-workflow:v2"
HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[1] / "assets/WORKFLOW.v4.template.md"
# LD-004 item 3/4: a NEW, additive marker recognised alongside VERSION ("v2").
# VERSION and the v2 ESSENTIAL tuple stay untouched so already materialised v2
# documents retain their original read contract; BOOTSTRAP_VERSION below owns
# the independent choice for an absent document.
V3_MARKER_VERSION = "v3"
# Same additive contract LD-004 established for v3: a NEW marker recognised
# alongside VERSION, never assigned to it. The v2 ESSENTIAL tuple below stays
# byte-for-byte untouched even though fresh bootstrap now selects v4.
V4_MARKER_VERSION = "v4"
# Existing v2 documents remain readable against VERSION/ESSENTIAL above, but
# a fresh project must start on the executable frontier.  Keeping these names
# separate is what lets bootstrap advance without silently reinterpreting an
# already-materialised v2 document as v4.
BOOTSTRAP_VERSION = V4_MARKER_VERSION
#: Marker versions this build can execute against, newest last. v2 remains
#: readable through its frozen legacy contract but was never executable.
EXECUTABLE_MARKER_VERSIONS = (V3_MARKER_VERSION, V4_MARKER_VERSION)
# Same path grill_core/workflow_v3.py resolves REGISTRY to (its ASSETS is
# HERE.parents[2] / "assets" from one directory deeper); kept as a literal
# here rather than imported so this module has no load-time dependency on
# grill_core, matching the read-only, best-effort spirit of the hook.
REGISTRY = HERE.parents[1] / "assets/workflow-step-skills.json"
#: Registry asset per marker version. A materialised document pins the digest
#: of the registry belonging to ITS version, so the hook has to publish that
#: one -- publishing the active build's digest to a v3 repository would make
#: every v3 document look REGISTRY-PIN-DIVERGENT to whoever reads the hook.
REGISTRY_BY_VERSION = {
    V3_MARKER_VERSION: REGISTRY,
    V4_MARKER_VERSION: HERE.parents[1] / "assets/workflow-step-skills.v4.json",
}
#: The canonical cycle the hook prints, per marker version.
FLOW_BY_VERSION = {
    V3_MARKER_VERSION: ("specify → plan → checklist → tasks → analyze → agent-assign → "
                        "agent-execute → converge → verify → review → ship"),
    V4_MARKER_VERSION: ("specify → plan → checklist → tasks → analyze → partition → "
                        "implement-parallel → converge → verify → review → ship"),
}
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
)


class WorkflowResult(NamedTuple):
    """Decision taken about WORKFLOW.md, decoupled from how it is reported."""

    status: str
    path: Path | None
    content: bytes
    reason: str | None


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git_root(path: Path) -> Path | None:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return Path(output.strip()).resolve()


def compatible(text: str) -> bool:
    return bool(text.strip()) and all(item in text for item in ESSENTIAL)


def managed_version(text: str) -> str | None:
    match = re.search(r"grill-with-docs-workflow:(v\d+)", text)
    return match.group(1) if match else None


_GRILL_CORE: dict[str, object] = {}


def _load_grill_core(name: str):
    """Best-effort load of ``grill_core/<name>.py``; ``None`` on any failure.

    This module never edits grill_core (LD-004: it belongs to other pieces),
    it only consumes it as a library, and only for the one pure, side-effect
    free function it needs (``workflow_v3.compatible_v3``). Any load failure
    -- module absent, unreadable, syntactically broken while another builder
    is mid-edit -- degrades to "v3 not recognised" instead of raising: the
    hook and ``--ensure`` must stay usable even if that sibling module is
    momentarily unstable (gaps_deferred, not a reason to edit it).
    """
    if name in _GRILL_CORE:
        return _GRILL_CORE[name]
    try:
        path = HERE.with_name("grill_core") / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"ensure_workflow_grill_core_{name}", path)
        if spec is None or spec.loader is None:
            module = None
        else:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            with contextlib.redirect_stdout(io.StringIO()):
                spec.loader.exec_module(module)
    except BaseException:
        if 'spec' in locals() and spec is not None:
            sys.modules.pop(spec.name, None)
        module = None
    _GRILL_CORE[name] = module
    return module


def compatible_v3(text: str) -> bool:
    """v3 compatibility, delegated to grill_core/workflow_v3.py's own ESSENTIAL tuple.

    Single source of truth stays with the module that owns the v3 template
    and registry (peça D); this only asks it the same pure question
    ``resolve_workflow`` already asks ``compatible()`` for v2. An unloadable
    module means "not v3-compatible" -- the same BLOCKED outcome a v3-marked
    file already produced before this round, never a crash.

    Deliberately ESSENTIAL-substring-only, same as ``workflow_v3.compatible_v3``
    -- it does NOT check the registry pin. Callers that decide whether a v3
    document is safe to treat as READY (``resolve_workflow``'s REUSED branch,
    ``_execution_ready``) must use :func:`_v3_ready` instead, which also
    verifies the pin. This function stays a pure frontier check because
    ``tests/validate_v3_wiring_contract.py`` asserts it is identical to
    ``workflow_v3.compatible_v3`` (delegation, not the fuller execution gate).
    """
    module = _load_grill_core("workflow_v3")
    if module is None or not hasattr(module, "compatible_v3"):
        return False
    try:
        return bool(module.compatible_v3(text))
    except Exception:
        return False


def _v3_ready(text: str) -> bool:
    """v3 READINESS: ESSENTIAL frontier AND registry pin match (LD-010 item 2).

    Closes the fail-open this round opened: ``compatible_v3``/the old
    ``_execution_ready`` only tested ESSENTIAL substrings, and the literal
    unrendered ``__REGISTRY_SHA256__`` placeholder -- or a forged pin -- both
    still CONTAIN the substring "registry_sha256", so a substring-only check
    let them through. Delegates to ``grill_core/workflow_v3.py``'s
    ``execution_gate``, the same gate ``workflow_v3 detect`` already applies
    on read, so a document REUSED here can never disagree with what that
    module would report for the identical bytes. An unloadable module or any
    failure degrades to "not ready" -- the same conservative posture as
    ``compatible_v3`` -- never a crash.
    """
    module = _load_grill_core("workflow_v3")
    if module is None or not hasattr(module, "execution_gate"):
        return False
    try:
        return module.execution_gate(text).status == "OK"
    except Exception:
        return False


def bootstrap_document() -> tuple[bytes, str] | None:
    """Render the active bootstrap document through its owning version module."""
    if BOOTSTRAP_VERSION != V4_MARKER_VERSION:
        return None
    module = _load_grill_core("workflow_v4")
    if module is None or not hasattr(module, "render_v4"):
        return None
    try:
        _, template_text = read_regular(TEMPLATE)
        content = module.render_v4(template_text)
        text = content.decode("utf-8")
        if managed_version(text) != BOOTSTRAP_VERSION or module.execution_gate(text).status != "OK":
            return None
        return content, text
    except Exception:
        return None


def read_regular(path: Path) -> tuple[bytes, str]:
    """Open one regular file without following a final-component symlink."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    content = b"".join(chunks)
    return content, content.decode("utf-8")


def emit(status: str, path: Path | None = None, content: bytes | None = None, *, version: str = VERSION, **extra: str) -> None:
    payload: dict[str, str] = {"status": status, **extra}
    if path is not None and content is not None:
        payload.update(path=str(path), sha256=digest(content), version=version)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def atomic_create(target: Path, content: bytes) -> bool:
    """Create target exactly once; never replace an existing directory entry."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
            created = True
        except FileExistsError:
            created = False
        try:
            directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            directory_descriptor = os.open(target.parent, directory_flags)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError:
            # Directory fsync is unavailable on some supported filesystems.
            pass
        return created
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def resolve_workflow(root_argument: str | Path) -> WorkflowResult:
    """Materialise or validate WORKFLOW.md and return the decision without printing.

    Callers that own stdout (the CLI) render the result; callers embedded in
    another command (init) consume it directly, so the single-line JSON
    contract of the embedding command stays intact.
    """
    candidate = Path(root_argument).expanduser()
    if not candidate.is_dir():
        return WorkflowResult("BLOCKED", None, b"", "ROOT must be existing Git top-level")
    root = candidate.resolve()
    if git_root(root) != root:
        return WorkflowResult("BLOCKED", None, b"", "ROOT must be existing Git top-level")

    target = root / "WORKFLOW.md"
    try:
        if target.is_symlink() or target.resolve(strict=False).parent != root:
            return WorkflowResult("BLOCKED", None, b"", "unsafe target")

        if target.exists():
            content, text = read_regular(target)
            version = managed_version(text)
            # v3 branch first and separately from the v2 mismatch check below:
            # a v3-marked file must never hit "managed version mismatch" (that
            # is the exact failure LD-004 exists to close), and the v2
            # ESSENTIAL tuple / compatible() must never be asked to validate
            # v3 content. Falling through here is impossible -- both arms
            # return -- so a v2/unmarked/human-equivalent file takes the
            # unmodified path below, byte for byte.
            if version == V4_MARKER_VERSION:
                # Same shape as the v3 arm below, for the same reason: a
                # v4-marked file must never be judged by the v2 ESSENTIAL
                # tuple, and readiness means the registry pin matches, not
                # merely that the frontier words are present.
                if _v4_ready(text):
                    return WorkflowResult("REUSED", target, content, None)
                return WorkflowResult("BLOCKED", None, b"", "incompatible workflow")
            if version == V3_MARKER_VERSION:
                # _v3_ready, not compatible_v3: REUSED must mean "safe to
                # execute against", which requires the registry pin to match,
                # not merely the ESSENTIAL frontier being present (LD-010
                # item 2 -- this is the same gate --ensure/init must apply).
                if _v3_ready(text):
                    return WorkflowResult("REUSED", target, content, None)
                return WorkflowResult("BLOCKED", None, b"", "incompatible workflow")
            if version and version != VERSION:
                return WorkflowResult("BLOCKED", None, b"", "managed version mismatch")
            if compatible(text):
                return WorkflowResult("REUSED", target, content, None)
            return WorkflowResult("BLOCKED", None, b"", "incompatible workflow")

        rendered = bootstrap_document()
        if rendered is None:
            return WorkflowResult("BLOCKED", None, b"", "invalid bundled template")
        template_content, _template_text = rendered
        created = atomic_create(target, template_content)

        if target.is_symlink() or target.resolve(strict=False).parent != root:
            return WorkflowResult("BLOCKED", None, b"", "unsafe target after create")
        content, text = read_regular(target)
        version = managed_version(text)
        if version != BOOTSTRAP_VERSION or not _v4_ready(text):
            return WorkflowResult("BLOCKED", None, b"", "read-back validation failed")
        return WorkflowResult("CREATED" if created else "REUSED", target, content, None)
    except UnicodeError:
        return WorkflowResult("BLOCKED", None, b"", "invalid UTF-8 workflow")
    except OSError as error:
        return WorkflowResult("BLOCKED", None, b"", f"filesystem-error:{type(error).__name__}")


def ensure(root_argument: str) -> int:
    result = resolve_workflow(root_argument)
    if result.status == "BLOCKED":
        emit("BLOCKED", reason=result.reason or "unknown")
        return 2
    # Report the marker actually materialised/read back: CREATED now says v4,
    # while a REUSED v3 or v2 document retains its own declared version.
    try:
        actual_version = managed_version(result.content.decode("utf-8")) or VERSION
    except UnicodeError:
        actual_version = VERSION
    emit(result.status, result.path, result.content, version=actual_version)
    return 0


def human_status(payload: dict, root: Path) -> str:
    items = payload.get("work_items")
    if not isinstance(items, list):
        return "BLOCKED status: payload work_items inválido"
    count = len(items)
    if count == 0:
        return f"Itens: 0; inicialização necessária. Comando: grill_workspace.py init {root}"
    if count > 1:
        brief = ", ".join(f"{i.get('work_id','?')}:{(i.get('locations') or [{}])[0].get('branch','?')}" for i in items[:4] if isinstance(i, dict))
        return f"Itens: {count}; múltiplos work-items ({brief}); use --work-id."
    item = items[0] if isinstance(items[0], dict) else {}
    loc = (item.get("locations") or [{}])[0]
    planning = item.get("planning") or {}; development = item.get("development") or {}
    blockers = item.get("blockers") or item.get("findings") or []
    blockers = ", ".join(map(str, blockers[:3])) if isinstance(blockers, list) else str(blockers)
    completed = development.get("completed") if isinstance(development.get("completed"), list) else []
    return (f"Itens: 1; id={item.get('work_id','?')}; branch={loc.get('branch','?')}; head={str(loc.get('head','?'))[:12]}; "
            f"fase={planning.get('active_phase','?')}; DU/type={','.join(planning.get('delivery_units',[]) or []) or item.get('type','?')}; "
            f"etapa={development.get('current_step','?')}; concluídas={len(completed)}/11; próximo gate={item.get('next_gate','?')}; "
            f"blockers={blockers or 'nenhum'}. Comando: grill_workspace.py status {root}")


def render_hook_output(event: str, message: str) -> str:
    """Render one bounded hook JSON object without writing it."""
    output = {
        "status": "OK",
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": message,
        },
    }
    rendered = json.dumps(output, ensure_ascii=False, sort_keys=True)
    if len(rendered) > 2048:
        marker = "[TRUNCATED]"
        context = message
        while len(rendered) > 2048 and context:
            context = context[: max(0, len(context) - 128)]
            output["hookSpecificOutput"]["additionalContext"] = context.rstrip() + marker
            rendered = json.dumps(output, ensure_ascii=False, sort_keys=True)
        if len(rendered) > 2048:
            output["hookSpecificOutput"]["additionalContext"] = marker
            rendered = json.dumps(output, ensure_ascii=False, sort_keys=True)
    return rendered


def _v4_ready(text: str) -> bool:
    """v4 READINESS: v4 frontier AND live v4 registry pin.

    Same posture as :func:`_v3_ready` -- delegates to the module that owns the
    v4 template and registry, so a document REUSED here can never disagree with
    what ``workflow_v4 detect`` reports for identical bytes. An unloadable
    module degrades to "not ready", never a crash.
    """
    module = _load_grill_core("workflow_v4")
    if module is None or not hasattr(module, "execution_gate"):
        return False
    try:
        return module.execution_gate(text).status == "OK"
    except Exception:
        return False


def _execution_ready(text: str) -> bool:
    """True when ``text`` is a materialised workflow the hook can safely project status for."""
    version = managed_version(text)
    if version == V4_MARKER_VERSION:
        return _v4_ready(text)
    if version == V3_MARKER_VERSION:
        return _v3_ready(text)
    return version == VERSION and compatible(text)


def _registry_prefix(version: str | None = None) -> str:
    """LD-004 item 4 / LD-001: registry_sha256 (raw bytes hash) + the anti-emulation phrase.

    Built first, standalone, so it can be placed before the status projection
    in the hook message: render_hook_output truncates from the END of the
    string when the 2048-byte budget is exceeded, so anything after this
    prefix -- including the whole status line -- is what gets cut, never this.
    A missing/unreadable registry degrades the hash, not the phrase: the
    instruction to invoke the canonical skill instead of emulating it holds
    regardless of whether the registry asset can be read right now.
    """
    target = REGISTRY_BY_VERSION.get(version or V3_MARKER_VERSION, REGISTRY)
    try:
        registry_sha256 = digest(target.read_bytes())
    except OSError:
        registry_sha256 = "unavailable"
    return f"registry_sha256={registry_sha256}; read, resolve and invoke; do not emulate."


def hook() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError, UnicodeError):
        emit("BLOCKED", reason="invalid-json")
        return 0
    if not isinstance(payload, dict):
        emit("BLOCKED", reason="invalid-payload")
        return 0

    event = payload.get("hook_event_name")
    if event not in ("SessionStart", "SubagentStart"):
        emit("IGNORED")
        return 0
    root = git_root(Path(payload.get("cwd") or os.getcwd()))
    if root is None:
        emit("BLOCKED", reason="invalid-root")
        return 0

    path = root / "WORKFLOW.md"
    if path.is_symlink() or (path.exists() and path.resolve(strict=False).parent != root):
        message = f"WORKFLOW.md inseguro em {path}; invoque grill-with-docs para auditar."
    elif not path.is_file():
        message = f"WORKFLOW.md ausente em {root}; invoque grill-with-docs para preparar o workflow."
    else:
        try:
            content, text = read_regular(path)
        except (OSError, UnicodeError):
            content, text = b"", ""
        if _execution_ready(text):
            try:
                status_script = HERE.with_name("grill_workspace.py")
                result = subprocess.run([sys.executable, str(status_script), "status", str(root), "--current-worktree"], capture_output=True, text=True, check=False, timeout=3)
                status_payload = json.loads(result.stdout.strip()) if result.stdout.strip() else {"verdict":"BLOCKED"}
                status_line = human_status(status_payload, root) if isinstance(status_payload, dict) else "BLOCKED status"
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                status_line = "BLOCKED status"
            # Registry hash + anti-emulation phrase come first (see
            # _registry_prefix): truncation eats the tail (status/Fluxo), not
            # this head, when the 2048-byte hook budget is exceeded.
            materialised = managed_version(text) or V3_MARKER_VERSION
            flow = FLOW_BY_VERSION.get(materialised, FLOW_BY_VERSION[V3_MARKER_VERSION])
            message = (f"{_registry_prefix(materialised)} Leia {path}; sha256={digest(content)}. "
                       f"{status_line} Fluxo: {flow}.")
        else:
            message = f"WORKFLOW.md incompatível em {path}; invoque grill-with-docs para auditar."

    sys.stdout.write(render_hook_output(event, message))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ensure")
    group.add_argument("--hook", action="store_true")
    arguments = parser.parse_args(argv)
    return hook() if arguments.hook else ensure(arguments.ensure)


if __name__ == "__main__":
    raise SystemExit(main())
