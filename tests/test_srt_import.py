import copy
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "app", PROJECT_ROOT / "ui"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QMessageBox, QTextEdit, QWidget
from ui import i18n
from ui.controllers.subtitle_controller import SubtitleController
from ui.gui import _LogTee, _RuntimeLogCollector
from ui.helpers.srt_helpers import diagnose_srt_timeline, extract_subtitle_text_entries, validate_srt_text
from ui.main_window import VideoTranslatorGUI
from ui.utils.display_utils import log_message

app = QApplication.instance() or QApplication([])


class TestTranslatedSrtImport(unittest.TestCase):
    def setUp(self):
        previous_language = i18n.current_language()
        i18n.install_language_filter(app)
        i18n._current_language = "vi"
        self.addCleanup(setattr, i18n, "_current_language", previous_language)
        self.folder = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.folder) / "translated.srt"
        self.gui = QWidget()
        self.addCleanup(self.gui.deleteLater)
        gui = self.gui
        gui.workspace_root = self.folder
        gui.srt_output_folder_edit = QLineEdit(self.folder, gui)
        gui.translated_text = QTextEdit(gui)
        gui.keep_timeline_cb = QCheckBox(gui)
        gui.keep_timeline_cb.setChecked(True)
        gui.current_segments = [
            {"start": 0.0, "end": 2.0, "text": "Original 1", "speaker": "speaker_1"},
            {"start": 2.0, "end": 4.0, "text": "Original 2", "speaker": "speaker_2"},
        ]
        gui.current_translated_segments = [dict(segment, text=f"Old translation {i}")
                                           for i, segment in enumerate(gui.current_segments)]
        gui.translated_text.setText("Old translation")
        gui.processed_artifacts = {}
        gui.last_translated_srt_path = "old.srt"
        gui.validate_srt_text = validate_srt_text
        gui.diagnose_srt_timeline = diagnose_srt_timeline
        gui.extract_subtitle_text_entries = extract_subtitle_text_entries
        gui._completed_translation_provider_label = lambda: "google"
        gui.apply_edited_translation = SubtitleController(gui).apply_edited_translation
        for name in ("log", "_dict_segments_to_models", "apply_segments_to_timeline",
                     "persist_translation_project_data", "refresh_detected_speakers_section",
                     "_refresh_speaker_subtitle_colors_if_needed", "refresh_ui_state",
                     "schedule_auto_frame_preview"):
            setattr(gui, name, MagicMock())
        self.enterContext(patch("ui.main_window.QFileDialog.getOpenFileName", return_value=(str(self.path), "")))
        self.success = self.enterContext(patch("ui.main_window.QMessageBox.information"))

    def choose(self, role):
        def click_choice():
            box = app.activeModalWidget()
            button = next(button for button in box.buttons() if box.buttonRole(button) == role)
            QTest.mouseClick(button, Qt.LeftButton)
        QTimer.singleShot(0, click_choice)

    def test_continue_replaces_translation_with_fewer_or_more_cues(self):
        original = copy.deepcopy(self.gui.current_segments)
        previous_translation = copy.deepcopy(self.gui.current_translated_segments)
        for count in (1, 3):
            with self.subTest(count=count):
                self.gui.current_translated_segments = copy.deepcopy(previous_translation)
                text = "\n\n".join(f"{i + 1}\n00:00:0{i},500 --> 00:00:0{i + 1},000\nNew {i + 1}"
                                   for i in range(count))
                self.path.write_text(text, encoding="utf-8")
                self.choose(QMessageBox.AcceptRole)
                VideoTranslatorGUI.import_translated_srt(self.gui)
                self.assertEqual([segment["text"] for segment in self.gui.current_translated_segments],
                                 [f"New {i + 1}" for i in range(count)])
                self.assertEqual(self.gui.current_translated_segments[0]["start"], 0.5)
                self.assertEqual(self.gui.current_segments, original)
                self.assertEqual(self.gui.last_translated_srt_path, str(self.path))
                self.assertEqual(self.gui.processed_artifacts["srt_translated"], str(self.path))
                self.gui.persist_translation_project_data.assert_called_with(
                    self.gui.current_translated_segments, str(self.path))
                self.success.assert_called()

    def test_cancel_keeps_existing_translation(self):
        previous = copy.deepcopy(self.gui.current_translated_segments)
        self.path.write_text("1\n00:00:00,500 --> 00:00:01,000\nNew translation", encoding="utf-8")
        self.choose(QMessageBox.RejectRole)
        VideoTranslatorGUI.import_translated_srt(self.gui)
        self.assertEqual(self.gui.current_translated_segments, previous)
        self.assertEqual(self.gui.translated_text.toPlainText(), "Old translation")
        self.assertEqual(self.gui.last_translated_srt_path, "old.srt")
        self.gui.persist_translation_project_data.assert_not_called()
        self.success.assert_not_called()


class TestRuntimeLogForwarding(unittest.TestCase):
    def test_tee_logs_once_to_ui_and_keeps_log_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "runtime.log"
            for attached in (True, False):
                with self.subTest(attached=attached):
                    gui = MagicMock()
                    collector = _RuntimeLogCollector.__new__(_RuntimeLogCollector)
                    collector._window = gui if attached else None
                    collector._pending = []
                    collector._file_path = str(path)
                    output = io.StringIO()
                    with patch.object(sys, "stdout", _LogTee(output, collector)):
                        log_message(gui, "[Import] Message")
                    gui.runtime_log_received.emit.assert_called_once_with("[Import] Message")
                    self.assertEqual(output.getvalue(), "[Import] Message\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "[Import] Message\n" * 2)


if __name__ == "__main__":
    unittest.main()
