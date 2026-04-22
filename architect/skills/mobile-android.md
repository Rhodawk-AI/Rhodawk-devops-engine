---
name: mobile-android
domain: mobile
triggers:
  languages:    [java, kotlin, smali]
  asset_types:  [apk, aab, android]
tools:          [apktool, jadx, frida, objection, adb, mobsf]
severity_focus: [P1, P2]
---

# Android Application Security

## When to load
APK / AAB binaries, Android-specific bug-bounty programs, mobile SDKs.

## Procedure
1. **Decompile** — `apktool d app.apk` for resources/manifest;
   `jadx -d out app.apk` for Java.
2. **Manifest review** — exported activities/services/receivers, debuggable,
   `allowBackup`, `networkSecurityConfig`, custom URL schemes (deeplinks),
   `taskAffinity` task-hijack candidates.
3. **Static** — `MobSF`, look for hard-coded keys, hardcoded URLs, weak
   crypto (`DES`, `RC4`, ECB), `SQL` strings, exported content providers.
4. **Dynamic** — install on rooted device or emulator; `objection patchapk`
   to bypass cert pinning; intercept with Burp via Frida `frida-android-pin`
   bypass.
5. **Surfaces** — exported components callable via `adb shell am start`;
   intent redirection in `onActivityResult`; deeplink → WebView URL takeover.
6. **Storage** — inspect `/data/data/<pkg>/`, shared-prefs, sqlite DBs for
   PII / tokens stored in plaintext.

## Reporting
Include adb commands, intercepted requests, root cause source line.  Provide
fix in Kotlin/Java with `intent.setPackage`, `WebSettings` hardening, secure
storage migration.
