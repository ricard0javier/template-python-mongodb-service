import logging
import signal
import sys
import threading
import time

from src.config import LOG_LEVEL
from src.consumers.kafka_consumer import start_consumer

# Configure structured logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("app.log")],
)
logger = logging.getLogger(__name__)


class Application:
    def __init__(self):
        self.stop_event = threading.Event()
        self.consumer_thread = None

    def signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop_event.set()

    def setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def start(self) -> None:
        """Start the application"""
        logger.info("Starting application...")
        self.setup_signal_handlers()

        try:
            # Start consumer in a separate thread
            self.consumer_thread = threading.Thread(target=start_consumer, daemon=True)
            self.consumer_thread.start()

            # Run main loop in current thread
            self._run_main_loop()
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
            sys.exit(1)

    def _run_main_loop(self) -> None:
        """Main application loop with health monitoring"""
        logger.info("Application running, monitoring health...")

        while not self.stop_event.is_set():
            try:
                time.sleep(1)
                # Add health check logic here if needed

                # Check if consumer thread is still alive
                if self.consumer_thread and not self.consumer_thread.is_alive():
                    logger.error("Consumer thread died unexpectedly")
                    break

            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
                break

        logger.info("Application shutdown complete")


def main() -> None:
    """Main entry point"""
    app = Application()
    app.start()


if __name__ == "__main__":
    main()
