import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for folder in (PROJECT_ROOT, PROJECT_ROOT / "app", PROJECT_ROOT / "ui"):
    sys.path.insert(0, str(folder))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QObject, QSettings
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout, QWidget
from ui.main_window import VideoTranslatorGUI
from ui.utils.display_utils import set_windows_normal_geometry
from ui.views import advanced_tabs, start_panel

app = QApplication.instance() or QApplication([])


class _WindowShowObserver(QObject):
    def __init__(self):
        super().__init__()
        self.windows = []

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and isinstance(obj, QWidget) and obj.isWindow():
            self.windows.append(type(obj).__name__)
        return False


class TestInitialVisibility(unittest.TestCase):
    def setUp(self):
        self.observer = _WindowShowObserver()
        app.installEventFilter(self.observer)

    def tearDown(self):
        app.removeEventFilter(self.observer)

    def test_expanded_sections_do_not_show_temporary_windows_during_construction(self):
        wrapper, content_layout = start_panel._build_collapsible_section("Media")
        try:
            self.assertEqual(self.observer.windows, [])
            self.assertIs(content_layout.parentWidget().parentWidget(), wrapper)
        finally:
            wrapper.close()
            wrapper.deleteLater()

    def test_advanced_panel_does_not_show_temporary_windows_during_construction(self):
        parent = QWidget()
        left_layout = QVBoxLayout(parent)
        gui = SimpleNamespace(
            on_advanced_toggled=MagicMock(), make_helper_label=lambda text: QLabel(text),
            _runtime_logs=[], export_runtime_logs=MagicMock(), clear_log=MagicMock(),
            import_original_srt_btn=QWidget(parent),
        )
        try:
            with patch.object(advanced_tabs, "_build_hidden_runtime_widgets"), \
                    patch.object(advanced_tabs, "_build_audio_source_controls", return_value=QWidget(parent)):
                advanced_tabs.build_advanced_group(gui, left_layout)
            self.assertEqual(self.observer.windows, [])
        finally:
            parent.close()
            parent.deleteLater()

    def test_settings_do_not_show_orphan_labels_before_dialog_exec(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            for remote in (False, True):
                for engine in ("sensevoice", "whisper", "ocr"):
                    with self.subTest(remote=remote, engine=engine):
                        self.observer.windows.clear()
                        gui = QWidget()
                        gui.settings = QSettings(str(Path(tmp_dir) / "settings.ini"), QSettings.IniFormat)
                        gui.get_transcription_engine = lambda: engine
                        gui.get_whisper_model_name = lambda: "base"
                        gui.selected_voice_engine = "piper"
                        gui.selected_whisper_model_name = "base"
                        gui.open_resource_manager_dialog = MagicMock()
                        gui.log = MagicMock()
                        try:
                            with patch("ui.main_window.is_remote_profile", return_value=remote), \
                                    patch.dict(os.environ, {"OCR_BACKEND": "rapidocr", "OPENAI_PROVIDER": "google"}), \
                                    patch.object(QDialog, "exec", return_value=QDialog.Rejected):
                                VideoTranslatorGUI.open_model_settings_dialog(gui)
                            self.assertEqual(self.observer.windows, [])
                        finally:
                            gui.close()
                            gui.deleteLater()

    def test_editor_construction_does_not_show_temporary_windows(self):
        with patch("ui.main_window.QTimer.singleShot"), \
                patch("ui.main_window.apply_windows_dark_title_bar_impl"):
            gui = VideoTranslatorGUI()
        try:
            self.assertEqual(self.observer.windows, [])
            self.assertFalse(gui.isVisible())
        finally:
            gui._terminate_workers()
            gui.deleteLater()

    def test_setting_restore_geometry_keeps_hidden_window_hidden(self):
        import ctypes

        for visible in (False, True):
            with self.subTest(visible=visible):
                user32 = MagicMock()
                user32.GetWindowPlacement.side_effect = lambda hwnd, ptr: (setattr(ptr._obj, "showCmd", 3) or 1)
                captured = []
                def save_placement(hwnd, ptr):
                    wp = ptr._obj
                    captured.append((wp.showCmd, wp.rcNormalPosition.left, wp.rcNormalPosition.top,
                                     wp.rcNormalPosition.right, wp.rcNormalPosition.bottom))
                    return 1
                user32.SetWindowPlacement.side_effect = save_placement
                widget = MagicMock()
                widget.winId.return_value = 123
                widget.isVisible.return_value = visible
                with patch("ui.utils.display_utils.sys.platform", "win32"), \
                        patch.object(ctypes, "windll", SimpleNamespace(user32=user32), create=True):
                    self.assertTrue(set_windows_normal_geometry(widget, 10, 20, 800, 600))
                self.assertEqual(captured, [(3 if visible else 0, 10, 20, 810, 620)])


if __name__ == "__main__":
    unittest.main()
