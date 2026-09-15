from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from fastapi import HTTPException
from core import db

def money(value): return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

async def fee_settings():
    return await db.settings.find_one({'id': 'fees'}, {'_id': 0}) or {'percentage': 1, 'per_night': 1, 'minimum': 10, 'maximum': 30}

def calculate(price, nights, rate, services, settings):
    rental = money(Decimal(str(price))*nights)
    extras = money(sum(Decimal(str(s['price']))*(nights if s['basis']=='night' else 1) for s in services))
    fee = money(min(Decimal(str(settings['maximum'])), max(Decimal(str(settings['minimum'])), Decimal(str(rental))*Decimal(str(settings['percentage']))/100 + Decimal(str(settings['per_night']))*nights)))
    agency = money(Decimal(str(rental))*Decimal(str(rate))/100)
    platform = money(Decimal(str(rental))*Decimal('0.02'))
    return {'nights': nights, 'nightly_price': price, 'accommodation': rental, 'services_total': extras,
            'reservation_fee': fee, 'rental_balance': money(rental+extras), 'total': money(rental+extras+fee),
            'agency_rate': rate, 'agency_gross': agency, 'platform_commission': platform,
            'agency_retained': money(agency-platform), 'owner_allocation': money(rental-agency), 'currency':'EUR'}

def date_filter(start=None, end=None, field='check_in'):
    if start and end and start > end: raise HTTPException(400, 'Start date must be before end date')
    values = {}
    if start: values['$gte'] = start.isoformat()
    if end: values['$lte'] = end.isoformat()
    return {field: values} if values else {}

def expense_cost(e):
    return e['amount'] if e['payer']=='agency' and e['reimbursement']!='reimbursed' else 0