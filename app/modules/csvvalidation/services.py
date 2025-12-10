from app.modules.csvvalidation.repositories import CsvvalidationRepository
from core.services.BaseService import BaseService


class CsvvalidationService(BaseService):
    def __init__(self):
        super().__init__(CsvvalidationRepository())
