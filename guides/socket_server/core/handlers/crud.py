from collections.abc import Sequence
from typing import TypeVar, Generic, ClassVar

from sqlalchemy import delete
from sqlmodel import SQLModel, select, update, Session
from sqlmodel.sql.expression import _ColumnExpressionArgument  # noqa

from session import engine

T = TypeVar("T", bound=SQLModel)


class CRUDHandler(Generic[T]):
    _cls: ClassVar[type[SQLModel]] = T

    @classmethod
    def upsert_instance(
            cls,
            *,
            instance: T
    ) -> T:
        assert isinstance(instance, cls._cls)
        with Session(engine) as session:
            session.add(instance)
            session.commit()
            session.refresh(instance)
        return instance

    @classmethod
    def upsert_instances(
            cls,
            *,
            instances: Sequence[T]
    ) -> Sequence[T]:
        assert all(isinstance(instance, cls._cls) for instance in instances)
        with Session(engine) as session:
            session.add_all(instances)
            session.commit()
            for instance in instances:
                session.refresh(instance)
        return instances

    @classmethod
    def read_instances(
            cls,
            *,
            filters: tuple[bool, ...] | None = None
    ) -> Sequence[T]:
        with Session(engine) as session:
            statement = select(cls._cls)
            if filters is not None:
                statement = statement.where(*filters)
            return session.exec(statement=statement).all()

    @classmethod
    def update_instances(
            cls,
            *,
            update_to: T,
            filters: tuple[bool, ...] | None = None
    ) -> None:
        with Session(engine) as session:
            statement = update(cls._cls)
            if filters is not None:
                statement = statement.where(*filters)
            statement = statement.values(**update_to)
            session.execute(statement=statement)
            session.commit()

    @classmethod
    def delete_instances(
            cls,
            filters: tuple[bool, ...]
    ) -> None:
        with Session(engine) as session:
            statement = delete(cls._cls).where(*filters)
            session.execute(statement=statement)
            session.commit()
