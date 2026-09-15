import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict

load_dotenv(Path(__file__).parent / '.env')
client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
logger = logging.getLogger('aurastay.authorization')

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)
def iso(): return now().isoformat()

class Document(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str

def authorize(principal, action, resource=None):
    platform = principal.get('platform_role') == 'owner'
    tenant = principal.get('tenant_role') in ('admin', 'manager')
    permitted = (action.startswith('platform:') and platform) or (action.startswith('workspace:') and (tenant or (platform and bool(principal.get('agency_id')))))
    if resource and principal.get('agency_id') and resource.get('agency_id') != principal['agency_id']:
        logger.warning('deny user=%s action=%s reason=not_visible', principal.get('id'), action)
        raise HTTPException(404, 'Record not found')
    logger.info('%s user=%s agency=%s action=%s', 'allow' if permitted else 'deny', principal.get('id'), principal.get('agency_id'), action)
    if not permitted: raise HTTPException(403, 'You do not have permission for this action')

class ScopedRepo:
    """All workspace domain access carries a verified agency scope."""
    def __init__(self, principal): self.p = principal
    def query(self, query=None, write=False):
        if self.p.get('agency_id'):
            authorize(self.p, 'workspace:write' if write else 'workspace:read')
            return {'$and': [query or {}, {'agency_id': self.p['agency_id']}]}
        authorize(self.p, 'platform:read')
        if write: raise HTTPException(400, 'Select an agency before making changes')
        return query or {}
    async def list(self, collection, query=None, sort=None):
        cursor = db[collection].find(self.query(query), {'_id': 0})
        if sort: cursor = cursor.sort(*sort)
        return await cursor.to_list(10000)
    async def get(self, collection, id):
        doc = await db[collection].find_one(self.query({'id': id}), {'_id': 0})
        if not doc: raise HTTPException(404, 'Record not found')
        return doc
    async def insert(self, collection, fields):
        self.query(write=True)
        doc = {**fields, 'id': uid(), 'agency_id': self.p['agency_id'], 'created_by': self.p['id'], 'created_at': iso()}
        await db[collection].insert_one(doc.copy())
        return doc
    async def update(self, collection, id, fields):
        await self.get(collection, id)
        query = self.query({'id': id}, write=True)
        await db[collection].update_one(query, {'$set': {**fields, 'updated_at': iso()}})
        return await self.get(collection, id)
    async def delete(self, collection, id):
        await self.get(collection, id)
        await db[collection].delete_one(self.query({'id': id}, write=True))
        return {'ok': True}