# File: backend/tests/concurrency/test_concurrent_edit.py

import asyncio
import logging
import uuid
from uuid import UUID

# This test requires the app to be running
# It simulates multiple users editing the same block concurrently

# Mock user and block data for testing
TEST_USERS = [
    {"id": uuid.uuid4(), "token": "user1_token"},
    {"id": uuid.uuid4(), "token": "user2_token"},
    {"id": uuid.uuid4(), "token": "user3_token"},
]

TEST_CANVAS_ID = uuid.uuid4()
TEST_BLOCK_ID = uuid.uuid4()

API_URL = "http://localhost:8000/api/v1"

async def simulate_user_edit(user_data: dict, edit_number: int):
    """
    Simulates a single user sending a series of edits.
    """
    user_id = user_data["id"]
    token = user_data["token"]
    
    print(f"User {user_id} starting edit #{edit_number}")
    
    mutation_payload = {
        "client_op_id": f"{user_id}-edit-{edit_number}",
        "block_id": str(TEST_BLOCK_ID),
        "canvas_id": str(TEST_CANVAS_ID),
        "action": "update",
        "update_data": {
            "content": f"Edit by {user_id} - #{edit_number}"
        },
        "expected_version": edit_number - 1 # Optimistic locking
    }
    
    # In a real test, you would use httpx to make the request
    # For demonstration, we'll just simulate the logic
    print(f"User {user_id} sending payload: {mutation_payload}")
    
    # Simulate network delay
    await asyncio.sleep(0.1 + (edit_number * 0.05))
    
    # Simulate server processing time
    await asyncio.sleep(0.05)
    
    print(f"User {user_id} finished edit #{edit_number}")

async def run_concurrency_test():
    """
    Runs the main concurrency test scenario.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting concurrency test...")
    
    # Scenario: 3 users try to edit the same block 5 times each, concurrently
    tasks = []
    for user in TEST_USERS:
        for i in range(1, 6):
            task = asyncio.create_task(simulate_user_edit(user, i))
            tasks.append(task)
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks)
    
    logger.info("Concurrency test finished.")
    logger.info("Check the server logs and database to verify:")
    logger.info("1. All edits were processed.")
    logger.info("2. Block version incremented correctly.")
    logger.info("3. No data was lost or corrupted.")
    logger.info("4. Conflict resolution worked as expected.")

if __name__ == "__main__":
    asyncio.run(run_concurrency_test())