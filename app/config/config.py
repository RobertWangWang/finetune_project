# settings.py
from dotenv import load_dotenv
import os

load_dotenv()


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


# 创建全局实例
settings = Settings()
