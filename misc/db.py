import json
import logging
from decimal import Decimal
from itertools import zip_longest
from typing import (
    Any,
    Type,
    TypeVar,
    Callable,
    Mapping
)

import asyncpg
from pydantic import BaseModel

from misc.config import PostgresqlConfig

logger = logging.getLogger(__name__)

Connection = asyncpg.Connection
Pool = asyncpg.Pool
ModelCls = TypeVar('ModelCls', bound=BaseModel)


async def init(config: PostgresqlConfig) -> Pool:
    dsn = config.dsn
    if not dsn:
        raise RuntimeError('DB connection parameters not defined')
    return await asyncpg.create_pool(
        dsn,
        init=init_connection,
        **{k: v for k, v in config.model_dump().items() if k != 'dsn'}
    )


async def get_conn(config: PostgresqlConfig) -> Connection:
    dsn = config.dsn
    if not dsn:
        raise RuntimeError('DB connection parameters not defined')
    return await asyncpg.connect(dsn, **config.model_dump(exclude={'dsn'}))


async def close(db: Pool | Connection):
    await db.close()


async def init_connection(conn):
    await conn.set_type_codec(
        'jsonb',
        encoder=encode_json,
        decoder=json.loads,
        schema='pg_catalog'
    )
    return conn


def record_to_model_list(
        model_cls: Type[ModelCls],
        records: list[Mapping | BaseModel]
) -> list[ModelCls]:
    if records:
        return list(
            map(
                lambda x: record_to_model(
                    model_cls,
                    x
                ),
                records
            )
        )
    return []


def record_to_model(
        model_cls: Type[ModelCls],
        record: Mapping | BaseModel | None
) -> ModelCls | None:
    if record:
        return model_cls.model_validate(dict(record))
    return None


async def record_to_model_list_custom(
        conn: Connection,
        records: list[Mapping | BaseModel],
        record_to_model_func: Callable,
        **kwargs
) -> list:
    return [await record_to_model_func(conn=conn, record=r, **kwargs) for r in records if r]


async def get(
        conn: Connection,
        table: str,
        pk: int,
        fields: list[str] | None = None
) -> asyncpg.Record | None:
    select_fields = ', '.join(fields) if fields else '*'
    query = f'SELECT {select_fields} FROM {table} WHERE id = $1'
    try:
        return await conn.fetchrow(query, pk)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def get_by_where(
        conn: Connection,
        table: str,
        where: str,
        values: list | None = None,
        fields: list[str] | None = None,
        return_rows: bool = False
) -> asyncpg.Record | list[asyncpg.Record] | None:
    if values is None:
        values = []

    select_fields = ', '.join(fields) if fields else '*'
    query = f'SELECT {select_fields} FROM {table} WHERE {where}'
    if return_rows:
        execute = conn.fetch
    else:
        execute = conn.fetchrow
    try:
        return await execute(query, *values)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def get_list(
        conn: Connection,
        table: str,
        where: str | None = None,
        values: list | None = None,
        limit: int | None = None,
        page: int | None = None,
        order: list[str] | None = None,
        group: list[str] | None = None,
        fields: list[str] | None = None,
) -> list[asyncpg.Record]:
    if values is None:
        values = []

    select_fields = ', '.join(fields) if fields else '*'
    where_query, limit_query, offset_query, order_query, group_query = '', '', '', '', ''
    if where:
        where_query = f'WHERE {where}'
    if limit:
        limit_query = f'LIMIT {limit}'
    if page:
        offset_query = f'OFFSET {(page - 1) * limit}'
    if order:
        order_query = 'ORDER BY ' + ', '.join([f'{i[1:]} DESC' if i.startswith('-') else i for i in order])
    if group:
        group_query = f"GROUP BY {','.join(group)}"

    query = f'''
        SELECT 
            {select_fields} 
        FROM {table} {where_query} {order_query} {group_query} {limit_query} {offset_query}'''
    try:
        return await conn.fetch(query, *values)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def get_total(
        conn: Connection,
        table: str,
        where: str | None = None,
        values: list | None = None,
        group_by: list[str] | None = None
) -> int:
    if values is None:
        values = []

    where_query = ''
    if where:
        where_query = f'WHERE {where}'
    if group_by:
        f"GROUP BY {','.join(group_by)}"
    query = f'SELECT count(*) as count FROM {table} {where_query}'
    try:
        result = await conn.fetchrow(query, *values)
        return result['count']
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def exists(
        conn: Connection,
        table: str,
        where: str | None = None,
        values: list | None = None
) -> bool:
    where_query = ''
    if where:
        where_query = f"WHERE {where}"
    query = f"SELECT * FROM {table} {where_query}"
    try:
        return bool(await conn.fetchrow(
            query,
            *values
        ))
    except Exception:
        logger.exception(f"Query {query} failed")
        raise


async def create(
        conn: Connection,
        table: str,
        data: dict[str, Any],
        insert_fields: list[str] | None = None,
        ignore_fields: list[str] | None = None,
        fields: list[str] | None = None
) -> asyncpg.Record | None:
    return_fields = ', '.join(fields) if fields else '*'
    field_names = []
    placeholders = []
    values = []
    idx = 1
    for key in data.keys():
        if insert_fields and key not in insert_fields:
            continue

        if ignore_fields and key in ignore_fields:
            continue

        field_names.append(key)
        placeholders.append(f"${idx}")
        values.append(data[key])
        idx += 1

    query = f'''
        INSERT INTO {table} ({", ".join(field_names)}) 
        VALUES ({", ".join(placeholders)}) RETURNING {return_fields}'''
    try:
        return await conn.fetchrow(query, *values)
    except Exception:
        logger.exception(f'Query {query} with values {values} failed')
        raise


async def create_many(
        conn: Connection,
        table: str,
        data: list[dict],
        insert_fields: list[str] | None = None
) -> None:
    """Creates a list of objects in database"""
    if not data:
        return

    values = []
    insert_fields = insert_fields if insert_fields else [field for field in data[0]]
    for item in data:
        item_values = []
        for field in insert_fields:
            item_values.append(item.get(field))
        values.append(item_values)
    str_insert_fields = ", ".join(insert_fields)
    placeholders = ", ".join([f"${i + 1}" for i in range(len(insert_fields))])
    query = f'INSERT INTO {table} ({str_insert_fields}) VALUES ({placeholders})'
    try:
        await conn.executemany(query, values)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def create_list(
        conn: Connection,
        table: str,
        data: dict[str, list[Any]],
        fillvalue: Any = None,
        fields: list[str] | None = None,
) -> list[asyncpg.Record] | None:
    # Добавляет несколько значений в БД за раз
    # Значения передаются в словаре, ключ - список (длины списков должны совпадать)
    # fillvalue - значение, которым будет заполнятся список, если длины списков не совпадают.

    idx = 1
    val = []
    group_values = list(zip_longest(*data.values(), fillvalue=fillvalue))
    values = []
    for value in group_values:
        placeholders = []
        for item in value:
            values.append(item)
            placeholders.append(f'${idx}')
            idx += 1
        val.append(f'({", ".join(placeholders)})')
    query = f'''
        INSERT INTO {table} ({", ".join(data.keys())}) 
        VALUES {", ".join(val)} 
        RETURNING {", ".join(fields) if fields else "*"}'''
    try:
        return await conn.fetch(query, *values)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def update(
        conn: Connection,
        table: str,
        pk: int,
        data: dict[str, Any],
        update_fields: list[str] | None = None,
        ignore_fields: list[str] | None = None,
        fields: list[str] | None = None,
        with_atime: bool = False
) -> asyncpg.Record | None:
    if not data:
        return
    return_fields = ', '.join(fields) if fields else '*'
    placeholders = []
    values = []
    idx = 1
    for key in data.keys():
        if with_atime and key == 'atime':
            continue

        if update_fields and key not in update_fields:
            continue

        if ignore_fields and key in ignore_fields:
            continue

        placeholders.append(f"{key} = ${idx}")
        values.append(data[key])
        idx += 1
    if with_atime:
        placeholders.append("atime = (now() at time zone 'utc')")
    upd = ', '.join(placeholders)
    query = f'UPDATE {table} SET {upd} WHERE id = ${len(values) + 1} RETURNING {return_fields}'
    values.append(pk)
    try:
        return await conn.fetchrow(query, *values)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def update_by_where(
        conn: Connection,
        table: str,
        data: dict[str, Any],
        where: str,
        values: list | None = None,
        update_fields: list[str] | None = None,
        ignore_fields: list[str] | None = None,
        fields: list[str] | None = None,
        with_atime: bool = False,
        return_rows: bool = False
) -> asyncpg.Record | None:
    if values is None:
        values = []

    return_fields = ', '.join(fields) if fields else '*'
    placeholders = []
    update_values = []
    idx = len(values) + 1
    for key in data.keys():
        if with_atime and key == 'atime':
            continue

        if update_fields and key not in update_fields:
            continue

        if ignore_fields and key in ignore_fields:
            continue

        placeholders.append(f"{key} = ${idx}")
        update_values.append(data[key])
        idx += 1
    if with_atime:
        placeholders.append("atime = (now() at time zone 'utc')")
    upd = ', '.join(placeholders)
    values.extend(update_values)
    query = f'UPDATE {table} SET {upd} WHERE {where} RETURNING {return_fields}'

    execute = conn.fetchrow

    if return_rows:
        execute = conn.fetch

    try:
        return await execute(query, *values)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def disable_by_where(
        conn: Connection,
        table: str,
        pk: int,
        data: dict[str, Any] | None = None,
        with_dtime: bool = False
) -> asyncpg.Record | None:
    values = [pk]
    wheres = ["id = $1"]
    idx = 2
    if data:
        for k in data:
            values.append(data[k])
            wheres.append(f"{k} = ${idx}")
            idx += 1
    query = f"""
            UPDATE {table} 
            SET en = false 
            {",dtime = (now() at time zone 'utc')" if with_dtime is True else ""} 
            {"WHERE " + " AND ".join(wheres) if wheres else ""}
            RETURNING *
    """
    try:
        return await conn.fetchrow(
            query,
            *values
        )
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def delete_by_where(
        conn: Connection,
        table: str,
        where: str,
        values: list | None = None,
        fields: list[str] | None = None,
        return_rows: bool = False
) -> asyncpg.Record | None:
    values = values if values else []
    return_fields = ', '.join(fields) if fields else '*'
    query = f'DELETE FROM {table} WHERE {where} RETURNING {return_fields}'
    if return_rows:
        execute = conn.fetch
    else:
        execute = conn.fetchrow
    try:
        return await execute(query, *values)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


async def delete(
        conn: Connection,
        table: str,
        pk: int,
        fields: list[str] | None = None
) -> asyncpg.Record | None:
    return_fields = ', '.join(fields) if fields else '*'
    query = f'DELETE FROM {table} WHERE id = $1 RETURNING {return_fields}'
    try:
        return await conn.fetchrow(query, pk)
    except Exception:
        logger.exception(f'Query {query} failed')
        raise


def json_default_encoder(obj):
    if isinstance(obj, Decimal):
        return str(obj)


def encode_json(value: Any) -> str:
    return json.dumps(value, default=json_default_encoder)


def chain_filters(
        filters: list, values: list,
        *chained_filters
) -> tuple[list, list]:
    for f in chained_filters:
        func, *args = f
        filters, values = func(*args, filters, values)
    return filters, values


def equal_filter(
        field: str,
        value: int | str | float | Decimal | list | None,
        filters: list,
        values: list
) -> tuple[list, list]:
    start_idx = get_start_idx(values)
    if value is not None:
        if isinstance(value, (list, tuple)):
            filters.append(f'{field} = ANY(${start_idx})')
            values.append(list(value))
        else:
            filters.append(f'{field} = ${start_idx}')
            values.append(value)
    return filters, values


def between_filter(
        field: str,
        value_from: int | str | float | Decimal | list | None,
        value_to: int | str | float | Decimal | list | None,
        filters: list,
        values: list
) -> tuple[list, list]:
    start_idx = get_start_idx(values)
    if value_from and value_to:
        if value_from > value_to:
            value_from, value_to = value_to, value_from
        filters.append(f'{field} BETWEEN ${start_idx} AND ${start_idx + 1}')
        values.append(value_from)
        values.append(value_to)
    elif value_from:
        filters.append(f'{field} >= ${start_idx}')
        values.append(value_from)
    elif value_to:
        filters.append(f'{field} <= ${start_idx}')
        values.append(value_to)

    return filters, values


def lte_filter(
        field: str,
        value: int | str | float | Decimal | None,
        filters: list,
        values: list
) -> tuple[list, list]:
    start_idx = get_start_idx(values)
    if value:
        filters.append(f'{field} <= ${start_idx}')
        values.append(value)
    return filters, values


def gte_filter(
        field: str,
        value: int | str | float | Decimal | None,
        filters: list,
        values: list
) -> tuple[list, list]:
    start_idx = get_start_idx(values)
    if value:
        filters.append(f'{field} >= ${start_idx}')
        values.append(value)
    return filters, values


def startswith_filter(
        field: str,
        value: str | None,
        filters: list,
        values: list
) -> tuple[list, list]:
    start_idx = get_start_idx(values)
    if value:
        filters.append(f'{field} ILIKE ${start_idx}')
        values.append(f"{value}%")
    return filters, values


def is_blank_filter(
        field: str,
        value: bool | None,
        filters: list,
        values: list
) -> tuple[list, list]:
    if value:
        filters.append(f"({field} is NULL or {field} = '')")
    return filters, values


def is_null_filter(
        field: str,
        value: bool | None,
        filters: list,
        values: list
) -> tuple[list, list]:
    if value:
        filters.append(f"{field} is NULL")
    return filters, values


def get_start_idx(values: list) -> int:
    return len(values) + 1


async def check_exist(
        conn: Connection,
        table: str,
        pk: int
) -> bool:
    return bool(await conn.fetchrow(f"SELECT * FROM {table} WHERE id = $1", pk))


def build_params(
        data: list[tuple[str, Any]],
        wheres: list[str],
        values: list[Any],
        arg_count: int = 1,
) -> tuple[list[str], list[Any]]:
    if data:
        logger.info(data[arg_count:])
        field_name, value = data[:arg_count][0]
        wheres.append(f"{field_name} = ${arg_count}")
        values.append(value)
        return build_params(data[arg_count:], wheres, values, arg_count + 1)
    return wheres, values
