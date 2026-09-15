import os
import jwt
import bcrypt
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import EmailStr, Field
from core import db, now, authorize, ScopedRepo
from models import Strict

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
class Login(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

def hash_password(value): return bcrypt.hashpw(value.encode(), bcrypt.gensalt()).decode()

async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), x_agency_id: str | None = Header(default=None)):
    if not credentials: raise HTTPException(401, 'Please sign in')
    try:
        claims = jwt.decode(credentials.credentials, os.environ['JWT_SECRET'], algorithms=['HS256'])
        user = await db.users.find_one({'id': claims['sub'], 'active': True}, {'_id': 0, 'password_hash': 0})
        if not user: raise ValueError()
    except (jwt.PyJWTError, ValueError, KeyError): raise HTTPException(401, 'Session expired. Please sign in again')
    if user.get('platform_role') == 'owner':
        user['agency_id'] = None
        user['tenant_role'] = None
        if x_agency_id:
            agency = await db.agencies.find_one({'id': x_agency_id}, {'_id': 0})
            if not agency: raise HTTPException(404, 'Agency not found')
            authorize(user, 'platform:act_as_agency')
            user['agency_id'] = agency['id']
    else:
        member = await db.memberships.find_one({'user_id': user['id'], 'active': True}, {'_id': 0})
        if not member: raise HTTPException(403, 'Workspace access is disabled')
        agency = await db.agencies.find_one({'id': member['agency_id'], 'active': True}, {'_id': 0})
        if not agency: raise HTTPException(403, 'Agency access is disabled')
        if x_agency_id and x_agency_id != member['agency_id']: raise HTTPException(404, 'Workspace not found')
        user.update(agency_id=member['agency_id'], tenant_role=member['tenant_role'])
    return user

async def repo(user=Depends(current_user)): return ScopedRepo(user)

@router.post('/auth/login')
async def login(data: Login):
    user = await db.users.find_one({'email': str(data.email).lower(), 'active': True}, {'_id': 0})
    if not user or len(data.password.encode()) > 72 or not bcrypt.checkpw(data.password.encode(), user['password_hash'].encode()):
        raise HTTPException(401, 'Email or password is incorrect')
    token = jwt.encode({'sub': user['id'], 'exp': now()+timedelta(hours=12)}, os.environ['JWT_SECRET'], algorithm='HS256')
    return {'token': token}

@router.get('/auth/me')
async def me(user=Depends(current_user)):
    return {k: user.get(k) for k in ('id','name','email','platform_role','tenant_role','agency_id')}