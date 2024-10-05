import uuid

from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

from backend.db import database
from backend.routes.companies import fetch_companies_with_liked
from backend.schemas import (
    CompanyCollectionOutput, 
    CompanyCollectionMetadata,
    BulkDeleteRequest,
    OperationStatusResponse
)
from backend.utils.redis_client import redis_client

router = APIRouter(
    prefix="/collections",
    tags=["collections"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("", response_model=list[CompanyCollectionMetadata])
def get_all_collection_metadata(
    db: Session = Depends(database.get_db),
):
    collections = db.query(database.CompanyCollection).all()

    return [
        CompanyCollectionMetadata(
            id=collection.id,
            collection_name=collection.collection_name,
        )
        for collection in collections
    ]


@router.get("/{collection_id}", response_model=CompanyCollectionOutput)
def get_company_collection_by_id(
    collection_id: uuid.UUID,
    offset: int = Query(
        0, description="The number of items to skip from the beginning"
    ),
    limit: int = Query(10, description="The number of items to fetch"),
    db: Session = Depends(database.get_db),
):
    query = (
        db.query(database.CompanyCollectionAssociation, database.Company)
        .join(database.Company)
        .filter(database.CompanyCollectionAssociation.collection_id == collection_id)
    )

    total_count = query.with_entities(func.count()).scalar()

    results = query.offset(offset).limit(limit).all()
    companies = fetch_companies_with_liked(db, [company.id for _, company in results])

    return CompanyCollectionOutput(
        id=collection_id,
        collection_name=db.query(database.CompanyCollection)
        .get(collection_id)
        .collection_name,
        companies=companies,
        total=total_count,
    )


def process_bulk_delete(
    operation_id: str,
    collection_id: uuid.UUID,
    delete_request: BulkDeleteRequest,
    db: Session
):
    try:
        # Start a database transaction
        # (Assuming you're handling transactions manually; SQLAlchemy sessions handle this by default)
        
        if delete_request.company_ids:
            # Delete specific companies from the collection
            associations_query = db.query(database.CompanyCollectionAssociation).filter(
                database.CompanyCollectionAssociation.collection_id == collection_id,
                database.CompanyCollectionAssociation.company_id.in_(delete_request.company_ids)
            )
        else:
            # Delete all companies from the collection
            associations_query = db.query(database.CompanyCollectionAssociation).filter(
                database.CompanyCollectionAssociation.collection_id == collection_id
            )

        total_to_delete = associations_query.count()
        if total_to_delete == 0:
            redis_client.set_operation_status(
                operation_id,
                {"status": "completed", "detail": "No companies to delete."}
            )
            logging.info(f"Operation {operation_id}: No companies found to delete in collection {collection_id}.")
            return

        # Fetch all company_ids to delete (for logging or further processing if needed)
        associations = associations_query.all()
        delete_company_ids = [assoc.company_id for assoc in associations]

        # Implement batch deletion to optimize performance
        batch_size = 1000  # Adjust based on performance and testing
        total_deleted = 0
        company_ids_to_delete = delete_company_ids

        for i in range(0, len(company_ids_to_delete), batch_size):
            batch_ids = company_ids_to_delete[i:i + batch_size]
            db.query(database.CompanyCollectionAssociation).filter(
                database.CompanyCollectionAssociation.collection_id == collection_id,
                database.CompanyCollectionAssociation.company_id.in_(batch_ids)
            ).delete(synchronize_session=False)
            db.commit()
            total_deleted += len(batch_ids)
            logging.info(f"Operation {operation_id}: Deleted batch {i // batch_size + 1} of {len(batch_ids)} companies.")

            # Update progress in Redis
            redis_client.set_operation_status(
                operation_id,
                {
                    "status": "in_progress",
                    "detail": f"Deleted {total_deleted} out of {total_to_delete} companies."
                }
            )

        # Final status update
        redis_client.set_operation_status(
            operation_id,
            {"status": "completed", "detail": f"Deleted {total_deleted} companies from the collection."}
        )
        logging.info(f"Operation {operation_id}: Bulk deletion completed. Total deleted: {total_deleted} companies.")

    except Exception as e:
        db.rollback()
        redis_client.set_operation_status(
            operation_id,
            {"status": "failed", "detail": str(e)}
        )
        logging.error(f"Operation {operation_id} failed with exception: {e}")



@router.delete("/{collection_id}/companies", response_model=OperationStatusResponse)
def bulk_delete_companies(
    collection_id: uuid.UUID,
    delete_request: BulkDeleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    """
    Bulk delete companies from a specific collection.

    - **collection_id**: UUID of the collection
    - **company_ids**: List of company IDs to delete. If empty, deletes all companies from the collection.
    """
    # Verify collection existence
    collection = db.query(database.CompanyCollection).get(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found.")

    # Generate a unique operation ID
    operation_id = str(uuid.uuid4())

    # Set initial operation status in Redis
    redis_client.set_operation_status(
        operation_id,
        {"status": "in_progress", "detail": "Bulk deletion started."}
    )

    # Add the background task for deletion
    background_tasks.add_task(
        process_bulk_delete, operation_id, collection_id, delete_request, db
    )

    return OperationStatusResponse(
        operation_id=operation_id,
        status="in_progress",
        detail="Bulk deletion has started.",
    )