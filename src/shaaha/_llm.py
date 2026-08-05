"""
shaaha._llm
===========
Shared helper for calling the Claude Messages API.

Deliberately implemented with stdlib `urllib` rather than the `anthropic`
SDK — the AI-powered layers (agent, rewriter, explainer) are opt-in
features that fall back to rule-based behaviour with no API key, and
Shaaha ships with zero hard dependencies by design. Pulling in the SDK
just for this would work against that.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

# Centralised so a model rotation is a one-line change instead of a
# find-and-replace across three files.
DEFAULT_MODEL = "claude-sonnet-5"
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def call_claude(
    prompt: str,
    api_key: str,
    *,
    system: Optional[str] = None,
    max_tokens: int = 1000,
    timeout: int = 30,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Call the Claude Messages API and return the response's raw text.

    Raises whatever urllib/json raises on failure — callers are expected
    to catch and fall back to their rule-based behaviour.
    """
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
        return data["content"][0]["text"]


def strip_json_fence(text: str) -> str:
    """Strip a ```json ... ``` or ``` ... ``` markdown fence if present."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()
