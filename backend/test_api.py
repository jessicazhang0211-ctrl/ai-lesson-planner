import json
import urllib.request

BASE='http://127.0.0.1:5000'

def post(path, data, headers=None):
    data_bytes = json.dumps(data).encode('utf-8')
    hdrs = {'Content-Type':'application/json'}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(BASE+path, data=data_bytes, headers=hdrs)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode('utf-8')
    except urllib.error.HTTPError as he:
        body = he.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f'HTTP {he.code}: {body}')

try:
    print('1) login user (or register if missing)')
    try:
        r = json.loads(post('/api/auth/login', {'email':'teacher@example.test','password':'pass123'}))
        print('login ok')
        print(json.dumps(r, ensure_ascii=False, indent=2))
        uid = r['data']['user']['id']
    except Exception:
        r = json.loads(post('/api/auth/register', {'name':'Teacher','email':'teacher@example.test','password':'pass123'}))
        print('registered')
        print(json.dumps(r, ensure_ascii=False, indent=2))
        uid = r['data']['user']['id']

    print('\n2) create class')
    cls = json.loads(post('/api/class/', {'name':'一年级（1）班','desc':'数学基础'}, headers={'X-User-Id':str(uid)}))
    print(json.dumps(cls, ensure_ascii=False, indent=2))
    # find code by querying class list
    print('\n3) list classes for user')
    req = urllib.request.Request(BASE+'/api/class/?status=all', headers={'X-User-Id':str(uid)})
    with urllib.request.urlopen(req) as resp:
        lst = json.loads(resp.read().decode())
    print(json.dumps(lst, ensure_ascii=False, indent=2))
    if isinstance(lst, dict) and lst.get('data'):
        classes = lst['data']
    else:
        classes = lst
    if classes:
        code = classes[0].get('code')
        cid = classes[0].get('id')
    else:
        print('no classes found')
        raise SystemExit(1)

    print('\n4) join by code (student Alice)')
    joined = json.loads(post('/api/class/join', {'code':code,'name':'Alice','stu_id':'202601001','parent_phone':'13888880001'}))
    print(json.dumps(joined, ensure_ascii=False, indent=2))

    print('\n5) get class detail')
    req = urllib.request.Request(BASE+f'/api/class/{cid}', headers={'X-User-Id':str(uid)})
    with urllib.request.urlopen(req) as resp:
        detail = json.loads(resp.read().decode())
    print(json.dumps(detail, ensure_ascii=False, indent=2))

except Exception as e:
    print('ERROR:', e)
    import traceback; traceback.print_exc()
