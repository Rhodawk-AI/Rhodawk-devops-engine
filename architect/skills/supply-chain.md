---
name: supply-chain
domain: supply-chain
triggers:
  languages:    [python, javascript, go, rust, ruby, java]
  asset_types:  [package, npm, pypi, dockerhub, ci]
tools:          [pip-audit, npm-audit, govulncheck, semgrep, syft, grype, sigstore]
severity_focus: [P1, P2]
---

# Supply-Chain Security

## When to load
Any project shipping or consuming third-party packages, container images, or
build artefacts.

## Findings to hunt
* **Known vulnerable dep** — pip-audit / npm audit / govulncheck output that
  the project has not yet fixed.
* **Typosquatting** — Levenshtein distance ≤ 2 against any popular package
  name (`crossenv` vs `cross-env`).
* **Dependency confusion** — internal package names also published on the
  public index.
* **Unsigned release artefacts** — no Sigstore / cosign signature; Docker
  image not pinned by digest.
* **Compromised maintainer** — recent maintainer change + new release with
  obfuscated code.
* **Build-script execution** — `setup.py` / `package.json` postinstall that
  pulls remote code or contacts unknown C2.
* **CI poisoning** — workflow uses `pull_request_target` and checks out the
  PR head with secrets exposed.

## Procedure
1. Generate SBOM with `syft <repo>`; scan with `grype`.
2. Diff package set against the previous release; flag any net-new top-level
   dep added in the last 30 days.
3. Run semgrep `r/supply-chain` ruleset across CI YAML.
4. For NPM: `npm pack <name>` → inspect `postinstall` and any binary blobs.
5. For Docker: pin every base image by sha256; never `:latest`.

## Reporting
Cite the vulnerable version, fixed version, CVE (if any), and downstream
blast radius.
