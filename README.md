# GitHub Workflows

Reusable checks, version calculation, and GitHub Releases for .NET, Node.js, Python, and Docker projects.

Project workflows own their triggers and dependencies. Shared workflows own the Actions and their pinned versions. Pushes to `develop` and pull requests run checks. Pushes to `main` run the same checks before version calculation, artifact publication, and release creation.

## Workflows

| Workflow | Purpose | Required inputs |
| --- | --- | --- |
| `dotnet-checks.yml` | Restore, build, optional formatting, tests, and test results | `project`, `dotnet-version` |
| `node-checks.yml` | Install, lint, optional type checks, tests, and build | `node-version` |
| `python-checks.yml` | Install, lint, type checks, and tests | `python-version`, `install-command` |
| `docker-checks.yml` | Build an image without publishing it | None |
| `gitversion.yml` | Calculate GitVersion 6.8.2 outputs from project history and configuration | None |
| `release.yml` | Create a GitHub Release using the triggering commit's complete message | `version` |

`gitversion.yml` exposes the three-part `version` output from `MajorMinorPatch`, along with `major`, `assembly-version`, `file-version`, `commits-since-version-source`, and `sha`. It uses the project's existing GitVersion configuration.

`release.yml` runs on `main`, creates `v<version>`, and uses `ncipollo/release-action`. Its optional `artifact-name` input attaches files from an uploaded artifact. Its caller must grant `contents: write`.

## .NET project

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

permissions:
  contents: read

jobs:
  checks:
    uses: bvdcode/github-workflows/.github/workflows/dotnet-checks.yml@v1
    with:
      project: src/Application.sln
      dotnet-version: 10.0.x

  version:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: checks
    uses: bvdcode/github-workflows/.github/workflows/gitversion.yml@v1
```

Place artifact build and publication jobs after `version`, and make release creation depend on successful publication. Give publishing permissions only to the corresponding jobs.

## Project commands

Node.js and Python callers can set `working-directory` and replace the install, lint, type-check, test, and build commands exposed by each workflow. An empty optional command skips that check; omit only checks the project does not provide.

.NET callers can set `runner`, `configuration`, `locked-mode`, `format`, and `run-tests`. SDK versions are explicit so adopting shared checks does not upgrade a project's runtime. Test results are retained for seven days.

The four checks workflows also accept `repository` and `ref`, defaulting to the calling repository and commit. The CI workflow uses these inputs to exercise the workflows against fixed public projects. Docker checks use a local build fixture.

## Versions

Use `@v1` to receive compatible releases after the complete CI passes. Use a full tag such as `@v1.0.0` to keep a fixed version. Action versions are pinned centrally in the reusable workflows. A new major workflow interface uses a new major tag.

## Validation

CI validates every workflow with actionlint, runs .NET, Node.js, and Python checks, builds the Docker fixture, and calculates the repository version before creating a release.
