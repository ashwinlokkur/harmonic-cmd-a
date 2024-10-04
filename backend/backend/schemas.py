from pydantic import BaseModel
from typing import List, Optional
import uuid

class CompanyOutput(BaseModel):
    id: int
    company_name: str
    liked: bool

    class Config:
        orm_mode = True

class CompanyBatchOutput(BaseModel):
    companies: List[CompanyOutput]
    total: int

class CompanyCollectionMetadata(BaseModel):
    id: uuid.UUID
    collection_name: str

    class Config:
        orm_mode = True

class CompanyCollectionOutput(BaseModel):
    id: uuid.UUID
    collection_name: str
    companies: List[CompanyOutput]
    total: int

    class Config:
        orm_mode = True

class TransferRequest(BaseModel):
    source_collection_id: uuid.UUID
    target_collection_id: uuid.UUID
    company_ids: Optional[List[int]] = []

class OperationStatusResponse(BaseModel):
    operation_id: str
    status: str
    detail: Optional[str] = None
