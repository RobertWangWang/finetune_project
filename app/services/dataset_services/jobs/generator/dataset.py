import json
import traceback

from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import question_db, file_pair_db, ga_pair_db, dataset_db
from app.db.dataset_db_model.dataset_db import DatasetORM
from app.db.dataset_db_model.ga_pair_db import GAPairORM
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.question_model import DatasetGeneratorRequest
from app.models.dataset_models.job_model import JobResult, Progress, JobStatus
from app.services.dataset_services.common_service import check_and_update_question_has_dataset
from app.services.dataset_services.jobs.connon import JobHandlerInterface, build_user, update_job_status
from app.services.common_services.model_service import chat_cot_with_error_handling, get_model
from app.services.dataset_services.prompt.answer import get_answer_prompt
from app.services.dataset_services.prompt.answer_en import get_answer_en_prompt
from app.services.dataset_services.prompt.enhanced_answer import get_enhanced_answer_prompt
from app.services.dataset_services.prompt.enhanced_answer_en import get_enhanced_answer_en_prompt
from app.services.dataset_services.prompt.optimize_cot import optimize_cot_prompt
from app.services.dataset_services.prompt.optimize_cot_en import optimize_cot_en_prompt


class DatasetGeneratorHandler(JobHandlerInterface):

    def execute(self, job: JobORM) -> JobORM:
        content_map = json.loads(job.content)
        content = DatasetGeneratorRequest(**content_map)

        job_result = JobResult(
            progress=Progress(
                total=len(content.question_ids),
                done_count=0
            ),
        )

        job_result.append_logs(
            i18n.gettext("Process dataset generator config: {config}").format(config=job.content))
        update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)

        for question_id in content.question_ids:
            try:
                job_result.append_logs(
                    i18n.gettext("Start process question. question_id: {id}").format(id=question_id))

                with manual_get_db() as session:
                    question_orm = question_db.get(session, build_user(job), question_id)
                    file_pair_orm = file_pair_db.get(session, build_user(job), question_orm.file_pair_id)
                    ga_pairs_orm, _ = ga_pair_db.list(session, build_user(job), 1, 9999, file_id=file_pair_orm.file_id,
                                                      enable="true")
                    if question_orm.ga_pair and question_orm.ga_pair != "":
                        ga_orm = GAPairORM(**json.loads(question_orm.ga_pair))

                if ga_orm or len(ga_pairs_orm) > 0:
                    job_result.append_logs(
                        i18n.gettext("Use MGA to enhance prompt words to generate answers"))

                    prompt_func = get_enhanced_answer_prompt
                    if job.locale == "en":
                        prompt_func = get_enhanced_answer_en_prompt
                    prompt = prompt_func(file_pair_orm.content, question_orm.question, job.locale, "", "", ga_pairs_orm, ga_orm)

                else:
                    job_result.append_logs(
                        i18n.gettext("Generate answers using standard prompt words"))

                    prompt_func = get_answer_prompt
                    if job.locale == "en":
                        prompt_func = get_answer_en_prompt
                    prompt = prompt_func(file_pair_orm.content, question_orm.question, job.locale, "", "")

                job_result.append_logs(
                    i18n.gettext(
                        "Start LLM generator dataset, prompt: {prompt}").format(prompt=prompt))
                chat_cot_resp, error = chat_cot_with_error_handling(prompt)
                job_result.append_logs(
                    i18n.gettext("End LLM generator dataset. result={result}").format(
                        result=chat_cot_resp.json()))
                if error:
                    job_result.append_logs(error)
                    continue

                llm_model, err = get_model()
                if err:
                    job_result.append_logs(error)
                    continue

                dataset = DatasetORM(
                    question=question_orm.question,
                    answer=chat_cot_resp.answer,
                    question_id=question_orm.id,
                    tag_name=question_orm.tag_name,
                    file_pair_id=question_orm.file_pair_id,
                    model=llm_model.model_name,
                    confirmed=False,
                    file_id=question_orm.file_id,
                    project_id=question_orm.project_id,
                )
                if ga_orm:
                    dataset.ga_pair = json.dumps(ga_orm.to_dict(), ensure_ascii=False)

                # 思维链优化
                if chat_cot_resp.cot is not None and chat_cot_resp.cot != "":
                    cot_prompt_func = optimize_cot_prompt
                    if job.locale == "en":
                        cot_prompt_func = optimize_cot_en_prompt
                    cot_prompt = cot_prompt_func(question_orm.question, chat_cot_resp.answer, chat_cot_resp.cot)
                    chat_cot_resp, error = chat_cot_with_error_handling(cot_prompt)
                    if error:
                        job_result.append_logs(error)
                    else:
                        dataset.cot = chat_cot_resp.answer or chat_cot_resp.cot

                with manual_get_db() as session:
                    dataset_db.create(session, build_user(job), dataset)
                    check_and_update_question_has_dataset(session, build_user(job), question_id)

                job_result.progress.done_count += 1
                job_result.append_logs(
                    i18n.gettext("End process question. question_id: {id}").format(id=question_id))
            except Exception as e:
                traceback.print_exc()
                job_result.append_logs(
                    i18n.gettext("Process question failed, question_id: {question_id}, error: {error}").format(
                        question_id=question_id, error=e))
            finally:
                update_job_status(session, job.id, build_user(job), JobStatus.Running, job_result)

        job.result = job_result.json()
        return job