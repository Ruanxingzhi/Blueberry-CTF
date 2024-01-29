from flask import current_app
from util.db import db_pool
from datetime import datetime

def refresh_config():
    with db_pool.connection() as conn:
        for row in conn.execute('SELECT config_key, config_value FROM site_config').fetchall():
            k, v = row['config_key'].upper(), row['config_value']

            if k.endswith('_TIME'):
                try:
                    v = datetime.strptime(v, "%B %d, %Y %I:%M %p")
                except Exception:
                    v = None

            current_app.config[k] = v
            # print('config:', k, '=', v)
