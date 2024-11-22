#!/usr/bin/env python3

import argparse
import base64
import json
import logging
import signal
import sys
import time
import threading
import wave
from pathlib import Path

import numpy as np
from websocket import WebSocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioClient:
    """Simple audio streaming client."""
    
    def __init__(self, source: Path, server_url: str, chunk_duration: float, sample_rate: int):
        self.source = source
        self.server_url = server_url
        self.chunk_duration = chunk_duration
        self.sample_rate = sample_rate
        self.shutdown_flag = threading.Event()
        self.ws = None
        self._validate_config()
        
    def _validate_config(self):
        """Validate configuration parameters."""
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

    def _encode_chunk(self, chunk: np.ndarray) -> str:
        """Encode audio chunk to base64 string."""
        float32_data = chunk.astype(np.float32) / 32768.0  # Normalize to [-1.0, 1.0]
        return base64.b64encode(float32_data.tobytes()).decode("utf-8")

    def send_audio(self):
        """Stream audio file to WebSocket server."""
        chunk_frames = int(self.chunk_duration * self.sample_rate)
        total_chunks = 0
        processed_chunks = 0
        
        try:
            # Count total chunks first
            with wave.open(str(self.source), 'rb') as wf:
                frames = wf.getnframes()
                total_chunks = (frames + chunk_frames - 1) // chunk_frames  # Round up division
            
            # Stream the audio
            with wave.open(str(self.source), 'rb') as wf:
                while not self.shutdown_flag.is_set():
                    frames = wf.readframes(chunk_frames)
                    if not frames:
                        logger.info("Reached end of audio file")
                        break

                    chunk = np.frombuffer(frames, dtype=np.int16)
                    encoded_data = self._encode_chunk(chunk)
                    
                    try:
                        self.ws.send(encoded_data)
                        processed_chunks += 1
                        
                        # Log progress every 10%
                        if processed_chunks % max(1, total_chunks // 10) == 0:
                            progress = min(100.0, (processed_chunks / total_chunks) * 100)
                            logger.info(f"Processing progress: {progress:.1f}%")
                            
                        time.sleep(self.chunk_duration)
                    except Exception as e:
                        logger.error(f"Error sending data: {e}")
                        break

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise

    def receive_messages(self):
        """Handle incoming WebSocket messages."""
        while not self.shutdown_flag.is_set():
            try:
                message = self.ws.recv()
                try:
                    # Try to parse JSON response
                    response = json.loads(message)
                    logger.info(f"Server response: {response}")
                except json.JSONDecodeError:
                    # If not JSON, log as plain text
                    logger.info(f"Server message: {message}...")  # First 100 chars
            except Exception as e:
                if not self.shutdown_flag.is_set():
                    logger.error(f"Error receiving message: {e}")
                break

    def run(self):
        """Run the client."""
        try:
            # Connect to WebSocket server
            self.ws = WebSocket()
            self.ws.connect(self.server_url)
            logger.info(f"Connected to {self.server_url}")

            # Start sender and receiver threads
            sender = threading.Thread(target=self.send_audio)
            receiver = threading.Thread(target=self.receive_messages)
            
            sender.start()
            receiver.start()
            
            # Wait for completion or interrupt
            sender.join()
            receiver.join()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown of the client."""
        logger.info("Shutting down...")
        self.shutdown_flag.set()
        if self.ws:
            try:
                self.ws.close()
            except:
                pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stream audio to a WebSocket server as base64 text."
    )
    parser.add_argument(
        "source",
        type=str,
        help="Path to the audio file (e.g., test_audio.wav)."
    )
    parser.add_argument(
        "server_url",
        type=str,
        help="WebSocket server URL (e.g., ws://localhost:8765)."
    )
    parser.add_argument(
        "--chunk-duration",
        type=float,
        default=0.5,
        help="Duration of each chunk in seconds. Default: 0.5"
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Expected sample rate of the audio file. Default: 16000"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        client = AudioClient(
            source=Path(args.source),
            server_url=args.server_url,
            chunk_duration=args.chunk_duration,
            sample_rate=args.sample_rate
        )
        client.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
