from sqlalchemy import Enum as SQLAlchemyEnum

from app import db
from app.modules.dataset.models import League


class BasketModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_set_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)
    bm_meta_data_id = db.Column(db.Integer, db.ForeignKey("bm_meta_data.id"))
    files = db.relationship("Hubfile", backref="basket_model", lazy=True, cascade="all, delete")
    bm_meta_data = db.relationship("BMMetaData", uselist=False, backref="basket_model", cascade="all, delete")

    def __repr__(self):
        return f"BasketModel<{self.id}>"


class BMMetaData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    csv_filename = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    league = db.Column(SQLAlchemyEnum(League), nullable=False)
    tags = db.Column(db.String(120))
    csv_version = db.Column(db.String(120))
    bm_metrics_id = db.Column(db.Integer, db.ForeignKey("bm_metrics.id"))
    bm_metrics = db.relationship("BMMetrics", uselist=False, backref="bm_meta_data")

    def __repr__(self):
        return f"BMMetaData<{self.title}"


class BMMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    solver = db.Column(db.Text)
    not_solver = db.Column(db.Text)

    def __repr__(self):
        return f"BMMetrics<solver={self.solver}, not_solver={self.not_solver}>"
