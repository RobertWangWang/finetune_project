import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config.config import settings
from app.db.dataset_db_model import dataset_version_db
from app.db.dataset_db_model.dataset_version_db import DatasetVersionORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.dataset_version_model import DatasetVersionUpdate, DatasetVersionCreate, \
    DatasetVersionList, DatasetVersionItem, DatasetType
from app.models.user_model import User
from app.services.dataset_services.dataset_version_processer.sft_processor import sft_dataset_processor


def dataset_version_file_path_builder(id: str):
    return os.path.join(settings.DATASET_VERSION_DIR, id + ".jsonl")


def list_dataset_version(session: Session, current_user: User, page: int, page_size: int, project_id: str = None,
                         name: str = None) -> DatasetVersionList:
    dataset_version_list, total = dataset_version_db.list(session, current_user, page, page_size, project_id, name)
    items = [DatasetVersionItem(**version.to_dict()) for version in dataset_version_list]
    return DatasetVersionList(
        data=items,
        count=total
    )


def get_dataset_version_path(session: Session, current_user: User, id: str) -> str:
    orm = dataset_version_db.get(session, current_user, id)
    if orm is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Dataset version not found. id: {id}").format(id=id))

    return dataset_version_file_path_builder(orm.id)


def create_dataset_version(session: Session, current_user: User,
                           dataset_version_create: DatasetVersionCreate) -> DatasetVersionItem:
    if dataset_version_create.dataset_type != DatasetType.SupervisedFineTuning:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Parameter verification failed. {param}").format(param="dataset_type"))

    create_result = dataset_version_db.create(session, current_user, DatasetVersionORM(
        name=dataset_version_create.name,
        description=dataset_version_create.description,
        project_id=dataset_version_create.project_id,
        dataset_type=dataset_version_create.dataset_type,
        options=dataset_version_create.options
    ))

    for offset in range(0, len(dataset_version_create.dataset_id_list), 1000):
        batch_ids = dataset_version_create.dataset_id_list[offset:offset + 1000]

        datasets = sft_dataset_processor(session, current_user, dataset_version_create.project_id, batch_ids,
                                         dataset_version_create.options)

        try:
            with open(dataset_version_file_path_builder(create_result.id), 'w',
                      encoding='utf-8') as file:
                lines: [str] = []
                for dataset in datasets:
                    lines.append(dataset.json() + "\n")
                file.writelines(lines)
        except IOError as e:
            raise HTTPException(status_code=500,
                                detail=i18n.gettext("I/O error occurred while writing file. error: {error}").format(
                                    error=str(e)))
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=i18n.gettext("Unexpected error occurred. error: {error}").format(
                                    error=str(e)))

    return DatasetVersionItem(
        **create_result.to_dict()
    )


def update_dataset_version(session: Session, current_user: User, id: str,
                           dataset_version_update: DatasetVersionUpdate) -> DatasetVersionItem:
    update_orm = dataset_version_db.update(session, current_user, id, dataset_version_update.dict())
    if update_orm is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Dataset version not found. id: {id}").format(id=id))

    return DatasetVersionItem(
        **update_orm.to_dict()
    )


def delete_dataset_version(session: Session, current_user: User, id: str) -> DatasetVersionItem:
    delete_orm = dataset_version_db.delete(session, current_user, id)
    if delete_orm is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Dataset version not found. id: {id}").format(id=id))

    try:
        os.remove(dataset_version_file_path_builder(id))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("File not found. error: {error}").format(error=str(e)))
    except PermissionError as e:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("No permission to read. error: {error}").format(error=str(e)))
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Unexpected error occurred. error: {error}").format(error=str(e)))

    return DatasetVersionItem(
        **delete_orm.to_dict()
    )
