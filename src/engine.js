/* =====================================================================
   1. Catalogue preparation: flags re-derived from the ingredient list (B5)
   ===================================================================== */
const RX = {
  frag:/\b(parfum|fragrance|aroma|perfume|limonene|linalool|geraniol|citronellol|citral|eugenol|isoeugenol|coumarin|farnesol|cinnamal|hexyl cinnamal|amyl cinnamal|benzyl salicylate|benzyl benzoate|benzyl cinnamate|cinnamyl alcohol|anise alcohol|hydroxycitronellal|alpha-isomethyl ionone|butylphenyl methylpropional|evernia)\b/gi,
  eo:/(melaleuca alternifolia[^,]*oil|lavandula angustifolia[^,]*oil|rosa damascena flower oil|citrus [a-z]+ (?:peel|fruit|leaf) oil|mentha piperita[^,]*oil|eucalyptus[^,]*oil|cananga odorata[^,]*oil|rosmarinus officinalis[^,]*oil|citrus aurantium bergamia[^,]*oil|cymbopogon[^,]*oil|santalum[^,]*oil|pelargonium[^,]*oil)/gi,
  dry:/\b(alcohol denat\.?|sd alcohol[^,]*|isopropyl alcohol|ethanol)\b|(^|,\s*)alcohol\s*(,|$)/i,
  ret:/\b(retinol|retinal|retinyl [a-z]+|hydroxypinacolone retinoate|adapalene|tretinoin)\b/i,
  aha:/\b(glycolic acid|lactic acid|mandelic acid)\b/i,
  bha:/\bsalicylic acid\b/i,
};
const uniq=a=>[...new Set(a)];
const matchAll=(re,s)=>s?uniq((s.match(re)||[]).map(x=>x.trim().replace(/^,\s*/,""))):[];
let FLAG_FIXES=0;
for(const p of CAT){
  const f=p.fl, inci=p.i||"";
  p.fragHits=matchAll(RX.frag,inci); p.eoHits=matchAll(RX.eo,inci);
  const d={frag:p.fragHits.length>0,eo:p.eoHits.length>0,dry:RX.dry.test(inci),ret:RX.ret.test(inci),aha:RX.aha.test(inci),bha:RX.bha.test(inci)};
  const fl={frag:f[0]==="1",eo:f[1]==="1",dry:f[2]==="1",ret:f[3]==="1",aha:f[4]==="1",bha:f[5]==="1"};
  for(const k in d){ if(p.i && d[k]!==fl[k]) FLAG_FIXES++; }
  // the stricter of flag and ingredient list wins
  p.frag=d.frag||fl.frag; p.eo=d.eo||fl.eo; p.dryAlc=d.dry||fl.dry; p.ret=d.ret||fl.ret; p.aha=d.aha||fl.aha; p.bha=d.bha||fl.bha;
  p.preg=f[6]==="1";
  const sal=/salicylic acid\s*([\d.]+)%/i.exec(p.a||""); p.salPct=sal?parseFloat(sal[1]):(p.bha?1:0);
  const g=/glycolic acid\s*([\d.]+)%/i.exec(p.a||""); p.glyPct=g?parseFloat(g[1]):0;
  const r=/retinol\s*([\d.]+)%/i.exec(p.a||""); p.retPct=r?parseFloat(r[1]):0;
  p.leaveOn=!["Cleanser","Face mask"].includes(p.c);
  p.blankInci=!p.i;
}
const BY_ID=Object.fromEntries(CAT.map(p=>[p.id,p]));
const BRANDS=uniq(CAT.map(p=>p.b)).sort((a,b)=>b.length-a.length);
const COMPLEXION=["Foundation","Concealer","Compact powder","BB / CC cream"];

/* =====================================================================
   2. Profile + climate
   ===================================================================== */
const CITY_CLIMATE={"ahmedabad":"hot and dry / cold winters","bengaluru":"temperate","bangalore":"temperate","bhubaneswar":"humid coastal","chennai":"humid coastal","dehradun":"cool / hill","guwahati":"humid coastal","hyderabad":"hot semi-arid","jaipur":"hot and dry / cold winters","kochi":"humid coastal","kolkata":"humid coastal","lucknow":"hot and dry / cold winters","mumbai":"humid coastal","nagpur":"hot semi-arid","new delhi":"hot and dry / cold winters","delhi":"hot and dry / cold winters","pune":"temperate","shimla":"cool / hill","gurgaon":"hot and dry / cold winters","gurugram":"hot and dry / cold winters","noida":"hot and dry / cold winters","goa":"humid coastal"};
const MONTHS=["january","february","march","april","may","june","july","august","september","october","november","december"];
function emptyProfile(){return{noClog:false,state:null,skin:null,skinConfirmed:false,concerns:[],sensitive:false,avoidFrag:null,avoidEO:false,reactions:[],pregnancy:null,city:null,climate:null,month:new Date().getMonth(),budget:null,steps:3,tone:null,undertone:null,toneSource:null}}
let P=emptyProfile();
function dryWinter(prof=P){
  if(prof.weather&&prof.weather.avg)return !!(prof.weather.flags.dry&&prof.weather.avg.tmin<15);   // live: dry air and cold nights
  const cl=prof.climate;if(!cl)return false;
  if(cl==="cool / hill")return true;
  if(cl==="hot and dry / cold winters")return [10,11,0,1].includes(prof.month);
  return false;
}
function humid(prof=P){if(prof.weather&&prof.weather.avg)return !!(prof.weather.flags.humid||(prof.weather.avg.rh>=65&&prof.weather.avg.tmax>=28));return prof.climate==="humid coastal"}

/* reaction families: what the shopper says -> ingredient patterns to block */
const REACTIONS={
  "glycolic acid":{re:/glycolic acid/i,say:/glycolic/i},
  "salicylic acid":{re:/salicylic acid/i,say:/salicylic|\bbha\b/i},
  "vitamin c":{re:/ascorb(ic|yl)/i,say:/vitamin c|ascorbic|ascorbyl/i},
  "retinoids":{re:RX.ret,say:/retin(ol|oid|al)|vitamin a\b/i},
  "tea tree oil":{re:/melaleuca alternifolia/i,say:/tea ?tree|melaleuca/i},
  "lavender oil":{re:/lavandula/i,say:/lavender|lavandula/i},
  "linalool":{re:/linalool/i,say:/linalool/i},
  "niacinamide":{re:/niacinamide/i,say:/niacinamide/i},
  "lactic acid":{re:/lactic acid/i,say:/lactic/i},
  "azelaic acid":{re:/azelaic/i,say:/azelaic/i},
};

/* =====================================================================
   3. Hard filter (code, never the chat model) — guardrails A2 B1–B7 C5
   ===================================================================== */
function check(p,prof=P){
  const blocks=[],warns=[];
  const constrained=prof.avoidFrag||prof.avoidEO||prof.reactions.length||prof.pregnancy!==false||prof.sensitive;
  if(p.blankInci){ if(constrained)blocks.push(["B4","its ingredient list is missing, so I can't check it is safe for you"]); else warns.push(["B4","ingredients not listed"]); }
  if(prof.avoidFrag&&(p.frag||p.eo))blocks.push(["B1",p.fragHits.length?`it contains ${p.fragHits.slice(0,3).join(", ")} (fragrance)`:p.eoHits.length?`it contains ${p.eoHits[0]} (an essential oil, which is also a fragrance)`:"it is fragranced"]);
  if(prof.avoidEO&&p.eo)blocks.push(["B2",`it contains ${p.eoHits[0]||"an essential oil"}`]);
  for(const r of prof.reactions){const fam=REACTIONS[r];if(fam&&p.i&&fam.re.test(p.i))blocks.push(["B3",`it contains ${r}, which you reacted to`]);}
  if(prof.pregnancy!==false){
    if(p.ret)blocks.push(["A2","it contains a retinoid"]);
    else if(p.preg)blocks.push(["A2","it carries a pregnancy caution"]);
    else if(p.leaveOn&&p.salPct>=2)blocks.push(["A2",`it is a leave-on product with ${p.salPct}% salicylic acid`]);
  }
  if(prof.skin&&!p.st.includes(prof.skin))blocks.push(["B6",`it isn't suited to ${prof.skin} skin`]);
  else if(!prof.skinConfirmed&&p.st.length<4)blocks.push(["B6",`it only suits ${p.st.join(", ")} skin, and your skin type isn't confirmed yet`]);
  if(prof.skin==="oily"&&prof.concerns.includes("acne")&&p.com==="high")blocks.push(["B6","it has a high pore-clogging risk for acne-prone skin"]);
  else if(prof.noClog&&p.com==="high")blocks.push(["B6","it has a high pore-clogging risk, and you said you break out easily"]);
  if(prof.skin==="dry"&&dryWinter(prof)&&p.dryAlc)blocks.push(["B7","it contains drying alcohol, which is harsh on dry skin in this weather"]);
  if(prof.budget&&p.p!=null&&p.p>prof.budget)blocks.push(["C5",`it costs ₹${p.p}, above your ₹${prof.budget} budget`]);
  if(prof.sensitive&&(p.glyPct>=10||p.retPct>=0.5))warns.push(["A4","strong active for sensitive skin"]);
  return{ok:blocks.length===0,blocks,warns};
}

/* Ranker: suitability only. The sponsorship flag is never read here (D1). */
function score(p,prof=P){
  let s=0;
  const hit=p.con.filter(c=>prof.concerns.includes(c)).length; s+=hit*3;
  if(humid(prof)&&(p.fin==="matte"||/gel|matte|oil[- ]free/i.test(p.n)))s+=1;
  if((prof.skin==="dry"||dryWinter(prof))&&(p.fin==="dewy"||/ceramide|butyrospermum|squalane|shea/i.test(p.i||"")))s+=1;
  if(dryWinter(prof)&&p.dryAlc)s-=1.5;
  if(p.c==="Sunscreen"){ if((p.spf||0)>=30)s+=1; if(p.pa==="PA+++")s+=0.5; if(humid(prof)&&p.fin==="matte")s+=1.5; }
  if((prof.skin==="oily"||prof.concerns.includes("acne"))&&p.com==="low")s+=0.5;
  if(p.com==="medium"&&prof.skin==="oily")s-=0.5;
  if(prof.sensitive&&(p.glyPct>=10||p.retPct>=0.5))s-=2;
  if(p.blankInci)s-=3;
  s-=(p.p||0)/4000;
  return s;
}
function rank(cat,prof=P,opts={}){
  return CAT.filter(p=>p.c===cat&&(!opts.where||opts.where(p))&&check(p,prof).ok)
            .map(p=>({p,s:score(p,prof)})).sort((a,b)=>b.s-a.s||(a.p.p||0)-(b.p.p||0)||a.p.id.localeCompare(b.p.id)).map(x=>x.p);
}

/* Explainer: a one-line reason from the shopper's own profile (F3) */
function reason(p,prof=P){
  const bits=[];
  const hit=p.con.filter(c=>prof.concerns.includes(c));
  if(p.a)bits.push(p.a.replace(/,\s*/g," + "));
  if(hit.length)bits.push(`targets ${hit.join(" and ")}`);
  if(prof.skin)bits.push(`suits ${prof.skin} skin`);
  if(prof.avoidFrag)bits.push("fragrance-free");
  if((prof.skin==="oily"||prof.concerns.includes("acne"))&&p.com==="low")bits.push("low pore-clogging risk");
  if(p.c==="Sunscreen"&&p.spf)bits.push(`SPF ${p.spf}${p.pa?" "+p.pa:""}${p.fin?", "+p.fin+" finish":""}`);
  else if(humid(prof)&&p.fin==="matte")bits.push("matte finish for humid weather");
  if((prof.skin==="dry"||dryWinter(prof))&&/ceramide|butyrospermum|squalane/i.test(p.i||""))bits.push("barrier-supporting ceramides/shea/squalane");
  if(dryWinter(prof)&&!p.dryAlc&&prof.skin==="dry")bits.push("no drying alcohol");
  return bits.slice(0,4).join(" · ");
}
const isActive=p=>p.aha||p.bha||p.ret||/vitamin c 1[0-9]|vitamin c [2-9]\d/i.test(p.a||"");

/* =====================================================================
   4. Routine builder — B8 (no clashing actives), AM ends with SPF
   ===================================================================== */
const PLAN={AM:{2:["Cleanser","Sunscreen"],3:["Cleanser","Moisturiser","Sunscreen"],4:["Cleanser","Serum","Moisturiser","Sunscreen"]},
            PM:{2:["Cleanser","Moisturiser"],3:["Cleanser","Serum","Moisturiser"],4:["Cleanser","Toner","Serum","Moisturiser"]}};
function buildRoutine(when,prof=P){
  const steps=PLAN[when][Math.min(4,Math.max(2,prof.steps||3))];
  const picks=[],gaps=[],notes=[];
  let hasRet=false,hasAcid=false;
  // choose the treatment step first so the others can avoid clashes
  const order=[...steps].sort((a,b)=>(b==="Serum")-(a==="Serum"));
  const chosen={};
  for(const cat of order){
    const where=p=>{
      if(when==="AM"&&(p.ret||p.aha||(p.bha&&p.leaveOn)))return false;     // acids/retinoids at night only
      if(hasRet&&(p.aha||p.bha))return false;                                  // never retinoid + acid in one routine
      if(hasAcid&&p.ret)return false;
      if(Object.values(chosen).some(q=>q.id===p.id))return false;
      return true;
    };
    const list=rank(cat,prof,{where});
    if(!list.length){gaps.push(cat);continue}
    const p=list[0];chosen[cat]=p;
    if(p.ret)hasRet=true; if(p.aha||p.bha)hasAcid=true;
  }
  for(const cat of steps)if(chosen[cat])picks.push({cat,p:chosen[cat]});
  if(hasRet||hasAcid)notes.push("A4");
  // sponsored slot: same checks, labelled, separate (D1/D2)
  const spCands=CAT.filter(p=>p.sp&&steps.includes(p.c)&&!picks.some(x=>x.p.id===p.id));
  const spPass=spCands.filter(p=>check(p,prof).ok).sort((a,b)=>score(b,prof)-score(a,prof));
  const spBlocked=spCands.filter(p=>!check(p,prof).ok);
  return{when,steps,picks,gaps,notes,sponsored:spPass[0]||null,spBlocked};
}

/* =====================================================================
   5. Face reader (port of the aaina_face_reader library)
   ===================================================================== */
const MONK_HEX={1:"#f6ede4",2:"#f3e7db",3:"#f7ead0",4:"#eadaba",5:"#d7bd96",6:"#a07e56",7:"#825c43",8:"#604134",9:"#3a312a",10:"#292420"};
const MONK_LABEL={1:"very light",2:"very light",3:"light",4:"light",5:"medium",6:"medium",7:"medium-deep",8:"deep",9:"deep",10:"very deep"};
const lin=c=>{c/=255;return c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4)};
const flab=t=>t>0.008856?Math.cbrt(t):7.787*t+16/116;
function rgb2lab(r,g,b){const R=lin(r),G=lin(g),B=lin(b);const X=(R*0.4124+G*0.3576+B*0.1805)/0.95047,Y=R*0.2126+G*0.7152+B*0.0722,Z=(R*0.0193+G*0.1192+B*0.9505)/1.08883;const fx=flab(X),fy=flab(Y),fz=flab(Z);return[116*fy-16,500*(fx-fy),200*(fy-fz)]}
function lab2rgb(L,a,b){const fy=(L+16)/116,fx=fy+a/500,fz=fy-b/200;const inv=t=>t**3>0.008856?t**3:(t-16/116)/7.787;const X=inv(fx)*0.95047,Y=inv(fy),Z=inv(fz)*1.08883;let R=X*3.2406+Y*-1.5372+Z*-0.4986,G=X*-0.9689+Y*1.8758+Z*0.0415,B=X*0.0557+Y*-0.2040+Z*1.0570;const g=c=>Math.round(255*Math.min(1,Math.max(0,c<=0.0031308?12.92*c:1.055*Math.pow(c,1/2.4)-0.055)));return[g(R),g(G),g(B)]}
const hex2rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
const MONK_LAB={};for(const t in MONK_HEX)MONK_LAB[t]=rgb2lab(...hex2rgb(MONK_HEX[t]));
const lch=([L,a,b])=>[L,Math.hypot(a,b),Math.atan2(b,a)*180/Math.PI];
function toneDist(x,y){const[L1,C1,h1]=lch(x),[L2,C2,h2]=lch(y);const dH=2*Math.sqrt(Math.max(C1*C2,0))*Math.sin((h1-h2)*Math.PI/360);return Math.hypot(L1-L2,0.5*(C1-C2),0.5*dH)}
const FR={minShortSide:480,minScene:45,maxHigh:0.06,maxLow:0.12,minSharp:18,maxCast:1.40,minSkin:0.40,maxCheekGap:9,maxSpread:1,maxAmb:0.80,utMargin:2.5,minConf:0.60,coolBelow:50,warmFrom:60,oliveFrom:72,maxAttempts:3,minOvalSkin:0.35,closeAmb:0.55,maxSceneWhite:0.30,nearRef:4};
const TIPS={TOO_DARK:"Move somewhere brighter, ideally facing a window in daylight.",LOW_RESOLUTION:"Use your phone's main camera at full quality.",NO_FACE:"Fit your whole face inside the oval and look straight at the camera.",OVEREXPOSED:"Turn off the flash and move out of direct sunlight.",UNDEREXPOSED:"Find softer, even light; part of your face is in deep shadow.",BLURRY:"Hold the phone steady and tap your face to focus before taking it.",COLOUR_CAST:"The light looks yellow or coloured. Try natural daylight instead of indoor bulbs.",SKIN_HIDDEN:"Keep your cheeks and forehead clear of hair, glasses, masks or a heavy beard.",UNEVEN_LIGHT:"One side of your face is in shadow. Face the light so it falls evenly.",REGIONS_DISAGREE:"Your cheeks and forehead read as different shades, often from makeup or uneven light. Please use a bare face in even daylight.",TONE_AMBIGUOUS:"Your skin sits between two shades on our scale. One more photo in daylight will help.",UNDERTONE_AMBIGUOUS:"I can't tell your undertone clearly. Natural daylight without filters helps most.",LOW_CONFIDENCE:"I'm not confident enough in this reading. Please try again in natural daylight."};
const JUDGEMENT=new Set(["TONE_AMBIGUOUS","UNDERTONE_AMBIGUOUS","LOW_CONFIDENCE"]);
function isSkin(L,a,b){const C=Math.hypot(a,b),h=Math.atan2(b,a)*180/Math.PI;return L>3&&L<98.5&&a>-2&&b>1&&C>(L<35?1.5:3)&&h>10&&h<110}
function median(arr){const s=Float64Array.from(arr).sort();const n=s.length;return n?(n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2):NaN}
function quant(arr,q){const s=Float64Array.from(arr).sort();return s[Math.min(s.length-1,Math.floor(q*(s.length-1)))]}
function sampleRegion(img,name,x,y,w,h){const W=img.width,H=img.height,d=img.data;const x0=Math.max(1,x|0),y0=Math.max(1,y|0),x1=Math.min(W-1,(x+w)|0),y1=Math.min(H-1,(y+h)|0);const px=[];let tot=0;for(let j=y0;j<y1;j++)for(let i=x0;i<x1;i++){let r=0,g=0,b=0;for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const k=((j+dy)*W+i+dx)*4;r+=d[k];g+=d[k+1];b+=d[k+2]}const lab=rgb2lab(r/9,g/9,b/9);tot++;if(isSkin(...lab))px.push(lab)}const frac=tot?px.length/tot:0;const box=[x,y,w,h];if(px.length<20)return{name,box,frac,lab:null,px:[]};const Ls=px.map(p=>p[0]);const lo=quant(Ls,0.15),hi=quant(Ls,0.85);let keep=px.filter(p=>p[0]>=lo&&p[0]<=hi);if(keep.length<10)keep=px;return{name,box,frac,lab:[0,1,2].map(c=>median(keep.map(p=>p[c]))),px:keep}}
function scaled(src,sx,sy,sw,sh,tw){const th=Math.max(1,Math.round(sh*tw/sw));const c=document.createElement("canvas");c.width=tw;c.height=th;const g=c.getContext("2d",{willReadFrequently:true});g.imageSmoothingEnabled=true;g.imageSmoothingQuality="high";g.drawImage(src,sx,sy,sw,sh,0,0,tw,th);return g.getImageData(0,0,tw,th)}
function estimateUndertone(lab){const[,a,b]=lab;const h=Math.atan2(b,a)*180/Math.PI;let ut,m,why;if(h<FR.coolBelow){ut="cool";m=FR.coolBelow-h;why="your skin leans pink-red rather than golden"}else if(h<FR.warmFrom){ut="neutral";m=Math.min(h-FR.coolBelow,FR.warmFrom-h);why="your skin has a balance of pink and golden tones"}else if(h<FR.oliveFrom){ut="warm";m=Math.min(h-FR.warmFrom,FR.oliveFrom-h);why="your skin leans golden-yellow rather than pink"}else{ut="olive";m=h-FR.oliveFrom;why="your skin leans golden with a slight green cast and very little redness"}return{ut,h,margin:m,why}}
function estimateTone(lab){const r=Object.keys(MONK_LAB).map(t=>[+t,toneDist(lab,MONK_LAB[t])]).sort((p,q)=>p[1]-q[1]);return{tone:r[0][0],second:r[1][0],amb:r[1][1]>1e-6?r[0][1]/r[1][1]:1}}
function readPhoto(src,oval){
  const W=src.width,H=src.height,full=src.getContext("2d",{willReadFrequently:true}).getImageData(0,0,W,H);const issues=[];
  if(Math.min(W,H)<FR.minShortSide)issues.push("LOW_RESOLUTION");
  const small=scaled(src,0,0,W,H,200);let lum=0;for(let k=0;k<small.data.length;k+=4)lum+=0.299*small.data[k]+0.587*small.data[k+1]+0.114*small.data[k+2];lum/=small.data.length/4;if(lum<FR.minScene)issues.push("TOO_DARK");
  {let wh=0;for(let k=0;k<small.data.length;k+=4)if(Math.min(small.data[k],small.data[k+1],small.data[k+2])>=250)wh++;if(wh/(small.data.length/4)>FR.maxSceneWhite)issues.push("OVEREXPOSED")}   // blown-out scene, even if the face itself isn't clipped
  const fw=oval.w*W,fh=oval.h*H,fx=oval.cx*W-fw/2,fy=oval.cy*H-fh/2;const sx=Math.max(0,fx),sy=Math.max(0,fy),sw=Math.min(W,fx+fw)-sx,sh=Math.min(H,fy+fh)-sy;
  {let cr=0,cg=0,cb=0,cn=0;const bx0=sx/W,by0=sy/H,bx1=(sx+sw)/W,by1=(sy+sh)/H;for(let j=0;j<small.height;j++)for(let i=0;i<small.width;i++){const u=i/small.width,v=j/small.height;if(u>=bx0&&u<=bx1&&v>=by0&&v<=by1)continue;const k=(j*small.width+i)*4;cr+=small.data[k];cg+=small.data[k+1];cb+=small.data[k+2];cn++}
   if(cn>200){const m=[cr/cn+1,cg/cn+1,cb/cn+1];if(Math.max(...m)/Math.min(...m)>FR.maxCast)issues.push("COLOUR_CAST")}}
  const face=scaled(src,sx,sy,sw,sh,128);let skin=0,inside=0,high=0,low=0;
  for(let j=0;j<face.height;j++)for(let i=0;i<face.width;i++){const nx=(i+0.5)/face.width-0.5,ny=(j+0.5)/face.height-0.5;if(nx*nx/0.25+ny*ny/0.25>1)continue;const k=(j*face.width+i)*4,r=face.data[k],g=face.data[k+1],b=face.data[k+2];inside++;if(isSkin(...rgb2lab(r,g,b)))skin++;if(Math.min(r,g,b)>=252)high++;if(Math.max(r,g,b)<=6)low++}
  if(!inside||skin/inside<FR.minOvalSkin){if(!issues.includes("COLOUR_CAST"))issues.push("NO_FACE");return{status:"RECAPTURE",issues,regions:[]}}   // a strong tint hides skin: say "lighting", not "no face"
  if(high/inside>FR.maxHigh&&!issues.includes("OVEREXPOSED"))issues.push("OVEREXPOSED");if(low/inside>FR.maxLow)issues.push("UNDEREXPOSED");
  const f2=scaled(src,sx,sy,sw,sh,256),gw=f2.width,gh=f2.height,gray=new Float32Array(gw*gh);for(let k=0;k<gw*gh;k++)gray[k]=0.299*f2.data[k*4]+0.587*f2.data[k*4+1]+0.114*f2.data[k*4+2];
  let s1=0,s2=0,n=0;for(let j=1;j<gh-1;j++)for(let i=1;i<gw-1;i++){const k=j*gw+i;const v=gray[k-1]+gray[k+1]+gray[k-gw]+gray[k+gw]-4*gray[k];s1+=v;s2+=v*v;n++}
  if((n?s2/n-(s1/n)**2:0)<FR.minSharp)issues.push("BLURRY");
  const s=Math.max(Math.round(0.13*fw),6);
  const regions=[sampleRegion(full,"cheek",fx+0.18*fw,fy+0.52*fh,s,s),sampleRegion(full,"cheek",fx+0.82*fw-s,fy+0.52*fh,s,s),sampleRegion(full,"forehead",fx+0.35*fw,fy+0.14*fh,0.30*fw,0.09*fh)];
  if(regions.some(r=>r.frac<FR.minSkin||!r.lab))issues.push("SKIN_HIDDEN");
  const usable=regions.filter(r=>r.lab),cheeks=usable.filter(r=>r.name==="cheek");
  if(cheeks.length===2&&Math.abs(cheeks[0].lab[0]-cheeks[1].lab[0])>FR.maxCheekGap)issues.push("UNEVEN_LIGHT");
  const pool=usable.flatMap(r=>r.px);if(!pool.length){if(!issues.includes("SKIN_HIDDEN"))issues.push("SKIN_HIDDEN");return{status:"RECAPTURE",issues,regions}}
  const lab=[0,1,2].map(c=>median(pool.map(p=>p[c])));const T=estimateTone(lab),U=estimateUndertone(lab);
  const rt=usable.map(r=>estimateTone(r.lab).tone),spread=Math.max(...rt)-Math.min(...rt);
  if(spread>FR.maxSpread)issues.push("REGIONS_DISAGREE");if(T.amb>FR.maxAmb)issues.push("TONE_AMBIGUOUS");if(U.margin<FR.utMargin)issues.push("UNDERTONE_AMBIGUOUS");
  const conf=(1-0.5*Math.max(0,Math.min(1,(T.amb-0.5)/0.5)))*(0.7+0.3*Math.min(1,U.margin/(2*FR.utMargin)))*(spread===0?1:spread===1?0.9:0.6)*(0.6+0.4*Math.min(1,Math.min(...regions.map(r=>r.frac))/0.8));
  if(conf<FR.minConf)issues.push("LOW_CONFIDENCE");
  const blocking=issues.filter(i=>i!=="UNDERTONE_AMBIGUOUS");
  const nearRefs=toneDist(MONK_LAB[T.tone],MONK_LAB[T.second])<FR.nearRef;   // e.g. Monk 1 and 2 are almost the same colour
  const closeCall=!issues.includes("TONE_AMBIGUOUS")&&Math.abs(T.tone-T.second)===1&&(T.amb>FR.closeAmb||nearRefs);
  return{status:blocking.length?"RECAPTURE":"OK",issues,regions,lab,tone:T.tone,second:T.second,ut:U.ut,why:U.why,conf:+conf.toFixed(2),candidates:uniq([T.tone,T.second]).sort((a,b)=>a-b),
    utUnsure:issues.includes("UNDERTONE_AMBIGUOUS"),closeCall,amb:+T.amb.toFixed(2)};
}
let photoAttempts=[];
function sessionRead(res){
  photoAttempts.push(res);
  if(res.status==="OK")return res;
  const good=photoAttempts.filter(a=>a.lab&&a.issues.every(i=>JUDGEMENT.has(i)));
  if(good.length>=2&&good.includes(res)){const lab=[0,1,2].map(c=>good.reduce((s,a)=>s+a.lab[c],0)/good.length);const T=estimateTone(lab),U=estimateUndertone(lab);
    if(T.amb<=FR.maxAmb&&U.margin>=FR.utMargin)return Object.assign(res,{status:"OK",tone:T.tone,ut:U.ut,why:U.why,conf:Math.max(res.conf,FR.minConf),averaged:good.length})}
  if(photoAttempts.length>=FR.maxAttempts){const readable=photoAttempts.filter(a=>a.tone);if(!readable.length)return Object.assign(res,{status:"ASK_USER",candidates:[]});const best=readable.reduce((p,q)=>q.conf>p.conf?q:p);return Object.assign({},best,{status:"ASK_USER",regions:res.regions})}
  return res;
}

/* =====================================================================
   6. Shade matching — C2 honest "shade not available"
   ===================================================================== */
/* C3: self-reported tone is corrected by the average gap to in-store measurements (learned from 1,122 instore_tone_checks) */
const SELF_BIAS={1:1,2:1,3:1,4:1,5:1,6:0,7:0,8:0,9:0,10:0};
const correctedTone=t=>Math.min(10,t+(SELF_BIAS[t]||0));
const selfReported=()=>P.toneSource&&/picked|told/.test(P.toneSource);
function matchTone(){return selfReported()?correctedTone(P.tone):P.tone}
function utPenalty(want,have){if(want===have)return 0;if(want==="neutral"||have==="neutral")return 0.5;if((want==="warm"&&have==="olive")||(want==="olive"&&have==="warm"))return 1;return 1.5}
function bestShade(p,tone,ut){let best=null;for(const[name,depth,und,hex,cov]of p.s||[]){const dd=Math.abs(depth-tone),up=utPenalty(ut,und),sc=dd+up;if(!best||sc<best.score)best={name,depth,und,hex,cov,score:sc,good:dd<=1&&up<=0.5}}return best}

/* =====================================================================
   7. Input guardrails
   ===================================================================== */
const G={
  inject:/\b(ignore (all |your |the |any )?(previous |prior )?(rules|instructions)|disregard (your|the) (rules|instructions)|system prompt|developer mode|jailbreak|i am (the |an )?(admin|developer|owner)|bypass|override (the|your)|recommend it anyway|show (it|me) anyway|don'?t care about (the )?(rules|safety|fragrance)|pretend (you|to be)|act as)\b/i,
  redflag:/\b(pain(ful)?|hurts?|hurting|spreading|bleed(s|ing)?|pus|ooz(e|ing)|swollen|swelling|fever|blisters?|open sores?|crust(ing|y)|infect(ed|ion)|hives|can'?t breathe|burn(s|ing)? (that )?(won'?t|doesn'?t) stop|mole (is )?(chang|grow|bleed|itch)|changing mole|lump)\b/i,
  rx:/\b(tretinoin|retin-?a|hydroquinone|clindamycin|isotretinoin|accutane|adapalene|steroid cream|hydrocortisone|clobetasol|betamethasone|mometasone|antibiotic|doxycycline|minocycline|ketoconazole|spironolactone|prescription|prescribe)\b/i,
  fair:/\b(fair(er|ness)( cream)?|whiten(ing)?|lighten(ing)? my skin|skin lightening|bleach(ing)? my (skin|face)|make me (white|lighter|fair)|gora|get rid of (my )?dark skin|too dark)\b/i,
  guarantee:/\b(guarantee(d)?|promise me|100 ?%|permanent(ly)?|overnight results|cure (my|it))\b/i,
  del:/\b(delete|forget|erase|remove|wipe)\b.*\b(my )?(data|profile|details|information|photo|everything)\b/i,
  beauty:/skin|face|routine|serum|moistur|sunscreen|spf|cleanser|toner|acne|pimple|spot|pigment|dull|tan|oil|dry|foundation|concealer|shade|tone|undertone|makeup|lip|kajal|eye|wrinkle|fine line|pore|glow|product|ingredient|fragrance|niacinamide|retinol|vitamin|acid|hydrat|barrier|mask|exfoli|blush|primer|compact|bb|cc cream|beauty|aaina|budget|pregnan|sensitive|react|allerg|photo|selfie|routine/i,
};
const BANNED_OUT=/\b(cure[sd]?|heal(s|ed)?|guarantee(d)?|100 ?%|permanent(ly)?|whiten(ing)?|fairness|fairer|lighten(ing)? (your|the) skin|eczema|psoriasis|rosacea|dermatitis|fungal|infection|tretinoin|hydroquinone|clindamycin|isotretinoin|steroid|antibiotic)\b/i;

/* =====================================================================
   8. Slot parsing from free text
   ===================================================================== */
const CONCERN_WORDS=[["acne",/acne|pimple|breakout|zit/i],["pigmentation",/pigment|dark spot|spots|uneven (skin )?tone|blemish/i],["dullness",/dull|glow|radian/i],["dehydration",/dehydrat|tight|flak/i],["oiliness",/oiliness|too oily|shine|greasy/i],["tanning",/\btan(ning|ned)?\b|sun ?tan/i],["redness",/redness|\bred\b(?! patch)/i],["fine lines",/fine line|wrinkle|anti-?ag|ageing|aging/i],["dark circles",/dark circle|under ?eye/i]];
const CATEGORY_WORDS=[["Serum",/serum/i],["Moisturiser",/moistu?ri[sz]er|cream for|night cream|face cream/i],["Sunscreen",/sunscreen|sun ?block|spf/i],["Cleanser",/cleanser|face ?wash/i],["Toner",/toner/i],["Exfoliant",/exfoli/i],["Face mask",/\bmask\b/i],["Eye cream",/eye cream/i],["Spot treatment",/spot treatment|spot gel/i],["Face oil",/face oil/i],["Primer",/primer/i],["Lip care",/lip balm|lip care/i],["Lipstick",/lipstick/i],["Kajal / eyeliner",/kajal|eyeliner/i],["Blush",/blush/i],["Foundation",/foundation/i],["Concealer",/concealer/i],["Compact powder",/compact|pressed powder/i],["BB / CC cream",/\b(bb|cc)( \/ cc)? cream\b/i]];
function parseSlots(t){
  const s={},low=t.toLowerCase();
  const sk=/\b(oily|dry|combination|combo|normal)\b(?=[^.]*\bskin)|\bskin (is|type is|feels)? ?(oily|dry|combination|normal)\b/i.exec(t);
  if(sk){const v=(sk[1]||sk[3]||"").toLowerCase();s.skin=v==="combo"?"combination":v}
  const cons=CONCERN_WORDS.filter(([,re])=>re.test(t)).map(([c])=>c);if(cons.length)s.concerns=cons;
  if(/(fragrance|perfume|scent)[- ]?(free|sensitive)|avoid (fragrance|perfume|scent)|no (fragrance|perfume)|fragrance (irritates|bothers)/i.test(t))s.avoidFrag=true;
  if(/essential oil/i.test(t)&&/avoid|no |free|react|allerg/i.test(t))s.avoidEO=true;
  if(/sensitive skin|skin is (very )?sensitive|i'?m sensitive|my skin reacts easily/i.test(t))s.sensitive=true;
  if(/\b(react(ed|ion)?|allerg(ic|y)|broke out|break out|irritat|sting|burn(ed|t)?)\b/i.test(t)){
    const rs=Object.entries(REACTIONS).filter(([,f])=>f.say.test(t)).map(([k])=>k);if(rs.length)s.reactions=rs;
    if(/fragrance|perfume/i.test(t))s.avoidFrag=true;
  }
  if(/\b(not|n't|no longer) (pregnant|expecting)/i.test(t))s.pregnancy=false;
  else if(/pregnan|expecting|breastfeed|nursing|trying to conceive/i.test(t))s.pregnancy=true;
  for(const c in CITY_CLIMATE)if(new RegExp("\\b"+c+"\\b","i").test(t)){s.city=c.replace(/\b\w/g,m=>m.toUpperCase());s.climate=CITY_CLIMATE[c];break}
  const mo=MONTHS.findIndex(m=>low.includes(m));if(mo>=0)s.month=mo;else if(/\bwinter\b/.test(low))s.month=11;else if(/\bmonsoon\b/.test(low))s.month=7;else if(/\bsummer\b/.test(low))s.month=4;
  const bud=/(?:₹|rs\.?|inr|under|below|budget(?: of| is)?|less than|within)\s*₹?\s*([\d,]{3,6})/i.exec(t);if(bud)s.budget=parseInt(bud[1].replace(/,/g,""));
  const st=/\b([2-4])[- ]?step/i.exec(t);if(st)s.steps=+st[1];
  const tn=/\b(?:tone|monk|depth|shade)\s*(?:is|of)?\s*(10|[1-9])\b/i.exec(t);if(tn)s.tone=+tn[1];
  const ut=/\b(warm|cool|neutral|olive)\b(?=\s*(undertone|skin|tone)?)/i.exec(t);if(ut&&/undertone|warm undertone|cool undertone|olive/i.test(t))s.undertone=ut[1].toLowerCase();
  const br=BRANDS.find(b=>low.includes(b.toLowerCase()));if(br)s.brand=br;
  return s;
}
function applySlots(s){
  const changed=[];
  for(const k of["skin","sensitive","avoidFrag","avoidEO","pregnancy","city","climate","month","budget","steps","tone","undertone"])if(s[k]!==undefined&&P[k]!==s[k]){P[k]=s[k];changed.push(k)}
  if(s.concerns){const before=P.concerns.length;P.concerns=uniq([...P.concerns,...s.concerns]);if(P.concerns.length!==before)changed.push("concerns")}
  if(s.reactions){const before=P.reactions.length;P.reactions=uniq([...P.reactions,...s.reactions]);if(P.reactions.length!==before)changed.push("reactions")}
  if(s.tone!==undefined)P.toneSource="told me";
  return changed;
}


/* ---- simulated example photos ---- */
const EXAMPLES=[{label:"Medium-deep, warm",lab:[45,10,22]},{label:"Deep, olive",lab:[24,2,9]},{label:"Light, cool",lab:[77,14,10]},{label:"Dim yellow room",lab:[45,10,22],dark:true},{label:"Between two shades",lab:[49,10.3,24]}];
function makeExample(ex){const W=900,H=1200,c=document.createElement("canvas");c.width=W;c.height=H;const g=c.getContext("2d");g.fillStyle=ex.dark?"rgb(120,92,40)":"rgb(165,165,165)";g.fillRect(0,0,W,H);const[r,gg,b]=lab2rgb(...ex.lab);g.fillStyle=`rgb(${r},${gg},${b})`;g.beginPath();g.ellipse(450,500,225,300,0,0,Math.PI*2);g.fill();g.fillStyle="rgba(30,20,20,.85)";for(const x of[306,594]){g.beginPath();g.ellipse(x,452,32,14,0,0,Math.PI*2);g.fill()}g.strokeStyle="rgba(90,40,40,.7)";g.lineWidth=8;g.beginPath();g.moveTo(400,665);g.quadraticCurveTo(450,690,500,665);g.stroke();const img=g.getImageData(0,0,W,H),d=img.data;let seed=7;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647};for(let k=0;k<d.length;k+=4){const n=(rnd()+rnd()+rnd()-1.5)*9;const f=ex.dark?0.32:1;d[k]=Math.max(0,Math.min(255,(d[k]+n)*f));d[k+1]=Math.max(0,Math.min(255,(d[k+1]+n)*f));d[k+2]=Math.max(0,Math.min(255,(d[k+2]+n)*f))}g.putImageData(img,0,0);return c}

