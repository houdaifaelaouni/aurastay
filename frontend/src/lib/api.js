import axios from 'axios';
export const BASE = process.env.REACT_APP_BACKEND_URL;
export const api = axios.create({baseURL: `${BASE}/api`});
api.interceptors.request.use(config => {
  if(config.params) config.params=Object.fromEntries(Object.entries(config.params).filter(([,value])=>value!=='' && value!==null && value!==undefined));
  const token = localStorage.getItem('aurastay-token');
  const agency = localStorage.getItem('aurastay-agency');
  if(token) config.headers.Authorization = `Bearer ${token}`;
  if(agency) config.headers['X-Agency-Id'] = agency;
  return config;
});
export const euro = (value=0, cents=true) => new Intl.NumberFormat('en-IE', {style:'currency',currency:'EUR',maximumFractionDigits:cents?2:0,minimumFractionDigits:cents?2:0}).format(value);
export const photoUrl = url => url?.startsWith('/api/') ? `${BASE}${url}` : url;
export const errorMessage = e => {const detail=e.response?.data?.detail; return typeof detail==='string'?detail:Array.isArray(detail)?detail.map(x=>x.msg.replace('Value error, ','')).join('. '):'Something went wrong. Please try again.';};
export const today = () => new Date().toLocaleDateString('en-CA');
export const dateLabel = value => new Date(`${value}T12:00:00`).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});
export async function downloadCSV(kind, params) {
  const {data}=await api.get(`/workspace/${kind}/export`,{params,responseType:'blob'});
  const url=URL.createObjectURL(data); const a=document.createElement('a'); a.href=url;a.download=`aurastay-${kind}.csv`;a.click();URL.revokeObjectURL(url);
}