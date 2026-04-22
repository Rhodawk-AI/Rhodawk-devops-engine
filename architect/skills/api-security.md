---
name: api-security
domain: api
triggers:
  asset_types:  [rest, graphql, grpc, openapi]
  frameworks:   [fastapi, express, gin, spring, hasura, apollo, grpc-go]
tools:          [burp, ffuf, nuclei, graphql-cop, inql]
severity_focus: [P1, P2]
---

# API Security

## When to load
REST/GraphQL/gRPC services, OpenAPI specs, mobile back-ends, internal
microservices.

## OWASP API Top-10 (2023) checklist
1. **BOLA** — every object id in the URL must be checked against the caller's
   tenant.  Try sibling tenant ids, deleted ids, IDs from `/me/audit-log`.
2. **Broken Auth** — `Authorization: Bearer null`, missing `aud`/`iss`,
   refresh-token replay, token reuse across tenants.
3. **BOPLA** — properties returned beyond what the UI needs (PII).  Confirm
   with `?include=*` / GraphQL `__schema { types { fields { name } } }`.
4. **Unrestricted resource consumption** — pagination `?per_page=10000`,
   GraphQL deep nested queries (`a { a { a { a {...}}}}`), introspection abuse.
5. **BFLA** — admin-only mutations exposed to standard role.
6. **Unrestricted access to sensitive flows** — registration / password-reset
   abusable for enumeration, no rate limit.
7. **SSRF** — webhook URL, profile-image URL, file-import URL.
8. **Security misconfig** — verbose error messages, `Allow: TRACE`,
   debug toolbars, default credentials, exposed `swagger.json` / `actuator`.
9. **Improper inventory** — `/v1` deprecated but still live, staging
   subdomains exposing admin.
10. **Unsafe consumption of APIs** — outbound webhooks not validated.

## Procedure
1. Pull spec: `swagger.json`, `/openapi.yaml`, gRPC reflection (`grpcurl`).
2. Auto-generate request matrix for every endpoint × every role.
3. Diff responses across roles for the same resource id.
4. For GraphQL — run `graphql-cop` and `inql`, then attempt batch-query
   abuse and field-level introspection.
5. Use `browser-agent-mcp` only when interactive flow is needed.

## Reporting
Include the curl reproduction, response delta, CVSS vector, and a concrete
remediation (e.g. middleware policy snippet).
