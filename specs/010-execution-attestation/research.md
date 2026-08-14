# Research: Runtime Attestation Boundary

**Date**: 2026-08-14
**Question**: can the observed Claude Code or Codex runtime supply a verifier-backed receipt that proves one canonical skill invocation?

## Observed capability

| Runtime | Observed output | Why it is insufficient as a receipt verifier |
|---|---|---|
| Claude Code 2.1.229 | `--output-format stream-json` and `--include-hook-events`; hooks receive event JSON and can call command, HTTP, or MCP handlers. | Events and local hook output are audit material, not a documented signature, signer identity, public trust anchor, or replay-proof receipt format. |
| Codex CLI 0.147.0 | Official OpenTelemetry export for prompts, tool approvals/results, MCP usage, and network policy events. | No configured collector exists locally and the documented export is telemetry, not a signed per-skill receipt verifier. |

Evidence: [Claude Code CLI reference](https://code.claude.com/docs/en/cli-usage), [Claude Code hooks reference](https://code.claude.com/docs/en/hooks), [OpenAI Codex telemetry](https://openai.com/index/running-codex-safely/). Local checks found no configured Claude gateway or Codex OTLP exporter.

## Decision

The product trust model is cooperative coordination, not defense against a malicious executor. Stream JSON, hooks, local transcripts and hashes are accepted as structural evidence only when the complete chain is current and correlated. They are not represented as cryptographic provenance.

## Future hardening

If hostile-executor resistance becomes a requirement, the verifier must be external to the worktree and supply all of:

1. a versioned verifier identity and public trust anchor;
2. a signed receipt bound to runtime session/invocation, canonical `skill_id`, `project_id`, `work_item_id`, `run_id`, step, registry hash and terminal result;
3. a nonce or monotonic identifier with replay semantics;
4. a verification endpoint or offline verifier whose result is independently recomputable by `grill_workspace.py`.

This is not a blocker for the current cooperative workflow.
