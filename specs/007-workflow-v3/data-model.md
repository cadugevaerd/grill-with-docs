# Data Model: Canonical Step Skills

`workflow-step-skills/v1` contains ordered `steps`. Each `step_id` has a required canonical skill and one resolution per runtime.

`skill-catalog/v1` is an observed runtime snapshot: `catalog_id`, byte-bound `catalog_sha256`, and native entrypoint content/manifest digests.

`workflow-trusted-catalogs/v1` maps an allowed catalog ID to its immutable digest. It is versioned data, never an invocation input that can self-authorize.

`skill-resolution/v1` binds `step_id`, runtime, adapter, entrypoint, source/version/content hashes, catalog identity and registry hash. `skill_resolution_sha256` covers its canonical body.

`skill-invocation/v1` binds a receipt to that resolution and to one project/work item/run/attempt context. It is valid only after recomputation against the shipped registry and trusted-catalog asset.
