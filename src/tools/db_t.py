import logging

from typing import List, Union

from asyncpg import (
    create_pool,
    Pool,
    Connection,
    Record,
)


from src.tools.db import (
    ConnectionInterface,
    ManagerInterface,
    DatabaseConnection,
)


class TestPostgresConnection(ConnectionInterface):
    """Test asyncpg Postgres Connection"""

    def __init__(self, connection: Connection):
        self._wrapped_connection = connection

    async def set_type_codec(self, *args, **kwargs):
        return await self._wrapped_connection.set_type_codec(*args, **kwargs)

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


class TestPostgresManager(ManagerInterface):
    """DatabaseManger for Postgres"""

    def __init__(self, query_init_file: str):
        with open(query_init_file, "r") as file:
            init_query = file.read()

        self.pool: Pool = None
        self.setup_query = init_query
        self.drop_query = """
           DO $$ DECLARE
                obj RECORD;
            BEGIN
                -- Drop tables
                FOR obj IN (
                    SELECT tablename AS name FROM pg_tables
                    WHERE schemaname = 'public'
                ) LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || obj.name || ' CASCADE';
                END LOOP;

                -- Drop sequences
                FOR obj IN (
                    SELECT sequencename AS name FROM pg_sequences
                    WHERE schemaname = 'public'
                ) LOOP
                    EXECUTE 'DROP SEQUENCE IF EXISTS ' || obj.name || ' CASCADE';
                END LOOP;

                -- Drop other objects
                FOR obj IN (
                    SELECT oid::regclass::text AS name FROM pg_class
                    WHERE relnamespace = 'public'::regnamespace AND relkind IN ('i', 'S')
                ) LOOP
                    EXECUTE 'DROP INDEX IF EXISTS ' || obj.name;
                END LOOP;

                -- Drop domains
                FOR obj IN (
                    SELECT domain_name AS name FROM information_schema.domains
                    WHERE domain_schema = 'public'
                ) LOOP
                    EXECUTE 'DROP DOMAIN IF EXISTS ' || obj.name || ' CASCADE';
                END LOOP;
            END;
            $$;
        """
        self.clean_query = """
            DO $$ DECLARE
                obj RECORD;
            BEGIN
                -- Disable triggers temporarily
                EXECUTE 'SET session_replication_role = replica';

                -- Truncate all tables
                FOR obj IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE format('TRUNCATE TABLE public.%I RESTART IDENTITY CASCADE', obj.tablename);
                END LOOP;

                -- Enable triggers back
                EXECUTE 'SET session_replication_role = DEFAULT';
            END $$;
        """

    async def cleanup(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(self.clean_query)

    async def setup(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(self.setup_query)

    async def reset(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(self.drop_query)
        await self.setup()

    async def get_connection(self) -> TestPostgresConnection:
        return TestPostgresConnection(await self.pool.acquire())

    async def close_connection(self, connection: TestPostgresConnection) -> None:
        await self.pool.release(connection._wrapped_connection)


test_postgres_manager = TestPostgresManager("sql.sql")


async def init_tets_postgres(
    db_name: str,
    db_host: str,
    db_user: str,
    db_password: str,
):
    """Init function to start postgres manager
    (connect to database and create pool)
    """
    test_postgres_manager.pool = await create_pool(
        database=db_name,
        host=db_host,
        user=db_user,
        password=db_password,
    )
    logging.info(
        f"TestPostgresManager create testing postgres pool on:{test_postgres_manager.pool}",
    )
    return test_postgres_manager


async def stop_test_asyncpg():
    """Stop function to stop postgres manager
    (close pool and disconect from database)
    """
    if test_postgres_manager.pool:
        await test_postgres_manager.pool.close()
        logging.info(
            f"TestPostgresManager closed test postgres pool on:{test_postgres_manager.pool}",
        )
    else:
        logging.info(
            "TestPostgresManager was never started",
        )
    return test_postgres_manager
