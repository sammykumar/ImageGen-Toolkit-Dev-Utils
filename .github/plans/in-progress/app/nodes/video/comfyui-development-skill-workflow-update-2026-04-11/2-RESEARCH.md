# Research: ComfyUI Skill Workflow Update

**Date**: 2026-04-11  
**Agent**: vibe-flow  
**Status**: Complete  
**Related Plan**: `.github/plans/in-progress/app/nodes/video/comfyui-development-skill-workflow-update-2026-04-11/`

---

## 1. Context & Goals

### Business Objective

Keep the ComfyUI development skill aligned with the actual development workflow used for this node pack.

### Technical Goals

- Add repo-specific workflow guidance for nightly-versus-release usage.
- Document the browser-based update path in ComfyUI Manager.
- Preserve the existing docs-first and source-fallback guidance in the skill.

### Success Criteria

- [x] A focused plan exists for the skill-content update.
- [x] The owning implementation surface is identified as the existing skill file.
- [x] The live ComfyUI UI labels needed for the update steps are validated.

### Constraints

- Keep the change scoped to the existing skill.
- Use the actual UI labels shown by the live ComfyUI Manager flow.
- Avoid changing runtime code or unrelated docs.

---

## 2. Codebase Analysis

### Existing Patterns

**Architecture**:  
The existing ComfyUI guidance lives in `.github/skills/comfyui-development/SKILL.md`, so the update should extend that file rather than introducing a second overlapping skill.

**Likely Affected Components**:

- `.github/skills/comfyui-development/SKILL.md`: current skill definition and the only expected edit target.

### Affected Files

| File | Current Role | Impact Level | Change Type |
| ---- | ------------ | ------------ | ----------- |
| `.github/skills/comfyui-development/SKILL.md` | Repo-local ComfyUI development skill | 🔴 High | Modify |

### Conventions Discovered

**Code Style**:

- The skill is concise, section-based markdown with direct operational guidance.

**Validation Patterns**:

- For a markdown-only update, the narrowest proof is diagnostics cleanliness plus direct content checks for the required workflow and update instructions.

### Live UI Findings

- The top-level button label is `Manager` under `ComfyUI Manager`.
- The relevant dialog action is labeled `Custom Nodes Manager`.
- The nested manager view exposes `Filter`, `Search`, and `Try update`.
- The row for `ImageGen Toolkit Dev Utils` currently shows `nightly`, which matches the user-provided workflow context.

---

## 3. Alternative Analysis

### Alternative Matrix

| Approach | Pros | Cons | Recommendation |
| -------- | ---- | ---- | -------------- |
| Update the existing skill | Single source of truth, minimal scope | Requires careful insertion to stay concise | ✅ Recommended |
| Create a second workflow-specific skill | Separates general and local guidance | Overlaps heavily and risks conflicting triggers | ❌ Reject |
| Put workflow only in README | Helpful for humans | Less likely to be loaded automatically for the LLM | ⚠️ Avoid |

---

## 4. Risk Assessment

| Risk | Impact | Likelihood | Mitigation Strategy | Status |
| ---- | ------ | ---------- | ------------------- | ------ |
| UI labels drift from the live app | Medium | Low | Use the currently verified labels from the browser session | Identified |
| Skill grows too broad | Low | Medium | Add one compact workflow section and one compact update checklist | Identified |
| Workflow guidance becomes stale later | Medium | Medium | Phrase it as current repo workflow and keep steps concrete | Identified |

---

## 5. Recommendation

### Selected Approach

Extend the existing ComfyUI development skill with a short repo workflow section and a short browser update checklist using the verified live UI labels.

### Next Steps

1. Edit `.github/skills/comfyui-development/SKILL.md`.
2. Add the nightly-versus-release guidance for this repo.
3. Add the manager-based update steps using `Manager`, `Custom Nodes Manager`, `Installed`, `Search`, and `Try update`.
4. Validate the touched markdown and required content.

---

## 6. Open Questions

- [x] Which manager label should the skill use? `Custom Nodes Manager`, verified from the live UI.
- [ ] Whether production update guidance should later include a stricter release-only checklist beyond the skill note.

---

## 7. References

### Internal Documentation

- `.github/skills/comfyui-development/SKILL.md`

### External / Runtime Evidence

- https://prd-comfyui.devlabhq.com/

---

## Metadata

**Research Duration**: ~10 minutes  
**Files Analyzed**: existing skill file and live ComfyUI manager UI snapshot  
**Alternatives Evaluated**: 3  
**Updated**: 2026-04-11