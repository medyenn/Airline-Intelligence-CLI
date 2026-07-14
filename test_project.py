from project import Airline, AirlineAnalyzer
from pydantic import ValidationError
import pytest


def make_airline(
    fleet_size=180,
    average_age=5.5,
    founded=1997
):
    return Airline(
        name="Qatar Airways",
        country="Qatar",
        iata="QR",
        icao="QTR",
        hub="DOH",
        fleet_size=fleet_size,
        average_age=average_age,
        founded=founded,
        status="active",
        type_="scheduled"
    )


def test_classify_fleet():

    assert AirlineAnalyzer.classify_fleet(
        make_airline(fleet_size=20)
    ) == "Small"

    assert AirlineAnalyzer.classify_fleet(
        make_airline(fleet_size=120)
    ) == "Medium"

    assert AirlineAnalyzer.classify_fleet(
        make_airline(fleet_size=220)
    ) == "Large"


def test_classify_age():

    assert AirlineAnalyzer.classify_age(
        make_airline(average_age=5)
    ) == "Modern"

    assert AirlineAnalyzer.classify_age(
        make_airline(average_age=10)
    ) == "Balanced"

    assert AirlineAnalyzer.classify_age(
        make_airline(average_age=16)
    ) == "Aging"


def test_airline_score():

    airline = make_airline()

    score = AirlineAnalyzer.airline_score(airline)

    assert isinstance(score, float)
    assert 0 <= score <= 10


def test_generate_summary():

    airline = make_airline()

    summary = AirlineAnalyzer.generate_summary(airline)

    assert summary["Name"] == "Qatar Airways"
    assert summary["Fleet Category"] == "Large"
    assert summary["Fleet Health"] == "Modern"
    assert "Fleet Efficiency" in summary
    assert "Operational Maturity" in summary
    assert "Age Score" in summary
    assert "Overall Airline Score" in summary


def test_airline_validation():

    with pytest.raises(ValidationError):
        Airline(
            name="A",
            country="Qatar",
            iata="QR",
            icao="QTR",
            hub="DOH",
            fleet_size=-1,
            average_age=5,
            founded=1997,
            status="active",
            type_="scheduled"
        )


def test_compare():

    qatar = make_airline(
        fleet_size=180,
        average_age=5,
        founded=1997
    )

    ryanair = make_airline(
        fleet_size=620,
        average_age=10,
        founded=1984
    )

    comparison = AirlineAnalyzer.compare(qatar, ryanair)

    assert comparison["Fleet Size"] == (180, 620)
    assert comparison["Average Fleet Age"] == (5, 10)
    assert comparison["Founded"] == (1997, 1984)
