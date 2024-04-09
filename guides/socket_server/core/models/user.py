import uuid

from sqlmodel import (
    SQLModel,
    Field
)


class User(SQLModel, table=True):
    __tablename__ = 'users'
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=32)
    public_key: bytes = Field()
