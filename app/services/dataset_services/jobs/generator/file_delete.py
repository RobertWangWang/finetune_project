import json

from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import catalog_db
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.lib.split.markdown.cores import toc
from app.models.dataset_models.file_model import FileDeleteGeneratorContent
from app.models.dataset_models.job_model import JobResult, Progress
from app.services.dataset_services.jobs.connon import JobHandlerInterface, build_user
from app.services.dataset_services.jobs.generator.file_pair import tag_generator


class FileDeleteGeneratorHandler(JobHandlerInterface):
    def execute(self, job: JobORM) -> JobORM:
        content_map = json.loads(job.content)
        content = FileDeleteGeneratorContent(**content_map)

        job_result = JobResult(
            progress=Progress(
                total=1,
                done_count=1
            ),
        )

        job_result.append_logs(
            i18n.gettext("Process file delete config, file_name: {file_name}, config: {config}").format(
                file_name=content.file.file_name, config=content.config.json()))

        file_catalog_info = toc.extract_table_of_contents(content.file.content)
        delete_toc = json.dumps(file_catalog_info, ensure_ascii=False)
        tag_generator(job, content.config.toc_build_action, job_result, delete_toc, "")
        # 事后删除目录，因为 tag_generator 要使用
        with manual_get_db() as session:
            catalog_db.bulk_delete_catalog(session, build_user(job), file_ids=[content.file.id])
        job.result = job_result.json()
        return job





