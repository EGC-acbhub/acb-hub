import re

import unidecode
from sqlalchemy import any_, or_

from app.modules.basketmodel.models import BasketModel, BMMetaData
from app.modules.dataset.models import DataSet, DSMetaData, League
from core.repositories.BaseRepository import BaseRepository


class ExploreRepository(BaseRepository):
    def __init__(self):
        super().__init__(DataSet)

    def filter(self, query="", sorting="newest", league="any", tags=[], **kwargs):
        # Normalize and remove unwanted characters
        normalized_query = unidecode.unidecode(query).lower()
        cleaned_query = re.sub(r'[,.":\'()\[\]^;!¡¿?]', "", normalized_query)

        filters = []
        for word in cleaned_query.split():
            filters.append(DSMetaData.title.ilike(f"%{word}%"))
            filters.append(DSMetaData.description.ilike(f"%{word}%"))
            # search by csv filename
            filters.append(BMMetaData.csv_filename.ilike(f"%{word}%"))
            filters.append(BMMetaData.title.ilike(f"%{word}%"))
            filters.append(BMMetaData.description.ilike(f"%{word}%"))
            filters.append(BMMetaData.tags.ilike(f"%{word}%"))
            filters.append(DSMetaData.tags.ilike(f"%{word}%"))

        datasets = (
            self.model.query.join(DataSet.ds_meta_data)
            .join(DataSet.basket_models)
            .join(BasketModel.bm_meta_data)
            .filter(or_(*filters))
            .filter(DSMetaData.deposition_id.isnot(None))  # Exclude datasets with empty deposition_id
        )

        if league != "any":
            matching_type = None
            for member in League:
                if member.value.lower() == league:
                    matching_type = member
                    break

            if matching_type is not None:
                datasets = datasets.filter(DSMetaData.league == matching_type.name)

        if tags:
            datasets = datasets.filter(DSMetaData.tags.ilike(any_(f"%{tag}%" for tag in tags)))

        # Order by created_at
        if sorting == "oldest":
            datasets = datasets.order_by(self.model.created_at.asc())
        else:
            datasets = datasets.order_by(self.model.created_at.desc())

        return datasets.all()
