import os
import secrets
import time

pgsql_passwd = secrets.token_urlsafe(16)

compose = open(os.path.join('conf', 'template-pgsql-compose.yml')).read()
compose = compose.replace('$PGSQL_PASSWORD$', pgsql_passwd)
open(os.path.join('pgsql', 'docker-compose.yml'), 'w').write(compose)

os.chdir('pgsql')
os.system('docker-compose down -t 0')
os.system('rm -rf pgsql_data')

os.system('docker-compose up -d')
os.chdir('..')

print('DB init ok. sleep 10s.')

time.sleep(10)

env = open(os.path.join('conf', 'template.env')).read()
env = env.replace('$PGSQL_PASSWORD$', pgsql_passwd)
env = env.replace('$SECRET_KEY$', secrets.token_urlsafe(16))
env = env.replace('$FLAG_GEN_KEY$', secrets.token_hex(8))
open(os.path.join('web', '.env'), 'w').write(env)

os.chdir('web')

os.system('flask erase-db')
os.system('flask init-db')