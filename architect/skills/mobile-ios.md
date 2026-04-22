---
name: mobile-ios
domain: mobile
triggers:
  languages:    [swift, objective-c]
  asset_types:  [ipa, ios]
tools:          [class-dump, frida, objection, otool, hopper, cycript]
severity_focus: [P1, P2]
---

# iOS Application Security

## When to load
IPA binaries, iOS-specific bug-bounty programs, SDKs that ship for iOS.

## Procedure
1. **Decrypt** — pull decrypted IPA via `frida-ios-dump` from a jailbroken
   device.
2. **Static** — `otool -L`, `class-dump`, search for embedded API keys,
   AWS creds, Firebase configs, custom URL schemes, ATS exceptions in
   `Info.plist`.
3. **Pinning bypass** — `objection -g <bundle> explore --startup-command
   'ios sslpinning disable'`.
4. **Dynamic** — `frida-trace -i 'NSURLConnection*' -i 'NSURLRequest*'` to
   audit network paths; intercept with Burp.
5. **Storage** — Keychain dump (`Keychain-Dumper`), NSUserDefaults plist,
   Core Data SQLite — flag PII / credentials at rest.
6. **Inter-process** — exported URL schemes, Universal Links, App Groups
   shared containers, app extensions.

## Reporting
Provide bundle id, exploit primitive, jailbroken-device-only caveats, and a
suggested patch (Keychain `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`,
ATS, transparent SSL pinning with TrustKit).
