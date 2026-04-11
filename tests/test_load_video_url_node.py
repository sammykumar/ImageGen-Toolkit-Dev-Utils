import importlib
import sys
import types
import unittest


sys.modules.setdefault("folder_paths", types.SimpleNamespace())
sys.modules.setdefault("nodes", types.SimpleNamespace(LoadImage=object))


class _FakeLoadVideoPath:
    return_types = ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO")
    last_call = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("STRING", {"placeholder": "X://insert/path/here.mp4"}),
                "force_rate": ("FLOAT", {"default": 0}),
            },
            "optional": {
                "vae": ("VAE",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = return_types

    def load_video(self, **kwargs):
        type(self).last_call = kwargs
        return ("image", 12, "audio", "video_info")

    @classmethod
    def IS_CHANGED(cls, video, **kwargs):
        return f"changed:{video}"

    @classmethod
    def VALIDATE_INPUTS(cls, video):
        return video.startswith("http")


videohelpersuite_module = types.ModuleType("videohelpersuite")
load_video_nodes_module = types.ModuleType("videohelpersuite.load_video_nodes")
load_video_nodes_module.LoadVideoPath = _FakeLoadVideoPath
videohelpersuite_module.load_video_nodes = load_video_nodes_module
sys.modules["videohelpersuite"] = videohelpersuite_module
sys.modules["videohelpersuite.load_video_nodes"] = load_video_nodes_module


module = importlib.import_module("load_video_url_node")


class LoadVideoURLNodeTests(unittest.TestCase):
    def test_node_mappings_only_export_load_video_url(self):
        self.assertEqual(module.NODE_CLASS_MAPPINGS, {"load-video-url": module.LoadVideoURL})
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS, {"load-video-url": "Load Video URL"})

    def test_normalize_video_url_trims_and_accepts_http_urls(self):
        self.assertEqual(
            module._normalize_video_url("  https://example.com/video.mp4  "),
            "https://example.com/video.mp4",
        )

    def test_validate_inputs_rejects_non_http_urls(self):
        self.assertEqual(
            module.LoadVideoURL.VALIDATE_INPUTS("/tmp/video.mp4"),
            "video_url must be an absolute http or https URL",
        )

    def test_load_video_delegates_to_vhs_path_loader(self):
        node = module.LoadVideoURL()

        result = node.load_video("https://example.com/video.mp4", force_rate=8, frame_load_cap=24)

        self.assertEqual(result, ("image", 12, "audio", "video_info"))
        self.assertEqual(
            _FakeLoadVideoPath.last_call,
            {
                "video": "https://example.com/video.mp4",
                "force_rate": 8,
                "frame_load_cap": 24,
            },
        )

    def test_input_types_rename_video_to_video_url(self):
        input_types = module.LoadVideoURL.INPUT_TYPES()

        self.assertIn("video_url", input_types["required"])
        self.assertNotIn("video", input_types["required"])
        self.assertEqual(input_types["required"]["video_url"][0], "STRING")


if __name__ == "__main__":
    unittest.main()