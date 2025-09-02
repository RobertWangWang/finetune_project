import json
import traceback

from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import file_db, ga_pair_db
from app.db.dataset_db_model.ga_pair_db import GAPairORM
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.ga_pair_model import GaPairGeneratorConfig, GaPairChatResultItem
from app.models.dataset_models.job_model import JobResult, Progress, JobStatus
from app.services.dataset_services.jobs.connon import JobHandlerInterface, build_user, update_job_status
from app.services.common_services.model_service import chat_with_error_handling, extract_json_from_llm_output
from app.services.dataset_services.prompt.ga_generation import GA_GENERATION_PROMPT
from app.services.dataset_services.prompt.ga_generation_en import GA_GENERATION_PROMPT_EN


class GaPairGeneratorHandler(JobHandlerInterface):

    def execute(self, job: JobORM) -> JobORM:
        content_map = json.loads(job.content)
        config = GaPairGeneratorConfig(**content_map)

        job_result = JobResult(
            progress=Progress(
                total=len(config.file_ids),
                done_count=0
            ),
        )

        job_result.append_logs(
            i18n.gettext("Ga Pair generate config. config: {config}").format(config=config.json()))
        update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)

        with manual_get_db() as session:
            file_orm_list, _ = file_db.list(session, build_user(job), page_no=1, page_size=len(config.file_ids), project_id=config.project_id, file_ids=config.file_ids)

        file_ids = []
        for file_id in config.file_ids:
            if not any(file_id == file_orm.id for file_orm in file_orm_list):
                job_result.append_logs(i18n.gettext("File not found. id: {id}").format(id=id))
            else:
                file_ids.append(file_id)
        if job_result.logs != "":
            update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)

        for file in file_orm_list:
            try:
                job_result.append_logs(i18n.gettext("Start processing files, file_name: {file_name}").format(file_name=file.file_name))
                job_result.append_logs(i18n.gettext("Start calling the llm to generate data"))
                update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)

                prompt_template = GA_GENERATION_PROMPT
                if job.locale == "en":
                    prompt_template = GA_GENERATION_PROMPT_EN

                question = prompt_template.replace("{text_content}", file.content)
                chat_result, error = chat_with_error_handling(question)
                job_result.append_logs(i18n.gettext("End calling the llm to generate data. output: {output}").format(output=chat_result))
                if error is not None:
                    job_result.append_logs(error)
                    continue

                generator_ga_pairs = extract_json_from_llm_output(chat_result)
                if generator_ga_pairs is None or len(generator_ga_pairs) == 0:
                    job_result.append_logs(i18n.gettext("LLM generation result failed, result is empty"))
                    continue

                ga_pair_list: [GAPairORM] = []
                for ga_pair_dict in generator_ga_pairs:
                    item = GaPairChatResultItem(**ga_pair_dict)
                    ga_pair_list.append(GAPairORM(
                        text_style=item.genre.title,
                        text_desc=item.genre.description,
                        audience=item.audience.title,
                        audience_desc=item.audience.description,

                        enable=True,
                        file_id=file.id,
                        project_id=file.project_id
                    ))

                with manual_get_db() as session:
                    if config.append_mode:
                        existing_ga_pairs, total = ga_pair_db.list(session, build_user(job), 1, 999, file.id)
                        if total > 0:
                            existing_keys = {
                                (pair.text_style, pair.text_desc, pair.audience, pair.audience_desc)
                                for pair in existing_ga_pairs
                            }

                            create_ga_pair_dict = [
                                pair.to_dict() for pair in ga_pair_list
                                if (pair.text_style, pair.text_desc, pair.audience, pair.audience_desc) not in existing_keys
                            ]
                        else:
                            create_ga_pair_dict = [pair.to_dict() for pair in ga_pair_list]
                        if len(create_ga_pair_dict) > 0:
                            ga_pair_db.bulk_create(session, build_user(job), create_ga_pair_dict)
                    else:
                        ga_pair_db.bulk_delete_ga_pairs(session, build_user(job), file_ids=[file.id])
                        ga_pair_db.bulk_create(session, build_user(job), [pair.to_dict() for pair in ga_pair_list])

                job_result.append_logs(
                    i18n.gettext("End processing files, file_name: {file_name}").format(file_name=file.file_name))
                job_result.progress.done_count += 1
            except Exception as e:
                traceback.print_exc()
                job_result.append_logs(
                    i18n.gettext("Process files failed, file_id: {file_id}, error: {error}").format(
                        file_id=file.id, error=e))
            finally:
                update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)

        job.result = job_result.json()
        return job

