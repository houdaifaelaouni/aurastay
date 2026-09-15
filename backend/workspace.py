from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from typing import Literal
from core import db, Document, iso, uid
from auth import repo
from models import PropertyInput, BlockInput, TeamInput, ExpenseInput, Strict
from finance import date_filter
from availability import acquire, release

router=APIRouter(prefix='/workspace')

async def validate_photos(r, photos, property_id=None):
    for url in photos:
        if url.startswith('/api/media/'):
            record=await r.get('files',url.rsplit('/',1)[-1])
            if record.get('is_deleted') or (property_id and record.get('property_id') not in [None,property_id]):
                raise HTTPException(400,'Photo is unavailable or belongs to another property')

@router.get('/properties',response_model=list[Document])
async def properties(r=Depends(repo)): return await r.list('properties',sort=('created_at',-1))

@router.post('/properties',response_model=Document)
async def add_property(data:PropertyInput,r=Depends(repo)):
    await validate_photos(r,data.photos)
    p=await r.insert('properties',data.model_dump())
    await db.calendars.insert_one({'id':p['id'],'agency_id':p['agency_id'],'slots':[]})
    for url in data.photos:
        if url.startswith('/api/media/'): await r.update('files',url.rsplit('/',1)[-1],{'property_id':p['id']})
    return p

@router.put('/properties/{id}',response_model=Document)
async def edit_property(id:str,data:PropertyInput,r=Depends(repo)):
    old=await r.get('properties',id)
    await validate_photos(r,data.photos,id)
    p=await r.update('properties',id,data.model_dump())
    for url in data.photos:
        if url.startswith('/api/media/'): await r.update('files',url.rsplit('/',1)[-1],{'property_id':id})
    for url in old.get('photos',[]):
        if url.startswith('/api/media/') and url not in data.photos: await r.update('files',url.rsplit('/',1)[-1],{'is_deleted':True})
    return p

@router.get('/properties/{id}/calendar')
async def property_calendar(id:str,r=Depends(repo)):
    await r.get('properties',id)
    return {'blocks':await r.list('blocks',{'property_id':id}), 'reservations':await r.list('bookings',{'property_id':id,'status':{'$in':['confirmed','completed','payment_pending']}})}

@router.post('/properties/{id}/blocks',response_model=Document)
async def add_block(id:str,data:BlockInput,r=Depends(repo)):
    await r.get('properties',id); r.query(write=True)
    bid=uid(); slot={'id':bid,'kind':data.kind,'check_in':data.check_in.isoformat(),'check_out':data.check_out.isoformat()}
    await acquire(id,slot)
    try:
        result=await r.insert('blocks',{**data.model_dump(mode='json'),'property_id':id,'slot_id':bid})
        return result
    except Exception:
        await release(id,bid)
        raise

@router.delete('/blocks/{id}')
async def delete_block(id:str,r=Depends(repo)):
    block=await r.get('blocks',id);r.query(write=True)
    await release(block['property_id'],block['slot_id'])
    return await r.delete('blocks',id)

@router.get('/bookings',response_model=list[Document])
async def bookings(start:date|None=None,end:date|None=None,status:str='',r=Depends(repo)):
    q=date_filter(start,end)
    if status:q['status']=status
    return await r.list('bookings',q,sort=('check_in',-1))

class BookingAction(Strict):
    action:Literal['rent_paid','complete','cancel']
    reason:str=Field(default='',max_length=500)

@router.post('/bookings/{id}/action',response_model=Document)
async def booking_action(id:str,data:BookingAction,r=Depends(repo)):
    b=await r.get('bookings',id);r.query(write=True)
    if b['status'] not in ['confirmed','completed']:raise HTTPException(400,'This reservation cannot be changed')
    if data.action=='rent_paid':return await r.update('bookings',id,{'rental_status':'paid','rental_paid_at':iso()})
    if data.action=='complete':
        if b['check_out']>date.today().isoformat():raise HTTPException(400,'A future stay cannot be marked completed')
        return await r.update('bookings',id,{'status':'completed','completed_at':iso()})
    if b['status']=='completed': raise HTTPException(400,'Completed stays cannot be cancelled')
    if not data.reason.strip():raise HTTPException(400,'A cancellation reason is required')
    await release(b['property_id'],id)
    return await r.update('bookings',id,{'status':'cancelled','cancellation_reason':data.reason,'cancelled_at':iso()})

@router.get('/team',response_model=list[Document])
async def team(r=Depends(repo)):return await r.list('team')

async def validate_assignments(data,r):
    for id in data.property_ids:await r.get('properties',id)

@router.post('/team',response_model=Document)
async def add_team(data:TeamInput,r=Depends(repo)):
    await validate_assignments(data,r)
    return await r.insert('team',data.model_dump())

@router.put('/team/{id}',response_model=Document)
async def edit_team(id:str,data:TeamInput,r=Depends(repo)):
    await r.get('team',id)
    await validate_assignments(data,r)
    return await r.update('team',id,data.model_dump())

@router.get('/expenses',response_model=list[Document])
async def expenses(property_id:str='',category:str='',start:date|None=None,end:date|None=None,r=Depends(repo)):
    q=date_filter(start,end,'date')
    if property_id:q['property_id']=property_id
    if category:q['category']=category
    return await r.list('expenses',q,sort=('date',-1))

@router.post('/expenses',response_model=Document)
async def add_expense(data:ExpenseInput,r=Depends(repo)):
    await r.get('properties',data.property_id)
    return await r.insert('expenses',data.model_dump(mode='json'))

@router.put('/expenses/{id}',response_model=Document)
async def edit_expense(id:str,data:ExpenseInput,r=Depends(repo)):
    await r.get('expenses',id)
    await r.get('properties',data.property_id)
    return await r.update('expenses',id,data.model_dump(mode='json'))

from reports import router as reports_router
router.include_router(reports_router)