<!-- grill-task-files:v1 -->

# Tasks: <feature>

## Phase 1: <phase name>

- [ ] T001 <task description>
  Files: ["path/to/file", "specs/<feature>/implement/T001.tasks.json"]
  Result: "specs/<feature>/implement/T001.tasks.json"

## Phase 2: <phase name>

- [ ] T002 <read-only task description>
  Files: []

## Authoring rules

- Declare `Files:` immediately after every checklist task as a one-line JSON array of strings.
- A dispatchable task with writes declares exactly one `Result:` immediately after `Files:`; its path is `specs/<feature>/implement/<task_id>.tasks.json` and is also present in `Files:`.
- A read-only task declares `Files: []` and no `Result:`. It creates no worker grant or fallback scope.
- A task with leader-reserved evidence is deferred to the leader, including any product paths in its `Files:` list, and needs no `Result:`; do not invent a worker result for it.
- Keep every task in its declared numeric phase. `Files` conflicts are grouped within that phase; phases remain barriers.
- Results and phase-ordered deferred/read-only handling apply only after the candidate adopts `task-files/v1`; historical tasks retain their sealed protocol.
