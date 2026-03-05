from __future__ import annotations

import json
import os
from typing import Any

import httpx

DISCLAIMER = "DISCLAIMER: This analysis was generated with AI assistance and has not been reviewed by a licensed attorney. It is provided as a preliminary draft for attorney review and should not be relied upon as legal advice or filed with any tribunal without thorough human review and verification of all citations. AI-generated analysis may contain errors, hallucinated citations, or incomplete analysis. All citations must be independently verified against the source patent documents."


def _backend() -> str | None:
    b = os.getenv("LLM_BACKEND")
    if b in {"anthropic", "openai"}:
        return b
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return None


def _call_llm(system: str, prompt: str) -> str:
    backend = _backend()
    if not backend:
        raise RuntimeError("LLM is not configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")
    with httpx.Client(timeout=60) as client:
        if backend == "anthropic":
            r = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": os.getenv("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01"},
                json={"model": "claude-3-5-sonnet-20241022", "max_tokens": 1800, "system": system, "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"]
        r = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "temperature": 0.2},
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def build_evidence_map(claims: list[dict], excerpts: list[dict]) -> dict[str, Any]:
    system = "Return strict JSON only. Use only provided excerpts and verbatim short quotes with citations. No paraphrase."
    prompt = json.dumps({"claims": claims, "excerpts": excerpts}, indent=2)
    out = _call_llm(system, prompt)
    return json.loads(out)


def draft_from_evidence(evidence_map: dict, proceeding_type: str, construction_standard: str, mode: str, action: str) -> str:
    system = "Draft attorney-quality post-grant text using ONLY evidence map facts. Every factual sentence must include citation. Separate facts vs argument."
    prompt = json.dumps(
        {
            "evidence_map": evidence_map,
            "proceeding_type": proceeding_type,
            "construction_standard": construction_standard,
            "drafting_mode": mode,
            "action": action,
        },
        indent=2,
    )
    out = _call_llm(system, prompt)
    return f"{DISCLAIMER}\n\n{out}"
