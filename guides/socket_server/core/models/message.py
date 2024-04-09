import uuid

from sqlmodel import (
    SQLModel,
    Field
)


class Message(SQLModel, table=True):
    __tablename__ = 'messages'
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key='users.id', index=True)
    user_name: str = Field(foreign_key='users.name', index=True)
    content: bytes = Field(default=b'')
