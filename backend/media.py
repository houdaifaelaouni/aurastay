import os
import asyncio
import httpx
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response, Request
from core import db,uid,iso
from auth import repo,current_user
from fastapi.security import HTTPAuthorizationCredentials

router=APIRouter()

# Use local storage fallback if emergent integration is not configured
USE_EMERGENT_STORAGE = bool(os.environ.get('EMERGENT_LLM_KEY') and os.environ.get('INTEGRATION_PROXY_URL'))
STORAGE_BASE=(os.environ.get('INTEGRATION_PROXY_URL') or '').strip() or 'https://integrations.emergentagent.com'
STORAGE_URL=STORAGE_BASE.rstrip('/')+'/objstore/api/v1/storage'
storage_key=None
lock=asyncio.Lock()

async def storage_request(method,path,content=None,content_type=None):
    if not USE_EMERGENT_STORAGE:
        raise HTTPException(503, 'Storage service not configured. Set EMERGENT_LLM_KEY and INTEGRATION_PROXY_URL.')
    global storage_key
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(2):
            async with lock:
                if not storage_key:
                    init=await client.post(STORAGE_URL+'/init',json={'emergent_key':os.environ['EMERGENT_LLM_KEY']})
                    init.raise_for_status();storage_key=init.json()['storage_key']
            response=await client.request(method,STORAGE_URL+'/objects/'+path,content=content,headers={'X-Storage-Key':storage_key,'Content-Type':content_type or 'application/octet-stream'})
            if response.status_code==404 and attempt==0:storage_key=None;continue
            response.raise_for_status();return response

@router.post('/workspace/photos')
async def upload_photo(file:UploadFile=File(...),r=Depends(repo)):
    r.query(write=True)
    content=await file.read(8*1024*1024+1)
    if len(content)>8*1024*1024:raise HTTPException(413,'Images must be smaller than 8 MB')
    if content.startswith(b'\xff\xd8\xff'):kind,ext='image/jpeg','jpg'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'):kind,ext='image/png','png'
    elif content[:4]==b'RIFF' and content[8:12]==b'WEBP':kind,ext='image/webp','webp'
    else:raise HTTPException(400,'Choose a JPEG, PNG or WebP image')
    path=f'aurastay/uploads/{r.p["agency_id"]}/{uid()}.{ext}'
    try:response=await storage_request('PUT',path,content,kind)
    except Exception:raise HTTPException(503,'Photo storage is temporarily unavailable. Please try again.')
    record=await r.insert('files',{'storage_path':response.json()['path'],'original_filename':file.filename,'content_type':kind,'size':len(content),'is_deleted':False,'property_id':None})
    return {'id':record['id'],'url':'/api/media/'+record['id']}

@router.get('/media/{id}')
async def photo(id:str,request:Request):
    record=await db.files.find_one({'id':id,'is_deleted':False},{'_id':0})
    if not record:raise HTTPException(404,'Photo not found')
    prop=await db.properties.find_one({'id':record.get('property_id'),'status':'published','photos':f'/api/media/{id}'},{'_id':0,'agency_id':1})
    active=prop and await db.agencies.find_one({'id':prop['agency_id'],'active':True},{'_id':0,'id':1})
    if not active:
        header=request.headers.get('Authorization','')
        if not header.startswith('Bearer '):raise HTTPException(404,'Photo not found')
        user=await current_user(HTTPAuthorizationCredentials(scheme='Bearer',credentials=header[7:]),request.headers.get('X-Agency-Id'))
        if user.get('agency_id')!=record['agency_id']:raise HTTPException(404,'Photo not found')
    try:response=await storage_request('GET',record['storage_path'])
    except Exception:raise HTTPException(503,'Photo is temporarily unavailable')
    return Response(content=response.content,media_type=record['content_type'],headers={'Cache-Control':'private, no-cache','X-Content-Type-Options':'nosniff'})