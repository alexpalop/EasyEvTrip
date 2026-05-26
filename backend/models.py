from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date


# Categoria de cotxe segons mida de bateria
CarCategory = Literal["compact", "medium", "large", "premium"]


class PlanRequest(BaseModel):
    """Dades que envia el frontend per demanar una planificació."""
    origin: str = Field(..., description="Ciutat d'origen, ex: 'Barcelona'")
    destination: str = Field(..., description="Ciutat de destí, ex: 'Sevilla'")
    car_category: CarCategory = Field(..., description="Categoria del cotxe")
    travel_date: date = Field(..., description="Data del viatge")
    departure_window: Literal["morning_early", "morning_late", "afternoon"] = Field(
        ..., description="Franja horària de sortida"
    )
    lunch_window: Optional[Literal["13_14", "13_30_15", "14_15_30", "none"]] = Field(
        "13_30_15", description="Franja per dinar, o 'none' si no cal"
    )
    needs_overnight: Literal["yes", "no", "auto"] = Field(
        "auto", description="Si cal dormir pel camí"
    )


class PlanStop(BaseModel):
    """Una parada del pla del viatge."""
    type: Literal["start", "charge", "lunch", "hotel", "destination"]
    name: str
    description: str
    arrival_time: str  # "HH:MM"
    departure_time: Optional[str] = None  # buit si és destí final
    battery_arrival: Optional[int] = None  # % de bateria a l'arribada
    battery_departure: Optional[int] = None  # % de bateria a la sortida
    location: Optional[str] = None  # localitat/municipi de la parada
    lat: Optional[float] = None
    lon: Optional[float] = None
    km_pos: Optional[float] = None
    walk_to_lat: Optional[float] = None  # destí a peu des del carregador
    walk_to_lon: Optional[float] = None


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Valoració de l'1 al 5")
    comment: Optional[str] = Field(None, max_length=1000)
    origin: Optional[str] = None
    destination: Optional[str] = None
    car_category: Optional[str] = None


class PlanResponse(BaseModel):
    """Resposta amb el pla complet."""
    total_distance_km: int
    total_duration_minutes: int
    estimated_charge_cost_eur: float
    stops: list[PlanStop]
    notes: Optional[str] = None
    route_polyline: Optional[list[list[float]]] = None  # [[lat,lon], ...] simplificat
