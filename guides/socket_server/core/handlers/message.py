from core.handlers.crud import CRUDHandler
from core.models import Message


class MessageHandler(CRUDHandler[Message]):
    _cls = Message
