import csv
import io
from datetime import date
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from auth import repo
from finance import date_filter,money,expense_cost
from models import Strict
from core import Document

router=APIRouter()

@router.get('/dashboard')
async def dashboard(start:date|None=None,end:date|None=None,r=Depends(repo)):
    start=start or date(date.today().year,1,1);end=end or date(date.today().year,12,31)
    q=date_filter(start,end)
    props=await r.list('properties');bookings=await r.list('bookings',q);expenses=await r.list('expenses',date_filter(start,end,'date'))
    active=[b for b in bookings if b['status'] in ['confirmed','completed']]
    completed=[b for b in active if b['status']=='completed'];future=[b for b in active if b['status']=='confirmed']
    total=lambda rows,key:money(sum(b['quote'][key] for b in rows))
    paid=[b for b in bookings if b['fee_status'] in ['paid','refunded']]
    refunded=[b for b in bookings if b['fee_status']=='refunded']
    cost=money(sum(expense_cost(e) for e in expenses))
    occupancy_rows=await r.list('bookings',{'status':{'$in':['confirmed','completed']},'check_in':{'$lte':end.isoformat()},'check_out':{'$gt':start.isoformat()}})
    occupied=sum(max(0,(min(date.fromisoformat(b['check_out']),end.fromordinal(end.toordinal()+1))-max(date.fromisoformat(b['check_in']),start)).days) for b in occupancy_rows)
    inventory=[p for p in props if p['status']!='archived']
    denominator=len(inventory)*((end-start).days+1)
    stats={'properties':len(inventory),'reservations':len(active),'nights':sum(b['quote']['nights'] for b in active),'occupancy':round(100*occupied/denominator,1) if denominator else 0,
           'rental_value':total(active,'accommodation'),'agency_gross':total(active,'agency_gross'),'platform_commission':total(active,'platform_commission'),
           'agency_retained':total(active,'agency_retained'),'earned_commission':total(completed,'agency_retained'),'projected_commission':total(future,'agency_retained'),
           'expenses':money(sum(e['amount'] for e in expenses)),'agency_costs':cost,'agency_net':money(total(completed,'agency_retained')-cost),
           'fees_collected':total(paid,'reservation_fee'),'fees_refunded':total(refunded,'reservation_fee'),'fees_net':money(total(paid,'reservation_fee')-total(refunded,'reservation_fee')),
           'platform_earned':total(completed,'platform_commission'),'platform_projected':total(future,'platform_commission'),
           'platform_outstanding':total([b for b in completed if b['settlement_status']=='outstanding'],'platform_commission'),
           'platform_settled':total([b for b in active if b['settlement_status']=='settled'],'platform_commission'),
           'services_revenue':total(active,'services_total'),'rent_received':total([b for b in active if b['rental_status']=='paid'],'rental_balance'),
           'refund_issues':len([b for b in bookings if b['fee_status'] in ['refund_required','refund_failed']])}
    months=defaultdict(lambda:{'rental':0,'agency':0,'platform':0,'reservations':0})
    for b in active:
        m=b['check_in'][:7];months[m]['rental']+=b['quote']['accommodation'];months[m]['agency']+=b['quote']['agency_retained'];months[m]['platform']+=b['quote']['platform_commission'];months[m]['reservations']+=1
    trends=[{'month':m,**{k:money(v) for k,v in vals.items()}} for m,vals in sorted(months.items())]
    comparison=[{'id':p['id'],'name':p['name'],'rental':total([b for b in active if b['property_id']==p['id']],'accommodation'),'nights':sum(b['quote']['nights'] for b in active if b['property_id']==p['id'])} for p in props]
    return {'stats':stats,'trends':trends,'properties':sorted(comparison,key=lambda p:-p['rental']),'sample':any(p.get('sample') for p in props)}

@router.get('/commissions',response_model=list[Document])
async def commissions(start:date|None=None,end:date|None=None,status:str='',r=Depends(repo)):
    q=date_filter(start,end);q['status']={'$in':['confirmed','completed']}
    if status:q['settlement_status']=status
    return await r.list('bookings',q,sort=('check_in',-1))

class Settlement(Strict):
    reference:str=Field(min_length=2,max_length=150)
    date:date

@router.post('/commissions/{id}/settle',response_model=Document)
async def settle(id:str,data:Settlement,r=Depends(repo)):
    b=await r.get('bookings',id)
    if b['status']!='completed':raise HTTPException(400,'Only earned commissions on completed stays can be settled')
    if data.date>date.today():raise HTTPException(400,'Settlement date cannot be in the future')
    if b['settlement_status']=='settled':raise HTTPException(409,'This commission is already settled')
    return await r.update('bookings',id,{'settlement_status':'settled','settlement_date':data.date.isoformat(),'settlement_reference':data.reference})

def csv_response(rows,fields,name):
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for row in rows:
        safe={k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()}
        writer.writerow(safe)
    return Response('\ufeff'+output.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{name}.csv"'})

@router.get('/commissions/export')
async def export_commissions(start:date|None=None,end:date|None=None,status:str='',r=Depends(repo)):
    bookings=await commissions(start,end,status,r)
    fields=['reference','property','check_in','status','accommodation_eur','agency_gross_eur','platform_2pct_eur','agency_retained_eur','settlement','settlement_date','settlement_reference']
    rows=[dict(zip(fields,[b['reference'],b['property_name'],b['check_in'],b['status'],b['quote']['accommodation'],b['quote']['agency_gross'],b['quote']['platform_commission'],b['quote']['agency_retained'],b['settlement_status'],b.get('settlement_date',''),b.get('settlement_reference','')])) for b in bookings]
    return csv_response(rows,fields,'commissions')

@router.get('/expenses/export')
async def export_expenses(start:date|None=None,end:date|None=None,property_id:str='',category:str='',r=Depends(repo)):
    q=date_filter(start,end,'date')
    if property_id:q['property_id']=property_id
    if category:q['category']=category
    expenses=await r.list('expenses',q);props={p['id']:p['name'] for p in await r.list('properties')}
    fields=['date','property','category','description','amount_eur','payer','reimbursement','agency_cost_eur']
    rows=[dict(zip(fields,[e['date'],props.get(e['property_id'],e['property_id']),e['category'],e['description'],e['amount'],e['payer'],e['reimbursement'],expense_cost(e)])) for e in expenses]
    return csv_response(rows,fields,'expenses')