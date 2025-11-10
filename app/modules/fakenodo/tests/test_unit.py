import pytest
from unittest.mock import patch, MagicMock

from app import db
from app.modules.fakenodo.services import FakenodoService
from app.modules.fakenodo.models import Deposition
from app.modules.dataset.models import DSMetaData, DataSet
from app.modules.featuremodel.models import FeatureModel


@pytest.fixture(scope="module")
def test_client(test_client):
    with test_client.application.app_context():
        # Add a sample deposition to the database for testing
        sample_deposition = Deposition(
            meta_data={"title": "Sample Dataset", "description": "Sample Description"},
            status="draft",
            doi=None
        )
        db.session.add(sample_deposition)
        db.session.commit()
    yield test_client


def test_create_new_deposition():
    service = FakenodoService()
    ds_meta_data = DSMetaData(
        title="Test Dataset",
        publication_type=MagicMock(value="none"),
        description="Test Description",
        authors=[],
        tags=""
    )
    dataset = DataSet(ds_meta_data=ds_meta_data)
    with patch('app.modules.fakenodo.repositories.DepositionRepo.create_new_deposition') as mock_create_new_deposition:
        mock_create_new_deposition.return_value = MagicMock(id=1)
        response = service.create_new_deposition(dataset)
        assert response['id'] == 1
        assert response['message'] == "Deposition succesfully created in Fakenodo"


def test_create_new_deposition_with_authors():
    service = FakenodoService()
    ds_meta_data = DSMetaData(
        title="Test Dataset",
        publication_type=MagicMock(value="none"),
        description="Test Description",
        authors=[MagicMock(name="Author1", affiliation="Affiliation1", orcid="0000-0000-0000-0000")],
        tags=""
    )
    dataset = DataSet(ds_meta_data=ds_meta_data)
    with patch('app.modules.fakenodo.repositories.DepositionRepo.create_new_deposition') as mock_create_new_deposition:
        mock_create_new_deposition.return_value = MagicMock(id=1)
        response = service.create_new_deposition(dataset)
        assert response['id'] == 1
        assert response['message'] == "Deposition succesfully created in Fakenodo"


def test_upload_file():
    service = FakenodoService()
    dataset = DataSet(id=1)
    feature_model = FeatureModel(fm_meta_data=MagicMock(uvl_filename="test.uvl"))
    with patch('os.path.getsize') as mock_getsize, \
         patch('app.modules.fakenodo.services.checksum') as mock_checksum, \
         patch('flask_login.current_user') as mock_current_user:
        mock_current_user.id = 1
        mock_checksum.return_value = 'dummychecksum'
        mock_getsize.return_value = 1234
        response = service.upload_file(dataset, 1, feature_model, user=mock_current_user)
        assert response['id'] == 1
        assert response['file'] == "test.uvl"
        assert response['fileSize'] == 1234
        assert response['checksum'] == 'dummychecksum'


def test_publish_deposition(test_client):
    service = FakenodoService()
    with patch('app.modules.fakenodo.models.Deposition.query.get') as mock_query_get, \
         patch('app.modules.fakenodo.repositories.DepositionRepo.update'):
        mock_deposition = MagicMock(id=1, status="draft")
        mock_query_get.return_value = mock_deposition
        response = service.publish_deposition(1)
        assert response['id'] == 1
        assert response['status'] == "published"
        assert response['message'] == "Deposition published successfully in fakenodo."


def test_get_deposition(test_client):
    service = FakenodoService()
    with patch('app.modules.fakenodo.models.Deposition.query.get') as mock_query_get:
        mock_deposition = MagicMock(id=1, doi="fakenodo.doi.1", meta_data={}, status="draft")
        mock_query_get.return_value = mock_deposition
        response = service.get_deposition(1)
        assert response['id'] == 1
        assert response['doi'] == "fakenodo.doi.1"
        assert response['message'] == "Deposition succesfully get from Fakenodo."


def test_get_doi(test_client):
    service = FakenodoService()
    with patch('app.modules.fakenodo.models.Deposition.query.get') as mock_query_get:
        mock_deposition = MagicMock(id=1, doi="fakenodo.doi.1")
        mock_query_get.return_value = mock_deposition
        doi = service.get_doi(1)
        assert doi == "fakenodo.doi.1"
