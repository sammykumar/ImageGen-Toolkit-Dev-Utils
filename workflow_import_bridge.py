from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


WORKFLOW_IMPORT_LIST_PATH = "/api/image-gen-toolkit/workflows/importable"
WORKFLOW_IMPORT_CONTENT_PATH = "/api/image-gen-toolkit/workflows/importable/content"
USERDATA_WORKFLOWS_PREFIX = "workflows"


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
    except (OSError, json.JSONDecodeError):
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
    if record is None:
        raise ValueError(f"Userdata workflow '{source_id}' is not a valid JSON workflow")
    return record


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

    workflow = _read_json_object(record.file_path)
    payload: dict[str, Any] = {
        "summary": record.to_summary(),
        "workflow": workflow,
        "formatHint": record.format_hint or _detect_format_hint(workflow),
    }
    if payload["formatHint"] == "unknown":
        payload["warnings"] = ["Could not infer whether this JSON is an API prompt or workflow export."]
    return payload


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
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except FileNotFoundError as exc:
            return web.json_response({"error": str(exc)}, status=404)

        return web.json_response(payload)


_register_routes()