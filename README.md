# ImageGen Toolkit Dev Utils
(Important: Make sure to install this latest version of ComfyUI Frontend - **1.24.4**!!!)

A focused ComfyUI custom node pack that provides a VideoHelperSuite-compatible remote video URL loader.

## Overview

ImageGen Toolkit Dev Utils currently ships a single backend node, `Load Video URL`, which accepts a remote `http` or `https` video URL and delegates decoding to comfyui-videohelpersuite's non-ffmpeg `VHS_LoadVideo` path loader behavior.

## Features

- `Load Video URL`, a small adapter node that reuses comfyui-videohelpersuite `VHS_LoadVideo` path-loading behavior for remote `http` and `https` video URLs
- Clear validation for blank or non-HTTP(S) inputs before delegation
- Package entrypoint exports only the supported node mappings

## Installation

⚠️ **Important** ⚠️

This demonstration node is not designed to be installed directly via **git clone**. For proper functionality, please install through:

- ComfyUI Manager
- ComfyUI Registry

### Additional dependency for `Load Video URL`

The new `Load Video URL` node intentionally targets parity with comfyui-videohelpersuite `VHS_LoadVideo` and delegates to VideoHelperSuite's non-ffmpeg path loader.

Install comfyui-videohelpersuite alongside this package if you want to use that node. If VideoHelperSuite is missing, `Load Video URL` will raise a clear runtime error instead of silently falling back to a different decoder path.

## Development Setup
If you want to modify this custom node locally, use the following setup:
1. Clone the repository in your ComfyUI custom nodes directory:
   ```bash
   git clone https://github.com/sammykumar/ImageGen-Toolkit-Dev-Utils
2. Navigate to the project directory: 
   ```bash
   cd ImageGen-Toolkit-Dev-Utils
   ```
3. Install dependencies:
   ```bash
    npm install
    ```
4. Build the project:
    ```bash
    npm run build
    ```
5. Refresh ComfyUI to load.

## Usage

After installation:

1. Add the "Load Video URL" node under `video`
2. Paste a direct `http` or `https` video URL into the `video_url` field
3. Adjust `force_rate`, `frame_load_cap`, `skip_first_frames`, `select_every_nth`, and optional `vae` the same way you would with the VideoHelperSuite baseline node
4. Execute the workflow to download or reuse the cached remote asset through VideoHelperSuite's existing path loader behavior

Notes:

- This node targets the non-ffmpeg `VHS_LoadVideo` behavior, not `VHS_LoadVideoFFmpeg`
- The input is intentionally a plain string widget
- Invalid, blank, or non-HTTP(S) URLs are rejected before the delegate loader runs

## Contributing

Contributions are welcome! If you have ideas for improvements or have found bugs, feel free to:

- Open an issue
- Submit a pull request with proposed changes

## License

[GNU General Public License v3](LICENSE)
