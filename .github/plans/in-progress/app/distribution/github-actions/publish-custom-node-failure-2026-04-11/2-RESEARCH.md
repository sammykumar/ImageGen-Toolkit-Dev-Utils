# Research: Publish Custom Node Failure

**Date**: 2026-04-11  
**Agent**: research.agent  
**Status**: Complete  
**Related Plan**: `.github/plans/in-progress/app/distribution/github-actions/publish-custom-node-failure-2026-04-11/`

---

## 1. Context & Goals

### Business Objective

Determine why the GitHub Actions workflow `NodeJS with vite build + Publish to Comfy registry` fails in `Publish Custom Node` even though local install, build, and Python tests now pass.

### Technical Goals

Identify the most likely publish-step failure mode from repository and public run evidence, and name the smallest repository-side correction.

### Success Criteria

- [x] One primary root cause identified from available evidence
- [x] Minimal repo-side fix identified
- [x] Publish-on-PR behavior evaluated explicitly
- [x] Residual uncertainty from missing hosted logs documented

### Constraints

- Public run logs for the failing step are not visible while logged out.
- Research must rely on the visible run summary, repository workflow/configuration, and public documentation for GitHub Actions and `Comfy-Org/publish-node-action`.
- Do not edit source files; only author plan artifacts.

---

## 2. Codebase Analysis

The decisive repository fact is that the workflow publishes on both `push` and `pull_request` to `master`:

```yaml
on:
  push:
    branches: [ "master" ]
  pull_request:
    branches: [ "master" ]
```

The same job then always executes the publish action after a successful build:

```yaml
- name: Publish Custom Node
  uses: Comfy-Org/publish-node-action@main
  with:
    personal_access_token: ${{ secrets.REGISTRY_ACCESS_TOKEN }}
    skip_checkout: 'true'
```

Public run evidence shows the failing run was attached to pull request `#6` and that `Build` succeeded before `Publish Custom Node` failed. That narrows the problem to publish-time conditions, not local install/build/test behavior.

Repository metadata required for publishing appears to exist:

- `pyproject.toml` contains `[tool.comfy]` metadata, including `PublisherId`, `DisplayName`, and `Repository`.
- `pyproject.toml` contains a normal `[project]` version field (`0.0.2`).

That makes a missing-manifest diagnosis less likely than an event/authentication diagnosis.

External action documentation for `Comfy-Org/publish-node-action` recommends a push-driven publish workflow and assumes a repository secret named `REGISTRY_ACCESS_TOKEN`. GitHub documentation states that, for `pull_request` workflows from forked repositories, secrets other than `GITHUB_TOKEN` are not passed to the runner. Even when the PR is not from a fork, publishing on PR is still the wrong lifecycle point because a PR build is unmerged candidate code rather than trusted branch state.

---

## 3. Alternative Analysis

### Alternative A: Publish step is running in a `pull_request` context where the registry PAT is unavailable

Status: Most likely primary root cause.

Why it fits:

- The failing run is explicitly tied to PR `#6`.
- The only step that failed requires a repository secret: `secrets.REGISTRY_ACCESS_TOKEN`.
- GitHub does not expose repository secrets to runners for fork-originated `pull_request` workflows.
- Build succeeds first, which matches a failure caused by the first privileged step rather than source/build correctness.

Why this is enough to drive the fix even without the hidden log line:

- The workflow is structurally wrong to attempt a registry publish during PR validation.
- Gating publish to trusted `push` events eliminates the secret-availability failure mode and aligns the workflow with publish semantics.

### Alternative B: The registry token is missing or invalid for all events

Status: Plausible but not the primary repo-side conclusion.

Why it fits partially:

- The publish action depends on `REGISTRY_ACCESS_TOKEN`.
- Missing or revoked credentials would also fail specifically in the publish step.

Why it is not the primary conclusion:

- The visible run evidence already shows the workflow attempted to publish from a PR, which is independently incorrect.
- A valid secret would still leave the workflow able to publish unmerged PR state, so push-only gating is still required.
- Missing hosted logs prevent proving whether the exact runtime error was `missing token`, `unauthorized`, or another auth message.

### Alternative C: Missing Comfy registry metadata in the repository

Status: Rejected.

Why it does not fit:

- `pyproject.toml` already includes `[tool.comfy]` and the repository URL.
- The action's documented prerequisites are visibly present in the repo.
- If metadata were fatally incomplete, that would remain possible, but the PR-triggered privileged publish is a stronger and more direct explanation from the evidence we do have.

### Alternative D: `skip_checkout: 'true'` is the problem

Status: Unlikely.

Why it does not fit:

- The workflow already checked out the repository earlier in the same job.
- `skip_checkout: 'true'` is consistent with reusing the existing workspace.
- There is no evidence of missing files after build, and the action would still need the PAT regardless.

---

## 4. Root Cause Determination

The most likely primary root cause is that the workflow unconditionally runs `Comfy-Org/publish-node-action@main` during `pull_request` runs, including the observed failing PR `#6`, even though publishing requires privileged registry credentials and should only happen from trusted branch state.

In the observed run shape, the highest-probability concrete failure is that `secrets.REGISTRY_ACCESS_TOKEN` was unavailable to the PR-triggered runner or otherwise unusable in that context. The repository evidence does not prove the exact hidden log message, but it does prove the workflow currently attempts a privileged publish in a PR validation path where it should not.

---

## 5. Minimal Repo-Side Fix

Gate the publish step to push-only, ideally restricted to the protected branch as well. The smallest correction is a step-level condition such as:

```yaml
- name: Publish Custom Node
  if: github.event_name == 'push' && github.ref == 'refs/heads/master'
  uses: Comfy-Org/publish-node-action@main
  with:
    personal_access_token: ${{ secrets.REGISTRY_ACCESS_TOKEN }}
    skip_checkout: 'true'
```

This keeps PR validation for checkout/install/build intact while preventing publish from running in untrusted or semantically incorrect contexts.

---

## 6. Explicit Publish-Gating Position

Yes, the publish step should be gated to push-only.

Why:

- Publishing is a deployment/distribution action, not a PR validation action.
- PRs represent unmerged candidate state; publishing them risks releasing code that never lands on `master`.
- PR workflows can run without repository secrets when the PR originates from a fork or Dependabot, making the current configuration fragile by design.
- The upstream action documentation shows a push-oriented publishing pattern rather than a PR-driven one.

If later desired, publish could be tightened further with `paths: ["pyproject.toml"]`, tags, or manual dispatch. Those are optional improvements, not required to fix the observed failure.

---

## 7. Residual Uncertainty

Because the hosted logs for `Publish Custom Node` are hidden while logged out, this research cannot quote the exact action error string. Residual uncertainty is limited to the specific auth/publish message, for example:

- missing secret/token input
- invalid or expired registry token
- registry-side authorization rejection

That uncertainty does not materially change the minimal repo-side fix, because the workflow should not attempt publishing on `pull_request` in the first place.
