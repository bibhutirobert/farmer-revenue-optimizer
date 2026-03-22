import pytest
from utils.map_utils import extract_lat_lng, extract_polygon_coords, validate_india_bounds


def _clicked_result(lat: float, lng: float) -> dict:
    return {
        "last_clicked": {"lat": lat, "lng": lng},
        "all_drawings": [],
    }


def _marker_result(lat: float, lng: float) -> dict:
    return {
        "last_clicked": None,
        "all_drawings": [
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat],
                }
            }
        ],
    }


def _polygon_result(coords_lng_lat: list) -> dict:
    return {
        "last_clicked": None,
        "all_drawings": [
            {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords_lng_lat],
                }
            }
        ],
    }


def test_extract_from_click():
    lat, lng = extract_lat_lng(_clicked_result(19.076, 72.877))
    assert abs(lat - 19.076) < 1e-4
    assert abs(lng - 72.877) < 1e-4


def test_extract_from_marker_takes_priority_over_click():
    result = _marker_result(28.613, 77.209)
    result["last_clicked"] = {"lat": 10.0, "lng": 10.0}
    lat, lng = extract_lat_lng(result)
    assert abs(lat - 28.613) < 1e-4
    assert abs(lng - 77.209) < 1e-4


def test_extract_from_polygon_centroid():
    poly_coords = [[70, 20], [72, 20], [72, 22], [70, 22], [70, 20]]
    lat, lng = extract_lat_lng(_polygon_result(poly_coords))
    assert abs(lat - 21.0) < 0.1
    assert abs(lng - 71.0) < 0.1


def test_extract_returns_none_on_none_input():
    lat, lng = extract_lat_lng(None)
    assert lat is None
    assert lng is None


def test_extract_returns_none_on_empty_result():
    lat, lng = extract_lat_lng({"last_clicked": None, "all_drawings": []})
    assert lat is None
    assert lng is None


def test_extract_returns_none_on_empty_dict():
    lat, lng = extract_lat_lng({})
    assert lat is None
    assert lng is None


def test_polygon_coords_extracted():
    poly_coords = [[70, 20], [72, 20], [72, 22], [70, 22], [70, 20]]
    polygon = extract_polygon_coords(_polygon_result(poly_coords))
    assert polygon is not None
    assert len(polygon) == 5
    assert abs(polygon[0][0] - 20.0) < 1e-4
    assert abs(polygon[0][1] - 70.0) < 1e-4


def test_polygon_coords_none_when_no_drawing():
    assert extract_polygon_coords(_clicked_result(20.0, 78.0)) is None


def test_polygon_coords_none_on_none_input():
    assert extract_polygon_coords(None) is None


def test_valid_india_location():
    assert validate_india_bounds(19.076, 72.877) is True
    assert validate_india_bounds(28.613, 77.209) is True
    assert validate_india_bounds(13.083, 80.270) is True
    assert validate_india_bounds(8.524,  76.936) is True


def test_out_of_bounds_locations():
    assert validate_india_bounds(51.5,  0.1)   is False
    assert validate_india_bounds(-33.9, 18.4)  is False
    assert validate_india_bounds(35.7,  139.7) is False
    assert validate_india_bounds(0.0,   0.0)   is False


def test_boundary_edges():
    assert validate_india_bounds(6.0,  68.0) is True
    assert validate_india_bounds(38.0, 98.0) is True
    assert validate_india_bounds(5.9,  78.0) is False
    assert validate_india_bounds(20.0, 67.9) is False
