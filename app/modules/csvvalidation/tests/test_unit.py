import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing with valid headers."""
    required_columns = [
        "league",
        "game_date",
        "local_team",
        "local_team_points",
        "visit_team",
        "visit_team_points",
        "player_team",
        "player_name",
        "player_total_points",
        "time",
        "one_point_shots_get",
        "one_point_shots_made",
        "two_point_shots_get",
        "two_point_shots_made",
        "three_point_shots_get",
        "three_point_shots_made",
        "rebouts",
        "assists",
        "fouls",
        "received_fouls",
    ]
    headers = ",".join(required_columns)
    data = ",".join(
        [
            "ACB",
            "2023-01-01",
            "TeamA",
            "80",
            "TeamB",
            "75",
            "TeamA",
            "Player1",
            "20",
            "10:00",
            "1",
            "1",
            "5",
            "3",
            "2",
            "1",
            "5",
            "2",
            "1",
            "0",
        ]
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(headers + "\n" + data + "\n")
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def mock_hubfile(temp_csv_file):
    """Mock hubfile object."""
    hubfile = MagicMock()
    hubfile.get_path.return_value = temp_csv_file
    hubfile.id = 1
    return hubfile


# ===== EXISTING SAMPLE TEST =====


def test_sample_assertion(test_client):
    """
    Sample test to verify that the test framework and environment are working correctly.
    It does not communicate with the Flask application; it only performs a simple assertion to
    confirm that the tests in this module can be executed.
    """
    greeting = "Hello, World!"
    assert greeting == "Hello, World!", "The greeting does not coincide with 'Hello, World!'"


# ===== ROUTE TESTS =====


def test_check_csv_valid(temp_csv_file, mock_hubfile, test_client):
    """Test check_csv with valid CSV."""
    with patch("app.modules.csvvalidation.routes.HubfileService") as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.get_by_id.return_value = mock_hubfile

        response = test_client.get("/csv_validation/check_csv/1")

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert data["success"] is True


def test_check_csv_missing_columns(temp_csv_file, mock_hubfile, test_client):
    """Test check_csv with missing columns."""
    # Create invalid CSV
    with open(temp_csv_file, "w") as f:
        f.write("league,game_date\nACB,2023-01-01\n")  # Missing local_team, etc.

    with patch("app.modules.csvvalidation.routes.HubfileService") as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.get_by_id.return_value = mock_hubfile

        response = test_client.get("/csv_validation/check_csv/1")

        assert response.status_code == 400
        data = json.loads(response.data.decode("utf-8"))
        assert data["success"] is False
        assert "Faltan columnas obligatorias" in str(data["errors"])


def test_check_csv_empty_file(mock_hubfile, test_client):
    """Test check_csv with empty file."""
    # Create empty CSV
    with open(mock_hubfile.get_path(), "w") as f:
        f.write("")

    with patch("app.modules.csvvalidation.routes.HubfileService") as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.get_by_id.return_value = mock_hubfile

        response = test_client.get("/csv_validation/check_csv/1")

        assert response.status_code == 400
        data = json.loads(response.data.decode("utf-8"))
        assert data["success"] is False
        assert "Faltan columnas" in str(data["errors"])  # Empty file has no headers


@patch("app.modules.csvvalidation.routes.csv.Sniffer")
def test_check_csv_encoding_issue(mock_sniffer, temp_csv_file, mock_hubfile, test_client):
    """Test check_csv with encoding issues."""
    mock_sniffer.return_value.sniff.return_value = MagicMock(delimiter=",")

    with patch("builtins.open", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "reason")):
        with patch("app.modules.csvvalidation.routes.HubfileService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_by_id.return_value = mock_hubfile

            response = test_client.get("/csv_validation/check_csv/1")

            assert response.status_code == 500
            data = json.loads(response.data.decode("utf-8"))
            assert data["success"] is False
            assert "Error interno" in str(data["errors"])


def test_check_csv_malformed_rows(temp_csv_file, mock_hubfile, test_client):
    """Test check_csv with malformed rows."""
    # Create CSV with wrong row count
    with open(temp_csv_file, "w") as f:
        f.write("league,game_date\nACB\n")  # Incomplete row

    with patch("app.modules.csvvalidation.routes.HubfileService") as mock_service_class:
        mock_service = mock_service_class.return_value
        mock_service.get_by_id.return_value = mock_hubfile

        response = test_client.get("/csv_validation/check_csv/1")

        assert response.status_code == 400  # Missing columns
        data = json.loads(response.data.decode("utf-8"))
        assert data["success"] is False
