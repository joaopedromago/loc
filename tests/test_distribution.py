import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loc_cli.core import LocError
from loc_cli.distribution import download_release, latest_release, self_update, self_uninstall


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.release = {"version": "0.2.0", "wheel_name": "loc_coding-0.2.0-py3-none-any.whl", "wheel_url": "https://example.test/wheel", "checksums_url": "https://example.test/SHA256SUMS", "update_available": True}

    def test_release_integrity_verified(self):
        content = b"wheel fixture"
        checksum = hashlib.sha256(content).hexdigest()
        with patch("loc_cli.distribution.fetch", side_effect=[(f"{checksum}  {self.release['wheel_name']}\n".encode(), {}), (content, {})]):
            path = download_release(self.release, self.root)
        self.assertEqual(path.read_bytes(), content)

    def test_checksum_mismatch_preserves_installation(self):
        with patch("loc_cli.distribution.fetch", side_effect=[(f"{'a' * 64}  {self.release['wheel_name']}\n".encode(), {}), (b"wrong", {})]):
            with self.assertRaises(LocError):
                download_release(self.release, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_release_rejects_unexpected_asset_host(self):
        data = {"tag_name": "v0.2.0", "assets": [{"name": self.release["wheel_name"], "browser_download_url": "https://untrusted.example/loc.whl"},
                                                       {"name": "SHA256SUMS", "browser_download_url": "https://untrusted.example/checksum"}]}
        with patch("loc_cli.distribution.fetch", return_value=(json.dumps(data).encode(), {})), self.assertRaises(LocError):
            latest_release()

    def test_self_update_never_switches_unknown_owner(self):
        with patch("loc_cli.distribution.latest_release", return_value=self.release), patch("loc_cli.distribution.installation_owner", return_value={"owner": "unknown"}), patch("loc_cli.distribution.subprocess.run") as run:
            with self.assertRaises(LocError):
                self_update(yes=True)
            run.assert_not_called()

    def test_update_check_never_mutates(self):
        with patch("loc_cli.distribution.latest_release", return_value=self.release), patch("loc_cli.distribution.installation_owner", return_value={"owner": "pipx"}), patch("loc_cli.distribution.subprocess.run") as run:
            result = self_update(check=True)
            self.assertTrue(result["update_available"])
            run.assert_not_called()

    def test_self_uninstall_preview_preserves_user_data(self):
        with patch("loc_cli.distribution.installation_owner", return_value={"owner": "loc-bootstrap"}), patch("loc_cli.distribution.subprocess.run") as run:
            result = self_uninstall(dry_run=True)
            self.assertIn("profiles", result["preserved"])
            run.assert_not_called()

    def test_bootstrap_exits_without_installer_when_loc_exists(self):
        spec = importlib.util.spec_from_file_location("bootstrap", Path(__file__).resolve().parents[1] / "scripts/install.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "find_existing", return_value="/existing/loc"), patch.object(module.subprocess, "run") as run:
            self.assertEqual(module.main(["--yes"]), 0)
            run.assert_not_called()

    def test_bootstrap_manager_inspection_failure_is_not_absence(self):
        spec = importlib.util.spec_from_file_location("bootstrap", Path(__file__).resolve().parents[1] / "scripts/install.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module.shutil, "which", return_value="/fixture/uv"), patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "")), patch.object(module.Path, "exists", return_value=False), patch.object(module.Path, "is_symlink", return_value=False):
            with self.assertRaises(RuntimeError):
                module.find_existing(self.root / "prefix")


if __name__ == "__main__":
    unittest.main()
