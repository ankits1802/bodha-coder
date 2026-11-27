from pydantic import BaseModel, ConfigDict

__all__ = ["View"]


class View(BaseModel):
    model_config = ConfigDict(extra="forbid")
