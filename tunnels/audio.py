import base64
import logging
import wave
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

class AudioStream:
    """Handles audio file processing and validation."""
    
    def __init__(self, source: Path, chunk_duration: float, sample_rate: int):
        self.source = source
        self.chunk_duration = chunk_duration
        self.sample_rate = sample_rate
        
    def validate_config(self):
        """Validate audio configuration parameters."""
        if not self.source.exists():
            raise ValueError(f"Audio file not found: {self.source}")
        if self.chunk_duration <= 0:
            raise ValueError(f"Invalid chunk duration: {self.chunk_duration}")
        if self.sample_rate <= 0:
            raise ValueError(f"Invalid sample rate: {self.sample_rate}")
            
        # Validate audio file format
        try:
            with wave.open(str(self.source), 'rb') as wf:
                if wf.getframerate() != self.sample_rate:
                    raise ValueError(
                        f"Expected sample rate {self.sample_rate}, "
                        f"got {wf.getframerate()}"
                    )
                if wf.getsampwidth() != 2:
                    raise ValueError("Only 16-bit PCM WAV files are supported")
                if wf.getnchannels() != 1:
                    raise ValueError("Only mono audio is supported")
        except wave.Error as e:
            raise ValueError(f"Invalid WAV file: {e}")

    def encode_chunk(self, chunk: np.ndarray) -> str:
        """Encode audio chunk to base64 string."""
        float32_data = chunk.astype(np.float32) / 32768.0  # Normalize to [-1.0, 1.0]
        return base64.b64encode(float32_data.tobytes()).decode("utf-8")

    def get_total_chunks(self) -> int:
        """Calculate total number of chunks in the audio file."""
        chunk_frames = int(self.chunk_duration * self.sample_rate)
        with wave.open(str(self.source), 'rb') as wf:
            frames = wf.getnframes()
            return (frames + chunk_frames - 1) // chunk_frames  # Round up division

    def read_chunks(self):
        """Generator that yields audio chunks."""
        chunk_frames = int(self.chunk_duration * self.sample_rate)
        
        with wave.open(str(self.source), 'rb') as wf:
            while True:
                frames = wf.readframes(chunk_frames)
                if not frames:
                    break
                    
                chunk = np.frombuffer(frames, dtype=np.int16)
                yield chunk
