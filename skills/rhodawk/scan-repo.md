# scan-repo

**Summary:** Scan a repository

Trigger an OSSGuardian campaign on the supplied repo URL or org/name. Replies with mode (attack/fix) and finding count.

## Trigger phrases
- (see openclaw_gateway intent registry for the regex)

## Output contract
- Telegram-safe text <= 4000 chars
- include the intent name
