import os
import redis
import json
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        redis_host = os.getenv('REDIS_HOST', 'redis-server')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))
        try:
            self.client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
            # Test the connection
            self.client.ping()
            logger.info("Connected to Redis successfully.")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis at {redis_host}:{redis_port} - {e}")
            self.client = None  # TODO implement retry logic

    def set_operation_status(self, operation_id: str, status: Dict, expire_seconds: int = 86400):
        """
        Stores the operation status in Redis as a JSON string with an optional expiration time.
        Default expiration is 24 hours.
        """
        if self.client:
            try:
                self.client.set(operation_id, json.dumps(status), ex=expire_seconds)
                logger.debug(f"Set status for operation {operation_id}: {status}")
            except Exception as e:
                logger.error(f"Error setting status for operation {operation_id}: {e}")
        else:
            logger.error("Redis client is not connected. Cannot set operation status.")

    def get_operation_status(self, operation_id: str) -> Optional[Dict]:
        """
        Retrieves the operation status from Redis. Returns None if not found.
        """
        if self.client:
            try:
                status_json = self.client.get(operation_id)
                if status_json:
                    status = json.loads(status_json)
                    logger.debug(f"Retrieved status for operation {operation_id}: {status}")
                    return status
            except Exception as e:
                logger.error(f"Error retrieving status for operation {operation_id}: {e}")
        else:
            logger.error("Redis client is not connected. Cannot get operation status.")
        return None

# init client 
redis_client = RedisClient()
