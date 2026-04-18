from pydantic import BaseModel
from typing import Optional

class StartCampaignRequest(BaseModel):
    campaign_id: int
    message: str
    limit: Optional[int] = None
    min_interval: int = 15
    max_interval: int = 45

class ImportContactsRequest(BaseModel):
    campaign_id: int
    xlsx_path: str

class ActivateLicenseRequest(BaseModel):
    key: str

class AddBlacklistRequest(BaseModel):
    phone: str
    reason: Optional[str] = "MANUAL"

class SaveConfigRequest(BaseModel):
    configs: dict

class CreateTemplateRequest(BaseModel):
    name: str
    content: str
