# pc/app/ai/ai_ark.py
import base64
import json
import os
import re
from typing import Any, Dict

import cv2

# Best-effort JSON extraction from model output
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _resize_for_ai(frame_bgr, max_w: int = 640):
    """Downscale to reduce payload size (data-url can be very large)."""
    h, w = frame_bgr.shape[:2]
    if w <= max_w:
        return frame_bgr
    new_h = int(h * (max_w / w))
    return cv2.resize(frame_bgr, (max_w, new_h))


def _frame_to_data_url_jpeg(frame_bgr, jpeg_quality: int = 85) -> str:
    """OpenCV BGR -> JPEG base64 data url (Ark supports data:image/...;base64)."""
    ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Best-effort JSON object extraction:
      1) json.loads(text)
      2) extract first {...} block then json.loads(...)
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("empty model output")

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    m = _JSON_RE.search(text)
    if not m:
        raise ValueError("no json object found in model output")

    chunk = m.group(0)
    obj = json.loads(chunk)
    if not isinstance(obj, dict):
        raise ValueError("json is not an object")
    return obj


def resolve_api_key(cfg_or_key: Any = None) -> str:
    """
    Compatible with two call styles (matches ai_monitor_worker usage):
      - resolve_api_key(cfg_dict)
      - resolve_api_key("xxx")

    Priority:
      explicit string > env ARK_API_KEY > cfg['ark_api_key'/...]
    """
    if isinstance(cfg_or_key, str):
        return cfg_or_key

    env_key = os.environ.get("ARK_API_KEY")
    if env_key:
        return env_key

    if isinstance(cfg_or_key, dict):
        for k in ("ark_api_key", "ARK_API_KEY", "api_key", "API_KEY"):
            v = cfg_or_key.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    return ""


class ArkVisionClient:
    """
    Volcengine Ark vision client wrapper.

    Uses volcenginesdkarkruntime.Ark and chat.completions.create with a "text + image_url" content structure.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_sec: int = 30,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_sec = timeout_sec
        self.base_url = base_url

        try:
            from volcenginesdkarkruntime import Ark  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Missing dependency: volcenginesdkarkruntime. "
                "Install it first (pip install volcenginesdkarkruntime). "
                f"Import error: {e}"
            )

        # Some environments require explicit base_url.
        try:
            self._client = Ark(api_key=self.api_key, base_url=self.base_url)
        except TypeError:
            # Backward-compatible with older SDKs (no base_url parameter)
            self._client = Ark(api_key=self.api_key)

    @staticmethod
    def build_prompt_contract() -> str:
        """
        Output contract (no response_format dependency).
        The model MUST return only one JSON object, no markdown, no extra text.
        """
        return (
            "You MUST output ONLY one JSON object (no markdown, no explanations, no code fences).\n"
            "The JSON MUST contain these fields:\n"
            "- has_person: boolean\n"
            "- person_count: number or null\n"
            "- activity: string (passing/standing/lingering/unknown)\n"
            "- risk_level: string (info/warn/critical)\n"
            "- summary: string\n"
            "- confidence: number (0~1)\n"
        )

    def analyze_frame(
        self,
        frame_bgr,
        time_text: str,
        prompt_template: str = "",
        scene_profile: str = "",
        session_focus: str = "",
        extra_prompt: str = "",
        jpeg_quality: int = 85,
        max_w: int = 640,
    ) -> Dict[str, Any]:
        """Analyze one frame and return a parsed JSON dict (with safe defaults)."""
        frame_bgr = _resize_for_ai(frame_bgr, max_w=max_w)
        data_url = _frame_to_data_url_jpeg(frame_bgr, jpeg_quality=jpeg_quality)

        prompt_parts = [f"Current time: {time_text}"]
        if prompt_template:
            prompt_parts.append(f"Role: {prompt_template}")
        if scene_profile:
            prompt_parts.append(f"Long-term scene profile: {scene_profile}")
        if session_focus:
            prompt_parts.append(f"Session focus: {session_focus}")
        if extra_prompt:
            prompt_parts.append(f"Extra rules/notes: {extra_prompt}")

        prompt_parts.append(self.build_prompt_contract())
        prompt_parts.append("Based on the CCTV frame, output the JSON now.")

        prompt_text = "\n\n".join(prompt_parts)

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                    ],
                }
            ],
        )

        out_text = ""
        try:
            out_text = resp.choices[0].message.content  # type: ignore
        except Exception:
            out_text = str(resp)

        parsed = _extract_json(out_text)

        # Safe defaults to avoid worker crashes
        parsed = dict(parsed or {})
        parsed.setdefault("has_person", False)
        parsed.setdefault("person_count", None)
        parsed.setdefault("activity", "unknown")
        parsed.setdefault("risk_level", "info")
        parsed.setdefault("summary", "")
        parsed.setdefault("confidence", 0.0)

        # Light normalization
        try:
            parsed["has_person"] = bool(parsed["has_person"])
        except Exception:
            parsed["has_person"] = False

        try:
            c = float(parsed.get("confidence", 0.0) or 0.0)
            parsed["confidence"] = max(0.0, min(1.0, c))
        except Exception:
            parsed["confidence"] = 0.0

        return parsed