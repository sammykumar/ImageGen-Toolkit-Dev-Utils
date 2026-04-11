import importlib
import inspect
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

    def test_validate_inputs_accepts_video_url_with_numeric_kwargs_ignored(self):
        self.assertTrue(
            module.LoadVideoURL.VALIDATE_INPUTS(
                " https://example.com/video.mp4 ",
                force_rate="0",
                custom_width="0",
                custom_height=0,
                frame_load_cap="0",
                skip_first_frames="0",
                select_every_nth="1",
            )
        )

    def test_validate_inputs_rejects_non_string_video_url(self):
        self.assertEqual(
            module.LoadVideoURL.VALIDATE_INPUTS(
                42,
                force_rate="0",
                custom_width="0",
                custom_height="0",
                frame_load_cap="0",
                skip_first_frames="0",
                select_every_nth="1",
            ),
            "video_url must be a string",
        )

    def test_validate_inputs_signature_only_exposes_video_url_for_custom_validation(self):
        signature = inspect.signature(module.LoadVideoURL.VALIDATE_INPUTS)
        parameters = list(signature.parameters.values())

        self.assertEqual([parameter.name for parameter in parameters], ["video_url", "kwargs"])
        self.assertEqual(parameters[0].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(parameters[1].kind, inspect.Parameter.VAR_KEYWORD)

    def test_validate_inputs_does_not_report_numeric_field_errors(self):
        self.assertTrue(
            module.LoadVideoURL.VALIDATE_INPUTS(
                "https://example.com/video.mp4",
                frame_load_cap="abc",
                custom_width="abc",
                skip_first_frames="abc",
                select_every_nth="0",
            )
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

    def test_load_video_coerces_prompt_scalars_before_decode(self):
        node = module.LoadVideoURL()
        cached_path = pathlib.Path("/tmp/cached-video.mp4")
        decoded = ("image", 4, None, {"loaded_frame_count": 4})

        with mock.patch.object(module, "_get_existing_cached_video_path", return_value=cached_path), mock.patch.object(
            module, "_download_video_to_cache"
        ) as download_mock, mock.patch.object(module, "_decode_video_file", return_value=decoded) as decode_mock:
            result = node.load_video(
                "https://example.com/video.mp4",
                force_rate="0",
                custom_width="0",
                custom_height="0",
                frame_load_cap="0",
                skip_first_frames="0",
                select_every_nth="2",
            )

        self.assertEqual(result, decoded)
        download_mock.assert_not_called()
        decode_mock.assert_called_once_with(
            cached_path,
            force_rate=0.0,
            custom_width=0,
            custom_height=0,
            frame_load_cap=0,
            skip_first_frames=0,
            select_every_nth=2,
        )

    def test_load_video_still_validates_numeric_controls_at_execution_time(self):
        node = module.LoadVideoURL()

        with self.assertRaises(ValueError) as exc_info:
            node.load_video(
                "https://example.com/video.mp4",
                frame_load_cap="abc",
            )

        self.assertIn("frame_load_cap must be an integer", str(exc_info.exception))

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

    def test_decode_video_file_falls_back_to_legacy_ffmpeg_reader(self):
        legacy_reader = _FakeLegacyReader(
            metadata={"fps": 24, "nframes": 5},
            frames=["frame-0", "frame-1", "frame-2", "frame-3", "frame-4"],
        )
        imageio_module = types.ModuleType("imageio")
        imageio_module.get_reader = mock.Mock(return_value=legacy_reader)

        imageio_v3_module = types.ModuleType("imageio.v3")
        imageio_v3_module.immeta = mock.Mock(side_effect=ValueError("`ffmpeg` is not a registered plugin name."))
        imageio_v3_module.imiter = mock.Mock()
        imageio_module.v3 = imageio_v3_module

        with mock.patch.dict(
            sys.modules,
            {
                "imageio": imageio_module,
                "imageio.v3": imageio_v3_module,
                "numpy": _FakeNumpyModule(),
                "torch": _FakeTorchModule(),
            },
        ):
            images, frame_count, audio, video_info = module._decode_video_file(
                "/tmp/video.mp4",
                force_rate=0,
                custom_width=0,
                custom_height=0,
                frame_load_cap=0,
                skip_first_frames=1,
                select_every_nth=2,
            )

        self.assertEqual(frame_count, 2)
        self.assertIsNone(audio)
        self.assertEqual(images["dim"], 0)
        self.assertEqual(images["values"], [("frame-1", 255.0), ("frame-3", 255.0)])
        self.assertEqual(video_info["source_fps"], 24.0)
        self.assertEqual(video_info["loaded_fps"], 12.0)
        self.assertEqual(video_info["source_frame_count"], 5)
        self.assertTrue(legacy_reader.closed)
        imageio_module.get_reader.assert_called_once_with("/tmp/video.mp4", format="ffmpeg")

    def test_decode_video_file_reports_backend_failures_clearly(self):
        imageio_module = types.ModuleType("imageio")
        imageio_module.get_reader = mock.Mock(side_effect=RuntimeError("legacy reader missing"))

        imageio_v3_module = types.ModuleType("imageio.v3")
        imageio_v3_module.immeta = mock.Mock(side_effect=ValueError("`ffmpeg` is not a registered plugin name."))
        imageio_v3_module.imiter = mock.Mock()
        imageio_module.v3 = imageio_v3_module

        with mock.patch.dict(
            sys.modules,
            {
                "imageio": imageio_module,
                "imageio.v3": imageio_v3_module,
                "numpy": _FakeNumpyModule(),
                "torch": _FakeTorchModule(),
            },
        ):
            with self.assertRaises(RuntimeError) as exc_info:
                module._decode_video_file(
                    "/tmp/video.mp4",
                    force_rate=0,
                    custom_width=0,
                    custom_height=0,
                    frame_load_cap=0,
                    skip_first_frames=0,
                    select_every_nth=1,
                )

        self.assertIn("usable ffmpeg decode backend", str(exc_info.exception))
        self.assertIn("imageio.v3 plugin='ffmpeg' failed", str(exc_info.exception))
        self.assertIn("legacy reader missing", str(exc_info.exception))


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


class _FakeNumpyModule:
    @staticmethod
    def asarray(value):
        return value


class _FakeTensor:
    def __init__(self, value):
        self.value = value

    def float(self):
        return self

    def __truediv__(self, divisor):
        return (self.value, divisor)


class _FakeTorchModule:
    @staticmethod
    def from_numpy(value):
        return _FakeTensor(value)

    @staticmethod
    def stack(values, dim=0):
        return {"values": values, "dim": dim}


class _FakeLegacyReader:
    def __init__(self, *, metadata, frames):
        self._metadata = metadata
        self._frames = list(frames)
        self.closed = False

    def get_meta_data(self):
        return self._metadata

    def __iter__(self):
        return iter(self._frames)

    def close(self):
        self.closed = True


if __name__ == "__main__":
    unittest.main()