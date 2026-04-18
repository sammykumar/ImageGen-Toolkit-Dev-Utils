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


module = importlib.import_module("load_image_url_node")


class LoadImageURLNodeTests(unittest.TestCase):
    def test_node_mappings_only_export_load_image_url(self):
        self.assertEqual(module.NODE_CLASS_MAPPINGS, {"load-image-url": module.LoadImageURL})
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS, {"load-image-url": "Load Image URL"})

    def test_node_category_uses_pack_top_level_menu(self):
        self.assertEqual(module.LoadImageURL.CATEGORY, "ImageGen Toolkit Dev Utils/Image")

    def test_return_types_match_ootb_load_image(self):
        self.assertEqual(module.LoadImageURL.RETURN_TYPES, ("IMAGE", "MASK"))
        self.assertEqual(module.LoadImageURL.RETURN_NAMES, ("IMAGE", "MASK"))

    def test_normalize_image_url_trims_and_accepts_http_urls(self):
        self.assertEqual(
            module._normalize_image_url("  https://example.com/image.png  "),
            "https://example.com/image.png",
        )

    def test_validate_inputs_rejects_non_http_urls(self):
        self.assertEqual(
            module.LoadImageURL.VALIDATE_INPUTS("/tmp/image.png"),
            "image_url must be an absolute http or https URL",
        )

    def test_validate_inputs_rejects_empty_image_url(self):
        self.assertEqual(
            module.LoadImageURL.VALIDATE_INPUTS("   "),
            "image_url is required",
        )

    def test_validate_inputs_rejects_non_string_image_url(self):
        self.assertEqual(
            module.LoadImageURL.VALIDATE_INPUTS(42),
            "image_url must be a string",
        )

    def test_validate_inputs_accepts_absolute_http_url(self):
        self.assertTrue(module.LoadImageURL.VALIDATE_INPUTS("https://example.com/image.png"))

    def test_validate_inputs_signature_only_exposes_image_url_for_custom_validation(self):
        signature = inspect.signature(module.LoadImageURL.VALIDATE_INPUTS)
        parameters = list(signature.parameters.values())

        self.assertEqual([parameter.name for parameter in parameters], ["image_url", "kwargs"])
        self.assertEqual(parameters[0].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(parameters[1].kind, inspect.Parameter.VAR_KEYWORD)

    def test_input_types_expose_image_url_string_field(self):
        input_types = module.LoadImageURL.INPUT_TYPES()

        self.assertIn("image_url", input_types["required"])
        self.assertEqual(input_types["required"]["image_url"][0], "STRING")
        options = input_types["required"]["image_url"][1]
        self.assertEqual(options["default"], "")
        self.assertFalse(options["multiline"])
        self.assertIn("placeholder", options)

    def test_load_image_downloads_and_decodes_with_internal_helpers(self):
        node = module.LoadImageURL()
        cached_path = pathlib.Path("/tmp/downloaded-image.png")
        decoded = ("image-tensor", "mask-tensor")

        with mock.patch.object(module, "_get_existing_cached_image_path", return_value=None) as get_existing_mock, mock.patch.object(
            module, "_download_image_to_cache", return_value=cached_path
        ) as download_mock, mock.patch.object(module, "_decode_image_file", return_value=decoded) as decode_mock:
            result = node.load_image("https://example.com/image.png")

        self.assertEqual(result, decoded)
        get_existing_mock.assert_called_once_with("https://example.com/image.png")
        download_mock.assert_called_once_with("https://example.com/image.png")
        decode_mock.assert_called_once_with(cached_path)

    def test_load_image_reuses_cached_path_without_downloading(self):
        node = module.LoadImageURL()
        cached_path = pathlib.Path("/tmp/cached-image.png")
        decoded = ("image-tensor", "mask-tensor")

        with mock.patch.object(module, "_get_existing_cached_image_path", return_value=cached_path) as get_existing_mock, mock.patch.object(
            module, "_download_image_to_cache"
        ) as download_mock, mock.patch.object(module, "_decode_image_file", return_value=decoded) as decode_mock:
            result = node.load_image("https://example.com/image.png")

        self.assertEqual(result, decoded)
        get_existing_mock.assert_called_once_with("https://example.com/image.png")
        download_mock.assert_not_called()
        decode_mock.assert_called_once_with(cached_path)

    def test_load_image_normalizes_url_before_lookup(self):
        node = module.LoadImageURL()
        cached_path = pathlib.Path("/tmp/cached-image.png")
        decoded = ("image-tensor", "mask-tensor")

        with mock.patch.object(module, "_get_existing_cached_image_path", return_value=cached_path) as get_existing_mock, mock.patch.object(
            module, "_download_image_to_cache"
        ), mock.patch.object(module, "_decode_image_file", return_value=decoded):
            node.load_image("  https://example.com/image.png  ")

        get_existing_mock.assert_called_once_with("https://example.com/image.png")

    def test_load_image_rejects_invalid_url_eagerly(self):
        node = module.LoadImageURL()

        with self.assertRaises(ValueError) as exc_info:
            node.load_image("/tmp/image.png")

        self.assertIn("absolute http or https URL", str(exc_info.exception))

    def test_load_image_wraps_decode_failures_with_normalized_url(self):
        node = module.LoadImageURL()

        with mock.patch.object(module, "_get_existing_cached_image_path", return_value=pathlib.Path("/tmp/x.png")), mock.patch.object(
            module, "_decode_image_file", side_effect=RuntimeError("decode boom")
        ):
            with self.assertRaises(RuntimeError) as exc_info:
                node.load_image("https://example.com/image.png")

        self.assertIn("https://example.com/image.png", str(exc_info.exception))
        self.assertIn("decode boom", str(exc_info.exception))

    def test_download_image_to_cache_writes_response_bytes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(
                module, "_get_cache_directory", return_value=pathlib.Path(temp_dir)
            ), mock.patch.object(module, "_get_existing_cached_image_path", return_value=None):
                response = _FakeResponse(
                    headers={"Content-Type": "image/png"},
                    chunks=[b"abc", b"123", b""],
                )

                with mock.patch.object(module, "urlopen", return_value=response):
                    cached_path = module._download_image_to_cache("https://example.com/image.png")

            self.assertTrue(cached_path.exists())
            self.assertEqual(cached_path.read_bytes(), b"abc123")
            self.assertEqual(cached_path.suffix, ".png")

    def test_download_image_to_cache_guesses_extension_from_content_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(
                module, "_get_cache_directory", return_value=pathlib.Path(temp_dir)
            ), mock.patch.object(module, "_get_existing_cached_image_path", return_value=None):
                response = _FakeResponse(
                    headers={"Content-Type": "image/jpeg; charset=binary"},
                    chunks=[b"jpegbytes", b""],
                )

                with mock.patch.object(module, "urlopen", return_value=response):
                    cached_path = module._download_image_to_cache("https://example.com/no-extension")

            self.assertTrue(cached_path.exists())
            self.assertIn(cached_path.suffix, {".jpg", ".jpe", ".jpeg"})

    def test_download_image_to_cache_raises_for_http_errors(self):
        from urllib.error import HTTPError

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(
                module, "_get_cache_directory", return_value=pathlib.Path(temp_dir)
            ), mock.patch.object(module, "_get_existing_cached_image_path", return_value=None), mock.patch.object(
                module,
                "urlopen",
                side_effect=HTTPError("https://example.com/image.png", 404, "Not Found", {}, None),
            ):
                with self.assertRaises(RuntimeError) as exc_info:
                    module._download_image_to_cache("https://example.com/image.png")

        self.assertIn("HTTP 404", str(exc_info.exception))

    def test_is_changed_hashes_normalized_url(self):
        changed = module.LoadImageURL.IS_CHANGED(" https://example.com/image.png ")
        self.assertEqual(len(changed), 64)
        self.assertEqual(changed, module.LoadImageURL.IS_CHANGED("https://example.com/image.png"))

    def test_is_changed_falls_back_to_raw_value_for_invalid_url(self):
        self.assertEqual(module.LoadImageURL.IS_CHANGED("not-a-url"), "not-a-url")


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
