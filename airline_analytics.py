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
            slug = ''
            if len(nlst) >= 2:
                for word in nlst:
                    slug += f'{word.title()}%20' if nlst[-1] != word else word.title()
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
        from matplotlib.patches import FancyBboxPatch
 
        accent, dark, grey = "#0B3D91", "#111827", "#6B7280"
        card_bg, border, neutral = "#F3F4F6", "#E5E7EB", "#E5E7EB"
        status_colors = {
            "Modern": "#16A34A", "Balanced": "#D97706", "Aging": "#DC2626",
            "Excellent": "#16A34A", "Good": "#D97706", "Needs Renewal": "#DC2626",
            "Unknown": "#9CA3AF",
        }
 
        def box(ax, x, y, w, h, color, rounding=0.02):
            ax.add_patch(FancyBboxPatch((x, y), w, h,
                         boxstyle=f"round,pad=0,rounding_size={rounding}",
                         linewidth=0, facecolor=color))
 
        fig = plt.figure(figsize=(8, 6.6), facecolor="white")
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
 
        ax.text(0.06, 0.94, summary["Name"], fontsize=22, fontweight="bold",
                 color=dark, ha="left", va="top")
        ax.text(0.06, 0.88, f'{summary["IATA"]} · {summary["ICAO"]}  |  {summary["Country"]}',
                 fontsize=11, color=grey, ha="left", va="top")
        ax.plot([0.06, 0.94], [0.83, 0.83], color=border, linewidth=1)
 
        ax.text(0.06, 0.79, "KEY METRICS", fontsize=9.5, color=grey, fontweight="bold")
        kpis = [
            (summary["Fleet Size"], "Fleet Size"),
            (summary["Average Fleet Age"], "Avg. Fleet Age"),
            (summary["Years in Service"], "Years in Service"),
        ]
        x = 0.06
        for value, label in kpis:
            box(ax, x, 0.6, 0.27, 0.17, card_bg)
            ax.text(x + 0.135, 0.71, str(value), fontsize=20, fontweight="bold",
                     color=accent, ha="center", va="center")
            ax.text(x + 0.135, 0.65, label, fontsize=9.5, color=grey, ha="center", va="center")
            x += 0.29
 
        ax.text(0.06, 0.535, "OVERALL SCORE", fontsize=9.5, color=grey, fontweight="bold")
        score = summary["Overall Airline Score"]
        numeric_score = score if isinstance(score, (int, float)) else 0
        score_color = "#16A34A" if numeric_score >= 7 else "#D97706" if numeric_score >= 4 else "#DC2626"
        box(ax, 0.06, 0.46, 0.88, 0.045, "#E5E7EB")
        fill_w = max(0.88 * min(numeric_score, 10) / 10, 0.045)
        box(ax, 0.06, 0.46, fill_w, 0.045, score_color)
        ax.text(0.94, 0.4825, f"{score} / 10", fontsize=11, fontweight="bold",
                 color=dark, ha="right", va="center")
 
        ax.text(0.06, 0.375, "CLASSIFICATION", fontsize=9.5, color=grey, fontweight="bold")
        badges = [
            (summary["Fleet Category"], neutral),
            (summary["Fleet Health"], status_colors.get(summary["Fleet Health"], neutral)),
            (summary["Operational Maturity"], neutral),
            (summary["Fleet Efficiency"], status_colors.get(summary["Fleet Efficiency"], neutral)),
        ]
        x = 0.06
        for label, color in badges:
            w = 0.05 + len(str(label)) * 0.013
            box(ax, x, 0.3, w, 0.058, color, rounding=0.03)
            ax.text(x + w / 2, 0.329, str(label), fontsize=9, fontweight="bold",
                     color="white" if color != neutral else dark, ha="center", va="center")
            x += w + 0.02
 
        ax.plot([0.06, 0.94], [0.225, 0.225], color=border, linewidth=1)
        footer = [
            ("HUB", summary["Hub"]), ("FOUNDED", summary["Founded"]),
            ("STATUS", summary["Status"]), ("TYPE", summary["Type"]),
        ]
        x = 0.06
        for label, value in footer:
            ax.text(x, 0.17, label, fontsize=8, color=grey, fontweight="bold")
            ax.text(x, 0.1, str(value), fontsize=10.5, color=dark)
            x += 0.23
 
        plt.savefig(filename, dpi=200, bbox_inches="tight", facecolor="white")
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
