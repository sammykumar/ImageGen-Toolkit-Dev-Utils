# Research: Load Video URL Node

**Date**: 2026-04-11  
**Agent**: research.agent  
**Status**: Complete  
**Related Plan**: `.github/plans/in-progress/app/nodes/video/load-video-url-node-2026-04-11/`

---

## 1. Context & Goals

### Business Objective

Allow ComfyUI users to load a video directly from a URL so remote assets can be used without a separate manual upload step.

### Technical Goals

- Add a node whose primary input is a URL string rather than an uploaded filename.
- Preserve the baseline video loader output shape so downstream nodes continue to work.
- Keep the solution compatible with ComfyUI custom-node conventions already used in this repo.

### Success Criteria

- [x] A concrete plan exists for a URL-based video loading node.
- [x] The plan identifies the correct baseline layers from VideoHelperSuite.
- [x] The plan explicitly targets parity with `VHS_LoadVideo`, not `VHS_LoadVideoFFmpeg`.
- [x] The plan captures security, caching, and UX follow-up requirements.

### Constraints

- Must fit the current repo shape: one Python custom node surface plus a Vite/Vue frontend bundle.
- Should avoid unnecessary frontend complexity if a native string widget is sufficient.
- Must not assume unrestricted remote fetching without validation and clear failure behavior.
- Must not require `comfyui-videohelpersuite` to be installed at runtime.

---

## 2. Codebase Analysis

### Existing Patterns

**Architecture**:  
This repo currently exposes a single Python node class and a frontend extension that registers a custom Vue widget for the node.

**Key Components**:

- `ComfyUIFEExampleVueBasic.py`: defines the current example node and returns an image from a custom widget payload.
- `src/main.ts`: registers the frontend extension and mounts the Vue widget into the ComfyUI node.
- `__init__.py`: exports node mappings and registers the built frontend directory with ComfyUI.

**Data Flow**:

```mermaid
graph LR
    A[ComfyUI node definition] --> B[Frontend widget or string input]
    B --> C[Python node execution]
    C --> D[Local file resolution or URL download]
    D --> E[Frame decode and IMAGE output]
```

### Affected Files

| File               | Current Role  | Impact Level | Change Type      |
| ------------------ | ------------- | ------------ | ---------------- |
| `ComfyUIFEExampleVueBasic.py` | Existing example node backend | 🔴 High      | Modify or split |
| `src/main.ts` | Frontend widget registration | 🟡 Medium    | Modify |
| `README.md` | User-facing usage docs | 🟡 Medium    | Modify |
| `locales/en/main.json` | English widget copy | 🟢 Low       | Modify |
| `locales/zh/main.json` | Chinese widget copy | 🟢 Low       | Modify |

### Technical Debt

- The repo has no existing video decode or remote-download path.
- The current sample node is image-oriented and does not model richer output contracts like audio or video info.
- There is no visible local test harness yet for node runtime behavior.

### Conventions Discovered

**Code Style**:

- Python node classes expose `INPUT_TYPES`, `RETURN_TYPES`, `FUNCTION`, `CATEGORY`, and a runtime method.
- Frontend behavior is registered through `app.registerExtension` in `src/main.ts`.

**Testing Patterns**:

- No explicit local test files were found in the initial repo surface; verification will likely start with narrow runtime checks and then add focused tests as implementation solidifies.

**Documentation Standards**:

- `README.md` explains installation, usage, and development flow for the custom node.

---

## 3. Alternative Analysis

### Alternative Matrix

| Approach             | Principles Alignment | Pros                                | Cons                                | Risks        | Est. Effort  | Recommendation |
| -------------------- | -------------------- | ----------------------------------- | ----------------------------------- | ------------ | ------------ | -------------- |
| **A. Clone Upload Node Literally** | Medium                 | - Familiar baseline<br>- Similar user intent | - Upload concerns do not solve URL entry<br>- Would require bolting URL logic onto file-enumeration flow | Medium | 1-2 days | ⚠️ Consider |
| **B. New self-contained URL node with internal parity** | High                 | - Matches requested input contract<br>- Preserves `VHS_LoadVideo` behavior goals<br>- Removes runtime dependency on VideoHelperSuite<br>- Keeps package self-contained | - Requires internal loader implementation and tests | Medium | 1-2 days | ✅ RECOMMENDED |
| **C. Browser Fetch Then Re-upload** | Low                  | - Keeps Python path simple | - Adds frontend complexity<br>- Cross-origin and large-file issues<br>- Duplicates upload pipeline | High | 2-4 days | ❌ Reject |

### Detailed Analysis

#### Approach B: New self-contained URL node with internal parity ⭐ RECOMMENDED

**Description**: Create a dedicated URL node whose backend accepts a string input and resolves remote URLs using internal helpers, then loads video frames directly inside this package while preserving the needed `VHS_LoadVideo`-style interface.

**Technical Considerations**:

- `VHS_LoadVideo` remains the user-facing baseline for controls and output shape.
- The current local implementation still imports `videohelpersuite.load_video_nodes`, which is the direct cause of the runtime failure.
- The corrected design should keep input semantics separate from decode semantics, but own both responsibilities in this package.

**Why Recommended**:

It matches the requested user behavior while preserving `VHS_LoadVideo` as the behavioral baseline and removing the runtime dependency that is currently breaking execution.

---

## 4. External Discovery

### Library/Framework Research

#### ComfyUI-VideoHelperSuite

**Source**: [Repository](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)  
**Last Updated**: 2026-04-11 snapshot  
**License**: GPL-3.0  
**Community**: Established ComfyUI video helper plugin

**Key Features**:

- `VHS_LoadVideo` maps to `LoadVideoUpload`, the non-ffmpeg upload node.
- `Load Video (Upload)` enumerates local input-folder videos and resolves them via annotated filepaths.
- `Load Video (Path)` and `Load Video FFmpeg (Path)` accept a string and call URL-aware download logic before decoding.
- Frontend JS adds upload widgets and preview plumbing around node definitions.

**Relevant to This Task**:

- Confirms that the parity target should be `VHS_LoadVideo` and that URL resolution is a separate concern.
- Provides a proven backend pattern for `is_url(...)` then `try_download_video(...)` before loading.

---

## 5. Proof of Concept

### POC Files (Temporary)

> No proof-of-concept files were created during planning.

### POC Results

**Test**: Source-level comparison of the shipped implementation against the clarified requirement  
**Result**: ✅ Success  
**Finding**: The current node still delegates to VideoHelperSuite and raises when it is missing, so the next implementation slice must replace delegation with internal behavior.

---

## 6. Risk Assessment

| Risk                         | Impact | Likelihood | Mitigation Strategy | Owner       | Status     |
| ---------------------------- | ------ | ---------- | ------------------- | ----------- | ---------- |
| Remote fetch can become an unsafe open downloader | High   | Medium     | Restrict schemes, validate targets, and fail early on invalid URLs | Team | Identified |
| Repeated runs may redownload large videos | Medium | Medium     | Add cache path policy keyed by URL or content hash | Team | Identified |
| Baseline parity may be incomplete if only image output is implemented | Medium | Medium     | Decide early whether audio/video-info parity is required | Team | Identified |

---

## 7. Recommendation

### Selected Approach

**Approach B: New self-contained URL node with internal parity**

### Rationale

This best matches the requested behavior, removes the failing dependency edge, and still lets the frontend remain minimal unless the user explicitly wants a richer Vue-powered URL entry experience.

### Trade-offs Accepted

- A small amount of custom backend loader logic is preferable to shipping a node that hard-fails without another package.
- Full parity with all VHS outputs may still require staged validation in real ComfyUI runtime.

### Next Steps

1. ✅ Research complete → Create `3-SPEC.md`
2. ✅ Clarified that VideoHelperSuite delegation is not acceptable
3. ⏭️ Replace the delegation-based implementation with internal loading logic

---

## 8. Open Questions

- [ ] Should the self-contained implementation match all `VHS_LoadVideo` outputs immediately, or stage image-only parity first and add full parity next?
- [ ] Should remote files be cached under Comfy input, temp, or a node-specific cache directory?
- [x] ~~Is `VHS_LoadVideo` the ffmpeg variant?~~ - Answer: No. `VHS_LoadVideo` maps to `LoadVideoUpload`; the ffmpeg upload node is `VHS_LoadVideoFFmpeg`.

---

## 8A. Validation Follow-up Addendum

### Observed Runtime Regression

- Live ComfyUI prompt validation reports `frame_load_cap must be an integer` against every input on `load-video-url`, which indicates the custom validation path is not matching the actual raw prompt value shape reaching the node.
- The user also wants the node to explicitly enforce that `video_url` is a string.
- The user wants VHS-style `0` semantics preserved where `0` means "use the value from the video file itself" rather than forcing an override.

### Local Hypothesis

- `VALIDATE_INPUTS` is too strict about exact Python runtime types for ComfyUI prompt values and is likely validating a shared raw input shape rather than already-coerced Python ints.
- The cheapest discriminating check is the focused backend unit suite extended with raw string-valued prompt inputs and explicit `0` sentinel expectations.

---

## 9. References

### Internal Documentation

- `README.md`
- `ComfyUIFEExampleVueBasic.py`
- `src/main.ts`

### External Resources

- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) - Baseline upload/path node behavior
- [ComfyUI-VideoHelperSuite README](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite#readme) - Load Video node behavior and path variant notes

### Tools Used

- **Analysis Tools**: workspace file reads, GitHub repo search, webpage fetch

---

## Metadata

**Research Duration**: ~20 minutes  
**Files Analyzed**: 6 local, multiple external baseline snippets  
**External Sources**: 2  
**Alternatives Evaluated**: 3  
**Updated**: 2026-04-11 00:00
