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
        self.assertIn(
            "/api/image-gen-toolkit/workflows/published-api",
            routes.handlers,
        )

    def test_publish_route_stores_export_keyed_by_source_identity(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/published-api"]

        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "KSampler",
                    "mode": 0,
                    "inputs": [{"name": "seed", "type": "INT", "widget": {"name": "seed"}}],
                    "widgets_values": [42],
                }
            ],
            "links": [],
        }
        api_prompt = {"1": {"class_type": "KSampler", "inputs": {"seed": 42}}}

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                response = asyncio.run(
                    handler(
                        _FakePostRequest(
                            {
                                "sourceKind": "userdata_file",
                                "sourceId": "workflows/my-workflow.json",
                                "workflow": workflow,
                                "apiPrompt": api_prompt,
                            }
                        )
                    )
                )

            self.assertEqual(response["status"], 200)
            self.assertTrue(response["payload"]["ok"])
            self.assertIn("workflowHash", response["payload"])

            # Verify the published export can be found by source identity
            record = module.ImportableWorkflowRecord(
                source_kind="userdata_file",
                source_id="workflows/my-workflow.json",
                display_name="my-workflow.json",
                file_path=pathlib.Path(temp_dir) / "workflows" / "my-workflow.json",
            )
            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                found = module._load_published_api_export_for_record(record)

        self.assertIsNotNone(found)
        self.assertEqual(found["apiPrompt"], api_prompt)

    def test_publish_route_returns_400_when_source_identity_missing(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/published-api"]

        workflow = {"nodes": [], "links": []}
        api_prompt = {"1": {"class_type": "KSampler", "inputs": {}}}

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                response = asyncio.run(
                    handler(
                        _FakePostRequest(
                            {
                                "workflow": workflow,
                                "apiPrompt": api_prompt,
                            }
                        )
                    )
                )

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"], {"error": "sourceKind and sourceId are required"})

    def test_get_importable_workflow_content_uses_published_export_when_available(self):
        module = importlib.import_module("workflow_import_bridge")

        workflow_json = {
            "nodes": [
                {
                    "id": 50,
                    "type": "RandomNoise",
                    "mode": 0,
                    "inputs": [],
                    "widgets_values": [42, "fixed", True],
                }
            ],
            "links": [],
        }
        # Frontend-exported api_prompt that the Python bridge cannot reconstruct
        api_prompt = {"50": {"class_type": "RandomNoise", "inputs": {"noise_seed": 42, "noise_type": "fixed"}}}

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "random-noise.json").write_text(
                json.dumps(workflow_json),
                encoding="utf-8",
            )

            # Pre-publish the frontend export
            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                module.publish_frontend_api_export(
                    "userdata_file",
                    "workflows/random-noise.json",
                    workflow_json,
                    api_prompt,
                )
                result = module.get_importable_workflow_content(
                    "userdata_file",
                    "workflows/random-noise.json",
                )

        self.assertEqual(result["workflow"], api_prompt)
        self.assertEqual(result["runtimeFormat"], "api_prompt")
        self.assertEqual(result["provenance"]["source"], "frontend_publish")

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
                "runtimeFormat": "api_prompt",
                "conversion": {"performed": False},
                "provenance": {"source": "source_api_prompt"},
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

    def test_get_importable_workflow_content_converts_workflow_json_to_api_prompt(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "editor-export.json").write_text(
                json.dumps(
                    {
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
                            {
                                "id": 2,
                                "title": "Save Image",
                                "type": "SaveImage",
                                "mode": 0,
                                "inputs": [
                                    {
                                        "name": "images",
                                        "type": "IMAGE",
                                        "link": 10,
                                    },
                                    {
                                        "name": "filename_prefix",
                                        "type": "STRING",
                                        "widget": {"name": "filename_prefix"},
                                    },
                                ],
                                "widgets_values": ["ComfyUI"],
                            },
                        ],
                        "links": [[10, 1, 0, 2, 0, "IMAGE"]],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                result = module.get_importable_workflow_content(
                    "userdata_file",
                    "workflows/editor-export.json",
                )

        self.assertEqual(
            result["workflow"],
            {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": "input.png"},
                    "_meta": {"title": "Load Image"},
                },
                "2": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "images": ["1", 0],
                        "filename_prefix": "ComfyUI",
                    },
                    "_meta": {"title": "Save Image"},
                },
            },
        )
        self.assertEqual(result["formatHint"], "api_prompt")
        self.assertEqual(result["originalFormat"], "workflow_json")
        self.assertEqual(result["runtimeFormat"], "api_prompt")
        self.assertEqual(result["conversion"], {"performed": True})
        self.assertEqual(result["summary"]["formatHint"], "workflow_json")

    def test_get_importable_workflow_content_omits_frontend_only_note_nodes(self):
        module = importlib.import_module("workflow_import_bridge")

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "editor-export.json").write_text(
                json.dumps(
                    {
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
                            {
                                "id": 99,
                                "title": "Workflow Notes",
                                "type": "MarkdownNote",
                                "mode": 0,
                                "inputs": [
                                    {
                                        "name": "text",
                                        "type": "STRING",
                                        "widget": {"name": "text"},
                                    }
                                ],
                                "widgets_values": ["Use the default image input."],
                            },
                            {
                                "id": 2,
                                "title": "Save Image",
                                "type": "SaveImage",
                                "mode": 0,
                                "inputs": [
                                    {
                                        "name": "images",
                                        "type": "IMAGE",
                                        "link": 10,
                                    },
                                    {
                                        "name": "filename_prefix",
                                        "type": "STRING",
                                        "widget": {"name": "filename_prefix"},
                                    },
                                ],
                                "widgets_values": ["ComfyUI"],
                            },
                        ],
                        "links": [[10, 1, 0, 2, 0, "IMAGE"]],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                result = module.get_importable_workflow_content(
                    "userdata_file",
                    "workflows/editor-export.json",
                )

        self.assertEqual(set(result["workflow"].keys()), {"1", "2"})
        self.assertNotIn("99", result["workflow"])
        self.assertEqual(result["workflow"]["2"]["inputs"]["images"], ["1", 0])

    def test_convert_workflow_json_prunes_inputs_targeting_removed_note_nodes(self):
        module = importlib.import_module("workflow_import_bridge")

        workflow = {
            "nodes": [
                {
                    "id": 5,
                    "title": "Pinned Notes",
                    "type": "Note",
                    "mode": 0,
                    "outputs": [{"name": "text", "type": "STRING", "links": [20]}],
                    "widgets_values": ["Editor only"],
                },
                {
                    "id": 6,
                    "title": "Consumer",
                    "type": "CLIPTextEncode",
                    "mode": 0,
                    "inputs": [
                        {
                            "name": "text",
                            "type": "STRING",
                            "link": 20,
                        }
                    ],
                },
            ],
            "links": [[20, 5, 0, 6, 0, "STRING"]],
        }

        converted, warnings = module._convert_workflow_json_to_api_prompt(workflow)

        self.assertEqual(
            converted,
            {
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {},
                    "_meta": {"title": "Consumer"},
                }
            },
        )
        self.assertIn(
            "Removed dangling converted input 'text' that referenced an omitted node.",
            warnings,
        )

    def test_content_route_returns_422_for_unconvertible_workflow_json(self):
        routes = _FakeRoutes()
        module = _import_bridge_with_route_stubs(routes)
        handler = routes.handlers["/api/image-gen-toolkit/workflows/importable/content"]

        with tempfile.TemporaryDirectory() as temp_dir:
            userdata_root = pathlib.Path(temp_dir) / "default"
            workflows_dir = userdata_root / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "editor-export.json").write_text(
                '{"nodes": [], "links": []}',
                encoding="utf-8",
            )

            with mock.patch.object(module, "_get_userdata_root", return_value=userdata_root):
                response = asyncio.run(
                    handler(
                        _FakeRequest(
                            {
                                "sourceKind": "userdata_file",
                                "sourceId": "workflows/editor-export.json",
                            }
                        )
                    )
                )

        self.assertEqual(response["status"], 422)
        self.assertEqual(
            response["payload"],
            {
                "error": {
                    "code": "workflow_has_no_executable_nodes",
                    "message": "Workflow JSON did not contain any executable nodes after filtering muted or virtual nodes.",
                }
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


class _FakePostRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


class _FakeRoutes:
    def __init__(self):
        self.handlers = {}

    def get(self, path):
        def decorator(handler):
            self.handlers[path] = handler
            return handler

        return decorator

    def post(self, path):
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
