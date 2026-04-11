# ImageGen Toolkit Dev Utils
(Important: Make sure to install this latest version of ComfyUI Frontend - **1.24.4**!!!)

A focused ComfyUI custom node pack that provides a self-contained remote video URL loader for ComfyUI workflows.

## Overview

ImageGen Toolkit Dev Utils currently ships a single backend node, `Load Video URL`, which accepts a remote `http` or `https` video URL, caches the remote asset locally, and decodes frames inside this package without requiring VideoHelperSuite.

## Features

- `Load Video URL`, a self-contained node for remote `http` and `https` video URLs
- Clear validation for blank or non-HTTP(S) inputs before download and decode
- URL-addressed cache reuse for repeated executions of the same remote asset
- Package entrypoint exports only the supported node mappings

## Installation

⚠️ **Important** ⚠️

This demonstration node is not designed to be installed directly via **git clone**. For proper functionality, please install through:

- ComfyUI Manager
- ComfyUI Registry

### Runtime requirements for `Load Video URL`

`Load Video URL` no longer imports or delegates to VideoHelperSuite.

The node expects the normal ComfyUI Python runtime plus this package's Python dependencies, including `imageio[ffmpeg]` and `Pillow`, so it can download, cache, and decode the remote asset internally.

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

1. Add the "Load Video URL" node under `ImageGen Toolkit Dev Utils/video`
2. Paste a direct `http` or `https` video URL into the `video_url` field
3. Adjust `force_rate`, `frame_load_cap`, `skip_first_frames`, `select_every_nth`, optional `custom_width`, `custom_height`, and optional `vae` the same way you would with the current node surface
4. Execute the workflow to download or reuse the cached remote asset and decode frames locally inside this package

Notes:

- This node keeps the `video_url`-centered control surface aligned with the current `VHS_LoadVideo`-style contract as closely as practical, but it does not require VideoHelperSuite at runtime
- The input is intentionally a plain string widget
- Invalid, blank, or non-HTTP(S) URLs are rejected before any network fetch occurs
- Remote files are cached by URL hash under the ComfyUI temp directory when available, or the system temp directory otherwise
- The current implementation returns decoded image frames, frame count, and metadata; audio extraction is not implemented yet and the audio output is `None`

## Contributing

Contributions are welcome! If you have ideas for improvements or have found bugs, feel free to:

- Open an issue
- Submit a pull request with proposed changes

## License

[GNU General Public License v3](LICENSE)
