import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro

from config.logging import get_logger
from config.settings import (
    SPEAKER_LANG,
    SPEAKER_MODEL_PATH,
    SPEAKER_OUTPUT_GAIN,
    SPEAKER_SPEED,
    SPEAKER_VOICE_NAME,
    SPEAKER_VOICES_PATH,
)


class HalaEars:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        model_path: str = SPEAKER_MODEL_PATH,
        voices_path: str = SPEAKER_VOICES_PATH,
        voice_name: str = SPEAKER_VOICE_NAME,
        output_gain: float = SPEAKER_OUTPUT_GAIN,
        lang: str = SPEAKER_LANG,
        speed: float = SPEAKER_SPEED,
    ):
        if self.__class__._initialized:
            return
        self.__class__._initialized = True

        self.logger = get_logger(self.__class__.__name__)
        self.model_path = model_path
        self.voices_path = voices_path
        self.voice_name = voice_name
        self.output_gain = output_gain
        self.lang = lang
        self.speed = speed

        self.logger.info("Loading ears voice=%s", self.voice_name)
        try:
            self.kokoro = Kokoro(self.model_path, self.voices_path)
            self.logger.info("Ears online")
        except Exception as e:
            self.logger.error("Failed to load Kokoro model: %s", e)
            self.logger.error("Download the model files into audio/speaker/models")
            self.logger.error("Example:")
            self.logger.error("  mkdir -p models")
            self.logger.error(
                "  curl -L -o models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
            )
            self.logger.error(
                "  curl -L -o models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
            )
            raise SystemExit(1)

    def speak(self, text: str) -> None:
        """Synthesizes text to audio and plays it immediately."""
        if not text.strip():
            return

        self.logger.info("Speaking: %s", text)
        start_time = time.time()

        samples, sample_rate = self.kokoro.create(
            text,
            voice=self.voice_name,
            speed=self.speed,
            lang=self.lang,
        )

        latency = (time.time() - start_time) * 1000
        self.logger.info("Generated in %.0f ms", latency)

        if self.output_gain != 1.0:
            samples = np.clip(samples * self.output_gain, -1.0, 1.0)
        sd.play(samples, sample_rate)
        sd.wait()


if __name__ == "__main__":
    ears = HalaEars()

    ears.logger.info("Ears test")
    ears.logger.info("Type something to say (or 'exit'):")

    while True:
        user_input = input("\nText > ")
        if user_input.lower() in ["exit", "quit"]:
            break

        ears.speak(user_input)
