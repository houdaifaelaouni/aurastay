import { useEffect, useState, useId } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ArrowRight, LockKeyhole, Check, ShieldCheck } from 'lucide-react';
import { Action, Field, Modal } from './common';
import { api, euro, errorMessage, today } from '../lib/api';

export default function BookingPanel({property:p}) {
  const [params]=useSearchParams();
  const [dates,setDates]=useState({check_in:params.get('check_in')||'',check_out:params.get('check_out')||'',guests:Number(params.get('guests')||1)});
  const [services,setServices]=useState([]);
  const [quote,setQuote]=useState(null);
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(false);
  const [review,setReview]=useState(false);
  const [details,setDetails]=useState({guest_name:'',guest_email:'',guest_phone:'',accepted_terms:false});
  const [reviewed,setReviewed]=useState(false);
  useEffect(()=>{setQuote(null);setError('');setReviewed(false)},[dates,services]);

  async function getQuote(e) {
    e.preventDefault();setLoading(true);setError('');
    try {const {data}=await api.post(`/properties/${p.id}/quote`,{...dates,guests:Number(dates.guests),services});setQuote(data)}
    catch(e){setError(errorMessage(e))}finally{setLoading(false)}
  }

  return <aside className="booking-column">
    <div className="booking-panel" data-testid="booking-panel">
      <div className="booking-price"><div data-testid="booking-nightly-price"><strong>{euro(p.price,false)}</strong><span> / night</span></div><span className="booking-currency" data-testid="booking-currency">EUR</span></div>
      <p className="booking-price-note" data-testid="booking-price-note">A little escape, entirely yours.</p>
      <form onSubmit={getQuote}>
        <div className="booking-dates">
          <Field label="CHECK-IN" id="booking-check-in" type="date" required min={today()} value={dates.check_in} onChange={e=>setDates({...dates,check_in:e.target.value})}/>
          <Field label="CHECK-OUT" id="booking-check-out" type="date" required min={dates.check_in||today()} value={dates.check_out} onChange={e=>setDates({...dates,check_out:e.target.value})}/>
        </div>
        <Field label="GUESTS" id="booking-guests">
          <select id="booking-guests" data-testid="booking-guests" value={dates.guests} onChange={e=>setDates({...dates,guests:Number(e.target.value)})}>
            {Array.from({length:p.guests},(_,i)=><option key={i+1} value={i+1}>{`${i+1} guest${i?'s':''}`}</option>)}
          </select>
        </Field>
        {p.services.length>0&&<div className="booking-services">
          <h3 data-testid="optional-services-title">Make yourself at home <span>Optional</span></h3>
          {p.services.map(s=><label key={s.id} className="service-option">
            <input type="checkbox" data-testid={`booking-service-${s.id}`} checked={services.includes(s.id)} onChange={()=>setServices(services.includes(s.id)?services.filter(x=>x!==s.id):[...services,s.id])}/>
            <span>{s.name}<small>{s.basis==='night'?'Per night':'Per stay'}</small></span><strong>{euro(s.price,false)}</strong>
          </label>)}
        </div>}
        {error&&<div role="alert" className="error-banner" data-testid="booking-error">{error}</div>}
        {!quote?<Action id="check-availability" type="submit" className="full-width" disabled={loading}>{loading?'Checking dates…':'Check availability'}<ArrowRight size={17}/></Action>:<>
          <div className="availability-success" data-testid="dates-available"><Check size={15}/> Your dates are available</div>
          <PriceBreakdown quote={quote}/>
          <Action id="review-reservation" className="full-width" type="button" onClick={()=>setReview(true)}>Review your stay <ArrowRight size={16}/></Action>
        </>}
      </form>
      <div className="booking-bottom-note" data-testid="booking-no-charge"><ShieldCheck size={15}/> Clear pricing. No surprises.</div>
    </div>
    <div className="booking-offline" data-testid="payments-unavailable"><LockKeyhole size={17}/><p><strong>Online reservations opening soon</strong>Browse dates and prices, or contact {p.agency.name} to arrange your stay.</p></div>
    <Modal open={review} onClose={()=>setReview(false)} title={reviewed?'Your stay, at a glance':'A few details for your stay'} description={`${p.name} · ${dates.check_in} to ${dates.check_out}`}>
      <form className="form-stack" onSubmit={e=>{e.preventDefault();setReviewed(true)}}>
        {!reviewed?<>
          <Field label="Full name" id="guest-name" required minLength={2} value={details.guest_name} onChange={e=>setDetails({...details,guest_name:e.target.value})}/>
          <Field label="Email address" id="guest-email" type="email" required value={details.guest_email} onChange={e=>setDetails({...details,guest_email:e.target.value})}/>
          <Field label="Phone number" id="guest-phone" type="tel" required minLength={6} value={details.guest_phone} onChange={e=>setDetails({...details,guest_phone:e.target.value})}/>
          <label className="terms-checkbox"><input type="checkbox" data-testid="guest-accept-terms" required checked={details.accepted_terms} onChange={e=>setDetails({...details,accepted_terms:e.target.checked})}/>I accept the reservation-fee and cancellation terms, including applicable legal exceptions.</label>
          <Action id="guest-review-continue" type="submit">Review price breakdown <ArrowRight size={16}/></Action>
        </>:<>
          <PriceBreakdown quote={quote}/>
          <div className="info-banner" data-testid="review-rental-instructions">{p.agency.payment_instructions}</div>
          <div className="warning-banner" data-testid="checkout-disabled-notice">Whop payments are not enabled. No reservation has been made and no payment has been taken.</div>
          <Action id="whop-checkout-button" type="button" disabled><LockKeyhole size={16}/> Pay {euro(quote?.reservation_fee)} with Whop</Action>
          <a className="text-link" data-testid="review-contact-agency" href={`mailto:${p.agency.email}`}>Contact {p.agency.name} instead <ArrowRight size={15}/></a>
        </>}
      </form>
    </Modal>
  </aside>;
}

export const PriceBreakdown=({quote:q})=>{
  const instance=useId().replace(/[^a-z0-9]/gi,'');
  return q&&<div className="price-breakdown" data-testid={`price-breakdown-${instance}`}>
    <div data-testid={`price-accommodation-${instance}`}><span>{euro(q.nightly_price,false)} × {q.nights} nights</span><strong>{euro(q.accommodation)}</strong></div>
    {q.services_total>0&&<div data-testid={`price-services-${instance}`}><span>Optional services</span><strong>{euro(q.services_total)}</strong></div>}
    <div data-testid={`price-rental-balance-${instance}`}><span>Pay separately to the agency</span><strong>{euro(q.rental_balance)}</strong></div>
    <div className="price-total" data-testid={`price-fee-due-now-${instance}`}><span>Reservation fee <small>Pay online now</small></span><strong>{euro(q.reservation_fee)}</strong></div>
    <div className="price-grand-total" data-testid={`price-total-cost-${instance}`}><span>Total cost, including fee</span><span>{euro(q.total)}</span></div>
  </div>;
};