# Research: Tag Release Task and Publish Flow

**Date**: 2026-04-11  
**Agent**: vibe-flow  
**Status**: Complete  
**Related Plan**: `.github/plans/in-progress/app/distribution/github-actions/tag-release-task-and-publish-2026-04-11/`

---

## 1. Context & Goals

### Business Objective

Create an explicit, operator-driven release flow so publishing happens only when the user intentionally versions the package.

### Technical Goals

- Add a VS Code task that prompts for `patch`, `minor`, or `major`.
- Keep `npm version` in the release flow.
- Ensure the version used by the registry publish action is updated too.
- Restrict GitHub Actions publishing to tag pushes instead of ordinary `master` pushes.

### Success Criteria

- [x] The release task prompts for bump type.
- [x] The version source-of-truth mismatch is addressed.
- [x] PR validation remains intact.
- [x] Registry publishing only occurs on explicit version tags.

### Constraints

- The current publish system reads version from `pyproject.toml`, not `package.json`.
- The user wants `npm version` to remain the visible operator command.
- The frontend package scaffold should remain in the repo.

---

## 2. Codebase Analysis

### Existing Patterns

- `.github/workflows/vite-build.yml` currently builds on PRs and pushes to `master`.
- `package.json` contains npm scripts and now supports npm versioning.
- `pyproject.toml` contains the published package version (`[project].version = "0.0.2"`).

### Key Discovery

The failed publish log showed the registry rejected `node_version.version = '0.0.2'`, which came from `pyproject.toml`. That means `npm version` must be paired with a sync step; otherwise tag pushes would still publish stale Python metadata.

---

## 3. Alternative Analysis

### Option A: Use only `npm version`

Rejected.

Why:

- It updates `package.json`, but the registry publish action reads the Python project version.
- This would keep causing version drift or duplicate-version publish failures.

### Option B: Use `npm version` plus a sync hook for `pyproject.toml`

Recommended.

Why:

- Preserves the user-requested release command.
- Keeps frontend and Python metadata aligned.
- Works well with tag-based publishing.

### Option C: Stop using `npm version` and bump only `pyproject.toml`

Rejected.

Why:

- It ignores the user’s requested operator flow.

---

## 4. Recommendation

Use a VS Code task that prompts for bump type and runs an npm-based release flow that synchronizes `pyproject.toml`, then pushes commit plus tags to `master`. Change GitHub Actions to trigger publish runs on version tags and keep PR builds for validation.

---

## 5. Risks

| Risk | Impact | Likelihood | Mitigation |
| ---- | ------ | ---------- | ---------- |
| Package version drift returns | High | Medium | Sync `pyproject.toml` automatically during release |
| Tag pattern does not match npm’s default tag format | Medium | Low | Match `v*` tags in workflow |
| Release task pushes unintended branch state | Medium | Low | Push `HEAD:master` with `--follow-tags` explicitly |