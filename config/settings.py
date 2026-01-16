import logging
from pathlib import Path

LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
LOG_DATEFMT = "%H:%M:%S"

ROOT_DIR = Path(__file__).resolve().parents[1]
SPEAKER_MODEL_PATH = str(ROOT_DIR / "audio" / "speaker" / "models" / "kokoro-v1.0.onnx")
SPEAKER_VOICES_PATH = str(ROOT_DIR / "audio" / "speaker" / "models" / "voices-v1.0.bin")
SPEAKER_VOICE_NAME = "bm_lewis"
SPEAKER_OUTPUT_GAIN = 1.6
SPEAKER_LANG = "en-gb"
SPEAKER_SPEED = 1.0

MIC_TARGET_DEVICE_NAME = "Yeti Stereo Microphone"
MIC_SAMPLE_RATE = 16000
MIC_NATIVE_RATE = 48000
MIC_BLOCK_SIZE = 4096
MIC_THRESHOLD = 0.02
MIC_SILENCE_DURATION = 2.5
MIC_MIN_UTTERANCE_SECONDS = 1.0
MIC_CALIBRATION_SECONDS = 1.0
MIC_THRESHOLD_MULTIPLIER = 3.0
MIC_MIN_THRESHOLD = 0.005
MIC_SHOW_LEVEL_METER = True
MIC_LEVEL_METER_INTERVAL = 0.5
MIC_WHISPER_REPO = "mlx-community/whisper-base-mlx"
