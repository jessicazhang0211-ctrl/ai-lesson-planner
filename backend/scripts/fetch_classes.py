import urllib.request
BASE='http://127.0.0.1:5000'
uid=6
req=urllib.request.Request(BASE+f'/api/class/?status=all', headers={'X-User-Id':str(uid)})
with urllib.request.urlopen(req) as resp:
    print(resp.read().decode())
