---
name: cryptographic-implementation
domain: crypto
triggers:
  languages:    [c, cpp, rust, go, python, java]
  frameworks:   [openssl, boringssl, libsodium, mbedtls, wolfssl, ring, golang-crypto, bouncycastle]
  asset_types:  [tls, jwt, oauth, saml, jose, signing, kdf]
tools:          [tlsfuzzer, wycheproof, cryptosense, openssl-bench]
severity_focus: [P1, P2]
---

# Cryptographic Implementation Bugs

## When to load
Any TLS stack, JWT/JOSE library, signing service, KDF / PRNG, password
hashing, encrypted storage, or custom protocol crypto.

## Patterns that have produced real CVEs
1. **Nonce reuse** — AES-GCM same key + same nonce twice → key recovery.
   Look for: random nonces from weak RNG, counter resets on restart, nonce
   stored in field too small (e.g. 32-bit).
2. **Padding oracles** — CBC + MAC-then-encrypt, distinguishable error
   responses (HTTP 400 vs 403, timing). Bleichenbacher-style on RSA-PKCS1.
3. **Timing side-channels** — `strcmp`/`memcmp` on MAC verification,
   variable-time scalar multiplication, branch on secret bit.
4. **Algorithm confusion** — JWT `alg=none`, `alg=HS256` with RSA public
   key as HMAC secret, SAML signature wrap, JWS `crit` ignored.
5. **Curve confusion** — point not on curve check missing (invalid-curve
   attack), small-subgroup attack on DH.
6. **PRNG predictability** — `Math.random()` for tokens, `time(NULL)` seed,
   `/dev/urandom` not used inside container, Java `Random` not
   `SecureRandom`.
7. **Key-derivation gaps** — single-iteration PBKDF2, no salt, password
   used directly as AES key, missing HKDF info parameter binding.
8. **Signature malleability** — ECDSA low-s not enforced, DER vs raw
   signature confusion, ed25519 batch verification accepting non-canonical
   encodings.
9. **TLS configuration** — SSLv3 / TLS1.0 enabled, RSA key exchange
   (no PFS), weak DH primes (export-grade), client-cert auth without
   chain validation.
10. **Replay** — missing nonce / timestamp on signed messages, no `aud`
    check on JWT, no `iat`/`exp` enforcement.

## Test harness
Always run **Project Wycheproof** test vectors against any new crypto
binding. They cover years of accumulated vendor mistakes. `tlsfuzzer`
against any TLS endpoint; expect ≥ 3 bugs in non-major stacks.

## Cost-of-bug heuristic
- TLS lib bug = millions of devices = P1, vendor pays high.
- App-level JWT confusion = single product, but immediate account
  takeover = P1.
- Padding oracle behind auth = P2 unless full plaintext recovery is
  practical → P1.

## Reporting
Show the *math*. "AES-GCM nonce reuse" alone is rejected; include the
two ciphertexts, the recovered key-stream XOR, and a script that decrypts
a third message of the reviewer's choice.
