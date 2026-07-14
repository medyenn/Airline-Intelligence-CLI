
# Airline Intelligence CLI

#### Video Demo: https://youtu.be/yQ4LwjvHais

#### Description:

Airline Intelligence CLI is a command-line analytics platform written in Python that provides meaningful insights about commercial airlines using real aviation data retrieved from the AviationStack API.

Unlike a simple airline search tool, this project focuses on transforming raw airline information into analytical metrics that help users better understand an airline's operational profile. The application computes additional indicators such as fleet category, fleet health, operational maturity, fleet efficiency, age score, and an overall airline score. These metrics are generated locally by the application rather than returned by the API, making the project an analytics platform instead of merely a data viewer.

The application offers five main features:

- Search for an airline by name.
- Compare two airlines side by side.
- Export an airline summary as a CSV report.
- Export a graphical PNG summary using Matplotlib.
- Exit the application.

## Project Architecture

The project follows an object-oriented design where each class has a single responsibility.

### Airline

The `Airline` class is the domain model of the application. It is implemented using Pydantic to validate incoming data from the API and ensure that every airline object contains valid information before being analyzed.

### DataSource

`DataSource` is an abstract base class representing any provider capable of retrieving airline information. Using an abstraction allows future implementations without modifying the rest of the application.

### AviationStackSource

This class implements `DataSource` by connecting to the AviationStack REST API using the Requests library. It handles HTTP requests, error checking, JSON parsing, and converts the API response into validated `Airline` objects.

### AirlineAnalyzer

This is the core of the project.

Instead of displaying raw API data, the analyzer computes several derived metrics including:

- Fleet Category
- Fleet Health
- Operational Maturity
- Fleet Efficiency
- Age Score
- Overall Airline Score

These calculations transform factual airline information into meaningful operational insights.

### ReportGenerator

The `ReportGenerator` class exports analytical results in two formats:

- CSV reports using Pandas.
- PNG bar charts using Matplotlib.

Separating report generation from analysis keeps the code modular and easy to extend.

### Session

The `Session` class stores the most recently searched airline and comparison results. This allows reports to be exported without requiring another API request.

## Design Decisions

One important design decision was introducing the `DataSource` abstraction. Although the project currently uses AviationStack, this design allows replacing the data provider with another API or even a local database without changing the analyzer or user interface.

Another important decision was choosing Pydantic instead of manually validating every field. This greatly simplified validation while making the code safer and more readable.

Finally, I decided to compute several custom analytical metrics rather than simply presenting API data. This makes the application more useful and demonstrates analytical thinking rather than basic API consumption.

## Testing

The project includes a `test_project.py` file written with Pytest.

The tests verify:

- Fleet classification
- Fleet age classification
- Airline score calculation
- Summary generation
- Airline comparison
- Pydantic model validation

## Technologies Used

- Python
- Requests
- Pydantic
- Rich
- Pandas
- Matplotlib
- Pytest
- AviationStack API

## Future Improvements

Several improvements are planned for future versions:

- Support multiple aviation APIs.
- Add airline ranking by country or region.
- Compare more operational metrics.
- Generate richer visual reports.
- Cache API responses to reduce network requests.
- Build a web interface while keeping the analytics engine unchanged.

This project combines object-oriented programming, API integration, data validation, analytical computation, report generation, and automated testing into a complete airline analytics application.
````
PlaneSpottersSource
        │
        ▼
    Aircraft
        │
        ▼
Fleet (collection + domain behaviors)
        │
        ▼
FleetAnalyzer (analytics engine)
        │
        ▼
  ReportGenerator
        │
        ▼
       CLI
````
