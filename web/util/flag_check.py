from hmac import HMAC
import os

def check_flag(checker, flag, info={}):
    scope = info.copy()
    scope['dynamic_flag'] = 'flag{' + HMAC(os.getenv('FLAG_HMAC_KEY').encode(), f"{info['task_id']}|{info['user_id']}".encode(), 'md5').hexdigest() + '}'

    exec(checker, scope)
    res = scope['check'](flag)
    if type(res) == bool:
        return res, None
    else:
        is_correct, msg = res[0], res[1]
        assert type(is_correct) == bool
        return is_correct, msg