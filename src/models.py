from typing import Optional
from pydantic import BaseModel


class BotModel(BaseModel):

    login: str
    state: Optional[bool]
    password: Optional[str]
    steamid: Optional[str]
    shared_secret: Optional[str]
    identity_secret: Optional[str]
    steam_api_key: Optional[str]
    tm_api_key: Optional[str]
    google_doc_id: Optional[str]
    proxy: Optional[str]
