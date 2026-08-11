#!/usr/bin/env bash
# Canonical source fingerprint for the verify-review-ship gates.
#
# Identifies the REVIEWED CONTENT, never the commit that recorded a gate report.
# Writing and committing verify.md changes HEAD without changing what was
# reviewed, so a HEAD-based fingerprint invalidates itself between two gates of
# the same run. Excluding the report paths from a content hash removes that
# self-reference.
#
# Usage: scripts/source-fingerprint.sh <feature-dir> [config.yml]
# Output: "<tree>-<work>-<plan>" plus one labelled line per component.

set -euo pipefail

feature_dir="${1:?usage: source-fingerprint.sh <feature-dir> [config.yml]}"
config="${2:-.specify/extensions/verify-review-ship/verify-review-ship-config.yml}"

# Exclusions come from converge.fingerprint_exclude when the config provides
# them, so the published setting and the algorithm share one effective set.
# The defaults below apply only when the key is absent.
default_excludes=(
  ".specify/reports/verify-review-ship/**"
  "specs/**/verify.md"
  "specs/**/review.md"
)

read_excludes() {
  [ -f "$config" ] || return 1
  awk '
    /^[[:space:]]*fingerprint_exclude:[[:space:]]*$/ { collecting=1; found=1; next }
    collecting && /^[[:space:]]*-[[:space:]]*/ {
      line=$0
      sub(/^[[:space:]]*-[[:space:]]*/, "", line)
      gsub(/^["'"'"']|["'"'"']$/, "", line)
      print line
      next
    }
    collecting && NF { collecting=0 }
    END { if (!found) exit 1 }
  ' "$config"
}

mapfile -t excludes < <(read_excludes || printf '%s\n' "${default_excludes[@]}")
[ ${#excludes[@]} -gt 0 ] || excludes=("${default_excludes[@]}")

pathspec=(.)
for e in "${excludes[@]}"; do
  pathspec+=(":(exclude)$e")
done

# tree: committed and staged content of the reviewed scope.
tree=$(git ls-files -s -- "${pathspec[@]}" | sha256sum | cut -d' ' -f1)

# work: uncommitted changes AND untracked files. `git diff HEAD` alone misses a
# new implementation file that was never added, which would let unreviewed
# content ship under a matching fingerprint.
work=$( { git diff HEAD -- "${pathspec[@]}"
          git ls-files -o --exclude-standard -- "${pathspec[@]}" \
            | while IFS= read -r f; do printf '%s ' "$f"; sha256sum "$f"; done
        } | sha256sum | cut -d' ' -f1 )

plan=$(sha256sum "$feature_dir/tasks.md" | cut -d' ' -f1)

printf 'tree %s\nwork %s\nplan %s\n' "$tree" "$work" "$plan"
printf 'fingerprint %s-%s-%s\n' "${tree:0:12}" "${work:0:12}" "${plan:0:12}"
