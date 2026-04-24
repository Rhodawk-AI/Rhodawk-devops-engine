"""
Rhodawk AI — EmbodiedOS Gradio mount.

Tiny helper that builds the **EmbodiedOS** chat tab.  It is mounted by
``app.py`` inside the existing ``with gr.Tabs():`` block via a single
guarded import — it does **not** modify, rename, or remove any
existing tab, callback, or layout.  If anything in this module fails
(missing Gradio version, render error, etc.) the import in ``app.py``
catches it and the rest of the UI keeps working untouched.

The tab gives an investor-grade single-pane interface: type one
sentence in English, get a reply from EmbodiedOS, see the
mission transcript and recent missions side-by-side.  Under the
hood every keystroke goes through ``embodied_os.EmbodiedOS.dispatch``
which preserves every existing OpenClaw intent and adds the new
``mission repo`` / ``mission bounty`` / ``mission status`` /
``mission brief`` / ``mission list`` verbs.
"""

from __future__ import annotations

import json
from typing import Any


_EXAMPLES = [
    ["mission brief"],
    ["mission repo https://github.com/torvalds/linux"],
    ["mission bounty https://hackerone.com/security"],
    ["mission list"],
    ["scan https://github.com/openssl/openssl"],
    ["status"],
    ["help"],
]


def _format_reply(result: dict[str, Any]) -> str:
    if not result:
        return "(no reply)"
    head = result.get("reply", "(no reply)")
    intent = result.get("intent", "?")
    ok = result.get("ok", False)
    flag = "✅" if ok else "⚠️"
    body = f"{flag} **intent:** `{intent}`\n\n{head}"
    data = result.get("data")
    if data:
        try:
            blob = json.dumps(data, indent=2, default=str)
            if len(blob) > 4000:
                blob = blob[:4000] + "\n…(truncated)"
            body += f"\n\n<details><summary>data</summary>\n\n```json\n{blob}\n```\n\n</details>"
        except Exception:
            pass
    return body


def build_embodied_os_tab() -> None:
    """
    Construct the EmbodiedOS tab.  Must be called *inside* the existing
    ``with gr.Tabs():`` context in ``app.py``.
    """
    import gradio as gr

    try:
        from embodied_os import EmbodiedOS, _REGISTRY  # type: ignore
    except Exception as exc:  # noqa: BLE001
        gr.Markdown(f"### EmbodiedOS unavailable\n\n```\n{exc}\n```")
        return

    gr.Markdown(
        """
# 🧬 EmbodiedOS — the unified front-of-house brain

EmbodiedOS fuses **Hermes** (autonomous deep-research loop) and **OpenClaw**
(operator natural-language command bus) into one coordinator.  Type a single
English sentence; EmbodiedOS picks the right subsystem, runs the mission in
the background, and reports back.

**High-level missions**

| Verb | What it does |
|---|---|
| `mission repo <github-url>` | Clone → run failing tests → fix-mode (Hermes) → if all green, adversarial mutation pass (break/refix) → open PR → full zero-day attack pass (Hermes, 20 iter) → route P1/P2 findings into the disclosure vault. |
| `mission bounty <hackerone/bugcrowd-url>` | Fetch the program page (camofox-browser MCP if available, else `requests`), extract in-scope GitHub repos and domains, run `mission repo` on each, render a single PhD-level Markdown report listing every P1/P2 in submission-ready form. |
| `mission status <id>` | Live transcript of a running mission. |
| `mission list` | Recent missions with ids and status. |
| `mission brief` | Heartbeat snapshot — schedule, queue, skills, meta-learner cycle log. |

**Operator commands** (same as OpenClaw — every existing intent still works)

`scan <repo>` · `night run` · `pause night` · `resume night` · `status` ·
`approve <id>` · `reject <id>` · `explain <id>` · `help`
"""
    )

    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="EmbodiedOS",
                height=420,
                type="messages",
            )
            cmd = gr.Textbox(
                label="Command",
                placeholder="e.g. mission repo https://github.com/curl/curl",
                lines=2,
            )
            with gr.Row():
                send_btn  = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear")
            gr.Examples(examples=_EXAMPLES, inputs=cmd, label="Quick commands")
        with gr.Column(scale=1):
            recent_box = gr.Code(
                label="Recent missions",
                language="json",
                lines=22,
                interactive=False,
            )
            refresh_btn = gr.Button("🔄 Refresh recent missions")
            transcript_id  = gr.Textbox(
                label="Mission ID",
                placeholder="paste a mission id to inspect",
            )
            transcript_box = gr.TextArea(
                label="Mission transcript (last 50 lines)",
                lines=18, interactive=False,
            )
            transcript_btn = gr.Button("Load transcript")

    # ── handlers ────────────────────────────────────────────────────────
    def _send(message: str, history: list[dict] | None):
        history = history or []
        result = EmbodiedOS.dispatch(message, user="ui")
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": _format_reply(result)},
        ]
        return history, "", _recent_json()

    def _recent_json() -> str:
        try:
            return json.dumps(
                [m.summary() for m in _REGISTRY.list_recent(15)],
                indent=2, default=str,
            )
        except Exception as exc:  # noqa: BLE001
            return f"(error: {exc})"

    def _load_transcript(mid: str) -> str:
        mid = (mid or "").strip()
        if not mid:
            return "(enter a mission id)"
        ms = _REGISTRY.get(mid)
        if not ms:
            return f"(no mission with id={mid})"
        return "\n".join(ms.transcript[-50:])

    send_btn.click(_send, inputs=[cmd, chatbot],
                   outputs=[chatbot, cmd, recent_box])
    cmd.submit(_send, inputs=[cmd, chatbot],
               outputs=[chatbot, cmd, recent_box])
    clear_btn.click(lambda: ([], "", _recent_json()),
                    outputs=[chatbot, cmd, recent_box])
    refresh_btn.click(_recent_json, outputs=recent_box)
    transcript_btn.click(_load_transcript, inputs=transcript_id,
                         outputs=transcript_box)

    # Initial state on tab load.
    try:
        recent_box.value = _recent_json()
    except Exception:
        pass
