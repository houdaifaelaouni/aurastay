from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Service(Strict):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=100)
    price: float = Field(ge=0, le=10000, allow_inf_nan=False)
    basis: Literal['stay', 'night'] = 'stay'

class PropertyInput(Strict):
    name: str = Field(min_length=3, max_length=120)
    city: str = Field(min_length=2, max_length=100)
    country: str = Field(min_length=2, max_length=100)
    address: str = Field(default='', max_length=250)
    type: Literal['Apartment', 'Villa', 'Penthouse', 'Cottage'] = 'Apartment'
    category: Literal['City breaks', 'Coastal', 'Countryside', 'Villas'] = 'City breaks'
    description: str = Field(min_length=20, max_length=5000)
    price: float = Field(gt=0, le=100000, allow_inf_nan=False)
    commission_rate: float = Field(ge=2, le=100, allow_inf_nan=False)
    guests: int = Field(ge=1, le=50)
    bedrooms: int = Field(ge=0, le=30)
    bathrooms: int = Field(default=1, ge=1, le=30)
    amenities: list[str] = Field(default_factory=list, max_length=30)
    photos: list[str] = Field(default_factory=list, max_length=20)
    services: list[Service] = Field(default_factory=list, max_length=20)
    status: Literal['draft', 'published', 'archived'] = 'draft'
    @model_validator(mode='after')
    def valid_photos(self):
        if any(not (p.startswith('https://') or p.startswith('/api/media/')) for p in self.photos):
            raise ValueError('Photos must be secure image URLs or uploaded photos')
        if self.status == 'published' and not self.photos:
            raise ValueError('Add at least one photo before publishing')
        if len({s.id for s in self.services}) != len(self.services):
            raise ValueError('Service IDs must be unique')
        return self

class DateRange(Strict):
    check_in: date
    check_out: date
    @model_validator(mode='after')
    def range_valid(self):
        if self.check_out <= self.check_in: raise ValueError('Check-out must be after check-in')
        if (self.check_out-self.check_in).days > 365: raise ValueError('A stay cannot exceed 365 nights')
        return self

class QuoteInput(DateRange):
    guests: int = Field(ge=1, le=50)
    services: list[str] = Field(default_factory=list)
    @model_validator(mode='after')
    def future_dates(self):
        if self.check_in < date.today(): raise ValueError('Check-in cannot be in the past')
        return self

class BookingInput(QuoteInput):
    guest_name: str = Field(min_length=2, max_length=120)
    guest_email: EmailStr
    guest_phone: str = Field(min_length=6, max_length=30)
    accepted_terms: Literal[True]

class BlockInput(DateRange):
    reason: str = Field(min_length=2, max_length=200)
    kind: Literal['maintenance', 'owner', 'external'] = 'maintenance'

class TeamInput(Strict):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(default='', max_length=40)
    role: Literal['Manager', 'Commercial agent', 'Cleaning staff', 'Maintenance']
    active: bool = True
    property_ids: list[str] = Field(default_factory=list)

class ExpenseInput(Strict):
    property_id: str
    amount: float = Field(gt=0, le=1000000, allow_inf_nan=False)
    date: date
    category: Literal['Repairs', 'Cleaning', 'Utilities', 'Furniture', 'Supplies', 'Other']
    description: str = Field(min_length=3, max_length=1500)
    payer: Literal['agency', 'owner'] = 'agency'
    reimbursement: Literal['not_applicable', 'pending', 'reimbursed'] = 'not_applicable'
    @model_validator(mode='after')
    def valid_reimbursement(self):
        if self.payer == 'owner' and self.reimbursement != 'not_applicable':
            raise ValueError('Owner-paid expenses cannot be reimbursed to the agency')
        return self

class FeeSettings(Strict):
    percentage: float = Field(ge=0, le=20, allow_inf_nan=False)
    per_night: float = Field(ge=0, le=100, allow_inf_nan=False)
    minimum: float = Field(ge=0, le=1000, allow_inf_nan=False)
    maximum: float = Field(ge=0, le=1000, allow_inf_nan=False)
    @model_validator(mode='after')
    def ordered(self):
        if self.maximum < self.minimum: raise ValueError('Maximum must be at least the minimum')
        return self