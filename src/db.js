/* =====================================================================
   Database layer (Supabase). Optional: with no URL/key configured, or with
   the network down, every function quietly does nothing and the app keeps
   working from the bundled catalogue and this browser's storage.

   Plain fetch against Supabase's REST endpoints (Auth + PostgREST), so the
   page stays one self-contained file with no library to load.

   What goes where:
     - catalogue ............ read from the database when its version differs
                              from the one this page was built with
     - account data ......... only after sign-in AND the consent tick:
                              saved answers, plans, check-ins, reactions
     - analytics ............ anonymous events, never linked to the login;
                              no name, city, pregnancy or reaction details
   ===================================================================== */
const DB=(()=>{
  const CFG=(typeof AAINA_DB_CONFIG!=="undefined"&&AAINA_DB_CONFIG)||{};
  const BASE=String(CFG.url||"").replace(/\/+$/,""),KEY=String(CFG.anonKey||"");
  const enabled=/^https:\/\/.+/.test(BASE)&&KEY.length>20;
  const CONSENT_VERSION="v1-2026-11";
  const AUTH_KEY="aaina.auth.v1",PENDING_KEY="aaina.consent.pending",SID_KEY="aaina.sid";
  const store=k=>{try{return window[k]}catch{return null}};
  const getJ=(s,k)=>{try{return JSON.parse(store(s)?.getItem(k)||"null")}catch{return null}};
  const setJ=(s,k,v)=>{try{v==null?store(s)?.removeItem(k):store(s)?.setItem(k,JSON.stringify(v))}catch{}};

  let session=getJ("localStorage",AUTH_KEY);   // {access_token, refresh_token, expires_at, user:{id,email}}
  let consented=false;                         // a profile row (with consent_at) exists for this login
  let lastError=null,refreshing=null;
  const listeners=new Set();
  const emit=()=>listeners.forEach(f=>{try{f()}catch{}});

  /* ---------- low-level request ---------- */
  async function req(path,{method="GET",body,headers={},asUser=true,timeout=8000,keepalive=false}={}){
    if(!enabled)return{ok:false,status:0};
    if(asUser&&session)await ensureFresh();
    const token=asUser&&session?session.access_token:KEY;
    const ctrl=typeof AbortController!=="undefined"?new AbortController():null;
    const timer=ctrl?setTimeout(()=>ctrl.abort(),timeout):null;
    try{
      const r=await fetch(BASE+path,{method,keepalive,signal:ctrl?.signal,
        headers:{apikey:KEY,Authorization:`Bearer ${token}`,"Content-Type":"application/json",...headers},
        body:body===undefined?undefined:JSON.stringify(body)});
      const txt=await r.text();let data=null;try{data=txt?JSON.parse(txt):null}catch{data=txt}
      if(!r.ok){lastError=(data&&(data.message||data.msg||data.error_description))||`HTTP ${r.status}`;
        if(r.status===401&&asUser&&session)dropSession()}
      return{ok:r.ok,status:r.status,data,headers:r.headers};
    }catch(e){lastError=String(e&&e.name==="AbortError"?"timed out":e);return{ok:false,status:0}}
    finally{if(timer)clearTimeout(timer)}
  }

  /* ---------- auth: email magic link ---------- */
  function dropSession(){session=null;consented=false;setJ("localStorage",AUTH_KEY,null);emit()}
  async function ensureFresh(){
    if(!session||!session.expires_at||session.expires_at*1000-Date.now()>60000)return;
    if(refreshing)return refreshing;   // one refresh at a time; asUser:false below can't recurse
    const s=session;
    refreshing=(async()=>{
    const r=await req("/auth/v1/token?grant_type=refresh_token",{method:"POST",body:{refresh_token:s.refresh_token},asUser:false});
    if(r.ok&&r.data?.access_token){session={access_token:r.data.access_token,refresh_token:r.data.refresh_token,
      expires_at:r.data.expires_at||Math.floor(Date.now()/1000)+(r.data.expires_in||3600),user:s.user};setJ("localStorage",AUTH_KEY,session)}
    else if(r.status>=400&&r.status<500)dropSession();   // refresh token rejected; a network blip keeps the session
    })();
    try{await refreshing}finally{refreshing=null}
  }
  // The sign-in link returns to this page with the tokens in the #hash.
  async function readRedirect(){
    const h=location.hash||"";if(!/access_token=|error_description=/.test(h))return null;
    const q=new URLSearchParams(h.replace(/^#/,""));
    try{history.replaceState(null,"",location.pathname+location.search)}catch{}
    if(q.get("error_description"))return{error:q.get("error_description").replace(/\+/g," ")};
    const at=q.get("access_token");if(!at)return null;
    session={access_token:at,refresh_token:q.get("refresh_token"),expires_at:+q.get("expires_at")||Math.floor(Date.now()/1000)+(+q.get("expires_in")||3600),user:null};
    const u=await req("/auth/v1/user");
    if(!u.ok||!u.data?.id){dropSession();return{error:"That sign-in link didn't work. Please ask for a new one."}}
    session.user={id:u.data.id,email:u.data.email};setJ("localStorage",AUTH_KEY,session);return{signedIn:true};
  }
  async function sendLink(email){
    email=String(email||"").trim();
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))return{ok:false,error:"That email address doesn't look right."};
    const back=encodeURIComponent(location.origin+location.pathname);
    const r=await req(`/auth/v1/otp?redirect_to=${back}`,{method:"POST",body:{email,create_user:true},asUser:false});
    return r.ok?{ok:true}:{ok:false,error:r.status===429?"Too many requests. Please wait a minute and try again.":"I couldn't send the link right now. Please try again."};
  }
  async function signOut(){if(session)await req("/auth/v1/logout?scope=local",{method:"POST"});dropSession()}

  /* ---------- consent ---------- */
  // Consent is ticked before the sign-in email is sent, then confirmed on return.
  const setPendingConsent=on=>setJ("localStorage",PENDING_KEY,on?{v:CONSENT_VERSION,at:new Date().toISOString()}:null);
  const pendingConsent=()=>getJ("localStorage",PENDING_KEY);

  /* ---------- account data ---------- */
  async function pullProfile(){
    if(!session)return null;
    const r=await req("/rest/v1/profiles?select=display_name,state,consent_version,consent_at,updated_at&limit=1");
    if(!r.ok)return null;const row=Array.isArray(r.data)?r.data[0]:null;consented=!!row;emit();return row||null;
  }
  async function writeProfile(state,name){
    if(!session)return false;
    const pc=pendingConsent();if(!consented&&!pc)return false;   // never store without consent
    const body={user_id:session.user.id,display_name:name?String(name).slice(0,24):null,state:state||{}};
    if(!consented){body.consent_version=pc.v;body.consent_at=pc.at}
    const keepalive=JSON.stringify(body).length<60000;   // lets a save survive the tab closing
    const r=consented
      ?await req(`/rest/v1/profiles?user_id=eq.${session.user.id}`,{method:"PATCH",body,keepalive,headers:{Prefer:"return=minimal"}})
      :await req("/rest/v1/profiles",{method:"POST",body,keepalive,headers:{Prefer:"resolution=merge-duplicates,return=minimal"}});
    if(r.ok&&!consented){consented=true;setPendingConsent(false);emit()}
    return r.ok;
  }
  let pushTimer=null,pushArgs=null;
  function pushState(state,name){       // debounced: the app saves on every tap
    if(!enabled||!session||(!consented&&!pendingConsent()))return;
    pushArgs=[state,name];clearTimeout(pushTimer);
    pushTimer=setTimeout(()=>{const a=pushArgs;pushArgs=null;writeProfile(...a)},1500);
  }
  function flush(){if(pushArgs){clearTimeout(pushTimer);const a=pushArgs;pushArgs=null;return writeProfile(...a)}return Promise.resolve(true)}
  const planIds={};
  async function savePlan(plan){        // {madeAt, concern, productIds, extras}
    if(!session||!consented||!plan?.madeAt)return null;
    const made=new Date(plan.madeAt).toISOString();
    const r=await req("/rest/v1/plans?on_conflict=user_id,made_at",{method:"POST",
      body:{user_id:session.user.id,made_at:made,concern:plan.concern||null,product_ids:plan.productIds||[],extras:plan.extras||[]},
      headers:{Prefer:"resolution=merge-duplicates,return=representation"}});
    const id=r.ok&&Array.isArray(r.data)&&r.data[0]?.id;if(id)planIds[made]=id;return id||null;
  }
  async function saveCheckin(c){        // {stage, results, planMadeAt}
    if(!session||!consented)return false;
    const made=c.planMadeAt?new Date(c.planMadeAt).toISOString():null;
    const stage=["day3","week2"].includes(c.stage)?c.stage:"manual";
    const r=await req("/rest/v1/checkins",{method:"POST",body:{user_id:session.user.id,stage,results:c.results||{},plan_id:(made&&planIds[made])||null},headers:{Prefer:"return=minimal"}});
    return r.ok;
  }
  async function saveReactions(list,source,productId){
    if(!session||!consented||!list?.length)return false;
    const rows=list.map(reaction=>({user_id:session.user.id,reaction:String(reaction).slice(0,40),source,product_id:productId||null}));
    const r=await req("/rest/v1/reactions?on_conflict=user_id,reaction",{method:"POST",body:rows,headers:{Prefer:"resolution=ignore-duplicates,return=minimal"}});
    return r.ok;
  }
  async function deleteAll(){           // erases every row and the login itself
    if(!session)return{ok:true};
    clearTimeout(pushTimer);pushArgs=null;
    const r=await req("/rest/v1/rpc/delete_my_data",{method:"POST",body:{}});
    if(r.ok)dropSession();
    return{ok:r.ok,error:r.ok?null:"I couldn't reach your account to delete it. Please try again in a minute."};
  }

  /* ---------- catalogue ---------- */
  const toProduct=(r,shades)=>{
    const fl=[r.contains_fragrance,r.contains_essential_oils,r.contains_drying_alcohol,r.contains_retinoid,r.contains_aha,r.contains_bha,r.pregnancy_caution].map(b=>b?"1":"0").join("");
    const p={id:r.id,b:r.brand,n:r.name,c:r.category,con:r.concerns||[],st:r.skin_types||[],fl,com:r.comedogenic_risk,
      p:r.price_inr==null?null:+r.price_inr,sz:r.size,sp:!!r.is_sponsored};
    if(r.key_actives)p.a=r.key_actives;if(r.inci)p.i=r.inci;if(r.finish)p.fin=r.finish;
    if(r.spf!=null)p.spf=+r.spf;if(r.pa_rating)p.pa=r.pa_rating;
    if(shades&&shades.length)p.s=shades.map(s=>[s.shade_name,s.depth,s.undertone,s.hex,s.coverage]);
    return p;
  };
  async function getAll(path){          // PostgREST returns at most ~1000 rows per call
    const out=[];for(let from=0;from<20000;from+=1000){
      const r=await req(path,{asUser:false,timeout:12000,headers:{"Range-Unit":"items",Range:`${from}-${from+999}`}});
      if(!r.ok||!Array.isArray(r.data))return null;out.push(...r.data);if(r.data.length<1000)break}
    return out;
  }
  async function fetchCatalogue(builtVersion){
    if(!enabled)return null;
    const m=await req("/rest/v1/catalogue_meta?select=version",{asUser:false,timeout:5000});
    const version=m.ok&&Array.isArray(m.data)&&m.data[0]?.version;
    if(!version||version===builtVersion)return null;
    const [rows,shades]=await Promise.all([
      getAll("/rest/v1/products?select=*&active=eq.true&order=id"),
      getAll("/rest/v1/shades?select=product_id,shade_name,depth,undertone,hex,coverage,sort_order&order=product_id,sort_order")]);
    if(!rows||!rows.length||!shades)return null;
    const by={};for(const s of shades)(by[s.product_id]??=[]).push(s);
    return{version,list:rows.map(r=>toProduct(r,by[r.id]))};
  }

  /* ---------- anonymous analytics ---------- */
  function sid(){
    let s=null;try{s=sessionStorage.getItem(SID_KEY)}catch{}
    if(!s){s=(crypto?.randomUUID?.())||"xxxxxxxx-xxxx-4xxx-8xxx-xxxxxxxxxxxx".replace(/x/g,()=>(Math.random()*16|0).toString(16));try{sessionStorage.setItem(SID_KEY,s)}catch{}}
    return s;
  }
  function track(name,props){
    if(!enabled)return;
    try{if(navigator.doNotTrack==="1"||window.doNotTrack==="1"||navigator.globalPrivacyControl)return}catch{}
    // sent with the public key, never the login, so events can't be tied to an account
    req("/rest/v1/events",{method:"POST",asUser:false,keepalive:true,timeout:5000,body:{session_id:sid(),name,props:props||{}},headers:{Prefer:"return=minimal"}});
  }

  async function init(){
    if(!enabled)return{};
    const back=await readRedirect();let profile=null;
    if(session){await ensureFresh();if(session)profile=await pullProfile()}
    emit();
    return{...(back||{}),profile};
  }
  return{enabled,CONSENT_VERSION,init,sendLink,signOut,setPendingConsent,pendingConsent,pullProfile,pushState,flush,savePlan,saveCheckin,saveReactions,deleteAll,fetchCatalogue,track,
    user:()=>session?.user||null,consented:()=>consented,lastError:()=>lastError,onChange:f=>{listeners.add(f);return()=>listeners.delete(f)},
    _toProduct:toProduct};
})();
