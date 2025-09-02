from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.common_db_model import machine_db
from app.db.common_db_model.machine_db import MachineORM
from app.lib.i18n.config import i18n
from app.lib.machine_connect.machine_connect import RemoteMachine, Machine
from app.models.user_model import User
from app.models.common_models.machine_model import MachineItem, \
    MachineList, MachineSave, MachineConnectTest

from app.db.common_db_model.machine_db import (
    create_machine as _create_machine,
    get_machine_by_id as _get_machine_by_id,
    update_machine as _update_machine,
    delete_machine as _delete_machine,
)


def orm_machine_to_item(orm: MachineORM) -> MachineItem:
    item = MachineItem(
        id=orm.id,
        is_active=orm.is_active,
        hostname=orm.hostname,
        device_type=orm.device_type,
        cuda_available=orm.cuda_available,
        gpu_count=orm.gpu_count,

        ip=orm.client_config.get("ip"),
        internal_ip=orm.client_config.get("internal_ip"),
        ssh_port=orm.client_config.get("ssh_port"),
        ssh_user=orm.client_config.get("ssh_user"),
        ssh_password=orm.client_config.get("ssh_password"),
        ssh_private_key=orm.client_config.get("ssh_private_key")
    )

    return item


def item_to_machine_orm(item: MachineSave) -> MachineORM:
    orm = MachineORM(
        hostname=item.hostname,
        device_type=item.device_type,
        cuda_available=item.cuda_available,
        gpu_count=item.gpu_count,
    )
    orm.client_config = {
        "ip": item.ip,
        "ssh_port": item.ssh_port,
        "ssh_user": item.ssh_user,
        "ssh_password": item.ssh_password,
        "ssh_private_key": item.ssh_private_key,
        "internal_ip": item.internal_ip,
    }
    return orm


def machine_map_search(session: Session, current_user: User, machine_id_list: list) -> dict:
    machine_list, _ = machine_db.list_machines(session, current_user, 1, len(machine_id_list),
                                               ids=machine_id_list)
    machine_dict = {machine.id: machine for machine in machine_list}
    return machine_dict


def create_machine(session: Session, current_user: User, data: MachineSave) -> MachineItem:
    orm = item_to_machine_orm(data)
    item = _create_machine(session, orm, current_user)
    return orm_machine_to_item(item)


def get_machine(session: Session, current_user: User, machine_id: str) -> Optional[MachineItem]:
    item = _get_machine_by_id(session, current_user, machine_id)
    if item:
        return orm_machine_to_item(item)

    raise HTTPException(status_code=500, detail=i18n.gettext("Machine not found. id: {id}").format(id=machine_id))


def update_machine(session: Session, current_user: User, machine_id: str, data: MachineSave) -> Optional[MachineItem]:
    orm = item_to_machine_orm(data)
    item = _update_machine(session, current_user, machine_id, orm.to_dict())
    return orm_machine_to_item(item)


def delete_machine(session: Session, current_user: User, machine_id: str) -> bool:
    item = _delete_machine(session, current_user, machine_id)
    return item


def list_machines(
        session: Session,
        current_user: User,
        page_no: int = 1,
        page_size: int = 100,
        is_active: Optional[bool] = None
) -> MachineList:
    machine_orm_list, total = machine_db.list_machines(session, current_user, page_no, page_size, is_active)
    items = [orm_machine_to_item(obj) for obj in machine_orm_list]
    return MachineList(items=items, total=total)


def get_machine_client(session: Session, current_user: User, id: str, local: str = None) -> RemoteMachine:
    machine_orm = machine_db.get_machine_by_id(session, current_user, id)
    if machine_orm is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Machine not found. id: {id}", local=local).format(id=id))

    machine_client = machine_orm.to_remote_machine()
    return machine_client


def machine_orm_to_client(orm) -> RemoteMachine:
    return RemoteMachine(
        Machine(
            ip=orm.client_config.get("ip"),
            ssh_port=orm.client_config.get("ssh_port"),
            ssh_user=orm.client_config.get("ssh_user"),
            ssh_password=orm.client_config.get("ssh_password"),
            ssh_private_key=orm.client_config.get("ssh_private_key")
        )
    )


def machine_connect_test(session: Session,
                         current_user: User,
                         test: MachineConnectTest) -> str:
    if test.id and test.id != "":
        machine_client = get_machine_client(session, current_user, test.id)
    else:
        machine_client = RemoteMachine(
            test
        )

    is_active = False
    try:
        ok, error_info = machine_client.test_connection()
        if not ok:
            raise HTTPException(status_code=500,
                                detail=i18n.gettext("Machine connection test failed. error: {error}").format(
                                    error_info))

        out, error, code = machine_client.execute_command("llamafactory-cli --help")
        if code != 0:
            raise HTTPException(status_code=500,
                                detail=i18n.gettext(
                                    "Llamafactory-cli on the machine was not found. exit_code: {exit_code}, error: {error}").format(
                                    exit_code=code, error=error))
        is_active = True
    except Exception as e:
        raise e
    finally:
        if test.id and test.id != "":
            _ = machine_db.update_machine(session, current_user, test.id, {
                "is_active": is_active
            })

    return i18n.gettext("Connection successful")
