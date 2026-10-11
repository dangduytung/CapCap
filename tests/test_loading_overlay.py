import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(PROJECT_ROOT, "app")
UI_DIR = os.path.join(PROJECT_ROOT, "ui")
for p in (PROJECT_ROOT, APP_DIR, UI_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QWidget
from widgets.loading_overlay import MainWindowLoadingOverlay
from main_window import VideoTranslatorGUI
from ui.i18n import t

app = QApplication.instance() or QApplication([])


class TestMainWindowLoadingOverlay(unittest.TestCase):
    def setUp(self):
        self.parent = QWidget()
        self.parent.resize(1280, 720)
        self.parent.show()
        self.overlay = MainWindowLoadingOverlay(self.parent)

    def tearDown(self):
        self.overlay.dismiss(fade=False)
        self.overlay.deleteLater()
        self.parent.deleteLater()

    def test_initial_state_hidden(self):
        self.assertFalse(self.overlay.isVisible())

    def test_show_for_video(self):
        self.overlay.show_for_video("C:/path/to/my_video.mp4", max_timeout_ms=1000)
        self.assertTrue(self.overlay.isVisible())
        self.assertEqual(self.overlay.subtitle_label.text(), "my_video.mp4")
        self.assertTrue(self.overlay.subtitle_label.isVisible())

    def test_show_for_empty_video(self):
        self.overlay.show_for_video("", max_timeout_ms=1000)
        self.assertTrue(self.overlay.isVisible())
        self.assertFalse(self.overlay.subtitle_label.isVisible())

    def test_set_status(self):
        self.overlay.set_status("Custom status")
        self.assertEqual(self.overlay.status_label.text(), "Custom status")

    def test_dismiss_instant(self):
        self.overlay.show_for_video("video.mp4", max_timeout_ms=1000)
        self.assertTrue(self.overlay.isVisible())
        self.overlay.dismiss(fade=False)
        self.assertFalse(self.overlay.isVisible())

    def test_event_filter_layout_request(self):
        self.overlay.show_for_video("test.mp4")
        self.parent.resize(800, 600)
        ev = QEvent(QEvent.Type.LayoutRequest)
        handled = self.overlay.eventFilter(self.parent, ev)
        self.assertEqual(self.overlay.geometry(), self.parent.rect())

    def test_event_filter_window_event(self):
        win = QWidget()
        win.resize(1000, 700)
        central = QWidget(win)
        central.resize(1000, 700)
        overlay = MainWindowLoadingOverlay(central)
        overlay.show_for_video("test.mp4")
        ev = QEvent(QEvent.Type.Resize)
        overlay.eventFilter(win, ev)
        self.assertEqual(overlay.geometry(), central.rect())
        overlay.dismiss()
        win.deleteLater()

    def test_main_window_integration_methods(self):
        gui = MagicMock(spec=VideoTranslatorGUI)
        gui._loading_overlay = MagicMock(spec=MainWindowLoadingOverlay)
        gui._current_video_path = "test.mp4"

        VideoTranslatorGUI.show_loading_overlay(gui, "test.mp4", 2000)
        gui._loading_overlay.show_for_video.assert_called_once_with("test.mp4", 2000)
        gui._loading_overlay.setGeometry.assert_called_once()
        gui._loading_overlay.raise_.assert_called_once()

        VideoTranslatorGUI.hide_loading_overlay(gui, fade=True)
        gui._loading_overlay.dismiss.assert_called_once_with(fade=True)

    def test_show_completion(self):
        called = []
        def on_click():
            called.append(True)

        self.overlay.show_completion(
            title="✅ Clean Project Completed",
            status="Removed 5 files",
            button_text=t("Back to Launcher"),
            on_action=on_click,
        )
        self.assertTrue(self.overlay.isVisible())
        self.assertEqual(self.overlay.title_label.text(), "✅ Clean Project Completed")
        self.assertEqual(self.overlay.status_label.text(), "Removed 5 files")
        self.assertFalse(self.overlay.subtitle_label.isVisible())
        self.assertFalse(self.overlay.progress_bar.isVisible())
        self.assertTrue(self.overlay.action_btn.isVisible())
        self.assertEqual(self.overlay.action_btn.text(), t("Back to Launcher"))

        self.overlay.action_btn.click()
        self.assertEqual(called, [True])

        # Test show_for_video resets the card state
        self.overlay.show_for_video("sample.mp4")
        self.assertTrue(self.overlay.isVisible())
        self.assertFalse(self.overlay.action_btn.isVisible())
        self.assertTrue(self.overlay.progress_bar.isVisible())
        self.assertEqual(self.overlay.subtitle_label.text(), "sample.mp4")
        self.assertTrue(self.overlay.subtitle_label.isVisible())

    def test_load_video_project_exception_dismisses_overlay(self):
        gui = MagicMock(spec=VideoTranslatorGUI)
        gui.video_path_edit = MagicMock()
        gui.update_project_header = MagicMock(side_effect=RuntimeError("Simulated header crash"))
        gui.show_loading_overlay = MagicMock()
        gui.hide_loading_overlay = MagicMock()

        with self.assertRaises(RuntimeError):
            VideoTranslatorGUI.load_video_project(gui, "test.mp4")

        gui.show_loading_overlay.assert_called_once_with("test.mp4")
        gui.hide_loading_overlay.assert_called_once_with(fade=False)

    def test_native_video_surface_stays_hidden_while_project_is_loading(self):
        from widgets.mpv_video_view import MpvVideoView

        self.parent._project_loading_in_progress = True
        view = MpvVideoView(self.parent)
        try:
            view.video_surface.hide()
            view.show()
            self.assertFalse(view.video_surface.isVisible())
            view.hide()
            self.parent._project_loading_in_progress = False
            view.show()
            self.assertTrue(view.video_surface.isVisible())
        finally:
            view.hide()
            view.deleteLater()

    def test_preview_is_revealed_after_overlay_dismissal_and_skips_stale_callbacks(self):
        gui = MagicMock(spec=VideoTranslatorGUI)
        for name in ("video_path_edit", "transcript_text", "translated_text", "timeline", "media_player", "video_view"):
            setattr(gui, name, MagicMock())
        gui._loading_overlay = MagicMock(spec=MainWindowLoadingOverlay)
        gui._media_backend_ready = True
        gui.isVisible.return_value = True
        gui.show_loading_overlay.side_effect = lambda path: VideoTranslatorGUI.show_loading_overlay(gui, path)
        gui.hide_loading_overlay.side_effect = lambda **kw: VideoTranslatorGUI.hide_loading_overlay(gui, **kw)
        callbacks = []
        with patch("main_window.QTimer.singleShot", side_effect=lambda ms, cb: callbacks.append((ms, cb))), \
                patch("views.launcher.LauncherWindow.add_recent"), \
                patch("views.launcher._get_video_duration", return_value=10.0):
            VideoTranslatorGUI.load_video_project(gui, "test.mp4")
            _, load_media = callbacks.pop(0)
            load_media()
            gui.video_view.video_surface.show.assert_not_called()
            _, dismiss_overlay = callbacks.pop(0)
            dismiss_overlay()
            gui._loading_overlay.dismiss.assert_called_once_with(fade=False)
            gui.video_view.video_surface.show.assert_not_called()
            delay_ms, reveal_preview = callbacks.pop(0)
            self.assertEqual(delay_ms, 100)
            reveal_preview()
            gui.video_view.video_surface.show.assert_called_once()

            gui.video_view.video_surface.show.reset_mock()
            gui._project_loading_in_progress = True
            reveal_preview()
            gui._project_loading_in_progress = False
            gui.isVisible.return_value = False
            reveal_preview()
            gui.isVisible.return_value = True
            gui._current_video_path = os.path.abspath("another.mp4")
            reveal_preview()
            gui.video_view.video_surface.show.assert_not_called()


if __name__ == "__main__":
    unittest.main()
