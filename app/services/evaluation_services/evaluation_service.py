# app/services/evaluation_service.py
from __future__ import annotations
from typing import Tuple, List, Optional, Iterable, Dict, Any
import hashlib
import asyncio
import os, paramiko
import requests
from tqdm import tqdm
import evaluate
from datasets import load_dataset
from sqlalchemy.orm import Session
from loguru import logger

from app.db.common_db_model.machine_db import get_machine_by_id
from app.lib.finetune_path.path_build import (
    build_evaluation_logs_path,
    build_evaluation_work_path,
    build_evaluation_lora_path,
    build_evaluation_llm_model_path,
    build_evaluation_lora_tar_path)
from app.models.user_model import User
from app.db.evaluation_db_model.evaluation_db import EvaluationORM, list_evaluations as orm_list, get_evaluation as orm_get
from app.db.evaluation_db_model.evaluation_db import EvaluationStatus
from app.models.evaluation_models.evaluation_model import (
    EvaluationCreate, EvaluationUpdate,
    EvaluationOut, EvaluationListQuery, EvaluationListOut,DatasetEvaluationRequest
)
from app.config.config import settings

def _allowed_fields_from_orm(orm_cls) -> set[str]:
    """
    根据 ORM 的 mapper 自动获取可写字段集合，避免硬编码字段名。
    """
    return {attr.key for attr in orm_cls.__mapper__.attrs}


def _assign_by_allowlist(obj: EvaluationORM, data: Dict[str, Any], allow: Iterable[str]) -> None:
    """
    仅给 ORM 对象赋值在 allow 集合中的字段，避免 Unknown 字段报错。
    """
    for k, v in data.items():
        if k in allow:
            setattr(obj, k, v)


# ------------------- CRUD for routes to call ------------------- #
def list_evaluations(
    session: Session,
    current_user: User,
    query: EvaluationListQuery
) -> EvaluationListOut:
    """
    分页查询 + 条件过滤。过滤字段与 ORM 层 list() 保持一致。
    """
    from app.db.evaluation_db_model.evaluation_db import list_evaluations as orm_list

    # 直接复用 ORM 层的 list()，确保排序/分页一致
    rows, total = orm_list(
        session=session,
        current_user=current_user,
        page_no=query.page_no,
        page_size=query.page_size,
        evaluation_dataset_id=query.evaluation_dataset_id,
        eval_type=query.eval_type,
        eval_model_id=query.eval_model_id,
    )

    items = [EvaluationOut.model_validate(r) for r in rows]
    return EvaluationListOut(items=items, total=total)


def get_evaluation(
    session: Session,
    current_user: User,
    evaluation_id: str
) -> Optional[EvaluationOut]:
    """
    根据 ID 获取单条记录。找不到返回 None。
    """
    from app.db.evaluation_db_model.evaluation_db import get_evaluation as orm_get

    row = orm_get(session=session, current_user=current_user, evaluation_id=evaluation_id)
    return EvaluationOut.model_validate(row) if row else None


def create_evaluation(
    session: Session,
    current_user: User,
    data: EvaluationCreate
) -> EvaluationOut:
    """
    创建记录：自动注入 user_id/group_id/时间戳 等在 ORM create() 里完成。
    """
    from app.db.evaluation_db_model.evaluation_db import create_evaluation as orm_create
    allow = _allowed_fields_from_orm(EvaluationORM)
    obj = EvaluationORM()
    _assign_by_allowlist(obj, data.model_dump(exclude_none=True), allow)

    created = orm_create(session=session, current_user=current_user, evaluation=obj)
    return EvaluationOut.model_validate(created)


def update_evaluation(
    session: Session,
    current_user: User,
    evaluation_id: str,
    patch: EvaluationUpdate
) -> Optional[EvaluationOut]:
    """
    局部更新：仅更新传入的字段，且只更新 ORM 允许的字段。
    """
    from app.db.evaluation_db_model.evaluation_db import update as orm_update

    allow = _allowed_fields_from_orm(EvaluationORM)
    payload = {k: v for k, v in patch.model_dump(exclude_none=True).items() if k in allow}

    updated = orm_update(
        session=session,
        current_user=current_user,
        evaluation_id=evaluation_id,
        update_data=payload
    )
    return EvaluationOut.model_validate(updated) if updated else None


def delete_evaluation(
    session: Session,
    current_user: User,
    evaluation_id: str
) -> Optional[EvaluationOut]:
    """
    软删除：底层把 is_deleted 置为1，保留审计。
    """
    from app.db.evaluation_db_model.evaluation_db import delete as orm_delete

    deleted = orm_delete(session=session, current_user=current_user, evaluation_id=evaluation_id)
    return EvaluationOut.model_validate(deleted) if deleted else None

async def evaluate_model_on_dataset(
    db: Session,
    current_user: User,
    request: DatasetEvaluationRequest
) -> dict:
    """
    在指定机器上运行大模型数据集评测
    - 加载数据集
    - 调用 vLLM API 推理
    - 计算 BLEU / ROUGE / Accuracy
    - 更新数据库
    """

    # 1. 找到 Evaluation 任务
    evaluation: EvaluationORM = db.query(EvaluationORM).filter_by(
        record_id=request.id,
        user_id=current_user.id
    ).first()
    if not evaluation:
        raise ValueError(f"未找到 record_id={request.record_id} 的任务")

    path_prefix = ""
    if request.role == "system":
        path_prefix = settings.DEFAULT_EVALUATION_FOLDER
    elif request.role == "user":
        path_prefix = settings.USER_EVALUATION_FOLDER

    evaluation_id = evaluation.record_id

    # === 动态创建日志文件（evaluation_id 命名） ===
    log_file = f"evaluation_{evaluation_id}.log"
    logger.add(
        log_file,
        rotation=None,       # 不分割
        enqueue=True,        # 实时写入
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )
    logger.info(f"日志文件已创建: {log_file}")

    print(path_prefix+request.dataset_path)

    # 2. 加载数据集
    if request.dataset_path.endswith(".json") or request.dataset_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=path_prefix+request.dataset_path, split=request.partition_keyword)
    else:
        dataset = load_dataset(path_prefix+request.dataset_path, split=request.partition_keyword)

    logger.info(f"数据集 {request.dataset_path} 加载完成，总样本数={len(dataset)}")

    # 取一个小样本（避免 OOM）
    subset = dataset.select(range(min(25, len(dataset))))
    logger.info(f"实际评测样本数={len(subset)}")

    predictions, references = [], []

    # 3. 推理接口配置
    machine = get_machine_by_id(db, current_user, request.machine_id)
    if not machine or not machine.client_config:
        logger.error(f"未找到指定机器或缺少 client_config: {request.machine_id}")
        raise ValueError(f"未找到指定机器或缺少 client_config: {request.machine_id}")

    ip = machine.client_config.get("ip")
    vllm_url = f"http://{ip}:8001/v1/chat/completions"
    model_name = evaluation.eval_model_id

    logger.info(f"使用机器 {ip}，推理接口={vllm_url}")

    # 4. 遍历数据集，调用 vLLM API
    for example in tqdm(subset, desc="Evaluating"):
        print(example)
        messages = example[request.evaluation_extraction_keyword]
        ref_answer = messages[-1]["content"].strip()

        payload = {
            "model": model_name,
            "messages": messages[:-1],
            "temperature": 0.1,
            "max_tokens": 512
        }

        try:
            resp = requests.post(vllm_url, json=payload, timeout=60)
            resp.raise_for_status()
            output = resp.json()

            generated = output["choices"][0]["message"]["content"].strip()

            predictions.append(generated)
            references.append(ref_answer)

            logger.debug(f"预测完成: ref={ref_answer[:30]} pred={generated[:30]}")

        except Exception as e:
            logger.exception(f"调用 vLLM API 出错: {e}")
            predictions.append("")
            references.append(ref_answer)

    # 5. 评测：ROUGE / BLEU / Accuracy
    rouge = evaluate.load("rouge")
    bleu = evaluate.load("bleu")

    logger.info("开始计算 ROUGE 和 BLEU")

    rouge_result = rouge.compute(predictions=predictions, references=references, num_process=16)
    bleu_result = bleu.compute(predictions=predictions, references=references, num_process=16)
    accuracy = sum(p == r for p, r in zip(predictions, references)) / len(predictions)

    results = {"rouge": rouge_result, "bleu": bleu_result, "accuracy": accuracy}
    logger.success(f"评测完成，结果: {results}")

    # 6. 更新数据库
    evaluation.eval_result = results
    evaluation.status = "evaluated"
    db.commit()
    logger.info(f"数据库已更新，record_id={evaluation_id}")

    return results


