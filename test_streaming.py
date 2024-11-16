import sounddevice as sd
import numpy as np
import wave
import queue
import time
import argparse
import threading

# Queue to buffer audio chunks
audio_queue = queue.Queue()


def play_audio_stream(out_stream):
    """ Function to play audio chunks from the queue continuously """
    while True:
        chunk = audio_queue.get()
        if chunk is None:  # Exit when no more chunks are left
            break
        out_stream.write(chunk)
        time.sleep(0.01)  # Small delay to ensure smooth playback


def play_audio(audio_file):
    """ Function to read audio from file and stream it to the output device """
    wf = wave.open(audio_file, 'rb')
    samplerate = wf.getframerate()
    chunk_size = int(0.5 * samplerate)  # Chunk duration (0.5s)
    print(f"Samplerate: {samplerate}, Chunk size: {chunk_size}")

    # Open output stream for continuous playback
    out_stream = sd.OutputStream(channels=1, samplerate=samplerate, dtype='int16')
    out_stream.start()

    # Start playback thread
    playback_thread = threading.Thread(target=play_audio_stream, args=(out_stream,))
    playback_thread.start()

    # Read and stream audio chunks
    while True:
        data = wf.readframes(chunk_size)
        if not data:
            break  # End of file

        # Convert to numpy array and put in the queue
        chunk = np.frombuffer(data, dtype=np.int16)
        audio_queue.put(chunk)

        # Simulate real-time streaming with a small delay between chunks
        time.sleep(0.05)

    # Signal the playback thread to stop
    audio_queue.put(None)
    playback_thread.join()

    # Stop the output stream
    out_stream.stop()
    print("Audio playback finished.")


def main():
    parser = argparse.ArgumentParser(description="Test audio playback")
    parser.add_argument("audio_file", type=str, help="Path to the audio file to be played.")
    args = parser.parse_args()

    # Pass the audio file path to the play_audio function
    play_audio(args.audio_file)


if __name__ == "__main__":
    main()
