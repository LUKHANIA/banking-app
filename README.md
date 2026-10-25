# Regulatory Patching Agent (GitHub × Claude)

Watches SEC, FinCEN and Basel publications, finds the code/docs they affect in your
banking repos, and opens **draft Pull Requests** with the compliance changes.

```
Trigger (cron / manual)
  → sources.py   fetch new SEC / FinCEN (Federal Register API) + Basel (RSS)
  → analyzer.py  Claude: relevant? extract obligations, citations, effective date
  → scanner.py   compliance-map.yml paths + keyword search → affected files
  → patcher.py   Claude: minimal exact-match edits per file
  → github_pr.py branch → run tests → draft PR + labels + reviewer team + audit trail
```

## Setup
1. Copy this folder's contents into your repo root (or a dedicated "compliance-ops" repo).
2. Add secrets: `ANTHROPIC_API_KEY`; optionally `AGENT_GH_TOKEN` (GitHub App / fine-grained PAT).
   PRs opened with the default `GITHUB_TOKEN` will **not** trigger your CI workflows — use an App token so tests/CodeQL run on agent PRs.
3. Edit `compliance-map.yml` so topics point at your real paths/keywords.
4. Edit `agent/config.yaml` (allowed paths, test command, reviewer team).
5. Run the workflow manually with `dry_run = true` first.
6. Settings → Branches: require PR review + CODEOWNERS for compliance paths. Enable "Allow GitHub Actions to create pull requests".

## Banking guardrails (built in)
- Draft PRs only; never auto-merges. Branch protection + compliance sign-off checklist in every PR.
- Path allow/deny lists; `.github/`, secrets, and prod infra are off-limits.
- Exact-match edits only; ambiguous items become "Open questions for Compliance".
- Confidence threshold (0.5) before any code is touched.
- Every decision logged to `audit/agent-log.jsonl` (uploaded as artifact; consider shipping to your SIEM).
- Idempotent: one branch per regulatory document, skipped if it exists.
- Failing tests are shown prominently in the PR.

## Before production
- Have Model Risk Management classify and approve the agent (SR 11-7 / internal policy).
- Confirm your data-handling terms for sending regulatory text and source code to the LLM provider; keep PII/customer data out of the repo paths the agent can read.
- Verify feed URLs and add other sources (OCC, Fed, FINRA, EBA) in `config.yaml`.
- Add a ruleset or CODEOWNERS entry so compliance must approve `[Reg Patch]` PRs.

## Extending
- Add a doc-scanning step for `docs/compliance/` policies (already covered via `allowed_paths`).
- Open a tracking Issue per regulation with an implementation checklist.
- Add a second "reviewer" LLM pass that re-checks diffs against the citation.
