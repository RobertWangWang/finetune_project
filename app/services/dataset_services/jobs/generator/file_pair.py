import json
import traceback
from typing import List, Dict

from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import file_db, file_pair_db, catalog_db, tag_db
from app.db.dataset_db_model.catalog_db import CatalogORM
from app.db.dataset_db_model.file_db import FileORM
from app.db.dataset_db_model.file_pair_db import FilePairORM
from app.db.dataset_db_model.job_db import JobORM
from app.db.dataset_db_model.tag_db import TagORM
from app.lib.i18n.config import i18n
from app.lib.split import split
from app.lib.split.markdown.cores import toc
from app.models.dataset_models.file_model import GetFileItem, FilePairGeneratorContent, TocBuildAction
from app.models.dataset_models.job_model import JobResult, Progress, JobStatus
from app.models.dataset_models.tag_model import TagChatResultItem
from app.services.dataset_services import catalog_service
from app.services.dataset_services.jobs.connon import JobHandlerInterface, update_job_status, build_user
from app.services.common_services.model_service import chat_with_error_handling, extract_json_from_llm_output
from app.services.dataset_services.prompt import label_en, label_revise, label, label_revise_en
from app.services.dataset_services.tag_service import batch_save_tags


def file_split(job: JobORM, content: FilePairGeneratorContent, job_result: JobResult, file: FileORM):
    with manual_get_db() as session:
        job_result.append_logs(
            i18n.gettext("Start splitting files"))
        file_pair_db.bulk_delete_file_pairs(session, build_user(job), file_ids=[file.id])
        update_job_status(session, job.id, build_user(job), JobStatus.Running, job_result)

        file_dict = file.to_dict()
        item = GetFileItem(**file_dict)
        split_items = split.split_file(item, content.config)
        file_pair_data: List[Dict] = []
        for split_item in split_items:
            file_pair = FilePairORM(**split_item.dict())
            file_pair.file_id = file.id
            file_pair.project_id = file.project_id
            file_pair.question_id_list = ""
            file_pair_data.append(file_pair.to_dict())
        file_pair_db.bulk_create(session, build_user(job), file_pair_data)

        job_result.append_logs(
            i18n.gettext("End splitting files"))

    update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)


def catalog_generator(job: JobORM, job_result: JobResult, file: FileORM) -> str:
    job_result.append_logs(
        i18n.gettext("Start create file catalog"))

    file_catalog_info = toc.extract_table_of_contents(file.content)
    new_toc = json.dumps(file_catalog_info, ensure_ascii=False)
    with manual_get_db() as session:
        catalog_db.bulk_delete_catalog(session, build_user(job), file_ids=[file.id])

        catalog_db.create(session, build_user(job), CatalogORM(
            file_id=file.id,
            file_name=file.file_name,
            content=new_toc,
            project_id=file.project_id,
        ))

    job_result.append_logs(
        i18n.gettext("End create file catalog"))

    update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)
    return new_toc


def orm_tag_to_tag_item(tags: List[TagORM]) -> List[TagChatResultItem]:
    # 1. 过滤已删除的标签并建立id到ORM对象的映射
    tag_map: Dict[str, TagORM] = {}
    for tag in tags:
        if tag.is_deleted == 0:  # 只处理未删除的标签
            tag_map[tag.id] = tag

    # 2. 建立父子关系映射
    parent_child_map: Dict[str, List[TagORM]] = {}
    for tag in tag_map.values():
        if tag.parent_id not in parent_child_map:
            parent_child_map[tag.parent_id] = []
        parent_child_map[tag.parent_id].append(tag)

    # 3. 递归构建树形结构
    def build_tree(parent_id: str) -> List[TagChatResultItem]:
        result = []
        # 获取当前parent_id下的所有子标签
        children = parent_child_map.get(parent_id, [])
        for child in children:
            # 为每个子标签创建节点
            node = TagChatResultItem(
                label=child.label,
                child=build_tree(child.id)  # 递归构建子树
            )
            result.append(node)
        return result

    # 4. 从根节点(parent_id为None或空字符串)开始构建树
    root_parent_ids = [None, ""]  # 考虑parent_id可能为None或空字符串的情况
    root_tags = []
    for root_id in root_parent_ids:
        if root_id in parent_child_map:
            root_tags.extend(parent_child_map[root_id])

    return build_tree("")  # 从根节点开始构建


def tag_generator(job: JobORM, toc_build_action: str, job_result: JobResult, delete_toc: str, new_toc: str):
    job_result.append_logs(
        i18n.gettext("Start generator tag"))

    with manual_get_db() as session:
        all_catalog = catalog_db.list(session, build_user(job), job.project_id)
        all_tags = tag_db.list(session, build_user(job), job.project_id)

    if toc_build_action == TocBuildAction.Revise.name and len(all_tags) == 0:
        toc_build_action = TocBuildAction.Rebuild.name

    prompt = ""
    toc = catalog_service.catalog_to_toc(all_catalog)
    if toc_build_action == TocBuildAction.Rebuild.name:
        tag_prompt_func = label.get_label_prompt
        if job.locale == "en":
            tag_prompt_func = label_en.get_label_prompt

        prompt = tag_prompt_func(toc, '', '')
    elif toc_build_action == TocBuildAction.Revise.name:
        tag_prompt_func = label_revise.get_label_revise_prompt
        if job.locale == "en":
            tag_prompt_func = label_revise_en.get_label_revise_prompt_en

        prompt = tag_prompt_func(toc, orm_tag_to_tag_item(all_tags), deleted_content=delete_toc, new_content=new_toc)

    tags = []
    if prompt != "":
        job_result.append_logs(i18n.gettext("Start calling the llm to generate data. prompt: {prompt}").format(prompt=prompt))
        chat_result, error = chat_with_error_handling(prompt)
        job_result.append_logs(
            i18n.gettext("End calling the llm to generate data. output: {output}").format(output=chat_result))
        if error is not None:
            job_result.append_logs(error)
        else:
            tags = extract_json_from_llm_output(chat_result)

    if len(tags) > 0:
        with manual_get_db() as session:
            batch_save_tags(session, build_user(job), job.project_id, tags)

    job_result.append_logs(
        i18n.gettext("End generator tag"))

    update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)


class FilePairGeneratorHandler(JobHandlerInterface):

    def execute(self, job: JobORM) -> JobORM:
        content_map = json.loads(job.content)
        content = FilePairGeneratorContent(**content_map)

        job_result = JobResult(
            progress=Progress(
                total=len(content.file_ids),
                done_count=0
            ),
        )

        job_result.append_logs(
            i18n.gettext("Process files config, file_id_list: {file_id_list}, config: {config}").format(
                file_id_list=json.dumps(content.file_ids), config=content.config.json()))
        update_job_status(None, job.id, build_user(job), JobStatus.Running, job_result)

        for file_id in content.file_ids:
            try:
                with manual_get_db() as session:
                    file = file_db.get(session, build_user(job), file_id)

                if not file:
                    job_result.append_logs(
                        i18n.gettext("File not found. id: {id}").format(id=id))
                else:
                    job_result.append_logs(
                        i18n.gettext("Start processing files, file_name: {file_name}").format(
                            file_name=file.file_name))

                    file_split(job, content, job_result, file)
                    new_toc = catalog_generator(job, job_result, file)
                    tag_generator(job, content.config.toc_build_action, job_result, "", new_toc)

                    job_result.append_logs(
                        i18n.gettext("End processing files, file_name: {file_name}").format(
                            file_name=file.file_name))

                job_result.progress.done_count += 1
            except Exception as e:
                traceback.print_exc()
                job_result.append_logs(
                    i18n.gettext("Process files failed, file_id: {file_id}, error: {error}").format(
                        file_id=file_id, error=e))
            finally:
                update_job_status(session, job.id, build_user(job), JobStatus.Running, job_result)

        job.result = job_result.json()
        return job
