from sqlalchemy import func

from app.modules.basketmodel.models import BasketModel, BMMetaData
from core.repositories.BaseRepository import BaseRepository


class BasketModelRepository(BaseRepository):
    def __init__(self):
        super().__init__(BasketModel)

    def count_basket_models(self) -> int:
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0


class BMMetaDataRepository(BaseRepository):
    def __init__(self):
        super().__init__(BMMetaData)
