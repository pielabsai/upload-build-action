"""Run the actual composite-action scripts with a local HTTP client stub."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
import zipfile


ACTION = Path(__file__).resolve().parents[1] / "action.yml"


def action_scripts():
    blocks = re.findall(r"      run: \|\n((?:        .*\n|\n)+)", ACTION.read_text())
    if len(blocks) != 2:
        raise AssertionError("Expected the build-check and upload scripts")
    return ["\n".join(line[8:] for line in block.splitlines()) for block in blocks]


class UploadActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.requests = self.root / "requests"
        self.output = self.root / "output"
        curl = self.bin / "curl"
        curl.write_text("""#!/bin/bash
 echo called >> "$REQUEST_LOG"
 while [ "$#" -gt 0 ]; do
   if [ "$1" = '-o' ]; then
     shift
     printf '%s' '{"data":{"buildID":"fixture-build"}}' > "$1"
   fi
   shift
 done
 printf '%s' "${TEST_HTTP_STATUS:-201}"
 """)
        curl.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        GITHUB_OUTPUT=str(self.output), REQUEST_LOG=str(self.requests), DEBUG="false")

    def run_action(self, build):
        replacements = {"inputs.build_path": str(build), "inputs.pie_api_key": "fixture-key"}
        result = None
        for script in action_scripts():
            for expression, value in replacements.items():
                script = script.replace("${{ " + expression + " }}", value)
            self.assertNotIn("${{", script)
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                                    cwd=self.root, env=self.env, text=True, capture_output=True)
            if result.returncode:
                return result
            outputs = dict(line.split("=", 1) for line in self.output.read_text().splitlines())
            replacements["steps.build_check.outputs.build_path"] = outputs["build_path"]
        return result

    def test_bundle_rejected_before_upload(self):
        for name in ("app.aab", "app.AAB", "app.AaB", "My app.aab"):
            with self.subTest(name=name):
                build = self.root / name
                build.write_bytes(b"fixture")
                result = self.run_action(build)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Android App Bundles (.aab) are unsupported. Upload an .apk instead.", result.stdout)
                self.assertFalse(self.requests.exists())
                self.assertFalse(self.output.exists())

    def test_supported_files_upload(self):
        for name in ("app.apk", "app.APK", "My app.zip", "app.APP"):
            with self.subTest(name=name):
                build = self.root / name
                build.write_bytes(b"fixture")
                result = self.run_action(build)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("build_id=fixture-build", self.output.read_text())
        self.assertEqual(self.requests.read_text().splitlines(), ["called"] * 4)

    def test_simulator_directory_keeps_app_at_archive_root(self):
        build = self.root / "My App.app"
        build.mkdir()
        (build / "Info.plist").write_text("fixture")
        result = self.run_action(build)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with zipfile.ZipFile(self.root / "My App.app.zip") as archive:
            self.assertIn("My App.app/Info.plist", archive.namelist())

    def test_api_rejection_does_not_emit_build_id(self):
        build = self.root / "app.zip"
        build.write_bytes(b"fixture")
        self.env["TEST_HTTP_STATUS"] = "400"
        result = self.run_action(build)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTP 400", result.stdout)
        self.assertNotIn("build_id=", self.output.read_text())


if __name__ == "__main__":
    unittest.main()
