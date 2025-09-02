from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from transformers import HfArgumentParser

from app.db.llamafactory_db_model import finetune_config_db
from app.db.llamafactory_db_model.finetune_config_db import FinetuneConfigORM
from app.lib.i18n.config import i18n
from app.models.llamafactory_models.finetune_config_model import FinetuneConfigSave, FinetuneConfigList, \
    FinetuneConfigItem
from app.models.user_model import User


def list_finetune_config(session: Session, current_user: User, page_no: int, page_size: int, module: str = None,
                         config_type: str = None, name: str = None) -> FinetuneConfigList:
    finetune_config_orm_list, total = finetune_config_db.list(session, current_user, page_no, page_size, module,
                                                              config_type, name)
    return FinetuneConfigList(
        data=[FinetuneConfigItem(**finetune_config.to_dict()) for finetune_config in finetune_config_orm_list],
        count=total
    )


def create_finetune_config(session: Session, current_user: User,
                           finetune_config_save: FinetuneConfigSave) -> FinetuneConfigItem:

    parser = HfArgumentParser(finetune_config_save.config_type.get_parser_cls())
    (args,) = parser.parse_dict(finetune_config_save.config, allow_extra_keys=True)

    finetune_config_orm = finetune_config_db.create(session, current_user, FinetuneConfigORM(
        **finetune_config_save.dict()
    ))
    return FinetuneConfigItem(**finetune_config_orm.to_dict())


def update_finetune_config(session: Session, current_user: User, id: str,
                           finetune_config_save: FinetuneConfigSave) -> FinetuneConfigItem:
    parser = HfArgumentParser(finetune_config_save.config_type.get_parser_cls())
    (args,) = parser.parse_dict(finetune_config_save.config, allow_extra_keys=True)

    finetune_config_orm = finetune_config_db.update(session, current_user, id,
                                                    finetune_config_save.model_dump(exclude_unset=True))
    if not finetune_config_orm:
        raise HTTPException(status_code=500, detail=i18n.gettext("FinetuneConfig not found. id: {id}").format(id=id))
    return FinetuneConfigItem(**finetune_config_orm.to_dict())


def delete_finetune_config(session: Session, current_user: User, finetune_config_id: str) -> FinetuneConfigItem:
    finetune_config_orm = finetune_config_db.delete(session, current_user, finetune_config_id)
    if finetune_config_orm:
        return FinetuneConfigItem(**finetune_config_orm.to_dict())
    else:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("FinetuneConfig not found. id: {id}").format(id=finetune_config_id))
