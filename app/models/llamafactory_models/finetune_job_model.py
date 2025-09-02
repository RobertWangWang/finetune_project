import enum
from typing import Optional

from pydantic import BaseModel, Field

from app.lib.machine_connect.machine_connect import Machine
from app.models.dataset_models.dataset_version_model import DatasetType, DatasetVersionItem
from app.models.llamafactory_models.finetune_config_model import FinetuneConfigItem
from app.models.common_models.machine_model import MachineItem


class FinetuneJobStatus(str, enum.Enum):
    Init = "Init"
    Initializing = "Initializing"
    Starting = "Starting"
    Cancel = "Cancel"
    Success = "Success"
    Failed = "Failed"
    Error = "error"


class FinetuneJobItem(BaseModel):
    id: str

    name: str = Field(..., description="任务名称")
    description: str = Field("", description="任务描述")
    status: FinetuneJobStatus = Field(..., description="任务状态")

    stage: DatasetType = Field(..., description="微调类型")
    finetune_method: str = Field(..., description="微调方法")
    dataset_version: DatasetVersionItem = Field(..., description="数据集版本")
    finetune_config_list: list[FinetuneConfigItem] = Field(..., description="配置列表")
    node_finetune_machines: list[MachineItem] = Field(None, description="微调 node 机器列表")

    error_info: Optional[str] = Field(None, description="错误信息")
    done_node_num: int = Field(0, description="完成节点数量")

    release_id: Optional[str] = Field(None, description="制品id")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class FinetuneJobList(BaseModel):
    data: list[FinetuneJobItem] = Field(..., description="微调任务列表")
    count: int = Field(..., description="总数")


class FinetuneJobCreate(BaseModel):
    name: str = Field(..., description="任务名称")
    description: str = Field(..., description="任务描述")

    stage: DatasetType = Field(..., description="微调类型")
    dataset_version_id: str = Field(..., description="数据集版本id")
    finetune_config_id_list: list[str] = Field(..., description="配置列表id")

    node_finetune_machine_id_list: list[str] = Field(None, description="微调 node 机器 id 列表")


class FinetuneJobRunningExampleRequest(BaseModel):
    id: Optional[str] = Field(None, description="id")

    stage: Optional[DatasetType] = Field(None, description="微调类型")
    dataset_version_id: Optional[str] = Field(None, description="数据集版本id")
    finetune_config_id_list: list[str] = Field(None, description="配置列表id")
    node_finetune_machine_id_list: list[str] = Field(None, description="微调 node 机器 id 列表")


class FinetuneJobRunningExample(BaseModel):
    machine_id: str = Field(..., description="机器id")
    machine_name: str = Field(..., description="机器名称")
    machine_client: Machine = Field(..., description="机器连接信息")

    cmds: list[str] = Field(..., description="运行的指令")
    train_yaml: str = Field(..., description="微调配置文件内容")
    deepspeed_json: str = Field(..., description="deepspeed配置")
    dataset_path: str = Field(..., description="数据集位置")

    markdown: str = Field(..., description="展示markdown")
