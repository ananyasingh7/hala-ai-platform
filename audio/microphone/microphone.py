import queue
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import mlx_whisper
import numpy as np
import sounddevice as sd

from config.logging import get_logger

TARGET_DEVICE_NAME = "Yeti Stereo Microphone"
SAMPLE_RATE = 16000
YETI_NATIVE_RATE = 48000
BLOCK_SIZE = 4096
THRESHOLD = 0.02
SILENCE_DURATION = 2.5
MIN_UTTERANCE_SECONDS = 1.0
CALIBRATION_SECONDS = 1.0
THRESHOLD_MULTIPLIER = 2.0
MIN_THRESHOLD = 0.001
SHOW_LEVEL_METER = True
LEVEL_METER_INTERVAL = 0.5
WHISPER_REPO = "mlx-community/whisper-base-mlx"


class HalaMicrophone:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        target_device_name: str = TARGET_DEVICE_NAME,
        sample_rate: int = SAMPLE_RATE,
        yeti_native_rate: int = YETI_NATIVE_RATE,
        block_size: int = BLOCK_SIZE,
        threshold: float = THRESHOLD,
        silence_duration: float = SILENCE_DURATION,
        min_utterance_seconds: float = MIN_UTTERANCE_SECONDS,
        calibration_seconds: float = CALIBRATION_SECONDS,
        threshold_multiplier: float = THRESHOLD_MULTIPLIER,
        min_threshold: float = MIN_THRESHOLD,
        show_level_meter: bool = SHOW_LEVEL_METER,
        level_meter_interval: float = LEVEL_METER_INTERVAL,
        whisper_repo: str = WHISPER_REPO,
    ):
        if self.__class__._initialized:
            return
        self.__class__._initialized = True

        self.logger = get_logger(self.__class__.__name__)
        self.target_device_name = target_device_name
        self.sample_rate = sample_rate
        self.yeti_native_rate = yeti_native_rate
        self.block_size = block_size
        self.threshold = threshold
        self.silence_duration = silence_duration
        self.min_utterance_seconds = min_utterance_seconds
        self.calibration_seconds = calibration_seconds
        self.threshold_multiplier = threshold_multiplier
        self.min_threshold = min_threshold
        self.show_level_meter = show_level_meter
        self.level_meter_interval = level_meter_interval
        self.whisper_repo = whisper_repo

        self.audio_queue = queue.Queue()
        self._reset_state()

    def _reset_state(self) -> None:
        self.buffer = []
        self.last_speech_time = time.time()
        self.is_speaking = False
        self.calibrating = True
        self.calibration_start = time.time()
        self.noise_levels = []
        self.adaptive_threshold = self.threshold
        self.last_meter_time = 0.0

    def _find_device(self):
        self.logger.info("Scanning for '%s'", self.target_device_name)
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if self.target_device_name in dev["name"] and dev["max_input_channels"] > 0:
                self.logger.info("Found microphone at device id %s", i)
                return i, dev["default_samplerate"]

        self.logger.warning("Microphone not found, using default system mic")
        return None, self.yeti_native_rate

    def _callback(self, indata, frames, time_info, status):
        if status:
            self.logger.warning("Stream status: %s", status)

        if self.yeti_native_rate == 48000:
            mono_audio = indata[::3, 0]
        else:
            mono_audio = indata[:, 0]

        self.audio_queue.put(mono_audio.copy())

    def _transcribe(self, audio_np: np.ndarray) -> None:
        self.logger.info("Transcribing")

        result = mlx_whisper.transcribe(
            audio_np,
            path_or_hf_repo=self.whisper_repo,
        )

        text = result["text"].strip()
        if text:
            self.logger.info("Heard: %s", text)
        else:
            self.logger.info("No intelligible speech")

    def listen_forever(self) -> None:
        device_id, native_rate = self._find_device()
        self.yeti_native_rate = int(native_rate)
        self._reset_state()

        self.logger.info(
            "Listening on %s (%s Hz)",
            self.target_device_name,
            self.yeti_native_rate,
        )
        self.logger.info("Calibrating noise floor, stay quiet for a moment")

        with sd.InputStream(
            device=device_id,
            channels=1,
            samplerate=self.yeti_native_rate,
            callback=self._callback,
            blocksize=self.block_size,
        ):
            while True:
                if not self.audio_queue.empty():
                    chunk = self.audio_queue.get()
                    energy = np.linalg.norm(chunk) / len(chunk)

                    if self.calibrating:
                        self.noise_levels.append(energy)
                        if time.time() - self.calibration_start >= self.calibration_seconds:
                            noise_floor = (
                                float(np.median(self.noise_levels))
                                if self.noise_levels
                                else 0.0
                            )
                            self.adaptive_threshold = max(
                                self.min_threshold,
                                noise_floor * self.threshold_multiplier,
                            )
                            self.calibrating = False
                            self.logger.info(
                                "Calibration done, threshold=%.4f",
                                self.adaptive_threshold,
                            )
                            self.logger.info("Speak now, transcription triggers after a pause")
                        time.sleep(0.01)
                        continue

                    if self.show_level_meter and not self.is_speaking:
                        now = time.time()
                        if now - self.last_meter_time >= self.level_meter_interval:
                            self.logger.info(
                                "Level %.4f | threshold %.4f",
                                energy,
                                self.adaptive_threshold,
                            )
                            self.last_meter_time = now

                    if energy > self.adaptive_threshold:
                        if not self.is_speaking:
                            self.logger.info("Recording")
                            self.is_speaking = True
                        self.last_speech_time = time.time()
                        self.buffer.append(chunk)

                    elif self.is_speaking:
                        self.buffer.append(chunk)
                        if time.time() - self.last_speech_time > self.silence_duration:
                            self.is_speaking = False
                            self.logger.info("Processing")

                            total_samples = sum(len(c) for c in self.buffer)
                            utterance_seconds = (
                                total_samples / self.sample_rate if self.sample_rate else 0.0
                            )
                            if utterance_seconds < self.min_utterance_seconds:
                                self.logger.info("Clip too short, keep listening")
                                self.buffer.clear()
                                continue

                            full_audio = np.concatenate(self.buffer)
                            self.buffer.clear()

                            self._transcribe(full_audio)
                            self.logger.info("Listening for the next phrase")

                time.sleep(0.01)


if __name__ == "__main__":
    microphone = HalaMicrophone()
    try:
        microphone.listen_forever()
    except KeyboardInterrupt:
        microphone.logger.info("Stopped")
