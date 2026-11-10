"use client";
import {useState} from 'react';
import Link from 'next/link';
import {api} from '@/lib/api';
import {useAuth} from '@/lib/auth';

export function RatingControl({movieId,onSaved}:{movieId:string;onSaved:()=>void}){
 const auth=useAuth();
 const [value,setValue]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
 async function save(event:React.FormEvent){
  event.preventDefault();setBusy(true);setMessage('');
  try{await api(`/me/ratings/${movieId}`,{method:'PUT',body:JSON.stringify({value:Number(value)})},auth.token);setMessage('Your star rating is saved.');onSaved();}
  catch(error){setMessage((error as Error).message);}finally{setBusy(false);}
 }
 return <section className="panel"><h2>Your rating</h2>{auth.user?<form className="form" onSubmit={save}><label>Stars<select required value={value} onChange={event=>setValue(event.target.value)}><option value="">Choose a rating</option>{Array.from({length:10},(_,index)=>(index+1)/2).map(stars=><option value={stars} key={stars}>{stars} / 5</option>)}</select></label><button className="button secondary" disabled={!value||busy}>{busy?'Saving…':'Save rating'}</button></form>:<p><Link href="/auth">Sign in</Link> to rate this film.</p>}<small>This records your rating separately from review sentiment.</small>{message&&<p role="status">{message}</p>}</section>;
}
