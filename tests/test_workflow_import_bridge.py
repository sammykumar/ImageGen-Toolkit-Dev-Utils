import asyncio
import importlib
import json
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
                "originalFormat": "api_prompt",
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

    def test_content_route_returns_400_when_params_are_missing(self):
        routes = _FakeRoutes()
        _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/importable/content"]

        response = asyncio.run(handler(_FakeRequest({})))

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["payload"],
            {"error": "sourceKind and sourceId are required"},
        )

    def test_content_route_returns_400_for_invalid_source_kind(self):
        routes = _FakeRoutes()
        _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/importable/content"]

        response = asyncio.run(
            handler(
                _FakeRequest(
                    {
                        "sourceKind": "unsupported_kind",
                        "sourceId": "workflows/selected.json",
                    }
                )
            )
        )

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["payload"],
            {
                "error": "sourceKind must be 'workflow_template' or 'userdata_file'"
            },
        )

    def test_content_route_returns_400_for_userdata_traversal_attempt(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/importable/content"]

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            (userdata_root / "workflows").mkdir(parents=True, exist_ok=True)

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                response = asyncio.run(
                    handler(
                        _FakeRequest(
                            {
                                "sourceKind": "userdata_file",
                                "sourceId": "../outside.json",
                            }
                        )
                    )
                )

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["payload"],
            {"error": "sourceId must be a relative userdata path"},
        )

    def test_content_route_returns_404_for_missing_userdata_file(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/importable/content"]

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            (userdata_root / "workflows").mkdir(parents=True, exist_ok=True)

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                response = asyncio.run(
                    handler(
                        _FakeRequest(
                            {
                                "sourceKind": "userdata_file",
                                "sourceId": "workflows/missing.json",
                            }
                        )
                    )
                )

        self.assertEqual(response["status"], 404)
        self.assertEqual(
            response["payload"],
            {"error": "Userdata workflow 'workflows/missing.json' was not found"},
        )

    def test_get_importable_workflow_content_serves_workflow_json_without_converting(self):
        module = importlib.import_module("workflow_import_bridge")

        workflow_json = {
            "nodes": [
                {
                    "id": 1,
                    "title": "Load Image",
                    "type": "LoadImage",
                    "mode": 0,
                    "inputs": [
                        {
                            "name": "image",
                            "type": "STRING",
                            "widget": {"name": "image"},
                        }
                    ],
                    "widgets_values": ["input.png"],
                },
            ],
            "links": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "editor-export.json").write_text(
                json.dumps(workflow_json),
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                result = module.get_importable_workflow_content(
                    "userdata_file",
                    "workflows/editor-export.json",
                )

        self.assertEqual(result["workflow"], workflow_json)
        self.assertEqual(result["formatHint"], "workflow_json")
        self.assertEqual(result["originalFormat"], "workflow_json")
        self.assertNotIn("runtimeFormat", result)
        self.assertNotIn("conversion", result)
        self.assertNotIn("provenance", result)

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


class WorkflowJsonConversionTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("workflow_import_bridge")

    def _convert(self, workflow: dict, nodes_map: dict) -> dict:
        return self.module._convert_workflow_json_to_api_prompt(
            workflow, nodes_map=nodes_map
        )

    def test_primitive_widgets_consumed_from_widgets_values(self):
        class MockNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {
                        "my_int": ("INT", {}),
                        "my_float": ("FLOAT", {}),
                        "my_str": ("STRING", {}),
                    },
                    "optional": {},
                }

        workflow = {
            "nodes": [
                {
                    "id": 10,
                    "type": "MockNode",
                    "mode": 0,
                    "inputs": [],
                    "widgets_values": [42, 3.14, "hello"],
                }
            ],
            "links": [],
        }
        result = self._convert(workflow, {"MockNode": MockNode})
        self.assertEqual(result["10"]["inputs"]["my_int"], 42)
        self.assertEqual(result["10"]["inputs"]["my_float"], 3.14)
        self.assertEqual(result["10"]["inputs"]["my_str"], "hello")

    def test_combo_widget_consumed_from_widgets_values(self):
        class MockNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {
                        "sampler_name": (["euler", "dpm_2", "lms"], {}),
                    },
                    "optional": {},
                }

        workflow = {
            "nodes": [
                {
                    "id": 5,
                    "type": "MockNode",
                    "mode": 0,
                    "inputs": [],
                    "widgets_values": ["euler"],
                }
            ],
            "links": [],
        }
        result = self._convert(workflow, {"MockNode": MockNode})
        self.assertEqual(result["5"]["inputs"]["sampler_name"], "euler")

    def test_link_type_input_resolved_from_links_array(self):
        class SrcNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        class DstNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {"model": ("MODEL", {})},
                    "optional": {},
                }

        workflow = {
            "nodes": [
                {"id": 1, "type": "SrcNode", "mode": 0, "inputs": [], "widgets_values": []},
                {
                    "id": 2,
                    "type": "DstNode",
                    "mode": 0,
                    "inputs": [{"name": "model", "type": "MODEL", "link": 10}],
                    "widgets_values": [],
                },
            ],
            "links": [[10, 1, 0, 2, 0, "MODEL"]],
        }
        result = self._convert(workflow, {"SrcNode": SrcNode, "DstNode": DstNode})
        self.assertEqual(result["2"]["inputs"]["model"], ["1", 0])

    def test_widget_converted_to_link_emits_link_ref(self):
        class SrcNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {"out": ("STRING", {})}, "optional": {}}

        class DstNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {"text": ("STRING", {})},
                    "optional": {},
                }

        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "SrcNode",
                    "mode": 0,
                    "inputs": [],
                    "widgets_values": ["src_value"],
                },
                {
                    "id": 2,
                    "type": "DstNode",
                    "mode": 0,
                    "inputs": [
                        {
                            "name": "text",
                            "type": "STRING",
                            "link": 20,
                            "widget": {"name": "text"},
                        }
                    ],
                    "widgets_values": ["widget_fallback"],
                },
            ],
            "links": [[20, 1, 0, 2, 0, "STRING"]],
        }
        result = self._convert(workflow, {"SrcNode": SrcNode, "DstNode": DstNode})
        self.assertEqual(result["2"]["inputs"]["text"], ["1", 0])

    def test_reroute_chain_resolved(self):
        class SrcNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        class DstNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {"image": ("IMAGE", {})},
                    "optional": {},
                }

        workflow = {
            "nodes": [
                {"id": 1, "type": "SrcNode", "mode": 0, "inputs": [], "widgets_values": []},
                {
                    "id": 2,
                    "type": "Reroute",
                    "mode": 0,
                    "inputs": [{"name": "value", "type": "*", "link": 10}],
                    "widgets_values": [],
                },
                {
                    "id": 3,
                    "type": "DstNode",
                    "mode": 0,
                    "inputs": [{"name": "image", "type": "IMAGE", "link": 20}],
                    "widgets_values": [],
                },
            ],
            "links": [
                [10, 1, 0, 2, 0, "*"],
                [20, 2, 0, 3, 0, "IMAGE"],
            ],
        }
        result = self._convert(workflow, {"SrcNode": SrcNode, "DstNode": DstNode})
        self.assertNotIn("2", result)
        self.assertEqual(result["3"]["inputs"]["image"], ["1", 0])

    def test_bypass_nodes_skipped(self):
        class MockNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        workflow = {
            "nodes": [
                {"id": 99, "type": "MockNode", "mode": 4, "inputs": [], "widgets_values": []}
            ],
            "links": [],
        }
        result = self._convert(workflow, {"MockNode": MockNode})
        self.assertNotIn("99", result)

    def test_never_nodes_skipped(self):
        class MockNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        workflow = {
            "nodes": [
                {"id": 77, "type": "MockNode", "mode": 2, "inputs": [], "widgets_values": []}
            ],
            "links": [],
        }
        result = self._convert(workflow, {"MockNode": MockNode})
        self.assertNotIn("77", result)

    def test_unknown_class_node_treated_as_transparent_for_chain_resolution(self):
        """Nodes whose class is not in NODE_CLASS_MAPPINGS must be treated as
        transparent so that downstream nodes' link references chain through them
        to the real source (same behavior as Reroute nodes)."""

        class SrcNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        class DstNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {"image": ("IMAGE", {})}, "optional": {}}

        workflow = {
            "nodes": [
                # Real source node (class known)
                {"id": 10, "type": "SrcNode", "mode": 0, "inputs": [], "widgets_values": []},
                # Unknown-class pass-through (e.g. a custom Reroute variant)
                {
                    "id": 11,
                    "type": "SomeCustomRerouteVariant",
                    "mode": 0,
                    "inputs": [{"name": "value", "type": "*", "link": 100}],
                    "widgets_values": [],
                },
                # Destination node (class known)
                {
                    "id": 12,
                    "type": "DstNode",
                    "mode": 0,
                    "inputs": [{"name": "image", "type": "IMAGE", "link": 200}],
                    "widgets_values": [],
                },
            ],
            "links": [
                [100, 10, 0, 11, 0, "*"],
                [200, 11, 0, 12, 0, "IMAGE"],
            ],
        }

        result = self._convert(workflow, {"SrcNode": SrcNode, "DstNode": DstNode})

        # Unknown-class node (11) must NOT appear in output
        self.assertNotIn("11", result)
        # DstNode's image must resolve through the unknown node to the real source
        self.assertEqual(result["12"]["inputs"]["image"], ["10", 0])

    def test_chain_resolution_uses_links_array_when_node_inputs_have_null_link(self):
        """When a custom reroute node's LiteGraph inputs[] carries link=null
        (or inputs is empty), chain resolution must still succeed by using the
        workflow links array (input_link_map) rather than nodes.inputs[].link."""

        class SrcNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        class DstNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {"image": ("IMAGE", {})}, "optional": {}}

        workflow = {
            "nodes": [
                {"id": 10, "type": "SrcNode", "mode": 0, "inputs": [], "widgets_values": []},
                # Custom reroute: inputs[] exists but link is null — simulates
                # the real-world failure seen with nodes 5160/5168/5178/5179.
                {
                    "id": 11,
                    "type": "SomeCustomRerouteVariant",
                    "mode": 0,
                    "inputs": [{"name": "value", "type": "*", "link": None}],
                    "widgets_values": [],
                },
                {
                    "id": 12,
                    "type": "DstNode",
                    "mode": 0,
                    "inputs": [{"name": "image", "type": "IMAGE", "link": 200}],
                    "widgets_values": [],
                },
            ],
            "links": [
                # link 100: 10→11 (src→reroute), link 200: 11→12 (reroute→dst)
                [100, 10, 0, 11, 0, "*"],
                [200, 11, 0, 12, 0, "IMAGE"],
            ],
        }

        result = self._convert(workflow, {"SrcNode": SrcNode, "DstNode": DstNode})

        self.assertNotIn("11", result)
        # Must resolve through node 11 (whose inputs[].link is null) using links array
        self.assertEqual(result["12"]["inputs"]["image"], ["10", 0])

    def test_chain_resolution_uses_links_array_when_node_has_empty_inputs(self):
        """Same as above but the custom reroute has inputs=[] entirely."""

        class SrcNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        class DstNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {"data": ("IMAGE", {})}, "optional": {}}

        workflow = {
            "nodes": [
                {"id": 20, "type": "SrcNode", "mode": 0, "inputs": [], "widgets_values": []},
                # Custom reroute: no inputs array at all
                {"id": 21, "type": "CustomFwdNode", "mode": 0, "widgets_values": []},
                {
                    "id": 22,
                    "type": "DstNode",
                    "mode": 0,
                    "inputs": [{"name": "data", "type": "IMAGE", "link": 300}],
                    "widgets_values": [],
                },
            ],
            "links": [
                [50, 20, 0, 21, 0, "*"],
                [300, 21, 0, 22, 0, "IMAGE"],
            ],
        }

        result = self._convert(workflow, {"SrcNode": SrcNode, "DstNode": DstNode})

        self.assertNotIn("21", result)
        self.assertEqual(result["22"]["inputs"]["data"], ["20", 0])

    def test_widget_default_used_when_widgets_values_exhausted(self):
        """When widgets_values is empty (e.g., all widgets converted to linked
        inputs in LiteGraph), fall back to the INPUT_TYPES config default."""

        class NodeWithDefaults:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {
                        "count": ("INT", {"default": 42}),
                        "label": ("STRING", {"default": "hello"}),
                        "rate": ("FLOAT", {"default": 3.14}),
                        "flag": ("BOOLEAN", {"default": True}),
                    },
                    "optional": {},
                }

        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "NodeWithDefaults",
                    "mode": 0,
                    "inputs": [],
                    "widgets_values": [],   # empty — simulate all-linked LiteGraph node
                }
            ],
            "links": [],
        }

        result = self._convert(workflow, {"NodeWithDefaults": NodeWithDefaults})

        self.assertEqual(result["1"]["inputs"]["count"], 42)
        self.assertEqual(result["1"]["inputs"]["label"], "hello")
        self.assertAlmostEqual(result["1"]["inputs"]["rate"], 3.14)
        self.assertEqual(result["1"]["inputs"]["flag"], True)

    def test_unknown_node_type_skipped(self):
        workflow = {
            "nodes": [
                {
                    "id": 5,
                    "type": "NonExistentNode",
                    "mode": 0,
                    "inputs": [],
                    "widgets_values": [],
                }
            ],
            "links": [],
        }
        result = self._convert(workflow, {})
        self.assertNotIn("5", result)

    def test_meta_title_uses_node_title(self):
        class MockNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        workflow = {
            "nodes": [
                {
                    "id": 7,
                    "type": "NodeType",
                    "title": "My Node",
                    "mode": 0,
                    "inputs": [],
                    "widgets_values": [],
                }
            ],
            "links": [],
        }
        result = self._convert(workflow, {"NodeType": MockNode})
        self.assertEqual(result["7"]["_meta"]["title"], "My Node")

    def test_meta_title_falls_back_to_type(self):
        class MockNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {"required": {}, "optional": {}}

        workflow = {
            "nodes": [
                {
                    "id": 7,
                    "type": "NodeType",
                    "mode": 0,
                    "inputs": [],
                    "widgets_values": [],
                }
            ],
            "links": [],
        }
        result = self._convert(workflow, {"NodeType": MockNode})
        self.assertEqual(result["7"]["_meta"]["title"], "NodeType")

    def test_vhs_formats_extra_widget_slots_consumed_and_named(self):
        """COMBO with 'formats' config (VHS pattern): format-specific extra widgets
        must be consumed from widgets_values and added to node_inputs with their names.
        Widgets declared after 'format' in INPUT_TYPES (pingpong, save_output) must
        read from the correct positions, not from the format-specific slots."""

        class VHSCombineNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {
                        "images": ("IMAGE",),
                        "frame_rate": ("FLOAT", {"default": 8}),
                        "loop_count": ("INT", {"default": 0}),
                        "filename_prefix": ("STRING", {"default": "AnimateDiff"}),
                        "format": (
                            ["image/gif", "video/h264-mp4"],
                            {
                                "formats": {
                                    "video/h264-mp4": [
                                        ["pix_fmt", ["yuv420p", "yuv420p10le"]],
                                        ["crf", "INT", {"default": 19}],
                                        ["save_metadata", "BOOLEAN", {"default": True}],
                                        ["trim_to_audio", "BOOLEAN", {"default": False}],
                                    ]
                                }
                            },
                        ),
                        "pingpong": ("BOOLEAN", {"default": False}),
                        "save_output": ("BOOLEAN", {"default": True}),
                    },
                    "optional": {
                        "audio": ("AUDIO",),
                    },
                }

        # widgets_values mirrors LiteGraph order: frame_rate, loop_count,
        # filename_prefix, format, <4 format extras>, pingpong, save_output
        workflow = {
            "nodes": [
                {
                    "id": 5175,
                    "type": "VHS_VideoCombine",
                    "mode": 0,
                    "inputs": [
                        {"name": "images", "link": 1},
                        {"name": "audio", "link": 2},
                    ],
                    "widgets_values": [
                        24,
                        0,
                        "video/big",
                        "video/h264-mp4",
                        "yuv420p",
                        16,
                        True,
                        False,
                        False,
                        True,
                    ],
                }
            ],
            "links": [
                [1, 100, 0, 5175, 0],
                [2, 200, 0, 5175, 1],
            ],
        }

        result = self._convert(workflow, {"VHS_VideoCombine": VHSCombineNode})
        node = result["5175"]["inputs"]

        # Core widget values
        self.assertEqual(node["frame_rate"], 24)
        self.assertEqual(node["loop_count"], 0)
        self.assertEqual(node["filename_prefix"], "video/big")
        self.assertEqual(node["format"], "video/h264-mp4")
        # Format-specific extra widgets present and correctly named
        self.assertEqual(node["pix_fmt"], "yuv420p")
        self.assertEqual(node["crf"], 16)
        self.assertEqual(node["save_metadata"], True)
        self.assertEqual(node["trim_to_audio"], False)
        # Widgets after format-extras read from correct positions
        self.assertEqual(node["pingpong"], False)
        self.assertEqual(node["save_output"], True)
        # Link inputs resolved
        self.assertEqual(node["images"], ["100", 0])
        self.assertEqual(node["audio"], ["200", 0])

    def test_vhs_formats_unknown_format_no_extra_slots(self):
        """COMBO with 'formats' config: an unknown/unregistered format value produces
        no extra widget slots and does not shift subsequent widget reads."""

        class VHSCombineNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {
                        "format": (
                            ["image/gif", "video/h264-mp4"],
                            {"formats": {"video/h264-mp4": [["crf", "INT"]]}},
                        ),
                        "pingpong": ("BOOLEAN", {"default": False}),
                    }
                }

        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "VHSNode",
                    "mode": 0,
                    "inputs": [],
                    # format=image/gif (no extras), then pingpong=True
                    "widgets_values": ["image/gif", True],
                }
            ],
            "links": [],
        }

        result = self._convert(workflow, {"VHSNode": VHSCombineNode})
        node = result["1"]["inputs"]
        self.assertEqual(node["format"], "image/gif")
        self.assertEqual(node["pingpong"], True)

    def test_dynamic_combo_v3_sub_inputs_consumed_and_named(self):
        """COMFY_DYNAMICCOMBO_V3 inputs expand sub-inputs based on the selected
        option. The sub-inputs must be consumed from widgets_values and stored with
        dot-prefixed names (e.g. resize_type.width)."""

        class ResizeNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {
                        "input": ("IMAGE",),
                        "resize_type": (
                            "COMFY_DYNAMICCOMBO_V3",
                            {
                                "options": [
                                    {
                                        "key": "scale dimensions",
                                        "inputs": {
                                            "required": {
                                                "width": ("INT", {"default": 512}),
                                                "height": ("INT", {"default": 512}),
                                                "crop": (
                                                    "COMBO",
                                                    {
                                                        "options": [
                                                            "disabled",
                                                            "center",
                                                        ]
                                                    },
                                                ),
                                            }
                                        },
                                    },
                                    {
                                        "key": "scale by multiplier",
                                        "inputs": {
                                            "required": {
                                                "multiplier": (
                                                    "FLOAT",
                                                    {"default": 1.0},
                                                )
                                            }
                                        },
                                    },
                                ]
                            },
                        ),
                        "scale_method": (
                            "COMBO",
                            {"options": ["nearest-exact", "bilinear", "lanczos"]},
                        ),
                    }
                }

        # widgets_values: resize_type="scale dimensions", width=720, height=1280,
        # crop="center", scale_method="lanczos"
        workflow = {
            "nodes": [
                {
                    "id": 5153,
                    "type": "ResizeImageMaskNode",
                    "mode": 0,
                    "inputs": [{"name": "input", "link": 10}],
                    "widgets_values": [
                        "scale dimensions",
                        720,
                        1280,
                        "center",
                        "lanczos",
                    ],
                }
            ],
            "links": [[10, 50, 0, 5153, 0]],
        }

        result = self._convert(workflow, {"ResizeImageMaskNode": ResizeNode})
        node = result["5153"]["inputs"]

        # Parent DYNAMICCOMBO value
        self.assertEqual(node["resize_type"], "scale dimensions")
        # Sub-inputs with dot-prefixed names
        self.assertEqual(node["resize_type.width"], 720)
        self.assertEqual(node["resize_type.height"], 1280)
        self.assertEqual(node["resize_type.crop"], "center")
        # Widget AFTER the dynamic combo reads from correct position
        self.assertEqual(node["scale_method"], "lanczos")
        # Link input
        self.assertEqual(node["input"], ["50", 0])

    def test_dynamic_combo_v3_different_option_consumes_correct_slots(self):
        """Selecting a different DYNAMICCOMBO option expands different sub-inputs."""

        class ResizeNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {
                        "resize_type": (
                            "COMFY_DYNAMICCOMBO_V3",
                            {
                                "options": [
                                    {
                                        "key": "scale by multiplier",
                                        "inputs": {
                                            "required": {
                                                "multiplier": (
                                                    "FLOAT",
                                                    {"default": 1.0},
                                                )
                                            }
                                        },
                                    }
                                ]
                            },
                        ),
                        "scale_method": ("COMBO", {"options": ["lanczos"]}),
                    }
                }

        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "ResizeNode",
                    "mode": 0,
                    "inputs": [],
                    # resize_type="scale by multiplier", multiplier=2.0, scale_method="lanczos"
                    "widgets_values": ["scale by multiplier", 2.0, "lanczos"],
                }
            ],
            "links": [],
        }

        result = self._convert(workflow, {"ResizeNode": ResizeNode})
        node = result["1"]["inputs"]
        self.assertEqual(node["resize_type"], "scale by multiplier")
        self.assertEqual(node["resize_type.multiplier"], 2.0)
        self.assertEqual(node["scale_method"], "lanczos")

    def test_dynamic_combo_v3_unknown_option_skips_sub_inputs(self):
        """An unrecognised DYNAMICCOMBO value gracefully skips sub-input expansion."""

        class ResizeNode:
            @classmethod
            def INPUT_TYPES(cls):
                return {
                    "required": {
                        "resize_type": (
                            "COMFY_DYNAMICCOMBO_V3",
                            {"options": [{"key": "scale dimensions", "inputs": {}}]},
                        ),
                        "scale_method": ("COMBO", {"options": ["lanczos"]}),
                    }
                }

        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "ResizeNode",
                    "mode": 0,
                    "inputs": [],
                    # "unknown option" is not in options — no sub-inputs consumed
                    "widgets_values": ["unknown option", "lanczos"],
                }
            ],
            "links": [],
        }

        result = self._convert(workflow, {"ResizeNode": ResizeNode})
        node = result["1"]["inputs"]
        self.assertEqual(node["resize_type"], "unknown option")
        self.assertEqual(node["scale_method"], "lanczos")

    def test_get_importable_workflow_content_converts_workflow_json_file(self):
        module = importlib.import_module("workflow_import_bridge")

        mock_api_prompt = {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": "test.png"},
                "_meta": {"title": "LoadImage"},
            }
        }
        workflow_json = {
            "nodes": [{"id": 1, "type": "LoadImage", "mode": 0}],
            "links": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "test.json").write_text(
                json.dumps(workflow_json),
                encoding="utf-8",
            )

            with mock.patch.object(
                module, "_get_userdata_root", return_value=userdata_root
            ), mock.patch.object(
                module,
                "_convert_workflow_json_to_api_prompt",
                return_value=mock_api_prompt,
            ):
                result = module.get_importable_workflow_content(
                    "userdata_file",
                    "workflows/test.json",
                )

        self.assertEqual(result["formatHint"], "api_prompt")
        self.assertEqual(result["originalFormat"], "workflow_json")
