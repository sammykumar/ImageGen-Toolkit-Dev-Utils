"""
ImageGen Toolkit job event node.

Provides a single completion event node that accepts the durable ``job_id``
directly, extracts best-effort output filename metadata from the VHS payload,
and posts the finished webhook consumed by the TanStack app.
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


def _extract_filename_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _resolve_setting_value(value)

    if isinstance(value, dict):
        for key in ("filename", "name", "path", "filepath"):
            candidate = _resolve_setting_value(value.get(key))
            if candidate:
                return candidate

        for key in ("videos", "gifs", "filenames", "images"):
            candidate = _extract_filename_value(value.get(key))
            if candidate:
                return candidate

        return None

    if isinstance(value, (list, tuple)):
        for item in value:
            candidate = _extract_filename_value(item)
            if candidate:
                return candidate

    return None


def _extract_output_metadata(value: Any) -> tuple[str | None, dict[str, str] | None]:
    if isinstance(value, str):
        return (_resolve_setting_value(value), None)

    if isinstance(value, dict):
        filename = _resolve_setting_value(value.get("filename"))
        subfolder = _resolve_setting_value(value.get("subfolder"))
        output_type = _resolve_setting_value(value.get("type"))

        if filename and subfolder and output_type:
            return (
                filename,
                {
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": output_type,
                },
            )

        if filename:
            return (filename, None)

        for key in ("name", "path", "filepath"):
            candidate = _resolve_setting_value(value.get(key))
            if candidate:
                return (candidate, None)

        for key in ("videos", "gifs", "filenames", "images"):
            candidate_filename, candidate_output = _extract_output_metadata(value.get(key))
            if candidate_filename:
                return (candidate_filename, candidate_output)

        return (None, None)

    if isinstance(value, (list, tuple)):
        for item in value:
            candidate_filename, candidate_output = _extract_output_metadata(item)
            if candidate_filename:
                return (candidate_filename, candidate_output)

    return (None, None)


def _extract_output_filename(video: Any) -> str | None:
    filename, _ = _extract_output_metadata(video)
    return filename


def _normalize_sampler_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _resolve_setting_value(value)

    if isinstance(value, dict):
        for key in ("sampler_name", "name", "label", "value", "sampler"):
            candidate = _normalize_sampler_value(value.get(key))
            if candidate:
                return candidate
        return None

    if isinstance(value, (list, tuple)):
        for item in value:
            candidate = _normalize_sampler_value(item)
            if candidate:
                return candidate

    return None


def _payload_completeness(output_filename: str | None, output_metadata: dict[str, str] | None) -> str:
    if output_metadata is not None:
        return "structured"

    if output_filename:
        return "filename_only"

    return "none"


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
                "job_id": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "app durable job id",
                    },
                ),
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
                "negative_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "negative prompt",
                    },
                ),
                "guidance_scale": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "step": 0.1,
                    },
                ),
                "steps": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "step": 1,
                    },
                ),
                "sampler": ("SAMPLER",),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "step": 1,
                    },
                ),
            },
            "hidden": {
                "prompt": "PROMPT",
            },
        }

    def emit_and_passthrough(
        self,
        job_id: str,
        video: Any,
        events_url: str = "",
        event_token: str = "",
        negative_prompt: str = "",
        guidance_scale: float = 0.0,
        steps: int = 0,
        sampler: Any = "",
        seed: int = 0,
        prompt: Any = None,
    ) -> tuple[Any]:
        comfyui_run_id = _extract_prompt_id(prompt)
        effective_job_id = _resolve_setting_value(job_id)
        output_filename, output_metadata = _extract_output_metadata(video)
        effective_negative_prompt = _resolve_setting_value(negative_prompt)
        effective_sampler = _normalize_sampler_value(sampler)

        payload: dict[str, Any] = {
            "event_type": "job_completed",
            "timestamp": _utc_timestamp_z(),
        }

        if effective_job_id:
            payload["job_id"] = effective_job_id

        if comfyui_run_id:
            payload["comfyui_run_id"] = comfyui_run_id

        if output_filename:
            payload["output_url"] = output_filename

        if output_metadata is not None:
            payload["output"] = output_metadata

        if effective_negative_prompt:
            payload["negative_prompt"] = effective_negative_prompt

        if isinstance(guidance_scale, (int, float)) and float(guidance_scale) != 0.0:
            payload["guidance_scale"] = float(guidance_scale)

        if isinstance(steps, int) and steps > 0:
            payload["steps"] = steps

        if effective_sampler:
            payload["sampler"] = effective_sampler

        if isinstance(seed, int) and seed != 0:
            payload["seed"] = seed

        logger.info(
            "[job_event_emitter] Prepared completion payload completeness=%s payload=%s",
            _payload_completeness(output_filename, output_metadata),
            _payload_summary(payload),
        )

        _post_event(payload, events_url=events_url, event_token=event_token)
        return (video,)


NODE_CLASS_MAPPINGS: dict[str, type] = {
    "JobEventFinished": JobEventFinishedNode,
}

NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    "JobEventFinished": "Job Event Emitter",
}
