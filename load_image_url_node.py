import hashlib
import mimetypes
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_RETURN_TYPES = ("IMAGE", "MASK")
DEFAULT_IMAGE_INPUT_TYPES = {
    "required": {
        "image_url": (
            "STRING",
            {
                "default": "",
                "multiline": False,
                "placeholder": "https://example.com/image.png",
            },
        ),
    },
    "optional": {},
    "hidden": {},
}


def _normalize_image_url(image_url):
    if not isinstance(image_url, str):
        raise ValueError("image_url must be a string")

    normalized = image_url.strip()
    if not normalized:
        raise ValueError("image_url is required")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("image_url must be an absolute http or https URL")

    return normalized


def _get_cache_directory():
    try:
        import folder_paths  # type: ignore

        get_temp_directory = getattr(folder_paths, "get_temp_directory", None)
        if callable(get_temp_directory):
            base_dir = get_temp_directory()
        else:
            raise AttributeError("folder_paths.get_temp_directory is unavailable")
    except Exception:
        base_dir = tempfile.gettempdir()

    cache_dir = Path(base_dir) / "imagegen-toolkit-dev-utils" / "image-url-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _guess_extension(image_url, content_type):
    parsed_path = urlparse(image_url).path
    suffix = Path(parsed_path).suffix.lower()
    if suffix:
        return suffix

    if content_type:
        mime_type = content_type.split(";", 1)[0].strip().lower()
        guessed = mimetypes.guess_extension(mime_type)
        if guessed:
            return guessed

    return ".image"


def _build_cached_image_path(image_url, content_type=None):
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
    return _get_cache_directory() / f"{digest}{_guess_extension(image_url, content_type)}"


def _get_existing_cached_image_path(image_url):
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
    matches = sorted(_get_cache_directory().glob(f"{digest}.*"))
    if matches:
        return matches[0]

    return None


def _download_image_to_cache(image_url):
    existing_path = _get_existing_cached_image_path(image_url)
    if existing_path is not None:
        return existing_path

    request = Request(image_url, headers={"User-Agent": "ImageGenToolkitDevUtils/0.0.5"})

    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type")
            destination = _build_cached_image_path(image_url, content_type)
            if destination.exists():
                return destination

            with destination.open("wb") as output_file:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output_file.write(chunk)
    except HTTPError as exc:
        raise RuntimeError(f"Failed to download remote image URL '{image_url}': HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to download remote image URL '{image_url}': {exc.reason}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to cache remote image URL '{image_url}': {exc}") from exc

    return destination


def _decode_image_file(image_path):
    try:
        import numpy as np
        import torch
        from PIL import Image, ImageOps, ImageSequence
    except Exception as exc:
        raise RuntimeError(
            "Load Image URL requires torch, numpy, and Pillow in the ComfyUI Python environment"
        ) from exc

    try:
        import node_helpers  # type: ignore
    except Exception:
        node_helpers = None

    try:
        import comfy.model_management as model_management  # type: ignore

        dtype = model_management.intermediate_dtype()
    except Exception:
        dtype = torch.float32

    def _pillow(function, *args, **kwargs):
        if node_helpers is not None and hasattr(node_helpers, "pillow"):
            return node_helpers.pillow(function, *args, **kwargs)
        return function(*args, **kwargs)

    img = _pillow(Image.open, str(image_path))

    output_images = []
    output_masks = []
    w, h = None, None

    for frame in ImageSequence.Iterator(img):
        frame = _pillow(ImageOps.exif_transpose, frame)

        if frame.mode == "I":
            frame = frame.point(lambda value: value * (1 / 255))
        image = frame.convert("RGB")

        if len(output_images) == 0:
            w = image.size[0]
            h = image.size[1]

        if image.size[0] != w or image.size[1] != h:
            continue

        image_array = np.array(image).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_array)[None,]
        if "A" in frame.getbands():
            mask_array = np.array(frame.getchannel("A")).astype(np.float32) / 255.0
            mask = 1.0 - torch.from_numpy(mask_array)
        elif frame.mode == "P" and "transparency" in frame.info:
            mask_array = np.array(frame.convert("RGBA").getchannel("A")).astype(np.float32) / 255.0
            mask = 1.0 - torch.from_numpy(mask_array)
        else:
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

        output_images.append(image_tensor.to(dtype=dtype))
        output_masks.append(mask.unsqueeze(0).to(dtype=dtype))

        if getattr(img, "format", None) == "MPO":
            break

    if not output_images:
        raise RuntimeError(f"No frames could be loaded from '{image_path}'")

    if len(output_images) > 1:
        output_image = torch.cat(output_images, dim=0)
        output_mask = torch.cat(output_masks, dim=0)
    else:
        output_image = output_images[0]
        output_mask = output_masks[0]

    return output_image, output_mask


class LoadImageURL:
    @classmethod
    def INPUT_TYPES(cls):
        return DEFAULT_IMAGE_INPUT_TYPES

    RETURN_TYPES = DEFAULT_RETURN_TYPES
    RETURN_NAMES = ("IMAGE", "MASK")

    FUNCTION = "load_image"

    CATEGORY = "ImageGen Toolkit Dev Utils/Image"

    def load_image(self, image_url, **kwargs):
        normalized_url = _normalize_image_url(image_url)

        try:
            cached_image_path = _get_existing_cached_image_path(normalized_url)
            if cached_image_path is None:
                cached_image_path = _download_image_to_cache(normalized_url)
            return _decode_image_file(cached_image_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to load remote image URL '{normalized_url}': {exc}") from exc

    @classmethod
    def IS_CHANGED(cls, image_url, **kwargs):
        try:
            normalized_url = _normalize_image_url(image_url)
            return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
        except ValueError:
            return image_url

    @classmethod
    def VALIDATE_INPUTS(cls, image_url, **kwargs):
        try:
            _normalize_image_url(image_url)
        except ValueError as exc:
            return str(exc)

        return True


NODE_CLASS_MAPPINGS = {
    "load-image-url": LoadImageURL,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "load-image-url": "Load Image URL",
}
