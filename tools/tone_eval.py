"""Skin tone reader: old (v1) vs new (v2) on physically simulated selfies.
Each face = a skin colour near one of the 10 Aaina swatches, eye whites, iris, brows, lips, on a wall.
Light is applied to EVERYTHING in linear light (face, eyes and wall together), then the camera clips and adds noise,
so a warm bulb tints the face too, and dim light darkens the face and the eyes alike.
Truth = nearest swatch to the person's true skin colour (before any lighting)."""
import json, pathlib, collections
from playwright.sync_api import sync_playwright
S = pathlib.Path(__file__).resolve().parent.parent
GEN = r"""
(spec)=>{
  const W=spec.lowres?300:900,H=spec.lowres?400:1200,k=W/900;let seed=spec.seed;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647};
  const L=c=>{c/=255;return c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4)};
  const skinLab=[MONK_LAB[spec.tone][0]+spec.jit[0],MONK_LAB[spec.tone][1]+spec.jit[1],MONK_LAB[spec.tone][2]+spec.jit[2]];
  const refl=lab=>lab2rgb(...lab).map(L);
  const skin=refl(skinLab),scl=[0.86,0.84,0.79].map((v,i)=>v*spec.scl*(i===2?spec.sclB:1)),iris=[0.05,0.035,0.025],brow=[0.03,0.025,0.02],lip=skin.map((v,i)=>v*(i===0?0.8:0.55));
  const wall=spec.wall;
  let illum=spec.illum.slice(),kx=spec.expo;
  if(spec.ae){const Y=0.2126*skin[0]+0.7152*skin[1]+0.0722*skin[2];kx=Math.min(3,Math.max(0.4,0.30/Y))*spec.expo}   // phone auto-exposure on the face
  const c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d');const img=g.createImageData(W,H),d=img.data;
  const cx=450*k,cy=500*k,rx=225*k,ry=300*k;
  const eyes=[[369*k,452*k],[531*k,452*k]];
  for(let j=0;j<H;j++)for(let i=0;i<W;i++){
    let r=wall;const fe=((i-cx)/rx)**2+((j-cy)/ry)**2;
    if(fe<=1){r=skin;
      for(const[ex,ey]of eyes){const e=((i-ex)/(34*k))**2+((j-ey)/(13*k))**2;if(e<=1){r=spec.eyesOpen?(Math.hypot(i-ex,j-ey)<11*k?iris:scl):brow}
        if(Math.abs(j-(ey-30*k))<5*k&&Math.abs(i-ex)<38*k)r=brow}
      if(Math.abs(j-665*k)<7*k&&Math.abs(i-cx)<55*k)r=lip;
      if(j<cy-ry*0.82)r=brow;   // hairline
    }
    let sh=1;if(spec.shadow&&i<cx&&fe<=1)sh=0.45;
    const q=(j*W+i)*4;for(let ch=0;ch<3;ch++){const v=r[ch]*illum[ch]*kx*sh;const s=v<=0.0031308?12.92*v:1.055*Math.pow(Math.min(1,v),1/2.4)-0.055;d[q+ch]=Math.max(0,Math.min(255,255*Math.min(1,s)+(rnd()+rnd()+rnd()-1.5)*5))}
    d[q+3]=255}
  g.putImageData(img,0,0);const oval={cx:0.5,cy:500/1200,w:0.5,h:0.5};
  const truth=estimateTone(skinLab).tone;
  const a=readPhotoV1(c,oval),b=readPhoto(c,oval);
  return {truth,v1:{status:a.status,tone:a.tone??null,issues:a.issues},v2:{status:b.status,tone:b.tone??null,issues:b.issues,method:b.method||null,notes:b.notes||[]}};
}"""
CONDS = {
 "daylight":     dict(illum=[1,1,1], expo=1.0),
 "warm_bulb":    dict(illum=[1.0,0.80,0.52], expo=0.8),
 "cool_shade":   dict(illum=[0.82,0.95,1.18], expo=0.9),
 "dim_room":     dict(illum=[1,1,1], expo=0.35),
 "dim_warm":     dict(illum=[1.0,0.80,0.52], expo=0.4),
 "bright_sun":   dict(illum=[1,1,1], expo=1.55),
 "phone_auto_exposure": dict(illum=[1,1,1], expo=1.0, ae=True),
 "side_shadow":  dict(illum=[1,1,1], expo=1.0, shadow=True),
 "low_res":      dict(illum=[1,1,1], expo=1.0, lowres=True),
}
WALLS = {"grey":[0.30,0.30,0.30],"white":[0.80,0.80,0.80],"beige":[0.62,0.52,0.38],"dark":[0.05,0.05,0.05],"teal":[0.20,0.40,0.42]}
import random
rng = random.Random(14)
people = []
for tone in range(1,11):
    for rep in range(5):
        people.append(dict(pid=f"T{tone}-{rep}", tone=tone, jit=[rng.uniform(-3,3),rng.uniform(-2,2),rng.uniform(-2,2)],
                           scl=rng.uniform(0.9,1.1), sclB=rng.uniform(0.92,1.0), eyesOpen=rng.random()>0.2))
rows=[]
with sync_playwright() as pw:
    b=pw.chromium.launch();pg=b.new_page();pg.route("https://**/*",lambda r:r.abort())
    pg.goto("file://"+str(S/"index.html"));pg.wait_for_timeout(300)
    n=0
    for p in people:
        for cname,c in CONDS.items():
            wall=rng.choice(list(WALLS));spec=dict(tone=p["tone"],jit=p["jit"],scl=p["scl"],sclB=p["sclB"],eyesOpen=p["eyesOpen"],wall=WALLS[wall],
                illum=c["illum"],expo=c["expo"],ae=c.get("ae",False),shadow=c.get("shadow",False),lowres=c.get("lowres",False),seed=1+n*7)
            r=pg.evaluate(GEN,spec);rows.append(dict(pid=p["pid"],eyes=p["eyesOpen"],cond=cname,wall=wall,**r));n+=1
json.dump(rows,open(S/"tools"/"tone_eval.json","w"),indent=0)
def summ(key,sel=lambda r:True):
    R=[r for r in rows if sel(r)];n=len(R);acc=[r for r in R if r[key]["status"]=="OK"]
    ex=sum(r[key]["tone"]==r["truth"] for r in acc);w1=sum(abs(r[key]["tone"]-r["truth"])<=1 for r in acc)
    band=lambda t:0 if t<=3 else 1 if t<=6 else 2
    bd=sum(band(r[key]["tone"])==band(r["truth"]) for r in acc)
    return dict(n=n,rejected=n-len(acc),reject_rate=round(100*(n-len(acc))/n,1),exact=round(100*ex/max(1,len(acc)),1),within1=round(100*w1/max(1,len(acc)),1),band=round(100*bd/max(1,len(acc)),1),
                answered_exact=round(100*ex/n,1),answered_within1=round(100*w1/n,1))
out={"all":{"v1":summ("v1"),"v2":summ("v2")},"by_condition":{},"eyes_closed_v2":summ("v2",lambda r:not r["eyes"]),"eyes_open_v2":summ("v2",lambda r:r["eyes"])}
for c in CONDS: out["by_condition"][c]={"v1":summ("v1",lambda r:r["cond"]==c),"v2":summ("v2",lambda r:r["cond"]==c)}
# consistency: same person across all lighting conditions
def consist(key):
    by=collections.defaultdict(list)
    for r in rows:
        if r[key]["status"]=="OK":by[r["pid"]].append(r[key]["tone"])
    same=[collections.Counter(v).most_common(1)[0][1]/9 for v in by.values()]   # share of the 9 photos giving the person's most common answer
    spread=[max(v)-min(v) for v in by.values() if v]
    return dict(people=len(people),avg_share_same_answer=round(100*sum(same)/len(people),1),avg_spread=round(sum(spread)/len(spread),2))
out["consistency"]={"v1":consist("v1"),"v2":consist("v2")}
out["v2_rejections"]=collections.Counter(i for r in rows if r["v2"]["status"]!="OK" for i in r["v2"]["issues"])
json.dump(out,open(S/"tools"/"tone_eval_summary.json","w"),indent=1)
print(json.dumps(out,indent=1))
