"""Export a RobotElectricalSystem as a WireViz-compatible YAML harness diagram source.

WireViz (https://github.com/wireviz/WireViz) turns a YAML description of
connectors/cables/connections into a rendered harness diagram. This module
produces a best-effort WireViz YAML from the same spec harness-check
validates, so the one spec can drive both the validation report and the
diagram. Cables without from_connector/to_connector set are included in the
connectors/cables sections but omitted from the connections section, since
WireViz needs both endpoints to draw a connection.
"""

from __future__ import annotations

from .models import RobotElectricalSystem


def to_wireviz_yaml_dict(sys: RobotElectricalSystem) -> dict:
    connectors = {}
    for conn in sys.connectors:
        pinlabels = [p.signal for p in conn.pins] or None
        entry: dict = {"type": conn.part or "connector"}
        if pinlabels:
            entry["pinlabels"] = pinlabels
        connectors[conn.id] = entry

    cables = {}
    connections = []
    for cable in sys.cables:
        cables[cable.id] = {
            "gauge": f"{cable.awg} AWG",
            "length": cable.length_m,
            "wirecount": 1,
        }
        if cable.from_connector and cable.to_connector:
            connections.append([cable.from_connector, cable.id, cable.to_connector])

    out: dict = {"connectors": connectors, "cables": cables}
    if connections:
        out["connections"] = connections
    return out
