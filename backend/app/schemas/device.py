"""Request/response DTOs for connector devices and the print queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

_MAX_ZPL_BYTES = 512 * 1024


class DeviceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class DevicePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    agent_version: str | None
    printers: list[Any]
    last_seen_at: datetime | None
    created_at: datetime


class PrintJobCreateRequest(BaseModel):
    device_id: int
    printer: str = Field(min_length=1, max_length=100)
    zpl: str = Field(min_length=1, max_length=_MAX_ZPL_BYTES)
    copies: int = Field(default=1, ge=1, le=1000)


class PrintJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    printer: str
    copies: int
    status: str
    error: str | None
    created_at: datetime
    sent_at: datetime | None
    finished_at: datetime | None


class AgentJobPayload(BaseModel):
    """What the agent needs to print — includes the ZPL body."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    printer: str
    copies: int
    zpl: str


class AgentStatusRequest(BaseModel):
    status: Literal["done", "error"]
    error: str | None = Field(default=None, max_length=2000)


class AgentPrinter(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=9100, ge=1, le=65535)


class AgentStateRequest(BaseModel):
    agent_version: str | None = Field(default=None, max_length=50)
    printers: list[AgentPrinter] = Field(default_factory=list, max_length=50)
