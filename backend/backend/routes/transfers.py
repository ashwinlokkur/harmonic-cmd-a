import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.db import database
from backend.schemas import TransferRequest, OperationStatusResponse
import logging

from backend.utils.redis_client import redis_client 

router = APIRouter(
    prefix="/transfers",
    tags=["transfers"],
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("", response_model=OperationStatusResponse)
def transfer_companies(
    transfer_request: TransferRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    operation_id = str(uuid.uuid4())
    # Store initial operation status in Redis
    redis_client.set_operation_status(operation_id, {"status": "in_progress", "detail": "Transfer started."})
    logger.info(f"Operation {operation_id} initiated: Transfer from {transfer_request.source_collection_id} to {transfer_request.target_collection_id}")

    # Add the background task to process the transfer
    background_tasks.add_task(
        process_transfer, operation_id, transfer_request, db
    )

    return OperationStatusResponse(
        operation_id=operation_id,
        status="in_progress",
        detail="Transfer has started.",
    )


def process_transfer(operation_id: str, transfer_request: TransferRequest, db: Session):
    try:
        source_collection = db.query(database.CompanyCollection).filter(
            database.CompanyCollection.id == transfer_request.source_collection_id
        ).first()

        target_collection = db.query(database.CompanyCollection).filter(
            database.CompanyCollection.id == transfer_request.target_collection_id
        ).first()

        if not source_collection or not target_collection:
            message = "Invalid source or target collection ID."
            redis_client.set_operation_status(operation_id, {"status": "failed", "detail": message})
            logger.error(f"Operation {operation_id} failed: {message}")
            return

        if transfer_request.company_ids:
            # Transfer specific companies
            companies = db.query(database.Company).filter(
                database.Company.id.in_(transfer_request.company_ids)
            ).all()
        else:
            # Transfer all companies from source to target
            companies = db.query(database.Company).join(
                database.CompanyCollectionAssociation,
                database.Company.id == database.CompanyCollectionAssociation.company_id
            ).filter(
                database.CompanyCollectionAssociation.collection_id == transfer_request.source_collection_id
            ).all()

        # Prepare bulk insert for associations
        existing_associations = db.query(database.CompanyCollectionAssociation.company_id).filter(
            database.CompanyCollectionAssociation.collection_id == transfer_request.target_collection_id,
            database.CompanyCollectionAssociation.company_id.in_([company.id for company in companies])
        ).all()
        existing_company_ids = {assoc.company_id for assoc in existing_associations}

        new_associations = [
            {
                "company_id": company.id,
                "collection_id": transfer_request.target_collection_id
            }
            for company in companies if company.id not in existing_company_ids
        ]

        if new_associations:
            # Batch insert in groups to mitigate trigger delays
            batch_size = 1000  # Adjust based on performance
            total_batches = (len(new_associations) + batch_size - 1) // batch_size
            transferred = 0

            for i in range(0, len(new_associations), batch_size):
                batch = new_associations[i:i + batch_size]
                db.bulk_insert_mappings(database.CompanyCollectionAssociation, batch)
                db.commit()
                transferred += len(batch)
                logger.info(f"Operation {operation_id}: Transferred batch {i // batch_size + 1} of {len(batch)} companies.")

                # Optionally, update progress in Redis
                redis_client.set_operation_status(operation_id, {
                    "status": "in_progress",
                    "detail": f"Transferred {transferred} out of {len(new_associations)} companies."
                })

            # Final status update
            redis_client.set_operation_status(operation_id, {
                "status": "completed",
                "detail": f"Transferred {transferred} companies."
            })
            logger.info(f"Operation {operation_id} completed: Transferred {transferred} companies.")
        else:
            message = "No new companies to transfer."
            redis_client.set_operation_status(operation_id, {"status": "completed", "detail": message})
            logger.info(f"Operation {operation_id} completed: {message}")

    except Exception as e:
        db.rollback()
        redis_client.set_operation_status(operation_id, {"status": "failed", "detail": str(e)})
        logger.error(f"Operation {operation_id} failed with exception: {e}")


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
