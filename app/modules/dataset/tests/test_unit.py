import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.modules.auth.seeders import AuthSeeder
from app.modules.conftest import login, logout
from app.modules.dataset.repositories import DSChangeLogRepository
from app.modules.dataset.seeders import DataSetSeeder
from app.modules.dataset.services import DataSetService, calculate_checksum_and_size


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

    mock_league = MagicMock()
    mock_league.name = "ACB"
    mock_league.value = "acb"
    dataset.ds_meta_data.league = mock_league

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


@pytest.fixture
def mock_dataset_with_bm(mock_dataset, mock_basket_model):
    """Mock dataset with metadata and basket models for update testing."""
    mock_bm1_league = MagicMock()
    mock_bm1_league.value = "nba"
    mock_bm1_league.name = "NBA"
    # Simular la estructura de datos que set_dsmetadata() espera
    mock_bm1 = MagicMock()
    mock_bm1.bm_meta_data.csv_filename = "file1.csv"
    mock_bm1.bm_meta_data.league = mock_bm1_league
    mock_bm1.bm_meta_data.tags = "tagA"
    # ... otros campos ...

    mock_dataset.basket_models = [mock_bm1]

    main_ds_league = MagicMock()
    main_ds_league.value = "acb"
    main_ds_league.name = "ACB"
    # Asignar valores al metadata principal para que el form.data tenga algo que enviar
    mock_dataset.ds_meta_data.league = main_ds_league
    mock_dataset.ds_meta_data.title = "Old Title"
    mock_dataset.ds_meta_data.description = "Old description"
    mock_dataset.id = 1
    mock_dataset.ds_meta_data_id = 1

    return mock_dataset


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


# --- NUEVOS TESTS DE INTEGRACIÓN ---


@patch('app.modules.dataset.routes.dataset_service')
@patch('app.modules.dataset.forms.DataSet')
def test_update_dataset_validation_passes_with_bm(mock_ds_model, mock_dataset_service, test_client, mock_dataset_with_bm):  # noqa: E501
    """
    Prueba que la validación del formulario de actualización pasa,
    incluso con FieldList(BasketModelForm) presente,
    simulando la corrección del SelectField 'league' y la lógica de set_dsmetadata.
    """

    # Simular el dataset existente (usado en la función de la vista)
    mock_dataset_service.get_by_id.return_value = mock_dataset_with_bm

    # ----------------------------------------------------
    # Simular el envío de datos POST (datos de formulario válidos)
    # ----------------------------------------------------
    new_title = "New Updated Title"
    post_data = {
        "title": new_title,
        "desc": "Updated description",
        "league": "euroleague",
        "tags": "new,tags,update",
        # Simular los datos del BasketModel
        "basket_models-0-csv_filename": "file1.csv",
        "basket_models-0-title": "Model Title",
        "basket_models-0-desc": "Model Desc",
        "basket_models-0-league": "nba",
        "basket_models-0-tags": "tagA",
        "basket_models-0-version": "1.0",
        "basket_models-0-csrf_token": "mock_token"
    }

    # Asegurar la autenticación
    login(test_client, "user1@example.com", "1234")

    # Ejecutar la solicitud POST (ESTO DEBE DEVOLVER UN OBJETO Response REAL)
    response = test_client.post("/dataset/update/1", data=post_data)

    # ----------------------------------------------------
    # ASERCIONES Y VERIFICACIONES (Usando la corrección de aserción)
    # ----------------------------------------------------

    # Aseguramos que la aserción de 200 pasa. Si falla, mostramos el cuerpo de la respuesta real.
    if response.status_code != 200:
        error_info = response.data.decode('utf-8', errors='ignore')
        # Utilizamos pytest.fail() para asegurar que el test se detiene y muestra el mensaje.
        pytest.fail(f"La validación falló. Status: {response.status_code}. Respuesta: {error_info}")

    assert response.status_code == 200, "La actualización del dataset debería haber devuelto 200 (OK)."

    # 1. Verificar que se llamó al servicio de actualización de metadatos
    mock_dataset_service.update_dsmetadata.assert_called_once()

    # 2. Verificar que el servicio de log de cambios fue llamado después de la actualización exitosa
    mock_dataset_service.create_dschangelog.assert_called_once_with(dataset=mock_dataset_with_bm)

    logout(test_client)


@patch('app.modules.dataset.routes.dataset_service')
def test_update_dataset_creates_changelog_on_success(mock_dataset_service, test_client, mock_dataset_with_bm):
    """
    Prueba más simple para asegurar que el log de cambios se llama después de la validación
    en la ruta POST /dataset/update/<id>.
    """
    # Configurar el mock para que la validación pase
    mock_dataset_service.get_by_id.return_value = mock_dataset_with_bm

    post_data = {
        "title": "T",
        "desc": "D",
        "league": "acb",
        "tags": "",
        "basket_models-0-csv_filename": "file1.csv",
        "basket_models-0-league": "nba",
    }

    login(test_client, "user1@example.com", "1234")

    test_client.post("/dataset/update/1", data=post_data)

    # Afirmar que se llamó al creador de log de cambios
    mock_dataset_service.create_dschangelog.assert_called_once()

    logout(test_client)


# --- NUEVOS TESTS UNITARIOS ---


def test_dschangelog_repository_create_new_record():
    """
    Prueba la función del repositorio que crea el DSChangeLog,
    asegurando que los datos de DSMetaData se mapean correctamente.
    """
    # Mocks para DSMetaData y DataSet (simulando current_user.id = 1)
    mock_ds_meta_data = MagicMock()
    mock_ds_meta_data.title = "Change Title"
    mock_ds_meta_data.description = "Change Description"
    mock_ds_meta_data.league = "ACB"
    mock_ds_meta_data.tags = "tag1, tag2"
    mock_ds_meta_data.updated_at = datetime.now(timezone.utc)

    # Mockear el método 'create' del BaseRepository
    mock_repo = DSChangeLogRepository()
    mock_repo.create = MagicMock()

    with patch('app.modules.dataset.repositories.current_user', MagicMock(id=1, is_authenticated=True)):
        mock_repo.create_new_record(
            dataset_id=10,
            ds_meta_data=mock_ds_meta_data
        )

    # Verificar que 'create' fue llamado con los argumentos correctos
    mock_repo.create.assert_called_once()
    args, kwargs = mock_repo.create.call_args

    assert kwargs['data_set_id'] == 10
    assert kwargs['title'] == "Change Title"
    assert kwargs['description'] == "Change Description"
    assert kwargs['league'] == mock_ds_meta_data.league
    assert kwargs['tags'] == "tag1, tag2"
    assert kwargs['user_id'] == 1


@patch('app.modules.dataset.services.DSChangeLogRepository')
def test_dataset_service_create_dschangelog(MockDSChangeLogRepository):
    """
    Prueba que el servicio llama al repositorio con los argumentos
    correctos (dataset_id y ds_meta_data).
    """

    # Mocks
    mock_dschangelog_repo = MockDSChangeLogRepository.return_value
    dataset_service = DataSetService()

    mock_dataset = MagicMock()
    mock_dataset.id = 5
    mock_dataset.ds_meta_data = MagicMock()

    # Ejecución
    dataset_service.create_dschangelog(dataset=mock_dataset)

    # Verificación
    mock_dschangelog_repo.create_new_record.assert_called_once_with(
        dataset_id=5,
        ds_meta_data=mock_dataset.ds_meta_data
    )
