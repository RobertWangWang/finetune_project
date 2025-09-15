from os import path

from app.config.config import settings

machine_run_dir = "/dataset_finetune"


def build_logs_path(job_id: str):
    return path.join(machine_run_dir, 'jobs', job_id, "run.log")


def build_local_logs_path(job_id: str, machine_id: str):
    return path.join(settings.FINETUNE_FILE_LOCAL_DIR, job_id, machine_id, "run.log")


def build_local_lora_model_path(job_id: str):
    return path.join(settings.FINETUNE_FILE_LOCAL_DIR, job_id, "lora_model.tar.gz")


def build_work_path(job_id: str):
    return path.join(machine_run_dir, 'jobs', job_id)


def build_config_path(job_id: str):
    return path.join(machine_run_dir, 'jobs', job_id, "config.yaml")


def build_deepspeed_path(job_id: str):
    return path.join(machine_run_dir, 'jobs', job_id, "deepspeed.json")


def build_dataset_path(dataset_id: str):
    return path.join(machine_run_dir, 'datasets', dataset_id + ".json")


def build_train_dataset_info_json_path(job_id: str):
    return path.join(machine_run_dir, "datasets", job_id, "dataset_info.json")


def build_train_dataset_info_path(job_id: str):
    return path.join(machine_run_dir, "datasets", job_id)


def build_output_path(job_id: str):
    return path.join(machine_run_dir, 'jobs', job_id, "output")


def build_lora_output_tar_path(job_id: str):
    return path.join(machine_run_dir, 'jobs', job_id, "lora_model.tar.gz")


# --------- 部署的地址
def build_deploy_work_path(deploy_id: str):
    return path.join(machine_run_dir, 'deploys', deploy_id)


def build_deploy_logs_path(deploy_id: str):
    return path.join(machine_run_dir, 'deploys', deploy_id, "run.log")


def build_deploy_lora_tar_path(deploy_id: str, lora_id: str):
    return path.join(machine_run_dir, 'deploys', deploy_id, "loras", lora_id, "lora_model.tar.gz")


def build_deploy_lora_path(deploy_id: str, lora_id: str):
    return path.join(machine_run_dir, 'deploys', deploy_id, "loras", lora_id)

# --------- 评估的地址
def build_evaluation_work_path(evaluation_id: str):
    return path.join(machine_run_dir, 'evaluations', evaluation_id)

def build_evaluation_logs_path(evaluation_id: str):
    return path.join(machine_run_dir, 'evaluations', evaluation_id, "run.log")

def build_evaluation_lora_tar_path(evaluation_id: str, lora_id: str):
    return path.join(machine_run_dir, 'evaluations', evaluation_id, "loras", lora_id, "lora_model.tar.gz")

def build_evaluation_lora_path(evaluation_id: str, lora_id: str):
    return path.join(machine_run_dir, 'evaluations', evaluation_id, "loras", lora_id)

def build_evaluation_llm_model_path(evaluation_id: str, llm_name: str):
    return path.join(machine_run_dir, 'evaluations', evaluation_id, "llm_model", llm_name)