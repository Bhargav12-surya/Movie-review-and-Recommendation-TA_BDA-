"""Bound body buffering and local process rate limits, without logging bodies."""
from collections import OrderedDict
import time
from starlette.responses import JSONResponse

class BoundsMiddleware:
    def __init__(self,app,maximum_bytes,requests_per_minute):
        self.app=app;self.maximum=maximum_bytes;self.limit=requests_per_minute;self.windows=OrderedDict()
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        now=time.monotonic();client=(scope.get('client') or ('unknown',0))[0]
        auth=scope.get('path','').startswith('/api/v1/auth/')
        key=(client,auth);start,count=self.windows.get(key,(now,0))
        if now-start>=60:start,count=now,0
        limit=10 if auth else self.limit
        self.windows[key]=(start,count+1);self.windows.move_to_end(key)
        while len(self.windows)>1000:self.windows.popitem(last=False)
        if count>=limit:return await JSONResponse({'error':{'code':'rate_limit_exceeded'}},429,headers={'Retry-After':'60'})(scope,receive,send)
        parts=[];total=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect': return
            data=message.get('body',b'');total+=len(data)
            if total>self.maximum:return await JSONResponse({'error':{'code':'request_too_large'}},413)(scope,receive,send)
            parts.append(data)
            if not message.get('more_body',False):break
        body=b''.join(parts);sent=False
        async def replay():
            nonlocal sent
            if not sent:sent=True;return {'type':'http.request','body':body,'more_body':False}
            return await receive()
        async def safe_send(message):
            if message['type']=='http.response.start':
                message['headers']=list(message.get('headers',[]))+[(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')]
            await send(message)
        await self.app(scope,replay,safe_send)
