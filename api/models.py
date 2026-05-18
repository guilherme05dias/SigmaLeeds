from pydantic import BaseModel, Field
from typing import Optional

class StartCampaignRequest(BaseModel):
    campaign_id: int
    message: str
    limit: Optional[int] = None
    min_interval: int = 30
    max_interval: int = 60

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

class SendWindowConfigRequest(BaseModel):
    enabled: bool = False
    start: str = "08:00"
    end: str = "20:00"
    days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
