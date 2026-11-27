# harness-check

Validate a robot's (or any multi-subsystem electromechanical project's)
electrical architecture from a single YAML spec — before you order
connectors, crimp a harness, or find out the hard way that a fuse is
undersized.

Robots aren't one PCB. They're a battery, a handful of subsystems (motor
drivers, an SBC, sensors), and a wiring harness tying it all together.
Existing tools cover pieces of this well — [WireViz](https://github.com/wireviz/WireViz)
draws harness diagrams, KiCad's ERC/DRC checks a single board's schematic —
but nothing checks the *system-level* electrical budget across the whole
harness. Most teams end up doing this by hand in a spreadsheet. `harness-check`
is that spreadsheet, as a linter.

## What it checks

Given a YAML description of your battery, subsystems (loads), cables,
connectors, and fuses, `harness-check` validates:

- **Voltage drop** per cable run, from wire gauge (AWG) and length, against
  a configurable threshold (e.g. flag any run that drops more than 3% of
  rail voltage).
- **Connector current ratings** — total current (nominal and peak) drawn
  through each connector, checked against its rated current.
- **Fuse ratings** — same idea, flagging fuses that will blow under normal
  or peak operation.
- **Pin assignment conflicts** — two signals accidentally mapped to the
  same pin on the same connector.
- **Power budget vs. battery** — total system power per operating mode
  (idle/nominal/peak), checked against the battery's max continuous
  discharge rating, plus an estimated runtime at nominal load.

It can also export your spec as a [WireViz](https://github.com/wireviz/WireViz)
YAML, so the same file that gets validated can generate a harness diagram.

## Install

```bash
pip install -e .
```

(Not yet published to PyPI — clone and install locally, or copy
`src/harness_check` into your own project.)

## Usage

```bash
harness-check check examples/example_robot.yaml
```

```
harness-check report: demo-rover

┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Severity ┃ Check            ┃ Subject           ┃ Message                   ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ERROR    │ voltage_drop     │ cable-drive-power │ 0.799 V drop (5.40% of     │
│          │                  │                   │ 14.8 V) — exceeds 3%      │
│ ERROR    │ connector_rating │ main-power-conn   │ rated 15 A but sees 18 A   │
│ ...                                                                         │
└──────────┴──────────────────┴───────────────────┴────────────────────────────┘

FAIL — 4 error(s), 2 warning(s)
```

Other output formats, for CI or sharing:

```bash
harness-check check my_robot.yaml --format json --out report.json
harness-check check my_robot.yaml --format markdown --out report.md
```

The command exits non-zero on any error (use `--fail-on-warning` to also
fail on warnings), so it drops straight into a CI pipeline as a pre-build
gate on your electrical design.

Export a diagram-ready WireViz YAML:

```bash
harness-check export-wireviz my_robot.yaml --out harness.yaml
wireviz harness.yaml   # requires `pip install wireviz` separately
```

## Writing a spec

See [`examples/example_robot.yaml`](examples/example_robot.yaml) for a full
annotated example (with intentionally broken bits, so you can see what each
check catches). The shape:

```yaml
name: my-robot

battery:
  nominal_voltage: 14.8
  capacity_ah: 10.0
  max_discharge_c: 2.0      # => 20 A max continuous discharge
  usable_fraction: 0.8      # usable capacity before cutoff/derating

loads:
  - id: drive-motors
    rail_voltage: 14.8
    current:
      idle: 0.5
      nominal: 8.0
      peak: 18.0
    connector: main-power-conn
    fuse: main-fuse

cables:
  - id: cable-drive-power
    load: drive-motors
    awg: 20
    length_m: 1.5           # one-way; doubled automatically for round-trip
    max_drop_pct: 3.0

connectors:
  - id: main-power-conn
    part: XT30
    rated_current_a: 15
    pins:
      - { pin: "1", signal: "VBAT+" }
      - { pin: "2", signal: "VBAT-" }

fuses:
  - id: main-fuse
    rated_current_a: 10
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Why this instead of X

- **WireViz** draws a harness diagram from a similar YAML shape, but doesn't
  validate current ratings, voltage drop, or power budget — `harness-check`
  is meant to run alongside it, not replace it.
- **KiCad ERC/DRC**, **kicad-tools**, **VelaTrace**, etc. validate a single
  board's schematic/layout. `harness-check` operates one level up, across
  the whole electromechanical system's wiring and power architecture.
- **Battery/IoT power estimators** (Wisebatt, VBatPower, etc.) model a
  single board's power draw; they don't model a harness with multiple
  connectors, fuses, and cable runs.

## License

MIT
