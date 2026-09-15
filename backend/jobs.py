import os
import secrets
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from pymongo.errors import DuplicateKeyError
from core import db, iso
from availability import expire_holds

router=APIRouter()
@router.post('/cron/expire-holds')
async def expire(request:Request, tasks:BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth=request.headers.get('Authorization','')
    expected='Bearer '+os.environ['WEBHOOK_CRON_SECRET']
    if not secrets.compare_digest(auth,expected): raise HTTPException(401,'Unauthorized')
    try:
        body=await request.json()
        run_id=request.headers.get('X-Webhook-Id') or body['run_id']
        if not isinstance(body,dict) or body.get('event')!='schedule.triggered' or not isinstance(run_id,str) or not run_id: raise ValueError()
    except Exception: raise HTTPException(400,'Invalid schedule envelope')
    try: await db.job_runs.insert_one({'run_id':run_id,'received_at':iso()})
    except DuplicateKeyError: return {'accepted':True,'duplicate':True}
    tasks.add_task(expire_holds)
    return {'accepted':True}