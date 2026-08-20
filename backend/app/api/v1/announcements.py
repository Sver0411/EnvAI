from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization, get_current_user
from app.db.session import get_db
from app.models.tenant import Organization
from app.models.user import User
from app.schemas.commercial import AnnouncementOut
from app.schemas.common import Resp
from app.services.platform_service import active_announcements

router = APIRouter(tags=["announcements"])


@router.get("/announcements/active", response_model=Resp[list[AnnouncementOut]])
def active(db: Session = Depends(get_db), user: User = Depends(get_current_user), org: Organization = Depends(get_current_organization)):
    return Resp(data=[AnnouncementOut.model_validate(x) for x in active_announcements(db, org.id)])

