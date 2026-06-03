from dataclasses import dataclass


@dataclass(frozen=True)
class VisualToken:
    """A visual patch token from UAV or satellite image."""

    token_id: str
    view: str
    x: float
    y: float
    feature: tuple[float, ...]
    label_hint: str = ""


@dataclass(frozen=True)
class SemanticAnchor:
    """A VLM-derived stable semantic cue."""

    name: str
    weight: float = 1.0


@dataclass(frozen=True)
class MapToken:
    """A simplified vector-map topology token."""

    token_id: str
    category: str
    x: float
    y: float
    orientation: float = 0.0
    confidence: float = 1.0

