from pydantic import BaseModel


class BuildingCreate(BaseModel):
    description: str
    address: str
    bedroom_no: str
    bathroom_no:str
    furnished: str
    available_facilities: str
    interior_features: str
    exterior_features: str
    purpose: str
    price: int
    payment_frequency: int
    property_type: str

class Building(BuildingCreate):
    id: str

class BuildingDisplay(BuildingCreate):
    pass