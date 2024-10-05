
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.db import database
from backend.schemas import TransferRequest, OperationStatusResponse
import logging

from backend.utils.redis_client import redis_client 

router = APIRouter(
    prefix="/operations",
    tags=["operations"],
)

@router.get("/{operation_id}", response_model=OperationStatusResponse)
def get_operation_status(operation_id: str):
    status = redis_client.get_operation_status(operation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Operation ID not found.")
    return OperationStatusResponse(
        operation_id=operation_id,
        status=status["status"],
        detail=status.get("detail"),
    )
