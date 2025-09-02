from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.llamafactory_db_model import release_db
from app.lib.i18n.config import i18n
from app.models.llamafactory_models.release_model import ReleaseList, ReleaseUpdate, ReleaseItem
from app.models.user_model import User


def list_release(session: Session, current_user: User, page_no: int, page_size: int, name: str = None,
                 finetune_type: str = None) -> ReleaseList:
    releases, total = release_db.list_releases(session, current_user, page_no, page_size, name, finetune_type)

    items = [ReleaseItem(**release_orm.to_dict()) for release_orm in releases]

    for item in items:
        # todo search deploy
        pass

    return ReleaseList(
        data=items,
        count=total
    )


def update_release(session: Session, current_user: User, id: str, update: ReleaseUpdate) -> ReleaseItem:
    update_orm = release_db.update_release(session, current_user, id, update.dict())
    if update_orm is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Finetune release not found. {id}").format(id=id))

    return ReleaseItem(
        **update_orm.to_dict()
    )
