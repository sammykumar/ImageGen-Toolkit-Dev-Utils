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