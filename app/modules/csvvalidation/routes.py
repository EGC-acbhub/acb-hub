import csv
import logging

from flask import jsonify

from app.modules.csvvalidation import csv_validation_bp
from app.modules.hubfile.services import HubfileService

logger = logging.getLogger(__name__)

# Columnas requeridas según tu archivo de ejemplo players_acb_2016_2020.csv
REQUIRED_COLUMNS = {
    "league",
    "game_date",
    "local_team",
    "local_team_points",
    "visit_team",
    "visit_team_points",
    "player_team",
    "player_name",
    "player_total_points",
    "time",
    "one_point_shots_get",
    "one_point_shots_made",
    "two_point_shots_get",
    "two_point_shots_made",
    "three_point_shots_get",
    "three_point_shots_made",
    "rebouts",
    "assists",
    "fouls",
    "received_fouls",
}


@csv_validation_bp.route("/csv_validation/check_csv/<int:file_id>", methods=["GET"])
def check_csv(file_id):
    try:
        hubfile = HubfileService().get_by_id(file_id)
        file_path = hubfile.get_path()

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            # 1. Leemos una muestra
            sample = csvfile.read(1024)
            
            # 2. Intentamos detectar el formato (punto y coma, comas, etc.)
            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                # SI FALLA (porque es una sola columna o muy pequeño), 
                # forzamos el estándar de Excel (separado por comas)
                dialect = csv.excel
            
            # 3. Volvemos al inicio del archivo
            csvfile.seek(0)

            reader = csv.DictReader(csvfile, dialect=dialect)

            # Normalizamos cabeceras a minúsculas y eliminamos espacios extra
            headers = set(h.lower().strip() for h in reader.fieldnames) if reader.fieldnames else set()
            required_lower = set(h.lower() for h in REQUIRED_COLUMNS)

            missing_columns = required_lower - headers

            if missing_columns:
                return jsonify(
                    {"success": False, "errors": [f"Faltan columnas obligatorias: {', '.join(missing_columns)}"]}
                ), 400

            # Validación extra: Leer la primera fila para ver si hay datos
            try:
                next(reader)
            except StopIteration:
                return jsonify({"success": False, "errors": ["El archivo CSV está vacío"]}), 400

        return jsonify({"success": True, "message": "Valid Basketball CSV"}), 200

    except Exception as e:
        logger.exception(f"Error validating CSV: {str(e)}")
        return jsonify({"success": False, "errors": [f"Error interno: {str(e)}"]}), 500