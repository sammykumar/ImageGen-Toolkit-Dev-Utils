import asyncio
import importlib
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class WorkflowImportBridgeTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop("workflow_import_bridge", None)

    def test_routes_register_with_prompt_server_route_table(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)

        self.assertIsNotNone(module)
        self.assertIn(
			"/api/image-gen-toolkit/workflows/importable",
            routes.handlers,
        )
        self.assertIn(
			"/api/image-gen-toolkit/workflows/importable/content",
            routes.handlers,
        )

    def test_list_importable_workflows_returns_individually_selectable_catalog(self):
        module = importlib.import_module("workflow_import_bridge")

        with mock.patch.object(module, "_list_workflow_templates") as list_templates_mock, mock.patch.object(
            module,
            "_list_userdata_workflows",
        ) as list_userdata_mock:
            list_templates_mock.return_value = [
                module.ImportableWorkflowRecord(
                    source_kind="workflow_template",
                    source_id="wan-vace:wan-vace-api.json",
                    display_name="WAN VACE",
                    file_path=pathlib.Path("/tmp/wan-vace-api.json"),
                    modified_at="2026-04-11T12:00:00Z",
                    format_hint="api_prompt",
                ),
            ]
            list_userdata_mock.return_value = [
                module.ImportableWorkflowRecord(
                    source_kind="userdata_file",
                    source_id="workflows/export.json",
                    display_name="export.json",
                    file_path=pathlib.Path("/tmp/export.json"),
                    path="userdata/workflows/export.json",
                    modified_at="2026-04-10T12:00:00Z",
                    format_hint="workflow_json",
                ),
            ]

            result = module.list_importable_workflows()

        self.assertEqual(
            result,
            [
                {
                    "sourceKind": "workflow_template",
                    "sourceId": "wan-vace:wan-vace-api.json",
                    "displayName": "WAN VACE",
                    "modifiedAt": "2026-04-11T12:00:00Z",
                    "formatHint": "api_prompt",
                },
                {
                    "sourceKind": "userdata_file",
                    "sourceId": "workflows/export.json",
                    "displayName": "export.json",
                    "path": "userdata/workflows/export.json",
                    "modifiedAt": "2026-04-10T12:00:00Z",
                    "formatHint": "workflow_json",
                },
            ],
        )

    def test_get_importable_workflow_content_returns_only_requested_userdata_workflow(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "selected.json").write_text(
                '{"1": {"class_type": "LoadImage", "inputs": {}}}',
                encoding="utf-8",
            )
            (workflows_dir / "other.json").write_text(
                '{"nodes": [], "links": []}',
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                result = module.get_importable_workflow_content(
                    "userdata_file",
                    "workflows/selected.json",
                )

        self.assertEqual(
            result,
            {
                "summary": {
                    "sourceKind": "userdata_file",
                    "sourceId": "workflows/selected.json",
                    "displayName": "selected.json",
                    "path": "userdata/workflows/selected.json",
                    "modifiedAt": result["summary"]["modifiedAt"],
                    "formatHint": "api_prompt",
                },
                "workflow": {"1": {"class_type": "LoadImage", "inputs": {}}},
                "formatHint": "api_prompt",
            },
        )

    def test_list_importable_workflows_skips_userdata_file_with_invalid_utf8(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "valid.json").write_text(
                '{"1": {"class_type": "LoadImage", "inputs": {}}}',
                encoding="utf-8",
            )
            (workflows_dir / "broken.json").write_bytes(b"\x80\x81not-utf8")

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root), mock.patch.object(
                module,
                "_list_workflow_templates",
                return_value=[],
            ):
                result = module.list_importable_workflows()

        self.assertEqual(
            result,
            [
                {
                    "sourceKind": "userdata_file",
                    "sourceId": "workflows/valid.json",
                    "displayName": "valid.json",
                    "path": "userdata/workflows/valid.json",
                    "modifiedAt": result[0]["modifiedAt"],
                    "formatHint": "api_prompt",
                }
            ],
        )

    def test_list_importable_workflows_skips_userdata_file_with_invalid_json(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "valid.json").write_text(
                '{"1": {"class_type": "LoadImage", "inputs": {}}}',
                encoding="utf-8",
            )
            (workflows_dir / "broken.json").write_text(
                '{"nodes": [}',
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root), mock.patch.object(
                module,
                "_list_workflow_templates",
                return_value=[],
            ):
                result = module.list_importable_workflows()

        self.assertEqual(
            result,
            [
                {
                    "sourceKind": "userdata_file",
                    "sourceId": "workflows/valid.json",
                    "displayName": "valid.json",
                    "path": "userdata/workflows/valid.json",
                    "modifiedAt": result[0]["modifiedAt"],
                    "formatHint": "api_prompt",
                }
            ],
        )

    def test_list_importable_workflows_skips_userdata_file_when_read_fails(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            valid_path = workflows_dir / "valid.json"
            valid_path.write_text(
                '{"1": {"class_type": "LoadImage", "inputs": {}}}',
                encoding="utf-8",
            )
            broken_path = workflows_dir / "broken.json"
            broken_path.write_text(
                '{"1": {"class_type": "LoadImage", "inputs": {}}}',
                encoding="utf-8",
            )
            broken_path_resolved = broken_path.resolve()

            original_read_json_object = module._read_json_object

            def read_json_object_side_effect(file_path):
                if file_path.resolve() == broken_path_resolved:
                    raise OSError("permission denied")
                return original_read_json_object(file_path)

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root), mock.patch.object(
                module,
                "_list_workflow_templates",
                return_value=[],
            ), mock.patch.object(module, "_read_json_object", side_effect=read_json_object_side_effect):
                result = module.list_importable_workflows()

        self.assertEqual(
            result,
            [
                {
                    "sourceKind": "userdata_file",
                    "sourceId": "workflows/valid.json",
                    "displayName": "valid.json",
                    "path": "userdata/workflows/valid.json",
                    "modifiedAt": result[0]["modifiedAt"],
                    "formatHint": "api_prompt",
                }
            ],
        )

    def test_get_importable_workflow_content_raises_clear_error_for_invalid_utf8(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "broken.json").write_bytes(b"\x80\x81not-utf8")

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                with self.assertRaisesRegex(
                    ValueError,
                    "Workflow 'workflows/broken.json' could not be read as valid UTF-8 JSON",
                ):
                    module.get_importable_workflow_content(
                        "userdata_file",
                        "workflows/broken.json",
                    )

    def test_get_importable_workflow_content_raises_clear_error_for_invalid_json(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "broken.json").write_text(
                '{"nodes": [}',
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                with self.assertRaisesRegex(
                    ValueError,
                    "Workflow 'workflows/broken.json' could not be read as valid UTF-8 JSON",
                ):
                    module.get_importable_workflow_content(
                        "userdata_file",
                        "workflows/broken.json",
                    )

    def test_get_importable_workflow_content_raises_clear_error_when_read_fails(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            broken_path = workflows_dir / "broken.json"
            broken_path.write_text(
                '{"1": {"class_type": "LoadImage", "inputs": {}}}',
                encoding="utf-8",
            )
            broken_path_resolved = broken_path.resolve()

            original_read_json_object = module._read_json_object

            def read_json_object_side_effect(file_path):
                if file_path.resolve() == broken_path_resolved:
                    raise OSError("permission denied")
                return original_read_json_object(file_path)

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root), mock.patch.object(
                module,
                "_read_json_object",
                side_effect=read_json_object_side_effect,
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "Workflow 'workflows/broken.json' could not be read as valid UTF-8 JSON",
                ):
                    module.get_importable_workflow_content(
                        "userdata_file",
                        "workflows/broken.json",
                    )

    def test_list_route_returns_200_when_userdata_contains_invalid_json(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/importable"]

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "valid.json").write_text(
                '{"1": {"class_type": "LoadImage", "inputs": {}}}',
                encoding="utf-8",
            )
            (workflows_dir / "broken.json").write_text(
                '{"nodes": [}',
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root), mock.patch.object(
                module,
                "_list_workflow_templates",
                return_value=[],
            ):
                response = asyncio.run(handler(_FakeRequest({})))

        self.assertEqual(response["status"], 200)
        self.assertEqual(
            response["payload"],
            {
                "workflows": [
                    {
                        "sourceKind": "userdata_file",
                        "sourceId": "workflows/valid.json",
                        "displayName": "valid.json",
                        "path": "userdata/workflows/valid.json",
                        "modifiedAt": response["payload"]["workflows"][0]["modifiedAt"],
                        "formatHint": "api_prompt",
                    }
                ]
            },
        )

    def test_content_route_returns_clear_400_for_invalid_json_userdata_file(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/importable/content"]

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "broken.json").write_text(
                '{"nodes": [}',
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                response = asyncio.run(
                    handler(
                        _FakeRequest(
                            {
                                "sourceKind": "userdata_file",
                                "sourceId": "workflows/broken.json",
                            }
                        )
                    )
                )

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["payload"],
            {
                "error": "Workflow 'workflows/broken.json' could not be read as valid UTF-8 JSON"
            },
        )

    def test_content_route_reads_only_specific_requested_workflow(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/importable/content"]

        with mock.patch.object(module, "get_importable_workflow_content") as get_content_mock:
            get_content_mock.return_value = {
                "summary": {
                    "sourceKind": "workflow_template",
                    "sourceId": "wan-vace:template.json",
                    "displayName": "WAN VACE",
                },
                "workflow": {"1": {"class_type": "LoadImage", "inputs": {}}},
                "formatHint": "api_prompt",
            }

            response = asyncio.run(
                handler(
                    _FakeRequest(
                        {
                            "sourceKind": "workflow_template",
                            "sourceId": "wan-vace:template.json",
                        }
                    )
                )
            )

        get_content_mock.assert_called_once_with(
            "workflow_template",
            "wan-vace:template.json",
        )
        self.assertEqual(response["status"], 200)
        self.assertEqual(
            response["payload"]["summary"]["sourceId"],
            "wan-vace:template.json",
        )


class _FakeRequest:
    def __init__(self, query):
        self.rel_url = types.SimpleNamespace(query=query)


class _FakeRoutes:
    def __init__(self):
        self.handlers = {}

    def get(self, path):
        def decorator(handler):
            self.handlers[path] = handler
            return handler

        return decorator


def _import_bridge_with_route_stubs(routes):
    sys.modules.pop("workflow_import_bridge", None)
    server_module = types.ModuleType("server")
    server_module.PromptServer = types.SimpleNamespace(
        instance=types.SimpleNamespace(routes=routes)
    )
    aiohttp_module = types.ModuleType("aiohttp")
    aiohttp_module.web = _FakeWebModule()

    with mock.patch.dict(
        sys.modules,
        {
            "server": server_module,
            "aiohttp": aiohttp_module,
        },
    ):
        return importlib.import_module("workflow_import_bridge")


class _FakeWebModule:
    @staticmethod
    def json_response(payload, status=200):
        return {"payload": payload, "status": status}
