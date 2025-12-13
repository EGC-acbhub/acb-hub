import hashlib
import json
import os

from app import db
from app.modules.fakenodo.models import FakeDeposition, FakeFile
from app.modules.fakenodo.repositories import FakenodoRepository
from core.configuration.configuration import uploads_folder_name
from core.services.BaseService import BaseService


class FakenodoService(BaseService):
    def __init__(self):
        super().__init__(FakenodoRepository())

    def create_new_deposition(self, dataset):
        """Create a new deposition with metadata (matches ZenodoService interface)."""

        metadata = {
            "title": dataset.ds_meta_data.title,
            "upload_type": "dataset",
            "description": dataset.ds_meta_data.description,
            "creators": [
                {
                    "name": f"{dataset.user.profile.surname}, {dataset.user.profile.name}",
                    "affiliation": dataset.user.profile.affiliation or "ACB Hub User",
                }
            ],
            "keywords": (
                ["acbhub"] if not dataset.ds_meta_data.tags else dataset.ds_meta_data.tags.split(", ") + ["acbhub"]
            ),
            "access_right": "open",
            "license": "CC-BY-4.0",
        }

        deposition = FakeDeposition()
        deposition.title = metadata.get("title", "")
        deposition.description = metadata.get("description", "")
        deposition.upload_type = metadata.get("upload_type", "dataset")
        deposition.creators = json.dumps(metadata.get("creators", []))
        deposition.keywords = json.dumps(metadata.get("keywords", []))
        deposition.access_right = metadata.get("access_right", "open")
        deposition.license = metadata.get("license", "CC-BY-4.0")
        deposition.state = "unsubmitted"

        # Generate conceptrecid (same as id for simplicity)
        db.session.add(deposition)
        db.session.flush()  # Get the ID
        deposition.conceptrecid = deposition.id
        db.session.commit()

        # Return Zenodo-compatible response
        return deposition.to_dict()

    def upload_file(self, dataset, deposition_id, basket_model, user=None):
        """Upload a file to a deposition (matches ZenodoService interface)."""

        deposition = FakeDeposition.query.get_or_404(deposition_id)

        if deposition.state == "done":
            raise Exception("Cannot upload files to a published deposition")

        # Get file data
        csv_filename = basket_model.bm_meta_data.csv_filename
        user_id = user.id if user else dataset.user_id
        file_path = os.path.join(uploads_folder_name(), f"user_{str(user_id)}", f"dataset_{dataset.id}/", csv_filename)

        with open(file_path, "rb") as f:
            file_data = f.read()

        # Calculate checksum
        checksum = hashlib.md5(file_data).hexdigest()

        # Save file to fakenodo directory
        fakenodo_dir = os.path.join(uploads_folder_name(), "fakenodo")
        os.makedirs(fakenodo_dir, exist_ok=True)

        fake_file_path = os.path.join(fakenodo_dir, f"deposition_{deposition_id}_{csv_filename}")
        with open(fake_file_path, "wb") as f:
            f.write(file_data)

        # Create file record
        fake_file = FakeFile()
        fake_file.deposition_id = deposition_id
        fake_file.filename = csv_filename
        fake_file.filesize = len(file_data)
        fake_file.checksum = f"md5:{checksum}"

        db.session.add(fake_file)
        db.session.commit()

        # Update deposition state
        deposition.state = "submitted"
        db.session.commit()

        # Return Zenodo-compatible response
        return {
            "id": fake_file.id,
            "filename": fake_file.filename,
            "filesize": fake_file.filesize,
            "checksum": fake_file.checksum,
        }

    def publish_deposition(self, deposition_id):
        """Publish a deposition and generate DOI (matches ZenodoService interface)."""
        deposition = FakeDeposition.query.get_or_404(deposition_id)

        if deposition.state == "done":
            raise Exception("Deposition is already published")

        # Generate DOI
        deposition.doi = f"10.5281/fakenodo.{deposition_id}"
        deposition.state = "done"
        db.session.commit()

        # Return Zenodo-compatible response
        response = deposition.to_dict()
        response["files"] = [file.to_dict() for file in deposition.files]
        return response

    def get_deposition(self, deposition_id):
        """Get deposition details."""
        deposition = FakeDeposition.query.get_or_404(deposition_id)

        # Get files
        files = FakeFile.query.filter_by(deposition_id=deposition_id).all()
        deposition_dict = deposition.to_dict()
        deposition_dict["files"] = [file.to_dict() for file in files]

        return deposition_dict

    def list_depositions(self):
        """List all depositions."""
        depositions = FakeDeposition.query.all()
        result = []

        for deposition in depositions:
            files = FakeFile.query.filter_by(deposition_id=deposition.id).all()
            deposition_dict = deposition.to_dict()
            deposition_dict["files"] = [file.to_dict() for file in files]
            result.append(deposition_dict)

        return result

    def test_connection(self):
        """Test connection (always returns success for fakenodo)."""
        return True

    def get_doi(self, deposition_id):
        """Get the DOI of a deposition."""
        deposition = FakeDeposition.query.get_or_404(deposition_id)
        return deposition.doi

    def get_all_depositions(self):
        """Get all depositions (for compatibility)."""
        return self.list_depositions()
