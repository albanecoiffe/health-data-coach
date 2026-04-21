from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HeartRateZone:
    id: str
    label: str
    column: str
    lower_bpm: int | None
    upper_bpm: int | None
    color: str

    @property
    def range_label(self) -> str:
        if self.lower_bpm is None and self.upper_bpm is not None:
            return f"< {self.upper_bpm} bpm"
        if self.lower_bpm is not None and self.upper_bpm is not None:
            return f"{self.lower_bpm}-{self.upper_bpm - 1} bpm"
        if self.lower_bpm is not None:
            return f">= {self.lower_bpm} bpm"
        return "non defini"


HEART_RATE_ZONES: tuple[HeartRateZone, ...] = (
    # Modifier les seuils cardiaques du coureur ici.
    HeartRateZone("z1", "Z1", "z1_min", None, 145, "#2f80ed"),
    HeartRateZone("z2", "Z2", "z2_min", 145, 159, "#00a7a7"),
    HeartRateZone("z3", "Z3", "z3_min", 159, 173, "#2ecc71"),
    HeartRateZone("z4", "Z4", "z4_min", 173, 186, "#f2994a"),
    HeartRateZone("z5", "Z5", "z5_min", 186, None, "#eb5757"),
)

LOW_INTENSITY_ZONE_IDS = ("z1", "z2", "z3")
HIGH_INTENSITY_ZONE_IDS = ("z4", "z5")
LOW_INTENSITY_LABEL = "Low intensity (Z1-Z3)"
HIGH_INTENSITY_LABEL = "High intensity (Z4-Z5)"


def zone_by_id(zone_id: str) -> HeartRateZone:
    return next(zone for zone in HEART_RATE_ZONES if zone.id == zone_id)


def zone_color_map() -> dict[str, str]:
    return {zone.label: zone.color for zone in HEART_RATE_ZONES}


def zone_column_labels() -> dict[str, str]:
    return {zone.column: zone.label for zone in HEART_RATE_ZONES}


def zone_columns(zone_ids: tuple[str, ...] | None = None) -> list[str]:
    if zone_ids is None:
        return [zone.column for zone in HEART_RATE_ZONES]
    selected = set(zone_ids)
    return [zone.column for zone in HEART_RATE_ZONES if zone.id in selected]


def zone_minutes(record: Any, zone_ids: tuple[str, ...] | None = None) -> float:
    return sum(float(getattr(record, column, 0) or 0) for column in zone_columns(zone_ids))


def low_intensity_minutes(record: Any) -> float:
    return zone_minutes(record, LOW_INTENSITY_ZONE_IDS)


def high_intensity_minutes(record: Any) -> float:
    return zone_minutes(record, HIGH_INTENSITY_ZONE_IDS)


def zone_ranges_rows() -> list[dict[str, str]]:
    return [
        {
            "Zone": zone.label,
            "BPM": zone.range_label,
            "Couleur": zone.color,
        }
        for zone in HEART_RATE_ZONES
    ]
