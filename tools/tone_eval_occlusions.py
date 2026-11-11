"""Skin tone reader v3 (skin mask + mapping layer) vs the previous reader, on simulated selfies that stress
what the mask is for (hair fringe, beard, lipstick), camera processing, filters, and product-shade matching.
Same physics as tone_eval.py: light applied to face, eyes and wall together in linear light."""
import json, pathlib, collections, random, re
from playwright.sync_api import sync_playwright
S = pathlib.Path(__file__).resolve().parent.parent
GEN = r"""
(spec)=>{
  const W=900,H=1200,k=1;let seed=spec.seed;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647};
  const L=c=>{c/=255;return c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4)};
  const skinLab=[MONK_LAB[spec.tone][0]+spec.jit[0],MONK_LAB[spec.tone][1]+spec.jit[1],MONK_LAB[spec.tone][2]+spec.jit[2]];
  const refl=lab=>lab2rgb(...lab).map(L);
  const skin=refl(skinLab),scl=[0.86,0.84,0.79].map((v,i)=>v*spec.scl*(i===2?spec.sclB:1)),iris=[0.05,0.035,0.025],hair=[0.025,0.02,0.018];
  const lip=spec.lipstick?[0.45,0.03,0.06]:skin.map((v,i)=>v*(i===0?0.8:0.55));
  let kx=spec.expo;const c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d');const img=g.createImageData(W,H),d=img.data;
  const cx=450,cy=500,rx=225,ry=300,eyes=[[369,452],[531,452]];
  for(let j=0;j<H;j++)for(let i=0;i<W;i++){
    let r=spec.wall;const fe=((i-cx)/rx)**2+((j-cy)/ry)**2;
    if(fe<=1){r=skin;
      for(const[ex,ey]of eyes){const e=((i-ex)/34)**2+((j-ey)/13)**2;if(e<=1)r=Math.hypot(i-ex,j-ey)<11?iris:scl;if(Math.abs(j-(ey-30))<5&&Math.abs(i-ex)<38)r=hair}
      if(((i-cx)/60)**2+((j-668)/(spec.lipstick?14:8))**2<=1)r=lip;
      if(j<cy-ry*0.82)r=hair;
      if(spec.fringe&&j<cy-ry*(0.55-0.25*Math.abs(i-cx)/rx)&&rnd()<0.92)r=hair;           // fringe over most of the forehead
      if(spec.beard&&j>590&&fe>0.05&&rnd()<0.55)r=hair;                                    // stubble over chin and lower cheeks
      if(spec.glasses){for(const[ex,ey]of eyes){const e=Math.hypot((i-ex)/52,(j-ey)/34);if(e>0.92&&e<1.05)r=hair}}
    }
    let sh=1;if(spec.shadow&&i<cx&&fe<=1)sh=0.45;
    const q=(j*W+i)*4;for(let ch=0;ch<3;ch++){let v=r[ch]*spec.illum[ch]*kx*sh;let s=v<=0.0031308?12.92*v:1.055*Math.pow(Math.min(1,v),1/2.4)-0.055;d[q+ch]=Math.max(0,Math.min(255,255*Math.min(1,s)+(rnd()+rnd()+rnd()-1.5)*5))}
    d[q+3]=255}
  // camera processing / filters, applied in sRGB like a phone would
  if(spec.vivid||spec.beauty||spec.tint){for(let q=0;q<d.length;q+=4){let r=d[q],gg=d[q+1],b=d[q+2];
    if(spec.vivid){const m=(r+gg+b)/3;r=m+(r-m)*1.3;gg=m+(gg-m)*1.3;b=m+(b-m)*1.3;const cu=v=>255/(1+Math.exp(-(v/255-0.5)*5.5));r=0.6*r+0.4*cu(r);gg=0.6*gg+0.4*cu(gg);b=0.6*b+0.4*cu(b)}
    if(spec.tint){r*=0.92;gg*=1.06;b*=1.12}
    d[q]=Math.max(0,Math.min(255,r));d[q+1]=Math.max(0,Math.min(255,gg));d[q+2]=Math.max(0,Math.min(255,b))}}
  g.putImageData(img,0,0);
  if(spec.beauty){const c2=document.createElement('canvas');c2.width=W;c2.height=H;const g2=c2.getContext('2d');g2.filter='blur(6px) brightness(1.12) saturate(0.9)';g2.drawImage(c,0,0);
    g.save();g.beginPath();g.ellipse(cx,cy,rx*0.95,ry*0.95,0,0,Math.PI*2);g.clip();g.drawImage(c2,0,0);g.restore()}
  const oval={cx:0.5,cy:500/1200,w:0.5,h:0.5};
  const truth=estimateTone(skinLab).tone;
  const res=readPhoto(c,oval);
  const filt=(typeof detectFilter==='function')?detectFilter(c,oval):null;
  // closest-shade truth vs pick, over the base-makeup products in the catalogue
  let shade=null;
  if(res.status==="OK"&&typeof matchShade==='function'){const prods=CAT.filter(p=>p.s&&p.s.length>=4).slice(0,12);let hit=0,n=0,ex=0,dd=0;
    for(const p of prods){const tr=p.s.map(s=>[s,Math.hypot(...rgb2lab(...hex2rgb(s[3])).map((v,i)=>v-skinLab[i]))]).sort((a,b)=>a[1]-b[1])[0];
      const m=matchShade(p,{lab:res.lab,tone:res.tone});if(!m)continue;n++;
      const mde=Math.hypot(...rgb2lab(...hex2rgb(m.hex)).map((v,i)=>v-skinLab[i]));if(m.hex===tr[0][3])hit++;ex+=mde-tr[1];dd+=Math.abs(m.depth-tr[0][1])}
    shade={n,hit,excessDE:n?ex/n:null,depthErr:n?dd/n:null}}
  return {truth,status:res.status,tone:res.tone??null,issues:res.issues,conf:res.conf??null,coverage:res.coverage??null,method:res.method||null,filter:filt?filt.flags.map(f=>f.k):null,shade};
}"""
CONDS = {
 "daylight":dict(illum=[1,1,1],expo=1.0),
 "warm_bulb":dict(illum=[1.0,0.80,0.52],expo=0.8),
 "dim_room":dict(illum=[1,1,1],expo=0.35),
 "side_shadow":dict(illum=[1,1,1],expo=1.0,shadow=True),
 "hair_fringe":dict(illum=[1,1,1],expo=1.0,fringe=True),
 "beard":dict(illum=[1,1,1],expo=1.0,beard=True),
 "lipstick":dict(illum=[1,1,1],expo=1.0,lipstick=True),
 "glasses":dict(illum=[1,1,1],expo=1.0,glasses=True),
 "fringe_beard_warm":dict(illum=[1.0,0.80,0.52],expo=0.8,fringe=True,beard=True),
 "vivid_camera":dict(illum=[1,1,1],expo=1.0,vivid=True),
 "beauty_filter":dict(illum=[1,1,1],expo=1.0,beauty=True),
 "colour_filter":dict(illum=[1,1,1],expo=1.0,tint=True),
}
WALLS = {"grey":[0.30,0.30,0.30],"white":[0.80,0.80,0.80],"beige":[0.62,0.52,0.38],"dark":[0.05,0.05,0.05],"teal":[0.20,0.40,0.42]}
rng = random.Random(18)
people=[dict(pid=f"T{t}-{r}",tone=t,jit=[rng.uniform(-3,3),rng.uniform(-2,2),rng.uniform(-2,2)],scl=rng.uniform(0.9,1.1),sclB=rng.uniform(0.92,1.0)) for t in range(1,11) for r in range(4)]
specs=[]
for p in people:
    for cn,c in CONDS.items():
        specs.append((p,cn,dict(tone=p["tone"],jit=p["jit"],scl=p["scl"],sclB=p["sclB"],wall=WALLS[rng.choice(list(WALLS))],illum=c["illum"],expo=c["expo"],
            shadow=c.get("shadow",False),fringe=c.get("fringe",False),beard=c.get("beard",False),lipstick=c.get("lipstick",False),glasses=c.get("glasses",False),
            vivid=c.get("vivid",False),beauty=c.get("beauty",False),tint=c.get("tint",False),seed=11+len(specs)*7)))
out={}
with sync_playwright() as pw:
    b=pw.chromium.launch()
    for ver,page in [("v3","index.html")]:
        pg=b.new_page();pg.route("https://**/*",lambda r:r.abort());pg.goto("file://"+str(S/page));pg.wait_for_timeout(300)
        out[ver]=[dict(pid=p["pid"],cond=cn,**pg.evaluate(GEN,sp)) for p,cn,sp in specs];pg.close()
json.dump(out,open(S/"tools"/"tone_eval2.json","w"))
band=lambda t:0 if t<=3 else 1 if t<=6 else 2
def summ(R):
    n=len(R);ok=[r for r in R if r["status"]=="OK"]
    ex=sum(r["tone"]==r["truth"] for r in ok);w1=sum(abs(r["tone"]-r["truth"])<=1 for r in ok);bd=sum(band(r["tone"])==band(r["truth"]) for r in ok)
    wrong2=sum(abs(r["tone"]-r["truth"])>=2 for r in ok)
    return dict(n=n,recapture=round(100*(n-len(ok))/n,1),exact=round(100*ex/max(1,len(ok)),1),within1=round(100*w1/max(1,len(ok)),1),band=round(100*bd/max(1,len(ok)),1),off_by_2plus=round(100*wrong2/max(1,len(ok)),1))
S2={}
for ver,R in out.items():
    S2[ver]={"all":summ(R),"by_condition":{c:summ([r for r in R if r["cond"]==c]) for c in CONDS}}
    by=collections.defaultdict(list)
    for r in R:
        if r["status"]=="OK":by[r["pid"]].append(r["tone"])
    S2[ver]["consistency"]=round(100*sum(collections.Counter(v).most_common(1)[0][1]/len(CONDS) for v in by.values())/len(people),1)
# product shades + confidence + filters (v3 only)
R=out["v3"];sh=[r["shade"] for r in R if r.get("shade") and r["shade"]["n"]]
S2["v3"]["product_shades"]=dict(photos=len(sh),exact_closest_shade=round(100*sum(s["hit"] for s in sh)/sum(s["n"] for s in sh),1),
    avg_extra_colour_difference_dE=round(sum(s["excessDE"] for s in sh)/len(sh),2),avg_depth_error=round(sum(s["depthErr"] for s in sh)/len(sh),2))
ok=[r for r in R if r["status"]=="OK"]
right=[r["conf"] for r in ok if r["tone"]==r["truth"]];wrong=[r["conf"] for r in ok if abs(r["tone"]-r["truth"])>=2]
S2["v3"]["confidence"]=dict(avg_when_exact=round(sum(right)/max(1,len(right)),2),avg_when_off_by_2plus=round(sum(wrong)/max(1,len(wrong)),2))
fl=lambda c:collections.Counter(tuple(r["filter"] or []) for r in R if r["cond"]==c)
S2["v3"]["filter_flags"]={c:{(",".join(k) or "none"):v for k,v in fl(c).items()} for c in ["daylight","vivid_camera","beauty_filter","colour_filter","warm_bulb"]}
S2["v3"]["recapture_reasons"]=dict(collections.Counter(i for r in R if r["status"]!="OK" for i in r["issues"]))
json.dump(S2,open(S/"tools"/"tone_eval2_summary.json","w"),indent=1)
f=lambda d:f"recapture {d['recapture']:>5}% | exact {d['exact']:>5}% | ±1 {d['within1']:>5}% | band {d['band']:>5}% | off≥2 {d['off_by_2plus']:>5}%"
for ver in out:print(ver.upper(),f(S2[ver]["all"]),"| consistency",S2[ver]["consistency"])
for c in CONDS:print(f"{c:19} prev {f(S2['prev']['by_condition'][c])}\n{'':19} v3   {f(S2['v3']['by_condition'][c])}")
for k in ("product_shades","confidence","filter_flags","recapture_reasons"):print(k,S2["v3"][k])
