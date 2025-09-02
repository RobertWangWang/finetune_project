import json
import traceback
from typing import List

from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import file_pair_db, ga_pair_db, tag_db, question_db
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.file_pair_model import FilePairQuestionGeneratorContent
from app.models.dataset_models.job_model import JobResult, Progress, JobStatus
from app.models.user_model import User
from app.services.dataset_services.jobs.connon import JobHandlerInterface, update_job_status, build_user
from app.services.dataset_services.jobs.generator.file_pair import orm_tag_to_tag_item
from app.services.common_services.model_service import chat_with_error_handling, extract_json_from_llm_output
from app.services.dataset_services.prompt.add_label import get_add_label_prompt
from app.services.dataset_services.prompt.add_label_en import get_add_label_prompt_en
from app.services.dataset_services.prompt.question import get_question_prompt
from app.services.dataset_services.prompt.question_en import get_question_prompt_en


def batch_save_questions(label_questions, file_pair_orm, ga_pair_orm):
    create_questions: List[dict] = []
    for label_question in label_questions:
        question = label_question.get("question", "")
        if question == "":
            continue
        label = label_question.get("label", "")

        create_question_dict = {
            "question": question,
            "tag_name": label,
            "ga_pair": "",
            "file_pair_id": file_pair_orm.id,
            "file_id": file_pair_orm.file_id,
            "project_id": file_pair_orm.project_id,
        }
        if ga_pair_orm is not None:
            create_question_dict["ga_pair"] = json.dumps(ga_pair_orm.to_dict(), ensure_ascii=False)
        create_questions.append(create_question_dict)
    with manual_get_db() as session:
        question_db.bulk_create(session, User(id=file_pair_orm.user_id, group_id=file_pair_orm.group_id),
                                create_questions)


def chat_label_question(tags_orm, questions, label_prompt_func, job_result):
    tag_items = orm_tag_to_tag_item(tags_orm)
    label_prompt = label_prompt_func(tag_items, json.dumps(questions, ensure_ascii=False))
    job_result.append_logs(
        i18n.gettext("Start LLM rebuild question by label. prompt: {prompt}").format(
            prompt=label_prompt))
    chat_result, error = chat_with_error_handling(label_prompt)
    job_result.append_logs(
        i18n.gettext("End LLM rebuild question by label. result: {result}").format(
            result=chat_result))
    if error is not None:
        job_result.append_logs(error)
        return None
    label_questions = extract_json_from_llm_output(chat_result)
    return label_questions


class QuestionGeneratorHandler(JobHandlerInterface):
    def execute(self, job: JobORM) -> JobORM:
        content_map = json.loads(job.content)
        content = FilePairQuestionGeneratorContent(**content_map)

        job_result = JobResult(
            progress=Progress(
                total=len(content.file_pair_ids),
                done_count=0
            ),
        )

        job_result.append_logs(
            i18n.gettext("Process file_pair config: {config}").format(config=content.json()))
        update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)

        for file_pair_id in content.file_pair_ids:
            job_result.append_logs(
                i18n.gettext("Start process file_pair id: {id}").format(id=file_pair_id))

            try:
                with manual_get_db() as session:
                    file_pair_orm = file_pair_db.get(session, build_user(job), file_pair_id)
                    ga_pairs_orm, _ = ga_pair_db.list(session, build_user(job), 1, 9999, file_id=file_pair_orm.file_id,
                                                      enable="true")
                    tags_orm = tag_db.list(session, build_user(job), project_id=job.project_id)

                if content.number == 0:
                    content.number = int(len(file_pair_orm.content) / content.question_generation_length)

                prompt_func = get_question_prompt
                if job.locale == "en":
                    prompt_func = get_question_prompt_en

                label_prompt_func = get_add_label_prompt
                if job.locale == "en":
                    label_prompt_func = get_add_label_prompt_en

                if content.use_ga_generator:
                    for ga in ga_pairs_orm:
                        prompt = prompt_func(text=file_pair_orm.content, number=content.number, language=job.locale,
                                             global_prompt="", question_prompt="", active_ga_pair=ga)
                        job_result.append_logs(
                            i18n.gettext(
                                "Start LLM generator question by GA. ga_info: {ga_info}, prompt: {prompt}").format(
                                ga_info=ga.to_dict(), prompt=prompt))
                        chat_result, error = chat_with_error_handling(prompt)
                        job_result.append_logs(
                            i18n.gettext("End LLM generator question by GA. result={result}").format(
                                result=chat_result))
                        if error is not None:
                            job_result.append_logs(error)
                            continue

                        questions = extract_json_from_llm_output(chat_result)
                        if questions is None or len(questions) == 0:
                            job_result.append_logs(i18n.gettext("LLM generation result failed, result is empty"))
                            continue

                        label_questions = chat_label_question(tags_orm, questions, label_prompt_func,
                                                              job_result)
                        if label_questions is None:
                            continue
                        batch_save_questions(label_questions, file_pair_orm, ga)
                else:
                    prompt = prompt_func(text=file_pair_orm.content, number=content.number, language=job.locale,
                                         global_prompt="", question_prompt="", active_ga_pair=None)
                    job_result.append_logs(
                        i18n.gettext(
                            "Start LLM generator question. prompt: {prompt}").format(prompt=prompt))
                    chat_result, error = chat_with_error_handling(prompt)
                    job_result.append_logs(
                        i18n.gettext("End LLM generator question. result={result}").format(
                            result=chat_result))
                    if error is not None:
                        job_result.append_logs(error)
                        continue
                    questions = extract_json_from_llm_output(chat_result)
                    if questions is None or len(questions) == 0:
                        job_result.append_logs(i18n.gettext("LLM generation result failed, result is empty"))
                        continue

                    label_questions = chat_label_question(tags_orm, questions, label_prompt_func, job_result)
                    if label_questions is None:
                        continue
                    batch_save_questions(label_questions, file_pair_orm, None)

                job_result.progress.done_count += 1
                job_result.append_logs(
                    i18n.gettext("End process file_pair id: {id}").format(id=file_pair_id))
            except Exception as e:
                traceback.print_exc()
                job_result.append_logs(
                    i18n.gettext("Process file_pair failed, file_pair_id: {file_pair_id}, error: {error}").format(
                        file_pair_id=file_pair_id, error=e))
            finally:
                update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)

        job.result = job_result.json()
        return job
