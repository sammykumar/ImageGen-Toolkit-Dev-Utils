# Progress & Tasks

> Purpose: Combined task plan and chronological execution log. Tracks what needs to be done, what changed, and why.

---

## Task Plan

**Date**: 2026-04-11  
**Agent**: vibe-flow  
**Status**: Draft  
**Based on Spec**: `3-SPEC.md`

### Goal

Add a new ComfyUI node that preserves the same core functionality as `comfyui-videohelpersuite -> VHS_LoadVideo` and adds URL input so the video source can come from a remote location instead of only the local upload flow.

### Approach

Use VideoHelperSuite `VHS_LoadVideo` as the baseline for outputs and load behavior, while replacing the upload-only source selection with a URL-capable source resolver. The backend URL resolution should borrow from the path-style loader behavior because that is where VHS already handles string paths and remote URLs.

### Pre-Implementation Checklist

- [ ] Spec reviewed and approved (`3-SPEC.md`)
- [ ] Research findings validated (`2-RESEARCH.md`)
- [ ] Dependencies identified and available

### Implementation Tasks

#### Task 1: Create backend URL-loading node

**Goal**: Add a Python node class that accepts a URL string, resolves it to a local file or streamable path, and returns the same output contract as the baseline video loader.

**Files**:

- `ComfyUIFEExampleVueBasic.py` (modify or split)
- `__init__.py` (modify)
- `README.md` (modify)

**Steps**:

1. Isolate the node registration and choose whether to extend the existing demo module or create a dedicated video node module.
2. Define URL-oriented `INPUT_TYPES` using a string input instead of uploaded-file enumeration.
3. Reuse a download/resolve step before delegating to the actual frame loading implementation.

**Verification**:

- [ ] Run `get_errors` - must be clean
- [ ] Happy path test: a direct `.mp4` URL produces image output without manual upload

**Status**: ⬜ Not Started

---

#### Task 2: Add node UI for URL entry

**Goal**: Provide a practical ComfyUI input experience for entering, editing, and validating a remote video URL.

**Files**:

- `src/main.ts` (modify)
- `src/components/` (create or modify URL input component)
- `locales/en/main.json` (modify)
- `locales/zh/main.json` (modify)

**Steps**:

1. Decide whether a plain string widget is sufficient or whether to add a Vue-backed URL input with validation/help text.
2. Register the widget for the new node and size the node appropriately.
3. Surface validation hints and baseline instructions for supported URLs.

**Verification**:

- [ ] Run `get_errors` - must be clean
- [ ] Happy path test: the node shows an editable URL field and persists the value in the graph

**Dependencies**: Requires Task 1 scope decisions complete

**Status**: ⬜ Not Started

---

#### Task 3: Handle remote download, caching, and failures

**Goal**: Make remote loading reliable enough for repeated ComfyUI runs without turning the node into an unsafe open fetch proxy.

**Files**:

- `ComfyUIFEExampleVueBasic.py` (modify or split)
- `README.md` (modify)

**Steps**:

1. Define allowed URL schemes and rejection behavior for invalid or missing resources.
2. Choose whether to download into Comfy input/temp storage or a node-managed cache keyed by URL.
3. Define cache invalidation, duplicate-download behavior, and user-facing error messages.

**Verification**:

- [ ] Run `get_errors` - must be clean
- [ ] Error-path test: invalid URL and unreachable host fail with actionable errors

**Dependencies**: Requires Task 1 complete

**Status**: ⬜ Not Started

---

#### Task 4: Prove parity with the baseline loader

**Goal**: Confirm the new node matches `VHS_LoadVideo` closely enough in outputs, load controls, ergonomics, and documentation, with URL input as the added capability.

**Files**:

- `README.md` (modify)
- `doc/` (optional additions)
- test files to be determined during implementation

**Steps**:

1. Compare output types and node behavior against the chosen VideoHelperSuite baseline.
1. Compare output types and node behavior against `VHS_LoadVideo` specifically.
2. Add focused tests for URL success, URL failure, and repeated execution behavior.
3. Document which parts are intentionally kept identical to `VHS_LoadVideo` and which parts are new for URL support.

**Verification**:

- [ ] Happy path test: same video loaded locally and via URL produces the same output shape
- [ ] Narrow test: repeated execution avoids unnecessary re-download when cache is valid

**Dependencies**: Requires Tasks 1-3 complete

**Status**: ⬜ Not Started

---

### Task Summary

| Status         | Count | Tasks     |
| -------------- | ----- | --------- |
| ✅ Complete    | 0     | -         |
| 🔄 In Progress | 0     | -         |
| ⬜ Not Started | 4     | Tasks 1-4 |
| **Total**      | **4** | -         |

---

## Execution Log

## Quick Index

| Date       | Work Item          | Status  | Key outputs                              |
| ---------- | ------------------ | ------- | ---------------------------------------- |
| 2026-04-11 | Orchestrator Plan  | ✅ PASS | Plan folder created, research/spec drafted |

---

## 2026-04-11 — Orchestrator Planning

### Summary

| Field   | Value                                                                                                  |
| ------- | ------------------------------------------------------------------------------------------------------ |
| Goal    | Create a plan for a URL-based video loading node                                                       |
| Scope   | Plan-only PDD artifacts for backend loader, frontend widget, caching, and validation                   |
| Status  | ✅ PASS                                                                                                |
| Owner   | vibe-flow                                                                                               |
| Related | Plan: `.github/plans/todo/app/nodes/video/load-video-url-node-2026-04-11/`                            |

### Changes

| Area              | Details                                                                                                            |
| ----------------- | ------------------------------------------------------------------------------------------------------------------ |
| What changed      | - Created plan-only task folder<br>- Anchored baseline on `VHS_LoadVideo` / Load Video (Upload)<br>- Selected URL/path semantics for implementation |
| Notes / decisions | - `VHS_LoadVideo` is the non-ffmpeg baseline node<br>- Path-style handling is only the resolver layer for the added URL feature |

**Files changed**

- `.github/plans/todo/app/nodes/video/load-video-url-node-2026-04-11/1-PROGRESS.md` (created)
- `.github/plans/todo/app/nodes/video/load-video-url-node-2026-04-11/2-RESEARCH.md` (created)
- `.github/plans/todo/app/nodes/video/load-video-url-node-2026-04-11/3-SPEC.md` (created)

### Verification

- [x] Required plan-only folder created under `todo/`
- [x] Required template-backed files instantiated
- [x] Plan stops before implementation, per user request

### Risks

| Risk                     | Impact | Likelihood | Mitigation                              | Owner | Link |
| ------------------------ | ------ | ---------- | --------------------------------------- | ----- | ---- |
| URL download semantics differ from local upload semantics | Medium | Medium     | Reuse the path-style resolver flow and document expected differences | Team  | -    |
| Remote media introduces security and caching issues       | High   | Medium     | Treat validation, allowed schemes, and cache location as first-class tasks | Team  | -    |

### Follow-ups

| Item                                      | Priority | Owner | Due        | Link |
| ----------------------------------------- | -------- | ----- | ---------- | ---- |
| Confirm whether plain string UI is enough | P1       | User  | 2026-04-11 | -    |
| Confirm whether ffmpeg-style loader parity is required | P1       | User  | 2026-04-11 | -    |

---

## Notes

- This is a plan-only artifact set; no code implementation or test execution has been performed.
- The parity target is `VHS_LoadVideo` specifically; `LoadVideoPath` is only referenced because it already demonstrates URL-aware string resolution.