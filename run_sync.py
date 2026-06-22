import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.auto_sync import trigger_folder_sync

if __name__ == "__main__":
    asyncio.run(trigger_folder_sync(5, True, 1))
