import base64, hashlib, hmac, secrets, struct, time
from urllib.parse import quote

def new_secret(): return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
def code(secret:str, timestamp:int|None=None):
    counter=int((timestamp or int(time.time()))/30)
    key=base64.b32decode(secret + "="*((8-len(secret)%8)%8))
    digest=hmac.new(key,struct.pack(">Q",counter),hashlib.sha1).digest()
    offset=digest[-1]&15
    return str((struct.unpack(">I",digest[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
def verify(secret:str,value:str):
    now=int(time.time())
    return any(hmac.compare_digest(code(secret,now+(step*30)),value) for step in (-1,0,1))
def uri(secret:str,email:str): return f"otpauth://totp/Recruta%20IA:{quote(email)}?secret={secret}&issuer=Recruta%20IA&digits=6&period=30"
