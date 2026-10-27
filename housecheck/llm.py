"""Meterless Nightshift client: HouseCheck's only AI provider (NVIDIA Nemotron lanes).

Follows the Meterless Runtime provider contract: OpenAI-compatible
/v1/chat/completions, bearer runtime token, `meterless-app` header,
GET /v1/models as the online check.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

import httpx

from .config import Settings
from .trace import Trace

T = TypeVar("T")


class LLMError(RuntimeError):
    pass


@dataclass
class ChatResult:
    content: str
    model: str
    ms: int


class Nightshift:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.s = settings
        self.http = client or httpx.Client(timeout=settings.llm_timeout_s)

    def _headers(self) -> dict[str, str]:
        h = {"meterless-app": "housecheck"}
        if self.s.llm_token:
            h["Authorization"] = f"Bearer {self.s.llm_token}"
        return h

    def status(self) -> tuple[str, list[str], str]:
        try:
            res = self.http.get(f"{self.s.llm_url}/models", headers=self._headers(), timeout=5)
        except httpx.HTTPError as e:
            return "offline", [], str(e)[:200]
        if res.status_code in (401, 403):
            return "unauthorized", [], f"HTTP {res.status_code}"
        if res.status_code >= 400:
            return "offline", [], f"HTTP {res.status_code}"
        models = [m.get("id", "") for m in (res.json().get("data") or [])]
        return ("online" if models else "offline"), models, "" if models else "no models listed"

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> ChatResult:
        try:
            return self._chat_once(messages, temperature)
        except LLMError as e:
            if "HTTP 5" not in str(e) and "empty answer" not in str(e):
                raise
            time.sleep(3)
            return self._chat_once(messages, temperature)

    def _chat_once(self, messages: list[dict[str, str]], temperature: float) -> ChatResult:
        if not self.s.llm_token:
            raise LLMError("METERLESS_RUNTIME_TOKEN is not set (copy it from the Nightshift Console)")
        started = time.time()
        try:
            res = self.http.post(
                f"{self.s.llm_url}/chat/completions",
                headers={
                    **self._headers(),
                    "meterless-scope": "user",
                    # Nemotron reasons before its first token; raise Nightshift's first-token limit.
                    "meterless-ttfb-ms": "240000",
                    "Content-Type": "application/json",
                },
                json={"model": self.s.llm_model, "messages": messages, "temperature": temperature},
            )
        except httpx.HTTPError as e:
            raise LLMError(f"Nightshift unreachable: {e}") from e
        if res.status_code in (401, 403):
            raise LLMError(f"Nightshift rejected the runtime token (HTTP {res.status_code})")
        if res.status_code >= 400:
            raise LLMError(f"Nightshift HTTP {res.status_code}: {res.text[:200]}")
        body = res.json()
        content = strip_reasoning(((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
        if not content.strip():
            raise LLMError("Nightshift returned an empty answer")
        model = body.get("model") or res.headers.get("meterless-model") or "unknown"
        return ChatResult(content, model, int((time.time() - started) * 1000))

    def chat_json(
        self,
        trace: Trace,
        agent: str,
        action: str,
        messages: list[dict[str, str]],
        validate: Callable[[Any], T],
        retries: int = 1,
    ) -> tuple[T, str]:
        """Ask for JSON; on a parse/validation failure send the error back once so the model can fix it."""
        convo = list(messages)
        for attempt in range(retries + 1):
            result = self.chat(convo)
            try:
                value = validate(extract_json(result.content))
                trace.log(agent, action, model=result.model, ms=result.ms, attempt=attempt)
                return value, result.model
            except (ValueError, KeyError, TypeError) as e:
                trace.log(agent, action, status="retry", model=result.model, ms=result.ms, attempt=attempt, error=str(e)[:200])
                convo += [
                    {"role": "assistant", "content": result.content},
                    {"role": "user", "content": f"That was not valid: {e}. Reply again with only the corrected JSON object."},
                ]
        raise LLMError(f"{agent} could not get valid JSON from the model")


def strip_reasoning(text: str) -> str:
    """Nemotron reasoning models can inline their thinking ending in </think>; keep only the answer."""
    end = text.rfind("</think>")
    if end >= 0:
        text = text[end + len("</think>"):]
    return re.sub(r"<think>[\s\S]*$", "", text).strip()


def extract_json(text: str) -> Any:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    body = fenced.group(1) if fenced else text
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the reply")
    return json.loads(body[start : end + 1])
