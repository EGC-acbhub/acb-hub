from app.modules.basketmodel.repositories import BasketModelRepository, BMMetaDataRepository
from app.modules.hubfile.services import HubfileService
from core.services.BaseService import BaseService


class BasketModelService(BaseService):
    def __init__(self):
        super().__init__(BasketModelRepository())
        self.hubfile_service = HubfileService()

    def total_basket_model_views(self) -> int:
        return self.hubfile_service.total_hubfile_views()

    def total_basket_model_downloads(self) -> int:
        return self.hubfile_service.total_hubfile_downloads()

    def count_basket_models(self):
        return self.repository.count_basket_models()

    class BMMetaDataService(BaseService):
        def __init__(self):
            super().__init__(BMMetaDataRepository())
