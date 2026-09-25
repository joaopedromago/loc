import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from loc_cli.core import LocError, Store
from loc_cli.discovery import Discovery, Detection, Installation
from loc_cli.install import Installer


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "state")
        self.discovery = Discovery(self.store, home=self.root, system="macos")
        self.discovery.brew_records = (set(), set())
        self.discovery.tool_records = ({}, [])
        self.runtime_probe = patch("loc_cli.install.Ollama.version", side_effect=LocError("fixture runtime unavailable"))
        self.runtime_probe.start()
        self.addCleanup(self.runtime_probe.stop)
        self.executable = self.root / "ollama"
        self.executable.write_text("#!/bin/sh\nexit 0\n")
        self.executable.chmod(0o755)

    def test_known_location_outside_path_is_present(self):
        with patch.object(self.discovery, "paths", return_value=[self.executable]):
            self.assertEqual(self.discovery.detect("ollama").status, "present")

    @unittest.skipIf(os.name == "nt", "symlink setup requires Windows privileges")
    def test_symlink_and_target_are_one_installation(self):
        link = self.root / "alias"
        link.symlink_to(self.executable)
        with patch.object(self.discovery, "paths", return_value=[link, self.executable]):
            self.assertEqual(len(self.discovery.detect("ollama").installations), 1)

    def test_multiple_copies_require_registration(self):
        second = self.root / "second"
        second.write_text("#!/bin/sh\nexit 0\n")
        second.chmod(0o755)
        with patch.object(self.discovery, "paths", return_value=[self.executable, second]):
            result = self.discovery.detect("ollama")
            self.assertEqual(result.status, "multiple")
            with self.assertRaises(LocError):
                result.require()

    def test_broken_executable_is_not_absent(self):
        self.executable.unlink()
        if os.name == "nt":
            self.skipTest("symlink permissions")
        self.executable.symlink_to(self.root / "missing")
        with patch.object(self.discovery, "paths", return_value=[self.executable]):
            self.assertEqual(self.discovery.detect("ollama").status, "unusable")

    def test_package_record_prevents_installation_without_executable(self):
        self.discovery.brew_records = (set(), {"ollama"})
        with patch.object(self.discovery, "paths", return_value=[]):
            result = self.discovery.detect("ollama")
        self.assertEqual(result.status, "unusable")
        self.assertEqual(Installer(self.store, self.discovery).plan("ollama")["action"], "reuse")

    def test_unreadable_records_do_not_establish_absence(self):
        self.discovery.brew_error = True
        with patch.object(self.discovery, "paths", return_value=[]):
            self.assertEqual(self.discovery.detect("llmfit").status, "unknown")

    def test_existing_application_data_is_uncertain(self):
        (self.root / ".ollama").mkdir()
        with patch.object(self.discovery, "paths", return_value=[]):
            self.assertEqual(self.discovery.detect("ollama").status, "unknown")

    def test_reuse_never_runs_installer(self):
        detection = Detection("ollama", "present", [Installation(str(self.executable), "manual", "test")])
        with patch.object(self.discovery, "detect", return_value=detection), patch("loc_cli.install.subprocess.run") as run:
            result = Installer(self.store, self.discovery).ensure("ollama", yes=True)
            self.assertEqual(result["action"], "reused")
            run.assert_not_called()

    def test_existing_unhealthy_install_is_not_reinstalled(self):
        detection = Detection("ollama", "unusable", [Installation(None, "manual", "test", False)])
        with patch.object(self.discovery, "detect", return_value=detection), patch("loc_cli.install.subprocess.run") as run:
            with self.assertRaises(LocError):
                Installer(self.store, self.discovery).ensure("ollama", yes=True)
            run.assert_not_called()

    def test_unknown_never_opens_browser_or_runs_installer(self):
        detection = Detection("ollama", "unknown", issues=["inaccessible"])
        with patch.object(self.discovery, "detect", return_value=detection), patch("loc_cli.install.webbrowser.open") as browser, patch("loc_cli.install.subprocess.run") as run:
            with self.assertRaises(LocError):
                Installer(self.store, self.discovery).ensure("ollama", yes=True)
            run.assert_not_called()
            browser.assert_not_called()

    def test_presence_rechecked_before_installation(self):
        absent = Detection("ollama", "absent")
        present = Detection("ollama", "present", [Installation(str(self.executable), "manual", "test")])
        with patch.object(self.discovery, "detect", side_effect=[absent, present]), patch("loc_cli.install.subprocess.run") as run:
            with self.assertRaises(LocError):
                Installer(self.store, self.discovery).ensure("ollama", yes=True)
            run.assert_not_called()

    def test_offline_missing_component_never_installs(self):
        with patch.object(self.discovery, "detect", return_value=Detection("ollama", "absent")), patch("loc_cli.install.subprocess.run") as run:
            with self.assertRaises(LocError):
                Installer(self.store, self.discovery).ensure("ollama", yes=True, offline=True)
            run.assert_not_called()

    def test_windows_registry_failure_is_unknown(self):
        if os.name == "nt":
            self.skipTest("Test covers missing winreg on another platform")
        discovery = Discovery(self.store, home=self.root, system="windows")
        with patch.object(discovery, "paths", return_value=[]):
            self.assertEqual(discovery.detect("llmfit").status, "unknown")

    def test_manual_install_needs_confirmation_even_with_yes(self):
        with patch.object(self.discovery, "detect", return_value=Detection("node", "absent")), patch("loc_cli.install.platform_name", return_value="unsupported"), patch("loc_cli.install.sys.stdin.isatty", return_value=False), patch("loc_cli.install.webbrowser.open") as browser:
            with self.assertRaises(LocError):
                Installer(self.store, self.discovery).ensure("node", yes=True)
            browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
