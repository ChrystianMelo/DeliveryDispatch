# DeliveryDispatch

Finding nearby couriers for a restaurant with low latency requires organizing geographic
positions and reducing the search space without sacrificing accuracy. DeliveryDispatch is being
built to explore this problem in Belo Horizonte by combining Geohash, a compact Trie, spatial
simulation, and road-network geometry.

In addition to advancing the solution, its development provides hands-on experience with data
structures, geospatial algorithms, integration with external services, and automated testing.

## Overview

The current workflow is as follows:

- prepares and geocodes a dataset of bars and restaurants;
- generates a synthetic fleet distributed around these establishments;
- snaps courier positions to the OpenStreetMap road network;
- converts coordinates into Geohashes;
- organizes establishments and couriers in compact Trie-based indexes;
- preselects couriers from the restaurant's Geohash cell and its adjacent cells;
- filters candidates by Haversine distance and highlights only those within the search radius;
- provides an interactive dashboard for searching restaurants and generating the simulated fleet.

## Requirements

- Python 3.12 or later;
- an internet connection if the processed dataset or road network is not yet available locally.

## Installation and usage

On Windows, run the following commands from the repository root:

```powershell
.\scripts\config.bat
.\scripts\run.bat
```

Open `http://127.0.0.1:8050` in your browser. In the interface, search for a restaurant by name
or address, set the search radius in kilometers, enter the number `N`, and select
**Gerar entregadores** (Generate couriers). Each generation replaces the previous fleet on the
map. When you select a restaurant, couriers found within the radius turn green,
while the others remain gray. Unselected restaurants are gray, while the selected restaurant is
highlighted in orange. Restaurants use a food-service symbol, while couriers use a
two-wheeled vehicle symbol.

The fleet is generated exclusively through the dashboard: the run command does not accept a
number of couriers as an argument.

To view the other options:

```powershell
.\scripts\run.bat --help
```

<details>
<summary>Linux and macOS</summary>

```bash
python -m venv .venv
source .venv/bin/activate
python scripts/tasks.py setup
python scripts/tasks.py run
```

</details>

## Data and cache

The dataset enriched with coordinates is stored in
`data/processed/bares_geocodificados.csv`. Geocoding responses are cached in `data/cache/` to
avoid repeated requests. The ready-to-use road network is stored in
`data/processed/belo_horizonte_drive.graphml`, allowing it to be distributed with the project.

The `--rebuild-processed` option rebuilds the processed dataset. This operation may require
thousands of requests and must comply with the
[Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/).

When the fleet is generated for the first time, the application may also download the Belo
Horizonte road network. Subsequent generations reuse the file saved in `data/processed/`.

The geographic data used by the project is provided by
[OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.

## Tests

On Windows:

```powershell
.\scripts\run_tests.bat
```

In other environments:

```bash
python scripts/tasks.py test
```

## Structure

- `src/delivery_dispatch/`: application implementation;
- `data/`: original and processed datasets, plus local caches;
- `tests/`: automated tests;
- `experiments/`: experimental scenarios and results;
- `docs/`: report and documentation.

## Report

The full problem description, implementation decisions, algorithm analysis, and experimental
results are consolidated in the report:

- [LaTeX source](docs/report.tex)
- [Download the report as a PDF](https://github.com/ChrystianMelo/DeliveryDispatch/releases/download/report/report.pdf)
