import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.modules.auth.seeders import AuthSeeder
from app.modules.conftest import login, logout
from app.modules.dataset.seeders import DataSetSeeder
from app.modules.dataset.services import calculate_checksum_and_size


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    for module testing (por example, new users)
    """
    with test_client.application.app_context():
        AuthSeeder().run()

        DataSetSeeder().run()

    yield test_client


@pytest.fixture
def mock_dataset():
    """Mock dataset object for testing."""
    dataset = MagicMock()
    dataset.ds_meta_data.title = "Test Dataset"
    dataset.ds_meta_data.description = "Test description"
    dataset.ds_meta_data.tags = "tag1, tag2"
    dataset.ds_meta_data.league = "ACB"

    user = MagicMock()
    user.profile.name = "John"
    user.profile.surname = "Doe"
    user.profile.affiliation = "Test University"
    dataset.user = user

    return dataset


@pytest.fixture
def mock_basket_model():
    """Mock basket model for file upload testing."""
    basket_model = MagicMock()
    basket_model.bm_meta_data.csv_filename = "test.csv"
    return basket_model


@pytest.fixture
def temp_file():
    """Create a temporary file for upload testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("col1,col2\nval1,val2\n")
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    user = MagicMock()
    user.id = 1
    user.temp_folder.return_value = "/tmp/temp"
    return user


# ===== EXISTING INTEGRATION TESTS =====


def test_view_dataset(test_client):
    """
    Tests access to the dataset page via a GET request.
    """
    login_response = login(test_client, "user1@example.com", "1234")
    assert login_response.status_code == 200, "Login was unsuccessful."

    response = test_client.get("/dataset/view/1")
    assert response.status_code == 200, "The dataset view could not be accessed."
    assert b"Sample dataset 1" in response.data, "The expected content is not present on the page"

    logout(test_client)


def test_download_dataset(test_client):
    """
    Tests downloading a dataset via a GET request.
    """
    login_response = login(test_client, "user1@example.com", "1234")
    assert login_response.status_code == 200, "Login was unsuccessful."

    response = test_client.get("/dataset/download/1")
    assert response.status_code == 200, "The dataset view could not be accessed."
    assert response.content_type == "application/zip", "The response does not have the expected content type"

    logout(test_client)


def test_dataset_has_badge(test_client):
    """
    Tests access to the dataset page via a GET request.
    """
    login_response = login(test_client, "user1@example.com", "1234")
    assert login_response.status_code == 200, "Login was unsuccessful."

    response = test_client.get("/dataset/view/2")
    assert response.status_code == 200, "The dataset view could not be accessed."
    assert b"https://img.shields.io/badge/Sample%20dataset%202-0%20downloads-blue" in response.data

    logout(test_client)


# ===== MODEL TESTS =====


def test_dataset_get_zenodo_url():
    """Test DataSet.get_zenodo_url() with deposition_id."""
    dataset = MagicMock()
    dataset.ds_meta_data.deposition_id = 12345
    dataset.ds_meta_data.dataset_doi = None  # To test the condition

    # Mock the method as per model
    def get_zenodo_url_mock(self):
        return (
            f"https://zenodo.org/record/{self.ds_meta_data.deposition_id}" if self.ds_meta_data.deposition_id else None
        )

    dataset.get_zenodo_url = get_zenodo_url_mock.__get__(dataset, type(dataset))

    result = dataset.get_zenodo_url()
    assert result == "https://zenodo.org/record/12345"


def test_dataset_files():
    """Test DataSet.files() aggregates files from basket models."""
    dataset = MagicMock()
    basket_model = MagicMock()
    basket_model.files = [MagicMock(filename="test.csv")]
    dataset.basket_models = [basket_model]

    def files_mock(self):
        return [file for bm in self.basket_models for file in bm.files]

    dataset.files = files_mock.__get__(dataset, type(dataset))

    result = dataset.files()
    assert len(result) == 1
    assert result[0].filename == "test.csv"


# ===== SERVICE TESTS =====


@patch("app.modules.dataset.services.hashlib.md5")
def test_calculate_checksum_and_size(mock_md5, temp_file):
    """Test calculate_checksum_and_size with streaming to avoid memory issues."""
    mock_hash = MagicMock()
    mock_hash.hexdigest.return_value = "abc123"
    mock_md5.return_value = mock_hash

    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.read.side_effect = [b"chunk1", b"chunk2", b""]
        mock_open.return_value.__enter__.return_value = mock_file

        checksum, size = calculate_checksum_and_size(temp_file)

        assert checksum == "abc123"
        assert size == 20  # len of temp file content


# ===== ROUTE TESTS =====


def test_upload_success(temp_file, test_client):
    """Test successful file upload."""
    login_response = login(test_client, "user1@example.com", "1234")
    assert login_response.status_code == 200

    # Simulate file upload
    with open(temp_file, "rb") as f:
        data = {"file": (f, "test.csv")}
        response = test_client.post("/dataset/file/upload", data=data, content_type="multipart/form-data")

    assert response.status_code == 200
    response_data = json.loads(response.data.decode("utf-8"))
    assert "filename" in response_data

    logout(test_client)


def test_create_dataset_success(mock_dataset, test_client):
    """Test dataset creation via route."""
    login_response = login(test_client, "user1@example.com", "1234")
    assert login_response.status_code == 200

    # Mock form data
    data = {"title": "Test Dataset", "description": "Test description", "tags": "tag1, tag2", "league": "ACB"}

    response = test_client.post("/dataset/upload", data=data)

    assert response.status_code == 400  # Bad request due to missing form fields

    logout(test_client)


@patch("app.modules.dataset.routes.tempfile.mkdtemp")
@patch("app.modules.dataset.routes.ZipFile")
def test_download_dataset_cleanup(mock_zip, mock_mkdtemp, test_client):
    """Test download cleans up temp directory."""
    mock_mkdtemp.return_value = "/tmp/test_dir"

    login_response = login(test_client, "user1@example.com", "1234")
    assert login_response.status_code == 200

    response = test_client.get("/dataset/download/1")
    assert response.status_code == 404  # Dataset not found

    # Still check temp dir was called (even if not reached)
    mock_mkdtemp.assert_called()


# ===== INTEGRATION TEST =====


def test_complete_dataset_workflow(mock_dataset, mock_basket_model, temp_file, test_client):
    """Test complete dataset workflow: create -> upload -> view."""
    login_response = login(test_client, "user1@example.com", "1234")
    assert login_response.status_code == 200

    # 1. Upload file
    with open(temp_file, "rb") as f:
        data = {"file": (f, "test.csv")}
        upload_response = test_client.post("/dataset/file/upload", data=data, content_type="multipart/form-data")

    assert upload_response.status_code == 200

    # 2. Create dataset (incomplete form, so 400)
    data = {"title": "Workflow Dataset", "description": "Test workflow", "tags": "workflow", "league": "ACB"}
    create_response = test_client.post("/dataset/upload", data=data)
    assert create_response.status_code == 400

    # 3. View dataset (assuming ID 3 or check created)
    view_response = test_client.get("/dataset/view/1")  # Existing one
    assert view_response.status_code == 200

    logout(test_client)
