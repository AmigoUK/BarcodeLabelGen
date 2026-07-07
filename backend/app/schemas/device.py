"""Request/response DTOs for connector devices and the print queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    # Empty host is legal only for kind="local" (a queue discovered on the
    # connector's computer) — see the validator below.
    host: str = Field(default="", max_length=255)
    port: int = Field(default=9100, ge=1, le=65535)
    kind: Literal["network", "file", "local"] = "network"

    @model_validator(mode="after")
    def _host_required_unless_local(self) -> AgentPrinter:
        if self.kind != "local" and not self.host:
            raise ValueError("host is required for network/file printers")
        return self


class AgentStateRequest(BaseModel):
    agent_version: str | None = Field(default=None, max_length=50)
    printers: list[AgentPrinter] = Field(default_factory=list, max_length=50)


# ~2 MB of base64 — driver-generated ZPL with ^GFA bitmaps gets big.
_MAX_CAPTURE_B64 = 3 * 1024 * 1024


class AgentCaptureRequest(BaseModel):
    """Captured print job, base64-encoded for safe JSON transport."""

    zpl_b64: str = Field(min_length=1, max_length=_MAX_CAPTURE_B64)


class CapturePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    size_bytes: int
    created_at: datetime
