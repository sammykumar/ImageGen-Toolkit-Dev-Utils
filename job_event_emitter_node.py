"""
ImageGen Toolkit job event nodes.

Provides a dedicated start event node that carries the durable ``job_id`` and a
separate finish event node that emits completion timing while inferring the same
``job_id`` from the connected start node in the hidden prompt graph.
"""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_POST_TIMEOUT_SECONDS = 15
_RESPONSE_SNIPPET_LIMIT = 300
_START_MARKER_PREFIX = "imagegen-job-started:"


def _resolve_setting_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    trimmed = value.strip()
    return trimmed or None


def _utc_timestamp_z() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _read_text_snippet(
    value: bytes | str | None,
    limit: int = _RESPONSE_SNIPPET_LIMIT,
) -> str | None:
    if value is None:
        return None

    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = value

    trimmed = text.strip()
    if not trimmed:
        return None

    return trimmed[:limit]


def _payload_summary(payload: dict[str, Any]) -> dict[str, str]:
    summary: dict[str, str] = {}
    for source_key, target_key in (
        ("event_type", "event_type"),
        ("job_id", "job_id"),
        ("comfyui_run_id", "comfyui_run_id"),
    ):
        value = payload.get(source_key)
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                summary[target_key] = trimmed

    return summary


def _post_event(
    payload: dict[str, Any],
    events_url: str | None = None,
    event_token: str | None = None,
) -> None:
    events_url = _resolve_setting_value(events_url)
    event_token = _resolve_setting_value(event_token)

    if not events_url:
        logger.warning("[job_event_emitter] events_url is blank - skipping event post")
        return

    if not event_token:
        logger.warning("[job_event_emitter] event_token is blank - skipping event post")
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
            response_snippet = _read_text_snippet(resp.read())
            if status >= 400:
                logger.warning(
                    "[job_event_emitter] Events endpoint returned HTTP %d payload=%s response=%s",
                    status,
                    _payload_summary(payload),
                    response_snippet,
                )
            else:
                logger.info(
                    "[job_event_emitter] Event posted successfully (HTTP %d) payload=%s",
                    status,
                    _payload_summary(payload),
                )
    except HTTPError as exc:
        response_snippet = _read_text_snippet(exc.read())
        logger.warning(
            "[job_event_emitter] Events endpoint rejected webhook HTTP %d payload=%s response=%s",
            exc.code,
            _payload_summary(payload),
            response_snippet,
        )
    except URLError as exc:
        logger.warning(
            "[job_event_emitter] Failed to post event payload=%s error=%s",
            _payload_summary(payload),
            exc,
        )
def _extract_prompt_id(prompt: Any) -> str | None:
    if not isinstance(prompt, dict):
        return None

    prompt_id = prompt.get("prompt_id")
    if isinstance(prompt_id, str):
        trimmed = prompt_id.strip()
        if trimmed:
            return trimmed

    return None


def _build_start_marker(job_id: str) -> str:
    return f"{_START_MARKER_PREFIX}{job_id}"


def _extract_job_id_from_marker(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    trimmed = value.strip()
    if not trimmed.startswith(_START_MARKER_PREFIX):
        return None

    job_id = trimmed.removeprefix(_START_MARKER_PREFIX).strip()
    return job_id or None


def _resolve_prompt_node(prompt: Any, node_id: str) -> dict[str, Any] | None:
    if not isinstance(prompt, dict):
        return None
    node = prompt.get(node_id)
    return node if isinstance(node, dict) else None


def _resolve_linked_node_id(input_value: Any) -> str | None:
    if not isinstance(input_value, list) or len(input_value) < 1:
        return None
    source_id = input_value[0]
    if isinstance(source_id, str):
        trimmed = source_id.strip()
        return trimmed or None
    if isinstance(source_id, int):
        return str(source_id)
    return None


def _infer_job_id_from_started_node(prompt: Any, unique_id: str | None) -> str | None:
    if not unique_id or not isinstance(prompt, dict):
        return None

    finish_node = _resolve_prompt_node(prompt, unique_id)
    if not finish_node:
        return None

    inputs = finish_node.get("inputs")
    if not isinstance(inputs, dict):
        return None

    started_marker_input = inputs.get("job_start")
    linked_node_id = _resolve_linked_node_id(started_marker_input)
    if not linked_node_id:
        return None

    started_node = _resolve_prompt_node(prompt, linked_node_id)
    if not started_node:
        return None

    started_inputs = started_node.get("inputs")
    if not isinstance(started_inputs, dict):
        return None

    job_id = started_inputs.get("job_id")
    return _resolve_setting_value(job_id)


class JobEventStartedNode:
    CATEGORY = "ImageGen Toolkit"
    FUNCTION = "emit"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("job_start",)

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # type: ignore[override]
        return {
            "required": {
                "job_id": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "app durable job id",
                    },
                ),
                "events_url": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "events webhook URL",
                    },
                ),
                "event_token": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "events bearer token",
                    },
                ),
            },
            "hidden": {
                "prompt": "PROMPT",
            },
        }

    def emit(
        self,
        job_id: str,
        events_url: str,
        event_token: str,
        prompt: Any = None,
    ) -> tuple[str]:
        effective_job_id = job_id.strip() if job_id else ""
        comfyui_run_id = _extract_prompt_id(prompt)

        payload: dict[str, Any] = {
            "event_type": "job_started",
            "job_id": effective_job_id,
            "timestamp": _utc_timestamp_z(),
        }
        if comfyui_run_id:
            payload["comfyui_run_id"] = comfyui_run_id

        _post_event(payload, events_url=events_url, event_token=event_token)
        return (_build_start_marker(effective_job_id),)


class JobEventFinishedNode:
    CATEGORY = "ImageGen Toolkit"
    FUNCTION = "emit_and_passthrough"
    RETURN_TYPES = ("VHS_FILENAMES",)
    RETURN_NAMES = ("video",)
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls) -> dict:  # type: ignore[override]
        return {
            "required": {
                "job_start": ("STRING",),
                "video": ("VHS_FILENAMES",),
                "events_url": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "events webhook URL",
                    },
                ),
                "event_token": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "events bearer token",
                    },
                ),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
            },
        }

    def emit_and_passthrough(
        self,
        job_start: str,
        video: Any,
        events_url: str = "",
        event_token: str = "",
        unique_id: str | None = None,
        prompt: Any = None,
    ) -> tuple[Any]:
        comfyui_run_id = _extract_prompt_id(prompt)
        effective_job_id = _extract_job_id_from_marker(job_start) or _infer_job_id_from_started_node(
            prompt,
            unique_id,
        )

        payload: dict[str, Any] = {
            "event_type": "job_completed",
            "job_id": effective_job_id or "",
            "timestamp": _utc_timestamp_z(),
        }

        if comfyui_run_id:
            payload["comfyui_run_id"] = comfyui_run_id

        _post_event(payload, events_url=events_url, event_token=event_token)
        return (video,)


NODE_CLASS_MAPPINGS: dict[str, type] = {
    "JobEventStarted": JobEventStartedNode,
    "JobEventFinished": JobEventFinishedNode,
}

NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    "JobEventStarted": "Event - Job Started",
    "JobEventFinished": "Event - Job Finished",
}
