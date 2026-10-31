# GitHub Workflows

Reusable checks, package and image publication, version calculation, and GitHub Releases for .NET, Node.js, Python, and Docker projects.

Project workflows own their triggers and dependencies. Shared workflows own the Actions and their pinned versions. Pushes to `develop` and pull requests run checks. Pushes to `main` run the same checks before version calculation, artifact publication, and release creation.

## Workflows

| Workflow | Purpose | Required inputs |
| --- | --- | --- |
| `dotnet-checks.yml` | Restore, build, optional formatting, tests, and test results | `project`, `dotnet-version` |
| `node-checks.yml` | Install, lint, optional type checks, tests, and build | `node-version` |
| `python-checks.yml` | Install, lint, type checks, and tests | `python-version`, `install-command` |
| `docker-checks.yml` | Build an image without publishing it | None |
| `dotnet-pack.yml` | Build and upload packages with the requested MajorMinorPatch version | `projects`, `dotnet-version`, `version` |
| `docker-publish.yml` | Build once and publish matching tags to Docker Hub and GHCR | `version`, `dockerhub-image`, `ghcr-image` |
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

Complete pipelines are available in [examples/nuget.yml](examples/nuget.yml) and [examples/docker.yml](examples/docker.yml). Replace project paths, SDK versions, image names, and credential mappings with the project configuration. Give publishing permissions only to the corresponding jobs. The examples serialize runs on main and cancel outdated development checks.

## Project commands

Node.js and Python callers can set `working-directory` and replace the install, lint, type-check, test, and build commands exposed by each workflow. An empty optional command skips that check; omit only checks the project does not provide.

.NET callers can set `runner`, `configuration`, `locked-mode`, `format`, `run-tests`, `test-filter`, and `test-results-name`. SDK versions are explicit so adopting shared checks does not upgrade a project's runtime. Test results are retained for seven days. Keep an existing unit-test filter in `test-filter`; give each .NET call a distinct `test-results-name` when a project uses multiple calls on the same runner OS.

The four checks workflows also accept `repository` and `ref`, defaulting to the calling repository and commit. The CI workflow uses these inputs to exercise the workflows against fixed public projects. Docker checks use a local build fixture.

## NuGet publication

`dotnet-pack.yml` packs the listed projects or solutions with the explicit SDK version. It sets `Version` and `PackageVersion` to the requested three-part version and uploads the `nuget-packages` artifact. `projects` accepts multiple paths separated by newlines. Native packages can keep their existing build job and supply a package artifact directly.

`actions/nuget-publish` downloads that artifact, checks every package and symbol-package version, and publishes the same packages to NuGet.org and the calling owner's GitHub Packages registry. GitHub Packages receives ordinary packages; NuGet.org also receives adjacent symbol packages. Both feeds use duplicate-version skipping for reruns. `publish` defaults to `false`, which validates the artifact without logging in or uploading packages. `publish: true` requires `main` outside a pull request.

Select `authentication` explicitly:

- `oidc`: supply `nuget-user` and grant the calling job `id-token: write`.
- `api-key`: supply `nuget-api-key` from the existing NuGet secret.

Always supply `github-packages-token`. The example uses `github.token` with `packages: write`; an existing package may require its current publishing token or a repository access grant. No credential is chosen automatically.

The publisher is a composite action and must run directly in the project's ordinary job. Keep the original workflow filename and any `environment` used by its NuGet policy. NuGet validates the repository and `job_workflow_ref`; putting the OIDC exchange inside a cross-repository reusable workflow changes that identity. See the [NuGet policy validator](https://github.com/NuGet/NuGetGallery/blob/main/src/NuGetGallery.Services/Authentication/Federated/GitHubTokenPolicyValidator.cs).

For API-key authentication, replace the OIDC inputs in the example with:

```yaml
authentication: api-key
nuget-api-key: ${{ secrets.NUGET_KEY }}
```

## Docker publication

`docker-publish.yml` builds once and pushes that build to both image names. The default tags are `<version>` and `latest`; `additional-tags` adds suffixes to both registries, and `tag-latest: false` disables the moving tag. Image names must be lowercase. `ghcr-image` includes the `ghcr.io/` prefix.

The workflow accepts `context`, `file`, `target`, `build-args`, `platforms`, `runner`, and `cache-scope`. Non-default platforms enable QEMU. BuildKit secret definitions are passed through the `BUILD_SECRETS` secret, using the format accepted by `docker/build-push-action`.

Publication requires `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, and `GHCR_TOKEN`. Map each one explicitly to the existing project credential. Using `github.token` for GHCR requires `packages: write` and access to the target package. Outputs expose `tags` and the published image `digest`.

`publish` defaults to `false`, so the workflow can build and validate tags without registry credentials. With `publish: true`, publication runs only on `main` outside a pull request. A development image such as Cotton's `dev` channel retains its separate development publication job.

## Versions

Use `@v1` to receive compatible releases after the complete CI passes. Use a full tag such as `@v1.0.0` to keep a fixed version. Action versions are pinned centrally in the reusable workflows. A new major workflow interface uses a new major tag.

## Validation

CI validates workflows and copyable examples with actionlint, runs .NET, Node.js, and Python checks, and checks package-version guards. It packs a real public .NET project, exercises both NuGet authentication configurations without publication, and builds a Docker fixture for amd64 and arm64 while checking both registry tag sets. Real registry uploads require project credentials and are not performed by these fixtures. Releases and major-tag promotion run only after all checks pass on main.
