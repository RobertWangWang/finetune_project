# app/services/evaluation_services/evaluation_service.py
import concurrent.futures
import json
import math
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
import evaluate  # pip install evaluate
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.model_evaluation_db_model import evaluation_db
from app.db.model_evaluation_db_model.evaluation_db import EvaluationORM
from app.db.dataset_db_model.dataset_db import DatasetORM  # 参考 dataset_db.py
from app.lib.i18n.config import i18n
from app.models.evaluation_models.evaluation_model import (
    EvaluationItem, EvaluationList, EvaluationCreate, EvaluationUpdate, EvaluationRun
)
from app.models.user_model import User


# ---------- utils ----------
def _http_ok(resp: requests.Response):
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")


def _curl_load_lora(vllm_base_url: str, lora_name: str, lora_path: str):
    """
    用命令行 curl 调 vLLM 的 /v1/load_lora_adapter 接口实现动态加载 LoRA。
    如你的 vLLM 分支字段不同，请在此调整 adapter_name/lora_path 键名。
    """
    url = vllm_base_url.rstrip("/") + "/v1/load_lora_adapter"
    payload = json.dumps({"adapter_name": lora_name, "lora_path": lora_path}, ensure_ascii=False)
    cmd = f"curl -sS -X POST {shlex.quote(url)} -H 'Content-Type: application/json' -d {shlex.quote(payload)}"
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"curl failed: {proc.stderr.strip() or proc.stdout.strip()}")


def _chat_completion(vllm_base_url: str, prompt: str, lora_name: str,
                     max_tokens: int, temperature: float) -> Tuple[str, float]:
    """
    调 vLLM 的 /v1/chat/completions；通过 header + extra_body 传 lora_name。
    返回：(生成文本, 单次请求延迟秒)
    """
    url = vllm_base_url.rstrip("/") + "/v1/chat/completions"
    headers = {"X-LoRA-Adapter": lora_name}
    body = {
        "model": "served-base",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "extra_body": {"lora_name": lora_name},
    }
    t0 = time.time()
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    latency = time.time() - t0
    _http_ok(resp)
    data = resp.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except Exception:
        text = json.dumps(data, ensure_ascii=False)
    return text, latency


def _compute_metrics(preds: List[str], refs: List[str]) -> Dict[str, Any]:
    """
    计算 Accuracy / BLEU / ROUGE
    - Accuracy: 严格字符串匹配（可按需拓展）
    - ROUGE: 取 rougeLsum 作为单值
    """
    correct = sum(1 for p, r in zip(preds, refs) if p.strip() == r.strip())
    accuracy = correct / max(1, len(refs))

    bleu = evaluate.load("bleu")
    rouge = evaluate.load("rouge")

    bleu_score = bleu.compute(predictions=preds, references=[[r] for r in refs])
    rouge_score = rouge.compute(predictions=preds, references=refs)
    rouge_scalar = float(rouge_score.get("rougeLsum", 0.0))

    return {
        "accuracy": float(accuracy),
        "bleu": float(bleu_score.get("bleu", 0.0)),
        "rouge_scalar": rouge_scalar,
        "rouge_detail": {
            "rouge1": float(rouge_score.get("rouge1", 0.0)),
            "rouge2": float(rouge_score.get("rouge2", 0.0)),
            "rougeL": float(rouge_score.get("rougeL", 0.0)),
            "rougeLsum": rouge_scalar,
        },
    }


# ---------- converters ----------
def _to_item(orm: EvaluationORM) -> EvaluationItem:
    return EvaluationItem(
        id=orm.id,
        project_id=orm.project_id,
        tag_name=orm.tag_name,
        model=orm.model,
        bleu=orm.bleu,
        rouge=orm.rouge,
        accuracy=orm.accuracy,
        latency=orm.latency,
        throughput=orm.throughput,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


# ---------- CRUD services ----------
def create_evaluation(session: Session, current_user: User, create: EvaluationCreate) -> EvaluationItem:
    obj = EvaluationORM(
        project_id=create.project_id,
        tag_name=create.tag_name,
        model=create.model,
        bleu=None, rouge=None, accuracy=None, latency=None, throughput=None,
    )
    saved = evaluation_db.create(session, current_user, obj)
    return _to_item(saved)


def get_evaluation(session: Session, current_user: User, id: str) -> EvaluationItem:
    obj = evaluation_db.get(session, current_user, id)
    if not obj:
        raise HTTPException(status_code=404, detail=i18n.gettext("Evaluation task not found. id: {id}").format(id=id))
    return _to_item(obj)


def list_evaluations(session: Session, current_user: User, page: int, page_size: int,
                     project_id: str, tag_name: Optional[str] = None, model: Optional[str] = None) -> EvaluationList:
    rows, total = evaluation_db.list(session, current_user, page, page_size, project_id, tag_name, model)
    return EvaluationList(data=[_to_item(r) for r in rows], count=total)


def update_evaluation(session: Session, current_user: User, id: str, update: EvaluationUpdate) -> EvaluationItem:
    data = update.model_dump(exclude_unset=True)
    obj = evaluation_db.update(session, current_user, id, data)
    if not obj:
        raise HTTPException(status_code=404, detail=i18n.gettext("Evaluation task not found. id: {id}").format(id=id))
    return _to_item(obj)


def delete_evaluation(session: Session, current_user: User, id: str) -> EvaluationItem:
    existed = evaluation_db.get(session, current_user, id)
    if not existed:
        raise HTTPException(status_code=404, detail=i18n.gettext("Evaluation task not found. id: {id}").format(id=id))
    deleted = evaluation_db.delete(session, current_user, id)
    return _to_item(deleted or existed)


# ---------- run evaluation (核心执行) ----------
def run_evaluation(session: Session, current_user: User, id: str, run: EvaluationRun) -> EvaluationItem:
    """
    运行评测：
      1) 命令行 curl 动态加载 LoRA
      2) 从 DatasetORM 读取 confirmed=True，叠加 EvaluationORM 的过滤（project_id/tag_name/model）
      3) 并发请求 vLLM /v1/chat/completions
      4) 计算 BLEU/ROUGE/准确率/平均延迟/吞吐
      5) 写回 EvaluationORM
    """
    orm = evaluation_db.get(session, current_user, id)
    if not orm:
        raise HTTPException(status_code=404, detail=i18n.gettext("Evaluation task not found. id: {id}").format(id=id))

    # 1) 动态加载 LoRA（命令行）
    _curl_load_lora(run.vllm_base_url, run.lora_name, run.lora_path)

    # 2) 拉数：仅 confirmed=True
    q = session.query(DatasetORM).filter(
        DatasetORM.user_id == current_user.id,
        DatasetORM.group_id == current_user.group_id,
        DatasetORM.is_deleted == 0,
        DatasetORM.confirmed == True,
    )
    if orm.project_id:
        q = q.filter(DatasetORM.project_id == orm.project_id)
    if orm.tag_name:
        q = q.filter(DatasetORM.tag_name == orm.tag_name)
    if orm.model:
        q = q.filter(DatasetORM.model == orm.model)

    rows = q.order_by(desc(DatasetORM.created_at)).limit(run.max_examples).all()
    if not rows:
        raise HTTPException(status_code=400, detail=i18n.gettext("No dataset rows found for evaluation."))

    prompts: List[str] = []
    refs: List[str] = []
    for r in rows:
        ques = (r.question or "").strip()
        cot = (r.cot or "").strip() if hasattr(r, "cot") else ""
        prompt = f"{ques}\n" if not cot else f"{ques}\n（可用思维链）{cot}\n"
        prompts.append(prompt)
        refs.append((r.answer or "").strip())

    # 3) 并发推理
    preds: List[str] = []
    latencies: List[float] = []

    def _worker(p: str) -> Tuple[str, float]:
        return _chat_completion(run.vllm_base_url, p, run.lora_name, run.max_tokens, run.temperature)

    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=run.concurrency) as ex:
        futs = [ex.submit(_worker, p) for p in prompts]
        for fut in concurrent.futures.as_completed(futs):
            try:
                text, lat = fut.result()
                preds.append(text)
                latencies.append(lat)
            except Exception:
                preds.append("")
                latencies.append(float("inf"))
    t1 = time.time()

    n = len(prompts)
    wall = max(1e-6, t1 - t0)
    finite = [x for x in latencies if math.isfinite(x)]
    avg_latency = (sum(finite) / max(1, len(finite))) if finite else float("inf")
    throughput_rps = n / wall

    # 4) 指标
    scores = _compute_metrics(preds, refs)

    # 5) 写回 ORM
    update_payload = dict(
        bleu=scores["bleu"],
        rouge=scores["rouge_scalar"],
        accuracy=scores["accuracy"],
        latency=float(avg_latency),
        throughput=float(throughput_rps),
    )
    saved = evaluation_db.update(session, current_user, id, update_payload)
    return _to_item(saved)
