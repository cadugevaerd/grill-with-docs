# Research: Canonical Step Skills

## Decisions

- The registry digest is SHA-256 of the literal asset bytes, not a reserialized JSON object. This prevents byte-distinct registries from sharing a claimed identity.
- Trust is anchored in `assets/workflow-trusted-catalogs.json`; callers may pass observed catalog bytes but cannot supply an in-memory trust mapping.
- Claude is the only runtime with an observed native entrypoint fixture. Hermes and Codex remain explicitly unresolved and must block.
- `ship` alone declares human authorization required. Authorization permits dispatch of the canonical skill; it never substitutes for its receipt.

## Rejected

- Documentation-based aliases or semantic equivalents: no observed native entrypoint and no immutable approval.
- A generic direct CLI action: it would bypass the resolution/invocation chain.
- Trust derived from caller-provided mappings: the caller could self-authorize altered catalog bytes.
