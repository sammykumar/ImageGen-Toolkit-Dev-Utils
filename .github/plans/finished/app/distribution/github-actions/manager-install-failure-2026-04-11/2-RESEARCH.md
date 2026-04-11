# Research: Manager Install Failure

**Date**: 2026-04-11  
**Agent**: research.agent  
**Status**: Pending  
**Related Plan**: `.github/plans/in-progress/app/distribution/github-actions/manager-install-failure-2026-04-11/`

---

## 1. Context & Goals

### Business Objective

Determine why ComfyUI-Manager fails before dependency installation when attempting to install this public custom-node repository from GitHub.

### Technical Goals

Establish whether the failure is caused by repository metadata, repository accessibility, GitHub Actions publishing, or an external host/network condition.

### Success Criteria

- [x] Root cause identified
- [x] GitHub Actions relevance confirmed or ruled out
- [x] Minimal remediation identified

### Constraints

- Use the provided install log as the failure anchor.
- Limit diagnosis to the clone layer unless evidence requires stepping later in the install flow.
- Do not edit source files; only update plan artifacts.

---

## 2. Codebase Analysis

The failure occurs in the first install gate: ComfyUI-Manager invokes `git clone -v --recursive --progress -- https://github.com/sammykumar/imagegen_toolkit_dev_utils ...` and exits with code 128 before any dependency installation or node import. That means the decisive question is whether that exact URL is cloneable.

Repository evidence shows a mismatch between the repo's actual origin and the URL published in manager-facing metadata:

- `.git/config` points `origin` at `git@github.com:sammykumar/ImageGen-Toolkit-Dev-Utils.git`.
- `pyproject.toml` publishes `https://github.com/sammykumar/imagegen_toolkit_dev_utils` under both `[project.urls].Repository` and `[tool.comfy].Repository`.
- Public GitHub verification shows `https://github.com/sammykumar/ImageGen-Toolkit-Dev-Utils` resolves to the repository page, while `https://github.com/sammykumar/imagegen_toolkit_dev_utils` returns HTTP 404.

That mismatch fully explains the exit-128 clone failure: ComfyUI-Manager is attempting to clone the wrong slug.

Additional repository metadata is stale but secondary to the clone failure:

- `README.md` tells users not to install via direct git clone, but the listed Manager and Registry links are empty placeholders.
- `README.md` still shows an old development clone command for `jtydhr88/ComfyUI_frontend_vue_basic`.
- `.github/workflows/vite-build.yml` builds and runs `Comfy-Org/publish-node-action@main`, but that workflow acts after checkout/build and does not participate in a manual Manager `git clone` of the GitHub URL shown in the failure log.

---

## 3. Alternative Analysis

### Alternative A: Repository metadata publishes the wrong GitHub URL

Status: Confirmed.

Why it fits:

- The failing URL in the user log exactly matches the URL published in `pyproject.toml` manager-facing metadata.
- The actual repo slug from `origin` is different.
- The published URL returns 404, which is a direct cause of `git clone` exit 128.

### Alternative B: GitHub Actions publishing failure causes install failure

Status: Rejected as the direct cause.

Why it does not fit:

- The failure happens before checkout completes in the user's Manager flow.
- A GitHub Actions workflow cannot fix a raw clone of a nonexistent GitHub slug.
- The existing workflow is only relevant indirectly because it likely publishes the same bad metadata to the registry if left unchanged.

### Alternative C: External environment or network issue in the user's ComfyUI host

Status: Rejected as the primary cause.

Why it does not fit:

- The wrong URL deterministically 404s from GitHub itself.
- The correct public repository URL resolves normally.
- No host-specific evidence is needed once the requested clone target is provably wrong.

---

## 4. External Discovery

GitHub page fetch results:

- `https://github.com/sammykumar/ImageGen-Toolkit-Dev-Utils` resolves to the public repository.
- `https://github.com/sammykumar/imagegen_toolkit_dev_utils` returns HTTP 404.

This external check matches the local metadata mismatch and confirms the failure is not caused by missing releases or packages.

---

## 5. Proof of Concept

Minimal proof chain:

1. User log shows Manager cloning `https://github.com/sammykumar/imagegen_toolkit_dev_utils`.
2. `pyproject.toml` publishes that same URL in manager-facing metadata.
3. `.git/config` shows the real repository is `sammykumar/ImageGen-Toolkit-Dev-Utils`.
4. GitHub serves the real slug and 404s the published slug.
5. Therefore the Manager clone failure is caused by incorrect repository metadata, not by dependency installation, runtime import, or GitHub Actions build output.

---

## 6. Risk Assessment

- Required remediation is small and repo-side: update the published repository URL in `pyproject.toml` to the real slug, then republish registry metadata if ComfyUI Registry/Manager is sourcing from the published package metadata.
- `README.md` is not required to fix the clone failure, but leaving the stale Manager/Registry placeholders and old clone example will continue to mislead users.
- No workflow code change is required unless the publish pipeline is sourcing or transforming the wrong URL independently; current evidence points to bad input metadata, not a bad workflow implementation.
