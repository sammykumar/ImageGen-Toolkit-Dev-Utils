# Research: Custom Pack Top-Level Node Category

**Date**: 2026-04-11  
**Agent**: vibe-flow  
**Status**: Complete  
**Related Plan**: `.github/plans/in-progress/app/nodes/video/custom-pack-top-level-category-2026-04-11/`

---

## 1. Context & Goals

### Business Objective

Make the custom node easier to discover in the ComfyUI add-node menu by grouping it under a top-level category aligned with the custom pack name.

### Technical Goals

- Ensure the pack exposes a top-level node directory/category matching the custom pack identity.
- Preserve existing node behavior and inputs.
- Keep the change limited to registration/category metadata unless implementation evidence requires more.

### Success Criteria

- [x] A focused plan exists for the node discoverability issue.
- [x] The likely control point is identified as node category/registration metadata.
- [x] Scope is constrained to add-menu organization, not node execution logic.

### Constraints

- Must remain compatible with ComfyUI custom-node registration.
- Should avoid changing runtime behavior for loading videos.
- Should not rename the pack in a way that breaks existing extension web-dir registration unless required.

---

## 2. Codebase Analysis

### Existing Patterns

**Architecture**:  
The package entrypoint in `__init__.py` registers node mappings and binds the frontend asset directory to the project name. The node itself is implemented in a dedicated backend module.

**Likely Affected Components**:

- `__init__.py`: pack-level registration already keyed off the project name.
- Backend node module: likely defines the node `CATEGORY` string that controls the ComfyUI menu path.
- `README.md`: may need a short note if the node menu location changes.

### Affected Files

| File | Current Role | Impact Level | Change Type |
| ---- | ------------ | ------------ | ----------- |
| `__init__.py` | Package registration and web-dir binding | 🟡 Medium | Verify or modify |
| backend node module | Node metadata and category path | 🔴 High | Modify |
| `README.md` | Optional usage note | 🟢 Low | Modify if needed |

### Conventions Discovered

**Code Style**:

- Node registration is exported through `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`.
- Pack identity is already derived from project config in the package entrypoint.

**Testing Patterns**:

- Focused Python tests exist for backend node behavior and can be extended for metadata assertions if needed.

---

## 3. Alternative Analysis

### Alternative Matrix

| Approach | Pros | Cons | Recommendation |
| -------- | ---- | ---- | -------------- |
| Change node `CATEGORY` to include pack name | Minimal, targeted, preserves behavior | Depends on ComfyUI menu semantics | ✅ Recommended |
| Add duplicate alias node under new category | Preserves old location too | Adds clutter and duplicate entries | ⚠️ Avoid unless requested |
| Rename package/project globally | Strong pack branding | Higher risk, touches extension registration | ❌ Reject |

### Detailed Analysis

#### Change node category metadata

The add-node tree in ComfyUI is primarily driven by node category strings. Since the pack is already named at the package level, the smallest likely fix is to set the node category path so the first segment matches the custom pack name.

---

## 4. Risk Assessment

| Risk | Impact | Likelihood | Mitigation Strategy | Status |
| ---- | ------ | ---------- | ------------------- | ------ |
| Wrong control point chosen | Medium | Low | Verify with a focused metadata/test check before widening scope | Identified |
| Existing workflows rely on old menu location | Low | Low | Keep node class name stable; change only discovery path | Identified |
| Pack-name source differs from desired menu label | Low | Medium | Use the existing project-config pack name when available | Identified |

---

## 5. Recommendation

### Selected Approach

Update the node category/registration metadata so the add-node menu exposes a top-level path aligned with the custom pack name.

### Next Steps

1. Confirm the exact metadata field controlling the current menu placement.
2. Update it to a pack-name-prefixed category path.
3. Add or adjust a focused validation check proving the new category/export metadata.

---

## 6. Open Questions

- [ ] Should the old category path remain available as a duplicate alias, or is a straight move acceptable?
- [x] Is this intended as a discoverability-only fix with no runtime changes? Likely yes.

---

## 7. References

### Internal Documentation

- `__init__.py`
- backend node module
- `tests/test_load_video_url_node.py`

---

## Metadata

**Research Duration**: ~10 minutes  
**Files Analyzed**: request context plus existing plan taxonomy  
**Alternatives Evaluated**: 3  
**Updated**: 2026-04-11
