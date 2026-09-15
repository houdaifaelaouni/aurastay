from fastapi import APIRouter, Depends, HTTPException
from pydantic import EmailStr, Field
from pymongo.errors import DuplicateKeyError
from typing import Literal
from core import db,authorize,uid,Document
from auth import current_user,hash_password
from models import Strict,FeeSettings
from finance import fee_settings

router=APIRouter()
@router.get('/agencies',response_model=list[Document])
async def agencies(user=Depends(current_user)):
    if user.get('platform_role')=='owner':authorize(user,'platform:agencies');query={}
    else:authorize(user,'workspace:read');query={'id':user['agency_id']}
    return await db.agencies.find(query,{'_id':0}).to_list(10000)

class AgencyInput(Strict):
    name:str=Field(min_length=2,max_length=100)
    email:EmailStr
    phone:str=Field(default='',max_length=40)
    payment_instructions:str=Field(min_length=20,max_length=2000)
    active:bool=True

@router.post('/platform/agencies',response_model=Document)
async def add_agency(data:AgencyInput,user=Depends(current_user)):
    authorize(user,'platform:agencies')
    doc={'id':uid(),**data.model_dump()};await db.agencies.insert_one(doc.copy());return doc

@router.put('/platform/agencies/{id}',response_model=Document)
async def edit_agency(id:str,data:AgencyInput,user=Depends(current_user)):
    authorize(user,'platform:agencies')
    result=await db.agencies.update_one({'id':id},{'$set':data.model_dump()})
    if not result.matched_count:raise HTTPException(404,'Agency not found')
    return {'id':id,**data.model_dump()}

@router.get('/platform/settings')
async def settings(user=Depends(current_user)):
    authorize(user,'platform:settings')
    return {'fees':await fee_settings(),'payments_enabled':False,'provider':'Whop','platform_commission_rate':2}

@router.put('/platform/settings')
async def update_settings(data:FeeSettings,user=Depends(current_user)):
    authorize(user,'platform:settings')
    await db.settings.update_one({'id':'fees'},{'$set':data.model_dump()},upsert=True)
    return data

class ManagerInput(Strict):
    name:str=Field(min_length=2,max_length=100)
    email:EmailStr
    password:str=Field(min_length=12,max_length=64)
    agency_id:str
    tenant_role:Literal['admin','manager']='manager'

@router.get('/platform/managers')
async def managers(user=Depends(current_user)):
    authorize(user,'platform:managers')
    memberships=await db.memberships.find({},{'_id':0}).to_list(10000)
    people={u['id']:u for u in await db.users.find({'platform_role':None},{'_id':0,'password_hash':0}).to_list(10000)}
    return [{**people[m['user_id']],'agency_id':m['agency_id'],'tenant_role':m['tenant_role']} for m in memberships if m['user_id'] in people]

@router.post('/platform/managers')
async def add_manager(data:ManagerInput,user=Depends(current_user)):
    authorize(user,'platform:managers')
    if len(data.password.encode())>72:raise HTTPException(400,'Password is too long')
    if not await db.agencies.find_one({'id':data.agency_id,'active':True},{'_id':0,'id':1}):raise HTTPException(404,'Active agency not found')
    id=uid();doc={'id':id,'name':data.name,'email':str(data.email).lower(),'password_hash':hash_password(data.password),'platform_role':None,'active':True}
    try:await db.users.insert_one(doc.copy())
    except DuplicateKeyError:raise HTTPException(409,'An account with this email already exists')
    await db.memberships.insert_one({'id':uid(),'user_id':id,'agency_id':data.agency_id,'tenant_role':data.tenant_role,'active':True})
    return {'id':id,'name':data.name,'email':data.email}

class AccessUpdate(Strict):
    active:bool

@router.patch('/platform/managers/{id}')
async def manager_access(id:str,data:AccessUpdate,user=Depends(current_user)):
    authorize(user,'platform:managers')
    result=await db.users.update_one({'id':id,'platform_role':None},{'$set':{'active':data.active}})
    if not result.matched_count:raise HTTPException(404,'Manager not found')
    return {'ok':True}