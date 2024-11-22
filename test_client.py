import argparse
import wave
import numpy as np
import base64
import time
import json
import threading
from websocket import create_connection, WebSocket
from threading import Thread


def encode_audio(waveform: np.ndarray) -> str:
    """
    Encode a waveform (numpy array) into a base64-encoded string.

    Args:
        waveform (np.ndarray): The waveform to encode.

    Returns:
        str: The base64-encoded string representation of the waveform.
    """
    data = waveform.astype(np.float32).tobytes()
    return base64.b64encode(data).decode("utf-8")

def send_audio(ws, file_path, chunk_duration=0.5, sample_rate=16000):
    """
    Stream audio file to a WebSocket server in chunks as base64-encoded text.

    Args:
        ws (WebSocket): The WebSocket connection.
        file_path (str): Path to an audio file (e.g., .wav file).
        chunk_duration (float): Duration of each audio chunk in seconds.
        sample_rate (int): Expected sample rate of the audio.
    """
    with wave.open(file_path, 'rb') as wf:
        # Ensure the file has the expected sample rate and format
        assert wf.getframerate() == sample_rate, f"Expected sample rate {sample_rate}, got {wf.getframerate()}"
        assert wf.getsampwidth() == 2, "Only 16-bit PCM WAV files are supported"
        assert wf.getnchannels() == 1, "Only mono audio is supported"

        # Calculate the number of frames per chunk
        chunk_frames = int(chunk_duration * sample_rate)

        while True:
            frames = wf.readframes(chunk_frames)
            if not frames:
                break  # End of file

            # Convert frames to a NumPy array (simulate Float32Array)
            int16_data = np.frombuffer(frames, dtype=np.int16)
            float32_data = int16_data.astype(np.float32) / 32768.0  # Normalize to [-1.0, 1.0]

            # Encode audio chunk to base64 text
            encoded_data = encode_audio(float32_data)

            # Send the encoded data
            ws.send(encoded_data)
            # print(f"Sent chunk of size {len(float32_data)}")

            # Simulate real-time streaming
            time.sleep(chunk_duration)


def receive_audio(ws: WebSocket):
    while True:
        message = ws.recv()
        print(f"Received: {message}")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Stream audio to a WebSocket server as base64 text.")
    parser.add_argument("source", type=str, help="Path to the audio file (e.g., test_audio.wav).")
    parser.add_argument("server_url", type=str, help="WebSocket server URL (e.g., ws://localhost:8765).")
    parser.add_argument("--chunk-duration", type=float, default=0.5, help="Duration of each chunk in seconds. Default: 0.5")
    parser.add_argument("--sample-rate", type=int, default=16000, help="Expected sample rate of the audio file. Default: 16000")
    args = parser.parse_args()

    # Create WebSocket connection
    ws = WebSocket()
    ws.connect(args.server_url)

    # Start sender and receiver threads
    sender = Thread(
        target=send_audio, args=[ws, args.source, args.chunk_duration, args.sample_rate]
    )
    receiver = Thread(target=receive_audio, args=[ws])
    sender.start()
    receiver.start()

    # Wait for threads to complete
    sender.join()
    receiver.join()
