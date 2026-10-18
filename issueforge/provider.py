"""Small real Chat Completions adapter; no SDK or automatic paid calls."""

import json
import re
import urllib.error
import urllib.parse
import urllib.request


class ModelError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def parse_action(content: str) -> dict:
    if not isinstance(content, str):
        raise ModelError("Model action content must be text")
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        action = json.loads(content)
    except (ValueError, TypeError) as exc:
        raise ModelError("Model returned invalid JSON") from exc
    if not isinstance(action, dict) or action.get("action") not in {"read", "search", "propose", "stop"}:
        raise ModelError("Model must return a supported structured action")
    field = {"read": "path", "search": "query", "propose": "test_code", "stop": "reason"}[action["action"]]
    if not isinstance(action.get(field), str) or not action[field].strip():
        raise ModelError(f"Model action requires a nonempty {field}")
    if action["action"] == "propose" and not isinstance(action.get("hypothesis"), str):
        raise ModelError("Proposal must explain its hypothesis")
    return action


class CompatibleProvider:
    mode = "live_model"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        *,
        allow_remote: bool = False,
        max_calls: int = 6,
        timeout: int = 30,
    ):
        url = urllib.parse.urlsplit(base_url)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            not model
            or not model.strip()
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.scheme not in {"http", "https"}
        ):
            raise ModelError("Invalid model or endpoint")
        if not local and (not allow_remote or url.scheme != "https"):
            raise ModelError("Remote model endpoints require HTTPS and explicit --allow-remote consent")
        if not 1 <= max_calls <= 12 or not 1 <= timeout <= 120:
            raise ModelError("Model budget out of bounds")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model, self.api_key = model, api_key
        self.max_calls, self.timeout, self.calls = max_calls, timeout, 0
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0}
        self.opener = urllib.request.build_opener(NoRedirect())

    def complete(self, messages: list[dict]) -> dict:
        if self.calls >= self.max_calls:
            raise ModelError("Model request budget exhausted")
        if len(json.dumps(messages)) > 70_000:
            raise ModelError("Context budget exhausted")
        self.calls += 1
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": 1600,
                "response_format": {"type": "json_object"},
            }
        ).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request = urllib.request.Request(self.url, data=payload, headers=headers)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                data = response.read(128_001)
            if len(data) > 128_000:
                raise ModelError("Model response exceeds size budget")
            body = json.loads(data)
            action = parse_action(body["choices"][0]["message"]["content"])
            usage = body.get("usage") or {}
            if not isinstance(usage, dict):
                raise ModelError("Malformed model usage record")
            for field in self.usage:
                value = usage.get(field, 0)
                if type(value) is int and value >= 0:
                    self.usage[field] += value
            return action
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            raise ModelError(f"Model HTTP {status}; check authentication, availability or rate limits") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ModelError("Model endpoint unavailable or timed out") from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise ModelError("Malformed model response envelope") from None
