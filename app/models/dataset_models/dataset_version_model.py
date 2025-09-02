import enum

from pydantic import BaseModel, Field


class DatasetType(str, enum.Enum):
    # Pre-training
    PreTraining = "PT"

    # Post-training
    SupervisedFineTuning = "SFT"
    DirectPreferenceOptimization = "DPO"
    KahnemanTaverskyOptimization = "KTO"


class DatasetVersionItem(BaseModel):
    id: str

    name: str = Field(..., description="版本名称")
    description: str = Field(..., description="版本描述")
    dataset_type: DatasetType = Field(..., description="数据集类型")
    options: dict = Field(..., description="版本配置")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class DatasetVersionList(BaseModel):
    data: list[DatasetVersionItem] = Field(..., description="版本列表")
    count: int = Field(..., description="总数")


class DatasetVersionCreate(BaseModel):
    name: str = Field(..., description="版本名称")
    description: str = Field(..., description="版本描述")

    project_id: str = Field(..., description="项目id")
    dataset_id_list: list[str] = Field(..., description="数据集列表")
    dataset_type: DatasetType = Field(..., description="数据集类型")

    options: dict = Field({}, description="版本配置")


class DatasetVersionUpdate(BaseModel):
    name: str = Field(..., description="版本名称")
    description: str = Field(..., description="版本描述")
