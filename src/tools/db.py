from abc import ABC
from typing import List, Union

# from fastapi import HTTPException

import asyncpg
from asyncpg import (
    create_pool,
    Pool,
    Connection,
    Record,
)

# from fastapiplugins.utils import raise_exception
from src.tools.exceptions import (
    get_exception_id,
    ExceptionMessage,
)


import logging


ORIGIN = "DB"


class ConnectionInterface(ABC):
    """Interface to implement for database connections"""

    async def fetch(
        self,
        query: str,
        *args,
        **kwargs,
    ) -> List[dict]:
        """Fetch listed result of query"""
        pass

    async def fetchrow(
        self,
        query: str,
        *args,
        **kwargs,
    ) -> dict:
        """Fetch single result of query"""
        pass


class PostgresConnection(ConnectionInterface):
    """Asyncpg Postgres Connection"""

    def __init__(self, connection: Connection):
        self._wrapped_connection = connection

    async def transaction(self, *args, **kwargs) -> asyncpg.transaction.Transaction:
        return await self._wrapped_connection.transaction(*args, **kwargs)

    async def set_type_codec(self, *args, **kwargs):
        return await self._wrapped_connection.set_type_codec(*args, **kwargs)

    async def execute(self, *args, **kwargs):
        return await self._wrapped_connection.execute(*args, **kwargs)

    async def fetch(
        self,
        query: str,
        *args,
        **kwargs,
    ) -> list:
        return await self._wrapped_connection.fetch(query, *args, **kwargs)

    async def fetchrow(
        self,
        query: str,
        *args,
        **kwargs,
    ) -> Union[dict, None]:
        result: Record = await self._wrapped_connection.fetchrow(query, *args, **kwargs)
        return dict(result) if result else None


class ManagerInterface(ABC):
    """Interface to implemet for managers.
    DatabaseManagers is an entity that manages connections
    and provide same api
    """

    async def get_connection(self) -> ConnectionInterface:
        pass

    async def close_connection(self, connection: ConnectionInterface) -> None:
        pass


class PostgresManager(ManagerInterface):
    """DatabaseManger for Postgres"""

    def __init__(self):
        self.pool: Pool = None

    async def get_connection(self) -> PostgresConnection:
        return PostgresConnection(await self.pool.acquire())

    async def close_connection(self, connection: PostgresConnection) -> None:
        await self.pool.release(connection._wrapped_connection)


class DatabaseConnection:
    """Context manager to handle database managers
    and open/close connections"""

    def __init__(self, engine):
        self._engine = engine
        self._connection = None

    async def __aenter__(self):
        self._connection = await self._engine.get_connection()
        return self._connection

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        await self._engine.close_connection(self._connection)


class PostgresRepository:
    def __init__(self, manager):
        self.manager = manager

    # async def connection(self):
    #     self.manager.

    @classmethod
    def acquire_connection(cls):
        def decoratror(func):
            async def wrapper(self, *args, **kwargs):
                if "conn" in kwargs.keys() or any(
                    filter(lambda x: isinstance(x, DatabaseConnection), args)
                ):
                    return await func(self, *args, **kwargs)
                async with DatabaseConnection(self.manager) as conn:
                    return await func(self, *args, conn=conn, **kwargs)

            return wrapper

        return decoratror


postgres_manager = PostgresManager()


async def init_asyncpg(
    db_name: str,
    db_host: str,
    db_user: str,
    db_password: str,
):
    """Init function to start postgres manager
    (connect to database and create pool)
    """
    postgres_manager.pool = await create_pool(
        database=db_name,
        host=db_host,
        user=db_user,
        password=db_password,
    )
    logging.info(
        f"PostgresManager create postgres pool on:{postgres_manager.pool}",
    )
    return postgres_manager


async def stop_asyncpg():
    """Stop function to stop postgres manager
    (close pool and disconect from database)
    """
    if postgres_manager.pool:
        await postgres_manager.pool.close()
        logging.info(
            f"PostgresManager closed postgres pool on:{postgres_manager.pool}",
        )
    else:
        logging.info(
            "PostgresManager was never started",
        )
    return postgres_manager


# def insert_q(
#     data: dict | BaseModel,
#     datatable: str,
# ) -> Tuple[str, Any]:
#     fields, values = unpack_data(data)
#     query = (
#         f'INSERT INTO \n'
#         f'\t{datatable} \n'
#         f'\t({", ".join(fields)}) \n'
#         f'VALUES \n'
#         f'\t({", ".join( [ f"${i+1}" for i in range(0, len(values)) ])}) \n'
#         f'RETURNING *\n'
#     )
#     return query, *values


# # def condition_constuct(
# #     field: str,
# #     i: int,
# #     value: Any,
# # ) -> str:
# #     if value is None:
# #         return f'{field} is ${i}'
# #     return f'{field} = ${i}'


# def delete_q(
#     datatable: str,
#     **data: dict[Any],
# ) -> Tuple[str, Any]:
#     conditions, values = generate_condidion(
#         data,
#     )
#     query = (
#         f'DELETE FROM\n'
#         f'\t{datatable}\n'
#         f'WHERE\n'
#         f'\t({" AND ".join(conditions)})\n'
#         f'RETURNING *\n'
#     )
#     return query, *values


# def update_q(
#     data: dict | BaseModel,
#     datatable: str,
#     **conditions: dict[Any],
# ) -> Tuple[str, Any]:
#     placeholder, values = generate_placeholder(data)
#     condition, condition_values = generate_condidion(
#         conditions,
#         len(values),
#     )
#     query = (
#         f'UPDATE\n'
#         f'\t{datatable}\n'
#         f'set\n\t{", ".join(placeholder)}\n'
#         f'where\n\t{" AND ".join(condition)}\n'
#         f'returning *\n')
#     return query, *values, *condition_values


# def select_q(
#     datatable: str,
#     ordering: List[str] = None,
#     **data: dict[Any],
# ) -> Tuple[str, Any]:
#     conditions, values = generate_condidion(
#         data,
#     )
#     ordering_str = ""
#     if ordering:
#         ordering_str = f"ORDER BY\n\t{', '.join(ordering)}"
#     sorting_str = ""
#     if data:
#         sorting_str = (
#             f'WHERE\n'
#             f'\t{" and ".join(conditions)}'
#         )
#     query = (
#         f'SELECT *\n'
#         f'FROM\n'
#         f'\t{datatable}\n'
#         f'{sorting_str}\n'
#         f'{ordering_str}\n'
#     )
#     return query, *values


# def select_q_detailed(
#     datatable: str,
#     model: dict | BaseModel,
#     ordering: List[str] = None,
#     **data: dict[Any],
# ) -> Tuple[str, Any]:
#     conditions, values = generate_condidion(data)
#     fields = get_fields(model)
#     ordering_str = ""
#     if ordering:
#         ordering_str = f"ORDER BY\n\t{', '.join(ordering)}"
#     sorting_str = ""
#     if data:
#         sorting_str = (
#             f'WHERE\n'
#             f'\t{" and ".join(conditions)}'
#         )
#     query = (
#         f'SELECT\n'
#         f'\t{", ".join(fields)}\n'
#         f'FROM\n'
#         f'\t{datatable}\n'
#         f'{sorting_str}\n'
#         f'{ordering_str}\n'
#     )
#     return query, *values


# def unpack_data(data: dict | BaseModel) -> tuple[list, list]:
#     if isinstance(data, BaseModel):
#         data = data.model_dump()
#     # if isinstance(data, dict):
#     fields = list(data.keys())
#     values = list(data.values())
#     # return fields, values
#     # fields = list(data.)
#     # values = list(data.__dict__.values())
#     assert len(fields) == len(values)
#     return fields, values


# def generate_placeholder(
#     data: dict | BaseModel,
#     i: int = 0,
# ) -> tuple[list]:
#     """
#         returns pairs like 'field_name = $1'
#         and values
#     """
#     fields, values = unpack_data(data)
#     pair = []
#     for field in fields:
#         i += 1
#         pair.append(f'{field} = ${i}')
#     return pair, values


# def generate_condidion(
#     data: dict | BaseModel,
#     i: int = 0,
#     # pair_construct:
#     # Callable[[str, int, Any], str] = lambda field, i, value: f'{field} = ${i}'
# ) -> tuple[list]:
#     """
#         returns pairs like 'field_name = $1'
#         and values
#     """
#     fields, values = unpack_data(data)
#     pair = []
#     for field, value in zip(fields, values.copy()):
#         if value is None:
#             pair.append(f'{field} is null')
#             values.remove(None)
#         else:
#             i += 1
#             pair.append(f'{field} = ${i}')
#             # pair.append(pair_construct(field, i, value))
#     return pair, values


# def validate(func):
#     async def wrapper(*args, **kwargs):
#         await args[0].validate_()
#         return await func(*args, **kwargs)
#     return wrapper


# def get_fields(model):
#     return model.__fields__.keys()


class NoDataException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


exceptions = {
    NoDataException: ExceptionMessage(
        id=get_exception_id(f"{ORIGIN}_GENERIC", "noqueryresult"),
        status=404,
        title="controllers: No result from sql query",
    ),
    asyncpg.exceptions.UniqueViolationError:
    # ExceptionMessage(
    #     id=get_exception_id(ORIGIN, 'uniqueviolationerror'),
    #     status=422,
    #     title="postgres: UniqueViolationError",
    # ),
    ExceptionMessage(
        id=get_exception_id(ORIGIN, "uniqueviolationerror"),
        status=1000,
        title="postgres: UniqueViolationError",
        update_func=lambda self, r, e: setattr(self, "short", e.detail),
    ),
    asyncpg.exceptions.ForeignKeyViolationError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "foreignkeyviolationerror"),
        status=422,
        title="postgres: ForeignKeyViolationError",
    ),
    asyncpg.exceptions.NotNullViolationError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "notnullviolationerror"),
        status=422,
        title="postgres: NotNullViolationError",
    ),
    asyncpg.exceptions.CheckViolationError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "checkviolationerror"),
        status=422,
        title="postgres: CheckViolationError",
    ),
    asyncpg.exceptions.RestrictViolationError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "restrictviolationerror"),
        status=422,
        title="postgres: RestrictViolationError",
    ),
    asyncpg.exceptions.ExclusionViolationError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "exclusionviolationerror"),
        status=422,
        title="postgres: ExclusionViolationError",
    ),
    asyncpg.exceptions.InvalidForeignKeyError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "invalidforeignkeyerror"),
        status=422,
        title="postgres: InvalidForeignKeyError",
    ),
    asyncpg.exceptions.NameTooLongError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "nametoolongerror"),
        status=422,
        title="postgres: NameTooLongError",
    ),
    asyncpg.exceptions.DuplicateColumnError: ExceptionMessage(
        id=get_exception_id(ORIGIN, "duplicatecolumnerroror"),
        status=422,
        title="postgres: DuplicateColumnErroror",
    ),
}
