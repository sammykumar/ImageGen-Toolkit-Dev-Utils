import importlib
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock


sys.modules.setdefault("folder_paths", types.SimpleNamespace())
sys.modules.setdefault("nodes", types.SimpleNamespace(LoadImage=object))

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


module = importlib.import_module("load_video_url_node")


class LoadVideoURLNodeTests(unittest.TestCase):
    def test_node_mappings_only_export_load_video_url(self):
        self.assertEqual(module.NODE_CLASS_MAPPINGS, {"load-video-url": module.LoadVideoURL})
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS, {"load-video-url": "Load Video URL"})

    def test_node_category_uses_pack_top_level_menu(self):
        self.assertEqual(module.LoadVideoURL.CATEGORY, "ImageGen Toolkit Dev Utils/video")

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

    def test_validate_inputs_rejects_invalid_controls(self):
        self.assertEqual(
            module.LoadVideoURL.VALIDATE_INPUTS(
                "https://example.com/video.mp4",
                select_every_nth=0,
            ),
            "select_every_nth must be >= 1",
        )

    def test_load_video_downloads_and_decodes_with_internal_helpers(self):
        node = module.LoadVideoURL()
        cached_path = pathlib.Path("/tmp/downloaded-video.mp4")
        decoded = ("image", 12, None, {"loaded_frame_count": 12})

        with mock.patch.object(module, "_get_existing_cached_video_path", return_value=None) as get_existing_mock, mock.patch.object(
            module, "_download_video_to_cache", return_value=cached_path
        ) as download_mock, mock.patch.object(module, "_decode_video_file", return_value=decoded) as decode_mock:
            result = node.load_video("https://example.com/video.mp4", force_rate=8, frame_load_cap=24)

        self.assertEqual(result, decoded)
        get_existing_mock.assert_called_once_with("https://example.com/video.mp4")
        download_mock.assert_called_once_with("https://example.com/video.mp4")
        decode_mock.assert_called_once_with(
            cached_path,
            force_rate=8,
            custom_width=0,
            custom_height=0,
            frame_load_cap=24,
            skip_first_frames=0,
            select_every_nth=1,
        )

    def test_load_video_reuses_cached_path_without_downloading(self):
        node = module.LoadVideoURL()
        cached_path = pathlib.Path("/tmp/cached-video.mp4")
        decoded = ("image", 4, None, {"loaded_frame_count": 4})

        with mock.patch.object(module, "_get_existing_cached_video_path", return_value=cached_path) as get_existing_mock, mock.patch.object(
            module, "_download_video_to_cache"
        ) as download_mock, mock.patch.object(module, "_decode_video_file", return_value=decoded) as decode_mock:
            result = node.load_video("https://example.com/video.mp4")

        self.assertEqual(result, decoded)
        get_existing_mock.assert_called_once_with("https://example.com/video.mp4")
        download_mock.assert_not_called()
        decode_mock.assert_called_once()

    def test_input_types_rename_video_to_video_url(self):
        input_types = module.LoadVideoURL.INPUT_TYPES()

        self.assertIn("video_url", input_types["required"])
        self.assertEqual(input_types["required"]["video_url"][0], "STRING")
        self.assertIn("vae", input_types["optional"])

    def test_download_video_to_cache_writes_response_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with unittest.mock.patch.object(
                module, "_get_cache_directory", return_value=pathlib.Path(temp_dir)
            ), unittest.mock.patch.object(module, "_get_existing_cached_video_path", return_value=None):
                response = _FakeResponse(
                    headers={"Content-Type": "video/mp4"},
                    chunks=[b"abc", b"123", b""],
                )

                with unittest.mock.patch.object(module, "urlopen", return_value=response):
                    cached_path = module._download_video_to_cache("https://example.com/video.mp4")

            self.assertTrue(cached_path.exists())
            self.assertEqual(cached_path.read_bytes(), b"abc123")
            self.assertEqual(cached_path.suffix, ".mp4")

    def test_is_changed_hashes_normalized_url(self):
        changed = module.LoadVideoURL.IS_CHANGED(" https://example.com/video.mp4 ")
        self.assertEqual(len(changed), 64)
        self.assertEqual(changed, module.LoadVideoURL.IS_CHANGED("https://example.com/video.mp4"))


class _FakeResponse:
    def __init__(self, *, headers, chunks):
        self.headers = headers
        self._chunks = list(chunks)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _size):
        return self._chunks.pop(0)


if __name__ == "__main__":
    unittest.main()