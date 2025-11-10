# tests/test_fakenodo_versioning_service.py
import io
from unittest.mock import MagicMock, patch
from app.modules.fakenodo.services import FakenodoService

def test_metadata_only_keeps_same_doi(test_client, monkeypatch):
    svc = FakenodoService()
    dep = MagicMock(id=1, doi="fakenodo.doi.v1", status="published")

    with test_client.application.app_context():
        with patch('app.modules.fakenodo.models.Deposition.query') as mock_query, \
             patch('app.modules.fakenodo.repositories.DepositionRepo.update') as repo_update:
            mock_query.get.return_value = dep
            # simula edición solo de metadatos
            resp1 = svc.publish_deposition(1)
            resp2 = svc.publish_deposition(1)

    assert resp1['status'] == 'published'
    assert resp2['status'] == 'published'
    assert resp2['message'].lower().startswith("deposition published")
    # mismo DOI en ambas publicaciones si solo cambian metadatos
    assert resp2.get('doi', dep.doi) == dep.doi

def test_files_change_creates_new_version(test_client, monkeypatch):
    svc = FakenodoService()
    dep = MagicMock(id=2, doi="fakenodo.doi.v1", status="published")

    with test_client.application.app_context():
        with patch('app.modules.fakenodo.models.Deposition.query') as mock_query, \
             patch('app.modules.fakenodo.repositories.DepositionRepo.update') as repo_update, \
             patch('flask_login.current_user') as current_user, \
             patch('os.path.getsize', return_value=3), \
             patch('app.modules.fakenodo.services.checksum', return_value='abc'):

            mock_query.get.return_value = dep
            current_user.id = 7

            # sube fichero
            svc.upload_file(MagicMock(id=99),
                            deposition_id=2,
                            feature_model=MagicMock(fm_meta_data=MagicMock(uvl_filename="a.txt")),
                            user=current_user)

            # al publicar, simula que el repo guarda nuevo DOI
            def _repo_update_side_effect(*args, **kwargs):
                dep.doi = "fakenodo.doi.v2"
            repo_update.side_effect = _repo_update_side_effect

            resp = svc.publish_deposition(2)

    assert resp['status'] == 'published'
    # consulta el DOI actualizado
    with patch('app.modules.fakenodo.models.Deposition.query') as q2:
        q2.get.return_value = dep
        new_doi = svc.get_doi(2)
    assert new_doi == "fakenodo.doi.v2"