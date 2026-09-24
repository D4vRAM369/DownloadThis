from pathlib import Path
import queue
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import downloadthis_modern as app


class UpdateUiTests(unittest.TestCase):
    def setUp(self):
        self.command = patch.object(app, "YTDLP_CMD", "/previous/yt-dlp")
        self.dialogs = patch.object(app, "messagebox")
        self.command.start()
        self.dialog = self.dialogs.start()
        self.addCleanup(self.command.stop)
        self.addCleanup(self.dialogs.stop)
        self.release = {"current_version": "2025.01.01", "latest_version": "2026.09.01"}
        self.ui = SimpleNamespace(
            _update_events=queue.Queue(), download_queue=queue.Queue(), dl_threads=set(),
            _updating_ytdlp=False, ytdlp_available=True, after=Mock(),
            _poll_update_events=Mock(), _run_update_worker=Mock(), _log_line=Mock(),
            sb_ytdlp_var=SimpleNamespace(set=Mock()),
        )

    def poll(self, event, result):
        self.ui._update_events.put((event, result))
        app.App._poll_update_events(self.ui)

    def test_cancel_does_not_install_or_change_engine(self):
        self.dialog.askokcancel.return_value = False
        with patch.object(app, "install_update") as install:
            self.poll("checked", self.release)
        self.dialog.askokcancel.assert_called_once()
        self.ui._run_update_worker.assert_not_called()
        install.assert_not_called()
        self.assertFalse(self.ui._updating_ytdlp)
        self.assertEqual(app.YTDLP_CMD, "/previous/yt-dlp")

    def test_accept_dispatches_install_to_worker(self):
        self.dialog.askokcancel.return_value = True
        with patch.object(app, "install_update") as install:
            self.poll("checked", self.release)
            self.ui._run_update_worker.assert_called_once_with(install, self.release, event="installed")
            install.assert_not_called()
        self.assertTrue(self.ui._updating_ytdlp)
        self.assertEqual(app.YTDLP_CMD, "/previous/yt-dlp")

    def test_active_or_queued_downloads_defer_prompt_until_idle(self):
        self.dialog.askokcancel.return_value = False
        self.ui.dl_threads.add("active")
        self.poll("checked", self.release)
        self.dialog.askokcancel.assert_not_called()
        self.ui.dl_threads.clear()
        self.ui.download_queue.put("https://example.com/audio")
        app.App._poll_update_events(self.ui)
        self.dialog.askokcancel.assert_not_called()
        self.ui.download_queue.get_nowait()
        app.App._poll_update_events(self.ui)
        self.dialog.askokcancel.assert_called_once()
        self.assertTrue(self.ui._update_events.empty())

    def test_install_results_change_command_only_on_success(self):
        self.ui._updating_ytdlp = True
        self.poll("installed_error", "Checksum mismatch")
        self.assertFalse(self.ui._updating_ytdlp)
        self.assertEqual(app.YTDLP_CMD, "/previous/yt-dlp")
        self.assertTrue(self.ui.ytdlp_available)
        self.dialog.showerror.assert_called_once()
        self.ui._updating_ytdlp = True
        self.ui.ytdlp_available = False
        self.poll("installed", "/managed/yt-dlp")
        self.assertFalse(self.ui._updating_ytdlp)
        self.assertEqual(app.YTDLP_CMD, "/managed/yt-dlp")
        self.assertTrue(self.ui.ytdlp_available)
        self.dialog.showinfo.assert_called_once()

    def test_check_failure_and_no_update_leave_engine_unchanged(self):
        self.poll("checked_error", "Network unavailable")
        self.poll("checked", None)
        self.assertEqual(app.YTDLP_CMD, "/previous/yt-dlp")
        self.dialog.askokcancel.assert_not_called()
        self.ui._run_update_worker.assert_not_called()
        self.ui.after.assert_called_with(200, self.ui._poll_update_events)

    def test_worker_only_uses_queue_and_runs_off_main_thread(self):
        # No Tk attributes exist on this object: workers can only post data.
        worker_state = SimpleNamespace(_update_events=queue.Queue())
        main_thread = threading.get_ident()
        app.App._run_update_worker(worker_state, threading.get_ident, event="checked")
        event, identity = worker_state._update_events.get(timeout=2)
        self.assertEqual(event, "checked")
        self.assertNotEqual(identity, main_thread)
        operation = Mock(side_effect=ValueError("download failed"))
        app.App._run_update_worker(worker_state, operation, "argument", event="installed")
        self.assertEqual(worker_state._update_events.get(timeout=2), ("installed_error", "download failed"))
        operation.assert_called_once_with("argument")
        self.assertEqual(self.dialog.mock_calls, [])

    def test_download_start_is_blocked_while_installing(self):
        # No destination/queue attributes: the guard must precede all download work.
        app.App._start_downloads(SimpleNamespace(_updating_ytdlp=True))
        self.dialog.showinfo.assert_called_once()


class EngineResolutionTests(unittest.TestCase):
    def test_source_and_frozen_windows_paths_prefer_managed_engine(self):
        for frozen in (False, True):
            with self.subTest(frozen=frozen), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = root / "engine/yt-dlp.exe"
                managed = root / "user/yt-dlp.exe"
                venv = root / "venv/Scripts/yt-dlp.exe"
                for binary in (bundle, managed, venv):
                    binary.parent.mkdir(parents=True, exist_ok=True)
                    binary.write_bytes(b"binary")
                    binary.chmod(0o755)
                with patch.object(app.sys, "platform", "win32"), \
                        patch.object(app.sys, "frozen", frozen, create=True), \
                        patch.object(app.sys, "executable", str(root / "downloadthis.exe") if frozen else "/python/python.exe"), \
                        patch.object(app, "__file__", str(root / "_internal/downloadthis_modern.py") if frozen else str(root / "downloadthis_modern.py")), \
                        patch.object(app, "managed_executable", return_value=managed):
                    self.assertEqual(app.resolve_ytdlp(), str(managed))
                    managed.unlink()
                    self.assertEqual(app.resolve_ytdlp(), str(bundle))
                    bundle.unlink()
                    self.assertEqual(app.resolve_ytdlp(), str(venv))
                    venv.unlink()
                    self.assertEqual(app.resolve_ytdlp(), "yt-dlp.exe")


if __name__ == "__main__":
    unittest.main()
