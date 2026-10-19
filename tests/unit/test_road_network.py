import networkx as nx
import pytest
from pyproj import Transformer
from shapely.geometry import LineString

from delivery_dispatch.services.road_network import OSMnxRoadProjector


def test_projects_coordinate_to_nearest_road_geometry():
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:31983", always_xy=True)
    longitude, latitude = -43.95, -19.91
    x, y = transformer.transform(longitude, latitude)

    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "EPSG:31983"
    graph.add_node(1, x=x - 100, y=y)
    graph.add_node(2, x=x + 100, y=y)
    graph.add_edge(
        1,
        2,
        0,
        geometry=LineString([(x - 100, y), (x + 100, y)]),
    )

    projector = OSMnxRoadProjector("unused.graphml")
    projector._graph = graph

    corrected_latitude, corrected_longitude = projector.project([(latitude - 0.0005, longitude)])[0]

    assert corrected_latitude == pytest.approx(latitude, abs=1e-6)
    assert corrected_longitude == pytest.approx(longitude, abs=1e-5)
