import importlib
from urllib.parse import urlparse


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


def _get_vhs_load_video_path_class():
    module = importlib.import_module("videohelpersuite.load_video_nodes")
    return module.LoadVideoPath


def _get_vhs_video_return_types():
    try:
        load_video_path_class = _get_vhs_load_video_path_class()
    except Exception:
        return ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO")

    return getattr(load_video_path_class, "RETURN_TYPES", ("IMAGE", "INT", "AUDIO", "VHS_VIDEOINFO"))


class LoadVideoURL:
    @classmethod
    def INPUT_TYPES(cls):
        try:
            input_types = _get_vhs_load_video_path_class().INPUT_TYPES()
        except Exception:
            input_types = {
                "required": {
                    "video": (
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
                "optional": {},
                "hidden": {},
            }

        required_inputs = dict(input_types.get("required", {}))
        video_input = required_inputs.pop("video", ("STRING", {}))
        video_options = dict(video_input[1] if len(video_input) > 1 else {})
        video_options.update(
            {
                "default": "",
                "multiline": False,
                "placeholder": "https://example.com/video.mp4",
            }
        )
        required_inputs["video_url"] = ("STRING", video_options)

        return {
            **input_types,
            "required": required_inputs,
        }

    RETURN_TYPES = _get_vhs_video_return_types()
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "video_info")

    FUNCTION = "load_video"

    CATEGORY = "video"

    def load_video(self, video_url, **kwargs):
        normalized_url = _normalize_video_url(video_url)

        try:
            loader = _get_vhs_load_video_path_class()()
        except Exception as exc:
            raise RuntimeError(
                "Load Video URL requires comfyui-videohelpersuite to be installed so it can reuse VHS_LoadVideo path loading behavior"
            ) from exc

        try:
            return loader.load_video(video=normalized_url, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"Failed to load remote video URL '{normalized_url}': {exc}") from exc

    @classmethod
    def IS_CHANGED(cls, video_url, **kwargs):
        normalized_url = _normalize_video_url(video_url)
        try:
            return _get_vhs_load_video_path_class().IS_CHANGED(normalized_url, **kwargs)
        except Exception:
            return normalized_url

    @classmethod
    def VALIDATE_INPUTS(cls, video_url, **kwargs):
        try:
            normalized_url = _normalize_video_url(video_url)
        except ValueError as exc:
            return str(exc)

        try:
            return _get_vhs_load_video_path_class().VALIDATE_INPUTS(normalized_url)
        except Exception:
            return True


NODE_CLASS_MAPPINGS = {
    "load-video-url": LoadVideoURL,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "load-video-url": "Load Video URL",
}