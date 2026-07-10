from typing import Literal
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod


class DataSource(ABC):

    @abstractmethod
    def fetch(self):
        ...

    @abstractmethod
    def parse(self):
        ...

    @abstractmethod
    def load(self):
        ...


class PlaneSpottersSource(DataSource):
    ...


class Aircraft(BaseModel):
    registration: str = Field(min_length=1)
    model: str = Field(min_length=1)
    manufacturer: str = Field(min_length=1)
    age: float = Field(ge=0)
    status: Literal["Active", "Stored", "Retired", "Unknown"] = "Unknown"


class Fleet(BaseModel):
    aircraft: list[Aircraft] = Field(default_factory=list)

    def add_aircraft():
        ...

    def size():
        ...

    def average_age():
        ...

    def oldest():
        ...

    def newest():
        ...

    def manufacturers():
        ...

    def models():
        ...


class Airline(BaseModel):
    name: str
    country: str | None = None
    fleet: Fleet
