"""Observed runtime boundary; caller supplied JSON is never evidence."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_HEX = re.compile(r"^[0-9a-f]{64}$")
_OBSERVATION_KEYS = {
    "schema", "adapter", "provider", "handle", "incarnation",
    "dispatch_incarnation", "runtime_instance", "host", "owner_dispatch",
    "task_id", "worktree_id", "source_ref", "source_sha256",
    "requested_model", "requested_effort", "effective_model",
    "effective_effort", "resolved_model_id", "activity", "close",
}
_ORCA_CAPABILITIES = {
    "orchestration.worker-launch-preferences.v1",
    "orchestration.federation-structured-read.v1",
    "orchestration.federation-lifecycle-settlement.v1",
    "orchestration.federation-release-archive.v1",
}
PRESENTATION_SCHEMA = "grill-gwd-presentation/v1"
PRESENTATION_COMPONENT = "i-have-adhd@i-have-adhd"
PRESENTATION_LOADER = "gwd-reference/v1"
_PRESENTATION_STATES = {"present", "outdated", "missing", "undetermined"}
_PRESENTATION_ENABLEMENT = {"enabled", "disabled", "undetermined"}
_PRESENTATION_TRUST = {"ready", "pending", "undetermined"}
_PRESENTATION_LOADING = {"required", "loaded", "stale", "unconfirmed"}
_PRESENTATION_APPLICATION = {"active", "suspended_by_user", "out_of_scope", "blocked"}
_PRESENTATION_BEHAVIOR = {"not_tested", "conformant", "nonconformant", "unconfirmed"}
_IMPECCABLE_OBSERVATION_KEYS = {
    "schema", "capability", "skill_path", "version", "skill_sha256", "entrypoint",
    "invocation_ref", "invocation_sha256",
}


class RuntimeError(ValueError):
    pass


class PresentationError(ValueError):
    """A presentation axis was not proven from correlated evidence."""

    pass


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _presentation_fail(code: str) -> None:
    raise PresentationError(code)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_impeccable_observation(value: Any) -> dict[str, Any]:
    """Accept a closed observation of an already-resolved Impeccable invocation.

    The visual gate never resolves, installs, or executes the skill.  It only
    consumes this leader-observed record, so a hand-written capability flag is
    not enough to pass the boundary.
    """
    if not isinstance(value, dict) or set(value) != _IMPECCABLE_OBSERVATION_KEYS:
        _fail("IMPECCABLE-CAPABILITY-UNPROVEN")
    if value.get("schema") != "grill-impeccable-observation/v1" or value.get("capability") != "impeccable":
        _fail("IMPECCABLE-CAPABILITY-UNPROVEN")
    for key in ("skill_path", "version", "entrypoint", "invocation_ref"):
        field = value.get(key)
        if not isinstance(field, str) or not field or any(ord(character) < 32 for character in field):
            _fail("IMPECCABLE-CAPABILITY-UNPROVEN")
    for key in ("skill_sha256", "invocation_sha256"):
        if not isinstance(value.get(key), str) or not _HEX.fullmatch(value[key]):
            _fail("IMPECCABLE-CAPABILITY-UNPROVEN")
    return dict(value)


def _safe_reference_bytes(value: str | Path) -> bytes:
    """Read one installed reference without following a symlink or executing it."""
    path = Path(value)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
        raise AssertionError("unreachable") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def presentation_body(raw: bytes) -> bytes:
    """Remove only the initial YAML frontmatter from the approved skill bytes."""
    if not isinstance(raw, bytes) or not raw.startswith(b"---\n"):
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
    closing = raw.find(b"\n---\n", len(b"---\n"))
    if closing < 0:
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
    body = raw[closing + len(b"\n---\n"):]
    if not body:
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
    try:
        body.decode("utf-8")
    except UnicodeDecodeError as exc:
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
        raise AssertionError("unreachable") from exc
    return body


def approved_presentation_reference(*, policy: dict[str, Any], version: str,
                                    skill_ref: str | Path) -> dict[str, Any]:
    """Resolve the exact installed bytes approved by the supplementary policy."""
    presentation = policy.get("presentation") if isinstance(policy, dict) else None
    approved = presentation.get("approved") if isinstance(presentation, dict) else None
    if (not isinstance(version, str) or not isinstance(approved, list)
            or not isinstance(presentation, dict)):
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
    expected = next((entry.get("skill_sha256") for entry in approved
                     if isinstance(entry, dict) and entry.get("version") == version), None)
    if not isinstance(expected, str) or not expected.startswith("sha256:"):
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
    raw = _safe_reference_bytes(skill_ref)
    skill_sha256 = _sha256(raw)
    if skill_sha256 != expected.removeprefix("sha256:"):
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
    body = presentation_body(raw)
    return {
        "version": version, "skill_ref": str(skill_ref), "skill_sha256": skill_sha256,
        "body_sha256": _sha256(body), "body": body,
    }


def _axis(value: Any, *, states: set[str], default: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"state": default, "source_ref": None, "source_sha256": None}
    state = value.get("state", default)
    source_ref, source_sha256 = value.get("source_ref"), value.get("source_sha256")
    if state not in states:
        state = default
    if state != default and (not isinstance(source_ref, str) or not source_ref
                             or not isinstance(source_sha256, str) or not _HEX.fullmatch(source_sha256)):
        state, source_ref, source_sha256 = default, None, None
    return {"state": state, "source_ref": source_ref, "source_sha256": source_sha256}


def _diagnostic(code: str, field: str, reason: str, recovery: str) -> dict[str, str]:
    return {"code": code, "field": field, "reason": reason, "recovery": recovery}


def presentation_state(*, policy: dict[str, Any], policy_sha256: str,
                       gwd_skill_sha256: str, runtime: str, session_identity: str,
                       config_fingerprint: str, scope: dict[str, Any],
                       installation: dict[str, Any] | None,
                       enablement: dict[str, Any] | None,
                       trust: dict[str, Any] | None,
                       loading: dict[str, Any] | None = None,
                       suspension: dict[str, Any] | None = None,
                       application: str = "active",
                       behavior: dict[str, Any] | None = None) -> dict[str, Any]:
    """Project presentation readiness from distinct, correlated observations.

    This is intentionally pure. The session owns observation and injection; the
    core only accepts a full-read event, never a listing, exit status, or model
    self-report as evidence that the reference was loaded.
    """
    if (runtime not in {"codex", "claude"} or not isinstance(session_identity, str)
            or not session_identity or not isinstance(config_fingerprint, str)
            or not config_fingerprint or not isinstance(scope, dict)
            or scope.get("kind") != "gwd" or not _HEX.fullmatch(policy_sha256)
            or not _HEX.fullmatch(gwd_skill_sha256)):
        _presentation_fail("STYLE-SCOPE-CONFLICT")
    configured = policy.get("presentation") if isinstance(policy, dict) else None
    if (not isinstance(configured, dict) or configured.get("schema") != PRESENTATION_SCHEMA
            or configured.get("component") != PRESENTATION_COMPONENT
            or configured.get("loader") != PRESENTATION_LOADER):
        _presentation_fail("STYLE-CONTENT-INCOMPATIBLE")
    installation = dict(installation or {})
    status = installation.get("status", "undetermined")
    if status not in _PRESENTATION_STATES:
        status = "undetermined"
    version = installation.get("version") if isinstance(installation.get("version"), str) else None
    skill_ref = installation.get("skill_ref")
    compatible, reference = "undetermined", None
    diagnostics: list[dict[str, str]] = []
    if config_fingerprint == "unobserved":
        diagnostics.append(_diagnostic("STYLE-CONFIG-UNPROVEN", "config_fingerprint",
            "effective session configuration not observed", "collect configuration from the session's owning harness"))
    if status == "missing":
        diagnostics.append(_diagnostic("STYLE-DEPENDENCY-MISSING", "installation", "component absent", "install through the harness"))
    elif status == "outdated":
        diagnostics.append(_diagnostic("STYLE-DEPENDENCY-OUTDATED", "installation", "version below policy minimum", "install approved version through the harness"))
    elif status == "undetermined":
        diagnostics.append(_diagnostic("STYLE-DEPENDENCY-UNDETERMINED", "installation", "installation source unreadable or ambiguous", "repair the runtime registry and observe again"))
    elif not isinstance(skill_ref, str) or not version:
        compatible = "undetermined"
        diagnostics.append(_diagnostic("STYLE-DEPENDENCY-UNDETERMINED", "installation", "effective skill path not observed", "collect runtime-correlated installation observation"))
    else:
        try:
            reference = approved_presentation_reference(policy=policy, version=version, skill_ref=skill_ref)
            compatible = "approved"
        except PresentationError:
            compatible = "incompatible"
            diagnostics.append(_diagnostic("STYLE-CONTENT-INCOMPATIBLE", "installation", "version or approved bytes differ", "review policy or repair selected installation"))
    install_record = {"status": status, "version": version, "marketplace": installation.get("marketplace"),
                      "install_root": installation.get("install_root"), "manifest_ref": installation.get("manifest_ref"),
                      "skill_ref": skill_ref, "skill_sha256": reference["skill_sha256"] if reference else None,
                      "body_sha256": reference["body_sha256"] if reference else None}
    enabled = _axis(enablement, states=_PRESENTATION_ENABLEMENT, default="undetermined")
    trusted = _axis(trust, states=_PRESENTATION_TRUST, default="undetermined")
    if enabled["state"] == "disabled":
        diagnostics.append(_diagnostic("STYLE-DISABLED", "enablement", "runtime plugin disabled", "use the runtime's native enable control"))
    elif enabled["state"] != "enabled":
        diagnostics.append(_diagnostic("STYLE-ENABLEMENT-UNPROVEN", "enablement", "no correlated enabled observation", "collect plugin state from this session"))
    if trusted["state"] == "pending":
        diagnostics.append(_diagnostic("STYLE-TRUST-PENDING", "trust", "runtime startup trust pending", "resolve trust in the harness UI"))
    elif trusted["state"] != "ready":
        diagnostics.append(_diagnostic("STYLE-TRUST-PENDING", "trust", "startup trust not observed", "collect startup observation"))
    prerequisites = (config_fingerprint != "unobserved" and status == "present" and compatible == "approved"
                     and enabled["state"] == "enabled" and trusted["state"] == "ready")
    request = ({"loader": PRESENTATION_LOADER, "component": PRESENTATION_COMPONENT,
                "version": reference["version"], "skill_ref": reference["skill_ref"],
                "skill_sha256": reference["skill_sha256"], "body_sha256": reference["body_sha256"],
                "policy_sha256": policy_sha256, "gwd_skill_sha256": gwd_skill_sha256,
                "scope": scope, "session_identity": session_identity,
                "config_fingerprint": config_fingerprint} if reference else None)
    requested = None
    loaded = False
    loading_state = "unconfirmed"
    if isinstance(loading, dict) and loading.get("stale") is True:
        loading_state = "stale"
    elif isinstance(loading, dict) and reference is not None:
        loaded = (loading.get("evidence_kind") == "full_read"
                  and loading.get("load_request") == request
                  and isinstance(loading.get("event_ref"), str) and bool(loading.get("event_ref"))
                  and isinstance(loading.get("event_sha256"), str) and bool(_HEX.fullmatch(loading.get("event_sha256")))
                  and loading.get("session_identity") == session_identity
                  and loading.get("config_fingerprint") == config_fingerprint
                  and loading.get("scope") == scope
                  and loading.get("skill_sha256") == reference["skill_sha256"]
                  and loading.get("body_sha256") == reference["body_sha256"])
        loading_state = "loaded" if loaded else "unconfirmed"
    if prerequisites and reference is not None and not loaded and application == "active":
        requested = request
        diagnostics.append(_diagnostic("STYLE-LOAD-UNCONFIRMED", "loading", "full read not observed for this session", "read the exact load_request then collect its full-read event"))
    valid_suspension = (isinstance(suspension, dict) and suspension.get("command") == "stop adhd mode"
                        and isinstance(suspension.get("source_ref"), str) and suspension.get("source_ref")
                        and isinstance(suspension.get("source_sha256"), str) and _HEX.fullmatch(suspension.get("source_sha256"))
                        and suspension.get("session_identity") == session_identity
                        and suspension.get("config_fingerprint") == config_fingerprint
                        and suspension.get("scope") == scope)
    if application == "suspended_by_user" and not valid_suspension:
        application = "blocked"
        diagnostics.append(_diagnostic("STYLE-SCOPE-CONFLICT", "suspension", "suspension is not bound to this session and scope", "collect the explicit user instruction again"))
    elif application not in _PRESENTATION_APPLICATION:
        application = "blocked"
    use_ready = prerequisites and loaded and application == "active"
    work_ready = prerequisites and (use_ready or (application == "suspended_by_user" and valid_suspension))
    observed_behavior = "not_tested"
    if isinstance(behavior, dict) and behavior.get("state") in _PRESENTATION_BEHAVIOR:
        candidate = behavior["state"]
        if candidate == "conformant" and not (isinstance(behavior.get("evidence_ref"), str) and behavior.get("evidence_ref")
                                                 and isinstance(behavior.get("review_ref"), str) and behavior.get("review_ref")):
            observed_behavior = "unconfirmed"
        else:
            observed_behavior = candidate
    functional_verified = use_ready and observed_behavior == "conformant"
    if observed_behavior == "nonconformant":
        diagnostics.append(_diagnostic("STYLE-BEHAVIOR-NONCONFORMANT", "behavior", "reviewed live sample failed", "correct integration and repeat both runtime cases"))
    elif observed_behavior == "unconfirmed":
        diagnostics.append(_diagnostic("STYLE-BEHAVIOR-UNPROVEN", "behavior", "behavior claim lacks reviewed live evidence", "persist complete prompts, responses, and review"))
    return {"schema": PRESENTATION_SCHEMA, "component": PRESENTATION_COMPONENT,
            "minimum_version": configured.get("minimum_version"), "loader": PRESENTATION_LOADER,
            "runtime": runtime, "session_identity": session_identity, "config_fingerprint": config_fingerprint,
            "scope": scope, "policy_sha256": policy_sha256, "gwd_skill_sha256": gwd_skill_sha256,
            "installation": install_record, "compatibility": compatible,
            "enablement": enabled["state"], "trust": trusted["state"], "loading": loading_state,
            "behavior": observed_behavior, "application": application,
            "suspension": dict(suspension) if valid_suspension else None,
            "evidence": {"enablement": enabled, "trust": trusted,
                         "loading": dict(loading) if isinstance(loading, dict) else None,
                         "behavior": dict(behavior) if isinstance(behavior, dict) else None},
            "load_request": requested, "use_ready": use_ready, "work_ready": work_ready,
            "functional_verified": functional_verified, "diagnostics": diagnostics}


def _source_digest(*parts: bytes) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        _fail(f"invalid {label} response")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid {label} response") from exc
    if not isinstance(value, dict) or value.get("ok") is not True or not isinstance(value.get("result"), dict):
        _fail(f"invalid {label} response")
    return value["result"]


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"missing {label}")
    return value


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"missing {label}")
    return value


def _same(label: str, *values: Any) -> str:
    values = tuple(_string(value, label) for value in values)
    if len(set(values)) != 1:
        _fail(f"uncorrelated {label}")
    return values[0]


def session_identity(value: dict[str, Any]) -> tuple[Any, ...]:
    """Return the runtime-issued session identity used for reviewer separation."""
    keys = (
        "adapter", "provider", "handle", "incarnation", "dispatch_incarnation",
        "runtime_instance", "host", "owner_dispatch", "task_id", "worktree_id",
    )
    if any(not value.get(key) for key in keys):
        _fail("runtime identity incomplete")
    return tuple(value[key] for key in keys)


def leader_session_identity(value: dict[str, Any]) -> str:
    """Canonical runtime-issued identity used by presentation correlation."""
    return json.dumps(session_identity(value), ensure_ascii=False, separators=(",", ":"))


def _tool_results(transcript: dict[str, Any]):
    """Only unambiguous adjacent native tool calls/results, never assistant prose."""
    previous = None
    for message in transcript.get("messages", []):
        blocks = message.get("blocks", []) if isinstance(message, dict) else []
        if not isinstance(blocks, list) or len(blocks) != 1 or not isinstance(blocks[0], dict):
            previous = None
            continue
        block = blocks[0]
        if message.get("role") == "tool" and block.get("type") == "tool-result" and previous and message.get("id"):
            output = block.get("output")
            if previous.get("name") == "exec":
                # One literal exec_command, printed unchanged. Never interpret
                # JavaScript, concatenate outputs, or strip arbitrary prose.
                match = re.fullmatch(r"Script completed\nWall time [0-9.]+ seconds\nOutput:\n([\s\S]+)", output or "") if isinstance(output, str) else None
                try:
                    result = json.loads(match[1]) if match else None
                except ValueError:
                    result = None
                if (not isinstance(result, dict) or type(result.get("exit_code")) is not int
                        or result["exit_code"] not in (0, 2) or result.get("session_id") is not None
                        or not isinstance(result.get("output"), str)):
                    previous = None
                    continue
                output = result["output"]
            yield previous, message.get("id"), output
        previous = block if message.get("role") == "assistant" and block.get("type") == "tool-call" else None


def _tool_command(call: dict[str, Any]) -> list[str]:
    value = call.get("input")
    try:
        if call.get("name") == "exec":
            match = re.fullmatch(r"text\(await tools\.exec_command\((\{[\s\S]+\})\)\);?\n?", value) if isinstance(value, str) else None
            if not match:
                return []
            value = json.loads(match[1])
        elif call.get("name") not in ("Bash", "exec_command", "functions.exec_command"):
            return []
        value = json.loads(value) if isinstance(value, str) else value
        if not isinstance(value, dict) or set(value) - {"command", "cmd", "max_output_tokens", "yield_time_ms", "timeout", "description"}:
            return []
        if ("command" in value) == ("cmd" in value):
            return []
        command = value.get("command", value.get("cmd")) if isinstance(value, dict) else None
        arguments = shlex.split(command) if isinstance(command, str) else []
        # Only canonical literal shell words. This excludes operators,
        # redirects, substitutions, comments, expansions and extra commands.
        return arguments if arguments and command == shlex.join(arguments) else []
    except (ValueError, TypeError):
        return []


def _orca_presentation_axes(observed: dict[str, Any], transcript: dict[str, Any]) -> dict[str, Any]:
    """Extract only native plugin-list fields. Orca has no startup-trust field.

    This injectable probe is not a serialized assertion interface. In particular,
    neither a live worker nor a successful tool exit proves hook approval.
    """
    evidence: dict[str, Any] = {"installation": {}, "enablement": {}, "trust": {}}
    for call, event_id, output in _tool_results(transcript):
        if _tool_command(call) != [shutil.which(observed["provider"]), "plugin", "list", "--json"]:
            continue
        evidence = {"installation": {}, "enablement": {}, "trust": {}}
        try:
            payload = json.loads(output)
        except (TypeError, ValueError):
            continue
        records = payload.get("installed") if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            continue
        records = [entry for entry in records if isinstance(entry, dict)
                   and entry.get("pluginId", entry.get("id")) == PRESENTATION_COMPONENT]
        if len(records) != 1 or not isinstance(event_id, str):
            continue
        entry = records[0]
        # A plugin-list child process does not expose the active session's
        # config/overrides or startup trust. Preserve the listing as history,
        # without promoting its enabled flag to current session authority.
        evidence["plugin_listing"] = {"source_ref": observed["source_ref"] + ":" + event_id,
                                     "source_sha256": _sha256(output.encode())}
        # Do not choose a cache version or guess a path absent from native output.
        path, version = entry.get("installPath"), entry.get("version")
        if isinstance(path, str) and Path(path).is_absolute() and isinstance(version, str):
            evidence["installation"] = {"status": "present", "version": version,
                "install_root": path, "skill_ref": str(Path(path) / "skills/i-have-adhd/SKILL.md")}
    return evidence


def _load_request_command(command: list[str], observed: dict[str, Any], request: dict[str, Any]) -> bool:
    script = str(Path(__file__).resolve().parents[1] / "grill_workspace.py")
    if len(command) < 5 or command[:3] != [sys.executable, "-B", script] or command[4] != request["scope"].get("root"):
        return False
    verb = command[3]
    if verb not in {"preflight", "init", "gauntlet-orchestration-adopt", "gauntlet-resume"}:
        return False
    fields, flags = {}, set()
    args = iter(command[5:])
    for key in args:
        if key == "--skip-backlog" and verb in {"preflight", "init"} and key not in flags:
            flags.add(key)
        elif key in {"--runtime", "--session-ref", "--work-id", "--type", "--slug", "--checkpoint"} and key not in fields:
            fields[key] = next(args, None)
        else:
            return False
    expected = {"--runtime": observed["provider"], "--session-ref": observed["source_ref"]}
    work_id = request["scope"].get("work_id")
    if verb == "preflight":
        return work_id is None and fields == expected
    if not isinstance(work_id, str):
        return False
    expected["--work-id"] = work_id
    if verb == "init":
        if fields.get("--type") not in {"feature", "fix", "hotfix"} or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", fields.get("--slug") or ""):
            return False
        expected.update({key: fields[key] for key in ("--type", "--slug")})
    if verb == "gauntlet-resume":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", fields.get("--checkpoint") or ""):
            return False
        expected["--checkpoint"] = fields["--checkpoint"]
    return fields == expected


@dataclass
class LeaderBoundary:
    """Read-only Orca session adapter. Callables are the offline injection seam.

    Session refs select a Dispatch; they contain no asserted session or style
    facts. Digests identify observed content, not cryptographic/execution proof.
    """

    session_ref: str
    root: Path
    runtime: str
    terminal_handle: str | None
    read: Callable[[list[str]], bytes]
    presentation_probe: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = _orca_presentation_axes

    def observe(self) -> dict[str, Any]:
        if not isinstance(self.session_ref, str) or not re.fullmatch(r"orca:ctx[-_][A-Za-z0-9_-]+", self.session_ref):
            _fail("LEADER-ADAPTER-UNSUPPORTED")
        dispatch_id = self.session_ref.removeprefix("orca:")
        raw = self.read(["orchestration", "worker-show", "--dispatch", dispatch_id, "--json"])
        show = _object(raw, "Orca worker-show")
        dispatch = _mapping(show.get("dispatch"), "dispatch")
        worker = _mapping(show.get("worker"), "worker")
        terminal = _mapping(show.get("terminal"), "current terminal")
        resource = _mapping(show.get("terminalResource"), "terminal resource")
        projection = _mapping(show.get("projection"), "projection")
        launch = _mapping(_mapping(worker.get("startOptions"), "startOptions").get("launch"), "launch")
        requested, effective = _mapping(launch.get("requested"), "requested"), _mapping(launch.get("effective"), "effective")
        _same("dispatch", dispatch_id, dispatch.get("id"), worker.get("dispatchId"), resource.get("ownerDispatchId"))
        handle = _same("current terminal", self.terminal_handle, terminal.get("handle"), worker.get("agentTerminalHandle"), resource.get("terminalHandle"))
        worktree = _same("worktree", terminal.get("worktreeId"), worker.get("worktreeId"), resource.get("worktreeId"))
        incarnation = _string(terminal.get("incarnationId"), "incarnation")
        process = _same("dispatch incarnation", dispatch.get("processIncarnation"), resource.get("endpointIncarnation"))
        if process != _string(terminal.get("ptyId"), "pty") + ":" + incarnation:
            _fail("LEADER-AUTHORITY-UNPROVEN")
        activity = {"ready": "active", "running": "active", "idle": "idle"}.get(_string(worker.get("state"), "worker state"))
        if (terminal.get("worktreePath") != str(self.root) or terminal.get("orphaned") is not False
                or _mapping(show.get("observation"), "observation").get("exactWorker") is not True
                or _mapping(projection.get("liveness"), "liveness").get("verdict") != "live"
                or projection["liveness"].get("source") != "agent_status"
                # Orca retains reused/pre-existing terminals independently of
                # this active Dispatch. All ownership/incarnation checks above
                # still apply; retention is neither release nor startup trust.
                or resource.get("releaseState") not in ("not_requested", "retained")
                or dispatch.get("status") not in ("dispatched", "running")
                or "capabilityRevokedAt" not in dispatch or dispatch["capabilityRevokedAt"] is not None
                or activity is None):
            _fail("LEADER-AUTHORITY-UNPROVEN")
        provider = _same("provider", self.runtime, terminal.get("agentIdentity"), effective.get("agent"),
                         _mapping(projection.get("provider"), "provider").get("id"))
        observed = {"schema": "grill-agent-observation/v1", "adapter": "orca", "provider": provider,
            "handle": handle, "incarnation": incarnation, "dispatch_incarnation": process,
            "runtime_instance": _same("runtime instance", worker.get("runtimeEpoch"), resource.get("endpointId")),
            "host": _same("host", terminal.get("executionHostId"), _mapping(dispatch.get("hostScope"), "host").get("hostId")),
            "owner_dispatch": dispatch_id, "task_id": _same("task", dispatch.get("taskId"), projection.get("taskId")),
            "worktree_id": worktree, "source_ref": self.session_ref,
            "requested_model": requested.get("model"), "requested_effort": requested.get("effort"),
            "effective_model": effective.get("model"), "effective_effort": effective.get("effort"),
            "resolved_model_id": None, "activity": activity, "close": "not_requested"}
        # Stable native fields only: timestamps/previews change on every read.
        observed["source_sha256"] = _sha256(json.dumps(observed, sort_keys=True).encode())
        return validate_observation(observed)

    def transcript(self, observed: dict[str, Any]) -> dict[str, Any]:
        raw = self.read(["orchestration", "worker-read", "--dispatch", observed["owner_dispatch"],
                         "--source", "transcript", "--limit", "1000", "--json"])
        value = _object(raw, "Orca worker-read")
        if (value.get("dispatchId") != observed["owner_dispatch"] or value.get("provider") != self.runtime
                or value.get("source") != "transcript" or value.get("sourceExact") is not True
                or value.get("contentComplete") is not True or value.get("clipping")
                or not isinstance(value.get("sourceIdentity"), str) or not value["sourceIdentity"]):
            _fail("LEADER-TRANSCRIPT-UNPROVEN")
        transcript = _mapping(value.get("transcript"), "transcript")
        if not isinstance(transcript.get("messages"), list) or transcript.get("limited") is not False:
            _fail("LEADER-TRANSCRIPT-UNPROVEN")
        return {**transcript, "sourceIdentity": value["sourceIdentity"]}


def _full_read(observed: dict[str, Any], transcript: dict[str, Any], request: dict[str, Any] | None) -> dict[str, Any] | None:
    if request is None:
        return None
    requested = False
    for call, event_id, output in _tool_results(transcript):
        command = _tool_command(call)
        # The native tool result must contain this exact core-issued request.
        if _load_request_command(command, observed, request):
            try:
                payload = json.loads(output)
            except (TypeError, ValueError):
                continue
            presentation = payload.get("presentation") if isinstance(payload, dict) else None
            requested = (isinstance(presentation, dict) and presentation.get("load_request") == request
                         and payload.get("verdict") == "BLOCKED" and payload.get("code") == "STYLE-LOAD-UNCONFIRMED")
            continue
        if not requested or command != [shutil.which("cat"), "--", request["skill_ref"]] or not isinstance(output, str) or not isinstance(event_id, str):
            continue
        raw = output.encode()
        if _sha256(raw) != request["skill_sha256"]:
            continue
        return {"evidence_kind": "full_read", "event_ref": observed["source_ref"] + ":" + event_id,
                "event_sha256": _sha256(raw), "load_request": request,
                **{key: request[key] for key in ("session_identity", "config_fingerprint", "scope", "skill_sha256", "body_sha256")}}
    return None


def project_leader_presentation(value: Any, *, policy: dict[str, Any], policy_sha256: str,
                                gwd_skill_sha256: str, runtime: str,
                                scope: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Observe through the adapter; a caller-authored projection is not a source."""
    if not isinstance(value, LeaderBoundary) or value.runtime != runtime:
        _fail("LEADER-AUTHORITY-UNPROVEN")
    observed = value.observe()
    transcript = value.transcript(observed)
    axes = value.presentation_probe(observed, transcript)
    configuration = _axis(axes.get("configuration"), states={"observed", "undetermined"}, default="undetermined")
    fingerprint = (_sha256(json.dumps({"source": transcript["sourceIdentity"], "axes": axes}, sort_keys=True).encode())
                   if configuration["state"] == "observed" else "unobserved")
    kwargs = dict(policy=policy, policy_sha256=policy_sha256, gwd_skill_sha256=gwd_skill_sha256,
        runtime=runtime, session_identity=leader_session_identity(observed), scope=scope,
        config_fingerprint=fingerprint,
        installation=axes.get("installation"), enablement=axes.get("enablement"), trust=axes.get("trust"))
    presentation = presentation_state(**kwargs)
    loading = _full_read(observed, transcript, presentation["load_request"])
    if loading:
        presentation = presentation_state(**kwargs, loading=loading)
    if value.observe() != observed:
        _fail("LEADER-AUTHORITY-UNPROVEN")
    return observed, presentation


def _identity(value: dict[str, Any]) -> tuple[Any, ...]:
    return session_identity(value)


def validate_observation(value: Any, source: tuple[bytes, ...] | None = None) -> dict[str, Any]:
    """Validate the closed normalized shape after an adapter observed it."""
    if not isinstance(value, dict):
        _fail("observation must be object")
    if set(value) != _OBSERVATION_KEYS or value.get("schema") != "grill-agent-observation/v1":
        _fail("invalid observation keys")
    _identity(value)
    if value["adapter"] != "orca" or value["provider"] not in {"codex", "claude"}:
        _fail("unknown runtime adapter or provider")
    if not isinstance(value["source_ref"], str) or not value["source_ref"]:
        _fail("invalid observation source")
    if not isinstance(value["source_sha256"], str) or not _HEX.fullmatch(value["source_sha256"]):
        _fail("invalid observation source")
    if source is not None and (not all(isinstance(raw, bytes) for raw in source) or value["source_sha256"] != _source_digest(*source)):
        _fail("observation digest mismatch")
    for key in (
        "requested_model", "requested_effort", "effective_model", "effective_effort",
        "resolved_model_id",
    ):
        if value[key] is not None and (not isinstance(value[key], str) or not value[key]):
            _fail(f"invalid {key}")
    if value["activity"] not in {"active", "idle", "exited", "unknown"}:
        _fail("invalid observation state")
    if value["close"] not in {"not_requested", "pending", "closed", "unknown", "preserved"}:
        _fail("invalid observation state")
    return value


def _launch_pair(launch: dict[str, Any], worker: dict[str, Any]) -> tuple[str, str, str, str, str]:
    launch_options = _mapping(launch.get("launch"), "launch")
    worker_options = _mapping(_mapping(worker.get("startOptions"), "worker startOptions").get("launch"), "worker launch")
    requested = _mapping(launch_options.get("requested"), "requested launch")
    effective = _mapping(launch_options.get("effective"), "effective launch")
    worker_requested = _mapping(worker_options.get("requested"), "worker requested launch")
    worker_effective = _mapping(worker_options.get("effective"), "worker effective launch")
    provider = _same("provider", effective.get("agent"), worker_effective.get("agent"))
    requested_model = _same("requested model", requested.get("model"), worker_requested.get("model"))
    requested_effort = _same("requested effort", requested.get("effort"), worker_requested.get("effort"))
    effective_model = _same("effective model", effective.get("model"), worker_effective.get("model"))
    effective_effort = _same("effective effort", effective.get("effort"), worker_effective.get("effort"))
    return requested_model, requested_effort, effective_model, effective_effort, provider


def _orca_observation(source_ref: str, launch_raw: bytes, show_raw: bytes) -> dict[str, Any]:
    """Normalize only fields that occur in correlated public Orca responses."""
    launch = _object(launch_raw, "Orca launch")
    show = _object(show_raw, "Orca worker-show")
    dispatch = _mapping(show.get("dispatch"), "dispatch")
    worker = _mapping(show.get("worker"), "worker")
    resource = _mapping(show.get("terminalResource"), "terminal resource")
    host_scope = _mapping(dispatch.get("hostScope"), "dispatch host")
    terminal = show.get("terminal")
    if terminal is not None and not isinstance(terminal, dict):
        _fail("invalid terminal")
    requested_model, requested_effort, effective_model, effective_effort, provider = _launch_pair(launch, worker)
    dispatch_id = _same("dispatch", launch.get("dispatchId"), dispatch.get("id"), worker.get("dispatchId"), resource.get("ownerDispatchId"))
    if dispatch_id not in source_ref:
        _fail("uncorrelated observation source")
    projection = _mapping(show.get("projection"), "projection")
    task_id = _same("task", launch.get("taskId"), dispatch.get("taskId"), projection.get("taskId"))
    worktree_id = _same("worktree", worker.get("worktreeId"), resource.get("worktreeId"))
    runtime_instance = _same("runtime instance", worker.get("runtimeEpoch"), resource.get("endpointId"))
    dispatch_incarnation = _string(resource.get("endpointIncarnation"), "dispatch incarnation")
    incarnation = _string(_mapping(launch.get("prompt"), "launch prompt").get("processIncarnation"), "launch process incarnation")
    handle = _same("terminal handle", worker.get("agentTerminalHandle"), resource.get("terminalHandle"))
    host = _string(host_scope.get("hostId"), "host")
    liveness = projection.get("liveness")
    if terminal is not None:
        _same("terminal handle", handle, terminal.get("handle"))
        _same("worktree", worktree_id, terminal.get("worktreeId"))
        _same("host", host, terminal.get("executionHostId"))
        _same("incarnation", incarnation, terminal.get("incarnationId"))
    projection_provider = projection.get("provider")
    if projection_provider is not None:
        _same("provider", provider, _mapping(projection_provider, "projection provider").get("id"))
    projection_host = projection.get("host")
    if projection_host is not None:
        _same("host", host, _mapping(projection_host, "projection host").get("id"))
    closed = (resource.get("releaseState") == "released" and isinstance(liveness, dict)
              and worker.get("agentWait", object()) is not None and dispatch.get("status") == "completed"
              and worker.get("stage") == "settled" and worker.get("state") in {"succeeded", "failed"}
              and liveness.get("verdict") == "exited" and liveness.get("source") == "resource_release"
              and _mapping(projection.get("resource"), "release resource").get("releaseState") == "released"
              and _mapping(projection.get("resource"), "release resource").get("ownerDispatchId") == dispatch_id)
    if terminal is None and not closed:
        _fail("current session incarnation unproven")
    close, activity = "not_requested", "unknown"
    if resource.get("releaseState") == "not_requested":
        if isinstance(liveness, dict) and liveness.get("verdict") == "exited":
            activity = "exited"
        elif isinstance(liveness, dict) and liveness.get("verdict") == "live" and liveness.get("source") == "agent_status":
            activity = {"ready": "active", "running": "active", "idle": "idle"}.get(worker.get("state"), "unknown")
    elif resource.get("releaseState") in {"release_pending", "pending"}:
        close = "pending"
    elif resource.get("releaseState") == "released":
        if closed:
            close, activity = "closed", "exited"
        else:
            close = "unknown"
    resolved_model_id = effective_model if requested_model == effective_model else None
    return validate_observation({
        "schema": "grill-agent-observation/v1", "adapter": "orca", "provider": provider,
        "handle": handle, "incarnation": incarnation, "dispatch_incarnation": dispatch_incarnation,
        "runtime_instance": runtime_instance, "host": host, "owner_dispatch": dispatch_id,
        "task_id": task_id, "worktree_id": worktree_id, "source_ref": source_ref,
        "source_sha256": _source_digest(launch_raw, show_raw), "requested_model": requested_model,
        "requested_effort": requested_effort, "effective_model": effective_model,
        "effective_effort": effective_effort, "resolved_model_id": resolved_model_id,
        "activity": activity, "close": close,
    }, (launch_raw, show_raw))


@dataclass
class RuntimeBoundary:
    """Known adapter seam. Its callables return native public response bytes."""

    adapter: str
    source_ref: str
    capabilities: set[str]
    probe: Callable[[], tuple[bytes, bytes]]
    observe: Callable[[], tuple[bytes, bytes]]
    request_close: Callable[[], bytes]
    read_after_close: Callable[[], tuple[bytes, bytes]]
    _closed: bool = field(default=False, init=False)
    # Process-local only; T005 owns durable operation recovery across boundaries.
    _close_pending: bool = field(default=False, init=False)

    def _supported(self) -> None:
        if self.adapter != "orca" or not isinstance(self.source_ref, str) or not self.source_ref or not _ORCA_CAPABILITIES.issubset(self.capabilities):
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")

    def _read(self, fn: Callable[[], tuple[bytes, bytes]]) -> dict[str, Any]:
        self._supported()
        pair = fn()
        if not isinstance(pair, tuple) or len(pair) != 2 or not all(isinstance(raw, bytes) for raw in pair):
            _fail("adapter did not return launch and worker-show bytes")
        return _orca_observation(self.source_ref, *pair)

    def verified(self, requested_model: str, requested_effort: str) -> dict[str, Any]:
        probed = self._read(self.probe)
        observation = self._read(self.observe)
        if _identity(probed) != _identity(observation):
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")
        if not isinstance(requested_model, str) or not requested_model or not isinstance(requested_effort, str) or not requested_effort or observation["effective_model"] != requested_model or observation["effective_effort"] != requested_effort or observation["resolved_model_id"] != observation["effective_model"] or observation["activity"] not in {"active", "idle"} or observation["close"] != "not_requested":
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")
        return observation

    def revalidate(self, expected: dict[str, Any]) -> dict[str, Any]:
        """Read current runtime facts before accepting a specialist return."""
        expected = validate_observation(expected)
        observed = self._read(self.observe)
        if (_identity(observed) != _identity(expected)
                or observed["effective_model"] != expected["effective_model"]
                or observed["effective_effort"] != expected["effective_effort"]
                or observed["resolved_model_id"] != expected["resolved_model_id"]
                or observed["activity"] not in {"active", "idle"}
                or observed["close"] != "not_requested"):
            _fail("SPECIALIST-CAPABILITY-UNPROVEN")
        return observed

    def close(self, expected: dict[str, Any]) -> dict[str, Any]:
        if self._closed:
            _fail("runtime close already confirmed")
        expected = validate_observation(expected)
        self._supported()
        if not self._close_pending:
            self._close_pending = True
            release = _object(self.request_close(), "Orca worker-release")
            if release.get("dispatchId") != expected["owner_dispatch"] or release.get("state") != "released" or release.get("processAction") != "closed_agent_terminal" or _mapping(release.get("archive"), "release archive").get("status") != "captured":
                _fail("runtime close unconfirmed")
        observed = self._read(self.read_after_close)
        if _identity(observed) != _identity(expected) or observed["close"] != "closed" or observed["activity"] != "exited":
            _fail("runtime close unconfirmed")
        self._closed = True
        self._close_pending = False
        return observed
