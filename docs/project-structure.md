# Project Structure

```text
CapCap/
├── ui/
│   ├── gui.py                 # Application entry point
│   ├── main_window.py         # Main-window behavior, adaptive layout, and signal handling
│   ├── i18n.py                # Internationalization catalog (Vietnamese/English)
│   ├── controllers/           # Pipeline, preview, and subtitle controllers
│   │   └── subtitle_controller.py # Translation prompt & pronoun review dialogs
│   ├── views/                 # Launcher, panels, preview, timeline, inspectors
│   ├── widgets/               # Native MPV preview and custom Qt widgets
│   ├── worker_adapters/       # QThread background worker adapters
│   └── utils/                 # UI, media, audio engine, and settings helpers
├── app/
│   ├── capcut/                # CapCut STT, TTS, signing, and draft integration
│   ├── workflows/             # Prepare, voice, and export workflows
│   ├── translation/           # AI translation framework
│   │   ├── context_analyzer.py # Dialogue context learning, rolling ledger, pronoun rules
│   │   ├── orchestrator.py    # Pipeline orchestration, batching, provider routing
│   │   ├── prompts.py         # Genre-specific translation presets
│   │   ├── srt_utils.py       # SRT parsing, timing, and formatting utilities
│   │   └── providers/         # Google AI Studio, OpenAI, Ollama, Google Translate, Bing Web
│   ├── engines/               # Whisper, OCR, TTS, FFmpeg adapters
│   ├── services/              # Project, resource, ASR, diarization services (model_utils.py)
│   ├── layers/                # Timeline track and layer domain models
│   ├── vieneu_tts.py          # VieNeu TTS and voice cloning integration
│   ├── ocr_processor.py       # OCR subtitle extraction
│   ├── whisper_processor.py   # Faster-Whisper integration
│   └── sensevoice_processor.py
├── tests/                     # Comprehensive automated test suite (350+ unit tests)
│   ├── test_portrait_workspace.py # Tests for adaptive 9:16 layout
│   ├── test_translation_context_review.py # Tests for pronoun review & feedback
│   └── ...
├── bin/                       # FFmpeg, MPV, on-demand CUDA runtime
├── installer/                 # Inno Setup script (CapCap_Setup.iss) and vc_redist.x64.exe
├── models/                    # Downloaded ASR, Piper, and diarization models
├── assets/                    # Icons, fonts, previews, voice samples, and image assets
│   ├── preview_1.png          # 16:9 Landscape workspace screenshot
│   ├── preview_2.png          # 9:16 Portrait workspace screenshot
│   ├── voices/                # Reference voice samples for cloning and preview
│   └── capcut/                # CapCut voice metadata definitions
├── docs/                      # Focused project documentation
├── release.md                 # Release notes and changelog
├── .env_example               # Optional environment template
└── requirements-*.txt         # Python dependency sets
```

Projects and generated artifacts are stored beneath `projects/`; temporary preview and processing files are stored beneath `temp/`.
