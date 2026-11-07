"""Data model for elevator/escalator units and their outages."""

from dataclasses import dataclass, field, asdict


@dataclass
class Unit:
    station: str
    kind: str            # "elevator" | "escalator"
    location: str        # free-text location within the station
    lines: list = field(default_factory=list)  # line letters, e.g. ["G"]
    in_service: bool = True
    reason: str = ""
    return_estimate: str = ""
    station_code: str = ""

    def key(self) -> str:
        return f"{self.station_code or self.station}|{self.kind}|{self.location}"

    def label(self) -> str:
        loc = self.location
        if loc.lower().startswith(self.kind):
            return f"{self.station} — {loc}"
        return f"{self.station} — {self.kind.title()} {loc}".strip()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Unit":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
