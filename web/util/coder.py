import base64
import json

def encode_json_b64(s):
    return base64.b64encode(json.dumps(s).encode()).decode()

def parse_tags(tags):
    if not tags:
        return []

    res = tags.split('|')
    res = [x.strip() for x in res]
    res = [x for x in res if x]
    return res