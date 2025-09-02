import enum
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.dataset_models.dataset_version_model import DatasetType
from app.models.common_models.machine_model import MachineItem


class DeployStatus(str, enum.Enum):
    Init = "Init"
    Deploying = "Deploying"
    Starting = "Starting"
    Uninstalled = "Uninstalled"
    Error = "Error"


class FinetuneMethod(str, enum.Enum):
    Lora = "lora"
    Full = "full"
    Freeze = "freeze"


class LoraDeployInfo(BaseModel):
    id: str
    release_id: Optional[str]
    finetune_model_path: str
    stage: DatasetType

    status: DeployStatus
    error_info: Optional[str]


class RayRunningStatus(BaseModel):
    machine_id: str
    status: Optional[DeployStatus]
    error_info: Optional[str]


class DeployClusterItem(BaseModel):
    id: str

    name: str = Field(..., description="集群名称")
    machine_list: Optional[list[MachineItem]] = Field(..., description="集群机器")
    ray_running_status: Optional[list[RayRunningStatus]] = Field(..., description="集群 ray 服务运行情况")
    status: DeployStatus = Field(..., description="运行状态")
    error_info: Optional[str] = Field(..., description="错误信息")

    base_model: str = Field(..., description="基础模型")
    finetune_method: str = Field(..., description="微调方法")
    lora_deploy_infos: list[LoraDeployInfo] = Field(..., description="lora 部署信息")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class MachineList(BaseModel):
    total: int
    items: List[DeployClusterItem]


class DeployClusterCreate(BaseModel):
    name: str = Field(..., description="集群名称")
    machine_id_list: list[str] = Field(..., description="集群机器的id")
    base_model: str = Field(..., description="基础模型")
    finetune_method: FinetuneMethod = Field(..., description="微调方法")


class DeployClusterUpdate(BaseModel):
    name: str = Field(..., description="集群名称")
    machine_id_list: list[str] = Field(..., description="集群机器的id")
    base_model: str = Field(..., description="基础模型")


class LoraAdaptorDeployCreate(BaseModel):
    release_id: Optional[str] = Field(..., description="制品的id")
    finetune_model_path: str = Field(..., description="部署的地址")
    stage: DatasetType = Field(..., description="部署的状态")
