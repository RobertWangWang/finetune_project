from dataclasses import dataclass

from app.db.dataset_db_model.dataset_version_db import DatasetVersionORM
from app.lib.finetune_path.path_build import build_dataset_path, build_deepspeed_path, build_config_path, \
    build_logs_path


@dataclass
class build_sft_template_params:
    dataset: DatasetVersionORM
    deepspeed_config_json: str
    job_id: str
    train_yaml: str
    cmds: list[str]


def build_sft_template(params: build_sft_template_params) -> str:
    deepspeed_markdown = ""
    if params.deepspeed_config_json != "":
        deepspeed_markdown = f"""#### deepspeed 微调配置文件准备
        当勾选了 deepspeed 配置时候, 微调任务初始化阶段会根据 deepspeed 配置生成对应的 deepspeed.json 文件并拷贝到主机的 {build_deepspeed_path(params.job_id)} 位置, deepspeed.json 文件内容如下
        ```json
        {params.deepspeed_config_json}
        ```
        """

    llamafactory_cmd = ""
    for cmd in params.cmds:
        llamafactory_cmd += cmd + "\r\n"

    template = f"""
## 微调任务的整体流程

### 微调任务初始化
微调任务创建之后会有一个初始化阶段，该阶段会将一些前置的文件拷贝到机器上, 前置任务如下

#### 数据集准备
在微调任务初始化阶段将会吧数据集({params.dataset.name})拷贝到主机的 {build_dataset_path(params.dataset.id)} 位置

#### llamafactory-cli 微调配置文件准备
在微调任务初始化阶段将会将勾选的配置合并生成 config.yaml 文件并拷贝到主机的 {build_config_path(params.job_id)} 位置, config.yaml 文件内容如下
```yaml
{params.train_yaml}
```

{deepspeed_markdown}

### 启动微调
在微调任务启动后会在机器上执行如下 shell 命令, 该命令会在机器上根据微调任务的 id 创建对应的 service。 后续对微调任务状态的管理都是根据 systemctl 的指令来操作这些 service
```shell
{llamafactory_cmd}
```

### 停止微调
在对运行中的微调任务进行取消会调用 `systemctl stop {params.job_id}.service` 命令来停止微调任务

### 微调日志查看
微调执行中生成的日志都会存储在 {build_logs_path(params.job_id)} 文件里面。 对于运行中的微调任务UI界面查看日志会执行 tail 命令实时监听日志文件并返回, 对于运行完成的微调任务会获取该文件内容并返回
    """
    return template
