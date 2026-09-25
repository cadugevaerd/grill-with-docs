#!/usr/bin/env python3
"""Typed workflow decisions through TypeSafe's Jev on the OpenRouter Decisions API.

Jev answers narrow questions (``noul``/``choice``/``score``) with probabilities
instead of prose. The GWD uses it to replace the prompt-and-parse step the agent
used to spend a full LLM turn on: step risk assessment, triage, interview
bookkeeping, finding severity, learning routing and a handful of cross-checks.

This is the core's only network call. It never downloads bytes, and it lives
behind one replaceable :class:`Transport` so no test ever touches the network.
The API key is read from the environment only, and never written, logged or
echoed into a payload. Every transport or contract failure is fail-closed
(``JevError``); an answer below its confidence threshold is not a failure:
confident questions land in ``decided``, the agent answers only the ``pending``
ones, and ``decided_by`` is ``jev``, ``partial`` or ``agent``.

Two guards keep repository text (which may carry injected instructions) from
loosening a gate: a question may declare ``decide_only`` -- Jev may settle it
only with one of those values (e.g. VIOLATION, never PASS) -- and a few kinds
compare against the agent's own proposal and may only harden it.

Pure except for :class:`Transport`: callers pass state already read through
``grill_workspace.safe_read_regular_fd``.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

KEY_ENV = "OPENROUTER_API_KEY"
CATALOG = Path(__file__).resolve().parents[2] / "assets/jev-questions.json"
CATALOG_SCHEMA = "grill-jev-questions/v1"
TIMEOUT = 10
# ~22k tokens of the 32k window, leaving room for the questions themselves.
MAX_STATE_CHARS = 90_000
DQ_BATCH = 3
REQUIREMENT_RE = re.compile(r"\b(?:FR|SC)-\d{3}\b")
HEADING_RE = re.compile(r"^#{2,3} +(.+?) *$", re.M)
SEVERITY_ORDER = ("low", "medium", "high", "critical")
# Keys the catalog uses for itself; never sent to the API.
LOCAL_KEYS = {"decide_only"}
NS = "__"


class JevError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def require_key(environ: dict[str, str] | None = None) -> None:
    """Refuse to run the workflow without an OpenRouter key; checks presence only."""
    if not (os.environ if environ is None else environ).get(KEY_ENV, "").strip():
        raise JevError("OPENROUTER-KEY-REQUIRED", KEY_ENV)


class Transport:
    """The one side effect of this module, replaceable in tests."""

    def __init__(self, environ: dict[str, str] | None = None,
                 opener: Callable[..., Any] = urllib.request.urlopen) -> None:
        self.environ = os.environ if environ is None else environ
        self.opener = opener

    def post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        require_key(self.environ)
        request = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {self.environ[KEY_ENV].strip()}",
                     "Content-Type": "application/json"},
        )
        try:
            with self.opener(request, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            code = {401: "OPENROUTER-KEY-INVALID", 402: "OPENROUTER-CREDIT-EXHAUSTED"}.get(
                error.code, "JEV-UNAVAILABLE")
            raise JevError(code, f"HTTP {error.code}") from error
        except (OSError, ValueError) as error:
            # URLError and TimeoutError are OSErrors; malformed JSON is a ValueError.
            raise JevError("JEV-UNAVAILABLE", type(error).__name__) from error


def load_catalog(path: Path = CATALOG) -> dict[str, Any]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or catalog.get("schema") != CATALOG_SCHEMA:
        raise JevError("JEV-CATALOG-INVALID", str(path))
    return catalog


def item_key(prefix: str, item: str) -> str:
    return prefix + re.sub(r"[^A-Za-z0-9]", "_", item).lower()


def _fill(value: Any, item: str) -> Any:
    if isinstance(value, str):
        return value.replace("{item}", item)
    if isinstance(value, list):
        return [_fill(v, item) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v, item) for k, v in value.items()}
    return value


def build_questions(spec: dict[str, Any], items: list[str]) -> dict[str, Any]:
    """Catalog questions plus one per item; may still carry LOCAL_KEYS."""
    questions = dict(spec["questions"])
    template = spec.get("per_item")
    for item in items if template else ():
        questions[item_key(template["prefix"], item)] = {
            k: _fill(v, item) for k, v in template.items() if k != "prefix"}
    return questions


def wire(question: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in question.items() if k not in LOCAL_KEYS}


def requirements(spec_text: str) -> dict[str, str]:
    """FR-/SC- id -> the first line naming it, in first-seen order."""
    found: dict[str, str] = {}
    for line in spec_text.splitlines():
        for rid in REQUIREMENT_RE.findall(line):
            found.setdefault(rid, line.strip())
    return found


def clauses(constitution: str) -> dict[str, str]:
    """H2/H3 heading -> its body, the constitution-check items."""
    marks = list(HEADING_RE.finditer(constitution))
    return {m.group(1): constitution[m.end():(marks[i + 1].start() if i + 1 < len(marks) else None)].strip()
            for i, m in enumerate(marks)}


def _probability(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise JevError("JEV-RESPONSE-INVALID", "probability out of range")
    return float(value)


def read_answer(question: dict[str, Any], answer: Any) -> tuple[Any, float]:
    """Return (value, confidence) for one answer, refusing any shape we did not ask for."""
    if not isinstance(answer, dict) or answer.get("type") != question["type"]:
        raise JevError("JEV-RESPONSE-INVALID", "answer type mismatch")
    if question["type"] == "noul":
        p = _probability(answer.get("noul"))
        return p >= 0.5, max(p, 1 - p)
    confidence = _probability(answer.get("confidence"))
    if question["type"] == "choice":
        if answer.get("choice") not in question["criteria"]:
            raise JevError("JEV-RESPONSE-INVALID", "choice outside criteria")
        return answer["choice"], confidence
    score = answer.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise JevError("JEV-RESPONSE-INVALID", "score not numeric")
    return score, confidence


def threshold_for(spec: dict[str, Any], question: dict[str, Any]) -> float:
    """Per-type override first: Jev's noul and choice confidences drift in opposite directions."""
    return float(spec.get("thresholds", {}).get(question["type"], spec["threshold"]))


def interpret(kind: str, questions: dict[str, Any], response: Any, spec: dict[str, Any] | float,
              items: list[str], prefix: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(spec, dict):
        spec = {"threshold": spec}
    if not isinstance(response, dict) or not isinstance(response.get("answers"), dict):
        raise JevError("JEV-RESPONSE-INVALID", "answers missing")
    values: dict[str, Any] = {}
    confidence: dict[str, float] = {}
    raw: dict[str, float] = {}
    decided: dict[str, Any] = {}
    for key, question in questions.items():
        answer = response["answers"].get(key)
        values[key], confidence[key] = read_answer(question, answer)
        if question["type"] == "noul":
            raw[key] = float(answer["noul"])
        allowed = question.get("decide_only")
        # Each question stands alone; below threshold, or outside decide_only,
        # a value is a hint for the agent, never an answer.
        if confidence[key] >= threshold_for(spec, question) and (allowed is None or values[key] in allowed):
            decided[key] = values[key]
    _harden(kind, decided, items, prefix, context or {})
    pending = [k for k in values if k not in decided]
    return {
        "kind": kind,
        "model": response.get("model"),
        "decided_by": "agent" if not decided else "partial" if pending else "jev",
        "confidence": confidence,
        "decided": decided,
        "pending": pending,
        "hint": {k: values[k] for k in pending},
        "result": _result(kind, decided, pending, items, prefix, raw, context or {}),
    }


def _harden(kind: str, decided: dict[str, Any], items: list[str], prefix: str, context: dict[str, Any]) -> None:
    """Drop decisions that would loosen what the agent proposed."""
    if kind == "finding-severity":
        findings = context.get("findings", {})
        for item in items:
            key = item_key(prefix, item)
            proposed = findings.get(item, {}).get("proposed") if isinstance(findings.get(item), dict) else None
            if key in decided and proposed in SEVERITY_ORDER and \
                    SEVERITY_ORDER.index(decided[key]) < SEVERITY_ORDER.index(proposed):
                del decided[key]


def _result(kind: str, decided: dict[str, Any], pending: list[str], items: list[str], prefix: str,
            raw: dict[str, float], context: dict[str, Any]) -> dict[str, Any] | None:
    by_item = {i: decided[item_key(prefix, i)] for i in items if item_key(prefix, i) in decided}
    # Hardening kinds report what Jev confidently found even while other
    # questions are still pending; everything else waits for a full answer.
    if kind == "spec-coverage":
        uncovered = [i for i in items if by_item.get(i) is False]
        if uncovered:
            return {"uncovered": uncovered, "verdict": "NO-GO"}
        return None if pending else {"uncovered": [], "verdict": "COVERED"}
    if kind == "constitution-check":
        violations = [i for i in items if by_item.get(i) == "VIOLATION"]
        return {"violations": violations, "verdict": "NO-GO"} if violations else None
    if kind == "diff-hygiene":
        flagged = [i for i in items if by_item.get(i) is True]
        return {"flagged": flagged} if flagged else None
    if kind == "human-or-author":
        to_human = [i for i in items if by_item.get(i) == "human"]
        return {"to_human": to_human} if to_human else None
    if kind == "delivery-classification":
        proposed = context.get("proposed", {})
        disagree = [k for k, v in decided.items() if k in proposed and proposed[k] != v]
        if disagree:
            return {"verdict": "ASK-HUMAN", "disagree": disagree}
        return None if pending else {"verdict": "CONFIRMED"}
    if kind == "finding-severity":
        return {"severities": by_item} if by_item else None
    if pending:
        return None
    if kind == "step-assessment":
        return {"new_how": decided["new_how"], "risks": [r for r in items if by_item[r]]}
    if kind == "partition-groups":
        return {"groups": int(decided["groups"])}
    if kind == "dq-batch":
        material = sorted((i for i in items if by_item[i]), key=lambda i: -raw[item_key(prefix, i)])
        return {"selected": material[:DQ_BATCH]}
    if kind == "round-record":
        artifacts = [i for i in items if by_item[i]]
        return {**{k: v for k, v in decided.items() if not k.startswith(prefix)}, "artifacts": artifacts}
    return dict(decided)


def decide_many(kinds: list[str], state: dict[str, Any], items: dict[str, list[str]], transport: Transport,
                catalog: dict[str, Any] | None = None, session_id: str | None = None) -> dict[str, Any]:
    """Answer several kinds in one request: Jev runs every question in parallel."""
    catalog = catalog or load_catalog()
    if len(json.dumps(state, ensure_ascii=False)) > MAX_STATE_CHARS:
        raise JevError("JEV-STATE-TOO-LARGE", f"> {MAX_STATE_CHARS} chars")
    plan: dict[str, tuple[dict[str, Any], dict[str, Any], list[str]]] = {}
    body_questions: dict[str, Any] = {}
    for kind in kinds:
        spec = catalog["kinds"].get(kind)
        if spec is None:
            raise JevError("JEV-KIND-UNKNOWN", kind)
        kind_items = items.get(kind) or list(spec.get("items", []))
        questions = build_questions(spec, kind_items)
        if not questions:
            raise JevError("JEV-NO-QUESTIONS", kind)
        plan[kind] = (spec, questions, kind_items)
        for key, question in questions.items():
            body_questions[kind.replace("-", "_") + NS + key] = wire(question)
    body: dict[str, Any] = {"model": catalog["model"], "state": state, "questions": body_questions,
                            "trace": {"trace_name": "gwd-decide", "span_name": ",".join(kinds)}}
    if session_id:
        body["session_id"] = session_id
    response = transport.post(catalog["endpoint"], body)
    answers = response.get("answers") if isinstance(response, dict) else None
    if not isinstance(answers, dict):
        raise JevError("JEV-RESPONSE-INVALID", "answers missing")
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    decisions = {}
    for kind, (spec, questions, kind_items) in plan.items():
        ns = kind.replace("-", "_") + NS
        scoped = {**response, "answers": {k[len(ns):]: v for k, v in answers.items() if k.startswith(ns)}}
        prefix = (spec.get("per_item") or {}).get("prefix", "")
        decisions[kind] = interpret(kind, questions, scoped, spec, kind_items, prefix, context)
    return decisions


def decide(kind: str, state: dict[str, Any], items: list[str], transport: Transport,
           catalog: dict[str, Any] | None = None, session_id: str | None = None) -> dict[str, Any]:
    return decide_many([kind], state, {kind: items}, transport, catalog, session_id)[kind]
