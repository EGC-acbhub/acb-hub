import pytest

from app.modules.auth.seeders import AuthSeeder
from app.modules.conftest import login, logout
from app.modules.dataset.seeders import DataSetSeeder


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
    assert (
        b"https://img.shields.io/badge/Sample%20dataset%202-0%20downloads-blue" in response.data
    ), "The expected content is not present on the page"

    logout(test_client)
