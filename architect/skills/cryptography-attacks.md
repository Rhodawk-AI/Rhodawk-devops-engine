---
name: cryptography-attacks
domain: crypto
triggers:
  asset_types:  [tls, jwt, jwe, kdf, signature, vpn]
  frameworks:   [openssl, libsodium, jwt, paseto]
tools:          [jwt_tool, sslscan, testssl, pycryptodome]
severity_focus: [P1, P2]
---

# Cryptography Attacks

## When to load
Anything signing, encrypting, or authenticating data — JWTs, sessions, JWE,
TLS, custom signatures, license-key checks, cookies.

## Common findings
* **JWT alg confusion** — `HS256` token forged using server's RSA public key.
* **JWT `alg=none`** — accepted by older libraries.
* **JWT key-injection** — `kid: "../../etc/passwd"` or SQL-style id.
* **Padding oracle** — CBC mode without authenticated encryption (POODLE,
  Vaudenay).
* **Length-extension** — MD5/SHA1 used as a MAC instead of HMAC.
* **Timing oracle** — string `==` for comparing HMACs / tokens.
* **Weak randomness** — `Math.random`, `mt19937`, `time()` seed for tokens.
* **Static IV / nonce reuse** — AES-GCM forgery.
* **PKCS#1 v1.5 oracle** — Bleichenbacher / ROBOT.
* **Hardcoded key / secret in repo** — search with `trufflehog-secrets`.
* **Signature stripping** — `Content-Type: text/plain` SAML, JWT `none`.

## Procedure
1. Identify every token / cookie that is server-issued and parsed.  For each:
   inspect header, replay across users, swap algorithm, fuzz fields.
2. Run `testssl.sh` against every TLS endpoint; flag `RC4`, `3DES`, `EXPORT`,
   `CBC` without `Encrypt-then-MAC`, no FS, weak DH params.
3. For custom signature schemes — test bit-flips, prepend/append, length-
   extension.
4. For password reset / invite tokens — measure entropy; predict if seeded
   from `time()` or sequential id.

## Reporting
Provide a concrete forged token / decrypted blob and the affected endpoint.
Recommend modern primitives (AES-GCM-SIV, Ed25519, Argon2id, PASETO).
