"""
ImageGen Toolkit — Job Event Emitter node.

Accepts a finished video output and POSTs a ``job_completed`` event to the
configured app webhook (``IMAGEGEN_EVENTS_URL`` / ``IMAGEGEN_EVENT_TOKEN``).

On failure the node logs a warning and passes the video through unchanged so the
workflow does not hard-fail. The caller is responsible for configuring the two
environment variables:

    IMAGEGEN_EVENTS_URL   — full URL of the POST endpoint, e.g.
                             https://my-app.vercel.app/api/comfyui/events
    IMAGEGEN_EVENT_TOKEN  — Bearer token matching COMFYUI_EVENT_TOKEN on the app

When ComfyUI exposes execution metadata through hidden inputs, the node includes
the real execution ``prompt_id`` as ``comfyui_run_id``. It never uses the graph
node ``unique_id`` as a stand-in for the execution id.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_ENV_EVENTS_URL = "IMAGEGEN_EVENTS_URL"
_ENV_EVENT_TOKEN = "IMAGEGEN_EVENT_TOKEN"
_POST_TIMEOUT_SECONDS = 15


def _resolve_env(name: str) -> str | None:
    return os.environ.get(name, "").strip() or None


def _resolve_setting_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    trimmed = value.strip()
    return trimmed or None


def _post_event(
    payload: dict[str, Any],
    events_url: str | None = None,
    event_token: str | None = None,
) -> None:
    """POST ``payload`` as JSON to the configured events endpoint."""
    events_url = _resolve_setting_value(events_url) or _resolve_env(_ENV_EVENTS_URL)
    event_token = _resolve_setting_value(event_token) or _resolve_env(_ENV_EVENT_TOKEN)

    if not events_url:
        logger.warning(
            "[job_event_emitter] %s is not set — skipping event post", _ENV_EVENTS_URL
        )
        return

    if not event_token:
        logger.warning(
            "[job_event_emitter] %s is not set — skipping event post", _ENV_EVENT_TOKEN
        )
        return

    body = json.dumps(payload).encode("utf-8")
    req = Request(
        events_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {event_token}",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=_POST_TIMEOUT_SECONDS) as resp:
            status = resp.status
            if status >= 400:
                logger.warning(
                    "[job_event_emitter] Events endpoint returned HTTP %d", status
                )
            else:
                logger.info(
                    "[job_event_emitter] Event posted successfully (HTTP %d)", status
                )
    except URLError as exc:
        logger.warning("[job_event_emitter] Failed to post event: %s", exc)


def _extract_output_filename(video: Any) -> str | None:
    """
    Try to extract a usable filename from the VHS video output dict or a plain
    string path.

    VHS ``VideoCombine`` outputs a dict (``VHS_FILENAMES``) with keys like
    ``gifs``, ``videos``, or ``filenames``.  Each entry is a list of dicts that
    may contain ``filename`` and ``subfolder``.
    A plain string value is returned as-is when provided programmatically.
    """
    if isinstance(video, str):
        return video.strip() or None

    if not isinstance(video, dict):
        return None

    for field in ("videos", "gifs", "filenames", "images"):
        entries = video.get(field)
        if not isinstance(entries, list) or not entries:
            continue
        first = entries[0]
        if isinstance(first, dict):
            filename = first.get("filename") or first.get("name")
            subfolder = first.get("subfolder", "")
            if filename:
                return f"{subfolder}/{filename}".lstrip("/") if subfolder else filename
        elif isinstance(first, str):
            return first

    return None


def _extract_prompt_id(prompt: Any) -> str | None:
    """Return the true Comfy execution prompt_id when the runtime exposes it."""
    if not isinstance(prompt, dict):
        return None

    prompt_id = prompt.get("prompt_id")
    if isinstance(prompt_id, str):
        trimmed = prompt_id.strip()
        if trimmed:
            return trimmed

    return None


class JobEventEmitterNode:
    """
    Emit a ``job_completed`` webhook event when generation finishes.

    Place this node at the *end* of your workflow, connected to the output of
    your ``SaveVideo`` / ``CreateVideo`` node.  The node passes the video data
    through unchanged so it can coexist with preview nodes.
    """

    CATEGORY = "ImageGen Toolkit"
    FUNCTION = "emit_and_passthrough"
    RETURN_TYPES = ("VHS_FILENAMES",)
    RETURN_NAMES = ("video",)
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # type: ignore[override]
        return {
            "required": {
                # Accepts the typed VHS filenames payload from VideoCombine.
                "video": ("VHS_FILENAMES",),
            },
            "optional": {
                # Explicitly-provided app job id.  Leave blank to fall back to
                # the prompt_id-based lookup on the app side.
                "job_id": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "app durable job id (optional)",
                    },
                ),
                "events_url": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "events webhook URL (optional)",
                    },
                ),
                "event_token": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "events bearer token (optional)",
                    },
                ),
            },
            "hidden": {
                # ComfyUI injects the node's unique graph id here.
                # Note: this is the graph node id, not the execution prompt_id.
                "unique_id": "UNIQUE_ID",
                # The prompt payload may include execution metadata depending on
                # the active ComfyUI runtime contract.
                "prompt": "PROMPT",
            },
        }

    def emit_and_passthrough(
        self,
        video: Any,
        job_id: str = "",
        events_url: str = "",
        event_token: str = "",
        unique_id: str | None = None,
        prompt: Any = None,
    ) -> tuple[Any]:
        output_filename = _extract_output_filename(video)

        effective_job_id = job_id.strip() if job_id else ""
        comfyui_run_id = _extract_prompt_id(prompt)

        payload: dict[str, Any] = {
            "event_type": "job_completed",
            "job_id": effective_job_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        # unique_id is the graph node id, not the execution prompt_id.
        # Only include comfyui_run_id when Comfy exposes a real prompt_id.
        if comfyui_run_id:
            payload["comfyui_run_id"] = comfyui_run_id

        if output_filename:
            payload["output_url"] = output_filename

        _post_event(payload, events_url=events_url, event_token=event_token)

        return (video,)


NODE_CLASS_MAPPINGS: dict[str, type] = {
    "JobEventEmitter": JobEventEmitterNode,
}

NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    "JobEventEmitter": "Job Event Emitter (ImageGen Toolkit)",
}
