"""
Parseltongue — input perturbation engine (G0DM0D3-inspired).

Used to red-team LLM endpoints, content-filter classifiers, and any text
decision boundary.  Detects trigger tokens and applies one or more
obfuscation techniques across three intensity tiers.

Pure-Python, no dependencies, deterministic.

Public API:
    perturb(text, *, technique=None, intensity="medium") -> str
    perturb_all(text, *, intensity="medium") -> dict[str, str]
    DEFAULT_TRIGGERS  — 33 default trigger words (red-team probes).
"""

from __future__ import annotations

import random
import re
from typing import Iterable

# 33 default triggers — common refusal / filter triggers.
DEFAULT_TRIGGERS: list[str] = [
    # Tier light (11)
    "password", "exploit", "vulnerability", "bypass", "inject",
    "shellcode", "payload", "malware", "ransomware", "backdoor", "rootkit",
    # Tier standard (+11 = 22)
    "phishing", "credential", "api key", "private key", "ssh key",
    "session token", "csrf", "ssrf", "xss", "rce", "lfi",
    # Tier heavy (+11 = 33)
    "sql injection", "command injection", "deserialization", "prototype pollution",
    "jailbreak", "prompt injection", "system prompt", "developer message",
    "tool call", "function call", "egress", "exfiltrate",
]

TIER_SIZE = {"light": 11, "medium": 22, "heavy": 33}

# ── Technique 1: leetspeak ─────────────────────────────────────────────────
_LEET = str.maketrans({
    "a": "4", "A": "4", "e": "3", "E": "3",
    "i": "1", "I": "1", "o": "0", "O": "0",
    "s": "5", "S": "5", "t": "7", "T": "7",
    "g": "9", "G": "9", "b": "8", "B": "8",
})


def _leet(s: str) -> str:
    return s.translate(_LEET)


# ── Technique 2: bubble (enclosed alphanumerics) ───────────────────────────
def _bubble(s: str) -> str:
    out = []
    for ch in s:
        cp = ord(ch)
        if "a" <= ch <= "z":
            out.append(chr(0x24D0 + (cp - ord("a"))))
        elif "A" <= ch <= "Z":
            out.append(chr(0x24B6 + (cp - ord("A"))))
        elif "0" <= ch <= "9":
            out.append(chr(0x2460 + (cp - ord("0"))) if ch != "0"
                       else chr(0x24EA))
        else:
            out.append(ch)
    return "".join(out)


# ── Technique 3: braille ───────────────────────────────────────────────────
_BRAILLE = {
    "a": "⠁", "b": "⠃", "c": "⠉", "d": "⠙", "e": "⠑", "f": "⠋",
    "g": "⠛", "h": "⠓", "i": "⠊", "j": "⠚", "k": "⠅", "l": "⠇",
    "m": "⠍", "n": "⠝", "o": "⠕", "p": "⠏", "q": "⠟", "r": "⠗",
    "s": "⠎", "t": "⠞", "u": "⠥", "v": "⠧", "w": "⠺", "x": "⠭",
    "y": "⠽", "z": "⠵", " ": " ",
}


def _braille(s: str) -> str:
    return "".join(_BRAILLE.get(ch.lower(), ch) for ch in s)


# ── Technique 4: morse ─────────────────────────────────────────────────────
_MORSE = {
    "a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".",
    "f": "..-.", "g": "--.", "h": "....", "i": "..", "j": ".---",
    "k": "-.-", "l": ".-..", "m": "--", "n": "-.", "o": "---",
    "p": ".--.", "q": "--.-", "r": ".-.", "s": "...", "t": "-",
    "u": "..-", "v": "...-", "w": ".--", "x": "-..-", "y": "-.--",
    "z": "--..", "0": "-----", "1": ".----", "2": "..---",
    "3": "...--", "4": "....-", "5": ".....", "6": "-....",
    "7": "--...", "8": "---..", "9": "----.",
}


def _morse(s: str) -> str:
    return " ".join(_MORSE.get(ch.lower(), ch) for ch in s)


# ── Technique 5: unicode look-alike substitution ───────────────────────────
_UNICODE_LOOKALIKE = {
    "a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "y": "у",
    "x": "х", "i": "і", "s": "ѕ", "h": "һ",
}


def _unicode_sub(s: str, *, density: float = 0.6) -> str:
    out = []
    for ch in s:
        sub = _UNICODE_LOOKALIKE.get(ch.lower())
        if sub and random.random() < density:
            out.append(sub if ch.islower() else sub.upper())
        else:
            out.append(ch)
    return "".join(out)


# ── Technique 6: phonetic spelling ─────────────────────────────────────────
_PHONETIC = {
    "a": "ay", "b": "bee", "c": "see", "d": "dee", "e": "ee",
    "f": "eff", "g": "gee", "h": "aitch", "i": "eye", "j": "jay",
    "k": "kay", "l": "ell", "m": "em", "n": "en", "o": "oh",
    "p": "pee", "q": "cue", "r": "ar", "s": "ess", "t": "tee",
    "u": "you", "v": "vee", "w": "double-you", "x": "ex", "y": "why",
    "z": "zee",
}


def _phonetic(s: str) -> str:
    return "-".join(_PHONETIC.get(ch.lower(), ch) for ch in s)


# ── Technique 7: zero-width joiner injection ───────────────────────────────
_ZW = "\u200b"  # zero-width space


def _zwj(s: str, *, density: float = 0.5) -> str:
    out: list[str] = []
    for ch in s:
        out.append(ch)
        if random.random() < density and ch.isalpha():
            out.append(_ZW)
    return "".join(out)


TECHNIQUES = {
    "leet":     _leet,
    "bubble":   _bubble,
    "braille":  _braille,
    "morse":    _morse,
    "unicode":  _unicode_sub,
    "phonetic": _phonetic,
    "zwj":      _zwj,
}


def _triggers_for_tier(intensity: str) -> list[str]:
    n = TIER_SIZE.get(intensity, TIER_SIZE["medium"])
    return DEFAULT_TRIGGERS[:n]


def perturb(
    text: str,
    *,
    technique: str | None = None,
    intensity: str = "medium",
    triggers: Iterable[str] | None = None,
    seed: int | None = None,
) -> str:
    """Apply one technique to every trigger in ``text`` (case-insensitive)."""
    if seed is not None:
        random.seed(seed)
    techs = list(TECHNIQUES.values()) if technique is None else [TECHNIQUES[technique]]
    trig = list(triggers) if triggers is not None else _triggers_for_tier(intensity)
    out = text
    for t in trig:
        pattern = re.compile(re.escape(t), re.IGNORECASE)
        for fn in techs:
            out = pattern.sub(lambda m, _fn=fn: _fn(m.group(0)), out)
    return out


def perturb_all(text: str, *, intensity: str = "medium",
                seed: int | None = None) -> dict[str, str]:
    """Run every technique against ``text`` and return one variant per technique."""
    out: dict[str, str] = {}
    for name in TECHNIQUES:
        out[name] = perturb(text, technique=name,
                            intensity=intensity, seed=seed)
    return out


def list_techniques() -> list[str]:
    return list(TECHNIQUES)
