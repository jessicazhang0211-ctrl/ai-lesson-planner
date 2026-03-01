import urllib.request
BASE='http://127.0.0.1:5000'
uid=6
url = BASE+f'/api/class/3/students/5/reset-password'
req = urllib.request.Request(url, data=b'{}', headers={'X-User-Id':str(uid), 'Content-Type':'application/json'}, method='POST')
with urllib.request.urlopen(req) as resp:
    print(resp.read().decode())
