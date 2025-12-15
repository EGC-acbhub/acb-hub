import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.modules.fakenodo.models import FakeDeposition, FakeFile
from app.modules.fakenodo.services import FakenodoService


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
def mock_dataset():
    """Mock dataset object for testing."""
    dataset = MagicMock()
    dataset.ds_meta_data.title = "Test Dataset"
    dataset.ds_meta_data.description = "Test description"
    dataset.ds_meta_data.tags = "tag1, tag2"

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


# ===== MODEL TESTS =====


def test_fake_deposition_to_dict():
    """Test FakeDeposition.to_dict() returns correct structure."""
    deposition = FakeDeposition(
        id=1,
        conceptrecid=1,
        title="Test Title",
        description="Test Description",
        upload_type="dataset",
        creators='[{"name": "John Doe"}]',
        keywords='["tag1", "tag2"]',
        access_right="open",
        license="CC-BY-4.0",
        doi="10.5281/fakenodo.1",
        state="done",
    )

    result = deposition.to_dict()

    assert result["id"] == 1
    assert result["conceptrecid"] == 1
    assert result["doi"] == "10.5281/fakenodo.1"
    assert result["metadata"]["title"] == "Test Title"
    assert result["metadata"]["description"] == "Test Description"
    assert result["state"] == "done"
    assert result["files"] == []  # Empty by default


def test_fake_file_to_dict():
    """Test FakeFile.to_dict() returns correct structure."""
    fake_file = FakeFile(id=1, deposition_id=1, filename="test.csv", filesize=1024, checksum="md5:abc123")

    result = fake_file.to_dict()

    assert result["id"] == 1
    assert result["filename"] == "test.csv"
    assert result["filesize"] == 1024
    assert result["checksum"] == "md5:abc123"


def test_fake_deposition_defaults(test_client):
    """Test FakeDeposition default values."""
    with test_client.application.app_context():
        deposition = FakeDeposition(title="Test", description="Test desc")
        db.session.add(deposition)
        db.session.flush()  # This sets the defaults

        assert deposition.state == "unsubmitted"
        assert deposition.upload_type == "dataset"
        assert deposition.access_right == "open"
        assert deposition.license == "CC-BY-4.0"


def test_models_repr():
    """Test model __repr__ methods."""
    deposition = FakeDeposition(id=1, title="Test", description="Test", state="done")
    fake_file = FakeFile(id=1, filename="test.csv", filesize=100)

    assert repr(deposition) == "FakeDeposition<1, state=done>"
    assert repr(fake_file) == "FakeFile<test.csv, size=100>"


# ===== SERVICE TESTS =====


def test_create_new_deposition(mock_dataset, test_client):
    """Test creating a new deposition."""
    with test_client.application.app_context():
        service = FakenodoService()

        result = service.create_new_deposition(mock_dataset)

        # Check deposition was created in database
        deposition = FakeDeposition.query.filter_by(title="Test Dataset").first()
        assert deposition is not None
        assert deposition.description == "Test description"
        assert deposition.state == "unsubmitted"
        assert deposition.conceptrecid == deposition.id

        # Check returned data structure
        assert result["id"] == deposition.id
        assert result["metadata"]["title"] == "Test Dataset"
        assert result["state"] == "unsubmitted"


@patch("app.modules.fakenodo.services.uploads_folder_name")
@patch("app.modules.fakenodo.services.os.makedirs")
@patch("app.modules.fakenodo.services.open", create=True)
def test_upload_file_success(
    mock_open, mock_makedirs, mock_uploads_folder, mock_dataset, mock_basket_model, temp_file, test_client
):
    """Test successful file upload to deposition."""
    with test_client.application.app_context():
        mock_uploads_folder.return_value = "/tmp/uploads"

        # Create a deposition first
        service = FakenodoService()
        deposition_data = service.create_new_deposition(mock_dataset)
        deposition_id = deposition_data["id"]

        # Mock file operations - need to return bytes for hashlib
        mock_file = MagicMock()
        mock_file.read.return_value = b"col1,col2\nval1,val2\n"
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock user for file path
        mock_user = MagicMock()
        mock_user.id = 1

        result = service.upload_file(mock_dataset, deposition_id, mock_basket_model, mock_user)

        # Check file was created in database
        fake_file = FakeFile.query.filter_by(deposition_id=deposition_id).first()
        assert fake_file is not None
        assert fake_file.filename == "test.csv"

        # Check deposition state was updated
        deposition = FakeDeposition.query.get(deposition_id)
        assert deposition.state == "submitted"

        # Check returned data
        assert result["filename"] == "test.csv"


def test_upload_file_to_published_deposition(mock_dataset, mock_basket_model, test_client):
    """Test that uploading to published deposition raises exception."""
    with test_client.application.app_context():
        service = FakenodoService()

        # Create and publish deposition
        deposition_data = service.create_new_deposition(mock_dataset)
        deposition_id = deposition_data["id"]
        service.publish_deposition(deposition_id)

        # Try to upload file - should raise exception
        with pytest.raises(Exception, match="Cannot upload files to a published deposition"):
            service.upload_file(mock_dataset, deposition_id, mock_basket_model)


def test_publish_deposition(mock_dataset, test_client):
    """Test publishing a deposition."""
    with test_client.application.app_context():
        service = FakenodoService()

        # Create deposition
        deposition_data = service.create_new_deposition(mock_dataset)
        deposition_id = deposition_data["id"]

        # Publish it
        result = service.publish_deposition(deposition_id)

        # Check deposition was updated
        deposition = FakeDeposition.query.get(deposition_id)
        assert deposition.state == "done"
        assert deposition.doi is not None

        # Check returned data includes files
        assert "files" in result
        assert result["state"] == "done"


def test_publish_already_published(mock_dataset, test_client):
    """Test publishing an already published deposition raises exception."""
    with test_client.application.app_context():
        service = FakenodoService()

        # Create and publish deposition
        deposition_data = service.create_new_deposition(mock_dataset)
        deposition_id = deposition_data["id"]
        service.publish_deposition(deposition_id)

        # Try to publish again - should raise exception
        with pytest.raises(Exception, match="Deposition is already published"):
            service.publish_deposition(deposition_id)


def test_get_deposition(mock_dataset, test_client):
    """Test getting deposition details."""
    with test_client.application.app_context():
        service = FakenodoService()

        # Create deposition
        deposition_data = service.create_new_deposition(mock_dataset)
        deposition_id = deposition_data["id"]

        # Get deposition
        result = service.get_deposition(deposition_id)

        assert result["id"] == deposition_id
        assert result["metadata"]["title"] == "Test Dataset"
        assert "files" in result


def test_get_nonexistent_deposition(test_client):
    """Test getting non-existent deposition raises 404."""
    with test_client.application.app_context():
        service = FakenodoService()

        with pytest.raises(Exception):  # Should raise 404
            service.get_deposition(99999)


def test_list_depositions(mock_dataset, test_client):
    """Test listing all depositions."""
    with test_client.application.app_context():
        service = FakenodoService()

        # Create a couple depositions
        service.create_new_deposition(mock_dataset)
        service.create_new_deposition(mock_dataset)

        result = service.list_depositions()

        assert len(result) >= 2
        assert all("metadata" in dep for dep in result)
        assert all("files" in dep for dep in result)


# ===== API ROUTE TESTS =====


def test_index_route(test_client):
    """Test /fakenodo route renders template."""
    response = test_client.get("/fakenodo")
    assert response.status_code == 200
    # Should render template (not JSON)


def test_create_deposition_api(test_client):
    """Test POST /api/deposit/depositions API endpoint."""
    data = {"metadata": {"title": "API Test Dataset", "description": "Test via API", "upload_type": "dataset"}}

    response = test_client.post("/api/deposit/depositions", json=data, content_type="application/json")

    assert response.status_code == 201
    response_data = json.loads(response.data.decode("utf-8"))
    assert "id" in response_data
    assert response_data["metadata"]["title"] == "API Test Dataset"


def test_create_deposition_api_missing_metadata(test_client):
    """Test POST /api/deposit/depositions with missing metadata."""
    response = test_client.post("/api/deposit/depositions", json={}, content_type="application/json")

    assert response.status_code == 400


def test_get_deposition_api(test_client):
    """Test GET /api/deposit/depositions/{id} endpoint."""
    # First create a deposition
    data = {"metadata": {"title": "API Get Test", "description": "Test get endpoint", "upload_type": "dataset"}}

    create_response = test_client.post("/api/deposit/depositions", json=data, content_type="application/json")
    deposition_id = json.loads(create_response.data.decode("utf-8"))["id"]

    # Now get it
    response = test_client.get(f"/api/deposit/depositions/{deposition_id}")
    assert response.status_code == 200

    response_data = json.loads(response.data.decode("utf-8"))
    assert response_data["id"] == deposition_id
    assert response_data["metadata"]["title"] == "API Get Test"


def test_list_depositions_api(test_client):
    """Test GET /api/deposit/depositions endpoint."""
    response = test_client.get("/api/deposit/depositions")
    assert response.status_code == 200

    response_data = json.loads(response.data)
    assert isinstance(response_data, list)


# ===== INTEGRATION TEST =====


def test_complete_deposition_workflow(mock_dataset, mock_basket_model, test_client):
    """Test complete deposition workflow: create -> upload -> publish."""
    with test_client.application.app_context():
        service = FakenodoService()

        # 1. Create deposition
        deposition_data = service.create_new_deposition(mock_dataset)
        deposition_id = deposition_data["id"]

        deposition = FakeDeposition.query.get(deposition_id)
        assert deposition.state == "unsubmitted"

        # 2. Upload file (mocked)
        with (
            patch("app.modules.fakenodo.services.uploads_folder_name", return_value="/tmp"),
            patch("app.modules.fakenodo.services.os.makedirs"),
            patch("app.modules.fakenodo.services.open", create=True) as mock_open,
        ):
            mock_file = MagicMock()
            mock_file.read.return_value = b"col1,col2\nval1,val2\n"
            mock_open.return_value.__enter__.return_value = mock_file

            mock_user = MagicMock()
            mock_user.id = 1

            service.upload_file(mock_dataset, deposition_id, mock_basket_model, mock_user)

            deposition = FakeDeposition.query.get(deposition_id)
            assert deposition.state == "submitted"

            # Check file was created
            fake_file = FakeFile.query.filter_by(deposition_id=deposition_id).first()
            assert fake_file is not None

        # 3. Publish deposition
        result = service.publish_deposition(deposition_id)

        deposition = FakeDeposition.query.get(deposition_id)
        assert deposition.state == "done"
        assert deposition.doi is not None

        # 4. Verify final result includes files
        assert "files" in result
        assert len(result["files"]) == 1
