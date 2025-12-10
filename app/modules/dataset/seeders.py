import os
import shutil
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.modules.auth.models import User
from app.modules.basketmodel.models import BasketModel, BMMetaData
from app.modules.dataset.models import DataSet, DSMetaData, DSMetrics, League
from app.modules.hubfile.models import Hubfile
from core.seeders.BaseSeeder import BaseSeeder


class DataSetSeeder(BaseSeeder):
    priority = 2  # Lower priority

    def run(self):
        # Retrieve users
        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()

        if not user1 or not user2:
            raise Exception("Users not found. Please seed users first.")

        # Create DSMetrics instance
        ds_metrics = DSMetrics(number_of_models="5", number_of_features="50")
        seeded_ds_metrics = self.seed([ds_metrics])[0]

        # Create DSMetaData instances
        ds_meta_data_list = [
            DSMetaData(
                deposition_id=1 + i,
                title=f"Sample dataset {i + 1}",
                description=f"Description for dataset {i + 1}",
                league=League.LEGA,
                tags="tag1, tag2",
                ds_metrics_id=seeded_ds_metrics.id,
            )
            for i in range(4)
        ]
        seeded_ds_meta_data = self.seed(ds_meta_data_list)

        # Create DataSet instances
        datasets = [
            DataSet(
                user_id=user1.id if i % 2 == 0 else user2.id,
                ds_meta_data_id=seeded_ds_meta_data[i].id,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(4)
        ]
        seeded_datasets = self.seed(datasets)

        # Assume there are 12 CSV files, create corresponding BMMetaData and BasketModel
        bm_meta_data_list = [
            BMMetaData(
                csv_filename=f"file{i + 1}.csv",
                title=f"Feature Model {i + 1}",
                description=f"Description for feature model {i + 1}",
                league=League.ACB,
                tags="tag1, tag2",
                csv_version="1.0",
            )
            for i in range(12)
        ]
        seeded_bm_meta_data = self.seed(bm_meta_data_list)

        basket_models = [
            BasketModel(data_set_id=seeded_datasets[i // 3].id, bm_meta_data_id=seeded_bm_meta_data[i].id)
            for i in range(12)
        ]
        seeded_basket_models = self.seed(basket_models)

        # Create files, associate them with BasketModels and copy files
        load_dotenv()
        working_dir = os.getenv("WORKING_DIR", "")
        src_folder = os.path.join(working_dir, "app", "modules", "dataset", "csv_examples")
        for i in range(12):
            file_name = f"file{i + 1}.csv"
            basket_model = seeded_basket_models[i]
            dataset = next(ds for ds in seeded_datasets if ds.id == basket_model.data_set_id)
            user_id = dataset.user_id

            dest_folder = os.path.join(working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy(os.path.join(src_folder, file_name), dest_folder)

            file_path = os.path.join(dest_folder, file_name)

            csv_file = Hubfile(
                name=file_name,
                checksum=f"checksum{i + 1}",
                size=os.path.getsize(file_path),
                basket_model_id=basket_model.id,
            )
            self.seed([csv_file])
