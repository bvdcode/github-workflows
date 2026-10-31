"""Validate release package versions before publishing to either registry."""

import argparse
import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


def validate_package(package: Path, expected_version: str) -> None:
    """Require exactly one package manifest with the expected version."""
    with ZipFile(package) as archive:
        manifests = [name for name in archive.namelist() if name.endswith(".nuspec")]
        if len(manifests) != 1:
            raise ValueError(f"{package.name}: expected exactly one nuspec manifest")
        metadata = ElementTree.fromstring(archive.read(manifests[0]))
        version = metadata.findtext("{*}metadata/{*}version")
    if version != expected_version:
        raise ValueError(
            f"{package.name}: expected version {expected_version}, received {version}"
        )


def validate_packages(directory: Path, version: str, manifest: Path) -> None:
    """Validate packages and write the list of ordinary packages to publish."""
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        raise ValueError("The expected version must be MajorMinorPatch")
    packages = sorted(directory.rglob("*.nupkg"))
    if not packages:
        raise ValueError("The artifact contains no nupkg files")
    for package in [*packages, *sorted(directory.rglob("*.snupkg"))]:
        validate_package(package, version)
    manifest.write_text(
        "".join(f"{package.resolve()}\n" for package in packages), encoding="utf-8"
    )


def main() -> None:
    """Read command arguments and validate the downloaded package artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("version")
    parser.add_argument("manifest", type=Path)
    arguments = parser.parse_args()
    validate_packages(arguments.directory, arguments.version, arguments.manifest)


if __name__ == "__main__":
    main()
