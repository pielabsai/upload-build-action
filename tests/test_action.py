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
 printf '%s\\n' "$@" > "$ARGS_LOG"
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
                        GITHUB_OUTPUT=str(self.output), REQUEST_LOG=str(self.requests),
                        ARGS_LOG=str(self.root / "args"), DEBUG="false", GITHUB_RUN_ID="")

    def curl_args(self):
        return (self.root / "args").read_text().splitlines()

    def run_action(self, build, pr_number=""):
        replacements = {"inputs.build_path": str(build), "inputs.pie_api_key": "fixture-key",
                        "inputs.pr_number": pr_number, "inputs.repository": "calm/android",
                        "inputs.commit_sha": "a" * 40}
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

    def test_android_output_directory_rejected_before_packaging_or_upload(self):
        for extension in ("apk", "aab"):
            with self.subTest(extension=extension):
                build = self.root / extension
                build.mkdir()
                (build / f"release.{extension}").write_bytes(b"fixture")
                result = self.run_action(build)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Directory uploads must be iOS Simulator .app bundles", result.stdout)
                self.assertFalse(build.with_suffix(".zip").exists())
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
        for path in (str(build), str(build) + "/."):
            with self.subTest(path=path):
                result = self.run_action(path)
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

    def test_regular_upload_unchanged_without_pr_number(self):
        build = self.root / "app.apk"
        build.write_bytes(b"fixture")
        result = self.run_action(build)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        args = self.curl_args()
        self.assertEqual(args[-1], "https://api.pie.inc/v1/app/builds")
        self.assertFalse(any(arg.startswith("changeNumber=") for arg in args))

    def test_pr_number_uploads_pr_build_with_commit(self):
        build = self.root / "app.apk"
        build.write_bytes(b"fixture")
        self.env["GITHUB_RUN_ID"] = "991"
        result = self.run_action(build, pr_number="6615")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        args = self.curl_args()
        self.assertEqual(args[-1], "https://api.pie.inc/v1/app/builds/code-review")
        for field in ("provider=github", "repository=calm/android", "changeNumber=6615",
                      "commitSHA=" + "a" * 40, "pipelineID=991"):
            self.assertIn(field, args)
        self.assertIn("build_id=fixture-build", self.output.read_text())

    def test_pr_build_already_uploaded_is_success(self):
        build = self.root / "app.apk"
        build.write_bytes(b"fixture")
        self.env["TEST_HTTP_STATUS"] = "200"
        result = self.run_action(build, pr_number="6615")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("build_id=fixture-build", self.output.read_text())

    def test_regular_upload_still_requires_created(self):
        build = self.root / "app.apk"
        build.write_bytes(b"fixture")
        self.env["TEST_HTTP_STATUS"] = "200"
        result = self.run_action(build)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTP 200 (expected 201)", result.stdout)


if __name__ == "__main__":
    unittest.main()
