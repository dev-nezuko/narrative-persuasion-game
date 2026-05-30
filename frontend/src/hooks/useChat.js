import { useState, useEffect, useCallback, useRef } from 'react';
import { sendMessage, getSession, createSession, resetSession } from '../utils/api';
const SESSION_KEY = 'doorman_session_id';
const emptyState = { cumulativeScore:0, threshold:100, accessGranted:false, messageCount:0 };
function storedSession() {
 try { const id=localStorage.getItem(SESSION_KEY); if (/^[A-Za-z0-9_-]{16,128}$/.test(id || '')) return id; } catch { /* Storage is optional. */ }
 return null;
}
// Resume the stored game if the server still has it; otherwise ask the server for a fresh ID.
async function restoreOrCreate(id) {
 if (id) {
  try { return await getSession(id); }
  catch (error) { if (error.status !== 404) throw error; }
 }
 return createSession();
}
function persist(id) { try { localStorage.setItem(SESSION_KEY,id); } catch { /* Keep playing in memory. */ } }
function gameStateFrom(data) { return {cumulativeScore:data.cumulative_score,threshold:data.threshold,accessGranted:data.access_granted,messageCount:data.message_count}; }
export function useChat() {
 const [sessionId,setSessionId]=useState(storedSession);
 const [messages,setMessages]=useState([]);
 const [gameState,setGameState]=useState(emptyState);
 const [isLoading,setIsLoading]=useState(true);
 const [error,setError]=useState(null);
 const [lastScore,setLastScore]=useState(null);
 const [audioData,setAudioData]=useState(null);
 const [ttsEnabled,setTtsEnabled]=useState(false);
 const busy=useRef(false);
 useEffect(()=>{
  let active=true;
  restoreOrCreate(sessionId).then(session=>{
   if (!active) return;
   if (session.session_id!==sessionId) { persist(session.session_id); setSessionId(session.session_id); }
   setGameState(gameStateFrom(session));
   setMessages((session.history || []).map((message,index)=>({id:index,role:message.role,content:message.content})));
  }).catch(()=>{if(active)setError('Could not restore this session. Check the local game server.');}).finally(()=>{if(active)setIsLoading(false);});
  return ()=>{active=false;};
 },[sessionId]);
 const send=useCallback(async text=>{
  if (busy.current || isLoading || !sessionId || !text.trim()) return false;
  busy.current=true;setIsLoading(true);setError(null);setLastScore(null);setAudioData(null);
  const id=crypto.randomUUID();
  setMessages(previous=>[...previous,{id,role:'user',content:text.trim()}]);
  try {
   const response=await sendMessage(sessionId,text.trim(),ttsEnabled);
   if(typeof response.reply!=='string'||!Number.isFinite(response.cumulative_score))throw new Error('The game returned an invalid response.');
   setMessages(previous=>[...previous,{id:crypto.randomUUID(),role:'assistant',content:response.reply}]);
   setGameState(gameStateFrom(response));setLastScore({delta:response.score_delta});setAudioData(response.audio_base64 || null);
   return true;
  } catch(error) {setError(error.message);setMessages(previous=>previous.filter(message=>message.id!==id));return false;}
  finally {busy.current=false;setIsLoading(false);}
 },[sessionId,isLoading,ttsEnabled]);
 const reset=useCallback(async()=>{
  if(busy.current||isLoading||!sessionId)return;
  busy.current=true;setIsLoading(true);
  try {const session=await resetSession(sessionId);setMessages([]);setGameState({...emptyState,cumulativeScore:session.cumulative_score});setLastScore(null);setAudioData(null);setError(null);}
  catch(error){setError(error.message);}
  finally{busy.current=false;setIsLoading(false);}
 },[sessionId,isLoading]);
 const clearLastScore=useCallback(()=>setLastScore(null),[]);
 const clearAudio=useCallback(()=>setAudioData(null),[]);
 const toggleTts=useCallback(()=>setTtsEnabled(previous=>!previous),[]);
 return {messages,isLoading,error,gameState,lastScore,audioData,ttsEnabled,send,reset,clearLastScore,clearAudio,toggleTts};
}
