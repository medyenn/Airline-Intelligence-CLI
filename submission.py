import os
from abc import ABC, abstractmethod

import re
import requests
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.aviationstack.com/v1/airlines?access_key="
API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

console = Console()


class Airline(BaseModel):

    name: str = Field(min_length=2)
    fleet_size: int = Field(ge=0)
 
    country: str | None = Field(default=None, min_length=2)
    iata: str | None = Field(default=None, min_length=2, max_length=2)
    icao: str | None = Field(default=None, min_length=3, max_length=3)
    average_age: float | None = Field(default=None, ge=0)
    founded: int | None = Field(default=None, ge=1900)
    hub: str | None = None
    status: str | None = None
    type_: str | None = None


class DataSource(ABC):

    @abstractmethod
    def search_airline(self, name: str) -> Airline:
        raise NotImplementedError


class AviationStackSource(DataSource):

    def search_airline(self, name: str) -> Airline:

        try:
            nlst = name.split(' ')
            if len(nlst) == 2:
                slug = f'{nlst[0].title()}%20{nlst[1].title()}'
            elif len(nlst) == 1:
                slug = nlst[0].title()
            response = requests.get(f'{API_URL}{API_KEY}&airline_name={slug}')
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error while contacting Aviationstack: {e}")

        payload = response.json()
        if "error" in payload:
            raise ValueError(payload["error"]["message"])

        if not payload.get("data"):
            raise ValueError(f"No airline found matching '{name}'.")

        data = payload["data"][0]

        return Airline(
            name=self._require(data, "airline_name", "airline name"),
            country=self._require(data, "country_name", "country"),
            iata=self._require(data, "iata_code", "IATA code"),
            icao=self._require(data, "icao_code", "ICAO code"),
            hub=self._require(data, "hub_code", "hub code"),
            fleet_size=int(data.get("fleet_size") or 0),
            average_age=float(data.get("fleet_average_age") or 0),
            founded=self._parse_founded(data),
            status=data.get("status") or "Unknown",
            type_=data.get("type") or "Unknown",
        )

    @staticmethod
    def _require(data: dict, key: str, label: str) -> str:
        """Fetch a required field, raising a clean, user-facing error if it's
        missing rather than letting a raw KeyError/ValidationError bubble up.
        Free-tier responses (and smaller/regional airlines) sometimes omit
        fields like hub_code or country_name.
        """
        value = data.get(key)
        if not value:
            raise ValueError(f"Missing '{label}' for this airline.")
        return value

    @staticmethod
    def _parse_founded(data: dict) -> int:
        """BUG FIX: the old code defaulted missing date_founded to 0, which
        always failed the Airline model's `founded >= 1900` constraint and
        surfaced as an ugly, uncaught pydantic ValidationError. Now it fails
        early with a clear message instead.
        """
        raw = data.get("date_founded")
        if not raw:
            raise ValueError("Missing founding year for this airline.")
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise ValueError(f"Unexpected founding year value: {raw!r}")


class AirlineAnalyzer:

    @staticmethod
    def classify_fleet(airline: Airline) -> str:

        if airline.fleet_size < 50:
            return "Small"

        if airline.fleet_size <= 150:
            return "Medium"

        return "Large"

    @staticmethod
    def classify_age(airline: Airline) -> str:

        if airline.average_age < 7:
            return "Modern"

        if airline.average_age <= 12:
            return "Balanced"

        return "Aging"

    @staticmethod
    def years_in_service(airline: Airline) -> int:

        return datetime.now().year - airline.founded

    @staticmethod
    def operational_maturity(airline: Airline) -> str:
        years = AirlineAnalyzer.years_in_service(airline)

        if years < 10:
            return "New"

        if years < 25:
            return "Developing"

        if years < 50:
            return "Mature"

        return "Legacy"

    @staticmethod
    def fleet_efficiency(airline: Airline) -> str:
        health = AirlineAnalyzer.classify_age(airline)

        if health == "Modern":
            return "Excellent"

        if health == "Balanced":
            return "Good"

        return "Needs Renewal"

    @staticmethod
    def age_score(airline: Airline) -> float:
        score = 10 - (airline.average_age / 2)

        return round(max(score, 0), 1)

    @staticmethod
    def airline_score(airline: Airline) -> float:
        # Composite score created for this project.
        # Combines fleet modernity, fleet size and operational experience.
        age = AirlineAnalyzer.age_score(airline)

        fleet = min(airline.fleet_size / 30, 10)

        experience = min(
            AirlineAnalyzer.years_in_service(airline) / 5,
            10
        )

        score = (
            age * 0.4
            + fleet * 0.3
            + experience * 0.3
        )

        return round(score, 1)

    @staticmethod
    def generate_summary(airline: Airline) -> dict:

        return {

            "Name": airline.name,

            "Country": airline.country,

            "IATA": airline.iata,

            "ICAO": airline.icao,

            "Hub": airline.hub,

            "Founded": airline.founded,

            "Years in Service": AirlineAnalyzer.years_in_service(airline),

            "Operational Maturity": AirlineAnalyzer.operational_maturity(airline),

            "Status": airline.status.capitalize(),

            "Type": airline.type_.capitalize(),

            "Fleet Size": airline.fleet_size,

            "Fleet Category": AirlineAnalyzer.classify_fleet(airline),

            "Average Fleet Age": airline.average_age,

            "Fleet Health": AirlineAnalyzer.classify_age(airline),

            "Fleet Efficiency": AirlineAnalyzer.fleet_efficiency(airline),

            "Age Score": AirlineAnalyzer.age_score(airline),

            "Overall Airline Score": AirlineAnalyzer.airline_score(airline),

        }

    @staticmethod
    def compare(first: Airline, second: Airline) -> dict:

        return {
            "Fleet Size": (first.fleet_size, second.fleet_size),
            "Fleet Category": (
                AirlineAnalyzer.classify_fleet(first),
                AirlineAnalyzer.classify_fleet(second),
            ),
            "Fleet Health": (
                AirlineAnalyzer.classify_age(first),
                AirlineAnalyzer.classify_age(second),
            ),
            "Operational Maturity": (
                AirlineAnalyzer.operational_maturity(first),
                AirlineAnalyzer.operational_maturity(second),
            ),
            "Overall Score": (
                AirlineAnalyzer.airline_score(first),
                AirlineAnalyzer.airline_score(second),
            ),
        }


class Session:

    def __init__(self):

        self.current_airline: Airline | None = None
        self.comparison: tuple[Airline, Airline] | None = None


session = Session()


class ReportGenerator:

    @staticmethod
    def export_csv(summary: dict, filename: str):

        df = pd.DataFrame(summary.items(), columns=["Metric", "Value"])

        df.to_csv(filename, index=False)

    @staticmethod
    def export_png(summary: dict, filename: str):
        # IMPROVEMENT: the original chart put Fleet Size (hundreds) on the
        # same axis as Average Fleet Age / Years in Service / Score (single
        # to double digits), which made everything but Fleet Size invisible.
        # Splitting into two panels by scale keeps every bar readable.
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))

        scale_metrics = {
            "Fleet Size": summary["Fleet Size"],
            "Years in Service": summary["Years in Service"],
        }

        rating_metrics = {
            "Avg Fleet Age": summary["Average Fleet Age"],
            "Overall Score": summary["Overall Airline Score"],
        }

        bars1 = axes[0].bar(scale_metrics.keys(), scale_metrics.values(), color="steelblue")
        axes[0].bar_label(bars1)
        axes[0].set_title("Scale")

        bars2 = axes[1].bar(rating_metrics.keys(), rating_metrics.values(), color="darkorange")
        axes[1].bar_label(bars2)
        axes[1].set_title("Ratings")

        for ax in axes:
            ax.tick_params(axis="x", rotation=20)

        fig.suptitle(summary["Name"])

        plt.tight_layout()

        plt.savefig(filename)

        plt.close(fig)


def print_airline(airline: Airline):

    summary = AirlineAnalyzer.generate_summary(airline)

    table = Table(title=summary["Name"])

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    for key, value in summary.items():
        table.add_row(key, str(value))

    console.print(table)


def search_airline(source: DataSource):

    name = input("Airline: ").strip()

    try:

        airline = source.search_airline(name)
        session.current_airline = airline

        print_airline(airline)

    except Exception as e:

        console.print(f"[red]{e}[/red]")


def compare_airlines(source: DataSource):

    first = input("First Airline: ")

    second = input("Second Airline: ")

    try:

        airline1 = source.search_airline(first)

        airline2 = source.search_airline(second)

        session.comparison = (airline1, airline2)

        comparison = AirlineAnalyzer.compare(airline1, airline2)

        table = Table(title="Comparison")

        table.add_column("Metric", style="cyan")
        table.add_column(airline1.name, style="green")
        table.add_column(airline2.name, style="yellow")

        for metric, values in comparison.items():
            table.add_row(metric, str(values[0]), str(values[1]))

        console.print(table)

    except Exception as e:

        console.print(f"[red]{e}[/red]")


def slugify(text: str) -> str:

    return re.sub(r"\W+", "_", text.lower()).strip("_")


def export_png() -> None:

    if session.current_airline is None:
        console.print("[red]Search an airline first.[/red]")
        return

    summary = AirlineAnalyzer.generate_summary(session.current_airline)

    filename = slugify(session.current_airline.name) + ".png"

    ReportGenerator.export_png(summary, filename)

    console.print(f"[green]PNG exported as {filename}[/green]")


def export_csv() -> None:

    if session.current_airline is None:
        console.print("[red]Search an airline first.[/red]")
        return

    summary = AirlineAnalyzer.generate_summary(session.current_airline)

    filename = slugify(session.current_airline.name) + ".csv"

    ReportGenerator.export_csv(summary, filename)

    console.print(f"[green]CSV exported as {filename}[/green]")


def print_menu() -> None:

    console.print("\n[bold cyan]AIRLINE INTELLIGENCE CLI[/bold cyan]\n")

    console.print("1. Search Airline")
    console.print("2. Compare Two Airlines")
    console.print("3. Export PNG Summary")
    console.print("4. Export CSV")
    console.print("5. Exit")


def main():

    if API_KEY is None:

        console.print("[red]Missing AVIATIONSTACK_API_KEY[/red]")

        return

    source = AviationStackSource()

    while True:

        print_menu()

        choice = input("\nChoice: ")

        if choice == "1":

            search_airline(source)

        elif choice == "2":

            compare_airlines(source)
        elif choice == "3":

            export_png()

        elif choice == "4":

            export_csv()

        elif choice == "5":

            console.print("[green]Goodbye![/green]")

            break

        else:

            console.print("[red]Invalid choice.[/red]")


if __name__ == "__main__":
    main()
