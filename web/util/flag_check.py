from hmac import HMAC
from Cryptodome.Cipher import AES
import struct
import os

def gen_flag(key, tid, uid):
    engine = AES.new(key, AES.MODE_ECB)
    plaintext = b'BerryCTF' + struct.pack('II', uid, tid)
    ciphertext = engine.encrypt(plaintext)

    return 'flag{' + ciphertext.hex() + '}'

def check_flag(checker, flag, info={}):
    scope = info.copy()
    scope['dynamic_flag'] = gen_flag(
        os.getenv('FLAG_GEN_KEY').encode(), 
        info['task_id'], 
        info['user_id']
    )

    exec(checker, scope)
    res = scope['check'](flag)
    if type(res) == bool:
        return res, None
    else:
        is_correct, msg = res[0], res[1]
        assert type(is_correct) == bool
        return is_correct, msg