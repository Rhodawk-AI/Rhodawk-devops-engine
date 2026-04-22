---
name: ai-ml-security
domain: ai
triggers:
  languages:    [python]
  frameworks:   [pytorch, tensorflow, jax, transformers, langchain, llamaindex, vllm, ollama]
  asset_types:  [model, llm, ml-pipeline, mlops]
tools:          [garak, promptfoo, llm-attacks, modelscan, picklescan]
severity_focus: [P1, P2]
---

# AI / ML Security

## When to load
Any model artefact (`.pt`, `.bin`, `.safetensors`, `.gguf`, `.onnx`,
`.pkl`), training pipeline, prompt template, RAG index, agent tool wiring,
or hosted-inference endpoint.

## Bug classes that pay
1. **Pickle-based RCE** — `torch.load(weights_only=False)`, scikit-learn
   joblib, transformers `trust_remote_code=True`. `picklescan` and
   `modelscan` find these in seconds.
2. **Prompt injection** — direct (user) and indirect (web page, document,
   tool output). Look for: tool calling without allowlist, system-prompt
   leakage on `Repeat the words above`, formatting tricks (markdown links,
   invisible Unicode).
3. **Tool-call abuse** — agents allowed to call `shell`, `python_exec`,
   `http_request` without sandbox; unrestricted file system writes.
4. **RAG poisoning** — attacker-controlled doc enters the index → influences
   future queries. Check ingestion source allowlists, doc-level signing.
5. **Model inversion / extraction** — query-budget unbounded, embeddings
   API exposed, logit access enabled.
6. **Supply-chain on weights** — Hugging Face repo hijack, weight
   substitution, LoRA backdoors, sleeper agents triggered by phrase.
7. **Data poisoning** — training pipeline pulls from S3/web without integrity
   check; gradient masking attacks; label-flipping in fine-tune jobs.
8. **Adversarial inputs** — image classifier evasion, audio universal
   perturbation, text obfuscation (Unicode, homoglyphs, zero-width).
9. **Jailbreak chains** — multi-turn role-play, base64/rot13/leetspeak
   wrapping, system-prompt override via long-context distraction.
10. **Resource abuse** — KV-cache exhaustion, token-flood DoS, runaway
    agent loops (>100 tool calls).

## Methodology
1. Inventory model loads → grep for `torch.load`, `pickle.load`,
   `joblib.load`, `trust_remote_code`.
2. Scan weight files: `picklescan -p <weights>`; `modelscan scan <path>`.
3. Run `garak` against any LLM endpoint with the `dan,prompt_injection,
   leakage,malware-gen` probes.
4. Map the agent tool surface — every tool is an attack class. Especially
   any tool that takes a free-form string and forwards to a shell,
   subprocess, HTTP client, or file path.
5. For RAG: list ingestion sources, check whether content is sanitised
   before embedding, check whether retrieved docs are passed verbatim into
   the system prompt (they almost always are).
6. PoC must cause real impact: data exfil, code execution, account access,
   moderation bypass on a hosted product.
