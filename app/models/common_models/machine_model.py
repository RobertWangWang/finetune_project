from pydantic import BaseModel, Field
from typing import Optional, List

from app.lib.machine_connect.machine_connect import Machine


### MachineBase
class MachineBase(BaseModel):
    hostname: str = Field(..., description="机器名称")
    device_type: Optional[str] = Field(..., description="设备类型")
    cuda_available: bool = Field(True, description="是否是 cuda 设备")
    gpu_count: int = Field(1, description="GPU的数量")

    ip: str = Field(..., description="机器的 ip")
    internal_ip: str = Field(..., description="机器的内网 ip")
    ssh_port: int = Field(22, description="登陆的端口")
    ssh_user: str = Field(..., description="ssh 登陆账号")
    ssh_password: Optional[str] = Field(None, description="登陆的密码")
    ssh_private_key: Optional[str] = Field(None, description="登陆使用的私钥")


class MachineSave(MachineBase):
    pass


### MachineOut / MachineItem Used for responses.
class MachineItem(MachineBase):
    id: str
    is_active: bool = Field(..., description="是否连接")


class MachineList(BaseModel):
    total: int
    items: List[MachineItem]


class MachineConnectTest(Machine):
    id: Optional[str] = Field(None, description="id")
