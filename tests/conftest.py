import pytest

from harness_check.models import (
    Battery,
    Cable,
    Connector,
    CurrentModes,
    Fuse,
    Load,
    PinAssignment,
    RobotElectricalSystem,
)


@pytest.fixture
def minimal_system() -> RobotElectricalSystem:
    """A clean, passing system used as a baseline that individual tests mutate."""
    return RobotElectricalSystem(
        name="test-bot",
        battery=Battery(nominal_voltage=12.0, capacity_ah=5.0, max_discharge_c=2.0),
        loads=[
            Load(
                id="load-a",
                rail_voltage=12.0,
                current=CurrentModes(idle=0.1, nominal=1.0, peak=1.5),
                connector="conn-a",
                fuse="fuse-a",
            )
        ],
        cables=[Cable(id="cable-a", load="load-a", awg=18, length_m=0.2)],
        connectors=[
            Connector(
                id="conn-a",
                part="JST-XH-2",
                rated_current_a=5.0,
                pins=[PinAssignment(pin="1", signal="V+"), PinAssignment(pin="2", signal="GND")],
            )
        ],
        fuses=[Fuse(id="fuse-a", rated_current_a=5.0)],
    )
