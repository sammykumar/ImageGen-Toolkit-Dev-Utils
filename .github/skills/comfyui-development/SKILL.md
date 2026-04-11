---
name: comfyui-development
description: Use this skill for ComfyUI custom-node development, debugging, and adjacent server communication work that affects custom nodes.
---

# ComfyUI Development

Use this skill when the task involves ComfyUI custom nodes, node registration or metadata, execution behavior, input and output contracts, or ComfyUI server communication that affects custom-node behavior.

## Read These First

Start with the official docs before making assumptions:

- https://docs.comfy.org/custom-nodes/overview
- https://docs.comfy.org/development/comfyui-server/comms_overview

## Apply This Skill When

- Building or modifying a ComfyUI custom node
- Debugging node inputs, outputs, execution flow, or registration behavior
- Working on API, websocket, or prompt-server communication that affects custom nodes
- Reconciling this repo's node behavior with current ComfyUI expectations

## Working Rules

1. Consult the official docs first for the intended custom-node and server-comms model.
2. Treat the docs as guidance, not ground truth. They can lag actual ComfyUI behavior.
3. When behavior is unclear or docs and reality diverge, inspect the upstream ComfyUI source: https://github.com/comfy-org/ComfyUI
4. Prefer upstream source for current implementation details such as node lifecycle, server message flow, request handlers, and compatibility expectations.
5. Keep changes aligned with this repository's existing node patterns unless the task explicitly requires broader refactoring.

## Repo Workflow

- Use https://prd-comfyui.devlabhq.com/ as the active development ComfyUI instance.
- Assume the node pack there is on the nightly build, which tracks the latest code from `master`.
- Treat released versions as the production install path only when the team is not actively developing, which is uncommon.

## Browser Update Checklist

1. Click `Manager`.
2. Click `Custom Nodes Manager`.
3. Filter by `Installed` and type `ImageGen Toolkit Dev Utils` in the `Search` box.
4. Click `Try update`.

## Practical Checklist

- Confirm whether the task is about node authoring, runtime behavior, or server integration.
- Check the official docs first.
- Verify real behavior against upstream ComfyUI source when needed.
- Then implement or review the local change using this repo's existing conventions.