#!/usr/bin/env python3

import json
import logging
import threading
import time
from pathlib import Path

from websocket import WebSocket

from tunnels.audio import AudioStream

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
        self.audio_stream = AudioStream(source, chunk_duration, sample_rate)
        self.audio_stream.validate_config()
        
    def send_audio(self):
        """Stream audio file to WebSocket server."""
        total_chunks = self.audio_stream.get_total_chunks()
        processed_chunks = 0
        
        try:
            for chunk in self.audio_stream.read_chunks():
                if self.shutdown_flag.is_set():
                    break

                encoded_data = self.audio_stream.encode_chunk(chunk)
                
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
