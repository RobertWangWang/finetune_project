import enum
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from llamafactory.hparams import model_args, data_args, training_args, finetuning_args, generating_args
from pydantic import BaseModel
from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Session, Mapped, mapped_column
from transformers import TrainingArguments

from app.db.db import Base
from app.models.user_model import User


@dataclass
class DeepSpeedArguments(dict):
    pass


class Module(str, enum.Enum):
    Model = "Model"
    Data = "Data"
    Training = "Training"
    Finetuning = "Finetuning"
    Generating = "Generating"
    Deepspeed = "Deepspeed"
    Output = "Output"


class ConfigType(str, enum.Enum):
    ModelArguments = "ModelArguments"
    # SGLangArguments = "SGLangArguments"
    # VllmArguments = "VllmArguments"
    # ExportArguments = "ExportArguments"
    # ProcessorArguments = "ProcessorArguments"
    # QuantizationArguments = "QuantizationArguments"
    # BaseModelArguments = "BaseModelArguments"

    DataArguments = "DataArguments"

    TrainingArguments = "TrainingArguments"
    # RayArguments = "RayArguments"
    # Seq2SeqTrainingArguments = "Seq2SeqTrainingArguments"

    FinetuningArguments = "FinetuningArguments"
    # SwanLabArguments = "SwanLabArguments"
    # BAdamArgument = "BAdamArgument"
    # ApolloArguments = "ApolloArguments"
    # GaloreArguments = "GaloreArguments"
    # RLHFArguments = "RLHFArguments"
    # LoraArguments = "LoraArguments"
    # FreezeArguments = "FreezeArguments"

    GeneratingArguments = "GeneratingArguments"

    DeepspeedArguments = "DeepspeedArguments"

    OutputArguments = "OutputArguments"

    def get_parser_cls(self):
        if self.value == ConfigType.ModelArguments.value:
            return model_args.ModelArguments
        # elif self.value == ConfigType.SGLangArguments.value:
        #     return model_args.SGLangArguments
        # elif self.value == ConfigType.VllmArguments.value:
        #     return model_args.VllmArguments
        # elif self.value == ConfigType.ExportArguments.value:
        #     return model_args.ExportArguments
        # elif self.value == ConfigType.ProcessorArguments.value:
        #     return model_args.ProcessorArguments
        # elif self.value == ConfigType.QuantizationArguments.value:
        #     return model_args.QuantizationArguments
        # elif self.value == ConfigType.BaseModelArguments.value:
        #     return model_args.BaseModelArguments

        elif self.value == ConfigType.DataArguments.value:
            return data_args.DataArguments

        elif self.value == ConfigType.TrainingArguments.value:
            return training_args.TrainingArguments
        # elif self.value == ConfigType.RayArguments.value:
        #     return training_args.RayArguments
        # elif self.value == ConfigType.Seq2SeqTrainingArguments.value:
        #     return training_args.Seq2SeqTrainingArguments

        elif self.value == ConfigType.FinetuningArguments.value:
            return finetuning_args.FinetuningArguments
        # elif self.value == ConfigType.SwanLabArguments.value:
        #     return finetuning_args.SwanLabArguments
        # elif self.value == ConfigType.BAdamArgument.value:
        #     return finetuning_args.BAdamArgument
        # elif self.value == ConfigType.ApolloArguments.value:
        #     return finetuning_args.ApolloArguments
        # elif self.value == ConfigType.GaloreArguments.value:
        #     return finetuning_args.GaloreArguments
        # elif self.value == ConfigType.RLHFArguments.value:
        #     return finetuning_args.RLHFArguments
        # elif self.value == ConfigType.LoraArguments.value:
        #     return finetuning_args.LoraArguments
        # elif self.value == ConfigType.FreezeArguments.value:
        #     return finetuning_args.FreezeArguments

        elif self.value == ConfigType.GeneratingArguments.value:
            return generating_args.GeneratingArguments
        elif self.value == ConfigType.DeepspeedArguments:
            return DeepSpeedArguments
        elif self.value == ConfigType.OutputArguments:
            return TrainingArguments
        else:
            raise ValueError(f"Unknown config type: {self.value}")


class FinetuneConfig(BaseModel):
    id: str
    user_id: str
    group_id: str

    name: str
    description: str

    module: Module
    config_type: ConfigType
    config: dict

    created_at: int
    updated_at: int
    is_deleted: int = 0


    def __json__(self):
        return self.model_dump()

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


class FinetuneConfigORM(Base):
    __tablename__ = "finetune_configs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(500))

    module: Mapped[Module] = mapped_column(String(255))
    config_type: Mapped[ConfigType] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[int] = mapped_column(Integer())
    updated_at: Mapped[int] = mapped_column(Integer())
    is_deleted: Mapped[int] = mapped_column(Integer(), default=0)

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


def list(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 100, module: str = None,
         config_type: str = None, name: str = None, ids: list[str] = None) -> (
        List[FinetuneConfigORM], int):
    query = session.query(FinetuneConfigORM).filter(FinetuneConfigORM.is_deleted == 0)

    if module:  # Add fuzzy search if name parameter is provided
        query = query.filter(FinetuneConfigORM.module == module)
    if config_type:
        query = query.filter(FinetuneConfigORM.config_type == config_type)
    if name:
        query = query.filter(FinetuneConfigORM.name.ilike(f'%{name}%'))
    if ids:
        query = query.filter(FinetuneConfigORM.id.in_(ids))

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, project_id: str) -> Optional[FinetuneConfigORM]:
    return session.query(FinetuneConfigORM).filter(
        FinetuneConfigORM.id == project_id,
        FinetuneConfigORM.group_id == current_user.group_id,
        FinetuneConfigORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, finetune_config: FinetuneConfigORM) -> Optional[FinetuneConfigORM]:
    finetune_config.id = str(uuid.uuid4())
    finetune_config.user_id = current_user.id
    finetune_config.group_id = current_user.group_id
    finetune_config.created_at = int(time.time())
    finetune_config.updated_at = int(time.time())
    session.add(finetune_config)
    session.commit()
    session.refresh(finetune_config)
    return finetune_config


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[FinetuneConfigORM]:
    finetune_config = get(session, current_user, id)
    if finetune_config:
        for key, value in update_data.items():
            setattr(finetune_config, key, value)
        finetune_config.updated_at = int(time.time())
        session.commit()
        session.refresh(finetune_config)
    return finetune_config


def delete(session: Session, current_user: User, id: str) -> Optional[FinetuneConfigORM]:
    finetune_config = get(session, current_user, id)
    if finetune_config:
        finetune_config.is_deleted = int(time.time())
        session.commit()
        session.refresh(finetune_config)
    return finetune_config
