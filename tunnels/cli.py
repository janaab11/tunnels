#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path

from tunnels.client import AudioClient

logger = logging.getLogger(__name__)

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

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        client = AudioClient(
            source=Path(args.source),
            server_url=args.server_url,
            chunk_duration=args.chunk_duration,
            sample_rate=args.sample_rate
        )
        client.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
