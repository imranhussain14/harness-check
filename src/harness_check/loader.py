"""Load a RobotElectricalSystem from a YAML file."""

from pathlib import Path

import yaml

from .models import RobotElectricalSystem


def load_spec(path: str | Path) -> RobotElectricalSystem:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return RobotElectricalSystem.model_validate(data)
