from flask import render_template

from app.modules.zenodo import zenodo_bp
from app.modules.zenodo.services import get_zenodo_service, get_zenodo_service_type


@zenodo_bp.route("/zenodo", methods=["GET"])
def index():
    return render_template("zenodo/index.html")


@zenodo_bp.route("/zenodo/test", methods=["GET"])
def zenodo_test():
    service = get_zenodo_service()
    service_type = get_zenodo_service_type()

    if service_type == "fakenodo":
        # Fakenodo always succeeds
        return {"success": True, "messages": ["Fakenodo connection test passed"]}
    else:
        # Real Zenodo test
        return service.test_full_connection()
