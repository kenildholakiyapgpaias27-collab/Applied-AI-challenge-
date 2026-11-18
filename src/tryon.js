/* =====================================================================
   Aaina virtual try-on
   - Three sources: live camera (mirrored), an uploaded photo, or an illustrated model face.
   - Face tracking: MediaPipe Face Landmarker, loaded from the CDN only when the try-on opens.
     Model faces ship with their landmarks, so they work offline.
   - Rendering: WebGL. Makeup is blended in OKLab with the photo's own texture and shading kept,
     so it reads as makeup, not paint. TRYON_COLOUR mirrors the shader maths in plain JS
     (used for the swatch previews and unit tests).
   - Everything runs on the device. Camera frames and photos are never uploaded or stored.
   ===================================================================== */

/* ---------- colour maths (pure, no DOM; mirrored in the fragment shader) ---------- */
const TRYON_COLOUR=(()=>{
  const clamp=(x,a,b)=>Math.min(b,Math.max(a,x)),mix=(a,b,t)=>a+(b-a)*t;
  const hexToRgb=h=>{const m=/^#?([0-9a-f]{6})$/i.exec(String(h||"").trim());if(!m)return null;const n=parseInt(m[1],16);return[(n>>16)&255,(n>>8)&255,n&255]};
  const rgbToHex=c=>"#"+c.map(v=>Math.round(clamp(v,0,255)).toString(16).padStart(2,"0")).join("");
  const s2l=c=>{c/=255;return c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4)};
  const l2s=c=>255*(c<=0.0031308?12.92*Math.max(0,c):1.055*Math.pow(Math.min(1,c),1/2.4)-0.055);
  const hexToLin=h=>{const c=hexToRgb(h);return c?c.map(s2l):null};
  const linToHex=l=>rgbToHex(l.map(v=>l2s(clamp(v,0,1))));
  const lum=c=>0.2126*c[0]+0.7152*c[1]+0.0722*c[2];
  const cbrt=x=>Math.sign(x)*Math.pow(Math.abs(x),1/3);
  function oklab([r,g,b]){
    const l=cbrt(0.4122214708*r+0.5363325363*g+0.0514459929*b),m=cbrt(0.2119034982*r+0.6806995451*g+0.1073969566*b),s=cbrt(0.0883024619*r+0.2817188376*g+0.6299787005*b);
    return[0.2104542553*l+0.7936177850*m-0.0040720468*s,1.9779984951*l-2.4285922050*m+0.4505937099*s,0.0259040371*l+0.7827717662*m-0.8086757660*s]}
  function fromOklab([L,a,b]){
    const l=(L+0.3963377774*a+0.2158037573*b)**3,m=(L-0.1055613458*a-0.0638541728*b)**3,s=(L-0.0894841775*a-1.2914855480*b)**3;
    return[4.0767416621*l-3.3077115913*m+0.2309699292*s,-1.2684380046*l+2.6097574011*m-0.3413193965*s,-0.0041960863*l-0.7034186147*m+1.7076147010*s].map(v=>Math.max(0,v))}
  const chroma=c=>{const o=oklab(c);return Math.hypot(o[1],o[2])};
  /* product data -> blend parameters */
  const COVER={sheer:0.38,light:0.45,medium:0.58,buildable:0.6,full:0.8};
  const coverageAlpha=cov=>COVER[String(cov||"medium").toLowerCase()]??COVER.medium;
  const baseFinish=f=>({matte:0,natural:1,satin:1,dewy:2,radiant:2}[String(f||"natural").toLowerCase()]??1);   // 0 matte, 1 natural, 2 dewy
  const lipFinish=f=>({matte:0,creme:1,satin:1,sheer:2,gloss:3}[String(f||"satin").toLowerCase()]??1);
  const lipAlpha=f=>[0.92,0.85,0.5,0.78][lipFinish(f)];
  /* shading of a pixel relative to the skin mean (1 = average lit skin) */
  const shadingK=(B,M)=>clamp(lum(B)/Math.max(lum(M),1e-4),0.2,1.6);
  /* foundation / BB / concealer / powder. S: pixel, B: local average (low frequency), M: skin mean, all linear RGB.
     The shade replaces the low-frequency colour (mixed in OKLab by coverage), then the pixel's own detail (S/B)
     is put back, so pores, shadows and highlights survive. A shade lighter than the skin picks up the grey,
     ashy cast real white pigments give on deeper skin. */
  function base(S,B,M,shadeLin,a,fin){
    const k=shadingK(B,M),F=shadeLin.map(v=>v*k),bo=oklab(B),fo=oklab(F);
    const mo=[0,1,2].map(i=>mix(bo[i],fo[i],a));
    const ash=clamp((fo[0]-bo[0])/0.25,0,1)*a;
    mo[1]*=1-0.55*ash;mo[2]*=1-0.55*ash;mo[2]-=0.012*ash;
    const b=fromOklab(mo),tex=1-0.35*a;
    let D=S.map((v,i)=>v/Math.max(B[i],1e-4));
    if(fin===0)D=D.map(d=>d>1?1+(d-1)*0.35:d);
    let out=b.map((v,i)=>v*Math.pow(D[i],tex));
    if(fin===2){const g=1+0.10*a*smooth(0.95,1.35,k);out=out.map(v=>v*g)}
    return out}
  function lip(S,B,lipMean,lipLin,a,fin){
    const k=clamp(lum(B)/Math.max(lum(lipMean),1e-4),0.2,1.8),T=lipLin.map(v=>v*k),bo=oklab(B),to=oklab(T);
    const b=fromOklab([0,1,2].map(i=>mix(bo[i],to[i],a)));
    const D=S.map((v,i)=>v/Math.max(B[i],1e-4)),dl=lum(D),tex=fin===0?0.6:1;
    let out=b.map((v,i)=>v*Math.pow(D[i],tex));
    if(fin===3)out=out.map(v=>v+0.35*a*smooth(1.04,1.25,dl)+0.05*smooth(1.0,1.2,k));
    else if(fin===1)out=out.map(v=>v+0.12*a*smooth(1.06,1.3,dl));
    return out}
  function blush(S,B,M,blushLin,a,fin){
    const k=shadingK(B,M),l=Math.max(lum(blushLin),1e-3);let c=blushLin.map(v=>v/l);const mx=Math.max(...c);c=c.map(v=>v/mx);
    const tinted=S.map((v,i)=>v*mix(1,c[i],0.55*a));
    const det=lum(S)/Math.max(lum(B),1e-4),pig=blushLin.map(v=>v*k*det);
    const to=oklab(tinted),po=oklab(pig);let out=fromOklab([0,1,2].map(i=>mix(to[i],po[i],0.22*a)));
    if(fin===2)out=out.map(v=>v*(1+0.06*a*smooth(1,1.3,k)));
    return out}
  function liner(S,B,M,linLin,a,shimmer){const k=shadingK(B,M);return S.map((v,i)=>mix(v,linLin[i]*(0.75+0.25*k)+(shimmer?0.4*linLin[i]+0.02:0),a))}
  function smooth(e0,e1,x){const t=clamp((x-e0)/(e1-e0),0,1);return t*t*(3-2*t)}
  /* what a shade looks like on a flat patch of skin (the swatch preview and the no-tracking fallback) */
  function onSkin(skinHex,shadeHex,cov,fin){const s=hexToLin(skinHex),c=hexToLin(shadeHex);if(!s||!c)return shadeHex;return linToHex(base(s,s,s,c,coverageAlpha(cov),baseFinish(fin)))}
  function deltaE(h1,h2){const a=oklab(hexToLin(h1)),b=oklab(hexToLin(h2));return 100*Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2])}
  return{hexToRgb,rgbToHex,hexToLin,linToHex,s2l,l2s,lum,oklab,fromOklab,chroma,coverageAlpha,baseFinish,lipFinish,lipAlpha,shadingK,base,lip,blush,liner,onSkin,deltaE}
})();

/* ---------- face-mesh landmark sets (MediaPipe Face Landmarker indices) ---------- */
const TRYON_LM={
  oval:[10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109],
  lipsOut:[61,146,91,181,84,17,314,405,321,375,291,409,270,269,267,0,37,39,40,185],
  lipsIn:[78,95,88,178,87,14,317,402,318,324,308,415,310,311,312,13,82,81,80,191],
  eyeR:{up:[33,246,161,160,159,158,157,173,133],lo:[33,7,163,144,145,153,154,155,133]},
  eyeL:{up:[263,466,388,387,386,385,384,398,362],lo:[263,249,390,373,374,380,381,382,362]},
  browR:[70,63,105,66,107,55,65,52,53,46],browL:[300,293,334,296,336,285,295,282,283,276],
  cheekR:[50,205,187,123,116,117,118,101],cheekL:[280,425,411,352,345,346,347,330],
  skin:[205,425,50,280,151,9,101,330],lip:[37,267,84,314,39,269,181,405]
};

const TRYON=(()=>{
  if(typeof document==="undefined")return null;
  const C=TRYON_COLOUR,LM=TRYON_LM;
  const MP_VER="0.10.35",MP_BASE=`https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VER}`;
  const MP_MODEL="https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
  const DEMO=(typeof TRYON_DEMO!=="undefined"&&TRYON_DEMO&&TRYON_DEMO.products)||{};
  const MODELS=(typeof TRYON_MODELS!=="undefined"&&TRYON_MODELS&&TRYON_MODELS.models)||[];
  const e=s=>typeof esc==="function"?esc(s):String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const money=v=>typeof rupee==="function"?rupee(v):"₹"+v;
  const TABS=[["face","Face",["Foundation","BB / CC cream","Concealer","Compact powder"]],["lips","Lips",["Lipstick"]],["cheeks","Cheeks",["Blush"]],["eyes","Eyes",["Kajal / eyeliner"]]];
  const SLOT={"Foundation":"base","BB / CC cream":"base","Concealer":"conc","Compact powder":"powder","Lipstick":"lips","Blush":"blush","Kajal / eyeliner":"liner"};
  const SLOT_LABEL={base:"Base",conc:"Concealer",powder:"Powder",lips:"Lips",blush:"Cheeks",liner:"Eyes"};

  /* ---------- state ---------- */
  const S={open:false,src:null,mode:null,model:null,stream:null,video:null,img:null,lm:null,lmS:null,tab:"face",cat:"Foundation",pid:null,
    look:{},compare:false,cmp:[],split:0.5,skinMean:[0.3,0.2,0.15],lipMean:[0.2,0.08,0.07],raf:0,lastDetect:0,detMs:[],noFaceSince:0,
    tracker:null,trackerP:null,fallback:null,snaps:[],gl:null,pushedHash:false,frameW:0,frameH:0,maskDirty:true,hover:null,sheetUp:false,added:new Set()};
  let root,stage,fit,cv,maskA,maskB,detCv;
  const mobile=()=>window.matchMedia("(max-width:767px)").matches;

  /* ---------- catalogue ---------- */
  const products=cat=>{const list=(typeof CAT!=="undefined"?CAT:[]).filter(p=>p.c===cat&&(SLOT[cat]&&(p.s&&p.s.length||DEMO[p.id])));
    return list.map(p=>({p,st:status(p)})).sort((a,b)=>(b.st.ok-a.st.ok)||((a.p.p||0)-(b.p.p||0)))};
  function shadesOf(p){
    if(p.s&&p.s.length)return p.s.map(([name,depth,und,hex,cov])=>({name,depth,und,hex,cov,fin:p.fin||"natural",demo:false}));
    const d=DEMO[p.id];return d?d.shades.map(s=>({name:s.name,hex:s.hex,fin:s.finish,demo:true})):[]}
  const profiled=()=>typeof DONE!=="undefined"&&DONE.has&&DONE.has("safety");
  function status(p){
    if(!profiled()||typeof check!=="function")return{ok:true,checked:false};
    const r=check(p);return{ok:r.ok,checked:true,why:r.blocks.length?r.blocks[0][1]:""}}
  function matchFor(p){
    if(!(p.s&&p.s.length)||typeof bestShade!=="function")return null;
    const tone=(typeof P!=="undefined"&&P.tone)||null;
    if(tone){const t=typeof matchTone==="function"?matchTone():tone,unsure=!P.undertone,ut=P.undertone||(typeof UNSURE_UNDERTONE!=="undefined"?UNSURE_UNDERTONE:"neutral");   /* matchTone corrects the known bias in self-picked tones */
      const m=bestShade(p,t,ut);if(!m)return null;
      const a=unsure&&typeof UNSURE_ALT!=="undefined"?bestShade(p,t,UNSURE_ALT):null;   /* not sure of undertone: also offer the warm match (most common) */
      return{name:m.name,good:m.good,label:m.good?"Your match":"Closest to you",you:true,alt:a&&a.name!==m.name?a.name:null}}
    if(S.model){const m=bestShade(p,S.model.monk,S.model.undertone);return m?{name:m.name,good:m.good,label:"Matches this model",you:false}:null}
    return null}
  const hasPlan=()=>typeof PL!=="undefined"&&!!PL;
  const inPlan=id=>hasPlan()&&((PL.extras||[]).some(x=>x.p.id===id)||PL.slots.some(s=>s.p&&s.p.id===id));
  const shadeInfo=s=>[s.name,s.depth?`Tone ${s.depth}`:"",s.und?`${s.und} undertone`:"",s.cov?`${s.cov} coverage`:"",s.demo?`${s.fin} · demo colour`:""].filter(Boolean).join(" · ");

  /* ---------- icons (simple line drawings) ---------- */
  const ic=d=>`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const ICON={
    camera:ic('<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>'),
    upload:ic('<path d="M12 15V4m0 0L8 8m4-4 4 4"/><path d="M5 14v5h14v-5"/>'),
    face:ic('<circle cx="12" cy="12" r="8.5"/><path d="M9 10h.01M15 10h.01M9 15c1.7 1.3 4.3 1.3 6 0"/>'),
    swap:ic('<path d="M4 8h14l-3-3M20 16H6l3 3"/>'),
    grid:ic('<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>'),
    snap:ic('<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>'),
    reset:ic('<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3"/><path d="M4 4.5v4h4"/>'),
    lock:ic('<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>')};

  /* ---------- DOM ---------- */
  function build(){
    root=document.createElement("section");root.id="tryon";root.className="tryon";root.hidden=true;
    root.setAttribute("role","dialog");root.setAttribute("aria-modal","true");root.setAttribute("aria-label","Virtual try-on");
    root.innerHTML=`<header class="to-bar"><div><span class="eyebrow">Aaina</span><h2>Try it on</h2></div><button type="button" class="to-x" data-to="close" aria-label="Close try-on">✕</button></header>
      <div class="to-main">
        <div class="to-left">
          <section class="to-start" data-pane="start">
            <h3 class="to-h">How would you like to try?</h3>
            <div class="to-ways">
              <button type="button" class="to-way" data-to="consent"><span class="to-wayic">${ICON.camera}</span><b>Use my camera</b><small>A live mirror that follows your face</small></button>
              <label class="to-way" tabindex="0"><span class="to-wayic">${ICON.upload}</span><b>Upload a photo</b><small>A clear, front-facing photo works best</small><input type="file" accept="image/*" data-to="file" hidden></label>
              <div class="to-way to-way-models"><span class="to-wayic">${ICON.face}</span><b>Try on a model</b><small>Six faces, fair to very deep</small>
                <div class="to-models">${MODELS.map((m,i)=>`<button type="button" class="to-model" data-to="model" data-i="${i}" aria-label="Model face: ${e(m.label)}, about Monk tone ${m.monk}"><span class="to-mimg"><img src="${m.src}" alt=""></span><span class="to-mlab">${e(m.label)}</span><span class="to-mclose">Closest to you</span></button>`).join("")}</div></div>
            </div>
            <p class="to-consentnote">${ICON.lock}<span>Your camera and photos stay on this device. Frames are processed in your browser and never uploaded or stored.</span></p>
            <p class="to-tip">Tip: face a window or soft, even light, with no beauty filter. Model faces are computer-rendered, not photos of real people.</p>
          </section>
          <section class="to-consent" data-pane="consent" hidden>
            <h3 class="to-h">Before your camera turns on</h3>
            <ul><li>Your camera feed is processed <b>on this device</b>, in your browser.</li><li>Frames are <b>never uploaded or stored</b>. Nothing is recorded.</li><li>You can <b>stop the camera</b> at any time.</li></ul>
            <p class="small muted">The face tracker (Google MediaPipe) downloads once from a public CDN. Your images never leave the device.</p>
            <div class="to-row"><button type="button" class="btn primary" data-to="camera">Turn on camera</button><button type="button" class="btn ghost" data-to="start">Not now</button></div>
          </section>
          <section class="to-stagewrap" data-pane="stage" hidden>
            <div class="to-stage">
              <div class="to-fit"><canvas class="to-cv" aria-label="Try-on preview"></canvas>
                <div class="to-divider"><span class="to-lbl b">Before</span><span class="to-lbl a">After</span>
                  <div class="to-handle" role="slider" tabindex="0" aria-label="Before and after: drag to compare with and without makeup" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"><span class="to-grip" aria-hidden="true">‹›</span></div></div>
                <div class="to-tiles" hidden></div>
              </div>
              <div class="to-tools" role="toolbar" aria-label="Try-on tools">
                <button type="button" class="to-tool" data-to="start" title="Switch input" aria-label="Switch input">${ICON.swap}</button>
                <button type="button" class="to-tool" data-to="compare" title="Compare shades" aria-label="Compare shades" aria-pressed="false">${ICON.grid}</button>
                <button type="button" class="to-tool" data-to="snap" title="Save snapshot to this device" aria-label="Save snapshot">${ICON.snap}</button>
                <button type="button" class="to-tool" data-to="clear" title="Reset look" aria-label="Reset look">${ICON.reset}</button>
              </div>
              <button type="button" class="to-stop" data-to="stop" hidden>Stop camera</button>
              <div class="to-face" role="status" aria-live="polite" hidden></div>
              <div class="to-toast" role="status" aria-live="polite" hidden></div>
              <button type="button" class="btn to-cmpdone" data-to="compare" hidden>Done comparing</button>
            </div>
          </section>
          <section class="to-fallback" data-pane="fallback" hidden></section>
        </div>
        <aside class="to-panel" aria-label="Products and shades">
          <button type="button" class="to-grab" aria-label="Show all products" aria-expanded="false"><span></span></button>
          <div class="to-tabs" role="tablist">${TABS.map(([k,l])=>`<button type="button" role="tab" data-tab="${k}">${l}</button>`).join("")}</div>
          <div class="to-scroll">
            <div class="to-cats"></div>
            <div class="to-prods" role="listbox" aria-label="Products"></div>
            <div class="to-detail"></div>
            <p class="to-note">Preview only. Screen colours vary; your shade match is based on your tone and undertone.</p>
          </div>
        </aside>
        <footer class="to-foot" aria-label="Your look"></footer>
      </div>`;
    document.body.appendChild(root);
    stage=root.querySelector(".to-stage");fit=root.querySelector(".to-fit");cv=root.querySelector(".to-cv");
    maskA=document.createElement("canvas");maskB=document.createElement("canvas");detCv=document.createElement("canvas");
    root.addEventListener("click",onClick);
    root.querySelector("[data-to=file]").addEventListener("change",ev=>{const f=ev.target.files&&ev.target.files[0];ev.target.value="";if(f)useFile(f)});
    root.querySelector(".to-way[tabindex]").addEventListener("keydown",ev=>{if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();root.querySelector("[data-to=file]").click()}});
    root.addEventListener("keydown",ev=>{if(ev.key==="Escape"){if(S.compare)toggleCompare(false);else close()}});
    root.addEventListener("pointerover",ev=>{const b=ev.target.closest&&ev.target.closest(".to-sw");if(b){S.hover=+b.dataset.shade;swInfo()}});
    root.addEventListener("pointerout",ev=>{const b=ev.target.closest&&ev.target.closest(".to-sw");if(b){S.hover=null;swInfo()}});
    root.addEventListener("focusin",ev=>{const b=ev.target.closest&&ev.target.closest(".to-sw");if(b){S.hover=+b.dataset.shade;swInfo()}});
    wireHandle();wireSheet();
    if("ResizeObserver"in window)new ResizeObserver(()=>{if(S.open&&S.src){layout();kick()}}).observe(stage);
  }
  const pane=name=>{root.querySelectorAll("[data-pane]").forEach(x=>x.hidden=x.dataset.pane!==name);root.dataset.pane=name;if(name==="start")markClosest()};
  /* the model face closest to the user's tone and undertone, if we know them */
  function closestModel(){
    const tone=typeof P!=="undefined"&&P.tone;if(!tone||!MODELS.length)return -1;const ut=P.undertone||null;
    let best=-1,bs=1e9;MODELS.forEach((m,i)=>{const sc=Math.abs(m.monk-tone)+(ut&&m.undertone!==ut?(typeof utPenalty==="function"?utPenalty(ut,m.undertone)*0.4:0.6):0);if(sc<bs){bs=sc;best=i}});return best}
  function markClosest(){const k=closestModel();root.querySelectorAll(".to-model").forEach((b,i)=>{const on=i===k;b.classList.toggle("closest",on);const l=b.getAttribute("aria-label").replace(/ \(closest to you\)$/,"");b.setAttribute("aria-label",on?l+" (closest to you)":l)})}
  function onClick(ev){
    const t=ev.target.closest("[data-to],[data-tab],[data-cat],[data-pid],[data-shade],[data-rm],[data-pick]");if(!t||!root.contains(t))return;
    if(t.dataset.tab){S.tab=t.dataset.tab;S.cat=TABS.find(x=>x[0]===S.tab)[2][0];S.pid=null;renderPanel();return}
    if(t.dataset.cat){S.cat=t.dataset.cat;S.pid=null;renderPanel();return}
    if(t.dataset.pid){pickProduct(t.dataset.pid);return}
    if(t.dataset.shade!=null){pickShade(+t.dataset.shade);return}
    if(t.dataset.rm){delete S.look[t.dataset.rm];renderPanel();kick();fallbackRender();return}
    if(t.dataset.pick!=null){const c=S.cmp[+t.dataset.pick];if(c){S.look[c.slot]={p:c.p,s:c.s};toggleCompare(false);toast(`Picked ${c.s.name}`)}return}
    const a=t.dataset.to;
    if(a==="close")close();
    else if(a==="consent"){stopCamera();pane("consent")}
    else if(a==="start"){stopCamera();S.src=null;toggleCompare(false,true);pane("start")}
    else if(a==="camera")startCamera();
    else if(a==="stop"){stopCamera();S.src=null;pane("start")}
    else if(a==="model")useModel(+t.dataset.i);
    else if(a==="compare")toggleCompare(!S.compare);
    else if(a==="snap")snapshot();
    else if(a==="addlook")addLook();
    else if(a==="clear"){S.look={};S.split=0.5;drawDivider();renderPanel();kick();fallbackRender();toast("Look cleared")}
  }

  /* ---------- panel ---------- */
  function renderPanel(){
    if(!root)return;
    root.querySelectorAll("[data-tab]").forEach(b=>{const on=b.dataset.tab===S.tab;b.classList.toggle("on",on);b.setAttribute("aria-selected",on);b.tabIndex=on?0:-1});
    const cats=TABS.find(x=>x[0]===S.tab)[2];
    root.querySelector(".to-cats").innerHTML=cats.length>1?cats.map(c=>`<button type="button" class="to-cat${c===S.cat?" on":""}" aria-pressed="${c===S.cat}" data-cat="${e(c)}">${e(c)}</button>`).join(""):"";
    const list=products(S.cat);
    if(!S.pid||!list.some(x=>x.p.id===S.pid)){const cur=S.look[SLOT[S.cat]];S.pid=cur&&cur.p.c===S.cat?cur.p.id:(list[0]&&list[0].p.id)||null}
    root.querySelector(".to-prods").innerHTML=list.length?list.map(({p,st})=>{const m=matchFor(p),demo=!(p.s&&p.s.length);
      const chips=[m&&m.you&&m.good?`<span class="to-chip match">Your match</span>`:"",demo?`<span class="to-chip demo">Demo colour</span>`:"",st.ok?"":`<span class="to-chip bad">Not suitable for you</span>`].join("");
      return`<button type="button" role="option" class="to-prod${p.id===S.pid?" on":""}${st.ok?"":" bad"}" aria-selected="${p.id===S.pid}" data-pid="${p.id}">
        <span class="to-dots" aria-hidden="true">${shadesOf(p).slice(0,4).map(s=>`<i style="background:${e(s.hex)}"></i>`).join("")}</span>
        <span class="to-pt"><b>${e(p.n.replace(p.b+" ",""))}</b><small>${e(p.b)}</small></span><span class="to-pp">${money(p.p)}</span>
        ${chips?`<span class="to-chips">${chips}</span>`:""}</button>`}).join(""):`<p class="small muted">No products in this category.</p>`;
    renderDetail();renderFoot();centerSel();
  }
  /* keep the selected product and shade in view in the horizontal strips */
  function centerSel(){for(const[box,sel]of[[".to-prods",".to-prod.on"],[".to-shades",".to-sw.on"]]){const b=root.querySelector(box),el=b&&b.querySelector(sel);if(!el||b.scrollWidth<=b.clientWidth)continue;b.scrollLeft=Math.max(0,el.offsetLeft-(b.clientWidth-el.offsetWidth)/2)}}
  function renderDetail(){
    const box=root.querySelector(".to-detail"),p=S.pid&&typeof BY_ID!=="undefined"?BY_ID[S.pid]:null;if(!p){box.innerHTML="";return}
    const sh=shadesOf(p),st=status(p),m=matchFor(p),slot=SLOT[p.c],cur=S.look[slot],curName=cur&&cur.p.id===p.id?cur.s.name:null,demo=sh.some(s=>s.demo);
    box.innerHTML=`<div class="to-ph"><b>${e(p.n)}</b><small>${e(p.c)} · ${money(p.p)}${p.fin?` · ${e(p.fin)} finish`:""}</small></div>
      ${st.ok?"":`<p class="to-bad" role="status"><b>Not suitable for you</b>: ${e(st.why)}. You can still preview it, but it won't be added to your plan.</p>`}
      ${demo?`<p class="to-demo">Demo colour, not real product data</p>`:""}
      ${S.compare?`<p class="to-cmphint">Tap shades to compare (${S.cmp.length}/4). The oldest is replaced after four.</p>`:""}
      <div class="to-shades" role="listbox" aria-label="Shades of ${e(p.n)}">${sh.map((s,i)=>{const isM=m&&m.name===s.name,on=S.compare?S.cmp.some(c=>c.p.id===p.id&&c.s.name===s.name):curName===s.name;
        const isA=m&&m.alt===s.name;
        return`<button type="button" role="option" aria-selected="${on}" class="to-sw${on?" on":""}${isM?" match":""}${isA?" alt":""}" data-shade="${i}" title="${e(shadeInfo(s))}" aria-label="${e(shadeInfo(s))}${isM?`, ${e(m.label)}`:""}${isA?", also try: warm match":""}"><i style="background:${e(s.hex)}"></i></button>`}).join("")}</div>
      ${m&&m.alt?`<p class="to-althint">Not sure of your undertone? This is a neutral match. The ringed dot is the warm match, the most common undertone: <b>${e(m.alt)}</b>.</p>`:""}
      <p class="to-swinfo" aria-live="polite"></p>`;
    swInfo();
  }
  function swInfo(){
    const box=root&&root.querySelector(".to-swinfo"),p=S.pid&&BY_ID[S.pid];if(!box||!p)return;
    const sh=shadesOf(p),cur=S.look[SLOT[p.c]],m=matchFor(p);
    const s=S.hover!=null?sh[S.hover]:cur&&cur.p.id===p.id?cur.s:null;
    box.innerHTML=s?`<b>${e(s.name)}</b>${m&&m.name===s.name?` <span class="to-chip match">${e(m.label)}</span>`:""}<br><small>${e(shadeInfo(s).replace(s.name+" · ",""))}</small>`:`<small>Hover or tap a shade to see its name and depth.</small>`;
  }
  function lookItems(){return Object.entries(S.look).map(([k,v])=>({k,v,st:status(v.p)}))}
  function renderFoot(){
    const box=root.querySelector(".to-foot"),items=lookItems();
    const ids=[...new Set(items.map(x=>x.v.p.id))],total=ids.reduce((t,id)=>t+(BY_ID[id].p||0),0);
    const addable=items.filter(x=>x.st.ok&&x.st.checked&&!inPlan(x.v.p.id)),bad=items.filter(x=>!x.st.ok);
    const hint=!items.length?"Pick shades in each tab to build a look."
      :bad.length?`${bad.length===1?"1 item isn't":`${bad.length} items aren't`} suitable for you and won't be added.`
      :!profiled()||!hasPlan()?"Finish the advisor to add this look to your plan."
      :!addable.length?"✓ In your plan":"";
    box.innerHTML=`<div class="to-lookchips"><span class="to-lookh">Your look</span>${items.map(({k,v,st})=>`<button type="button" class="to-lc${st.ok?"":" bad"}" data-rm="${k}" aria-label="Remove ${e(SLOT_LABEL[k])}: ${e(v.s.name)}"><i style="background:${e(v.s.hex)}"></i>${e(SLOT_LABEL[k])} · ${e(v.s.name)}${inPlan(v.p.id)?" ✓":""}<span aria-hidden="true">×</span></button>`).join("")||`<span class="small muted">Nothing yet</span>`}</div>
      <div class="to-total"><small>Total</small><b>${items.length?money(total):"–"}</b></div>
      <div class="to-addwrap"><button type="button" class="btn primary" data-to="addlook" ${addable.length&&hasPlan()?"":"disabled"}>Add look to my plan</button>${hint?`<small class="to-foothint">${e(hint)}</small>`:""}</div>`;
  }
  function pickProduct(id){
    S.pid=id;const p=BY_ID[id];const slot=SLOT[p.c];S.hover=null;
    if(S.compare)prefillCompare(p);
    else if(!(S.look[slot]&&S.look[slot].p.id===id)){const sh=shadesOf(p),m=matchFor(p);const i=m?Math.max(0,sh.findIndex(s=>s.name===m.name)):Math.floor(sh.length/2);if(sh[i])S.look[slot]={p,s:sh[i]}}
    renderPanel();kick();fallbackRender();if(S.compare)layout();
  }
  function pickShade(i){
    const p=BY_ID[S.pid];if(!p)return;const s=shadesOf(p)[i];if(!s)return;const slot=SLOT[p.c];
    if(S.compare){const k=S.cmp.findIndex(c=>c.p.id===p.id&&c.s.name===s.name);if(k>=0)S.cmp.splice(k,1);else{if(S.cmp.length>=4)S.cmp.shift();S.cmp.push({slot,p,s})}layout()}
    else S.look[slot]={p,s};
    renderPanel();kick();fallbackRender();
  }
  function prefillCompare(p){
    p=p||(S.pid&&BY_ID[S.pid]);if(!p)return;const sh=shadesOf(p),slot=SLOT[p.c],cur=S.look[slot],m=matchFor(p);
    let at=cur&&cur.p.id===p.id?sh.findIndex(s=>s.name===cur.s.name):m?sh.findIndex(s=>s.name===m.name):Math.floor(sh.length/2);at=Math.max(0,at);
    const idx=[at];for(let d=1;idx.length<Math.min(4,sh.length);d++){if(at+d<sh.length)idx.push(at+d);if(idx.length<4&&at-d>=0)idx.push(at-d)}
    S.cmp=idx.slice(0,4).sort((a,b)=>a-b).map(i=>({slot,p,s:sh[i]}));
  }
  function toggleCompare(on,quiet){
    if(!root)return;S.compare=!!on;S.cmp=[];if(on)prefillCompare();
    root.classList.toggle("cmp",S.compare);
    root.querySelectorAll("[data-to=compare]").forEach(b=>b.setAttribute("aria-pressed",S.compare));
    root.querySelector(".to-cmpdone").hidden=!S.compare;
    if(!quiet){layout();renderPanel();kick();}
  }
  function addLook(){
    if(!hasPlan())return;const items=lookItems().filter(x=>x.st.ok&&x.st.checked&&!inPlan(x.v.p.id));if(!items.length)return;
    PL.extras=PL.extras||[];
    for(const{v}of items)if(!PL.extras.some(x=>x.p.id===v.p.id))PL.extras.push({slot:{role:`${v.p.c} (try-on pick)`,when:`Shade: ${v.s.name}`},p:v.p});
    if(typeof META!=="undefined")META.extraIds=PL.extras.map(x=>({id:x.p.id,slot:x.slot}));
    if(typeof saveState==="function")saveState();
    if(typeof renderPlan==="function")renderPlan();
    renderFoot();toast(`Added ${items.length===1?items[0].v.p.n:`${items.length} products`} to your plan`);
  }
  function toast(t){const m=root.querySelector(".to-toast");m.textContent=t;m.hidden=false;m.classList.remove("show");void m.offsetWidth;m.classList.add("show");clearTimeout(toast.t);toast.t=setTimeout(()=>{m.classList.remove("show");setTimeout(()=>{m.hidden=true},200)},2600)}
  /* face-tracking state on the canvas: "busy", "finding", "noface" or "" (hidden) */
  function faceState(kind,text){
    const f=root.querySelector(".to-face");if(!kind){f.hidden=true;f.dataset.kind="";return}
    if(f.dataset.kind===kind&&f.dataset.text===(text||""))return;
    f.dataset.kind=kind;f.dataset.text=text||"";f.hidden=false;
    f.innerHTML=kind==="noface"?`<b>No face found.</b> Move into better light and face the camera. <button type="button" class="to-link" data-to="start">Try a photo or model</button>`
      :`<span class="to-pulse" aria-hidden="true"></span>${e(text||"Finding your face…")}`;
  }
  /* before/after handle: drag, or arrow keys */
  function setSplit(v){S.split=Math.min(1,Math.max(0,v));drawDivider();kick()}
  function wireHandle(){
    const h=root.querySelector(".to-handle");let drag=false;
    const at=ev=>{const r=fit.getBoundingClientRect();setSplit((ev.clientX-r.left)/Math.max(1,r.width))};
    h.addEventListener("pointerdown",ev=>{drag=true;h.setPointerCapture(ev.pointerId);ev.preventDefault();h.classList.add("drag")});
    h.addEventListener("pointermove",ev=>{if(drag)at(ev)});
    const end=ev=>{drag=false;h.classList.remove("drag");try{h.releasePointerCapture(ev.pointerId)}catch{}};
    h.addEventListener("pointerup",end);h.addEventListener("pointercancel",end);
    h.addEventListener("keydown",ev=>{const k={ArrowLeft:-0.05,ArrowRight:0.05,ArrowDown:-0.05,ArrowUp:0.05}[ev.key];if(k!=null){ev.preventDefault();setSplit(S.split+k)}else if(ev.key==="Home"){ev.preventDefault();setSplit(0)}else if(ev.key==="End"){ev.preventDefault();setSplit(1)}});
  }
  /* mobile bottom sheet: swipe up for the full product list, down to collapse */
  function wireSheet(){
    const panel=root.querySelector(".to-panel"),grab=root.querySelector(".to-grab");let y0=null;
    const set=up=>{S.sheetUp=up;root.classList.toggle("sheet-up",up);grab.setAttribute("aria-expanded",up);grab.setAttribute("aria-label",up?"Show fewer products":"Show all products")};
    grab.addEventListener("click",()=>set(!S.sheetUp));
    panel.addEventListener("pointerdown",ev=>{if(!mobile()||ev.target.closest(".to-prods,.to-shades,.to-cats"))return;y0=ev.clientY});
    panel.addEventListener("pointerup",ev=>{if(y0==null)return;const dy=ev.clientY-y0;y0=null;if(dy<-40)set(true);else if(dy>40)set(false)});
    panel.addEventListener("pointercancel",()=>{y0=null});
    S.setSheet=set;
  }

  /* ---------- fallback: swatches on your skin colour ---------- */
  function fallback(reason){
    S.fallback=reason;stopLoop();faceState("");toggleCompare(false,true);pane("fallback");fallbackRender();
  }
  function fallbackRender(){
    if(!S.fallback||!root)return;const box=root.querySelector("[data-pane=fallback]");
    const tone=(typeof P!=="undefined"&&P.tone)||(S.model&&S.model.monk)||5,skin=(typeof MONK_HEX!=="undefined"?MONK_HEX[tone]:"#d7bd96");
    const parts=Object.entries(S.look).map(([k,v])=>{const on=k==="lips"||k==="blush"||k==="liner"?v.s.hex:C.onSkin(skin,v.s.hex,v.s.cov,v.s.fin);
      return`<li><span class="to-fs"><i style="background:${skin}"></i><i style="background:${e(on)}"></i></span><div><b>${SLOT_LABEL[k]}: ${e(v.s.name)}</b><small>${e(v.p.n)}${v.s.demo?" · demo colour":""}</small></div></li>`});
    box.innerHTML=`<div class="to-fbmsg" role="status">${S.fallback}</div>
      <p class="small muted">Showing shades as swatches instead. Left: skin tone ${tone}. Right: the shade on that tone.</p>
      <ul class="to-fsl">${parts.join("")||"<li class='small muted'>Pick a shade on the right to see it here.</li>"}</ul>
      <div class="to-row"><button type="button" class="btn ghost" data-to="start">Try another way</button></div>`;
  }

  /* ---------- sources ---------- */
  async function startCamera(){
    S.fallback=null;S.mode="camera";pane("stage");faceState("busy","Starting your camera…");
    root.querySelector("[data-to=stop]").hidden=false;
    if(!glInit())return fallback("Your browser can't run the live try-on here (WebGL is off or unavailable).");
    try{S.stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"user",width:{ideal:960},height:{ideal:720}},audio:false})}
    catch(err){S.stream=null;return fallback(err&&err.name==="NotAllowedError"?"Camera permission was turned down. You can upload a photo or pick a model instead.":"I couldn't open a camera on this device. You can upload a photo or pick a model instead.")}
    const v=S.video||(S.video=Object.assign(document.createElement("video"),{muted:true,playsInline:true,autoplay:true}));v.setAttribute("playsinline","");
    v.srcObject=S.stream;try{await v.play()}catch{}
    await new Promise(r=>{if(v.readyState>=2)r();else v.onloadeddata=()=>r()});
    S.src=v;S.frameW=v.videoWidth;S.frameH=v.videoHeight;S.lm=S.lmS=null;S.noFaceSince=performance.now();S.detMs=[];
    faceState("busy","Loading face tracking…");
    const tr=await tracker("VIDEO");if(!tr)return fallback("Face tracking couldn't load (you may be offline). Showing shades as swatches.");
    if(S.mode!=="camera")return;faceState("finding","Finding your face…");setup();loop();
  }
  function stopCamera(){stopLoop();if(S.stream){S.stream.getTracks().forEach(t=>t.stop());S.stream=null}if(S.video){S.video.srcObject=null;if(S.src===S.video){S.src=null;S.lm=S.lmS=null}}if(root)root.querySelector("[data-to=stop]").hidden=true;if(S.mode==="camera")S.mode=null}
  async function useFile(f){
    stopCamera();S.fallback=null;S.mode="photo";S.model=null;pane("stage");faceState("busy","Reading your photo…");
    if(!glInit())return fallback("Your browser can't run the try-on here (WebGL is off or unavailable).");
    let img;try{img=await loadImage(URL.createObjectURL(f))}catch{return fallback("That file doesn't look like a photo I can open.")}
    S.src=toCanvas(img,1280);S.frameW=S.src.width;S.frameH=S.src.height;
    faceState("finding","Finding your face…");const tr=await tracker("IMAGE");
    if(!tr)return fallback("Face tracking couldn't load (you may be offline). Try a model face, or see shades as swatches.");
    let res;try{res=tr.detect(S.src)}catch{res=null}
    const lm=res&&res.faceLandmarks&&res.faceLandmarks[0];
    if(!lm)return fallback("No face found in that photo. Move into better light and face the camera, or try a model face.");
    S.lm=S.lmS=lm.map(p=>[p.x,p.y]);faceState("");setup();sampleColours();kick();
  }
  async function useModel(i){
    stopCamera();const m=MODELS[i];if(!m)return;S.fallback=null;S.mode="model";S.model=m;pane("stage");
    if(!glInit())return fallback("Your browser can't run the try-on here (WebGL is off or unavailable).");
    const img=await loadImage(m.src);S.src=toCanvas(img,1280);S.frameW=S.src.width;S.frameH=S.src.height;
    S.lm=S.lmS=m.landmarks.map(p=>p.slice());faceState("");setup();sampleColours();renderPanel();kick();
  }
  const loadImage=src=>new Promise((res,rej)=>{const im=new Image();im.onload=()=>res(im);im.onerror=rej;im.src=src});
  function toCanvas(img,max){const k=Math.min(1,max/Math.max(img.naturalWidth||img.width,img.naturalHeight||img.height));const c=document.createElement("canvas");c.width=Math.round((img.naturalWidth||img.width)*k);c.height=Math.round((img.naturalHeight||img.height)*k);c.getContext("2d").drawImage(img,0,0,c.width,c.height);return c}

  /* ---------- MediaPipe (lazy, pinned version) ---------- */
  function tracker(mode){
    if(!S.trackerP)S.trackerP=(async()=>{
      const vision=await withTimeout(import(/* pinned */`${MP_BASE}/vision_bundle.mjs`),25000);
      const files=await withTimeout(vision.FilesetResolver.forVisionTasks(`${MP_BASE}/wasm`),25000);
      const opts=d=>({baseOptions:{modelAssetPath:MP_MODEL,delegate:d},runningMode:"IMAGE",numFaces:1,outputFaceBlendshapes:false});
      try{return await withTimeout(vision.FaceLandmarker.createFromOptions(files,opts("GPU")),30000)}catch{return await withTimeout(vision.FaceLandmarker.createFromOptions(files,opts("CPU")),30000)}
    })().catch(()=>{S.trackerP=null;return null});
    return S.trackerP.then(async tr=>{if(!tr)return null;if(tr._aainaMode!==mode){await tr.setOptions({runningMode:mode});tr._aainaMode=mode}return tr});
  }
  const withTimeout=(p,ms)=>Promise.race([p,new Promise((_,rej)=>setTimeout(()=>rej(new Error("timeout")),ms))]);

  /* ---------- live loop ---------- */
  function loop(){
    stopLoop();
    const step=async now=>{
      S.raf=requestAnimationFrame(step);
      if(document.hidden||S.mode!=="camera"||!S.video||S.video.readyState<2)return;
      const tr=S.tracker;
      if(tr&&!S.busy&&now-S.lastDetect>=33){
        S.busy=true;S.lastDetect=now;
        const v=S.video,k=Math.min(1,256/Math.max(v.videoWidth,1));detCv.width=Math.round(v.videoWidth*k);detCv.height=Math.round(v.videoHeight*k);
        const dctx=detCv.getContext("2d",{willReadFrequently:true});dctx.drawImage(v,0,0,detCv.width,detCv.height);
        const t0=performance.now();let res=null;try{res=tr.detectForVideo(detCv,now)}catch{}
        const dt=performance.now()-t0;S.detMs.push(dt);if(S.detMs.length>30)S.detMs.shift();
        const lm=res&&res.faceLandmarks&&res.faceLandmarks[0];
        if(lm){const pts=lm.map(p=>[p.x,p.y]);S.lm=pts;S.lmS=S.lmS&&S.lmS.length===pts.length?S.lmS.map((q,i)=>[q[0]+(pts[i][0]-q[0])*0.6,q[1]+(pts[i][1]-q[1])*0.6]):pts;S.maskDirty=true;S.noFaceSince=0;
          if(++S.frameN%15===1)sampleColours(dctx,detCv.width,detCv.height);faceState("")}
        else{S.lm=null;if(!S.noFaceSince)S.noFaceSince=now;if(now-S.noFaceSince>4000)faceState("noface");else faceState("finding","Finding your face…")}
        if(S.detMs.length>=20&&avg(S.detMs)>150){S.busy=false;stopCamera();return fallback("This device is a bit slow for the live try-on. Try a photo or a model face, or see shades as swatches.")}
        S.busy=false}
      draw();
    };
    S.tracker=null;tracker("VIDEO").then(tr=>{S.tracker=tr});S.frameN=0;S.raf=requestAnimationFrame(step);
  }
  const avg=a=>a.reduce((x,y)=>x+y,0)/a.length;
  function stopLoop(){if(S.raf)cancelAnimationFrame(S.raf);S.raf=0}
  let kickQ=0;function kick(){if(S.mode==="camera")return;if(kickQ)return;kickQ=requestAnimationFrame(()=>{kickQ=0;draw()})}
  document.addEventListener("visibilitychange",()=>{if(!S.open)return;if(document.hidden)stopLoop();else if(S.mode==="camera"&&S.stream)loop()});

  /* sample the skin and lip mean colour at landmark points (linear RGB) */
  function sampleColours(ctx,w,h){
    if(!S.lm)return;
    if(!ctx){const k=Math.min(1,256/Math.max(S.frameW,1));detCv.width=Math.round(S.frameW*k);detCv.height=Math.round(S.frameH*k);ctx=detCv.getContext("2d",{willReadFrequently:true});ctx.drawImage(S.src,0,0,detCv.width,detCv.height);w=detCv.width;h=detCv.height}
    const at=ids=>{const acc=[0,0,0];let n=0;for(const i of ids){const p=S.lm[i];if(!p)continue;const x=Math.round(p[0]*w),y=Math.round(p[1]*h);if(x<1||y<1||x>=w-1||y>=h-1)continue;
      const d=ctx.getImageData(x-1,y-1,3,3).data;for(let k=0;k<36;k+=4){acc[0]+=C.s2l(d[k]);acc[1]+=C.s2l(d[k+1]);acc[2]+=C.s2l(d[k+2]);n++}}return n?acc.map(v=>v/n):null};
    S.skinMean=at(LM.skin)||S.skinMean;S.lipMean=at(LM.lip)||S.lipMean;
  }

  /* ---------- masks (2D canvas, one feature per colour channel) ---------- */
  const blurOK=(()=>{try{const c=document.createElement("canvas").getContext("2d");c.filter="blur(2px)";return c.filter==="blur(2px)"}catch{return false}})();
  function softFill(ctx,path,colour,blur,rule){
    ctx.save();
    if(blurOK){ctx.filter=`blur(${blur}px)`;ctx.fillStyle=colour;ctx.fill(path,rule||"nonzero")}
    else{ctx.shadowColor=colour;ctx.shadowBlur=blur*2;ctx.shadowOffsetX=10000;ctx.translate(-10000,0);ctx.fillStyle=colour;ctx.fill(path,rule||"nonzero")}
    ctx.restore()}
  function softStroke(ctx,pts,colour,width,blur){
    const p=new Path2D();pts.forEach((q,i)=>i?p.lineTo(q[0],q[1]):p.moveTo(q[0],q[1]));
    ctx.save();ctx.lineCap="round";ctx.lineJoin="round";ctx.lineWidth=width;
    if(blurOK){ctx.filter=`blur(${blur}px)`;ctx.strokeStyle=colour;ctx.stroke(p)}
    else{ctx.shadowColor=colour;ctx.shadowBlur=blur*2;ctx.shadowOffsetX=10000;ctx.translate(-10000,0);ctx.strokeStyle=colour;ctx.stroke(p)}
    ctx.restore()}
  function drawMasks(){
    const lm=S.lmS;if(!lm)return;
    const k=Math.min(1,(S.mode==="camera"?256:512)/Math.max(S.frameW,S.frameH)),W=Math.round(S.frameW*k),H=Math.round(S.frameH*k);
    for(const c of[maskA,maskB]){if(c.width!==W||c.height!==H){c.width=W;c.height=H}}
    const P=i=>[lm[i][0]*W,lm[i][1]*H],poly=ids=>{const p=new Path2D();ids.forEach((i,j)=>{const q=P(i);j?p.lineTo(q[0],q[1]):p.moveTo(q[0],q[1])});p.closePath();return p};
    const fw=Math.hypot(P(454)[0]-P(234)[0],P(454)[1]-P(234)[1])||W*0.4;
    const eyePts=ey=>ey.up.map(P).concat(ey.lo.slice(1,-1).reverse().map(P));
    const grow=(pts,s)=>{const cx=pts.reduce((a,p)=>a+p[0],0)/pts.length,cy=pts.reduce((a,p)=>a+p[1],0)/pts.length;return pts.map(p=>[cx+(p[0]-cx)*s,cy+(p[1]-cy)*s])};
    const path=pts=>{const p=new Path2D();pts.forEach((q,j)=>j?p.lineTo(q[0],q[1]):p.moveTo(q[0],q[1]));p.closePath();return p};
    // A: R face, G exclusions, B lips
    let g=maskA.getContext("2d");g.globalCompositeOperation="source-over";g.fillStyle="#000";g.fillRect(0,0,W,H);g.globalCompositeOperation="lighter";
    {const o=LM.oval.map(P),cx=o.reduce((t,q)=>t+q[0],0)/o.length,cy=o.reduce((t,q)=>t+q[1],0)/o.length;   // shrink so the soft edge stays inside the face, not on hair, scarves or background
     softFill(g,path(o.map(q=>[cx+(q[0]-cx)*0.955,cy+(q[1]-cy)*0.965])),"#ff0000",fw*0.03)}
    const ex=[path(grow(eyePts(LM.eyeR),1.18)),path(grow(eyePts(LM.eyeL),1.18)),poly(LM.browR),poly(LM.browL)];
    for(const x of ex)softFill(g,x,"#00ff00",fw*0.012);
    softFill(g,poly(LM.lipsOut),"#00ff00",fw*0.008);
    for(const al of[98,327]){const a=P(al),b=P(2);const c=[a[0]*0.58+b[0]*0.42,a[1]*0.45+b[1]*0.55];const p=new Path2D();p.ellipse(c[0],c[1],fw*0.03,fw*0.016,0,0,Math.PI*2);softFill(g,p,"#00ff00",fw*0.01)}
    const lips=new Path2D();lips.addPath(poly(LM.lipsOut));lips.addPath(poly(LM.lipsIn));softFill(g,lips,"#0000ff",fw*0.006,"evenodd");
    // B: R concealer, G blush, B liner
    g=maskB.getContext("2d");g.globalCompositeOperation="source-over";g.fillStyle="#000";g.fillRect(0,0,W,H);g.globalCompositeOperation="lighter";
    for(const ey of[LM.eyeR,LM.eyeL]){const lo=ey.lo.map(P),c0=P(ey.lo[0]),c1=P(ey.lo[ey.lo.length-1]),ew=Math.hypot(c1[0]-c0[0],c1[1]-c0[1]);
      const down=lo.slice().reverse().map((q,j,arr)=>{const t=j/(arr.length-1);return[q[0],q[1]+ew*(0.42*Math.sin(Math.PI*t)+0.06)]});
      softFill(g,path(lo.concat(down)),"#ff0000",ew*0.16)}
    for(const[i,j,s]of[[151,9,0.09],[6,197,0.05],[152,175,0.06]]){const a=P(i),b=P(j);const p=new Path2D();p.ellipse((a[0]+b[0])/2,(a[1]+b[1])/2,fw*s,fw*s*0.8,0,0,Math.PI*2);softFill(g,p,"#a00000",fw*0.05)}
    for(const ids of[LM.cheekR,LM.cheekL]){const pts=ids.map(P),cx=pts.reduce((a,p)=>a+p[0],0)/pts.length,cy=pts.reduce((a,p)=>a+p[1],0)/pts.length,r=fw*0.15;
      const gr=g.createRadialGradient(cx,cy,0,cx,cy,r);gr.addColorStop(0,"rgba(0,255,0,0.95)");gr.addColorStop(0.55,"rgba(0,255,0,0.5)");gr.addColorStop(1,"rgba(0,255,0,0)");
      g.save();g.translate(cx,cy);g.scale(1.25,0.85);g.translate(-cx,-cy);g.fillStyle=gr;g.beginPath();g.arc(cx,cy,r,0,Math.PI*2);g.fill();g.restore()}
    for(const ey of[LM.eyeR,LM.eyeL]){const up=ey.up.map(P),lo=ey.lo.map(P),ew=Math.hypot(up[up.length-1][0]-up[0][0],up[up.length-1][1]-up[0][1]);
      const outer=up[0],dir=Math.sign(outer[0]-up[up.length-1][0])||1;const wing=[outer[0]+dir*ew*0.14,outer[1]-ew*0.07];
      softStroke(g,[wing].concat(up),"#0000ff",ew*0.075,ew*0.012);softStroke(g,lo,"#0000ff",ew*0.04,ew*0.012)}
  }

  /* ---------- WebGL ---------- */
  const VS=`attribute vec2 a;varying vec2 uv;uniform vec4 uCrop;void main(){uv=uCrop.xy+(a*0.5+0.5)*uCrop.zw;gl_Position=vec4(a,0.,1.);}`;
  const FS=`#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec2 uv;uniform sampler2D uTex,uMA,uMB;uniform vec2 uTexel;uniform float uR,uMirror,uSplit,uTileX0,uTileW;
uniform vec3 uSkin,uLipM;
uniform vec4 uBase;uniform vec2 uBaseP;uniform vec4 uConc;uniform vec2 uConcP;uniform vec4 uPow;uniform vec4 uBlush;uniform float uBlushF;uniform vec4 uLip;uniform float uLipF;uniform vec4 uLin;uniform float uShim;
vec3 s2l(vec3 c){return mix(c/12.92,pow((c+0.055)/1.055,vec3(2.4)),step(0.04045,c));}
vec3 l2s(vec3 c){c=clamp(c,0.,1.);return mix(12.92*c,1.055*pow(c,vec3(1./2.4))-0.055,step(0.0031308,c));}
float lum(vec3 c){return dot(c,vec3(0.2126,0.7152,0.0722));}
vec3 cbrt3(vec3 x){return sign(x)*pow(abs(x),vec3(1./3.));}
vec3 ok(vec3 c){vec3 l=cbrt3(vec3(dot(c,vec3(0.4122214708,0.5363325363,0.0514459929)),dot(c,vec3(0.2119034982,0.6806995451,0.1073969566)),dot(c,vec3(0.0883024619,0.2817188376,0.6299787005))));
 return vec3(dot(l,vec3(0.2104542553,0.7936177850,-0.0040720468)),dot(l,vec3(1.9779984951,-2.4285922050,0.4505937099)),dot(l,vec3(0.0259040371,0.7827717662,-0.8086757660)));}
vec3 unok(vec3 o){vec3 l=vec3(o.x+0.3963377774*o.y+0.2158037573*o.z,o.x-0.1055613458*o.y-0.0638541728*o.z,o.x-0.0894841775*o.y-1.2914855480*o.z);l=l*l*l;
 return max(vec3(dot(l,vec3(4.0767416621,-3.3077115913,0.2309699292)),dot(l,vec3(-1.2684380046,2.6097574011,-0.3413193965)),dot(l,vec3(-0.0041960863,-0.7034186147,1.7076147010))),0.);}
float shK(vec3 B){return clamp(lum(B)/max(lum(uSkin),1e-4),0.2,1.6);}
vec3 baseB(vec3 S,vec3 B,vec3 sh,float a,float fin){float k=shK(B);vec3 bo=ok(B),fo=ok(sh*k);vec3 mo=mix(bo,fo,a);float ash=clamp((fo.x-bo.x)/0.25,0.,1.)*a;mo.yz*=1.-0.55*ash;mo.z-=0.012*ash;
 vec3 b=unok(mo);vec3 D=S/max(B,vec3(1e-4));if(fin<0.5)D=mix(D,1.+(D-1.)*0.35,step(1.,D));vec3 o=b*pow(D,vec3(1.-0.35*a));if(fin>1.5)o*=1.+0.10*a*smoothstep(0.95,1.35,k);return o;}
vec3 lipB(vec3 S,vec3 B,vec3 c,float a,float fin){float k=clamp(lum(B)/max(lum(uLipM),1e-4),0.2,1.8);vec3 b=unok(mix(ok(B),ok(c*k),a));vec3 D=S/max(B,vec3(1e-4));float dl=lum(D);
 vec3 o=b*pow(D,vec3(fin<0.5?0.6:1.));if(fin>2.5)o+=0.35*a*smoothstep(1.04,1.25,dl)+0.05*smoothstep(1.,1.2,k);else if(fin>0.5&&fin<1.5)o+=0.12*a*smoothstep(1.06,1.3,dl);return o;}
vec3 blushB(vec3 S,vec3 B,vec3 c,float a,float fin){float k=shK(B);vec3 t=c/max(lum(c),1e-3);t/=max(max(t.r,t.g),t.b);vec3 tin=S*mix(vec3(1.),t,0.55*a);
 vec3 pig=c*k*(lum(S)/max(lum(B),1e-4));vec3 o=unok(mix(ok(tin),ok(pig),0.22*a));if(fin>1.5)o*=1.+0.06*a*smoothstep(1.,1.3,k);return o;}
void main(){vec2 t=vec2(uMirror>0.5?1.-uv.x:uv.x,uv.y);vec3 S=s2l(texture2D(uTex,t).rgb);
 float sx=(gl_FragCoord.x/uTileW)-uTileX0;
 if(sx<uSplit){gl_FragColor=vec4(l2s(S),1.);return;}
 vec3 B=S*0.2;float r=uR;
 B+=s2l(texture2D(uTex,t+uTexel*vec2(r,0.)).rgb)*0.1;B+=s2l(texture2D(uTex,t+uTexel*vec2(-r,0.)).rgb)*0.1;B+=s2l(texture2D(uTex,t+uTexel*vec2(0.,r)).rgb)*0.1;B+=s2l(texture2D(uTex,t+uTexel*vec2(0.,-r)).rgb)*0.1;
 B+=s2l(texture2D(uTex,t+uTexel*vec2(0.7*r,0.7*r)).rgb)*0.1;B+=s2l(texture2D(uTex,t+uTexel*vec2(-0.7*r,0.7*r)).rgb)*0.1;B+=s2l(texture2D(uTex,t+uTexel*vec2(0.7*r,-0.7*r)).rgb)*0.1;B+=s2l(texture2D(uTex,t+uTexel*vec2(-0.7*r,-0.7*r)).rgb)*0.1;
 vec4 A=texture2D(uMA,t),M=texture2D(uMB,t);float ex=clamp(A.g,0.,1.);vec3 o=S;
 float fw=A.r*(1.-ex);
 if(uBase.a>0.){o=mix(o,baseB(o,B,uBase.rgb,uBase.a,uBaseP.x),fw);B=mix(B,baseB(B,B,uBase.rgb,uBase.a,uBaseP.x),fw);}
 if(uConc.a>0.){float w=M.r*(1.-ex);o=mix(o,baseB(o,B,uConc.rgb,uConc.a,uConcP.x),w);B=mix(B,baseB(B,B,uConc.rgb,uConc.a,uConcP.x),w);}
 if(uPow.a>0.){o=mix(o,baseB(o,B,uPow.rgb,uPow.a,0.),fw);}
 if(uBlush.a>0.){o=mix(o,blushB(o,B,uBlush.rgb,uBlush.a,uBlushF),M.g*(1.-ex));}
 if(uLip.a>0.){o=mix(o,lipB(o,B,uLip.rgb,uLip.a,uLipF),A.b);}
 if(uLin.a>0.){float k=shK(B);o=mix(o,uLin.rgb*(0.75+0.25*k)+(uShim>0.5?0.4*uLin.rgb+0.02:vec3(0.)),uLin.a*M.b);}
 gl_FragColor=vec4(l2s(o),1.);}`;
  function glInit(){
    if(S.gl)return true;
    let gl=null;try{gl=cv.getContext("webgl",{preserveDrawingBuffer:true,premultipliedAlpha:false,antialias:false})||cv.getContext("experimental-webgl",{preserveDrawingBuffer:true})}catch{}
    if(!gl)return false;
    const sh=(type,src)=>{const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s};
    let prog;try{prog=gl.createProgram();gl.attachShader(prog,sh(gl.VERTEX_SHADER,VS));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,FS));gl.linkProgram(prog);if(!gl.getProgramParameter(prog,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(prog))}
    catch(err){console.warn("try-on shader",err);return false}
    gl.useProgram(prog);
    const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
    const loc=gl.getAttribLocation(prog,"a");gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
    const tex=()=>{const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);for(const[p,v]of[[gl.TEXTURE_MIN_FILTER,gl.LINEAR],[gl.TEXTURE_MAG_FILTER,gl.LINEAR],[gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE],[gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE]])gl.texParameteri(gl.TEXTURE_2D,p,v);return t};
    const T=[tex(),tex(),tex()];
    ["uTex","uMA","uMB"].forEach((n,i)=>gl.uniform1i(gl.getUniformLocation(prog,n),i));
    const U={};for(const n of["uCrop","uTexel","uR","uMirror","uSplit","uTileX0","uTileW","uSkin","uLipM","uBase","uBaseP","uConc","uConcP","uPow","uBlush","uBlushF","uLip","uLipF","uLin","uShim"])U[n]=gl.getUniformLocation(prog,n);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
    S.gl={gl,T,U};return true;
  }
  function setup(){layout();S.maskDirty=true;if(S.mode!=="camera")drawMasks()}
  function layout(){
    if(!cv||!S.frameW||!fit)return;
    const r=stage.getBoundingClientRect();if(!r.width||!r.height)return;
    const ar=S.frameW/S.frameH;let w=r.width,h=w/ar;if(h>r.height){h=r.height;w=h*ar}
    w=Math.max(1,Math.floor(w));h=Math.max(1,Math.floor(h));fit.style.width=w+"px";fit.style.height=h+"px";
    const k=Math.min(Math.min(2,window.devicePixelRatio||1),1280/Math.max(w,h));
    const cw=Math.round(w*k),ch=Math.round(h*k);if(cv.width!==cw||cv.height!==ch){cv.width=cw;cv.height=ch}
    const tiles=root.querySelector(".to-tiles");tiles.hidden=!S.compare;
    if(S.compare)tiles.innerHTML=[0,1,2,3].map(i=>{const c=S.cmp[i];return`<div class="to-tile">${c?`<div class="to-tilecap"><span><b>${e(c.s.name)}</b><small>${money(c.p.p)}${c.s.demo?" · demo colour":""}</small></span><button type="button" class="to-pick" data-pick="${i}">Pick this</button></div>`:`<div class="to-tilecap empty">Tap a shade to compare</div>`}</div>`}).join("");
    drawDivider();
  }
  function drawDivider(){
    if(!root)return;const d=root.querySelector(".to-divider"),h=root.querySelector(".to-handle");
    d.hidden=S.compare;d.style.setProperty("--x",(S.split*100).toFixed(1)+"%");h.setAttribute("aria-valuenow",Math.round(S.split*100));
    d.classList.toggle("nob",S.split<=0.02);d.classList.toggle("noa",S.split>=0.98);
  }
  const lin=h=>C.hexToLin(h)||[0,0,0];
  function looks(){
    const L=S.look;
    if(!S.compare)return[L];
    return[0,1,2,3].map(i=>{const c=S.cmp[i];if(!c)return null;const o=Object.assign({},L);o[c.slot]={p:c.p,s:c.s};return o});
  }
  function setLook(U,gl,look){
    const v4=(n,c,a)=>gl.uniform4f(U[n],c[0],c[1],c[2],a);
    const b=look.base,cc=look.conc,pw=look.powder,bl=look.blush,lp=look.lips,ln=look.liner;
    v4("uBase",b?lin(b.s.hex):[0,0,0],b?C.coverageAlpha(b.s.cov)*(b.p.c==="BB / CC cream"?0.85:1):0);gl.uniform2f(U.uBaseP,b?C.baseFinish(b.s.fin):1,0);
    v4("uConc",cc?lin(cc.s.hex):[0,0,0],cc?Math.min(0.9,C.coverageAlpha(cc.s.cov)+0.1):0);gl.uniform2f(U.uConcP,cc?C.baseFinish(cc.s.fin):1,0);
    v4("uPow",pw?lin(pw.s.hex):[0,0,0],pw?C.coverageAlpha(pw.s.cov)*0.45:0);
    v4("uBlush",bl?lin(bl.s.hex):[0,0,0],bl?0.75:0);gl.uniform1f(U.uBlushF,bl&&bl.s.fin==="dewy"?2:0);
    v4("uLip",lp?lin(lp.s.hex):[0,0,0],lp?C.lipAlpha(lp.s.fin):0);gl.uniform1f(U.uLipF,lp?C.lipFinish(lp.s.fin):1);
    v4("uLin",ln?lin(ln.s.hex):[0,0,0],ln?0.9:0);gl.uniform1f(U.uShim,ln&&ln.s.fin==="shimmer"?1:0);
  }
  function faceCrop(){
    if(!S.lmS)return[0,0,1,1];
    let x0=1,y0=1,x1=0,y1=0;for(const i of LM.oval){const p=S.lmS[i];x0=Math.min(x0,p[0]);y0=Math.min(y0,p[1]);x1=Math.max(x1,p[0]);y1=Math.max(y1,p[1])}
    const cx=(x0+x1)/2,cy=(y0+y1)/2;let w=(x1-x0)*1.5,h=(y1-y0)*1.35;
    const tileAR=cv.width/cv.height,fAR=S.frameW/S.frameH;   // keep the tile's aspect
    if(w*fAR/h>tileAR)h=w*fAR/tileAR;else w=h*tileAR/fAR;
    w=Math.min(1,w);h=Math.min(1,h);return[Math.min(1-w,Math.max(0,cx-w/2)),Math.min(1-h,Math.max(0,cy-h/2)),w,h];
  }
  function draw(){
    const G=S.gl;if(!G||!S.src||!S.frameW)return;const{gl,T,U}=G;
    if(S.mode==="camera"&&S.maskDirty&&S.lmS){drawMasks();S.maskDirty=false}
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,T[0]);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,S.src);
    const has=!!S.lmS;
    if(has&&(S.mode!=="camera"||draw.mv!==S.lmS)){gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,T[1]);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,maskA);
      gl.activeTexture(gl.TEXTURE2);gl.bindTexture(gl.TEXTURE_2D,T[2]);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,maskB);draw.mv=S.lmS}
    gl.uniform2f(U.uTexel,1/S.frameW,1/S.frameH);
    let fwPx=S.frameW*0.4;if(has){const a=S.lmS[234],b=S.lmS[454];fwPx=Math.hypot((b[0]-a[0])*S.frameW,(b[1]-a[1])*S.frameH)}
    gl.uniform1f(U.uR,Math.max(2,fwPx*0.02));
    gl.uniform1f(U.uMirror,S.mode==="camera"?1:0);
    gl.uniform3f(U.uSkin,...S.skinMean);gl.uniform3f(U.uLipM,...S.lipMean);
    const W=cv.width,H=cv.height,L=looks();
    gl.clearColor(0.96,0.94,0.92,1);gl.clear(gl.COLOR_BUFFER_BIT);
    if(!S.compare){
      // texture y is flipped (UNPACK_FLIP_Y), so crop y is measured from the bottom
      const cr=has?faceCrop():[0,0,1,1],crop=has?[S.mode==="camera"?1-cr[0]-cr[2]:cr[0],1-cr[1]-cr[3],cr[2],cr[3]]:cr;
      gl.viewport(0,0,W,H);gl.uniform4f(U.uCrop,...crop);gl.uniform1f(U.uTileW,W);gl.uniform1f(U.uTileX0,0);
      gl.uniform1f(U.uSplit,has?S.split:2);setLook(U,gl,has?L[0]:{});gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
    }else{
      const cr=faceCrop(),tw=Math.floor(W/2),th=Math.floor(H/2);
      // texture y is flipped (UNPACK_FLIP_Y), so crop y is measured from the bottom
      const crop=[S.mode==="camera"?1-cr[0]-cr[2]:cr[0],1-cr[1]-cr[3],cr[2],cr[3]];
      L.forEach((lk,i)=>{const x=(i%2)*tw,y=(i<2?1:0)*th;gl.viewport(x,y,tw,th);gl.uniform4f(U.uCrop,...crop);gl.uniform1f(U.uTileW,tw);gl.uniform1f(U.uTileX0,x/tw);gl.uniform1f(U.uSplit,lk?-1:2);setLook(U,gl,lk||{});gl.drawArrays(gl.TRIANGLE_STRIP,0,4)});
    }
  }

  /* ---------- snapshot (stays on the device) ---------- */
  function snapshot(){
    if(!S.gl||!S.src)return;draw();
    let url;try{url=cv.toDataURL("image/jpeg",0.9)}catch{return toast("Couldn't save a snapshot here.")}
    S.snaps.unshift(url);S.snaps=S.snaps.slice(0,4);
    const a=document.createElement("a");a.href=url;a.download=`aaina-look-${new Date().toISOString().slice(0,10)}.jpg`;document.body.appendChild(a);a.click();a.remove();
    toast("Snapshot saved to this device only. Nothing is uploaded.");
  }

  /* ---------- open / close / route ---------- */
  function open(opts={}){
    if(!root)build();
    if(!S.open){S.open=true;root.hidden=false;if(S.setSheet)S.setSheet(false);document.documentElement.classList.add("to-lock");
      if(location.hash!=="#try-on"){history.pushState(null,"",location.pathname+location.search+"#try-on");S.pushedHash=true}}
    if(opts.pid&&typeof BY_ID!=="undefined"&&BY_ID[opts.pid]){const p=BY_ID[opts.pid];S.tab=TABS.find(t=>t[2].includes(p.c))[0];S.cat=p.c;pickProduct(p.id);
      if(opts.shade){const s=shadesOf(p).find(x=>x.name===opts.shade);if(s){S.look[SLOT[p.c]]={p,s};renderPanel()}}}
    else if(opts.base){S.tab="face";S.cat="Foundation";S.pid=null;renderPanel();const list=products("Foundation").filter(x=>x.st.ok);if(list[0])pickProduct(list[0].p.id)}
    else renderPanel();
    if(opts.model==="closest"&&!S.src){const k=closestModel();if(k>=0){useModel(k);return}}
    if(!S.src)pane("start");else{layout();kick()}
    root.querySelector(".to-x").focus();
  }
  function close(){
    if(!S.open)return;S.open=false;toggleCompare(false,true);stopCamera();
    try{const b=S.look.base;window.dispatchEvent(new CustomEvent("tryon:close",{detail:{look:{base:b?{pid:b.p.id,name:b.s.name}:null}}}))}catch{}stopLoop();root.hidden=true;document.documentElement.classList.remove("to-lock");
    if(location.hash==="#try-on"){if(S.pushedHash){S.pushedHash=false;window.__aainaTryonBack=true;history.back()}else history.replaceState(null,"",location.pathname+location.search)}
  }
  window.addEventListener("hashchange",()=>{if(location.hash==="#try-on"&&!S.open)open();else if(location.hash!=="#try-on"&&S.open){S.pushedHash=false;close()}});
  window.addEventListener("popstate",()=>{if(location.hash!=="#try-on"&&S.open){S.pushedHash=false;close()}});
  window.addEventListener("resize",()=>{if(S.open&&S.src){layout();kick()}});
  document.addEventListener("click",ev=>{const b=ev.target.closest&&ev.target.closest("[data-tryon]");if(!b||(root&&root.contains(b)))return;ev.preventDefault();open(b.dataset.tryon==="base"?{base:true}:{pid:b.dataset.tryon||null})});
  if(location.hash==="#try-on")setTimeout(()=>open(),0);
  /* face landmarks for any image, on this device (used by the Results timeline illustration) */
  async function landmarksFor(img){const tr=await tracker("IMAGE");if(!tr)return null;let r=null;try{r=tr.detect(img)}catch{}const lm=r&&r.faceLandmarks&&r.faceLandmarks[0];return lm?lm.map(p=>[p.x,p.y]):null}
  return{open,close,setSplit,closestModel,landmarksFor,state:S,_draw:draw,_products:products,_status:status};
})();
