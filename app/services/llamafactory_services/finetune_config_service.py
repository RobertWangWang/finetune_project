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

    """
    session: Session → 数据库会话，用于 ORM 操作。
    current_user: User → 当前用户对象，表明是谁创建的配置。
    finetune_config_save: FinetuneConfigSave → 输入的 Pydantic 模型（从 API 请求体传来的微调配置数据）。
    返回
        FinetuneConfigItem → Pydantic 模型，作为 API 返回体。

    class FinetuneConfigSave(BaseModel):
        name: str = Field(..., description="配置名称")
        description: str = Field(..., description="配重描述")
        module: Module = Field(..., description="模块") ### 微调的基座模型
        config_type: ConfigType = Field(..., description="配置类型") ### 配置所属的类别
        config: dict = Field(..., description="配置内容")

          "config": {
                "model_name_or_path": "/dataset_finetune/models/DeepSeek-R1-Distill-Qwen-1.5B",
                "trust_remote_code": true
                }
    """

    parser = HfArgumentParser(finetune_config_save.config_type.get_parser_cls())
    (args,) = parser.parse_dict(finetune_config_save.config, allow_extra_keys=True)

    """
    HfArgumentParser

        这是 HuggingFace Transformers 提供的工具类，常用于解析训练脚本的参数。
        get_parser_cls() 返回一个 dataclass 类（比如 TrainingArguments、ModelArguments），告诉解析器要生成哪种参数对象。

    parser.parse_dict(...)

        把 API 请求传来的配置字典 finetune_config_save.config 转换成 HuggingFace 风格的参数对象 args。
        allow_extra_keys=True 表示即使字典里多了一些字段，也不会报错。
        👉 作用：确保传进来的配置参数是 合法的 HuggingFace 微调参数。
    """

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
