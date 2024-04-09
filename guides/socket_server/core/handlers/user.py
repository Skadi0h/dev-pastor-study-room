from core.handlers.crud import CRUDHandler
from core.models import User


class UserHandler(CRUDHandler[User]):
    _cls = User
