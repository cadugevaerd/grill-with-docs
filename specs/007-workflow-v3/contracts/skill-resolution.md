# `skill-resolution/v1` Contract

Input: `step_id`, runtime, expected `registry_sha256`, raw registry bytes and an observed catalog document.

Output: one canonical resolution with `skill_id`, runtime/adapter/entrypoint, minimum and observed versions, source ref, content and manifest SHA-256, catalog identity, registry SHA-256 and `skill_resolution_sha256`.

Failure: `BLOCKED_CAPABILITY` for unavailable/unproven/invalid capability; `STALE_SKILL_RESOLUTION` for registry, catalog or digest divergence. No direct, emulated or best-effort output exists.
