from flask import Blueprint, abort, send_from_directory
from util.db import db_pool

bp = Blueprint('file', __name__, url_prefix='/files')


@bp.route('/<string:key>/<string:filename>')
def send_file(key, filename):
    with db_pool.connection() as conn:
        file = conn.execute('SELECT * FROM file WHERE download_key = %s', [key]).fetchone()
    
    if not file:
        abort(404)
    
    return send_from_directory('upload', key, as_attachment=True, download_name=filename)
