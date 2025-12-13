from flask import jsonify, request
from werkzeug.exceptions import BadRequest, NotFound

from app.modules.fakenodo import fakenodo_bp
from app.modules.fakenodo.services import FakenodoService

fakenodo_service = FakenodoService()


@fakenodo_bp.route('/fakenodo', methods=['GET'])
def index():
    return jsonify({"message": "Fakenodo API is running", "status": "ok"})


@fakenodo_bp.route('/api/deposit/depositions', methods=['POST'])
def create_deposition():
    """Create a new deposition."""
    try:
        data = request.get_json()
        if not data or 'metadata' not in data:
            raise BadRequest("Missing metadata")

        metadata = data['metadata']
        deposition = fakenodo_service.create_deposition(metadata)

        response = deposition.to_dict()
        response['files'] = []  # New depositions have no files yet

        return jsonify(response), 201

    except Exception as e:
        return jsonify({"message": str(e), "status": "error"}), 400


@fakenodo_bp.route('/api/deposit/depositions/<int:deposition_id>/files', methods=['POST'])
def upload_file(deposition_id):
    """Upload a file to a deposition."""
    try:
        if 'file' not in request.files:
            raise BadRequest("No file provided")

        file = request.files['file']
        if not file.filename:
            raise BadRequest("No filename provided")

        # Read file data
        file_data = file.read()

        # Upload file
        fake_file = fakenodo_service.upload_file(deposition_id, file.filename, file_data)

        response = {
            "id": fake_file.id,
            "filename": fake_file.filename,
            "filesize": fake_file.filesize,
            "checksum": fake_file.checksum,
            "created": fake_file.created.isoformat() if fake_file.created else None,
        }

        return jsonify(response), 201

    except NotFound:
        return jsonify({"message": "Deposition not found", "status": "error"}), 404
    except Exception as e:
        return jsonify({"message": str(e), "status": "error"}), 400


@fakenodo_bp.route('/api/deposit/depositions/<int:deposition_id>/actions/publish', methods=['POST'])
def publish_deposition(deposition_id):
    """Publish a deposition."""
    try:
        deposition = fakenodo_service.publish_deposition(deposition_id)

        response = deposition.to_dict()
        # Populate files for the response
        files = fakenodo_service.get_deposition(deposition_id)['files']
        response['files'] = files

        return jsonify(response), 202

    except NotFound:
        return jsonify({"message": "Deposition not found", "status": "error"}), 404
    except Exception as e:
        return jsonify({"message": str(e), "status": "error"}), 400


@fakenodo_bp.route('/api/deposit/depositions/<int:deposition_id>', methods=['GET'])
def get_deposition(deposition_id):
    """Get deposition details."""
    try:
        deposition_data = fakenodo_service.get_deposition(deposition_id)
        return jsonify(deposition_data), 200

    except NotFound:
        return jsonify({"message": "Deposition not found", "status": "error"}), 404
    except Exception as e:
        return jsonify({"message": str(e), "status": "error"}), 500


@fakenodo_bp.route('/api/deposit/depositions', methods=['GET'])
def list_depositions():
    """List all depositions."""
    try:
        depositions = fakenodo_service.list_depositions()
        return jsonify(depositions), 200

    except Exception as e:
        return jsonify({"message": str(e), "status": "error"}), 500
