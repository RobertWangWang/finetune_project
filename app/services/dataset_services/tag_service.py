from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.dataset_db_model import tag_db, project_db, question_db
from app.db.dataset_db_model.tag_db import TagORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.tag_model import TagItem, TagUpdate, TagCreate
from app.models.user_model import User


def get_all_tags(session: Session, current_user: User, project_id: str) -> List[TagItem]:
    tags = tag_db.list(session, current_user, project_id)
    if not tags:
        return []

    tag_map = {tag.id: TagItem(**tag.to_dict()) for tag in tags}
    root_tag = []
    for tag in tag_map.values():
        questions, total = question_db.list(session, current_user, 1, 9999, project_id=tag.project_id, match_tag_name=tag.label)
        if total > 0:
            tag.question_id_list = [question.id for question in questions]
        else:
            tag.question_id_list = []
        if tag.parent_id:
            parent = tag_map[tag.parent_id]
            if not parent:
                continue
            if parent.childes is None:
                parent.childes = []
            parent.childes.append(tag)
        else:
            root_tag.append(tag)
    return root_tag


def insert_tags(session: Session, current_user: User, project_id: str, tags: List[dict], parent_id: str):
    for tag in tags:
        tag_item = create_tag(session, current_user, TagCreate(
            label=tag["label"],
            parent_id=parent_id,
            project_id=project_id,
        ))
        childes = tag.get("child")
        if childes is not None and len(childes) > 0:
            insert_tags(session, current_user, project_id, childes, tag_item.id)


def batch_save_tags(session: Session, current_user: User, project_id: str, tags: List[dict]):
    tag_db.bulk_delete_tags(session, current_user, [project_id])
    insert_tags(session, current_user, project_id, tags, "")


def create_tag(session: Session, current_user: User, tag: TagCreate) -> TagItem:
    project = project_db.get(session, current_user, tag.project_id)
    if not project:
        raise HTTPException(status_code=500, detail=i18n.gettext("Project not found. id: {id}").format(id=tag.project_id))

    root_ids = ""
    if tag.parent_id:
        parent = tag_db.get(session, current_user, tag.parent_id)
        if not parent:
            raise HTTPException(status_code=500, detail=i18n.gettext("Parent tag not found. parent_id: {id}").format(id=tag.parent_id))
        root_ids = parent.root_ids + "," + parent.id

    tag_orm = TagORM(
        label=tag.label,
        parent_id=tag.parent_id,
        root_ids=root_ids,
        project_id=tag.project_id,
    )
    tag_orm = tag_db.create(session, current_user, tag_orm)
    return tag_orm


def update_tag(session: Session, current_user: User, id: str, tag: TagUpdate) -> TagItem:
    tag_orm = tag_db.update(session, current_user, id, tag.model_dump(exclude_unset=True))
    if not tag_orm:
        raise HTTPException(status_code=500, detail=i18n.gettext("Tag not found. id: {id}").format(id=id))
    return tag_orm


def delete_tag(session: Session, current_user: User, id: str) -> TagItem:
    tag_db.bulk_delete_tags(session, current_user, parent_id=id)
    tag_orm = tag_db.delete(session, current_user, id)
    if not tag_orm:
        raise HTTPException(status_code=500, detail=i18n.gettext("Tag not found. id: {id}").format(id=id))
    return tag_orm
