import hashlib
import mimetypes
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_RETURN_TYPES = ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO")
DEFAULT_VIDEO_INPUT_TYPES = {
    "required": {
        "video_url": (
            "STRING",
            {
                "default": "",
                "multiline": False,
                "placeholder": "https://example.com/video.mp4",
            },
        ),
        "force_rate": ("FLOAT", {"default": 0, "min": 0, "max": 60, "step": 1}),
        "custom_width": ("INT", {"default": 0, "min": 0, "max": 8192, "disable": 0}),
        "custom_height": ("INT", {"default": 0, "min": 0, "max": 8192, "disable": 0}),
        "frame_load_cap": ("INT", {"default": 0, "min": 0, "max": 9007199254740991, "step": 1}),
        "skip_first_frames": ("INT", {"default": 0, "min": 0, "max": 9007199254740991, "step": 1}),
        "select_every_nth": ("INT", {"default": 1, "min": 1, "max": 9007199254740991, "step": 1}),
    },
    "optional": {
        "vae": ("VAE",),
    },
    "hidden": {},
}


def _normalize_video_url(video_url):
    if not isinstance(video_url, str):
        raise ValueError("video_url must be a string")

    normalized = video_url.strip()
    if not normalized:
        raise ValueError("video_url is required")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("video_url must be an absolute http or https URL")

    return normalized


def _coerce_prompt_scalar(value):
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return value[0]

    return value


def _coerce_non_negative_int(value, field_name, *, minimum=0):
    value = _coerce_prompt_scalar(value)

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")

    if isinstance(value, int):
        coerced = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{field_name} must be an integer")
        coerced = int(value)
    elif isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must be an integer")

        try:
            if any(character in normalized.lower() for character in (".", "e")):
                parsed = float(normalized)
                if not parsed.is_integer():
                    raise ValueError
                coerced = int(parsed)
            else:
                coerced = int(normalized, 10)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer") from exc
    else:
        raise ValueError(f"{field_name} must be an integer")

    if coerced < minimum:
        comparator = f">= {minimum}"
        raise ValueError(f"{field_name} must be {comparator}")

    return coerced


def _coerce_non_negative_number(value, field_name):
    value = _coerce_prompt_scalar(value)

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")

    if isinstance(value, (int, float)):
        coerced = float(value)
    elif isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must be a number")

        try:
            coerced = float(normalized)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a number") from exc
    else:
        raise ValueError(f"{field_name} must be a number")

    if coerced < 0:
        raise ValueError(f"{field_name} must be >= 0")

    return coerced


def _coerce_video_controls(force_rate, custom_width, custom_height, frame_load_cap, skip_first_frames, select_every_nth):
    return (
        _coerce_non_negative_number(force_rate, "force_rate"),
        _coerce_non_negative_int(custom_width, "custom_width"),
        _coerce_non_negative_int(custom_height, "custom_height"),
        _coerce_non_negative_int(frame_load_cap, "frame_load_cap"),
        _coerce_non_negative_int(skip_first_frames, "skip_first_frames"),
        _coerce_non_negative_int(select_every_nth, "select_every_nth", minimum=1),
    )


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

    cache_dir = Path(base_dir) / "imagegen-toolkit-dev-utils" / "video-url-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _guess_extension(video_url, content_type):
    parsed_path = urlparse(video_url).path
    suffix = Path(parsed_path).suffix.lower()
    if suffix:
        return suffix

    if content_type:
        mime_type = content_type.split(";", 1)[0].strip().lower()
        guessed = mimetypes.guess_extension(mime_type)
        if guessed:
            return guessed

    return ".video"


def _build_cached_video_path(video_url, content_type=None):
    digest = hashlib.sha256(video_url.encode("utf-8")).hexdigest()
    return _get_cache_directory() / f"{digest}{_guess_extension(video_url, content_type)}"


def _get_existing_cached_video_path(video_url):
    digest = hashlib.sha256(video_url.encode("utf-8")).hexdigest()
    matches = sorted(_get_cache_directory().glob(f"{digest}.*"))
    if matches:
        return matches[0]

    return None


def _download_video_to_cache(video_url):
    existing_path = _get_existing_cached_video_path(video_url)
    if existing_path is not None:
        return existing_path

    request = Request(video_url, headers={"User-Agent": "ImageGenToolkitDevUtils/0.0.3"})

    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type")
            destination = _build_cached_video_path(video_url, content_type)
            if destination.exists():
                return destination

            with destination.open("wb") as output_file:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output_file.write(chunk)
    except HTTPError as exc:
        raise RuntimeError(f"Failed to download remote video URL '{video_url}': HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to download remote video URL '{video_url}': {exc.reason}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to cache remote video URL '{video_url}': {exc}") from exc

    return destination


def _resize_frame(frame_array, custom_width, custom_height):
    if custom_width == 0 and custom_height == 0:
        return frame_array

    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("Load Video URL requires Pillow in the ComfyUI Python environment") from exc

    image = Image.fromarray(frame_array)
    original_width, original_height = image.size

    if custom_width == 0:
        custom_width = max(1, round(original_width * (custom_height / original_height)))
    if custom_height == 0:
        custom_height = max(1, round(original_height * (custom_width / original_width)))

    resized = image.resize((custom_width, custom_height), Image.Resampling.LANCZOS)
    try:
        import numpy as np
    except Exception as exc:
        raise RuntimeError("Load Video URL requires numpy in the ComfyUI Python environment") from exc

    return np.asarray(resized)


def _compute_frame_step(select_every_nth, force_rate, source_fps):
    effective_step = select_every_nth
    if force_rate > 0 and source_fps and source_fps > force_rate:
        effective_step = max(effective_step, max(1, round(source_fps / force_rate)))
    return effective_step


def _open_video_reader(video_path, iio, imageio):
    try:
        metadata = iio.immeta(video_path, plugin="ffmpeg")
        return metadata, iio.imiter(video_path, plugin="ffmpeg"), None
    except Exception as primary_exc:
        try:
            legacy_reader = imageio.get_reader(video_path, format="ffmpeg")
            return legacy_reader.get_meta_data() or {}, legacy_reader, legacy_reader
        except Exception as fallback_exc:
            raise RuntimeError(
                "Load Video URL could not find a usable ffmpeg decode backend for "
                f"'{video_path}'. imageio.v3 plugin='ffmpeg' failed with: {primary_exc}. "
                "Legacy imageio.get_reader(..., format='ffmpeg') also failed with: "
                f"{fallback_exc}. Ensure imageio[ffmpeg] is installed in the ComfyUI Python environment."
            ) from fallback_exc


def _decode_video_file(video_path, *, force_rate, custom_width, custom_height, frame_load_cap, skip_first_frames, select_every_nth):
    try:
        import imageio
        import imageio.v3 as iio
        import numpy as np
        import torch
    except Exception as exc:
        raise RuntimeError(
            "Load Video URL requires torch, numpy, and imageio in the ComfyUI Python environment"
        ) from exc

    metadata, frame_iterator, closeable_reader = _open_video_reader(video_path, iio, imageio)

    try:
        source_fps = float(metadata.get("fps") or 0)
        frame_step = _compute_frame_step(select_every_nth, force_rate, source_fps)

        collected_frames = []
        emitted_frames = 0

        for frame_index, frame in enumerate(frame_iterator):
            if frame_index < skip_first_frames:
                continue

            if (frame_index - skip_first_frames) % frame_step != 0:
                continue

            resized_frame = _resize_frame(frame, custom_width, custom_height)
            collected_frames.append(torch.from_numpy(np.asarray(resized_frame)).float() / 255.0)
            emitted_frames += 1

            if frame_load_cap > 0 and emitted_frames >= frame_load_cap:
                break
    finally:
        if closeable_reader is not None:
            closeable_reader.close()

    if not collected_frames:
        raise RuntimeError(f"No frames could be loaded from '{video_path}'")

    images = torch.stack(collected_frames, dim=0)
    loaded_fps = source_fps / frame_step if source_fps else 0
    video_info = {
        "source_fps": source_fps,
        "loaded_fps": loaded_fps,
        "source_frame_count": metadata.get("nframes"),
        "loaded_frame_count": emitted_frames,
        "cached_video_path": str(video_path),
    }

    return images, emitted_frames, None, video_info


class LoadVideoURL:
    @classmethod
    def INPUT_TYPES(cls):
        return DEFAULT_VIDEO_INPUT_TYPES

    RETURN_TYPES = DEFAULT_RETURN_TYPES
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info")

    FUNCTION = "load_video"

    CATEGORY = "ImageGen Toolkit Dev Utils/Video"

    def load_video(
        self,
        video_url,
        force_rate=0,
        custom_width=0,
        custom_height=0,
        frame_load_cap=0,
        skip_first_frames=0,
        select_every_nth=1,
        vae=None,
        **kwargs,
    ):
        normalized_url = _normalize_video_url(video_url)
        force_rate, custom_width, custom_height, frame_load_cap, skip_first_frames, select_every_nth = _coerce_video_controls(
            force_rate,
            custom_width,
            custom_height,
            frame_load_cap,
            skip_first_frames,
            select_every_nth,
        )

        try:
            cached_video_path = _get_existing_cached_video_path(normalized_url)
            if cached_video_path is None:
                cached_video_path = _download_video_to_cache(normalized_url)
            return _decode_video_file(
                cached_video_path,
                force_rate=force_rate,
                custom_width=custom_width,
                custom_height=custom_height,
                frame_load_cap=frame_load_cap,
                skip_first_frames=skip_first_frames,
                select_every_nth=select_every_nth,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load remote video URL '{normalized_url}': {exc}") from exc

    @classmethod
    def IS_CHANGED(cls, video_url, **kwargs):
        try:
            normalized_url = _normalize_video_url(video_url)
            return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
        except ValueError:
            return video_url

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        video_url,
        **kwargs,
    ):
        try:
            _normalize_video_url(video_url)
        except ValueError as exc:
            return str(exc)

        return True


NODE_CLASS_MAPPINGS = {
    "load-video-url": LoadVideoURL,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "load-video-url": "Load Video URL",
}