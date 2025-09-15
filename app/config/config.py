# settings.py
import os
from dotenv import load_dotenv
from pathlib import Path

# 找到和 settings.py 同目录的 .env
env_path = Path(__file__).resolve().parent / ".env"
print(f"Loading .env from {env_path}")
load_dotenv(dotenv_path=env_path)

class Settings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_settings()
        return cls._instance

    def _init_settings(self):
        """初始化所有配置项"""
        self.DATABASE_URL = os.getenv('DATABASE_URL')
        self.MODEL_DATABASE_URL = os.getenv('MODEL_DATABASE_URL')
        self.DATASET_VERSION_DIR = os.getenv('DATASET_VERSION_DIR')
        self.FINETUNE_FILE_LOCAL_DIR = os.getenv('FINETUNE_FILE_LOCAL_DIR')
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        self.DEFAULT_EVALUATION_FOLDER = os.getenv('DEFAULT_EVALUATION_DATASET_FOLDER_DIR_PATH')
        self.USER_EVALUATION_FOLDER = os.getenv('DEFAULT_EVALUATION_DATASET_USER_UPLOAD_DIR_PATH')
        os.environ['DISABLE_VERSION_CHECK'] = "1" ### llamafactory 与 4.0.0版本的dataset冲突，临时关闭

# 创建全局实例
settings = Settings()