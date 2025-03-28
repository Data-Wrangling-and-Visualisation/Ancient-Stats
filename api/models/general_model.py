from pydantic import BaseModel


class StatusModel(BaseModel):
    status: bool
    details: str
