import importlib
import pathlib
import sys
import types
import unittest
from unittest import mock


sys.modules.setdefault("folder_paths", types.SimpleNamespace())
sys.modules.setdefault("nodes", types.SimpleNamespace(LoadImage=object))

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


module = importlib.import_module("job_event_emitter_node")


class JobEventEmitterNodeTests(unittest.TestCase):
    def test_normalize_sampler_value_recovers_ksampler_function_name(self):
        sampler = types.SimpleNamespace(
            sampler_function=types.SimpleNamespace(__name__="sample_euler_ancestral_cfg_pp"),
            extra_options={},
            inpaint_options={},
        )

        self.assertEqual(
            module._normalize_sampler_value(sampler),
            "euler_ancestral_cfg_pp",
        )

    def test_normalize_sampler_value_recovers_ddim_from_randomized_euler_ksampler(self):
        sampler = types.SimpleNamespace(
            sampler_function=types.SimpleNamespace(__name__="sample_euler"),
            extra_options={},
            inpaint_options={"random": True},
        )

        self.assertEqual(module._normalize_sampler_value(sampler), "ddim")

    def test_input_types_expose_comfy_workflow_params(self):
        inputs = module.JobEventFinishedNode.INPUT_TYPES()
        required = inputs["required"]

        self.assertIn("negative_prompt", required)
        self.assertIn("guidance_scale", required)
        self.assertIn("steps", required)
        self.assertIn("sampler", required)
        self.assertIn("seed", required)
        self.assertNotIn("control_after_generate", required)
        self.assertEqual(required["sampler"], ("SAMPLER",))

    def test_emit_and_passthrough_preserves_structured_output_metadata(self):
        node = module.JobEventFinishedNode()
        video = {
            "filename": "union-ic_00010-audio.mp4",
            "subfolder": "testing/video/LTX_2.3",
            "type": "output",
        }

        with mock.patch.object(module, "_utc_timestamp_z", return_value="2026-04-14T01:02:03.000Z"), mock.patch.object(
            module, "_post_event"
        ) as post_event_mock, self.assertLogs(module.logger, level="INFO") as logs:
            result = node.emit_and_passthrough(
                job_id="durable-id",
                video=video,
                events_url="https://example.com/events",
                event_token="secret-token",
                negative_prompt="blurry, low quality",
                guidance_scale=7.5,
                steps=28,
                sampler="dpmpp_2m",
                seed=123456,
                prompt={"prompt_id": "prompt-id"},
            )

        self.assertEqual(result, (video,))
        post_event_mock.assert_called_once_with(
            {
                "event_type": "job_completed",
                "timestamp": "2026-04-14T01:02:03.000Z",
                "job_id": "durable-id",
                "comfyui_run_id": "prompt-id",
                "output_url": "union-ic_00010-audio.mp4",
                "output": {
                    "filename": "union-ic_00010-audio.mp4",
                    "subfolder": "testing/video/LTX_2.3",
                    "type": "output",
                },
                "negative_prompt": "blurry, low quality",
                "guidance_scale": 7.5,
                "steps": 28,
                "sampler": "dpmpp_2m",
                "seed": 123456,
            },
            events_url="https://example.com/events",
            event_token="secret-token",
        )
        self.assertTrue(any("completeness=structured" in entry for entry in logs.output))

    def test_emit_and_passthrough_falls_back_to_filename_only_payload(self):
        node = module.JobEventFinishedNode()
        video = {"filename": "union-ic_00010-audio.mp4"}

        with mock.patch.object(module, "_utc_timestamp_z", return_value="2026-04-14T01:02:03.000Z"), mock.patch.object(
            module, "_post_event"
        ) as post_event_mock, self.assertLogs(module.logger, level="INFO") as logs:
            node.emit_and_passthrough(
                job_id="durable-id",
                video=video,
                events_url="https://example.com/events",
                event_token="secret-token",
                prompt={"prompt_id": "prompt-id"},
            )

        post_event_mock.assert_called_once_with(
            {
                "event_type": "job_completed",
                "timestamp": "2026-04-14T01:02:03.000Z",
                "job_id": "durable-id",
                "comfyui_run_id": "prompt-id",
                "output_url": "union-ic_00010-audio.mp4",
            },
            events_url="https://example.com/events",
            event_token="secret-token",
        )
        self.assertTrue(any("completeness=filename_only" in entry for entry in logs.output))

    def test_emit_and_passthrough_normalizes_sampler_typed_values_to_plain_string(self):
        node = module.JobEventFinishedNode()

        with mock.patch.object(module, "_utc_timestamp_z", return_value="2026-04-14T01:02:03.000Z"), mock.patch.object(
            module, "_post_event"
        ) as post_event_mock, self.assertLogs(module.logger, level="INFO") as logs:
            node.emit_and_passthrough(
                job_id="durable-id",
                video=None,
                events_url="https://example.com/events",
                event_token="secret-token",
                sampler={"sampler_name": " dpmpp_2m "},
                prompt={"prompt_id": "prompt-id"},
            )

        post_event_mock.assert_called_once_with(
            {
                "event_type": "job_completed",
                "timestamp": "2026-04-14T01:02:03.000Z",
                "job_id": "durable-id",
                "comfyui_run_id": "prompt-id",
                "sampler": "dpmpp_2m",
            },
            events_url="https://example.com/events",
            event_token="secret-token",
        )
        self.assertTrue(any("Sampler debug summary=" in entry for entry in logs.output))
        self.assertTrue(any("normalized_sampler': 'dpmpp_2m'" in entry for entry in logs.output))
        self.assertTrue(any("sampler_class_name': 'dict'" in entry for entry in logs.output))
        self.assertTrue(any("sampler_function_name': None" in entry for entry in logs.output))
        self.assertTrue(any("input_keys': ['sampler_name']" in entry for entry in logs.output))

    def test_emit_and_passthrough_recovers_sampler_label_from_ksampler_object(self):
        node = module.JobEventFinishedNode()
        sampler = types.SimpleNamespace(
            sampler_function=types.SimpleNamespace(__name__="sample_euler_ancestral_cfg_pp"),
            extra_options={},
            inpaint_options={},
        )

        with mock.patch.object(module, "_utc_timestamp_z", return_value="2026-04-14T01:02:03.000Z"), mock.patch.object(
            module, "_post_event"
        ) as post_event_mock, self.assertLogs(module.logger, level="INFO") as logs:
            node.emit_and_passthrough(
                job_id="durable-id",
                video=None,
                events_url="https://example.com/events",
                event_token="secret-token",
                sampler=sampler,
                prompt={"prompt_id": "prompt-id"},
            )

        post_event_mock.assert_called_once_with(
            {
                "event_type": "job_completed",
                "timestamp": "2026-04-14T01:02:03.000Z",
                "job_id": "durable-id",
                "comfyui_run_id": "prompt-id",
                "sampler": "euler_ancestral_cfg_pp",
            },
            events_url="https://example.com/events",
            event_token="secret-token",
        )
        self.assertTrue(any("normalized_sampler': 'euler_ancestral_cfg_pp'" in entry for entry in logs.output))
        self.assertTrue(any("sampler_class_name': 'SimpleNamespace'" in entry for entry in logs.output))
        self.assertTrue(any("sampler_function_name': 'sample_euler_ancestral_cfg_pp'" in entry for entry in logs.output))

    def test_emit_and_passthrough_logs_none_when_output_metadata_missing(self):
        node = module.JobEventFinishedNode()

        with mock.patch.object(module, "_utc_timestamp_z", return_value="2026-04-14T01:02:03.000Z"), mock.patch.object(
            module, "_post_event"
        ) as post_event_mock, self.assertLogs(module.logger, level="INFO") as logs:
            node.emit_and_passthrough(
                job_id="durable-id",
                video=None,
                events_url="https://example.com/events",
                event_token="secret-token",
                prompt={"prompt_id": "prompt-id"},
            )

        post_event_mock.assert_called_once_with(
            {
                "event_type": "job_completed",
                "timestamp": "2026-04-14T01:02:03.000Z",
                "job_id": "durable-id",
                "comfyui_run_id": "prompt-id",
            },
            events_url="https://example.com/events",
            event_token="secret-token",
        )
        self.assertTrue(any("completeness=none" in entry for entry in logs.output))