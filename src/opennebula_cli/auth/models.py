"""Auth model types."""

from pydantic import BaseModel, ConfigDict


class ResolvedAuth(BaseModel):
    """Resolved OpenNebula auth material."""

    model_config = ConfigDict(frozen=True)

    username: str
    secret: str
    source: str
    raw_session: str
