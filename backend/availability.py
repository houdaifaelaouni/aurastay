from datetime import timedelta
from fastapi import HTTPException
from core import db, iso, now

def overlap(check_in, check_out):
    return {'check_in': {'$lt': check_out}, 'check_out': {'$gt': check_in},
            '$or':[{'kind':{'$ne':'hold'}},{'expires_at':{'$gt':iso()}}]}

async def available(property_id, check_in, check_out):
    return not await db.calendars.find_one({'id':property_id,'slots':{'$elemMatch':overlap(check_in,check_out)}},{'_id':0,'id':1})

async def acquire(property_id, slot):
    """Single MongoDB document compare-and-set: no race between competing stays."""
    result=await db.calendars.update_one({'id':property_id,'slots':{'$not':{'$elemMatch':overlap(slot['check_in'],slot['check_out'])}}},{'$push':{'slots':slot}})
    if not result.modified_count: raise HTTPException(409,'Those dates are no longer available. Please choose another stay.')

async def release(property_id, slot_id):
    await db.calendars.update_one({'id':property_id},{'$pull':{'slots':{'id':slot_id}}})

async def expire_holds():
    timestamp=iso()
    await db.calendars.update_many({}, {'$pull':{'slots':{'kind':'hold','expires_at':{'$lte':timestamp}}}})
    await db.bookings.update_many({'status':'payment_pending','hold_expires_at':{'$lte':timestamp}}, {'$set':{'status':'expired'}})