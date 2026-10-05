import { useEffect,useRef,useState,useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Camera,CameraOff,CheckCircle2,XCircle,ScanLine,RotateCcw } from 'lucide-react';
import jsQR from 'jsqr';
import { PageHeading,Action,Field,Badge } from '../../components/common';
import { ScopeNotice } from '../../components/workspace-ui';
import { api,errorMessage,dateLabel } from '../../lib/api';
import { useWorkspace } from '../Workspace';
import { toast } from '../../components/ui/sonner';

function useScanner(onCode){
  const video=useRef(null);const canvas=useRef(document.createElement('canvas'));const stream=useRef(null);const frame=useRef(0);const [active,setActive]=useState(false);const [error,setError]=useState('');
  const stop=useCallback(()=>{cancelAnimationFrame(frame.current);stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;setActive(false)},[]);
  const tick=useCallback(()=>{const v=video.current;if(v&&v.readyState===v.HAVE_ENOUGH_DATA){const c=canvas.current;c.width=v.videoWidth;c.height=v.videoHeight;const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(v,0,0);const found=jsQR(ctx.getImageData(0,0,c.width,c.height).data,c.width,c.height,{inversionAttempts:'dontInvert'});if(found?.data){stop();onCode(found.data);return}}frame.current=requestAnimationFrame(tick)},[onCode,stop]);
  async function start(){setError('');try{stream.current=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});video.current.srcObject=stream.current;await video.current.play();setActive(true);frame.current=requestAnimationFrame(tick)}catch{stop();setError('The camera is unavailable. Allow camera access, or paste the code below.')}}
  useEffect(()=>stop,[stop]);
  return {video,active,error,start,stop};
}

export default function CheckIn(){
  const {canWrite}=useWorkspace();const [params,setParams]=useSearchParams();const [code,setCode]=useState('');const [result,setResult]=useState(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [done,setDone]=useState(false);
  const verify=useCallback(async value=>{const trimmed=value.trim();if(!trimmed)return;setCode(trimmed);setBusy(true);setError('');setResult(null);setDone(false);try{const {data}=await api.post('/workspace/checkin/verify',{code:trimmed});setResult(data)}catch(e){setError(errorMessage(e))}finally{setBusy(false)}},[]);
  const scanner=useScanner(verify);
  useEffect(()=>{const fromLink=params.get('code');if(fromLink){verify(fromLink);setParams({},{replace:true})}},[params,setParams,verify]);
  async function confirm(){setBusy(true);try{const {data}=await api.post('/workspace/checkin/confirm',{code});setResult(data);setDone(true);toast.success(`${data.guest_name} is checked in`)}catch(e){setError(errorMessage(e));setResult(null)}finally{setBusy(false)}}
  const reset=()=>{setCode('');setResult(null);setError('');setDone(false)};
  const note=done?`Recorded ${result.checked_in_at?.slice(0,16).replace('T',' ')} UTC${result.checked_in_by_name?` by ${result.checked_in_by_name}`:''}`:result?.reason;
  return <><PageHeading eyebrow="ARRIVALS" title="Guest check-in" description="Scan the QR code on the guest's check-in pass. Each code works once."/>{!canWrite&&<ScopeNotice/>}
    <div className="checkin-layout">
      <section className="checkin-panel" data-testid="checkin-scanner">
        <div className={`checkin-camera ${scanner.active?'live':''}`}><video ref={scanner.video} playsInline muted data-testid="checkin-video"/>{!scanner.active&&<ScanLine size={42}/>}</div>
        {scanner.active?<Action id="checkin-stop-camera" variant="outline" onClick={scanner.stop}><CameraOff size={16}/>Stop camera</Action>:<Action id="checkin-start-camera" onClick={scanner.start} disabled={busy}><Camera size={16}/>Scan with camera</Action>}
        {scanner.error&&<div className="warning-banner" data-testid="checkin-camera-error">{scanner.error}</div>}
        <form className="form-stack" onSubmit={e=>{e.preventDefault();verify(code)}}><Field label="Or paste the code or link" id="checkin-code" value={code} onChange={e=>setCode(e.target.value)} placeholder="eyJhbGciOi… or https://…/workspace/checkin?code=…"/><Action id="checkin-verify" type="submit" variant="outline" disabled={busy||!code.trim()}>Check code</Action></form>
      </section>
      <section className="checkin-panel" data-testid="checkin-result" aria-live="polite">
        {error?<div className="checkin-verdict bad" data-testid="checkin-invalid"><XCircle size={34}/><h2>Not valid</h2><p>{error}</p></div>
        :!result?<div className="checkin-verdict" data-testid="checkin-idle"><ScanLine size={34}/><h2>Waiting for a code</h2><p>The guest's details appear here before you confirm.</p></div>
        :<><div className={`checkin-verdict ${done?'good':result.valid?'ready':'bad'}`} data-testid="checkin-verdict">{done?<CheckCircle2 size={34}/>:result.valid?<ScanLine size={34}/>:<XCircle size={34}/>}<h2>{done?'Checked in':result.valid?'Ready to check in':'Cannot check in'}</h2>{note&&<p data-testid="checkin-reason">{note}</p>}</div>
          <dl className="checkin-details"><div><dt>Guest</dt><dd data-testid="checkin-guest">{result.guest_name}</dd></div><div><dt>Reference</dt><dd data-testid="checkin-reference">{result.reference}</dd></div><div><dt>Property</dt><dd>{result.property_name}</dd></div><div><dt>Stay</dt><dd>{dateLabel(result.check_in)} — {dateLabel(result.check_out)}</dd></div><div><dt>Guests</dt><dd>{result.guests}</dd></div><div><dt>Rental balance</dt><dd><Badge value={result.rental_status||'unpaid'} id="checkin-rental-status"/></dd></div></dl>
          <div className="modal-actions">{result.valid&&!done&&<Action id="checkin-confirm" disabled={busy||!canWrite} onClick={confirm}><CheckCircle2 size={16}/>Confirm check-in</Action>}<Action id="checkin-next" variant="outline" onClick={reset}><RotateCcw size={16}/>Next guest</Action></div></>}
      </section>
    </div></>;
}
