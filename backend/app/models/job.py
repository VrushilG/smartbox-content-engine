from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class PipelineJob(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    status: JobStatus
    created_at: datetime
    rows_total: int
    rows_done: int
