from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


WORKFLOW_IMPORT_LIST_PATH = "/api/image-gen-toolkit/workflows/importable"
WORKFLOW_IMPORT_CONTENT_PATH = "/api/image-gen-toolkit/workflows/importable/content"
USERDATA_WORKFLOWS_PREFIX = "workflows"
LGRAPH_EVENT_MODE_NEVER = 2
LGRAPH_EVENT_MODE_BYPASS = 4


class WorkflowImportConversionError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "workflow_conversion_failed",
        warnings: list[str] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.warnings = warnings or []


@dataclass(frozen=True)
class ImportableWorkflowRecord:
    source_kind: str
    source_id: str
    display_name: str
    file_path: Path
    path: str | None = None
    modified_at: str | None = None
    format_hint: str | None = None

    def to_summary(self) -> dict[str, Any]:
        summary = {
            "sourceKind": self.source_kind,
            "sourceId": self.source_id,
            "displayName": self.display_name,
        }
        if self.path is not None:
            summary["path"] = self.path
        if self.modified_at is not None:
            summary["modifiedAt"] = self.modified_at
        if self.format_hint is not None:
            summary["formatHint"] = self.format_hint
        return summary


def _to_iso_modified_at(file_path: Path) -> str | None:
    try:
        modified_at = file_path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(modified_at, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _read_json_object(file_path: Path) -> Any:
    with file_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _detect_format_hint(workflow: Any) -> str:
    if isinstance(workflow, dict):
        if workflow and all(
            isinstance(node_id, str)
            and isinstance(node_data, dict)
            and isinstance(node_data.get("class_type"), str)
            for node_id, node_data in workflow.items()
        ):
            return "api_prompt"
        if isinstance(workflow.get("nodes"), list):
            return "workflow_json"
    return "unknown"


def _normalize_widget_values(raw_value: Any) -> list[Any]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return raw_value
    if isinstance(raw_value, dict):
        length = raw_value.get("length")
        if isinstance(length, int) and length >= 0:
            values: list[Any] = []
            for index in range(length):
                if str(index) in raw_value:
                    values.append(raw_value[str(index)])
                elif index in raw_value:
                    values.append(raw_value[index])
                else:
                    raise WorkflowImportConversionError(
                        "Workflow JSON widgets_values could not be converted safely.",
                        code="workflow_widget_values_invalid",
                    )
            return values

    raise WorkflowImportConversionError(
        "Workflow JSON widgets_values must be a list-like structure.",
        code="workflow_widget_values_invalid",
    )


def _serialize_widget_value(value: Any) -> Any:
    if isinstance(value, list):
        return {"__value__": value}
    return value


def _build_link_lookup(links: Any) -> dict[Any, dict[str, Any]]:
    if not isinstance(links, list):
        return {}

    lookup: dict[Any, dict[str, Any]] = {}
    for link in links:
        link_id: Any = None
        origin_id: Any = None
        origin_slot: Any = None
        target_id: Any = None
        target_slot: Any = None

        if isinstance(link, list) and len(link) >= 5:
            link_id, origin_id, origin_slot, target_id, target_slot = link[:5]
        elif isinstance(link, dict):
            link_id = link.get("id")
            origin_id = link.get("origin_id")
            origin_slot = link.get("origin_slot")
            target_id = link.get("target_id")
            target_slot = link.get("target_slot")

        if link_id is None:
            continue

        lookup[link_id] = {
            "origin_id": origin_id,
            "origin_slot": origin_slot,
            "target_id": target_id,
            "target_slot": target_slot,
        }

    return lookup


def _get_node_title(node: dict[str, Any], fallback: str) -> str:
    title = node.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return fallback


def _should_skip_workflow_node(node: dict[str, Any]) -> bool:
    mode = node.get("mode")
    if mode in {LGRAPH_EVENT_MODE_NEVER, LGRAPH_EVENT_MODE_BYPASS}:
        return True

    flags = node.get("flags")
    if isinstance(flags, dict) and flags.get("virtual") is True:
        return True

    return False


def _convert_workflow_json_to_api_prompt(workflow: Any) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(workflow, dict):
        raise WorkflowImportConversionError(
            "Workflow JSON must be an object.",
            code="workflow_json_invalid",
        )

    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        raise WorkflowImportConversionError(
            "Workflow JSON is missing a nodes array.",
            code="workflow_json_missing_nodes",
        )

    link_lookup = _build_link_lookup(workflow.get("links"))
    converted: dict[str, Any] = {}
    warnings: list[str] = []

    for index, raw_node in enumerate(nodes):
        if not isinstance(raw_node, dict):
            raise WorkflowImportConversionError(
                f"Workflow JSON node at index {index} is not an object.",
                code="workflow_node_invalid",
            )

        if _should_skip_workflow_node(raw_node):
            continue

        node_id = raw_node.get("id")
        node_type = raw_node.get("type")
        if node_id is None or not isinstance(node_type, str) or not node_type.strip():
            raise WorkflowImportConversionError(
                f"Workflow JSON node at index {index} is missing an executable type.",
                code="workflow_node_missing_type",
            )

        node_title = _get_node_title(raw_node, node_type.strip())
        inputs: dict[str, Any] = {}

        input_slots = raw_node.get("inputs")
        if input_slots is not None and not isinstance(input_slots, list):
            raise WorkflowImportConversionError(
                f"Workflow node '{node_title}' inputs are malformed.",
                code="workflow_node_inputs_invalid",
            )

        widget_input_names: list[str] = []
        for raw_input in input_slots or []:
            if not isinstance(raw_input, dict):
                continue
            widget_meta = raw_input.get("widget")
            if isinstance(widget_meta, dict):
                widget_name = widget_meta.get("name")
                if isinstance(widget_name, str) and widget_name.strip():
                    widget_input_names.append(widget_name.strip())

        widget_values = _normalize_widget_values(raw_node.get("widgets_values"))
        if len(widget_values) > len(widget_input_names):
            raise WorkflowImportConversionError(
                f"Workflow node '{node_title}' has widget values that cannot be mapped safely by the bridge.",
                code="workflow_widget_mapping_ambiguous",
            )

        for widget_name, widget_value in zip(widget_input_names, widget_values):
            inputs[widget_name] = _serialize_widget_value(widget_value)

        for raw_input in input_slots or []:
            if not isinstance(raw_input, dict):
                continue
            input_name = raw_input.get("name")
            if not isinstance(input_name, str) or not input_name.strip():
                continue
            link_id = raw_input.get("link")
            if link_id is None:
                continue

            link_record = link_lookup.get(link_id)
            if link_record is None:
                warnings.append(
                    f"Omitted dangling link '{link_id}' from node '{node_title}' input '{input_name}'."
                )
                continue

            origin_id = link_record.get("origin_id")
            origin_slot = link_record.get("origin_slot")
            if origin_id is None or not isinstance(origin_slot, int):
                warnings.append(
                    f"Omitted malformed link '{link_id}' from node '{node_title}' input '{input_name}'."
                )
                continue

            inputs[input_name.strip()] = [str(origin_id), origin_slot]

        converted[str(node_id)] = {
            "inputs": inputs,
            "class_type": node_type.strip(),
            "_meta": {"title": node_title},
        }

    if not converted:
        raise WorkflowImportConversionError(
            "Workflow JSON did not contain any executable nodes after filtering muted or virtual nodes.",
            code="workflow_has_no_executable_nodes",
        )

    for node_payload in converted.values():
        node_inputs = node_payload.get("inputs")
        if not isinstance(node_inputs, dict):
            continue
        for input_name, input_value in list(node_inputs.items()):
            if (
                isinstance(input_value, list)
                and len(input_value) == 2
                and str(input_value[0]) not in converted
            ):
                del node_inputs[input_name]
                warnings.append(
                    f"Removed dangling converted input '{input_name}' that referenced an omitted node."
                )

    return converted, warnings


async def _validate_runtime_api_prompt(workflow: dict[str, Any]) -> None:
    try:
        from execution import validate_prompt  # type: ignore
    except ImportError:
        return

    is_valid, error, _outputs, _node_errors = await validate_prompt(
        "image-gen-toolkit-workflow-import",
        workflow,
        None,
    )
    if is_valid:
        return

    message = "Workflow JSON could not be converted into a valid API prompt."
    if isinstance(error, dict):
        error_message = error.get("message")
        error_details = error.get("details")
        if isinstance(error_message, str) and error_message.strip():
            message = error_message.strip()
            if isinstance(error_details, str) and error_details.strip():
                message = f"{message}: {error_details.strip()}"
        elif isinstance(error_details, str) and error_details.strip():
            message = error_details.strip()

    raise WorkflowImportConversionError(message)


def _build_fetch_payload(record: ImportableWorkflowRecord, workflow: Any) -> dict[str, Any]:
    original_format = record.format_hint or _detect_format_hint(workflow)
    runtime_workflow = workflow
    runtime_format: str | None = None
    warnings: list[str] = []
    conversion_payload: dict[str, Any] = {"performed": False}

    if original_format == "api_prompt":
        runtime_format = "api_prompt"
    elif original_format == "workflow_json":
        runtime_workflow, warnings = _convert_workflow_json_to_api_prompt(workflow)
        runtime_format = "api_prompt"
        conversion_payload = {"performed": True}
        if warnings:
            conversion_payload["warnings"] = warnings

    payload: dict[str, Any] = {
        "summary": record.to_summary(),
        "workflow": runtime_workflow,
        "formatHint": runtime_format or original_format,
        "originalFormat": original_format,
        "conversion": conversion_payload,
    }
    if runtime_format is not None:
        payload["runtimeFormat"] = runtime_format
    if warnings:
        payload["warnings"] = warnings
    if payload["formatHint"] == "unknown":
        payload["warnings"] = [
            "Could not infer whether this JSON is an API prompt or workflow export."
        ]
    return payload


def _is_json_file(file_path: Path) -> bool:
    return file_path.is_file() and file_path.suffix.lower() == ".json"


def _workflow_record_from_file(
	*,
	source_kind: str,
	source_id: str,
	display_name: str,
	file_path: Path,
	path: str | None = None,
) -> ImportableWorkflowRecord | None:
    if not _is_json_file(file_path):
        return None

    try:
        workflow = _read_json_object(file_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    return ImportableWorkflowRecord(
        source_kind=source_kind,
        source_id=source_id,
        display_name=display_name,
        file_path=file_path,
        path=path,
        modified_at=_to_iso_modified_at(file_path),
        format_hint=_detect_format_hint(workflow),
    )


def _build_template_display_name(
	template_name: str | None,
	asset_name: str,
	json_asset_count: int,
) -> str:
    asset_stem = Path(asset_name).stem
    if not template_name:
        return asset_stem
    if json_asset_count > 1:
        return f"{template_name} / {asset_stem}"
    return template_name


def _list_workflow_templates() -> list[ImportableWorkflowRecord]:
	try:
		from comfyui_workflow_templates import get_asset_path, iter_templates  # type: ignore
	except ImportError:
		return _list_legacy_workflow_templates()

	try:
		template_entries = list(iter_templates())
	except Exception:
		return []

	records: list[ImportableWorkflowRecord] = []
	for entry in template_entries:
		template_id = getattr(entry, "template_id", None) or getattr(entry, "id", None)
		assets = [
			asset
			for asset in getattr(entry, "assets", [])
			if getattr(asset, "filename", "").lower().endswith(".json")
		]
		for asset in assets:
			asset_name = getattr(asset, "filename", "")
			if not asset_name:
				continue
			try:
				asset_path = Path(get_asset_path(template_id, asset_name))
			except Exception:
				continue
			record = _workflow_record_from_file(
				source_kind="workflow_template",
				source_id=f"{template_id}:{asset_name}" if template_id else asset_name,
				display_name=_build_template_display_name(
					getattr(entry, "name", None) or getattr(entry, "title", None),
					asset_name,
					len(assets),
				),
				file_path=asset_path,
			)
			if record is not None:
				records.append(record)
	return records


def _list_legacy_workflow_templates() -> list[ImportableWorkflowRecord]:
    try:
        from app.frontend_management import FrontendManager  # type: ignore
    except ImportError:
        return []

    try:
        legacy_root_raw = FrontendManager.legacy_templates_path()
    except Exception:
        return []

    if not legacy_root_raw:
        return []

    legacy_root = Path(legacy_root_raw)
    if not legacy_root.is_dir():
        return []

    records: list[ImportableWorkflowRecord] = []
    for file_path in sorted(legacy_root.rglob("*.json")):
        relative_path = file_path.relative_to(legacy_root).as_posix()
        record = _workflow_record_from_file(
            source_kind="workflow_template",
            source_id=relative_path,
            display_name=file_path.stem,
            file_path=file_path,
        )
        if record is not None:
            records.append(record)
    return records


def _get_userdata_root() -> Path:
    import folder_paths  # type: ignore

    get_public_user_directory = getattr(folder_paths, "get_public_user_directory", None)
    if callable(get_public_user_directory):
        public_default = get_public_user_directory("default")
        if public_default:
            return Path(public_default)

    get_user_directory = getattr(folder_paths, "get_user_directory", None)
    if callable(get_user_directory):
        return Path(get_user_directory()) / "default"

    raise RuntimeError("ComfyUI userdata directory is unavailable")


def _normalize_userdata_source_id(source_id: str) -> PurePosixPath:
    normalized = PurePosixPath(source_id)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError("sourceId must be a relative userdata path")
    if not normalized.parts or normalized.parts[0] != USERDATA_WORKFLOWS_PREFIX:
        raise ValueError("sourceId must point to userdata/workflows content")
    return normalized


def _list_userdata_workflows() -> list[ImportableWorkflowRecord]:
    root = _get_userdata_root()
    workflow_root = root / USERDATA_WORKFLOWS_PREFIX
    if not workflow_root.is_dir():
        return []

    records: list[ImportableWorkflowRecord] = []
    for file_path in sorted(workflow_root.rglob("*.json")):
        source_id = file_path.relative_to(root).as_posix()
        record = _workflow_record_from_file(
            source_kind="userdata_file",
            source_id=source_id,
            display_name=file_path.name,
            file_path=file_path,
            path=f"userdata/{source_id}",
        )
        if record is not None:
            records.append(record)
    return records


def list_importable_workflows() -> list[dict[str, Any]]:
    records = [*_list_workflow_templates(), *_list_userdata_workflows()]
    records.sort(
        key=lambda record: (
            record.modified_at or "",
            record.display_name.lower(),
        ),
        reverse=True,
    )
    return [record.to_summary() for record in records]


def _resolve_workflow_template_record(source_id: str) -> ImportableWorkflowRecord:
    for record in _list_workflow_templates():
        if record.source_id == source_id:
            return record
    raise FileNotFoundError(f"Workflow template '{source_id}' was not found")


def _resolve_userdata_record(source_id: str) -> ImportableWorkflowRecord:
    root = _get_userdata_root().resolve()
    relative_path = _normalize_userdata_source_id(source_id)
    file_path = (root / relative_path).resolve()
    if root not in file_path.parents and file_path != root:
        raise ValueError("sourceId must remain inside the userdata directory")
    if not file_path.is_file():
        raise FileNotFoundError(f"Userdata workflow '{source_id}' was not found")

    record = _workflow_record_from_file(
        source_kind="userdata_file",
        source_id=relative_path.as_posix(),
        display_name=file_path.name,
        file_path=file_path,
        path=f"userdata/{relative_path.as_posix()}",
    )
    if record is not None:
        return record
    if not _is_json_file(file_path):
        raise ValueError(f"Userdata workflow '{source_id}' is not a valid JSON workflow")

    return ImportableWorkflowRecord(
        source_kind="userdata_file",
        source_id=relative_path.as_posix(),
        display_name=file_path.name,
        file_path=file_path,
        path=f"userdata/{relative_path.as_posix()}",
        modified_at=_to_iso_modified_at(file_path),
    )


def get_importable_workflow_content(
	source_kind: str,
	source_id: str,
) -> dict[str, Any]:
    if source_kind == "workflow_template":
        record = _resolve_workflow_template_record(source_id)
    elif source_kind == "userdata_file":
        record = _resolve_userdata_record(source_id)
    else:
        raise ValueError("sourceKind must be 'workflow_template' or 'userdata_file'")

    try:
        workflow = _read_json_object(record.file_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Workflow '{source_id}' could not be read as valid UTF-8 JSON"
        ) from exc

    return _build_fetch_payload(record, workflow)


def _register_routes() -> None:
    try:
        from aiohttp import web  # type: ignore
        from server import PromptServer  # type: ignore
    except ImportError:
        return

    prompt_server = getattr(PromptServer, "instance", None)
    routes = getattr(prompt_server, "routes", None)
    if routes is None:
        return

    @routes.get(WORKFLOW_IMPORT_LIST_PATH)
    async def list_importable_workflows_route(_request):
        return web.json_response({"workflows": list_importable_workflows()})

    @routes.get(WORKFLOW_IMPORT_CONTENT_PATH)
    async def get_importable_workflow_content_route(request):
        query = request.rel_url.query
        source_kind = query.get("sourceKind")
        source_id = query.get("sourceId")
        if not source_kind or not source_id:
            return web.json_response(
                {"error": "sourceKind and sourceId are required"},
                status=400,
            )

        try:
            payload = get_importable_workflow_content(source_kind, source_id)
            runtime_format = payload.get("runtimeFormat")
            workflow = payload.get("workflow")
            if runtime_format == "api_prompt" and isinstance(workflow, dict):
                await _validate_runtime_api_prompt(workflow)
        except WorkflowImportConversionError as exc:
            return web.json_response(
                {
                    "error": {
                        "code": exc.code,
                        "message": str(exc),
                    }
                },
                status=422,
            )
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except FileNotFoundError as exc:
            return web.json_response({"error": str(exc)}, status=404)

        return web.json_response(payload)


_register_routes()