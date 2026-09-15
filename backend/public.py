import re
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from core import db
from models import QuoteInput, BookingInput
from finance import calculate, fee_settings
from availability import available, overlap

router=APIRouter()
PUBLIC_FIELDS={k:1 for k in ['id','agency_id','name','city','country','type','category','description','price','guests','bedrooms','bathrooms','amenities','photos','services','sample']}
PUBLIC_FIELDS['_id']=0

async def published_property(id):
    p=await db.properties.find_one({'id':id,'status':'published'},PUBLIC_FIELDS)
    if not p: raise HTTPException(404,'This stay is not available')
    agency=await db.agencies.find_one({'id':p['agency_id'],'active':True},{'_id':0,'name':1,'email':1,'phone':1,'payment_instructions':1})
    if not agency: raise HTTPException(404,'This stay is not available')
    p['agency']=agency
    p.pop('_id', None)
    return p

@router.get('/properties')
async def catalogue(destination:str='', check_in:date|None=None, check_out:date|None=None,
                    guests:int=Query(1,ge=1,le=50), max_price:float=Query(100000,gt=0),
                    amenities:str='', category:str='', sort:str='recommended'):
    if bool(check_in)!=bool(check_out): raise HTTPException(400,'Choose both check-in and check-out dates')
    if check_in and (check_out<=check_in or check_in<date.today()): raise HTTPException(400,'Please choose valid future dates')
    active=await db.agencies.find({'active':True},{'_id':0,'id':1,'name':1}).to_list(10000)
    names={a['id']:a['name'] for a in active}
    q={'status':'published','agency_id':{'$in':list(names)},'guests':{'$gte':guests},'price':{'$lte':max_price}}
    if destination: q['$or']=[{key:{'$regex':re.escape(destination.strip()),'$options':'i'}} for key in ['name','city','country']]
    if category: q['category']=category
    if amenities: q['amenities']={'$all':[a for a in amenities.split(',') if a]}
    if check_in:
        blocked=await db.calendars.find({'slots':{'$elemMatch':overlap(check_in.isoformat(),check_out.isoformat())}},{'_id':0,'id':1}).to_list(10000)
        q['id']={'$nin':[x['id'] for x in blocked]}
    cursor=db.properties.find(q,PUBLIC_FIELDS)
    if sort in ['price_asc','price_desc']: cursor=cursor.sort('price',1 if sort=='price_asc' else -1)
    else: cursor=cursor.sort('id',1)
    rows=await cursor.to_list(500)
    for p in rows: p['agency_name']=names[p['agency_id']]
    return {'properties':rows,'total':len(rows)}

@router.get('/properties/{id}')
async def detail(id:str):
    p=await published_property(id)
    p['fee_settings']=await fee_settings()
    p['payments_enabled']=False
    return p

@router.get('/properties/{id}/availability')
async def calendar(id:str):
    await published_property(id)
    doc=await db.calendars.find_one({'id':id},{'_id':0,'slots':1})
    from core import iso
    return [{'check_in':s['check_in'],'check_out':s['check_out']} for s in (doc or {}).get('slots',[]) if s['check_out']>=date.today().isoformat() and (s['kind']!='hold' or s.get('expires_at','')>iso())]

@router.post('/properties/{id}/quote')
async def quote(id:str, data:QuoteInput):
    p=await published_property(id)
    if data.guests>p['guests']: raise HTTPException(400,'Guest count exceeds the property capacity')
    if not await available(id,data.check_in.isoformat(),data.check_out.isoformat()): raise HTTPException(409,'These dates are unavailable. Please choose different dates.')
    service_map={s['id']:s for s in p['services']}
    if len(data.services)!=len(set(data.services)) or any(x not in service_map for x in data.services): raise HTTPException(400,'Choose valid, unique services')
    private=await db.properties.find_one({'id':id},{'_id':0,'commission_rate':1})
    selected=[service_map[x] for x in data.services]
    q=calculate(p['price'],(data.check_out-data.check_in).days,private['commission_rate'],selected,await fee_settings())
    return {k:v for k,v in q.items() if k not in ['agency_rate','agency_gross','platform_commission','agency_retained','owner_allocation']} | {'selected_services':selected,'payments_enabled':False}

@router.post('/properties/{id}/checkout')
async def checkout(id:str,data:BookingInput):
    await quote(id,QuoteInput(**data.model_dump(include={'check_in','check_out','guests','services'})))
    # Deliberate fail-closed gate. No charge, hold or confirmation can be created
    # until Whop credentials AND merchant eligibility are configured and verified.
    raise HTTPException(503,'Online reservations are not open yet. No payment has been taken. Please contact the agency.')

@router.get('/bookings/status/{token}')
async def booking_status(token:str):
    if len(token)<32: raise HTTPException(404,'Reservation not found')
    b=await db.bookings.find_one({'status_token':token},{'_id':0})
    if not b: raise HTTPException(404,'Reservation not found')
    p=await db.properties.find_one({'id':b['property_id']},{'_id':0,'photos':1,'city':1,'country':1})
    fields=['reference','property_name','check_in','check_out','guests','status','fee_status','rental_status','payment_instructions','services']
    public={k:b.get(k) for k in fields}
    public['quote']={k:v for k,v in b['quote'].items() if k not in ['agency_rate','agency_gross','platform_commission','agency_retained','owner_allocation']}
    public['property']=p
    return public