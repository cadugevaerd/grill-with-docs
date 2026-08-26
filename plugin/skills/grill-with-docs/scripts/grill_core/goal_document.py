#!/usr/bin/env python3
"""SSOT for the ``goal.md`` document contract (stdlib only, no disk I/O at import).

Frozen literal, not derived from anywhere
------------------------------------------
``ESSENTIAL`` is a **frozen literal**. It is never computed from
``assets/GOAL.template.md`` -- deriving it from the template's own headings
would make a mutilated template validate itself, since the validator would
then only be confirming the template equals itself, which is always true.
It is never derived from another version's tuple either -- the same doctrine
``grill_core/workflow_versions.py`` already states for ``SEQUENCE_V3`` /
``SEQUENCE_V4``: a typo in a rename map would silently rewrite the contract
instead of failing a test. And it is declared exactly once, in this module --
the materialiser, the validator and any future consumer import it from here,
never redeclare it (FR-009, FR-010).

Adding an item to ``ESSENTIAL`` is a contract change, not a patch: every
``goal.md`` already materialised in a consumer project would diverge at once,
with no diff and no migration path. That is why a contract change is a new
marker version born **alongside** the old one -- ``v2`` next to ``v1``, each
with its own tuple by extension -- never an edit of the tuple an existing
version already shipped.
"""
from __future__ import annotations

import re
from pathlib import Path

VERSION = "v1"
MARKER = "grill-with-docs-goal:v1"
HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[2] / "assets/GOAL.template.md"

#: Substrings whose presence defines conformance (contracts/goal-document.md).
#: Presence, and only presence: order between items is not enforced and
#: additional content is not forbidden (FR-014). Copied verbatim from the
#: contract -- never invented, never paraphrased.
ESSENTIAL = (
    "## Contrato de parada",
    "GOAL-HOLD:",
    "## Templates de objetivo",
    "### Template A — trilha pré-ciclo",
    "### Template B — trilha ciclo v4",
    "## Trilha pré-ciclo",
    "## Trilha ciclo v4",
    "PLAN_ONLY_STOP",
    "## Cláusula residual",
    "## Delegação",
    "## Orientação",
)


def compatible(text: str) -> bool:
    return text.strip() != "" and all(item in text for item in ESSENTIAL)


def managed_version(text: str) -> str | None:
    """The marker version declared on the first line, or ``None``.

    Matched only against ``text``'s first line (FR-011): a marker loose in
    the middle of the document must not identify it as managed -- otherwise a
    human document that merely quotes the marker in prose would start being
    judged by the contract, and a managed document with its first line
    stripped would keep being accepted.
    """
    first_line = text.split("\n", 1)[0]
    match = re.search(r"grill-with-docs-goal:(v\d+)", first_line)
    return match.group(1) if match else None
