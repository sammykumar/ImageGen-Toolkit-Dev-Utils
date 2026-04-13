"""
ImageGen Toolkit — Job Event Emitter node.

Accepts a finished video output and POSTs a ``job_completed`` event to the
configured app webhook (``IMAGEGEN_EVENTS_URL`` / ``IMAGEGEN_EVENT_TOKEN``).

On failure the node logs a warning and passes the video through unchanged so the
workflow does not hard-fail.  The caller is responsible for configuring the two
environment variables:

    IMAGEGEN_EVENTS_URL   — full URL of the POST endpoint, e.g.
                             https://my-app.vercel.app/api/comfyui/events
    IMAGEGEN_EVENT_TOKEN  — Bearer token matching COMFYUI_EVENT_TOKEN on the app

The node infers the ComfyUI ``prompt_id`` from the hidden ``unique_id`` input
so it can be included in the payload as ``comfyui_run_id``.  The app uses this
to resolve the associated durable job when no explicit ``job_id`` is provided.
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


def _post_event(payload: dict[str, Any]) -> None:
    """POST ``payload`` as JSON to the configured events endpoint."""
    events_url = _resolve_env(_ENV_EVENTS_URL)
    event_token = _resolve_env(_ENV_EVENT_TOKEN)

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
    Try to extract a usable filename from the VHS video output dict.

    VHS ``SaveVideo`` / ``CreateVideo`` nodes return a dict with keys like
    ``gifs``, ``videos``, or ``filenames``.  Each entry is a list of dicts that
    may contain ``filename`` and ``subfolder``.
    """
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
            },
            "hidden": {
                # ComfyUI injects the node's unique graph id here.
                # Note: this is the graph node id, not the execution prompt_id.
                "unique_id": "UNIQUE_ID",
            },
        }

    def emit_and_passthrough(
        self,
        video: Any,
        job_id: str = "",
        unique_id: str | None = None,
    ) -> tuple[Any]:
        output_filename = _extract_output_filename(video)

        effective_job_id = job_id.strip() if job_id else ""

        payload: dict[str, Any] = {
            "event_type": "job_completed",
            "job_id": effective_job_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        # unique_id is the graph node id, not the execution prompt_id, so we
        # omit comfyui_run_id here.  The app resolves the job via job_id when
        # provided, or via the history fallback (resolveOutputFromHistory) on
        # the server side when job_id is absent.

        if output_filename:
            payload["output_url"] = output_filename

        _post_event(payload)

        return (video,)


NODE_CLASS_MAPPINGS: dict[str, type] = {
    "JobEventEmitter": JobEventEmitterNode,
}

NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    "JobEventEmitter": "Job Event Emitter (ImageGen Toolkit)",
}
