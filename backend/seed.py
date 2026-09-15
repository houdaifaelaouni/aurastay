import os
import secrets
from datetime import date, timedelta
from core import db, iso
from auth import hash_password
from finance import calculate

def img(code): return f'https://images.unsplash.com/{code}?auto=format&fit=crop&w=1200&q=85'
PHOTOS = [img(x) for x in ['photo-1660599197053-fe0aa8d5b3a4','photo-1688646953306-5ec93eab8c06','photo-1648881806148-e5c51179c826','photo-1549926977-c517237dee4d','photo-1628592102751-ba83b0314276','photo-1763506425614-cdfee3349eff','photo-1680526213972-6ffe80a90e4f','photo-1782939355626-8df602c595fb']]

async def seed():
    for name in ['users','agencies','memberships','properties','bookings','team','expenses','blocks','files','calendars']:
        await db[name].create_index('id', unique=True)
    await db.users.create_index('email', unique=True)
    await db.bookings.create_index('status_token', unique=True, sparse=True)
    for name in ['properties','bookings','team','expenses','blocks','files']:
        await db[name].create_index([('agency_id',1),('created_at',-1)])
    await db.job_runs.create_index('run_id', unique=True)
    if await db.settings.find_one({'id':'seed-v1'}): return
    settings={'id':'fees','percentage':1,'per_night':1,'minimum':10,'maximum':30}
    await db.settings.update_one({'id':'fees'},{'$setOnInsert':settings},upsert=True)
    agencies=[{'id':'agency-costa','name':'Costa Living','email':'hello@costaliving.example','phone':'+34 951 000 120','active':True,
               'payment_instructions':'The accommodation and selected services are payable separately to Costa Living. Contact the agency to arrange your rental balance before arrival.'},
              {'id':'agency-maison','name':'Maison Collective','email':'stays@maisoncollective.example','phone':'+33 4 00 00 12 34','active':True,
               'payment_instructions':'Please contact Maison Collective before arrival to arrange the separate accommodation and service payment.'}]
    for a in agencies: await db.agencies.update_one({'id':a['id']},{'$setOnInsert':a},upsert=True)
    for id,email,password,role,name in [('owner',os.environ['BOOTSTRAP_EMAIL'],os.environ['BOOTSTRAP_PASSWORD'],'owner','Alex Morgan'),('manager',os.environ['MANAGER_EMAIL'],os.environ['MANAGER_PASSWORD'],None,'Sofia Martinez')]:
        await db.users.update_one({'id':id},{'$setOnInsert':{'id':id,'name':name,'email':email,'password_hash':hash_password(password),'platform_role':role,'active':True}},upsert=True)
    await db.memberships.update_one({'id':'member-manager'},{'$setOnInsert':{'id':'member-manager','user_id':'manager','agency_id':'agency-costa','tenant_role':'admin','active':True}},upsert=True)
    rows=[('Casa Sol, a Mediterranean escape','Marbella','Spain',245,'Villa','Coastal',6,3,20),('The light-filled city loft','Barcelona','Spain',145,'Apartment','City breaks',4,2,15),('A slower kind of city stay','Lisbon','Portugal',125,'Apartment','City breaks',2,1,18),('Villa Oliva & the quiet coast','Ibiza','Spain',320,'Villa','Villas',8,4,20),('Your little corner of Madrid','Madrid','Spain',110,'Apartment','City breaks',3,1,15),('Riviera days, sea-view mornings','Nice','France',210,'Penthouse','Coastal',4,2,18),('The garden house','Aix-en-Provence','France',185,'Cottage','Countryside',6,3,15),('A home above the rooftops','Seville','Spain',165,'Penthouse','City breaks',4,2,20)]
    properties=[]
    for i,(name,city,country,price,kind,category,guests,beds,rate) in enumerate(rows):
        aid='agency-costa' if i<5 else 'agency-maison'
        p={'id':f'stay-{i+1}','agency_id':aid,'created_by':'owner','created_at':iso(),'name':name,'city':city,'country':country,'address':f'{city}, {country}','price':price,'commission_rate':rate,'type':kind,'category':category,'guests':guests,'bedrooms':beds,'bathrooms':max(1,beds-1),'description':f'Settle into a thoughtfully chosen home in {city}, where local character meets room to unwind. Light-filled interiors, comfortable gathering spaces and carefully considered details make this a place to feel at home.\n\nSpend your mornings over a slow coffee, discover the neighbourhood at your own pace, and come back to your own private retreat. The entire property is yours for the duration of your stay.',
           'amenities':['Wi-Fi','Kitchen','Air conditioning','Washer']+(['Pool','Free parking','Garden'] if kind in ['Villa','Cottage'] else ['Balcony','Workspace']),
           'photos':[PHOTOS[i],PHOTOS[(i+4)%8],PHOTOS[(i+2)%8]],'services':[{'id':'transfer','name':'Airport transfer','price':45,'basis':'stay'},{'id':'cleaning','name':'Additional cleaning','price':30,'basis':'stay'},{'id':'welcome','name':'Personal welcome','price':20,'basis':'stay'}], 'status':'published','sample':True}
        properties.append(p)
        await db.properties.update_one({'id':p['id']},{'$setOnInsert':p},upsert=True)
        await db.calendars.update_one({'id':p['id']},{'$setOnInsert':{'id':p['id'],'agency_id':aid,'slots':[]}},upsert=True)
    names=['Emma Wilson','Luca Rossi','Oliver James','Clara Dubois','Noah Andersen','Isabella Costa','James Taylor','Amelia Martin','Sophie Laurent','Daniel Weber','Mia Thompson','Leo Bernard']
    for i,name in enumerate(names):
        p=properties[i%8]; start=date.today()+timedelta(days=(i-6)*9); nights=3+i%5; end=start+timedelta(days=nights)
        status='completed' if end<date.today() else 'confirmed'
        q=calculate(p['price'],nights,p['commission_rate'],[],settings)
        b={'id':f'reservation-{i+1}','reference':f'AUR-{26001+i}','agency_id':p['agency_id'],'property_id':p['id'],'property_name':p['name'],'guest_name':name,'guest_email':f'guest{i+1}@example.com','guest_phone':'+44 7700 900123','check_in':start.isoformat(),'check_out':end.isoformat(),'guests':2,'services':[],'quote':q,'status':status,'fee_status':'paid','rental_status':'paid' if status=='completed' else 'unpaid','settlement_status':'settled' if i<3 else 'outstanding','settlement_reference':'SAMPLE-2026' if i<3 else '', 'settlement_date':end.isoformat() if i<3 else None,'payment_instructions':agencies[0 if p['agency_id']=='agency-costa' else 1]['payment_instructions'],'status_token':secrets.token_urlsafe(32),'created_at':(start-timedelta(days=20)).isoformat(),'sample':True}
        await db.bookings.update_one({'id':b['id']},{'$setOnInsert':b},upsert=True)
        await db.calendars.update_one({'id':p['id'],'slots.id':{'$ne':b['id']}},{'$push':{'slots':{'id':b['id'],'check_in':b['check_in'],'check_out':b['check_out'],'kind':'confirmed'}}})
    people=[('Sofia Martinez','Manager','agency-costa'),('Marco Garcia','Commercial agent','agency-costa'),('Elena Ruiz','Cleaning staff','agency-costa'),('Louis Moreau','Manager','agency-maison'),('Camille Petit','Maintenance','agency-maison')]
    for i,(name,role,aid) in enumerate(people):
        t={'id':f'team-{i+1}','agency_id':aid,'name':name,'role':role,'email':name.lower().replace(' ','.')+'@example.com','phone':'+34 600 123 456','active':True,'property_ids':[p['id'] for p in properties if p['agency_id']==aid][:2],'created_at':iso(),'sample':True}
        await db.team.update_one({'id':t['id']},{'$setOnInsert':t},upsert=True)
    for i,(amount,cat,desc,reimbursement) in enumerate([(125,'Repairs','Replaced the terrace door lock','pending'),(85,'Cleaning','Deep clean before guest arrival','not_applicable'),(240,'Furniture','Replacement outdoor dining chairs','reimbursed'),(67.5,'Supplies','Fresh linen and guest essentials','not_applicable'),(110,'Utilities','Quarterly garden irrigation maintenance','not_applicable')]):
        p=properties[i if i<3 else i+2]
        e={'id':f'expense-{i+1}','agency_id':p['agency_id'],'property_id':p['id'],'amount':amount,'category':cat,'description':desc,'date':(date.today()-timedelta(days=i*4)).isoformat(),'payer':'agency' if i!=4 else 'owner','reimbursement':reimbursement,'created_at':iso(),'sample':True}
        await db.expenses.update_one({'id':e['id']},{'$setOnInsert':e},upsert=True)
    await db.settings.insert_one({'id':'seed-v1','created_at':iso()})