from app.db.db import engine, Base
from app.db.evaluation_db_model.evaluation_dataset_db import EvaluationDataset  # ✅ 确保导入模型

def init_db():
    Base.metadata.create_all(engine)
