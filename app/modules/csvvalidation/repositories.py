from app.modules.csvvalidation.models import Csvvalidation
from core.repositories.BaseRepository import BaseRepository


class CsvvalidationRepository(BaseRepository):
    def __init__(self):
        super().__init__(Csvvalidation)
