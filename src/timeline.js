/* =====================================================================
   Results timeline: what most people can realistically expect from a product at
   2 weeks, 4 weeks, 3 months, 6 months and 1 year, from cited studies only.
   Source of truth: data/evidence/actives_timeline.json (TIMELINE_EVIDENCE).
   Rules:
   - A number appears only at a time point a study measured, and only as reported.
   - Scale down, never up: unknown or lower strength -> the low end, or no number at all.
   - Past the last study point: "maintenance" or "not studied", never an invented number.
   - Cosmetic wording only (see BANNED); nothing predicts a specific person's skin.
   - The illustration changes only the concern's region, never overall tone or lightness.
   ===================================================================== */
const TIMELINE=(()=>{
  const EV=(typeof TIMELINE_EVIDENCE!=="undefined"&&TIMELINE_EVIDENCE)||{entries:[],refs:{}};
  // FICTIONAL in-house product tests for the demo catalogue (data/evidence/sample_product_studies.json).
  // Kept apart on purpose: they never change a grade, a number, a comparison or the illustration.
  const SAMPLES=(typeof TIMELINE_SAMPLES!=="undefined"&&TIMELINE_SAMPLES)||{studies:{}};
  const SAMPLE_SAY={pigmentation:"dark spots looked less noticeable",tanning:"their skin tone looked more even",acne:"they had fewer new blemishes",
    oiliness:"their skin looked less shiny by midday",dullness:"their skin felt smoother",dehydration:"their skin felt more hydrated",
    "fine lines":"fine lines looked softer",redness:"their skin looked less red","dark circles":"the under-eye area looked more rested",
    comfort:"it was comfortable to wear every day",lips:"their lips felt softer"};
  function sampleStudy(p,concern){
    const st=p&&SAMPLES.studies[p.id];if(!st)return null;
    const c=concern&&SAMPLE_SAY[concern]&&(p.con||[]).includes(concern)&&!/^(comfort|lips)$/.test(st.concern)?concern:st.concern;   // match the timeline's concern when the product is tagged for it
    const say=SAMPLE_SAY[c]||SAMPLE_SAY.dehydration;
    return{fictional:true,label:SAMPLES.label||"Sample data · fictional",design:SAMPLES.design,n:st.n,weeks:st.weeks[st.weeks.length-1],
      who:`${st.n} adults in ${st.cities.join(", ")}, skin tones ${st.tones}`,
      lines:st.weeks.map((w,i)=>({weeks:w,pct:st.agree[i],text:`Week ${w}: ${st.agree[i]}% agreed ${say}.`})),
      summary:`${st.agree[st.agree.length-1]}% agreed ${say} after ${st.weeks[st.weeks.length-1]} weeks`}
  }
  const STOPS=[{w:2,label:"2 weeks"},{w:4,label:"4 weeks"},{w:12,label:"3 months"},{w:26,label:"6 months"},{w:52,label:"1 year"}];
  const RANK={A:0,B:1,C:2,D:3};
  const CONF={A:"Strong evidence",B:"Some evidence",C:"Early evidence"};
  const RINSE_OFF=new Set(["Cleanser","Face mask"]);
  const NUMERIC=new Set(["change","responders","ratio","protective"]);
  // kept in step with tools/check_evidence.py; tests/timeline_unit_test.js scans every string we show
  const BANNED=/\b(you will|guarantee\w*|cures?|cured|curing|removes?|removal|lighten\w*|brighten\w*|whiten\w*|fairer|fairness|treat(s|ed|ment|ing)?|heal\w*|eliminat\w*|permanent\w*|melasma|rosacea|eczema|psoriasis|dermatitis|acne|hyperpigmentation|PIH)\b/i;
  const LABEL={pigmentation:"the look of dark spots",tanning:"uneven tone from the sun",acne:"blemishes",oiliness:"oiliness and shine",dullness:"dullness and rough texture",
    dehydration:"dryness","fine lines":"fine lines",redness:"visible redness","dark circles":"under-eye darkness"};
  const FX={pigmentation:"spots",tanning:"spots",oiliness:"shine",acne:"redness",redness:"redness","fine lines":"texture",dullness:"texture",dehydration:"texture"};
  const fmt=v=>v==null?"":(Math.round(v*10)/10).toString().replace(/\.0$/,"");

  /* ---------- which evidence applies to a product ---------- */
  function strengthOf(p,e){   // the product's % of this active, if the key-actives line states it
    const a=String(p.a||"").toLowerCase();
    for(const m of e.match){const i=a.indexOf(m);if(i<0)continue;const seg=a.slice(i).split(/\s*\+\s*|,\s*/)[0];const x=/(\d+(?:\.\d+)?)\s*%/.exec(seg);if(x)return+x[1]}
    return null;
  }
  function entriesFor(p){
    if(!p||RINSE_OFF.has(p.c))return[];
    const a=String(p.a||"").toLowerCase();
    return EV.entries.filter(e=>e.active==="Sunscreen"?p.c==="Sunscreen":p.c!=="Sunscreen"||a?e.match.some(m=>a.includes(m)):false);
  }
  const numericCps=e=>e.checkpoints.filter(c=>c.representative!==false&&NUMERIC.has(c.kind));
  const better=(x,y)=>RANK[x.evidence_strength]-RANK[y.evidence_strength]||numericCps(y).length-numericCps(x).length||y.checkpoints.length-x.checkpoints.length;
  function noTimeline(p,reason,concern){return{pid:p&&p.id,grade:"D",confidence:null,stops:null,reason,alsoHelps:[],notes:[],sample:sampleStudy(p,concern)}}

  /* ---------- the main call ---------- */
  // productTimeline(product, P, {concern}) -> {grade, confidence, concern, active, stops[5], notes, alsoHelps, firstChangeWeek, at12}
  function productTimeline(p,prof,opts={}){
    prof=prof||{};
    if(!p)return noTimeline(p,"No product.");
    if(RINSE_OFF.has(p.c))return noTimeline(p,"This is a rinse-off product. The studies we rely on tested products left on the skin, so we can't show a fair timeline.",opts.concern);
    const ents=entriesFor(p),usable=ents.filter(e=>e.evidence_strength!=="D");
    if(!usable.length)return noTimeline(p,ents.length?`Not enough evidence: we found no suitable peer-reviewed study for ${uniq(ents.map(e=>e.active)).join(", ")}.`:p.a?"Not enough evidence for this product's key ingredients.":"This product doesn't list its key ingredients, so we can't match it to any study.",opts.concern);
    const want=opts.concern||null;
    let rel=want?usable.filter(e=>e.app_concerns.includes(want)):[];
    let concern=want;
    if(!rel.length){   // the product isn't studied for that concern: use what it is studied for, and say so
      const cons=(p.con||[]).concat(prof.concerns||[]);
      for(const c of cons){rel=usable.filter(e=>e.app_concerns.includes(c));if(rel.length){concern=c;break}}
      if(!rel.length){rel=usable;concern=rel.slice().sort(better)[0].app_concerns[0]||rel[0].concern_key}
    }
    const best=rel.slice().sort(better)[0];
    const alsoHelps=uniq(rel.filter(e=>e.active!==best.active).map(e=>e.active));
    const label=LABEL[concern]||best.concern;
    const pct=strengthOf(p,best),studied=best.studied_pct;
    const scaleDown=best.active!=="Sunscreen"&&(pct==null||(studied!=null&&pct<studied));
    const sensitive=!!(prof.sensitive&&best.can_irritate);
    const notes=[];
    if(scaleDown)notes.push(pct==null?`This product doesn't state how much ${best.active.toLowerCase()} it contains, so we show the lower end of study results (or no number).`
      :`This product has ${fmt(pct)}% ${best.active.toLowerCase()}; studies used ${best.typical_concentration}, so results may be smaller.`);
    if(sensitive)notes.push(`You told us your skin is sensitive. ${best.active} can sting or dry the skin at first, so start slowly, every other day, and give your skin time to adjust before judging results.`);
    if(want&&concern!==want)notes.push(`This product isn't studied for ${LABEL[want]||want}; the timeline below is for ${label}.`);
    if(best.note)notes.push(best.note);
    const cps=best.checkpoints.filter(c=>c.representative!==false).slice().sort((a,b)=>a.weeks-b.weeks);
    const side=best.checkpoints.filter(c=>c.representative===false);
    const assign=c=>STOPS.findIndex(s=>c.weeks<=s.w+1);
    const first=cps[0]&&cps[0].weeks,last=cps.length?cps[cps.length-1].weeks:0;
    let lastValue=null;
    const stops=STOPS.map((s,i)=>{
      const here=cps.filter(c=>assign(c)===i);
      const c=here[here.length-1]||null;
      const base={w:s.w,label:s.label,confidence:CONF[best.evidence_strength],grade:best.evidence_strength};
      if(c){
        const v=valueOf(c,scaleDown);
        if(c.kind==="change"&&v.value!=null)lastValue=v.value;
        const at=Math.abs(c.weeks-s.w)>1.01?` (measured at ${weeksText(c.weeks)})`:"";
        return{...base,grade:c.grade||best.evidence_strength,confidence:CONF[c.grade||best.evidence_strength],status:"measured",measuredAt:c.weeks,kind:c.kind,value:v.value,valueText:v.text,
          short:shortLine(c,label,v,s)+at,detail:c.plain,half:halfLine(c,v),ref:c.ref,refInfo:EV.refs[c.ref]||null,
          population:best.population,why:whyDiffers(best,prof,pct,scaleDown),illus:c.kind==="change"?v.value:null}
      }
      if(first==null||s.w<first-1)return{...base,status:"early",short:`Too early to judge: studies first measured results at ${weeksText(first)}.`,illus:0,value:null};
      if(s.w>last+1)return{...base,status:"maintenance",short:best.active==="Sunscreen"?"Keeps protecting with daily use.":
        /^maintenance/.test(best.beyond_last_study||"")?"Maintenance: results usually hold with continued use; no evidence of further change.":
        `Not studied beyond ${weeksText(last)}: ${best.beyond_last_study||"no evidence either way"}.`,illus:lastValue,value:null};
      return{...base,status:"gap",short:`Not measured at this point in studies; the next study point is ${weeksText(cps.find(x=>x.weeks>s.w).weeks)}.`,illus:lastValue,value:null};
    });
    const firstChange=cps[0]?cps[0].weeks:null;
    const at12=stops[2];
    return{pid:p.id,grade:best.evidence_strength,confidence:CONF[best.evidence_strength],concern,concernLabel:label,active:best.active,entryId:best.id,
      stops,notes,alsoHelps,firstChangeWeek:firstChange,at12,region:FX[concern]||best.region,
      hasNumeric:stops.some(x=>x.illus!=null&&x.illus>0),side:side.map(c=>({plain:c.plain,ref:c.ref,refInfo:EV.refs[c.ref]})),
      protective:best.checkpoints.filter(c=>c.kind==="protective").map(c=>({plain:c.plain,ref:c.ref,refInfo:EV.refs[c.ref]})),
      ifStopped:best.if_stopped||"not studied",refs:best.refs.map(r=>EV.refs[r]).filter(Boolean),sample:sampleStudy(p,concern)};
  }
  function valueOf(c,scaleDown){
    if(!NUMERIC.has(c.kind))return{value:null,text:""};
    const lo=c.change_low,ty=c.change_typical,hi=c.change_high;
    if(scaleDown){if(lo!=null)return{value:lo,text:unitText(c,lo)};return{value:null,text:"",withheld:true}}
    if(ty!=null)return{value:ty,text:unitText(c,ty)};
    if(lo!=null&&hi!=null)return{value:lo,text:`${fmt(lo)}–${fmt(hi)}${c.kind==="ratio"?"×":"%"}`};
    return{value:lo??hi,text:unitText(c,lo??hi)};
  }
  const unitText=(c,v)=>c.kind==="ratio"?`${fmt(v)}×`:`${fmt(v)}%`;
  function shortLine(c,label,v,s){
    const when=s.w<=4?`Week ${s.w}`:s.label.replace(/^./,x=>x.toUpperCase());
    if(v.withheld)return`${when}: studies saw ${label} improve; the size may be smaller at this product's strength.`;
    switch(c.kind){
      case"change":return`${when}: in studies, ${label} improved by about ${v.text} (${c.measure}).`;
      case"responders":return`${when}: in studies, ${v.text} of people saw ${label} improve.`;
      case"ratio":return`${when}: in a study, ${label} improved ${v.text} as much as with a plain product.`;
      case"protective":return`${when}: daily use protects against further visible sun damage.`;
      default:return`${when}: ${s.w<=4?"first":"a"} measurable change in ${label} for many people in studies.`;
    }
  }
  function halfLine(c,v){
    if(c.kind==="change"&&v.value!=null)return`If used about half the time: an estimated ${fmt(v.value/2)}% (our estimate, not a study result).`;
    if(c.kind==="responders"||c.kind==="ratio")return"If used about half the time: likely fewer people see a change (our estimate).";
    return"If used about half the time: results are likely smaller and slower (our estimate).";
  }
  function whyDiffers(e,prof,pct,scaleDown){
    const w=[];const pop=e.population||{};
    if(pop.deeper_tones)w.push(cap(pop.deeper_tones)+".");
    if(pop.skin)w.push(`Studied in ${pop.skin}${pop.country?` (${pop.country})`:""}.`);
    if(scaleDown)w.push(pct==null?"This product doesn't state its strength.":"This product's strength is lower than in the study.");
    if(prof.sensitive&&e.can_irritate)w.push("Sensitive skin may need a slower start.");
    w.push("Your skin, the rest of your routine, sun exposure and how often you use it all change results.");
    return w.join(" ");
  }
  const weeksText=w=>w==null?"":w>=52?`${Math.round(w/52*10)/10} year${w>=104?"s":""}`.replace(/\.0 /," "):w>=12&&Math.abs(w/4.33-Math.round(w/4.33))<0.3?`${Math.round(w/4.33)} months`:`${Math.round(w)} weeks`;
  const cap=s=>s?s[0].toUpperCase()+s.slice(1):s;
  const uniq=a=>[...new Set(a)];

  /* ---------- a whole plan: per concern, the best-evidenced product drives the line ---------- */
  function planTimeline(products,prof,concerns){
    const out=[];const ps=(products||[]).filter(Boolean);
    for(const c of uniq(concerns||[])){
      let best=null;
      for(const p of ps){const t=productTimeline(p,prof,{concern:c});if(t.grade==="D"||t.concern!==c)continue;
        if(!best||RANK[t.grade]<RANK[best.t.grade]||(t.grade===best.t.grade&&(t.firstChangeWeek??99)<(best.t.firstChangeWeek??99)))best={p,t}}
      out.push({concern:c,label:LABEL[c]||c,product:best&&best.p,timeline:best&&best.t});
    }
    const spf=ps.find(p=>p.c==="Sunscreen");
    const sun=spf?productTimeline(spf,prof,{concern:"pigmentation"}):null;
    return{lines:out,sunscreen:spf?{product:spf,protective:sun&&sun.protective}:null};
  }

  /* ---------- what to expect at a given time since starting (for check-ins) ---------- */
  function expectedBy(t,weeks){
    if(!t||!t.stops)return null;
    const e=EV.entries.find(x=>x.id===t.entryId);if(!e)return null;
    const seen=e.checkpoints.filter(c=>c.representative!==false&&c.weeks<=weeks+0.5).sort((a,b)=>a.weeks-b.weeks);
    return seen.length?{weeks:seen[seen.length-1].weeks,plain:seen[seen.length-1].plain,ref:seen[seen.length-1].ref}:{weeks:null,first:e.checkpoints[0]&&e.checkpoints[0].weeks};
  }

  /* ---------- illustration: pure pixel maths (testable without a browser) ----------
     data: RGBA bytes, w x h. mask: Float32Array(w*h) 0..1 (the concern's region). s: 0..1 strength.
     Only masked pixels change; local averages are kept, so overall tone and undertone stay put, and the
     mean lightness inside the mask is never allowed to rise. */
  function boxBlur(src,w,h,r){
    const out=new Float32Array(src.length),tmp=new Float32Array(src.length);
    for(let y=0;y<h;y++){let acc=0;const row=y*w;for(let x=-r;x<=r;x++)acc+=src[row+Math.min(w-1,Math.max(0,x))];
      for(let x=0;x<w;x++){tmp[row+x]=acc/(2*r+1);acc+=src[row+Math.min(w-1,x+r+1)]-src[row+Math.max(0,x-r)]}}
    for(let x=0;x<w;x++){let acc=0;for(let y=-r;y<=r;y++)acc+=tmp[Math.min(h-1,Math.max(0,y))*w+x];
      for(let y=0;y<h;y++){out[y*w+x]=acc/(2*r+1);acc+=tmp[Math.min(h-1,y+r+1)*w+x]-tmp[Math.max(0,y-r)*w+x]}}
    return out;
  }
  function illustrate(data,w,h,mask,type,s){
    const out=new Uint8ClampedArray(data);s=Math.max(0,Math.min(0.9,s||0));if(!s)return out;
    const n=w*h,ch=[0,1,2].map(c=>{const a=new Float32Array(n);for(let i=0;i<n;i++)a[i]=data[i*4+c];return a});
    const r=Math.max(2,Math.round(Math.min(w,h)*(type==="texture"?0.008:type==="shine"?0.02:0.03)));
    const M=ch.map(a=>boxBlur(a,w,h,r));
    const Y=(R,G,B)=>0.2126*R+0.7152*G+0.0722*B;
    let y0=0,y1=0,mw=0,mw2=0;const res=[new Float32Array(n),new Float32Array(n),new Float32Array(n)];
    for(let i=0;i<n;i++){
      const m=mask[i];let R=ch[0][i],G=ch[1][i],B=ch[2][i];
      if(m>0){
        const k=s*m;
        if(type==="spots"||type==="texture"){R=M[0][i]+(R-M[0][i])*(1-k);G=M[1][i]+(G-M[1][i])*(1-k);B=M[2][i]+(B-M[2][i])*(1-k)}
        else if(type==="shine"){if(Y(R,G,B)>Y(M[0][i],M[1][i],M[2][i])){R-=k*Math.max(0,R-M[0][i]);G-=k*Math.max(0,G-M[1][i]);B-=k*Math.max(0,B-M[2][i])}}
        else if(type==="redness"){const e=(R-M[0][i])-((G-M[1][i])+(B-M[2][i]))/2;if(e>0)R-=k*e}
        y0+=m*Y(ch[0][i],ch[1][i],ch[2][i]);y1+=m*Y(R,G,B);mw+=m;mw2+=m*m;
      }
      res[0][i]=R;res[1][i]=G;res[2][i]=B;
    }
    const lift=mw?(y1-y0)/mw2:0;   // never let the region get lighter on average
    for(let i=0;i<n;i++){const m=mask[i];if(m<=0)continue;const d=lift>0?lift*m:0;
      out[i*4]=res[0][i]-d;out[i*4+1]=res[1][i]-d;out[i*4+2]=res[2][i]-d}
    return out;
  }
  // concern region from face landmarks (browser): face skin, without eyes, brows and lips
  function maskFromLandmarks(w,h,lm,type){
    if(typeof document==="undefined"||!lm||typeof TRYON_LM==="undefined")return null;
    const L=TRYON_LM,c=document.createElement("canvas");c.width=w;c.height=h;const g=c.getContext("2d");
    const pt=i=>[lm[i][0]*w,lm[i][1]*h];const poly=ids=>{const p=new Path2D();ids.forEach((i,k)=>{const[x,y]=pt(i);k?p.lineTo(x,y):p.moveTo(x,y)});p.closePath();return p};
    const eye=e=>poly(e.up.concat(e.lo.slice().reverse()));
    g.filter=`blur(${Math.round(w*0.01)}px)`;g.fillStyle="#fff";g.fill(poly(L.oval));
    g.globalCompositeOperation="destination-out";[eye(L.eyeR),eye(L.eyeL),poly(L.browR),poly(L.browL),poly(L.lipsOut)].forEach(p=>{g.lineWidth=w*0.02;g.stroke(p);g.fill(p)});
    const d=g.getImageData(0,0,w,h).data,m=new Float32Array(w*h);for(let i=0;i<w*h;i++)m[i]=d[i*4+3]/255;
    return m;
  }
  const sampleTexts=t=>t&&t.sample?[t.sample.summary,t.sample.who,t.sample.design,...t.sample.lines.map(l=>l.text)]:[];
  const textsOf=t=>!t||!t.stops?[t&&t.reason,...sampleTexts(t)].filter(Boolean):[...t.stops.flatMap(s=>[s.short,s.detail,s.half,s.why]),...t.notes,t.concernLabel,...sampleTexts(t)].filter(Boolean);

  return{STOPS,CONF,LABEL,BANNED,SAMPLES,sampleStudy,productTimeline,planTimeline,expectedBy,illustrate,maskFromLandmarks,entriesFor,strengthOf,textsOf,evidence:EV};
})();
