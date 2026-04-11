# Research: ComfyUI Development Skill

**Date**: 2026-04-11  
**Agent**: vibe-flow  
**Status**: Complete  
**Related Plan**: `.github/plans/in-progress/app/nodes/video/comfyui-development-skill-2026-04-11/`

---

## 1. Context & Goals

### Business Objective

Make ComfyUI custom-node development work more reliable by giving the LLM a reusable repo-local skill that points it to the right documentation and source references.

### Technical Goals

- Add a repo-local skill that activates for ComfyUI custom-node development tasks.
- Direct the agent to the official ComfyUI docs provided by the user.
- Include explicit fallback guidance to inspect the upstream ComfyUI repository when documentation is out of date.

### Success Criteria

- [x] A focused plan exists for the skill-addition task.
- [x] The likely implementation surface is identified as a new repo skill.
- [x] Scope is constrained to skill authoring and validation, not custom-node runtime behavior changes.

### Constraints

- Keep the skill specific to ComfyUI development work.
- Prefer official docs first, upstream source second.
- Avoid inventing workflow steps that require unsupported tooling.

---

## 2. Codebase Analysis

### Existing Patterns

**Architecture**:  
The repository already uses `.github/plans/...` for PDD orchestration. No repo-local skills are present yet, so this task will likely establish the first `.github/skills/...` entry.

**Likely Affected Components**:

- `.github/skills/comfyui-development/SKILL.md`: primary new skill definition.
- Optional supporting assets: only if the skill format in this repo benefits from them.
- Optional README or agent-facing notes: only if discoverability requires it.

### Affected Files

| File | Current Role | Impact Level | Change Type |
| ---- | ------------ | ------------ | ----------- |
| `.github/skills/comfyui-development/SKILL.md` | Repo-local skill definition | 🔴 High | Create |
| supporting skill assets | Supplemental instructions if needed | 🟢 Low | Create if needed |
| `README.md` | User-facing repo docs | 🟢 Low | Modify if needed |

### Conventions Discovered

**Code Style**:

- Existing PDD artifacts in this repo use concise markdown with stable section headings.
- The available global skill instructions expect `SKILL.md` files under `.github/skills/<skill-name>/`.

**Testing Patterns**:

- For non-code changes, the narrowest proof is presence, content correctness, and markdown/config diagnostics cleanliness.

---

## 3. Alternative Analysis

### Alternative Matrix

| Approach | Pros | Cons | Recommendation |
| -------- | ---- | ---- | -------------- |
| Add repo-local skill under `.github/skills` | Native fit for request, reusable by agents, minimal scope | Requires getting the skill format right | ✅ Recommended |
| Add only README guidance | Easy to write | Less likely to be loaded automatically as a skill | ❌ Reject |
| Hardcode ComfyUI guidance into unrelated project instructions | Could be seen by the agent | Broader scope, poorer isolation, harder to maintain | ⚠️ Avoid |

### Detailed Analysis

#### Repo-local skill

The user explicitly asked for a development skill that gets loaded for ComfyUI custom-node work. A repo-local skill is the smallest change that matches that requirement and keeps the guidance isolated and maintainable.

---

## 4. Risk Assessment

| Risk | Impact | Likelihood | Mitigation Strategy | Status |
| ---- | ------ | ---------- | ------------------- | ------ |
| Skill format mismatch | Medium | Medium | Mirror existing GitHub Copilot skill conventions and keep the file simple | Identified |
| Skill is too vague to trigger reliably | Medium | Medium | Add explicit trigger phrases and task examples | Identified |
| Official docs lag real behavior | Medium | High | Include upstream source inspection fallback to `comfy-org/ComfyUI` | Identified |

---

## 5. Recommendation

### Selected Approach

Create a repo-local ComfyUI development skill that references the official docs first and instructs the agent to inspect the upstream ComfyUI source when the docs are incomplete or stale.

### Next Steps

1. Create the skill folder and `SKILL.md`.
2. Add crisp activation guidance for ComfyUI custom-node development tasks.
3. Link the two user-provided docs and the upstream repository as a fallback reference.
4. Validate the skill file content and markdown cleanliness.

---

## 6. Open Questions

- [ ] Whether the repo also wants a secondary skill for ComfyUI frontend extension work beyond custom nodes.
- [x] Whether source-code fallback should be included when docs lag. Yes, explicitly requested.

---

## 7. References

### External Documentation

- https://docs.comfy.org/custom-nodes/overview
- https://docs.comfy.org/development/comfyui-server/comms_overview
- https://github.com/comfy-org/ComfyUI

---

## Metadata

**Research Duration**: ~10 minutes  
**Files Analyzed**: existing plan taxonomy and repo structure  
**Alternatives Evaluated**: 3  
**Updated**: 2026-04-11