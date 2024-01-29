from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from util.env import env

db_pool = ConnectionPool(
    env('PGSQL_URI'),
    # min_size=1,
    kwargs={'row_factory': dict_row})
