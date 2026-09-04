from fastapi import APIRouter, Depends, HTTPException, status
import redis
from src.interfaces.api.dependencies import get_redis_client
import psycopg2
from src.core.config import settings

router = APIRouter()

@router.get("/")
def health_check(redis_client: redis.Redis = Depends(get_redis_client)):
    """Health check endpoint to verify connections to PostgreSQL and Redis."""
    health_status = {"status": "ok", "db": "unknown", "redis": "unknown"}
    
    # Check Redis
    try:
        redis_client.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = "disconnected"
        health_status["status"] = "error"
    
    # Check DB
    try:
        conn = psycopg2.connect(settings.POSTGRES_URL)
        conn.close()
        health_status["db"] = "connected"
    except Exception as e:
        health_status["db"] = "disconnected"
        health_status["status"] = "error"
    
    if health_status["status"] == "error":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status)
        
    return health_status
