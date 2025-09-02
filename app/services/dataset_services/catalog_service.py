import json

from sqlalchemy.orm import Session

from app.db.dataset_db_model import catalog_db
from app.db.dataset_db_model.catalog_db import CatalogORM
from app.lib.split.markdown.cores import toc
from app.models.user_model import User


def catalog_to_toc(catalog: list[CatalogORM]) -> str:
    result = ""
    for catalog in catalog:
        toc_content = json.loads(catalog.content)
        result += '# File：' + catalog.file_name + '\n'
        result += toc.toc_to_markdown(toc_content, {"is_nested": True}) + '\n'
    return result


def get_catalog(session: Session, current_user: User, project_id: str) -> str:
    all_catalog = catalog_db.list(session, current_user, project_id)
    return catalog_to_toc(all_catalog)
