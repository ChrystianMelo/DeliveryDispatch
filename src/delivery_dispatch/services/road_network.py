"""Projeção de coordenadas simuladas sobre a malha viária do OpenStreetMap."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from delivery_dispatch.services.courier_generation import Coordinates

DEFAULT_PLACE = "Belo Horizonte, Minas Gerais, Brasil"


class RoadNetworkError(RuntimeError):
    """Indica falha ao carregar ou consultar a malha viária."""


class OSMnxRoadProjector:
    """Projeta pontos para a via de automóveis mais próxima com OSMnx."""

    def __init__(self, cache_path: str | Path, *, place: str = DEFAULT_PLACE) -> None:
        self.cache_path = Path(cache_path)
        self.place = place
        self._graph: Any | None = None

    def project(self, coordinates: Sequence[Coordinates]) -> list[Coordinates]:
        if not coordinates:
            return []

        try:
            import geopandas as gpd
            import osmnx as ox
            from shapely.geometry import LineString, Point
        except ImportError as error:
            raise RoadNetworkError(
                "OSMnx não está instalado; execute scripts\\config.bat"
            ) from error

        try:
            graph = self._load_graph(ox)
            points = gpd.GeoSeries(
                [Point(longitude, latitude) for latitude, longitude in coordinates],
                crs="EPSG:4326",
            ).to_crs(graph.graph["crs"])
            nearest_edges = ox.distance.nearest_edges(graph, X=points.x, Y=points.y)
            corrected_points = []

            for point, (start, end, key) in zip(points, nearest_edges, strict=True):
                edge = graph.edges[start, end, key]
                geometry = edge.get("geometry")
                if geometry is None:
                    start_node = graph.nodes[start]
                    end_node = graph.nodes[end]
                    geometry = LineString(
                        [
                            (start_node["x"], start_node["y"]),
                            (end_node["x"], end_node["y"]),
                        ]
                    )
                corrected_points.append(geometry.interpolate(geometry.project(point)))

            geographic_points = gpd.GeoSeries(
                corrected_points,
                crs=graph.graph["crs"],
            ).to_crs("EPSG:4326")
            return [(point.y, point.x) for point in geographic_points]
        except RoadNetworkError:
            raise
        except Exception as error:
            raise RoadNetworkError("falha ao projetar entregadores na malha viária") from error

    def _load_graph(self, ox: Any) -> Any:
        if self._graph is not None:
            return self._graph

        if self.cache_path.exists():
            self._graph = ox.io.load_graphml(self.cache_path)
            return self._graph

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        graph = ox.graph.graph_from_place(self.place, network_type="drive", simplify=True)
        self._graph = ox.projection.project_graph(graph)
        ox.io.save_graphml(self._graph, self.cache_path)
        return self._graph
