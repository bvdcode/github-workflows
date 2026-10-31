"""Exercise publication guards against inconsistent NuGet artifacts."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "actions"
    / "nuget-publish"
    / "validate_packages.py"
)


class PackageValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.packages = self.root / "packages"
        self.packages.mkdir()
        self.manifest = self.root / "packages.txt"

    def create_package(self, name: str, version: str) -> Path:
        package = self.packages / name
        package.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(package, "w") as archive:
            archive.writestr(
                "Package.nuspec",
                '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">'
                f"<metadata><id>Package</id><version>{version}</version></metadata>"
                "</package>",
            )
        return package

    def validate(self, version: str = "1.2.3") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(self.packages),
                version,
                str(self.manifest),
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def test_multiple_nested_packages_and_symbols(self) -> None:
        first = self.create_package("First.1.2.3.nupkg", "1.2.3")
        second = self.create_package("nested/Second.1.2.3.nupkg", "1.2.3")
        self.create_package("First.1.2.3.snupkg", "1.2.3")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            set(self.manifest.read_text().splitlines()), {str(first), str(second)}
        )

    def test_rejects_wrong_package_version(self) -> None:
        self.create_package("Package.nupkg", "1.2.4")
        self.assertNotEqual(self.validate().returncode, 0)
        self.assertFalse(self.manifest.exists())

    def test_rejects_wrong_symbol_version(self) -> None:
        self.create_package("Package.nupkg", "1.2.3")
        self.create_package("Package.snupkg", "1.2.2")
        self.assertNotEqual(self.validate().returncode, 0)

    def test_rejects_prerelease_expected_version(self) -> None:
        self.create_package("Package.nupkg", "1.2.3-dev.1")
        self.assertNotEqual(self.validate("1.2.3-dev.1").returncode, 0)

    def test_rejects_empty_artifact(self) -> None:
        self.assertNotEqual(self.validate().returncode, 0)

    def test_rejects_missing_nuspec(self) -> None:
        with ZipFile(self.packages / "Package.nupkg", "w") as archive:
            archive.writestr("readme.txt", "Package")
        self.assertNotEqual(self.validate().returncode, 0)
