"""Pydantic data models for a robot electrical system spec."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Battery(BaseModel):
    name: str = "battery"
    nominal_voltage: float = Field(..., gt=0, description="Nominal pack voltage (V)")
    capacity_ah: float = Field(..., gt=0, description="Rated capacity (Ah)")
    max_discharge_c: float = Field(
        default=1.0, gt=0, description="Max continuous discharge rate (C)"
    )
    cutoff_voltage: Optional[float] = Field(
        default=None, description="Low-voltage cutoff, if known (V)"
    )
    usable_fraction: float = Field(
        default=0.8,
        gt=0,
        le=1.0,
        description="Fraction of rated capacity usable before cutoff/derating",
    )

    @property
    def max_discharge_current_a(self) -> float:
        return self.capacity_ah * self.max_discharge_c


class CurrentModes(BaseModel):
    """Current draw of a load in different operating modes (amps)."""

    idle: float = Field(default=0.0, ge=0)
    nominal: float = Field(..., ge=0)
    peak: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def default_peak(self) -> "CurrentModes":
        if self.peak is None:
            self.peak = self.nominal
        return self


class Load(BaseModel):
    id: str
    name: Optional[str] = None
    rail_voltage: float = Field(..., gt=0, description="Supply voltage for this load (V)")
    current: CurrentModes
    connector: Optional[str] = Field(
        default=None, description="ID of the Connector this load plugs into, if any"
    )
    fuse: Optional[str] = Field(default=None, description="ID of the Fuse protecting this load")

    def display_name(self) -> str:
        return self.name or self.id


class Cable(BaseModel):
    id: str
    load: str = Field(..., description="ID of the Load whose current flows through this cable")
    awg: int = Field(..., description="Wire gauge (AWG)")
    length_m: float = Field(..., gt=0, description="One-way cable length (m)")
    round_trip: bool = Field(
        default=True,
        description="Whether to double length_m for the return path when computing drop",
    )
    max_drop_pct: float = Field(
        default=3.0, description="Max acceptable voltage drop for this run, as % of rail voltage"
    )
    from_connector: Optional[str] = Field(
        default=None, description="Source Connector ID, for WireViz diagram export only"
    )
    to_connector: Optional[str] = Field(
        default=None, description="Destination Connector ID, for WireViz diagram export only"
    )


class PinAssignment(BaseModel):
    pin: str
    signal: str


class Connector(BaseModel):
    id: str
    part: Optional[str] = Field(default=None, description="e.g. 'JST-XH-4', 'XT60', 'DF13-6'")
    rated_current_a: Optional[float] = Field(default=None, gt=0)
    pins: list[PinAssignment] = Field(default_factory=list)


class Fuse(BaseModel):
    id: str
    rated_current_a: float = Field(..., gt=0)


class RobotElectricalSystem(BaseModel):
    name: str = "robot"
    battery: Battery
    loads: list[Load] = Field(default_factory=list)
    cables: list[Cable] = Field(default_factory=list)
    connectors: list[Connector] = Field(default_factory=list)
    fuses: list[Fuse] = Field(default_factory=list)

    def load_by_id(self, load_id: str) -> Optional[Load]:
        return next((l for l in self.loads if l.id == load_id), None)

    def connector_by_id(self, conn_id: str) -> Optional[Connector]:
        return next((c for c in self.connectors if c.id == conn_id), None)

    def fuse_by_id(self, fuse_id: str) -> Optional[Fuse]:
        return next((f for f in self.fuses if f.id == fuse_id), None)
