from dataclasses import dataclass

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.user_model import User
from app.services.dataset_services import dataset_service


class SFTData(BaseModel):
    instruction: str = Field(..., description="输入")
    input: str = Field(..., description="用户输入")
    output: str = Field(..., description="输出")


def sft_dataset_processor(session: Session, current_user: User, project_id: str, ids: list[str], options: dict) -> list:
    batch_datasets = dataset_service.list_datasets(
        session,
        current_user,
        1,
        len(ids),
        project_id=project_id,
        ids=ids
    )

    data = []
    for dataset in batch_datasets.data:
        instruction = dataset.question
        output = dataset.answer
        output_with_cot = options.get("output_with_cot")
        if output_with_cot is not None and output_with_cot == True and dataset.cot is not None and dataset.cot != "":
            output = f"<think>{dataset.cot}<\\think>\n{output}"
        data.append(SFTData(
            instruction=instruction,
            input="",
            output=output,
        ))
    return data

