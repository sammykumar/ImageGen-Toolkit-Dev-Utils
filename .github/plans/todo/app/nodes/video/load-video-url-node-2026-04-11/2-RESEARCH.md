# Research: Load Video URL Node

**Date**: 2026-04-11  
**Agent**: research.agent  
**Status**: Complete  
**Related Plan**: `.github/plans/todo/app/nodes/video/load-video-url-node-2026-04-11/`

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
| **B. New URL Node Using Path-Style Resolution** | High                 | - Matches requested input contract<br>- Preserves `VHS_LoadVideo` behavior<br>- Aligns with existing VHS URL handling<br>- Keeps backend responsibilities clear | - Still needs download/cache policy | Medium | 1-2 days | ✅ RECOMMENDED |
| **C. Browser Fetch Then Re-upload** | Low                  | - Keeps Python path simple | - Adds frontend complexity<br>- Cross-origin and large-file issues<br>- Duplicates upload pipeline | High | 2-4 days | ❌ Reject |

### Detailed Analysis

#### Approach A: Clone Upload Node Literally

**Description**: Start from the upload node shape and replace the picker with a URL field while preserving most of the surrounding code.

**Technical Considerations**:

- Works best for node naming, category, and output parity.
- Works poorly for actual input resolution, because upload nodes fundamentally enumerate local files.

**Implementation Path**:

1. Copy upload-node structure.
2. Replace file-list input with string input.
3. Add remote resolution logic inside `load_video`.

**Example**:

```typescript
// UI baseline only; not the preferred backend baseline.
```

**Alignment with Project Principles**:

- ✅ Simple shape reuse
- ⚠️ Backend mismatch
- ❌ Risks copying the wrong abstraction

---

#### Approach B: New URL Node Using Path-Style Resolution ⭐ RECOMMENDED

**Description**: Create a dedicated URL node whose backend accepts a string input and resolves remote URLs before delegating to the actual video loading logic, while borrowing the upload node's overall node behavior and possibly its UX cues.

**Technical Considerations**:

- VHS `LoadVideoPath` and `LoadVideoFFmpegPath` already validate string paths and call a download helper when the value is a URL.
- `VHS_LoadVideo` itself maps to `LoadVideoUpload`, which is the non-ffmpeg upload baseline the user pointed to.
- This approach keeps input semantics separate from decode semantics and makes caching/error handling easier to reason about.

**Implementation Path**:

1. Define a new URL-based node class in Python.
2. Resolve URL to a local/cache path before video loading.
3. Add a native string widget or Vue-assisted URL input in the frontend only if needed.

**Example**:

```typescript
// Frontend can stay minimal if the Python node simply exposes a STRING input.
```

**Alignment with Project Principles**:

- ✅ Correct input abstraction
- ✅ Minimal frontend if desired
- ⚠️ Requires explicit cache and security decisions

**Why Recommended**:

It matches the requested user behavior while preserving `VHS_LoadVideo` as the behavioral baseline and reusing the right proven helper behavior from VideoHelperSuite for URL-aware resolution.

---

#### Approach C: Browser Fetch Then Re-upload

**Description**: Fetch the video in the browser and send it through an upload flow so the backend still sees a local uploaded filename.

**Technical Considerations**:

- Browser fetches large media poorly and are subject to CORS and memory issues.
- This adds frontend coupling with little value over backend download.

**Implementation Path**:

1. Fetch remote file in browser.
2. Upload blob to Comfy input folder.
3. Reuse upload node path.

**Why Rejected**:

It is the highest-complexity route and shifts the hardest operational problems into the browser.

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

**Concerns**:

- The exact download helper behavior, cache policy, and security model should not be copied blindly without fitting this repo.

---

### Best Practices Research

**Source**: VideoHelperSuite source review

**Key Findings**:

- URL handling belongs at the string/path loader boundary, not in file-enumeration logic.
- Preview or upload widgets are optional enhancements, not prerequisites for loading by URL.
- ffmpeg-backed loading is useful when remote media requires better format coverage or audio extraction.

**Applicability**:  
These findings support a minimal first implementation: URL input, backend download/resolve, then frame loading.

---

### Similar Implementations

**Project**: VideoHelperSuite `VHS_LoadVideo` plus `LoadVideoPath`

**Approach**: Keep `VHS_LoadVideo` as the feature/output baseline while using the path-node approach for string input validation, URL detection, optional download, and delegation into the common video loader.

**Lessons Learned**:

- Do not mix picker/upload concerns into URL resolution.
- Keep decode outputs stable even when the source is remote.

---

## 5. Proof of Concept

### POC Files (Temporary)

> No proof-of-concept files were created during planning.

### POC Results

**Test**: Source-level comparison of local repo surfaces and VideoHelperSuite baseline behavior  
**Result**: ✅ Success  
**Finding**: The correct technical baseline is a hybrid: `VHS_LoadVideo` for parity, `LoadVideoPath` for URL handling.

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

**Approach B: New URL Node Using Path-Style Resolution**

### Rationale

This best matches the requested behavior, aligns with the simplest reliable backend model, and lets the frontend remain minimal unless the user explicitly wants a richer Vue-powered URL entry experience.

### Trade-offs Accepted

- A small amount of custom backend resolver logic is preferable to forcing URL behavior through upload plumbing.
- Full parity with all VHS outputs may require a second pass if the first implementation focuses only on image frames.

### Next Steps

1. ✅ Research complete → Create `3-SPEC.md`
2. ⏭️ Confirm required output parity: image-only or image-plus-audio/video-info
3. ⏭️ Proceed to implementation planning and task execution when approved

---

## 8. Open Questions

- [ ] Should the first version match all `VHS_LoadVideo` outputs immediately, or stage image-only parity first and add full parity next?
- [ ] Should remote files be cached under Comfy input, temp, or a node-specific cache directory?
- [x] ~~Is `VHS_LoadVideo` the ffmpeg variant?~~ - Answer: No. `VHS_LoadVideo` maps to `LoadVideoUpload`; the ffmpeg upload node is `VHS_LoadVideoFFmpeg`.

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