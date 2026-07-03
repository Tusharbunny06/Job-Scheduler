import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import asyncio
import signal
from worker_service import WorkerService

async def main():
    worker = WorkerService(concurrency_limit=10)
    
    stop_event = asyncio.Event()

    def handle_shutdown(signum, frame):
        print("\nReceived stop signal. Shutting down worker...")
        stop_event.set()
        
    # Windows doesn't fully support all signals, but we can catch SIGINT and SIGTERM
    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    except NotImplementedError:
        pass # Windows
        
    await worker.start()
    
    # Wait until a signal sets the event
    await stop_event.wait()
    
    # Gracefully stop the worker, waiting for jobs to finish
    await worker.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
