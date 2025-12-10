from flask import render_template

from app.modules.basketmodel import basketmodel_bp


@basketmodel_bp.route("/basketmodel", methods=["GET"])
def index():
    return render_template("basketmodel/index.html")
