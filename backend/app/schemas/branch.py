from pydantic import BaseModel, ConfigDict


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    is_active: bool
