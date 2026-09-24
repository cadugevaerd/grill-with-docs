#!/usr/bin/env python3
"""Typed workflow decisions through TypeSafe's Jev on the OpenRouter Decisions API.

Jev answers narrow questions (``noul``/``choice``/``score``) with probabilities
instead of prose. The GWD uses it to replace the prompt-and-parse step the agent
used to spend a full LLM turn on: step risk assessment, triage route, interview
question selection, partition group count and spec coverage.

This is the core's only network call. It never downloads bytes, and it lives
behind one replaceable :class:`Transport` so no test ever touches the network.
The API key is read from the environment only, and never written, logged or
echoed into a payload. Every transport or contract failure is fail-closed
(``JevError``); a response below the kind's confidence threshold is not a
failure, it is ``decided_by: agent`` and the agent decides as before.

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


def build_questions(spec: dict[str, Any], items: list[str]) -> dict[str, Any]:
    questions = dict(spec["questions"])
    template = spec.get("per_item")
    for item in items if template else ():
        questions[item_key(template["prefix"], item)] = {
            "type": template["type"],
            "instructions": template["instructions"].format(item=item),
            "criteria": {k: v.format(item=item) for k, v in template["criteria"].items()},
        }
    return questions


def requirements(spec_text: str) -> list[str]:
    """FR-/SC- ids in first-seen order; the spec-coverage items."""
    return list(dict.fromkeys(REQUIREMENT_RE.findall(spec_text)))


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


def interpret(kind: str, questions: dict[str, Any], response: Any, threshold: float,
              items: list[str], prefix: str = "") -> dict[str, Any]:
    if not isinstance(response, dict) or not isinstance(response.get("answers"), dict):
        raise JevError("JEV-RESPONSE-INVALID", "answers missing")
    values: dict[str, Any] = {}
    confidence: dict[str, float] = {}
    raw: dict[str, float] = {}
    for key, question in questions.items():
        answer = response["answers"].get(key)
        values[key], confidence[key] = read_answer(question, answer)
        if question["type"] == "noul":
            raw[key] = float(answer["noul"])
    confident = all(c >= threshold for c in confidence.values())
    decision: dict[str, Any] = {
        "kind": kind,
        "model": response.get("model"),
        "decided_by": "jev" if confident else "agent",
        "threshold": threshold,
        "confidence": confidence,
        "result": None,
    }
    if not confident:
        # Below threshold the probabilities are a hint, never an answer.
        decision["hint"] = values
        return decision
    by_item = {item: values[item_key(prefix, item)] for item in items}
    if kind == "step-assessment":
        decision["result"] = {"new_how": values["new_how"], "risks": [r for r in items if by_item[r]]}
    elif kind == "triage":
        decision["result"] = {"route": values["route"], "severity": values["severity"]}
    elif kind == "partition-groups":
        decision["result"] = {"groups": int(values["groups"])}
    elif kind == "dq-batch":
        material = sorted((i for i in items if by_item[i]), key=lambda i: -raw[item_key(prefix, i)])
        decision["result"] = {"selected": material[:DQ_BATCH]}
    elif kind == "spec-coverage":
        uncovered = [i for i in items if not by_item[i]]
        decision["result"] = {"uncovered": uncovered, "verdict": "NO-GO" if uncovered else "COVERED"}
    return decision


def decide(kind: str, state: dict[str, Any], items: list[str], transport: Transport,
           catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    catalog = catalog or load_catalog()
    spec = catalog["kinds"].get(kind)
    if spec is None:
        raise JevError("JEV-KIND-UNKNOWN", kind)
    if len(json.dumps(state, ensure_ascii=False)) > MAX_STATE_CHARS:
        raise JevError("JEV-STATE-TOO-LARGE", f"> {MAX_STATE_CHARS} chars")
    questions = build_questions(spec, items)
    if not questions:
        raise JevError("JEV-NO-QUESTIONS", kind)
    response = transport.post(catalog["endpoint"], {
        "model": catalog["model"], "state": state, "questions": questions})
    prefix = (spec.get("per_item") or {}).get("prefix", "")
    return interpret(kind, questions, response, float(spec["threshold"]), items, prefix)
