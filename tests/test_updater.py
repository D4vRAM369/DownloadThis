import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import ytdlp_updater as updater


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.system = patch.object(updater.platform, "system", return_value="Linux")
        self.machine = patch.object(updater.platform, "machine", return_value="x86_64")
        self.system.start()
        self.machine.start()
        self.addCleanup(self.system.stop)
        self.addCleanup(self.machine.stop)
        self.info = {
            "current_version": "2025.01.01", "latest_version": "2026.09.01",
            "asset_name": "yt-dlp_linux",
            "asset_url": f"{updater.RELEASE_URL}/2026.09.01/yt-dlp_linux",
            "checksums_url": f"{updater.RELEASE_URL}/2026.09.01/SHA2-256SUMS",
        }
        self.release = json.dumps({
            "tag_name": self.info["latest_version"],
            "assets": [
                {"name": "yt-dlp_linux", "browser_download_url": self.info["asset_url"]},
                {"name": "SHA2-256SUMS", "browser_download_url": self.info["checksums_url"]},
            ],
        }).encode()

    def test_current_or_newer_version_does_not_update(self):
        for version in ("2026.09.01", "2026.10.01", "2026.09.01.123456"):
            with self.subTest(version=version), patch.object(updater, "_read", return_value=self.release), \
                    patch.object(updater, "_version", return_value=version):
                self.assertIsNone(updater.check_for_update("yt-dlp"))

    def test_old_and_absent_engines_offer_update(self):
        for version in ("2025.01.01", FileNotFoundError()):
            kwargs = {"side_effect": version} if isinstance(version, Exception) else {"return_value": version}
            with self.subTest(version=version), patch.object(updater, "_read", return_value=self.release), \
                    patch.object(updater, "_version", **kwargs):
                info = updater.check_for_update("yt-dlp")
                self.assertEqual(info["latest_version"], "2026.09.01")
                self.assertEqual(info["current_version"], "" if isinstance(version, Exception) else version)

    def test_install_verifies_digest_and_version_before_replacing(self):
        payload = b"new executable"
        for scenario in ("success", "digest mismatch", "wrong version", "unrunnable"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "yt-dlp"
                target.write_bytes(b"old executable")
                digest = hashlib.sha256(payload if scenario != "digest mismatch" else b"other").hexdigest()
                checksums = f"{digest}  yt-dlp_linux\n".encode()
                version_args = {"return_value": "wrong" if scenario == "wrong version" else "2026.09.01"}
                if scenario == "unrunnable":
                    version_args = {"side_effect": subprocess.CalledProcessError(1, "yt-dlp")}
                with patch.object(updater, "managed_executable", return_value=target), \
                        patch.object(updater, "_read", return_value=checksums), \
                        patch.object(updater, "_open", return_value=io.BytesIO(payload)), \
                        patch.object(updater, "_version", **version_args):
                    if scenario == "success":
                        self.assertEqual(updater.install_update(self.info), str(target))
                        self.assertEqual(target.read_bytes(), payload)
                        self.assertTrue(target.stat().st_mode & 0o100)
                    else:
                        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                            updater.install_update(self.info)
                        self.assertEqual(target.read_bytes(), b"old executable")
                    self.assertEqual(list(Path(directory).iterdir()), [target])

    def test_unsupported_platform_and_untrusted_urls_fail_before_download(self):
        with patch.object(updater.platform, "machine", return_value="riscv64"):
            with self.assertRaises(ValueError):
                updater.check_for_update("yt-dlp")
        with patch.object(updater, "_read") as read:
            for url in ("http://github.com/yt-dlp", "https://evil.example/yt-dlp"):
                with self.assertRaises(ValueError):
                    updater.install_update({**self.info, "asset_url": url})
            read.assert_not_called()
        with self.assertRaises(ValueError):
            updater._OfficialRedirects().redirect_request(None, None, 302, "", {}, "https://evil.example/file")

    def test_managed_paths_and_official_assets(self):
        with patch.dict(updater.os.environ, {"XDG_DATA_HOME": "/tmp/downloadthis-test"}):
            self.assertEqual(updater.managed_executable(), Path("/tmp/downloadthis-test/downloadthis/bin/yt-dlp"))
        with patch.object(updater.platform, "system", return_value="Windows"), \
                patch.object(updater.platform, "machine", return_value="AMD64"), \
                patch.dict(updater.os.environ, {"LOCALAPPDATA": "/tmp/local-app-data"}):
            self.assertEqual(updater.managed_executable(), Path("/tmp/local-app-data/DownloadThis/bin/yt-dlp.exe"))
            self.assertEqual(updater._asset_name(), "yt-dlp.exe")
        with patch.object(updater.platform, "machine", return_value="aarch64"):
            self.assertEqual(updater._asset_name(), "yt-dlp_linux_aarch64")


if __name__ == "__main__":
    unittest.main()
