---
name: oauth2-jwt-attacks
domain: web
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# oauth2-jwt-attacks

OAuth2/OIDC: PKCE downgrade, state CSRF, redirect_uri shenanigans (open redirect/path normalisation), token leakage via Referer, refresh-token theft, JWKS rotation gaps. JWT: alg:none, key confusion (RS256→HS256), weak HMAC, kid path traversal.

## Detection checklist
- enumerate exposure
- match canonical sinks
- confirm reproducibility
- map to CWE / OWASP / CVSS

## Exploitation primitives
- reproduce in lab
- minimise the PoC
- assess blast radius

## Reporting fingerprint
- include affected version range
- include suggested fix snippet
- include CVSS 3.1 vector
