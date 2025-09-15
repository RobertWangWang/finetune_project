from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Body

from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.models.common_models.machine_model import (
    MachineItem,
    MachineList, MachineSave, MachineConnectTest,
)

from app.services.common_services import machine_service as machine_service

router = APIRouter(prefix="/machines", tags=["machines"])


@router.get("/", response_model=MachineList, summary="查询机器列表")
def list_machines(
    session: SessionDep,
    current_user: CurrentUserDep,
    page_no: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    is_active: Optional[bool] = Query(None),
):

    return machine_service.list_machines(
        session=session,
        current_user=current_user,
        page_no=page_no,
        page_size=page_size,
        is_active=is_active,
    )


@router.get("/{machine_id}", response_model=MachineItem, summary="获取机器详情")
def get_machine(
    machine_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    return machine_service.get_machine(session, current_user, machine_id)


@router.post("/", response_model=MachineItem, summary="创建机器")
def create_machine(
        session: SessionDep,
        current_user: CurrentUserDep,
        create_data: MachineSave = Body(...),

):
    """
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
    """
    return machine_service.create_machine(session, current_user, create_data)


@router.put("/{machine_id}", response_model=MachineItem, summary="更新机器")
def update_machine(
        machine_id: str,
        session: SessionDep,
        current_user: CurrentUserDep,
        update_data: MachineSave = Body(...),
):
    updated = machine_service.update_machine(session, current_user, machine_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="机器未找到或无法更新")
    return updated


@router.delete("/{machine_id}", response_model=bool, summary="删除机器")
def delete_machine(
        session: SessionDep,
        current_user: CurrentUserDep,
        machine_id: str,
):
    deleted = machine_service.delete_machine(session, current_user, machine_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="机器未找到或已删除")
    return deleted


@router.post("/connect_test", response_model=str, summary="连通性测试")
def machine_connect_test(
        session: SessionDep,
        current_user: CurrentUserDep,
        test: MachineConnectTest
):
    result = machine_service.machine_connect_test(session, current_user, test)
    return result