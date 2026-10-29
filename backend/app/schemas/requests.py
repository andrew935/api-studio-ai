from pydantic import BaseModel


class APIRequest(BaseModel):
    url: str
    method: str
