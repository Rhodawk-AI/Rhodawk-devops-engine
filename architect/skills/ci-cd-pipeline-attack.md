---
name: ci-cd-pipeline-attack
domain: supply-chain
triggers:
  languages:    [yaml, bash, python, javascript, dockerfile, hcl]
  frameworks:   [github-actions, gitlab-ci, jenkins, circleci, drone, argocd, tekton, buildkite]
  asset_types:  [pipeline, ci, cd, container, registry]
tools:          [trufflehog, gitleaks, checkov, kics, tfsec, actionlint, semgrep]
severity_focus: [P1, P2]
---

# CI / CD Pipeline Attack

## When to load
Any `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`,
`buildkite/*.yml`, Tekton/Argo manifests, or `Dockerfile` reachable from a
public-facing branch.

## High-impact bug classes
1. **Script injection in workflow inputs** —
   `${{ github.event.issue.title }}`, `pull_request_target`, comment body,
   branch name, fork PR title flowing into `run:` blocks. Pays
   $5K–$30K in mature programs.
2. **Privileged `pull_request_target`** — runs in base repo context with
   secret access; if it checks out the PR head and runs scripts → full
   token exfil.
3. **Self-hosted runner takeover** — non-ephemeral runner reused across PRs
   from forks; persistent backdoor via writable workspace.
4. **OIDC mis-config** — token claims (`sub`) pattern too loose
   (`repo:org/*`); attacker forks → mints AWS / GCP credentials.
5. **Cache poisoning** — pollute `actions/cache` from one workflow, harvest
   from a privileged one.
6. **Tag confusion in `uses:`** — `actions/checkout@v4` vs
   `actions/checkout@<commit-sha>`. Mutable tag = supply-chain RCE.
7. **Build-time secret leak** — `--build-arg` shows up in `docker history`,
   `set -x` in build script logs, `process.env` printed by `npm postinstall`.
8. **Artefact poisoning** — write to release, NPM, PyPI, container registry
   with attacker-controlled bytes; consumer pulls and runs.
9. **Branch-protection bypass** — admin override, required-checks not
   enforced on legacy branches, `gh pr merge --admin`.
10. **GitOps reconcile** — Argo / Flux pulling from a repo where attacker
    can open a PR that gets auto-applied to production.

## Recon checklist
- `gh api repos/<o/r>/actions/secrets --paginate` (will be 403 without
  token; check what's listed publicly via job logs instead).
- Scan logs for token prefixes (`ghs_`, `ghp_`, `ghu_`, `glpat-`).
- `gitleaks detect --source .` and `trufflehog git --branch all`.
- `actionlint -shellcheck= .github/workflows/*.yml`.
- Check for `permissions: write-all` (default → least privilege violation).

## Reporting
Always include the full token-exfil PoC as a private fork with the
workflow change committed; redact the actual stolen secret in the report.
Cite STRIDE-T (Tampering) and CWE-250 (Execution with Unnecessary
Privileges).
