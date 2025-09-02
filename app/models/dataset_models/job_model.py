import datetime
from enum import Enum
from typing import Union, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    Running = "Running"
    Failed = "Failed"
    Cancel = "Cancel"
    Success = "Success"


class JobType(str, Enum):
    FilePairGenerator = "FilePairGenerator"
    FileDeleteGenerator = "FileDeleteGenerator"
    GaPairGenerator = "GaPairGenerator"
    TagGenerator = "TagGenerator"
    QuestionGenerator = "QuestionGenerator"
    DatasetGenerator = "DatasetGenerator"


class Progress(BaseModel):
    total: int = Field(1, description="执行项数量")
    done_count: int = Field(1, description="执行项完成数量")


class JobResult(BaseModel):
    progress: Optional[Progress] = Field(None, description="执行项数量")
    logs: str = Field("", description="执行日志")
    error: str = Field("", description="错误日志")

    def append_logs(self, logs: str) -> None:
        # Get current time in a readable format
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Add timestamp to the log entry
        timestamped_log = f"[{current_time}] {logs}"

        if not self.logs:  # This checks for both empty string and None
            self.logs = timestamped_log
        else:
            self.logs = self.logs + "\n" + timestamped_log

    def clean_logs(self):
        self.logs = ""


class JobItem(BaseModel):
    id: str = Field(..., description="任务id")

    type: str = Field(..., description="任务类型")
    status: str = Field(..., description="任务状态")
    locale: str = Field(..., description="国际化语言")
    content: str = Field(..., description="任务内容")
    result: Optional[JobResult] = Field(None, description="任务结果")

    project_id: str = Field(..., description="所属项目")


class JobList(BaseModel):
    data: list[JobItem] = Field(..., description="任务列表")
    count: int = Field(..., description="总数")
