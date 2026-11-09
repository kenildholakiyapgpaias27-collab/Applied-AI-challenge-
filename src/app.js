/* =====================================================================
   Aaina AI Skin Advisor: problem first, 3-product plan, full explanation
   ===================================================================== */
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const rupee=v=>v==null?"–":"₹"+Math.round(v).toLocaleString("en-IN");
const cap=s=>s?s[0].toUpperCase()+s.slice(1):s;
const scaleHTML=()=>Object.values(MONK_HEX).map(h=>`<span style="background:${h}"></span>`).join("");
const SVG=d=>`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const IC={
  tube:SVG('<path d="M8 3h8l-1 4H9z"/><path d="M9 7h6l1.5 12a2 2 0 0 1-2 2h-5a2 2 0 0 1-2-2z"/>'),
  dropper:SVG('<path d="M10 3h4v4h-4z"/><path d="M12 7v3"/><path d="M12 10c-2.5 3-4 5-4 7a4 4 0 0 0 8 0c0-2-1.5-4-4-7z"/>'),
  jar:SVG('<rect x="5" y="9" width="14" height="11" rx="3"/><path d="M6 9V6.5A1.5 1.5 0 0 1 7.5 5h9A1.5 1.5 0 0 1 18 6.5V9"/>'),
  sun:SVG('<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4"/>'),
  eye:SVG('<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="2.5"/>'),
  spark:SVG('<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>'),
};
const CAT_IC={Cleanser:"tube",Serum:"dropper",Toner:"dropper",Exfoliant:"dropper","Spot treatment":"dropper",Moisturiser:"jar","Eye cream":"eye",Sunscreen:"sun"};

/* ---------- problems, their follow-up questions and 3-step plans ---------- */
const PROBLEMS={
  acne:{label:"Breakouts and acne",sub:"Pimples, blackheads, clogged pores",ic:"dropper",
    follow:{ask:"What do your breakouts usually look like?",opts:[
      ["Small pimples now and then","Occasional spots that come and go",{boost:[[/niacinamide|azelaic|zinc/i,2]]}],
      ["Blackheads and whiteheads","Clogged pores, often on the nose and chin",{boost:[[/salicylic/i,3]]}],
      ["Red, inflamed spots","Angry spots that leave marks",{boost:[[/azelaic|centella|niacinamide|zinc/i,2.5]],gentle:true}],
      ["Deep, painful lumps","Under the skin and sore to touch",{escalate:true,gentle:true}]]},
    plan:[{role:"Cleanse",when:"Morning and night",cats:["Cleanser"],con:"acne"},{role:"Treat",when:"At night",cats:["Serum","Spot treatment"],con:"acne",primary:true},{role:"Protect",when:"Every morning",cats:["Sunscreen"],con:"acne",boost:[[/matte|invisible|aqua/i,1.5]]}],
    expect:"Most people notice fewer new breakouts after 6–8 weeks of steady use. Existing marks take longer to fade."},
  pigmentation:{label:"Dark spots and marks",sub:"Marks after pimples, sun spots, patches",ic:"dropper",
    follow:{ask:"What kind of dark spots do you have?",opts:[
      ["Marks left after pimples","Flat brown or red marks",{boost:[[/niacinamide|azelaic/i,2.5]]}],
      ["Sun spots or freckles","Darker after time in the sun",{boost:[[/vitamin c|ascorb/i,2.5]],spf:50}],
      ["Uneven patches","Larger areas of darker skin",{boost:[[/tranexamic|arbutin|licorice/i,3]]}]]},
    plan:[{role:"Treat",when:"At night",cats:["Serum"],con:"pigmentation",primary:true},{role:"Hydrate",when:"Morning and night",cats:["Moisturiser"],con:"pigmentation"},{role:"Protect",when:"Every morning",cats:["Sunscreen"],con:"pigmentation",boost:[[/./,0]]}],
    expect:"Marks usually fade gradually over 8–12 weeks, and only stay away with daily sunscreen."},
  dullness:{label:"Dull, tired skin",sub:"Lacks glow, rough or uneven",ic:"spark",
    follow:{ask:"How would you describe the dullness?",opts:[
      ["Tired, flat-looking skin","Missing its usual glow",{boost:[[/vitamin c|ascorb/i,3]]}],
      ["Rough texture","Feels bumpy or uneven to touch",{boost:[[/lactic|glycolic/i,2]],exfoliateFirst:true}],
      ["Uneven tone","Some areas look darker or blotchy",{boost:[[/niacinamide|licorice/i,2.5]]}]]},
    plan:[{role:"Brighten",when:"Every morning",cats:["Serum"],con:"dullness",primary:true},{role:"Exfoliate",when:"Twice a week, at night",cats:["Exfoliant"],con:"dullness"},{role:"Protect",when:"Every morning",cats:["Sunscreen"],con:"dullness"}],
    expect:"Skin often looks brighter within 2–4 weeks; texture keeps improving with regular gentle exfoliation."},
  dehydration:{label:"Dryness and tightness",sub:"Tight, flaky or rough skin",ic:"jar",
    follow:{ask:"When does your skin feel driest?",opts:[
      ["Right after washing","Tight and stretchy after cleansing",{boost:[[/hydrating|gentle|cream/i,2.5]]}],
      ["All day, with flaky patches","Rough or peeling areas",{boost:[[/ceramide|barrier|rich|squalane|butyrospermum/i,2.5]]}],
      ["In winter or air-conditioning","Worse in dry air",{boost:[[/hyaluronic|ceramide/i,2]]}]]},
    plan:[{role:"Cleanse gently",when:"Morning and night",cats:["Cleanser"],con:"dehydration",boost:[[/hydrating|gentle|cream/i,1.5]]},{role:"Hydrate",when:"Morning and night",cats:["Serum","Toner"],con:"dehydration",boost:[[/hyaluronic/i,2]],primary:true},{role:"Seal in moisture",when:"Morning and night",cats:["Moisturiser"],con:"dehydration",boost:[[/ceramide|barrier|rich/i,2]]}],
    expect:"Tightness usually eases within days; the barrier rebuilds over 2–4 weeks."},
  oiliness:{label:"Oily, shiny skin",sub:"Shine, large pores",ic:"dropper",
    follow:{ask:"When does the shine show up?",opts:[
      ["Within an hour of washing","Very oily, all over",{boost:[[/zinc|niacinamide|salicylic/i,2.5]]}],
      ["By midday","Mostly on the forehead and nose",{boost:[[/niacinamide/i,2]]}],
      ["Shine and large pores","Pores look visible",{boost:[[/salicylic|niacinamide/i,2.5]]}]]},
    plan:[{role:"Cleanse",when:"Morning and night",cats:["Cleanser"],con:"oiliness",boost:[[/foaming|clarifying|gel/i,1.5]]},{role:"Balance",when:"Morning or night",cats:["Serum","Toner"],con:"oiliness",primary:true},{role:"Protect",when:"Every morning",cats:["Sunscreen"],con:"oiliness",boost:[[/matte|invisible|aqua/i,2]]}],
    expect:"Shine is usually easier to control within 2–4 weeks. Skipping moisture can make oiliness worse, so keep the routine light, not harsh."},
  tanning:{label:"Tanning and sun damage",sub:"Tan lines, uneven tone from sun",ic:"sun",
    follow:{ask:"How do you usually get tanned?",opts:[
      ["Daily commute","Short spells in the sun",{spf:30,boost:[[/invisible|aqua/i,1.5]]}],
      ["Long hours outdoors","Travel, sport or outdoor work",{spf:50}],
      ["An old tan I'd like to fade","Already there, not getting worse",{boost:[[/vitamin c|ascorb|lactic|glycolic/i,2]]}]]},
    plan:[{role:"Protect",when:"Every morning, reapply outdoors",cats:["Sunscreen"],con:"tanning",primary:true},{role:"Fade",when:"At night",cats:["Serum"],con:"tanning"},{role:"Exfoliate",when:"Twice a week, at night",cats:["Exfoliant"],con:"tanning"}],
    expect:"A tan usually fades over 4–8 weeks once you protect daily. Without sunscreen it keeps coming back."},
  redness:{label:"Redness and sensitivity",sub:"Flushing, stinging, easily irritated",ic:"jar",
    follow:{ask:"What's the redness like?",opts:[
      ["Flushes easily","With heat, spicy food or exercise",{boost:[[/centella|licorice|calming/i,2.5]]}],
      ["Stings with new products","Many products burn or itch",{sensitive:true,frag:true,boost:[[/centella|ceramide|calming/i,2.5]]}],
      ["Red around spots","Mostly where breakouts are",{boost:[[/azelaic|niacinamide/i,2.5]]}]]},
    plan:[{role:"Cleanse gently",when:"Morning and night",cats:["Cleanser"],con:"redness",boost:[[/gentle|cream|hydrating/i,1.5]]},{role:"Calm",when:"Morning and night",cats:["Serum","Toner"],con:"redness",primary:true},{role:"Repair",when:"Morning and night",cats:["Moisturiser"],con:"redness",boost:[[/ceramide|barrier/i,2]]}],
    expect:"Calmer skin usually shows within 2–4 weeks. Add new products one at a time."},
  "fine lines":{label:"Fine lines and firmness",sub:"Early lines, loss of bounce",ic:"dropper",
    follow:{ask:"Have you used retinol before?",opts:[
      ["Never used it","Start gentle",{boost:[[/bakuchiol|peptides|retinol 0\.1/i,2.5]],noStrongRet:true}],
      ["Yes, and it was fine","Stronger options are okay",{boost:[[/retinol/i,2.5]]}],
      ["I'd rather avoid retinol","Plant-based or peptide options",{noRet:true,boost:[[/bakuchiol|peptides/i,3]]}]]},
    plan:[{role:"Renew",when:"At night",cats:["Serum"],con:"fine lines",primary:true},{role:"Nourish",when:"Morning and night",cats:["Moisturiser"],con:"fine lines"},{role:"Protect",when:"Every morning",cats:["Sunscreen"],con:"",boost:[[/./,0]]}],
    expect:"Skin often feels smoother in 4 weeks; visible softening of lines usually takes 3 months or more. Daily sunscreen does the most to prevent new lines."},
  "dark circles":{label:"Dark circles",sub:"Shadows or puffiness under the eyes",ic:"eye",
    follow:{ask:"What do your dark circles look like?",opts:[
      ["Bluish or purple","More visible when tired",{boost:[[/caffeine/i,3]]}],
      ["Brown shadows","Darker skin under the eyes",{boost:[[/vitamin c|niacinamide|bright/i,2.5]]}],
      ["Puffy as well","Swelling in the morning",{boost:[[/caffeine/i,3]]}]]},
    plan:[{role:"Brighten eyes",when:"Morning and night",cats:["Eye cream"],con:"dark circles",primary:true},{role:"Hydrate",when:"Morning and night",cats:["Moisturiser"],con:"dehydration"},{role:"Protect",when:"Every morning",cats:["Sunscreen"],con:""}],
    expect:"Eye creams help with how dark circles look over 4–8 weeks; sleep, allergies and genetics play a big part too."},
};

/* actives that belong to each problem; strong actives outside this list are kept out */
const RELEVANT={acne:/salicylic|azelaic|niacinamide|zinc|tea tree|melaleuca/i,pigmentation:/vitamin c|ascorb|niacinamide|tranexamic|arbutin|licorice|glycyrrhiza|azelaic/i,dullness:/vitamin c|ascorb|lactic|glycolic|niacinamide/i,dehydration:/hyaluronic|ceramide|squalane/i,oiliness:/niacinamide|zinc|salicylic/i,tanning:/vitamin c|ascorb|lactic|glycolic|niacinamide/i,redness:/centella|ceramide|azelaic|licorice|glycyrrhiza|niacinamide/i,"fine lines":/retinol|retinal|bakuchiol|peptide|hyaluronic/i,"dark circles":/caffeine|vitamin c|ascorb|niacinamide|peptide/i};
const HARSH_NAME=/exfoliating|resurfacing|peel|clarifying/i;
/* ---------- ingredient explainer ---------- */
const INGR=[
  [/niacinamide/i,"Niacinamide","helps fade marks, balances oil and strengthens your skin barrier"],
  [/vitamin c|ascorb/i,"Vitamin C","brightens dull skin and helps fade sun spots, and protects against daily pollution"],
  [/salicylic/i,"Salicylic acid (BHA)","gets inside pores to dissolve oil, which helps clear blackheads and breakouts"],
  [/glycolic/i,"Glycolic acid (AHA)","loosens dead skin cells for smoother, brighter skin"],
  [/lactic/i,"Lactic acid","is a gentler exfoliating acid that smooths texture while it hydrates"],
  [/azelaic/i,"Azelaic acid","calms redness, helps with breakouts and fades post-pimple marks"],
  [/bakuchiol/i,"Bakuchiol","is a plant-based alternative to retinol that softens fine lines more gently"],
  [/retinol|retinal|retinyl/i,"Retinol","speeds up skin renewal, which softens fine lines and evens texture over time"],
  [/tranexamic/i,"Tranexamic acid","targets stubborn uneven patches and dark spots"],
  [/arbutin/i,"Alpha arbutin","gently fades dark spots"],
  [/licorice|glycyrrhiza/i,"Licorice extract","calms redness and brightens"],
  [/hyaluronic|sodium hyaluronate/i,"Hyaluronic acid","draws water into the skin so it looks plumper and feels less tight"],
  [/ceramide/i,"Ceramides","rebuild the skin barrier so it holds on to moisture"],
  [/centella/i,"Centella asiatica","soothes irritated, red skin"],
  [/zinc pca/i,"Zinc PCA","helps control oil and keeps pores clearer"],
  [/peptide/i,"Peptides","support firmer, smoother-looking skin"],
  [/caffeine/i,"Caffeine","helps reduce puffiness and the look of dark circles"],
  [/turmeric|curcuma/i,"Turmeric","is a soothing antioxidant that helps brighten"],
  [/saffron|crocus sativus/i,"Saffron extract","is a traditional brightening ingredient"],
  [/squalane/i,"Squalane","softens skin without feeling heavy or clogging pores"],
];
function actives(p){const src=(p.a||"")+" || "+(p.i||"");const out=[];for(const[re,name,does]of INGR)if(re.test(src)&&!out.some(o=>o.name===name)){out.push({name,does,inKey:re.test(p.a||"")})}const rel=n=>PROB&&RELEVANT[PROB]&&RELEVANT[PROB].test(n)?1:0;return out.sort((a,b)=>rel(b.name)-rel(a.name)||b.inKey-a.inKey).slice(0,2)}

/* ---------- state ---------- */
let PROB=null,SUB=null,PREF={boost:[]},FLOW=[],DONE=new Set(),stepNow=null,PL=null,turn=0;
const thread=$("thread");
const DEFAULT_STEPS=["problem","follow","extra","avoid","react","preg","location","skin","tone","shelf","budget"];
let STEPS=[...DEFAULT_STEPS];
const FACE_SKIN=[["Shiny all over","Oily skin","oily"],["Shiny T-zone, normal cheeks","Combination skin","combination"],["Tight, rough or flaky","Dry skin","dry"],["Comfortable","Normal skin","normal"]];
const SK_CATS=["Cleanser","Serum","Moisturiser","Sunscreen","Exfoliant","Toner","Spot treatment","Eye cream"];
const STEP={
  problem:{title:"Your skin",side:"Main concern",q:()=>({ask:"What's bothering your skin the most right now?",help:"Pick **the one that bothers you most**. You can also describe it in your own words below.",
      opts:Object.entries(PROBLEMS).map(([k,v])=>({label:v.label,sub:v.sub,value:k}))}),
    apply:v=>{PROB=v;SUB=null;PREF={boost:[]};P.concerns=[v];for(const k of["follow","extra"])DONE.delete(k)},show:()=>PROBLEMS[PROB]?.label||"–"},
  follow:{title:"Your skin",side:"Details",q:()=>{const F=PROBLEMS[PROB].follow;return{ask:F.ask,opts:F.opts.map(([label,sub],i)=>({label,sub,value:i}))}},
    apply:v=>{const o=PROBLEMS[PROB].follow.opts[v];SUB=o[0];const fx=o[2]||{};PREF={boost:[...(fx.boost||[])],spf:fx.spf||null,gentle:!!fx.gentle,noRet:!!fx.noRet,noStrongRet:!!fx.noStrongRet,escalate:!!fx.escalate,exfoliateFirst:!!fx.exfoliateFirst};
      PREF.forceSens=!!fx.sensitive;PREF.forceFrag=!!fx.frag;if(fx.sensitive)P.sensitive=true;if(fx.frag)P.avoidFrag=true;
      if(fx.noRet&&!P.reactions.includes("retinoids"))P.reactions=[...P.reactions,"retinoids"];},
    show:()=>SUB||"–"},
  extra:{title:"Your skin",side:"Also bothering you",q:()=>{const others=Object.entries(PROBLEMS).filter(([k])=>k!==PROB).map(([k,v])=>({label:v.label,value:k}));
      return{ask:"Anything else you'd like the plan to help with?",help:"Optional. Pick **up to two**, and I'll lean towards products that also help with these.",multi:true,max:2,opts:others,none:"No, just that",pre:P.concerns.filter(c=>c!==PROB)}},
    apply:v=>{P.concerns=uniq([PROB,...v])},show:()=>P.concerns.filter(c=>c!==PROB).map(c=>PROBLEMS[c].label).join(", ")||"Nothing else"},
  avoid:{title:"Safety",side:"Avoid",q:()=>({ask:"Should I avoid any of these?",help:"Pick all that apply. I check **every product's full ingredient list**, not just the label.",multi:true,
      opts:[{label:"Fragrance",sub:"Including hidden fragrance like linalool",value:"frag"},{label:"Essential oils",sub:"Tea tree, lavender, citrus and more",value:"eo"},{label:"Sensitive skin",sub:"Gentler picks and patch-test tips",value:"sens"},{label:"Pores clog easily",sub:"Skip pore-clogging formulas",value:"pores"}],
      none:"None of these",pre:[P.avoidFrag&&"frag",P.avoidEO&&"eo",P.sensitive&&"sens",P.noClog&&"pores"].filter(Boolean)}),
    apply:v=>{P.avoidFrag=v.includes("frag")||!!PREF.forceFrag;P.avoidEO=v.includes("eo");P.sensitive=v.includes("sens")||!!PREF.forceSens;P.noClog=v.includes("pores")},
    show:()=>[P.avoidFrag&&"Fragrance",P.avoidEO&&"Essential oils",P.sensitive&&"Sensitive skin",P.noClog&&"Pore-clogging"].filter(Boolean).join(", ")||"Nothing"},
  react:{title:"Safety",side:"Past reactions",q:()=>({ask:"Have you ever reacted to any of these ingredients?",help:"Pick any that **made your skin sting, itch or break out**, or type another.",multi:true,
      opts:Object.keys(REACTIONS).map(r=>({label:cap(r),value:r})),none:"No reactions",pre:P.reactions}),
    apply:v=>{P.reactions=uniq(v)},show:()=>P.reactions.map(cap).join(", ")||"None"},
  preg:{title:"Safety",side:"Pregnancy caution",q:()=>({ask:"Should I be pregnancy-cautious?",help:"This only means I skip **retinoids and strong salicylic acid**. Your answer stays on this page.",
      opts:[{label:"Yes, be cautious",value:true},{label:"No",value:false},{label:"Prefer not to say",sub:"I'll stay cautious to be safe",value:null}]}),
    apply:v=>{P.pregnancy=v},show:()=>P.pregnancy===null?"Cautious (not answered)":P.pregnancy?"Yes":"No"},
  location:{title:"Location",side:"Location",q:()=>({ask:"Which state and city do you live in?",help:"**Humidity and winter dryness** change which textures work for you.",location:true}),
    show:()=>P.city?`${P.city}, ${P.state}`:"Skipped"},
  skin:{title:"Your skin",side:"Skin type",q:()=>({ask:"How does your skin feel by midday, without products?",help:"Think of **midday, before any products**. Describing what you notice is more reliable than picking a label.",
      opts:FACE_SKIN.map(([label,sub,value])=>({label,sub,value}))}),
    apply:v=>{P.skin=v;P.skinConfirmed=true},show:()=>cap(P.skin)||"–"},
  tone:{title:"Your skin",side:"Skin tone",q:()=>({ask:"What's your skin tone?",help:"Tap **the closest shade**. Deeper skin marks more easily, so this changes **which ingredients and sunscreens** I pick.",tone:true}),
    show:()=>{if(!P.tone)return"Skipped";const src=P.toneSource||"";const m=/(\d) selfies/.exec(src);return`Tone ${P.tone} (${MONK_LABEL[P.tone]})${m?`, from ${m[1]} selfies`:/selfie/.test(src)?", from selfie":""}`}},
  shelf:{title:"Your routine",side:"Already using",q:()=>({ask:"What are you already using on your face?",help:"I'll **build around what you have**, skip steps you've already covered, and make sure nothing new **clashes** with it.",shelf:true}),
    apply:v=>{P.shelf=v},show:()=>{const it=shelfItems();return it.length?it.map(o=>o.short).join(", "):"Nothing yet"}},
  budget:{title:"Budget",side:"Budget",q:()=>({ask:"What's your budget per product?",help:"I'll keep **all three products** under this price.",
      opts:[{label:"Under ₹400",sub:"Most affordable",value:400},{label:"Under ₹700",sub:"Good mid-range choice",value:700},{label:"Under ₹1,200",sub:"Wider choice",value:1200},{label:"No limit",sub:"The best match regardless of price",value:null}]}),
    apply:v=>{P.budget=v},show:()=>P.budget?`Under ${rupee(P.budget)}`:"No limit"},
};

/* ---------- concern illustrations (drawn, not photos): a close-up of skin for each concern ---------- */
const ART=(()=>{
  const wrap=(id,inner)=>`<svg viewBox="0 0 96 96" role="img" aria-hidden="true"><defs><radialGradient id="sk${id}" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="#f6d2b8"/><stop offset="1" stop-color="#dfa585"/></radialGradient><clipPath id="cp${id}"><circle cx="48" cy="48" r="46"/></clipPath></defs><g clip-path="url(#cp${id})"><rect width="96" height="96" fill="url(#sk${id})"/>${inner}</g><circle cx="48" cy="48" r="46" fill="none" stroke="rgba(125,23,76,.18)" stroke-width="1.5"/></svg>`;
  const dots=(arr,fn)=>arr.map(fn).join("");
  return{
    acne:wrap("a",dots([[30,34,5],[58,28,4],[66,56,5.5],[40,62,4.5],[50,46,3.5]],([x,y,r])=>`<circle cx="${x}" cy="${y}" r="${r+3}" fill="#e98a86" opacity=".45"/><circle cx="${x}" cy="${y}" r="${r}" fill="#d9625e"/><circle cx="${x-1}" cy="${y-1}" r="${r*.38}" fill="#fff6e8"/>`)+dots([[22,54],[74,40],[34,78],[62,74]],([x,y])=>`<circle cx="${x}" cy="${y}" r="1.6" fill="#5b3a2e"/>`)),
    pigmentation:wrap("p",`<ellipse cx="34" cy="36" rx="9" ry="7" fill="#a86a48" opacity=".75"/><ellipse cx="60" cy="30" rx="5" ry="4" fill="#9a5c3c" opacity=".7"/><ellipse cx="62" cy="58" rx="11" ry="8" fill="#b47452" opacity=".6"/><ellipse cx="38" cy="66" rx="6" ry="5" fill="#8f5536" opacity=".7"/><circle cx="50" cy="48" r="2.5" fill="#8a5233" opacity=".8"/><circle cx="24" cy="52" r="2" fill="#8a5233" opacity=".7"/>`),
    dullness:wrap("d",`<rect width="48" height="96" fill="#9d8f88" opacity=".45"/><path d="M48 0v96" stroke="#fff" stroke-width="1.5" stroke-dasharray="4 4" opacity=".9"/><ellipse cx="68" cy="34" rx="10" ry="6" fill="#fff" opacity=".55"/><path d="M76 58l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="#fff" opacity=".9"/>`),
    dehydration:wrap("h",`<path d="M10 40l14 4 10-6 12 8 14-5 12 7 14-4M6 62l16-3 9 6 15-4 10 7 16-5 14 4M28 20l6 10-4 12M64 18l-4 12 6 10M40 70l-3 16M70 66l4 18" stroke="#b9826a" stroke-width="1.6" fill="none" opacity=".75"/>`+dots([[30,30],[52,26],[70,48],[22,74],[56,80],[44,52]],([x,y])=>`<path d="M${x} ${y}l6 -2 2 4 -5 3z" fill="#fbeee4" opacity=".95"/>`)),
    oiliness:wrap("o",`<ellipse cx="40" cy="32" rx="16" ry="7" fill="#fff" opacity=".6" transform="rotate(-18 40 32)"/><ellipse cx="62" cy="58" rx="12" ry="5" fill="#fff" opacity=".5" transform="rotate(-18 62 58)"/><ellipse cx="34" cy="64" rx="6" ry="3" fill="#fff" opacity=".45"/>`+dots([[26,46],[34,50],[46,44],[54,40],[68,36],[72,46],[44,74],[56,72],[64,78],[30,80]],([x,y])=>`<circle cx="${x}" cy="${y}" r="1.7" fill="#b07a5f" opacity=".85"/>`)),
    tanning:wrap("t",`<path d="M0 54 C30 46 60 62 96 50 V96 H0z" fill="#b07048" opacity=".75"/><path d="M0 54 C30 46 60 62 96 50" stroke="#fff" stroke-width="1.4" fill="none" stroke-dasharray="3 3" opacity=".8"/><circle cx="74" cy="22" r="8" fill="#ffd36e"/><path d="M74 8v4M74 32v4M60 22h4M84 22h4M64 12l3 3M81 29l3 3M64 32l3-3M81 15l3-3" stroke="#ffd36e" stroke-width="2" stroke-linecap="round"/>`),
    redness:wrap("r",`<ellipse cx="48" cy="52" rx="34" ry="24" fill="#e0716a" opacity=".38"/><ellipse cx="40" cy="48" rx="18" ry="12" fill="#d9524c" opacity=".3"/><path d="M26 44c6-2 8 3 14 1M54 62c5-3 9 1 14-2M50 38c3 2 6 0 9 2M30 60c4 1 6-2 10-1" stroke="#c4413c" stroke-width="1.2" fill="none" opacity=".7"/>`),
    "fine lines":wrap("f",`<path d="M14 40 C28 28 50 28 62 38" stroke="#6b4a3c" stroke-width="2.6" fill="none" stroke-linecap="round"/><path d="M18 38l-3-6M26 33l-2-6M35 30l-1-6M45 30l0-6M54 33l2-6" stroke="#6b4a3c" stroke-width="1.6" stroke-linecap="round"/><path d="M66 40 C74 36 80 34 88 34M66 46 C75 46 82 48 90 50M64 52 C72 56 78 62 84 68" stroke="#a87660" stroke-width="1.5" fill="none" stroke-linecap="round" opacity=".85"/><path d="M24 62c10 4 22 4 32 0" stroke="#b98670" stroke-width="1.3" fill="none" opacity=".8"/>`),
    "dark circles":wrap("c",`<path d="M16 42 C30 30 66 30 80 42" stroke="#6b4a3c" stroke-width="2.6" fill="none" stroke-linecap="round"/><path d="M22 41l-3-6M32 36l-2-6M44 34v-6M56 35l2-6M68 38l3-6" stroke="#6b4a3c" stroke-width="1.6" stroke-linecap="round"/><path d="M18 50 C34 72 62 72 78 50 C62 62 34 62 18 50z" fill="#7e5a76" opacity=".55"/><path d="M22 52 C36 66 60 66 74 52" stroke="#6a4763" stroke-width="1" fill="none" opacity=".6"/>`),
  };
})();

/* ---------- more drawn illustrations for other journey steps ---------- */
const ART2=(()=>{
  const skin=(id,inner)=>`<svg viewBox="0 0 96 96" role="img" aria-hidden="true"><defs><radialGradient id="s2${id}" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="#f6d2b8"/><stop offset="1" stop-color="#dfa585"/></radialGradient><clipPath id="c2${id}"><circle cx="48" cy="48" r="46"/></clipPath></defs><g clip-path="url(#c2${id})"><rect width="96" height="96" fill="url(#s2${id})"/>${inner}</g><circle cx="48" cy="48" r="46" fill="none" stroke="rgba(125,23,76,.18)" stroke-width="1.5"/></svg>`;
  const tile=(inner)=>`<svg viewBox="0 0 96 96" role="img" aria-hidden="true"><circle cx="48" cy="48" r="46" fill="#fbe7ef"/><circle cx="48" cy="48" r="46" fill="none" stroke="rgba(125,23,76,.18)" stroke-width="1.5"/>${inner}</svg>`;
  /* a little face for skin-type: zones get shine, flakes or nothing */
  const face=(id,zone)=>`<svg viewBox="0 0 96 96" role="img" aria-hidden="true"><defs><radialGradient id="f2${id}" cx="45%" cy="35%" r="70%"><stop offset="0" stop-color="#f6d2b8"/><stop offset="1" stop-color="#dba080"/></radialGradient></defs><circle cx="48" cy="48" r="46" fill="#fbe7ef"/><circle cx="48" cy="48" r="46" fill="none" stroke="rgba(125,23,76,.18)" stroke-width="1.5"/><path d="M26 30c0-14 10-22 22-22s22 8 22 22v18c0 18-10 32-22 32S26 66 26 48z" fill="#5a3326"/><ellipse cx="48" cy="50" rx="20" ry="26" fill="url(#f2${id})"/><path d="M28 34c4-12 12-16 20-16s16 4 20 16c-6-6-12-8-20-8s-14 2-20 8z" fill="#5a3326"/><path d="M38 47h5M53 47h5" stroke="#5a3326" stroke-width="2" stroke-linecap="round"/><path d="M48 50v8l-2 1" stroke="#b77d60" stroke-width="1.4" fill="none" stroke-linecap="round"/><path d="M43 66c3 2 7 2 10 0" stroke="#a0524a" stroke-width="1.8" fill="none" stroke-linecap="round"/>${zone}</svg>`;
  const shine=(x,y,rx,ry,o=.75)=>`<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="#fff" opacity="${o}"/>`;
  const flake=(x,y)=>`<path d="M${x} ${y}l4-1.5 1.5 3-3.5 2z" fill="#fff6ee" stroke="#b9826a" stroke-width=".6"/>`;
  return{
    /* skin type */
    oily:face("o",shine(48,38,7,2.6)+shine(48,56,2,3.5)+shine(36,56,4,2.4,.6)+shine(60,56,4,2.4,.6)+shine(48,72,3,1.4,.55)),
    combination:face("c",shine(48,38,8,2.6)+shine(48,56,2,3.8)+shine(48,72,3,1.4,.6)+`<path d="M38 33h20v4h-7v32h-6V37h-7z" fill="none" stroke="#c45b8a" stroke-width="1" stroke-dasharray="2 2" opacity=".8"/>`),
    dry:face("d",flake(34,56)+flake(58,58)+flake(44,36)+flake(54,40)+flake(40,62)+`<path d="M31 60l4 2 3-2M57 62l4 1 3-2" stroke="#b9826a" stroke-width=".9" fill="none"/>`),
    normal:face("n",`<path d="M70 26l1.6 4 4 1.6-4 1.6-1.6 4-1.6-4-4-1.6 4-1.6z" fill="#e0a64a"/><circle cx="36" cy="58" r="4" fill="#f0a3a0" opacity=".35"/><circle cx="60" cy="58" r="4" fill="#f0a3a0" opacity=".35"/>`),
    /* avoid */
    frag:tile(`<rect x="34" y="40" width="28" height="34" rx="6" fill="#f3c6d8" stroke="#7d174c" stroke-width="2"/><rect x="42" y="30" width="12" height="10" rx="2" fill="#7d174c"/><rect x="44" y="24" width="8" height="6" rx="1.5" fill="#c45b8a"/><path d="M58 22c4-3 8-1 10 2M62 30c5-1 8 2 9 5M56 16c2-3 6-4 9-2" stroke="#c45b8a" stroke-width="1.8" fill="none" stroke-linecap="round"/><path d="M40 52h16" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".8"/>`),
    eo:tile(`<path d="M30 70c0-20 14-34 34-38-2 22-14 36-34 38z" fill="#7fb07a"/><path d="M32 68c8-10 16-18 28-30" stroke="#4f8a4a" stroke-width="1.6" fill="none"/><rect x="52" y="44" width="16" height="26" rx="4" fill="#d9a35a" stroke="#8a5a1e" stroke-width="1.6"/><rect x="55" y="36" width="10" height="8" rx="1.5" fill="#5a3326"/><path d="M60 24c0 4-3 6-3 8a3 3 0 0 0 6 0c0-2-3-4-3-8z" fill="#e9b65e"/>`),
    sens:skin("se",`<ellipse cx="44" cy="52" rx="28" ry="20" fill="#e0716a" opacity=".38"/><path d="M28 48c5-2 7 2 12 1M50 60c4-2 8 1 12-1M44 40c3 2 6 0 9 2" stroke="#c4413c" stroke-width="1.2" fill="none" opacity=".7"/><path d="M66 22l12 4v9c0 8-5 13-12 16-7-3-12-8-12-16v-9z" fill="#fff" stroke="#7d174c" stroke-width="2"/><path d="M61 35l4 4 7-8" stroke="#7d174c" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`),
    pores:skin("po",`<circle cx="36" cy="40" r="9" fill="#c98f72"/><circle cx="36" cy="40" r="5" fill="#3d2a24"/><circle cx="62" cy="34" r="6" fill="#c98f72"/><circle cx="62" cy="34" r="3" fill="#3d2a24"/><circle cx="56" cy="62" r="10" fill="#c98f72"/><circle cx="56" cy="62" r="6" fill="#f3ead2"/><circle cx="54" cy="60" r="2" fill="#fff"/><circle cx="30" cy="66" r="4" fill="#c98f72"/><circle cx="30" cy="66" r="2" fill="#3d2a24"/>`),
    /* past-reaction ingredients: where each one usually comes from */
    "glycolic acid":tile(`<path d="M40 80V22M54 80V18" stroke="#8fb36a" stroke-width="7" stroke-linecap="round"/><path d="M36 40h8M36 58h8M50 34h8M50 54h8" stroke="#5f8a3c" stroke-width="2"/><path d="M54 22c8-6 16-4 20 0-8 0-14 2-20 6z" fill="#7fb07a"/>`),
    "salicylic acid":tile(`<path d="M48 82V30" stroke="#8a5a3c" stroke-width="5" stroke-linecap="round"/>${[[36,34,-30],[60,40,30],[36,52,-30],[60,58,30],[38,70,-25]].map(([x,y,r])=>`<ellipse cx="${x}" cy="${y}" rx="11" ry="4" fill="#9cc48a" transform="rotate(${r} ${x} ${y})"/>`).join("")}`),
    "vitamin c":tile(`<circle cx="48" cy="48" r="24" fill="#f7b04a"/><circle cx="48" cy="48" r="19" fill="#fcd27b"/>${[0,45,90,135].map(a=>`<path d="M48 48L${48+19*Math.cos(a*Math.PI/180)} ${48+19*Math.sin(a*Math.PI/180)}M48 48L${48-19*Math.cos(a*Math.PI/180)} ${48-19*Math.sin(a*Math.PI/180)}" stroke="#f7b04a" stroke-width="2"/>`).join("")}<circle cx="48" cy="48" r="3" fill="#f7b04a"/>`),
    retinoids:tile(`<rect x="36" y="42" width="24" height="34" rx="5" fill="#e0a0bd" stroke="#7d174c" stroke-width="2"/><rect x="40" y="32" width="16" height="10" rx="2" fill="#7d174c"/><rect x="44" y="18" width="8" height="14" rx="4" fill="#c45b8a"/><path d="M42 56h12M42 62h8" stroke="#fff" stroke-width="2" stroke-linecap="round"/><path d="M68 70c0 3-2 4-2 6a2.2 2.2 0 0 0 4.4 0c0-2-2.4-3-2.4-6z" fill="#c45b8a"/>`),
    "tea tree oil":tile(`<path d="M48 80V24" stroke="#6b8f4e" stroke-width="2.5"/>${[30,40,50,60,70].map((y,i)=>`<path d="M48 ${y}l-14 -6M48 ${y}l14 -6" stroke="#5f9a52" stroke-width="3" stroke-linecap="round"/>`).join("")}`),
    "lavender oil":tile(`<path d="M42 82V40M54 82V36" stroke="#6b8f4e" stroke-width="2.5"/>${[22,28,34,40,46].map(y=>`<ellipse cx="42" cy="${y+4}" rx="4" ry="3" fill="#9d7fd0"/><ellipse cx="54" cy="${y}" rx="4" ry="3" fill="#8a6cc4"/>`).join("")}`),
    linalool:tile(`${[0,72,144,216,288].map(a=>`<ellipse cx="48" cy="34" rx="7" ry="13" fill="#f4b8cf" transform="rotate(${a} 48 48)"/>`).join("")}<circle cx="48" cy="48" r="7" fill="#f2c94c"/><path d="M66 24c3-2 6-1 7 1M70 32c3 0 5 2 5 4" stroke="#c45b8a" stroke-width="1.6" fill="none" stroke-linecap="round"/>`),
    niacinamide:tile(`<rect x="26" y="38" width="44" height="20" rx="10" fill="#fff" stroke="#7d174c" stroke-width="2" transform="rotate(-30 48 48)"/><path d="M48 38v20" stroke="#7d174c" stroke-width="2" transform="rotate(-30 48 48)"/><rect x="26" y="38" width="22" height="20" rx="10" fill="#c45b8a" transform="rotate(-30 48 48)"/><text x="48" y="80" text-anchor="middle" font-size="12" font-weight="700" font-family="sans-serif" fill="#7d174c">B3</text>`),
    "lactic acid":tile(`<path d="M38 30h20l-2 8 6 10v28H34V48l6-10z" fill="#fff" stroke="#7d174c" stroke-width="2" stroke-linejoin="round"/><path d="M34 56h28v20H34z" fill="#f6e7d8"/><path d="M38 30h20" stroke="#7d174c" stroke-width="3"/>`),
    "azelaic acid":tile(`${[[40,30],[56,30],[48,42],[36,48],[60,48],[48,56],[42,68],[54,68]].map(([x,y])=>`<ellipse cx="${x}" cy="${y}" rx="5" ry="8" fill="#d8b46a" stroke="#a07a32" stroke-width="1"/>`).join("")}<path d="M48 76v8" stroke="#a07a32" stroke-width="2"/>`),
    /* budget: coin stacks */
    b400:tile(`<ellipse cx="48" cy="64" rx="16" ry="5" fill="#d9a441"/><rect x="32" y="58" width="32" height="6" fill="#e8b84f"/><ellipse cx="48" cy="58" rx="16" ry="5" fill="#f6d17a" stroke="#c48f2a"/><text x="48" y="42" text-anchor="middle" font-size="18" font-weight="700" font-family="sans-serif" fill="#7d174c">₹</text>`),
    b700:tile(`${[66,58,50].map(y=>`<ellipse cx="48" cy="${y+6}" rx="16" ry="5" fill="#d9a441"/><rect x="32" y="${y}" width="32" height="6" fill="#e8b84f"/><ellipse cx="48" cy="${y}" rx="16" ry="5" fill="#f6d17a" stroke="#c48f2a"/>`).join("")}<text x="48" y="34" text-anchor="middle" font-size="18" font-weight="700" font-family="sans-serif" fill="#7d174c">₹₹</text>`),
    b1200:tile(`${[66,58,50,42,34].map(y=>`<ellipse cx="48" cy="${y+6}" rx="16" ry="5" fill="#d9a441"/><rect x="32" y="${y}" width="32" height="6" fill="#e8b84f"/><ellipse cx="48" cy="${y}" rx="16" ry="5" fill="#f6d17a" stroke="#c48f2a"/>`).join("")}<text x="48" y="22" text-anchor="middle" font-size="14" font-weight="700" font-family="sans-serif" fill="#7d174c">₹₹₹</text>`),
    bnone:tile(`<path d="M30 48c0-8 10-8 18 0s18 8 18 0-10-8-18 0-18 8-18 0z" fill="none" stroke="#7d174c" stroke-width="4" stroke-linecap="round"/>`),
    /* pregnancy */
    pyes:tile(`<path d="M48 26l14 5v11c0 10-6 16-14 20-8-4-14-10-14-20V31z" fill="#fff" stroke="#7d174c" stroke-width="2.2"/><path d="M42 44l4 4 8-9" stroke="#7d174c" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M38 72c4-4 16-4 20 0" stroke="#c45b8a" stroke-width="2" fill="none" stroke-linecap="round"/>`),
    pno:tile(`<circle cx="48" cy="48" r="18" fill="#fff" stroke="#7d174c" stroke-width="2.2"/><path d="M40 48l6 6 11-12" stroke="#7d174c" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`),
    pskip:tile(`<rect x="34" y="44" width="28" height="22" rx="4" fill="#fff" stroke="#7d174c" stroke-width="2.2"/><path d="M40 44v-6a8 8 0 0 1 16 0v6" fill="none" stroke="#7d174c" stroke-width="2.2"/><circle cx="48" cy="55" r="3" fill="#7d174c"/>`),
  };
})();
/* which picture goes with which answer, per step */
let ART_N=0;
/* each drawing gets its own gradient ids, so a picture still renders when an earlier copy is hidden */
function artFor(key,o){const svg=artPick(key,o);if(!svg)return null;const n=++ART_N;return svg.replace(/id="([\w-]+)"/g,`id="$1_${n}"`).replace(/url\(#([\w-]+)\)/g,`url(#$1_${n})`)}
function artPick(key,o){
  if(key==="problem"||key==="extra")return ART[o.value];
  if(key==="skin"||key==="avoid"||key==="react")return ART2[o.value];
  if(key==="budget")return ART2[o.value===400?"b400":o.value===700?"b700":o.value===1200?"b1200":"bnone"];
  if(key==="preg")return ART2[o.value===true?"pyes":o.value===false?"pno":"pskip"];
  return null;
}
const ART_BIG=new Set(["problem","extra","skin","avoid"]),ART_MID=new Set(["react","budget","preg"]);

/* ---------- warmth: greeting, name, empathy, encouragement ---------- */
let NAME=null,nameAsked=false;
const nm=(pre="",post="")=>NAME?`${pre}${esc(NAME)}${post}`:"";
function dayPart(){const h=new Date().getHours();
  const moon=SVG('<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>'),sun=SVG('<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4"/>'),rise=SVG('<circle cx="12" cy="15" r="4"/><path d="M12 5v3M4.9 9.9l2.1 2.1M19.1 9.9L17 12M3 20h18"/>');
  if(h>=5&&h<12)return{hello:"Good morning!",line:"Let's start your day with a little care for your skin.",ic:rise};
  if(h>=12&&h<17)return{hello:"Good afternoon!",line:"Let's take a look at your skin together.",ic:sun};
  if(h>=17&&h<22)return{hello:"Good evening!",line:"Let's take a look at your skin together.",ic:moon};
  return{hello:"Hello, night owl!",line:"Let's take a look at your skin together.",ic:moon};}
const EMPATHY={
  acne:"Breakouts can really knock your confidence, and you're far from alone in this. <b>The right routine makes a real difference</b>, and I'll keep it simple.",
  pigmentation:"Dark spots can feel stubborn, but they <b>do fade</b> with steady care and <b>daily sunscreen</b>. Let's set you up for that.",
  dullness:"Let's <b>bring your glow back</b>. Dull skin usually just needs the right brightening steps, done consistently.",
  dehydration:"Tight, uncomfortable skin is no fun. Let's get it feeling <b>soft and comfortable</b> again.",
  oiliness:"Midday shine can be frustrating, but oily skin is <b>very manageable</b>. A few steady habits keep it in check.",
  tanning:"Let's <b>protect your skin</b> from here on and gently fade the tan that's already there.",
  redness:"Sensitive skin deserves kindness. I'll keep every pick <b>gentle and calming</b>.",
  "fine lines":"Fine lines are a natural part of your skin's story. We'll keep it <b>smooth, strong and well protected</b>.",
  "dark circles":"Let's help your eyes look <b>as rested</b> as you'd like them to feel.",
};
let OPEN_SELFIE=false;
function showWelcome(){
  const d=dayPart();$("greetText").textContent=d.hello;$("greetIc").innerHTML=d.ic;$("greetSub").textContent=d.line;
  $("welcome").hidden=false;$("advisor").hidden=true;renderResume();$("nameInput").value=NAME||"";$("nameGo").disabled=!cleanName(NAME||"");
  requestAnimationFrame(()=>$("nameInput").focus({preventScroll:true}));
}
function askName(){showWelcome()}
function cleanName(v){const n=String(v||"").replace(/[^\p{L}\p{M}' .-]/gu,"").trim().split(/\s+/)[0]||"";return n.length>=1&&n.length<=24?n[0].toUpperCase()+n.slice(1):""}
function setName(n,startKey){
  NAME=n;nameAsked=true;
  $("welcome").hidden=true;$("advisor").hidden=false;thread.innerHTML="";CUR_BLOCK=null;
  if(startKey&&startKey!=="problem"){STEPS=[startKey,...STEPS.filter(k=>k!==startKey)];if(startKey==="tone")OPEN_SELFIE=true}
  const d=dayPart();
  botSay(n?`<p>${d.hello.replace("!","")}, <b>${esc(n)}</b>! Lovely to meet you. Tell me what's bothering your skin, and I'll put together <b>three products that work together</b>, then explain exactly why I chose each one.</p><p class="small muted">It takes about two minutes, and every pick is checked against what you tell me.</p>`
          :`<p>${d.hello} No problem at all. ${startKey==="tone"?"Let's start with your skin tone, then I'll ask what's bothering your skin":startKey==="skin"?"Let's start with your skin type, then I'll ask what's bothering your skin":"Tell me what's bothering your skin"}, and I'll put together <b>three products that work together</b>, then explain exactly why I chose each one.</p><p class="small muted">It takes about two minutes, and every pick is checked against what you tell me.</p>`);
  updateTitle();next();saveState();
}
function updateTitle(){
  $("advTitle").textContent=PROB?`${NAME?NAME+"'s":"Your"} plan for ${PROBLEMS[PROB].label.toLowerCase()}`:NAME?`Hi ${NAME}, let's find your three`:"Three products for your skin";
}
/* ---------- thread helpers ---------- */
function avatar(){return`<div class="av brandav" aria-hidden="true"><span class="brandmark"></span></div>`}
let CUR_BLOCK=null;const host=()=>CUR_BLOCK&&CUR_BLOCK.isConnected?CUR_BLOCK:thread;
const fmt=t=>esc(t).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>");
function newBlock(step){
  const b=document.createElement("div");b.className="stepblock";b.dataset.step=step;
  const carry=[];
  for(const el of [...thread.children]){if(el.classList.contains("past"))continue;
    if(!el.classList.contains("stepblock")){if(el.classList.contains("row")&&!el.classList.contains("me"))carry.push(el);else el.classList.add("past");continue}
    let after=false;for(const c of [...el.children]){if(c.classList.contains("q")){after=true;continue}if(after&&c.classList.contains("row")&&!c.classList.contains("me"))carry.push(c)}
    el.classList.add("past")}
  for(const c of carry){c.classList.add("carried");b.appendChild(c)}
  thread.appendChild(b);CUR_BLOCK=b;thread.scrollTop=0;return b}
function botSay(html,kind=""){const r=document.createElement("div");r.className="row";r.innerHTML=avatar()+`<div class="say ${kind}">${html}</div>`;host().appendChild(r);focusEl(r);return r}
function meSay(text){const r=document.createElement("div");r.className="row me";const s=document.createElement("div");s.className="say";s.textContent=text;r.appendChild(s);host().appendChild(r)}
function focusEl(el){requestAnimationFrame(()=>el.scrollIntoView({block:"nearest",behavior:"smooth"}))}
function lockAll(){thread.querySelectorAll(".q:not(.answered)").forEach(q=>{q.classList.add("answered");q.querySelectorAll("button,select,input").forEach(x=>{if(!x.classList.contains("backcta"))x.disabled=true})})}
function progress(){const d=STEPS.filter(k=>DONE.has(k)).length,left=STEPS.length-d;$("bar").style.width=(100*d/STEPS.length)+"%";$("backBtn").disabled=false;
  $("eta").textContent=!nameAsked?"About 2 minutes":left===0?"Your plan is ready":left===1?"Last step":left<=3?"Almost there":`About ${Math.max(1,Math.round(left*10/60))} minute${Math.round(left*10/60)>1?"s":""} left`}

function next(){
  if(!nameAsked){progress();askName();return}
  stepNow=STEPS.find(k=>!DONE.has(k))||null;renderSide();updateTitle();
  if(stepNow)ask(stepNow);else buildPlan();
}
function ask(key){
  lockAll();const s=STEP[key],Q=s.q();const idx=STEPS.indexOf(key)+1;
  const box=document.createElement("div");box.className="q";box.dataset.step=key;
  box.innerHTML=`<div class="row qhead">${avatar()}<div><span class="qnum">Q${idx} of ${STEPS.length} · ${esc(s.title)}${STEPS.length-idx===0?" · last one":""}</span><h3 class="qtitle">${esc(Q.ask)}</h3>${Q.help?`<p class="qhelp">${fmt(Q.help)}</p>`:""}</div></div>`;
  box.appendChild(Q.location?locationWidget():Q.tone?toneWidget():Q.shelf?shelfWidget():optionsWidget(key,Q));
  const nav=document.createElement("div");nav.className="qnav";nav.innerHTML=`<button type="button" class="btn backcta">${SVG('<path d="M15 6l-6 6 6 6"/>')}Back</button><span class="qnav-step">Question ${idx} of ${STEPS.length}</span>`;
  nav.querySelector("button").onclick=goBack;box.appendChild(nav);
  newBlock(key).appendChild(box);progress();requestAnimationFrame(()=>thread.scrollTo({top:0}));
}
function optionsWidget(key,Q){
  const w=document.createElement("div");w.className="qbody";
  const grid=document.createElement("div");grid.className="opts"+(ART_BIG.has(key)?" big":ART_MID.has(key)?" big mid":"");
  const picked=new Set(Q.pre||[]);
  const done=document.createElement("button");done.type="button";done.className="btn primary";
  const update=()=>{done.textContent=picked.size?`Continue with ${picked.size}`:"Continue"};
  for(const o of Q.opts){const b=document.createElement("button");b.type="button";b.className="opt";
    const art=artFor(key,o);if(!o.sub&&art)b.classList.add("nosub");b.innerHTML=`${art?`<i class="art">${art}</i>`:""}<b>${esc(o.label)}</b>${o.sub?`<span>${esc(o.sub)}</span>`:""}`;
    if(Q.multi){b.setAttribute("aria-pressed",String(picked.has(o.value)));b.onclick=()=>{if(picked.has(o.value))picked.delete(o.value);else{if(Q.max&&picked.size>=Q.max)return;picked.add(o.value)}b.setAttribute("aria-pressed",String(picked.has(o.value)));update()}}
    else b.onclick=()=>{b.setAttribute("aria-pressed","true");answer(key,o.value,o.label)};
    grid.appendChild(b)}
  w.appendChild(grid);
  if(Q.multi){update();const a=document.createElement("div");a.className="qactions";done.onclick=()=>{const v=[...picked];answer(key,v,v.length?Q.opts.filter(o=>picked.has(o.value)).map(o=>o.label).join(", "):Q.none)};
    const none=document.createElement("button");none.type="button";none.className="btn";none.textContent=Q.none;none.onclick=()=>answer(key,[],Q.none);a.append(done,none);w.appendChild(a)}
  return w;
}
function answer(key,val,label){
  turn++;if(key==="follow")FOLLOW_IDX=val;if(key!=="tone"||val!==undefined)STEP[key].apply&&STEP[key].apply(val);DONE.add(key);lockAll();
  const note=afterNote(key);if(note)botSay(note[0],note[1]||"");
  next();saveState();
}
function afterNote(key){
  if(key==="problem")return[`<p>${nm("","," )} ${NAME?EMPATHY[PROB][0].toLowerCase()+EMPATHY[PROB].slice(1):EMPATHY[PROB]}</p><p class="small muted">A few quick questions so I can choose <b>the right three</b> for you.</p>`];
  if(key==="preg")return[`Thank you${nm(", ")}. <b>That's the important safety part done.</b> Now a little about where you live and your skin.`];
  if(key==="follow"&&PREF.escalate)return["<p>Deep, painful lumps are best looked at by a dermatologist, as they can scar and may need treatment I can't give. I'll still suggest a gentle, low-irritation plan for day-to-day care.</p>","escalate"];
  if(key==="follow"&&P.sensitive&&P.avoidFrag&&PROB==="redness")return["That sounds uncomfortable. I'll keep everything fragrance-free and extra gentle."];
  {const left=STEPS.filter(k=>!DONE.has(k)).length;
   if(left===1)return[`<b>Last question${nm(", ")}!</b> Your plan is ready right after this.`];
   if(left===2&&key!=="problem")return[`You're doing great${nm(", ")}. <b>Just two more</b> and your plan is ready.`];}
  if(key==="follow")return[`Thanks, that really helps me narrow it down.`];
  if(key==="location"&&P.city){const se=seasonFor();return[`${esc(P.city)} is mostly <b>${CLIMATE_SAY[P.climate]}</b>${se?`, and it's <b>${esc(se.say)}</b> there now`:""}. I'll pick textures to suit${P.seasonAlert&&se?`, and remind you to refresh your plan when ${esc(se.nextSay)} arrives`:""}.`]}
  return null;
}
function locationWidget(){
  const w=document.createElement("div");w.className="qbody";const states=Object.keys(INDIA).sort((a,b)=>a.localeCompare(b));
  const ALLC=[];for(const s of states)for(const c of Object.keys(INDIA[s].c))ALLC.push([c,s]);
  w.innerHTML=`<label class="citysearch">Search your city<input data-find type="search" list="cityList" autocomplete="off" placeholder="Start typing, e.g. Tezpur or Kochi"><datalist id="cityList">${ALLC.map(([c,s])=>`<option value="${esc(c)}, ${esc(s)}"></option>`).join("")}</datalist></label>
    <p class="small muted" style="margin:2px 0 8px">Or choose your state and city below. ${ALLC.length.toLocaleString("en-IN")} cities listed.</p>
    <div class="loc"><label>State or union territory<select data-st><option value="">Choose your state</option>${states.map(s=>`<option${s===P.state?" selected":""}>${esc(s)}</option>`).join("")}</select></label>
    <label>City<select data-ct disabled><option value="">Choose your state first</option></select></label>
    <label data-ow hidden>Your city<input data-other type="text" maxlength="40" placeholder="Type your city"></label></div>
    <div data-season></div>
    <div class="qactions"><button type="button" class="btn primary" data-go disabled>Continue</button></div>`;
  const st=w.querySelector("[data-st]"),ct=w.querySelector("[data-ct]"),ow=w.querySelector("[data-ow]"),other=w.querySelector("[data-other]"),go=w.querySelector("[data-go]");
  const seasonBox=w.querySelector("[data-season]");
  const ready=()=>{const ok=!!(st.value&&ct.value&&(ct.value!=="__other"||other.value.trim()));go.disabled=!ok;
    if(ok){const s=INDIA[st.value],listed=ct.value!=="__other",city=listed?ct.value:other.value.trim();const html=seasonCardHTML(city,st.value,(listed&&s.c[ct.value])||s.d);if(seasonBox.dataset.k!==city+st.value){seasonBox.innerHTML=html;seasonBox.dataset.k=city+st.value;focusEl(go)}}
    else{seasonBox.innerHTML="";seasonBox.dataset.k=""}};
  const fill=()=>{const s=INDIA[st.value];ct.innerHTML=s?`<option value="">Choose your city</option>`+Object.keys(s.c).sort((a,b)=>a.localeCompare(b)).map(c=>`<option${c===P.city?" selected":""}>${esc(c)}</option>`).join("")+`<option value="__other">My city isn't listed</option>`:`<option value="">Choose your state first</option>`;ct.disabled=!s;ow.hidden=true;ready()};
  st.onchange=fill;if(st.value)fill();
  const find=w.querySelector("[data-find]");find.oninput=()=>{const v=find.value.trim().toLowerCase();const hit=ALLC.find(([c,s])=>`${c}, ${s}`.toLowerCase()===v)||(v.length>2&&ALLC.filter(([c])=>c.toLowerCase()===v).length===1&&ALLC.find(([c])=>c.toLowerCase()===v));
    if(hit){st.value=hit[1];fill();ct.value=hit[0];ow.hidden=true;ready()}};ct.onchange=()=>{ow.hidden=ct.value!=="__other";if(!ow.hidden)other.focus();ready()};other.oninput=ready;
  go.onclick=()=>{const s=INDIA[st.value],listed=ct.value!=="__other",city=listed?ct.value:other.value.trim().replace(/\s+/g," ");P.state=st.value;P.city=city;P.climate=(listed&&s.c[ct.value])||s.d;const al=w.querySelector("[data-salert]");P.seasonAlert=al?al.checked:false;answer("location",null,`${city}, ${st.value}`)};
  return w;
}

/* ---------- skin tone step: pick on the scale, or selfies (1, 3 or 5) read by the face reader ---------- */
const TONE_GROUPS=[["Light",[1,2,3]],["Medium",[4,5,6]],["Deep",[7,8,9,10]]];
const QUALITY_ONLY=r=>r.issues.filter(i=>!JUDGEMENT.has(i));
const PHOTO_TIPS=[
  "Face a window in daylight, no makeup or filters.",
  "Turn your face slightly to the left, still facing the window.",
  "Turn slightly to the right, and hold the phone a little further away.",
  "Try a different spot with daylight, such as another window or a balcony in shade.",
  "Pull hair back from your forehead and cheeks, and take one straight on.",
];
const CAM=SVG('<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>');
function swBtn(t,{size="",pressed=false,label=true,onClick}={}){const b=document.createElement("button");b.type="button";b.className="tsw "+size;b.style.background=MONK_HEX[t];b.style.color=t>=6?"#fff":"#2a1f1a";b.textContent=label?t:"";b.setAttribute("aria-label",`Tone ${t}, ${MONK_LABEL[t]}`);b.setAttribute("aria-pressed",String(pressed));if(onClick)b.onclick=onClick;return b}
function thumbOf(src){const c=document.createElement("canvas");const s=96/Math.max(src.width,src.height);c.width=Math.round(src.width*s);c.height=Math.round(src.height*s);c.getContext("2d").drawImage(src,0,0,c.width,c.height);return c}

function toneWidget(){
  const w=document.createElement("div");w.className="qbody";
  const area=document.createElement("div");area.className="tonearea";w.appendChild(area);
  area.addEventListener("pickscale",()=>choose());
  let reads=[],target=1,failures=0;      // reads: accepted photo readings (numbers + thumbnail only, in memory)

  const finish=(t,ut,label)=>{P.tone=t;P.undertone=ut||P.undertone||null;answer("tone",t,label)};

  /* 1. choose: scale or selfie */
  const choose=()=>{
    reads=[];target=1;failures=0;area.innerHTML="";
    const sc=document.createElement("div");sc.className="tonescale";
    for(const[g,ts]of TONE_GROUPS){const col=document.createElement("div");col.className="tgroup";col.innerHTML=`<span class="tglbl">${g}</span>`;
      const row=document.createElement("div");row.className="trow";
      for(const t of ts)row.appendChild(swBtn(t,{pressed:P.tone===t,onClick:()=>{P.toneSource="you picked";finish(t,null,`Tone ${t} (${MONK_LABEL[t]})`)}}));
      col.appendChild(row);sc.appendChild(col)}
    area.appendChild(sc);
    area.insertAdjacentHTML("beforeend",`<p class="qhelp" style="margin:0">Compare with your jawline in daylight. Most people pick one a little lighter than they are.</p>`);
    const a=document.createElement("div");a.className="qactions";
    const selfie=document.createElement("button");selfie.type="button";selfie.className="btn primary";selfie.innerHTML=`${CAM}Not sure? Take a selfie`;selfie.onclick=consent;
    a.append(selfie);area.appendChild(a);
  };

  /* 2. consent (E1) */
  const consent=()=>{
    area.innerHTML=`<div class="say consent"><p><b>May we use your photo?</b></p><p>We only need a photo to better understand your skin tone. With your permission, it will be stored in our system for reference for <b>18 months</b>, then deleted. You can ask us to delete it sooner at any time, and you can still correct the result.</p>
    <label class="agree"><input type="checkbox" data-agree> I agree to Aaina storing my photo for 18 months to understand my skin tone.</label></div>
    <div class="nofilter">${SVG('<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>')}<div><b>Please take your selfie without a filter.</b> Turn off beauty mode, filters and portrait effects, and skip makeup if you can. Filters change your skin's colour and texture, so the recommendations get less accurate.</div></div>`;
    const a=document.createElement("div");a.className="qactions";
    const yes=document.createElement("button");yes.type="button";yes.className="btn primary";yes.textContent="Continue to camera or upload";yes.disabled=true;yes.onclick=()=>{P.photoConsent={retention:"18 months",at:new Date().toISOString()};capture()};
    area.querySelector("[data-agree]").onchange=e=>{yes.disabled=!e.target.checked};
    const no=document.createElement("button");no.type="button";no.className="btn";no.textContent="No thanks, I'll pick my shade";no.onclick=choose;
    a.append(yes,no);area.appendChild(a);focusEl(area);
  };

  /* 3. capture one photo (first, or one of several) */
  const capture=()=>{
    area.innerHTML="";
    const n=reads.length+1,multi=target>1;
    if(multi){
      area.insertAdjacentHTML("beforeend",`<div class="mphead"><div><div class="eyebrow">Photo ${n} of ${target}</div><p class="mptip">${esc(PHOTO_TIPS[Math.min(n-1,PHOTO_TIPS.length-1)])}</p></div><div class="mpdots">${Array.from({length:target},(_,i)=>`<span class="${i<reads.length?"done":i===reads.length?"now":""}"></span>`).join("")}</div></div>`);
      area.appendChild(strip());
    }
    area.appendChild(photoCard((res,src)=>onPhoto(res,src),{multi,cta:multi?`Add photo ${n}`:"Check my skin tone"}));
    focusEl(area);
  };
  const strip=()=>{const s=document.createElement("div");s.className="mpstrip";
    reads.forEach((r,i)=>{const d=document.createElement("div");d.className="mpthumb";d.appendChild(r.thumb);d.insertAdjacentHTML("beforeend",`<span class="mpread" style="background:${MONK_HEX[r.tone]};color:${r.tone>=6?"#fff":"#2a1f1a"}">${r.tone}</span><span class="small muted">Photo ${i+1}</span>`);s.appendChild(d)});
    return s};

  /* 4. read a photo */
  const onPhoto=(res,src)=>{
    area.querySelector(".readout")?.remove();
    const q=QUALITY_ONLY(res);
    if(res.status==="RECAPTURE"&&(q.length||!res.lab)){            // photo quality problem: ask for a retake, it doesn't count
      failures++;
      const out=document.createElement("div");out.className="readout";
      const tips=uniq(q.length?q:res.issues).map(c=>TIPS[c]).filter(Boolean).slice(0,3);
      out.innerHTML=`<div class="notice"><b>Let's retake this one.</b> It isn't clear enough to read.<ul class="tips">${tips.map(t=>`<li>${esc(t)}</li>`).join("")}</ul><span class="small muted">This photo hasn't been counted or saved.</span></div>`;
      if(failures>=3){const a=document.createElement("div");a.className="qactions";const p=document.createElement("button");p.type="button";p.className="btn";p.textContent="I'll pick my tone instead";p.onclick=choose;a.appendChild(p);out.appendChild(a)}
      area.appendChild(out);focusEl(out);return;
    }
    failures=0;
    reads.push({lab:res.lab,tone:res.tone,second:res.second,ut:res.ut,conf:res.conf,issues:res.issues,thumb:thumbOf(src)});
    if(reads.length<target){capture();return}
    if(target===1)firstResult(res);else combinedResult();
  };

  /* 5a. first photo result: clear, or torn between two */
  const firstResult=res=>{
    const torn=res.issues.some(i=>JUDGEMENT.has(i));
    const out=document.createElement("div");out.className="readout";
    if(torn){
      const [a,b]=res.candidates.length>1?res.candidates:[res.tone,res.second].sort((x,y)=>x-y);
      out.innerHTML=`<div class="notice info"><b>I'm torn between tone ${a} and tone ${b}.</b> Lighting in a single photo can tip it either way.</div>`;
      const pick=document.createElement("div");pick.className="torn";
      for(const t of[a,b]){const card=document.createElement("button");card.type="button";card.className="torncard";card.innerHTML=`<span class="bigsw" style="background:${MONK_HEX[t]}"></span><b>Tone ${t}</b><span class="small muted">${MONK_LABEL[t]}</span>`;
        card.onclick=()=>{P.toneSource="you chose after a selfie";finish(t,res.ut,`Tone ${t} (${MONK_LABEL[t]})`)};pick.appendChild(card)}
      out.appendChild(pick);
      out.appendChild(morePhotos("Not sure which? Add more photos and I'll compare them for a steadier reading:"));
    } else {
      out.appendChild(resultCard(res.tone,res.ut,`Your skin tone looks like <b>${res.tone} on the 1–10 scale (${MONK_LABEL[res.tone]})</b> with ${/^[aeiou]/.test(res.ut)?"an":"a"} <b>${res.ut} undertone</b>, because ${esc(res.why)}.`,"From your selfie","selfie"));
      out.appendChild(morePhotos("Want extra certainty? Add a few more photos:",true));
    }
    area.appendChild(out);focusEl(out);
  };
  const morePhotos=(lead,quiet=false)=>{
    const box=document.createElement("div");box.className="more"+(quiet?" quiet":"");
    box.innerHTML=`<p class="small" style="margin:0 0 8px">${esc(lead)}</p>`;
    const g=document.createElement("div");g.className="opts";
    for(const[nn,label,sub]of[[3,"3 photos","More accurate · 2 more, about 30 seconds"],[5,"5 photos","Most accurate · 4 more, best for tricky lighting"]]){
      const b=document.createElement("button");b.type="button";b.className="opt";b.innerHTML=`<b>${CAM} ${label}</b><span>${sub}</span>`;
      b.onclick=()=>{target=nn;capture()};g.appendChild(b)}
    box.appendChild(g);return box;
  };

  /* 5b. combine several photos */
  const combinedResult=()=>{
    const labs=reads.map(r=>r.lab);const lab=[0,1,2].map(c=>median(labs.map(l=>l[c])));
    const T=estimateTone(lab),U=estimateUndertone(lab);
    const votes={};for(const r of reads)votes[r.tone]=(votes[r.tone]||0)+1;
    const ranked=Object.entries(votes).map(([t,n])=>[+t,n]).sort((a,b)=>b[1]-a[1]||Math.abs(a[0]-T.tone)-Math.abs(b[0]-T.tone));
    const n=reads.length,top=ranked[0];
    const agree=votes[T.tone]||0;
    const clear=T.amb<=FR.maxAmb||agree/n>=0.6;
    const final=clear?(agree/n>=0.6||!top?T.tone:top[0]):null;
    const utVotes={};for(const r of reads)utVotes[r.ut]=(utVotes[r.ut]||0)+1;
    const out=document.createElement("div");out.className="readout";
    out.appendChild(strip());
    out.appendChild(voteChart(votes,n,final));
    if(final){
      const k=votes[final]||0;
      out.appendChild(resultCard(final,U.ut,`Across your ${n} photos, your skin tone reads as <b>${final} on the 1–10 scale (${MONK_LABEL[final]})</b> with ${/^[aeiou]/.test(U.ut)?"an":"a"} <b>${U.ut} undertone</b>. ${k} of ${n} photos landed on tone ${final}${k<n?", and I combined the colour from all of them":""}.`,`Based on ${n} photos`,`${n} selfies`));
    } else {
      const [a,b]=ranked.length>1?[ranked[0][0],ranked[1][0]].sort((x,y)=>x-y):[T.tone,T.second].sort((x,y)=>x-y);
      out.insertAdjacentHTML("beforeend",`<div class="notice info"><b>Your photos are split between tone ${a} and tone ${b}.</b> You're right on the line, so either will work well. Tap the one closer to your jawline in daylight.</div>`);
      const pick=document.createElement("div");pick.className="torn";
      for(const t of[a,b]){const card=document.createElement("button");card.type="button";card.className="torncard";card.innerHTML=`<span class="bigsw" style="background:${MONK_HEX[t]}"></span><b>Tone ${t}</b><span class="small muted">${votes[t]||0} of ${n} photos</span>`;
        card.onclick=()=>{P.toneSource=`you chose after ${n} selfies`;finish(t,U.ut,`Tone ${t} (${MONK_LABEL[t]})`)};pick.appendChild(card)}
      out.appendChild(pick);
      if(target<5){const m=document.createElement("button");m.type="button";m.className="btn ghost";m.textContent="Add 2 more photos";m.onclick=()=>{target=5;capture()};out.appendChild(m)}
    }
    area.innerHTML="";area.appendChild(out);focusEl(out);
  };
  const voteChart=(votes,n,final)=>{
    const max=Math.max(...Object.values(votes));const tones=Object.keys(votes).map(Number);const lo=Math.max(1,Math.min(...tones)-1),hi=Math.min(10,Math.max(...tones)+1);
    const d=document.createElement("div");d.className="votes";d.setAttribute("role","img");d.setAttribute("aria-label",`Photo readings: ${Object.entries(votes).map(([t,c])=>`${c} at tone ${t}`).join(", ")}`);
    let h=`<div class="eyebrow">How your ${n} photos read</div><div class="vbars">`;
    for(let t=lo;t<=hi;t++){const c=votes[t]||0;h+=`<div class="vcol${t===final?" win":""}"><span class="vn">${c||""}</span><span class="vbar" style="height:${c?Math.round(8+56*c/max):3}px;background:${c?MONK_HEX[t]:"var(--line)"}"></span><span class="vt">${t}</span></div>`}
    d.innerHTML=h+"</div>";return d;
  };
  const resultCard=(tone,ut,text,eyebrow,src)=>{
    let cur=tone;const wrap=document.createElement("div");wrap.style.display="flex";wrap.style.flexDirection="column";wrap.style.gap="10px";
    wrap.innerHTML=`<div class="toneresult"><span class="bigsw" style="background:${MONK_HEX[tone]}"></span><div><div class="eyebrow">${esc(eyebrow)}</div><p style="margin:2px 0 0">${text}</p><p class="small muted" style="margin:4px 0 0">Not quite right? Tap a different tone. Your photos have not been saved.</p></div></div>`;
    const row=document.createElement("div");row.className="trow";
    for(let t=1;t<=10;t++)row.appendChild(swBtn(t,{size:"sm",pressed:t===tone,onClick:()=>{cur=t;row.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",String(+x.textContent===t)));wrap.querySelector(".bigsw").style.background=MONK_HEX[t]}}));
    wrap.appendChild(row);
    const a=document.createElement("div");a.className="qactions";const ok=document.createElement("button");ok.type="button";ok.className="btn primary";ok.textContent="Looks right, continue";
    ok.onclick=()=>{P.toneSource=cur===tone?src:`${src}, corrected by you`;finish(cur,ut,`Tone ${cur} (${MONK_LABEL[cur]})${cur===tone?`, from ${src==="selfie"?"my selfie":"my "+src}`:""}`)};
    a.appendChild(ok);wrap.appendChild(a);return wrap;
  };
  if(OPEN_SELFIE){OPEN_SELFIE=false;consent()}else choose();return w;
}

/* ---------- filter check: beauty mode smooths skin while the background stays sharp; colour filters push hue or saturation out of the range real skin sits in ---------- */
function detectFilter(src,oval){
  const sc=Math.min(1,320/src.width),W=Math.max(8,Math.round(src.width*sc)),H=Math.max(8,Math.round(src.height*sc));
  const c=document.createElement("canvas");c.width=W;c.height=H;const g=c.getContext("2d");g.drawImage(src,0,0,W,H);const d=g.getImageData(0,0,W,H).data;
  const L=new Float32Array(W*H);for(let i=0;i<W*H;i++)L[i]=0.299*d[i*4]+0.587*d[i*4+1]+0.114*d[i*4+2];
  const cx=oval.cx*W,cy=oval.cy*H,rx=oval.w*W/2,ry=oval.h*H/2;
  let tIn=0,nIn=0,tOut=0,nOut=0,sIn=0,vIn=0,hx=0,hy=0,sAll=0,nAll=0;
  for(let y=1;y<H-1;y++)for(let x=1;x<W-1;x++){const i=y*W+x;const e=((x-cx)/rx)**2+((y-cy)/ry)**2;
    const lap=Math.abs(4*L[i]-L[i-1]-L[i+1]-L[i-W]-L[i+W]);
    const r=d[i*4]/255,gg=d[i*4+1]/255,b=d[i*4+2]/255,mx=Math.max(r,gg,b),mn=Math.min(r,gg,b),sat=mx?(mx-mn)/mx:0;sAll+=sat;nAll++;
    if(e<0.45){tIn+=lap;nIn++;sIn+=sat;vIn+=mx;
      if(mx-mn>0.02){let h=mx===r?((gg-b)/(mx-mn))%6:mx===gg?(b-r)/(mx-mn)+2:(r-gg)/(mx-mn)+4;h*=Math.PI/3;hx+=Math.cos(h)*sat;hy+=Math.sin(h)*sat}}
    else if(e>1.3){tOut+=lap;nOut++}}
  const skinTex=tIn/Math.max(1,nIn),bgTex=tOut/Math.max(1,nOut),skinSat=sIn/Math.max(1,nIn),skinV=vIn/Math.max(1,nIn),allSat=sAll/Math.max(1,nAll);
  let hue=Math.atan2(hy,hx)*180/Math.PI;if(hue<0)hue+=360;
  const flags=[];
  if(nOut>200&&skinTex<1.2&&bgTex>2.4&&bgTex/Math.max(skinTex,0.1)>2.6)flags.push({k:"smooth",say:"Your skin looks airbrushed while the background is sharp, which is what beauty mode does."});
  if(allSat<0.06)flags.push({k:"mono",say:"It looks black-and-white or sepia."});
  else if(skinSat>0.62)flags.push({k:"sat",say:"The colours look boosted."});
  if(allSat>=0.06&&skinSat>0.12&&hue>60&&hue<320)flags.push({k:"tint",say:"There's a green, blue or purple colour cast that real skin doesn't have."});
  else if(skinSat>0.3&&hue>=320&&hue<352)flags.push({k:"pink",say:"There's a pink or rosy tint over the photo."});
  return{filtered:flags.length>0,flags,stats:{skinTex,bgTex,skinSat,skinV,allSat,hue}};
}
function photoCard(onResult,{multi=false,cta="Check my skin tone"}={}){
  const box=document.createElement("div");box.className="photo";
  box.innerHTML=`<div class="stage"><canvas width="900" height="1200"></canvas><div class="empty">${SVG('<circle cx="12" cy="9" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>').replace("<svg",'<svg class="ph"')}${multi?"<span>Take the next photo.</span>":"<b>Selfie without a filter, please.</b><span>Face a window in daylight. Turn off beauty mode and filters.</span>"}</div></div>
  <div class="sizer" hidden><label>Oval</label><input type="range" min="0.25" max="0.85" step="0.01" value="0.55" aria-label="Oval size"><span>Drag the oval onto your face</span></div>
  <div class="camwrap" hidden><video playsinline muted autoplay></video><div class="qactions"><button type="button" class="btn primary" data-snap>${CAM}Capture</button><button type="button" class="btn" data-camx>Cancel</button></div></div>
  <div class="qactions" data-src><button type="button" class="btn primary" data-cam>${CAM}<span data-cap>Open camera</span></button><label class="btn filebtn">${SVG('<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>')}<span>Upload a photo</span><input type="file" accept="image/*"></label><button type="button" class="btn primary" data-read hidden>${esc(cta)}</button></div>
  <div class="qactions" data-pickrow><button type="button" class="btn ghost picklink" data-pick>Pick my shade from the scale instead</button></div>
  <div class="fcheck" hidden></div>
`;
  const cv=box.querySelector("canvas"),ctx=cv.getContext("2d"),empty=box.querySelector(".empty"),sizer=box.querySelector(".sizer"),range=sizer.querySelector("input"),file=box.querySelector("input[type=file]"),go=box.querySelector("[data-read]"),stage=box.querySelector(".stage"),cap=box.querySelector("[data-cap]");
  const src=document.createElement("canvas");let has=false,oval={cx:0.5,cy:0.45,w:0.55,h:0.5},regions=null;
  const setSize=v=>{oval.w=v;oval.h=Math.min(0.95,v*1.25*(src.width/src.height||0.75))};
  function draw(){if(!has)return;cv.width=src.width;cv.height=src.height;ctx.drawImage(src,0,0);const W=cv.width,H=cv.height,fw=oval.w*W,fh=oval.h*H,cx=oval.cx*W,cy=oval.cy*H;
    ctx.fillStyle="rgba(10,6,9,.45)";ctx.beginPath();ctx.rect(0,0,W,H);ctx.ellipse(cx,cy,fw/2,fh/2,0,0,Math.PI*2);ctx.fill("evenodd");ctx.lineWidth=Math.max(2,W/300);ctx.strokeStyle="#fff";ctx.setLineDash([W/60,W/90]);ctx.beginPath();ctx.ellipse(cx,cy,fw/2,fh/2,0,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);
    if(regions)for(const r of regions){ctx.strokeStyle=r.lab&&r.frac>=FR.minSkin?"#7CFFB2":"#FF8A8A";ctx.lineWidth=Math.max(2,W/350);ctx.strokeRect(...r.box)}}
  let isDemo=false,override=false;const fcheck=box.querySelector(".fcheck");
  const ready=()=>{has=true;box.classList.add("has");regions=null;override=false;fcheck.hidden=true;empty.hidden=true;sizer.hidden=false;go.hidden=false;go.disabled=false;cap.textContent="Retake";cap.parentElement.className="btn";draw()};
  /* live camera, when the browser allows it here; otherwise upload (which offers the camera on phones) */
  const camwrap=box.querySelector(".camwrap"),video=camwrap.querySelector("video"),srcRow=box.querySelector("[data-src]");let stream=null;
  const stopCam=()=>{if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;camwrap.hidden=true;srcRow.hidden=false;stage.hidden=false};
  box.querySelector("[data-cam]").onclick=async()=>{
    if(!navigator.mediaDevices?.getUserMedia){showCamErr();return}
    try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"user",width:{ideal:1280}},audio:false});video.srcObject=stream;camwrap.hidden=false;srcRow.hidden=true;stage.hidden=true;empty.hidden=true;focusEl(camwrap)}
    catch(e){showCamErr(e&&e.name)}};
  const showCamErr=n=>{empty.hidden=false;has=false;box.classList.remove("has");empty.innerHTML=`<b>The camera didn't open.</b><br>${n==="NotAllowedError"?"Camera access was blocked. Allow the camera for this page, or ":""}Use <b>Upload a photo</b> instead. On a phone it also lets you take a new selfie.`};
  box.querySelector("[data-snap]").onclick=()=>{if(!video.videoWidth)return;const c=document.createElement("canvas");c.width=video.videoWidth;c.height=video.videoHeight;c.getContext("2d").drawImage(video,0,0);stopCam();isDemo=false;load(c)};
  box.querySelector("[data-camx]").onclick=()=>{stopCam();if(!has)empty.hidden=false};
  function load(img){const s=Math.min(1,1200/Math.max(img.width,img.height));src.width=Math.round(img.width*s);src.height=Math.round(img.height*s);src.getContext("2d").drawImage(img,0,0,src.width,src.height);stage.style.aspectRatio=`${src.width}/${src.height}`;oval.cx=0.5;oval.cy=0.45;setSize(+range.value);ready()}
  file.onchange=e=>{const f=e.target.files&&e.target.files[0];if(!f)return;isDemo=false;const url=URL.createObjectURL(f),img=new Image();img.onload=()=>{load(img);URL.revokeObjectURL(url)};img.onerror=()=>{empty.hidden=false;empty.textContent="That file couldn't be opened as a photo. Try again.";URL.revokeObjectURL(url)};img.src=url;e.target.value=""};
  range.oninput=()=>{setSize(+range.value);regions=null;draw()};
  let drag=null;cv.onpointerdown=e=>{if(!has)return;const r=cv.getBoundingClientRect();drag={x:e.clientX,y:e.clientY,cx:oval.cx,cy:oval.cy,w:r.width,h:r.height};cv.setPointerCapture(e.pointerId)};
  cv.onpointermove=e=>{if(!drag)return;oval.cx=Math.min(0.95,Math.max(0.05,drag.cx+(e.clientX-drag.x)/drag.w));oval.cy=Math.min(0.95,Math.max(0.05,drag.cy+(e.clientY-drag.y)/drag.h));regions=null;draw()};
  cv.onpointerup=cv.onpointercancel=()=>drag=null;
  box.querySelector("[data-pick]").onclick=()=>{stopCam();box.dispatchEvent(new CustomEvent("pickscale",{bubbles:true}))};
  go.onclick=()=>{
    if(!isDemo&&!override){const f=detectFilter(src,oval);
      if(f.filtered){box.parentElement.querySelector(".readout")?.remove();fcheck.hidden=false;fcheck.className="fcheck warn";
        fcheck.innerHTML=`<b>This photo looks filtered.</b> ${esc(f.flags.map(x=>x.say).join(" "))} Filters change how your skin looks, so the tone I read would be off.<div class="qactions"><button type="button" class="btn primary" data-re>${CAM}Retake without a filter</button><button type="button" class="btn" data-ok>There's no filter, continue</button></div>`;
        fcheck.querySelector("[data-re]").onclick=()=>{fcheck.hidden=true;box.querySelector("[data-cam]").click()};
        fcheck.querySelector("[data-ok]").onclick=()=>{override=true;P.toneFilterDoubt=true;fcheck.hidden=true;go.click()};
        focusEl(fcheck);return}
      fcheck.hidden=false;fcheck.className="fcheck ok";fcheck.innerHTML=`${SVG('<path d="M5 12l4 4 10-10"/>')}No filter detected. Good to go.`}
    const res=readPhoto(src,oval);regions=res.regions;draw();onResult(res,src)};
  return box;
}

/* ---------- building the 3-product plan ---------- */
const hay=p=>p.n+" "+(p.a||"")+" "+(p.i||"");
function slotScore(p,slot){
  let s=score(p,P);
  if(slot.con&&p.con.includes(slot.con))s+=4;
  for(const c of P.concerns)if(c!==PROB&&p.con.includes(c))s+=1;
  for(const[re,w]of[...(slot.boost||[]),...(PREF.boost||[])])if(re.test(hay(p)))s+=w;
  if(p.c==="Sunscreen"&&PREF.spf)s+=(p.spf||0)>=PREF.spf?2.5:-2.5;
  if(p.c==="Sunscreen"&&(p.spf||0)<30)s-=3;
  const deep=P.tone>=7,medium=P.tone>=4&&P.tone<=6;
  if(deep&&p.c==="Sunscreen"){if(/invisible|aqua|hybrid/i.test(p.n))s+=2.5;if(/mineral/i.test(p.n))s-=2.5}
  if(medium&&p.c==="Sunscreen"&&/invisible|aqua/i.test(p.n))s+=1;
  if((deep||medium)&&["acne","pigmentation","dullness","tanning"].includes(PROB)){if(/niacinamide|azelaic|tranexamic|arbutin|licorice/i.test(hay(p)))s+=deep?1.5:0.8;if(p.glyPct>=10||(p.bha&&p.leaveOn&&p.salPct>=2))s-=deep?2.5:1}
  if((PREF.gentle||P.sensitive)&&(p.glyPct>=7||p.salPct>=2||p.retPct>=0.5))s-=4;
  if(PREF.noStrongRet&&p.retPct>=0.5)s-=4;
  if(P.noClog&&p.com==="medium")s-=1;
  if(PREF.escalate&&isActive(p))s-=5;
  const strong=p.ret||p.aha||(p.bha&&p.leaveOn);
  const exSlot=/exfoliat/i.test(slot.role);
  if(strong&&!exSlot){
    const inci=p.i||"";const strongNames=[p.ret&&"retinol",p.aha&&(/glycolic/i.test(inci)?"glycolic":"")||"",p.aha&&(/lactic acid/i.test(inci)?"lactic":"")||"",p.bha&&p.leaveOn&&"salicylic"].filter(Boolean);
    const ok=RELEVANT[PROB]&&strongNames.every(n=>RELEVANT[PROB].test(n));
    if(!ok)s-=6;                                   // strong active that doesn't serve this problem
    if(!slot.primary&&p.c!=="Cleanser")s-=4;        // keep supporting steps simple
  }
  if(p.aha&&p.c==="Cleanser"&&!["dullness","tanning"].includes(PROB))s-=2;
  if(!exSlot&&HARSH_NAME.test(p.n)&&["dehydration","redness","fine lines","dark circles"].includes(PROB))s-=4;
  if((PROB==="redness"||P.sensitive)&&(p.aha||p.ret||(p.bha&&p.leaveOn)))s-=6;
  s+=seasonBoost(p);
  if(SHELF_ACTS.size&&actives(p).some(a=>SHELF_ACTS.has(a.name.toLowerCase())))s-=5;   // don't double up on what they already use
  return s;
}
function rankSlot(slot,ctx){
  return CAT.filter(p=>slot.cats.includes(p.c)&&check(p).ok&&!p.sp&&!ctx.used.has(p.id)&&!clash(p,ctx)&&!(P.excluded||[]).includes(p.id)&&!(P.shelf||[]).some(x=>x.id===p.id))
    .map(p=>({p,s:slotScore(p,slot)})).sort((a,b)=>b.s-a.s||(a.p.p||0)-(b.p.p||0)||a.p.id.localeCompare(b.p.id)).map(x=>x.p);
}
function clash(p,ctx){return (ctx.ret&&(p.aha||p.bha||p.ret)&&p.c!=="Sunscreen")||((ctx.acid)&&p.ret)||(ctx.bp&&p.ret)}
function buildPlan(silent){
  lockAll();progress();
  const def=PROBLEMS[PROB].plan;
  const order=[...def.keys()].sort((a,b)=>(def[b].primary?1:0)-(def[a].primary?1:0));
  const shelf=shelfItems(),safe=shelf.filter(o=>o.safe);SHELF_ACTS=new Set(safe.flatMap(o=>o.acts));
  const ctx={used:new Set(),ret:safe.some(o=>o.ret),acid:safe.some(o=>o.acid),bp:safe.some(o=>o.bp)};const slots=[];const kept=new Set();
  const want=RESTORE_IDS;RESTORE_IDS=null;
  for(const i of order){const slot=def[i];const list=rankSlot(slot,ctx);
    const own=safe.find(o=>!kept.has(o.key)&&slot.cats.includes(o.cat)&&(!slot.primary||o.con.includes(PROB)));
    if(own&&(!want||want[i]==="keep")){kept.add(own.key);slots[i]={slot,list,idx:0,p:null,keep:own};continue}
    let p=list[0]||null;if(want&&want[i]&&want[i]!=="keep"){const j=list.findIndex(x=>x.id===want[i]);if(j>=0)p=list[j]}
    slots[i]={slot,list,idx:Math.max(0,list.indexOf(p)),p};if(p){ctx.used.add(p.id);if(p.ret)ctx.ret=true;if((p.aha||p.bha)&&p.c!=="Cleanser")ctx.acid=true}}
  PL={slots,ctx,shelf};
  if(!META.planAt||META.planProb!==PROB){META.planAt=Date.now();META.planProb=PROB;META.checks=[]}
  META.planSeason=seasonFor()?.key||null;
  if(!silent)renderPlan();
}
function removedFor(cats){const c={};let n=0;for(const p of CAT)if(cats.includes(p.c)){n++;for(const[b]of check(p).blocks)c[b]=(c[b]||0)+1}return{c,n}}
const SAY_BLOCK={B1:"contain fragrance or essential oils",B2:"contain essential oils",B3:"contain an ingredient you've reacted to",B4:"have no ingredient list, so I couldn't check them",A2:"contain retinoids or strong salicylic acid",B6:"don't suit your skin type or could clog pores",B7:"contain drying alcohol, which is harsh on dry skin in this weather",C5:"are over your budget"};

function cardHTML(i,s){
  const p=s.p,role=s.slot.role;
  if(s.keep)return`<article class="pcard keep"><div class="phead"><span class="stepn">${i+1}</span><div class="role">${esc(role)} <span class="when">· ${esc(s.slot.when)}</span></div><span class="ownbadge">Already yours</span></div>
    <div class="ptop"><div class="thumb">${IC[CAT_IC[s.keep.cat]||"dropper"]}</div><div style="min-width:0"><div class="brand">Keep using</div><div class="nm">${esc(s.keep.p?s.keep.p.n:cap(s.keep.name.replace(/^your /,"Your ")))}</div><div class="cat">${esc(s.keep.cat)}</div></div></div>
    <p class="why1">${s.keep.p?"It's already on your shelf and it passes all your checks":"You already have this step covered"}, so there's <b>no need to buy another</b>.${s.list[0]?` That saves you about <b>${rupee(s.list[0].p)}</b>.`:""}</p>
    <div class="pfoot"><span class="small muted">From your routine</span>${s.list.length?`<button type="button" class="btn ghost newone" data-i="${i}">Suggest a new one</button>`:""}</div></article>`;
  if(!p)return`<article class="pcard empty"><span class="stepn">${i+1}</span><div><div class="role">${esc(role)}</div><p class="muted small">No product in our range passes all your checks for this step${P.budget?" within budget":""}. I've left it out rather than bend a safety rule.</p></div></article>`;
  const act=actives(p);
  return`<article class="pcard">
    <div class="phead"><span class="stepn">${i+1}</span><div class="role">${esc(role)} <span class="when">· ${esc(s.slot.when)}</span></div><div class="price">${rupee(p.p)}</div></div>
    <div class="ptop"><div class="thumb">${IC[CAT_IC[p.c]||"dropper"]}</div><div style="min-width:0"><div class="brand">${esc(p.b)}</div><div class="nm">${esc(p.n.replace(p.b+" ",""))}</div><div class="cat">${esc(p.c)}</div></div></div>
    ${act.length?`<div class="keyact">${act.map(a=>`<span>${esc(a.name)}</span>`).join("")}${p.spf?`<span>SPF ${p.spf}${p.pa?" "+esc(p.pa):""}</span>`:""}</div>`:p.spf?`<div class="keyact"><span>SPF ${p.spf}${p.pa?" "+esc(p.pa):""}</span></div>`:""}
    <p class="why1">${lineHTML(p,s.slot)}</p>
    <div class="pfoot"><span class="small muted">${esc(p.sz||"")} · check availability</span>${s.list.length>1?`<button type="button" class="btn ghost swap" data-i="${i}">Show another</button>`:""}</div>
  </article>`;
}
function lineHTML(p,slot){let h=esc(oneLine(p,slot));const a=actives(p)[0];
  if(a)h=h.replace(esc(a.name),`<b>${esc(a.name)}</b>`);h=h.replace(/(SPF \d+)/,"<b>$1</b>");return h}
function oneLine(p,slot){
  const a=actives(p)[0];const prob=PROBLEMS[PROB].label.toLowerCase();
  if(p.c==="Sunscreen")return`Daily SPF ${p.spf||""} so your ${PROB==="pigmentation"||PROB==="tanning"?"spots and tan don't come back":"skin stays protected"}${humid()&&/matte|invisible|aqua/i.test(p.n)?", light enough for humid weather":""}.`;
  if(a)return`${a.name} ${a.does}.`;
  return`Chosen for ${prob} and your ${P.skin||""} skin.`;
}
function spReasonHTML(p){
  const slot=PL.slots.find(s=>s.slot.cats.includes(p.c))?.slot;
  const helps=(p.con||[]).filter(c=>P.concerns.includes(c)).map(c=>PROBLEMS[c]?.label.toLowerCase()).filter(Boolean);
  const fits=[P.skin&&`${cap(P.skin)} skin`,P.avoidFrag&&"Fragrance-free",P.avoidEO&&"No essential oils",P.sensitive&&"Gentle",P.budget&&`Under ${rupee(P.budget)}`].filter(Boolean);
  return `<ul class="spwhy"><li><span>Why</span><div>${lineHTML(p,slot)}</div></li>${helps.length?`<li><span>Helps with</span><div>${helps.map(h=>`<b>${esc(h)}</b>`).join(" and ")}</div></li>`:""}<li><span>Use it</span><div>In place of your plan's <b>${esc(p.c.toLowerCase())}</b> step.</div></li></ul>${fits.length?`<div class="spfit">${fits.map(f=>`<span>${SVG('<path d="M5 12l4 4 10-10"/>')}${esc(f)}</span>`).join("")}</div>`:""}`;
}
function spReason(p){
  const slot=PL.slots.find(s=>s.slot.cats.includes(p.c))?.slot;const prob=PROBLEMS[PROB].label.toLowerCase();
  const fits=[P.skin&&`${P.skin} skin`,P.avoidFrag&&"fragrance-free",P.sensitive&&"gentle enough for sensitive skin",P.budget&&`under your ${rupee(P.budget)} budget`].filter(Boolean);
  const helps=(p.con||[]).filter(c=>P.concerns.includes(c)).map(c=>PROBLEMS[c]?.label.toLowerCase()).filter(Boolean);
  return `${oneLine(p,slot)} ${helps.length?`It also targets ${helps.join(" and ")}`:`A good ${p.c.toLowerCase()} option for ${prob}`}${fits.length?`, and suits your answers: ${fits.join(", ")}`:""}. You could use it in place of your plan's ${p.c.toLowerCase()} step.`.replace(/\s+/g," ");
}
function renderPlan(){
  thread.querySelectorAll(".plan").forEach(r=>r.classList.add("old"));
  const box=document.createElement("div");box.className="plan";
  const total=PL.slots.reduce((t,s)=>t+(s.p?.p||0),0);const keptN=PL.slots.filter(s=>s.keep).length;
  const prob=PROBLEMS[PROB];
  const applied=[P.avoidFrag&&"Fragrance-free",P.avoidEO&&"No essential oils",P.noClog&&"Won't clog pores",P.reactions.length&&"No "+P.reactions.join(", "),P.pregnancy!==false&&"Pregnancy-safe",P.skin&&cap(P.skin)+" skin",P.city&&`${P.city} climate`,P.budget&&`Each under ${rupee(P.budget)}`].filter(Boolean);
  let h=`<div class="phero"><div class="eyebrow">${NAME?`${esc(NAME)}, your plan is ready`:"Your plan is ready"}</div><h3>Three steps for ${esc(prob.label.toLowerCase())}</h3><p class="lead">${SUB?`Made for what you described: ${esc(SUB.toLowerCase())}. `:""}Each product has one clear job, and together they take just a few minutes a day.</p>
    <div class="applied">${applied.map(x=>`<span class="chip ok">✓ ${esc(x)}</span>`).join("")}</div></div>
    <div class="pcards">${PL.slots.map((s,i)=>cardHTML(i,s)).join("")}</div>
    <div class="total"><span>${keptN?`Total for ${3-keptN===1?"the new product":`the ${3-keptN} new products`}`:"Total for all three"}${keptN?`<small>You're keeping ${keptN} from your routine</small>`:""}</span><b>${rupee(total)}</b></div>${shareBarHTML()}${shelfPlanNote()}`;
  // sponsored alternative (same checks, labelled, separate)
  const sp=CAT.filter(p=>p.sp&&PL.slots.some(s=>s.slot.cats.includes(p.c))&&check(p).ok&&!PL.ctx.used.has(p.id)&&!clash(p,PL.ctx))
    .map(p=>({p,s:slotScore(p,PL.slots.find(s=>s.slot.cats.includes(p.c)).slot)})).sort((a,b)=>b.s-a.s);
  const spPick=[];for(const x of sp){if(spPick.length>=2)break;if(!spPick.some(y=>y.p.c===x.p.c))spPick.push(x)}
  for(const x of sp){if(spPick.length>=2)break;if(!spPick.includes(x))spPick.push(x)}
  if(spPick.length)h+=`<div class="spwrap"><h4 class="sphead">You might also like</h4>${spPick.map(({p})=>`<div class="spalt"><div class="sptop"><span class="spl">Sponsored</span><b>${esc(p.n)}</b><span class="small muted">${esc(p.c)} · ${rupee(p.p)}</span></div>${spReasonHTML(p)}</div>`).join("")}</div>`;
  h+=explainHTML();
  h+=`<div class="sendoff"><span class="tagline-end">Reflect · Reveal · Radiate</span><h4>You've got this${nm(", ")}</h4><p>Start with one product at a time, a few days apart, so you know how your skin feels with each. Give the plan ${PROB==="dehydration"||PROB==="dullness"?"two to four":"six to eight"} weeks before judging it, and take a quick photo in the same light every couple of weeks. Small changes are easy to miss day to day.</p></div>`;
  box.innerHTML=h;
  const nx=document.createElement("div");nx.className="next";
  const add=(label,fn,primary)=>{const b=document.createElement("button");b.type="button";b.className="btn"+(primary?" primary":"");b.textContent=label;b.onclick=fn;nx.appendChild(b)};
  add("Plan for another concern",()=>{meSay("Plan for another concern");DONE.delete("problem");DONE.delete("follow");DONE.delete("extra");PROB=null;botSay(`Of course${nm(", ")}. I'll keep your safety, location and skin answers, so this one is quicker.`);next()},true);
  add("How's it going? Check in",()=>openCheckin());
  add("Check a product",()=>{$("askInput").focus();$("askInput").placeholder="Type a product name or code, e.g. P1025"});
  box.appendChild(nx);
  box.querySelectorAll(".swap").forEach(b=>b.onclick=()=>swap(+b.dataset.i));wireShare(box);
  box.querySelectorAll(".newone").forEach(b=>b.onclick=()=>{const s=PL.slots[+b.dataset.i];const p=s.list.find(x=>!PL.ctx.used.has(x.id)&&!clash(x,PL.ctx));if(!p)return;s.keep=null;s.p=p;s.idx=s.list.indexOf(p);PL.ctx.used.add(p.id);renderPlan();saveState()});
  newBlock("plan").appendChild(box);stepNow=null;renderSide();saveState();requestAnimationFrame(()=>box.scrollIntoView({block:"start",behavior:"smooth"}));
}
function shelfPlanNote(){
  const sh=PL.shelf||[];if(!sh.length)return"";
  const warn=sh.filter(o=>!o.safe),combos=[];const safe=sh.filter(o=>o.safe);
  const all=[...safe,...PL.slots.filter(s=>s.p).map(s=>({ret:!!s.p.ret,acid:!!((s.p.aha||s.p.bha)&&s.p.c!=="Cleanser"),bp:/benzoyl/i.test(hay(s.p)),short:s.p.n}))];
  if(all.some(o=>o.ret)&&all.some(o=>o.acid))combos.push("Use your <b>retinoid and exfoliating acid on different nights</b>, never together.");
  if(all.some(o=>o.ret)&&all.some(o=>o.bp))combos.push("Use <b>benzoyl peroxide in the morning</b> and your <b>retinoid at night</b>, as they can cancel each other out.");
  const picked=new Set(PL.slots.filter(s=>s.p).flatMap(s=>actives(s.p).map(a=>a.name.toLowerCase())));
  const avoided=uniq(safe.flatMap(o=>o.acts)).filter(a=>!picked.has(a)),doubled=uniq(safe.flatMap(o=>o.acts)).filter(a=>picked.has(a));
  return`<div class="shelfnote"><h4>Works with what you already use</h4><ul>
    ${PL.slots.filter(s=>s.keep).map(s=>`<li>${SVG('<path d="M5 12l4 4 10-10"/>')}<span>Keeping <b>${esc(s.keep.p?s.keep.p.n:s.keep.name)}</b> for your <b>${esc(s.slot.role.toLowerCase())}</b> step.</span></li>`).join("")}
    ${avoided.length?`<li>${SVG('<path d="M5 12l4 4 10-10"/>')}<span>No new product doubles up on <b>${esc(avoided.map(a=>a.replace(/ \(.*\)/,"")).join(", "))}</b>, since you already use ${avoided.length>1?"them":"it"}.</span></li>`:""}
    ${doubled.length?`<li class="tip">${SVG('<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/>')}<span>Your new picks also contain <b>${esc(doubled.map(a=>a.replace(/ \(.*\)/,"")).join(", "))}</b>, which you already use. That's gentle and fine to layer, but you don't need extra.</span></li>`:""}
    ${PL.ctx.ret||PL.ctx.acid||PL.ctx.bp?`<li>${SVG('<path d="M5 12l4 4 10-10"/>')}<span>Nothing new <b>clashes</b> with your ${esc(safe.filter(o=>o.ret||o.acid||o.bp).map(o=>o.short.toLowerCase()).join(" or ")||"routine")}.</span></li>`:""}
    ${combos.map(c=>`<li class="tip">${SVG('<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/>')}<span>${c}</span></li>`).join("")}
    ${warn.map(o=>`<li class="warn">${SVG('<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/>')}<span>Consider pausing <b>${esc(o.p?o.p.n:o.name)}</b>: ${esc(o.warn.join("; "))}.</span></li>`).join("")}
  </ul></div>`;
}
function swap(i){
  const s=PL.slots[i];PL.ctx.used.delete(s.p.id);
  s.idx=(s.idx+1)%s.list.length;let tries=0;
  while(tries<s.list.length&&(PL.ctx.used.has(s.list[s.idx].id)||clash(s.list[s.idx],{ret:PL.slots.some((x,j)=>j!==i&&x.p?.ret),acid:PL.slots.some((x,j)=>j!==i&&x.p&&(x.p.aha||x.p.bha)&&x.p.c!=="Cleanser")}))){s.idx=(s.idx+1)%s.list.length;tries++}
  s.p=s.list[s.idx];PL.ctx.used.add(s.p.id);
  meSay(`Show another ${s.slot.role.toLowerCase()} option`);renderPlan();
}

/* ---------- the "why" explanation ---------- */
function told(){
  const prob=PROBLEMS[PROB];const r=[["Main concern",esc(prob.label)+(SUB?`<small>${esc(SUB)}</small>`:"")]];
  const also=P.concerns.filter(c=>c!==PROB);if(also.length)r.push(["Also helping with",also.map(c=>esc(PROBLEMS[c].label)).join(", ")]);
  if(P.skin)r.push(["Skin type",esc(cap(P.skin))]);
  if(P.tone)r.push(["Skin tone",`${P.tone} of 10<small>${esc(cap(MONK_LABEL[P.tone]))}</small>`]);
  if(P.city){const se=seasonFor();r.push(["Where you live",`${esc(P.city)}<small>Mostly ${esc(CLIMATE_SAY[P.climate])}${se?` · ${esc(cap(se.say.replace(/^the /,"")))} now`:""}</small>`])}
  const avoid=[P.avoidFrag&&"Fragrance",P.avoidEO&&"Essential oils",P.noClog&&"Pore-clogging formulas",...P.reactions.map(cap)].filter(Boolean);
  if(avoid.length)r.push(["Avoiding",esc(avoid.join(", "))]);
  r.push(["Pregnancy-cautious",P.pregnancy===false?"No":"Yes"]);
  if(P.budget!==undefined)r.push(["Budget",P.budget?`Under ${rupee(P.budget)} each`:"No limit"]);
  return r;
}
function explainHTML(){
  const prob=PROBLEMS[PROB];const cats=uniq(PL.slots.flatMap(s=>s.slot.cats));const R=removedFor(cats);
  const you=[`your main concern is <b>${esc(prob.label.toLowerCase())}</b>${SUB?` ("${esc(SUB)}")`:""}`];
  const also=P.concerns.filter(c=>c!==PROB);if(also.length)you.push(`you'd also like help with ${also.map(c=>esc(PROBLEMS[c].label.toLowerCase())).join(" and ")}`);
  if(P.skin)you.push(`you have <b>${P.skin}</b> skin`);
  if(P.tone)you.push(`your skin tone is ${P.tone} on the 1–10 scale (${MONK_LABEL[P.tone]})`);
  if(P.city)you.push(`you live in ${esc(P.city)}, where it's mostly ${CLIMATE_SAY[P.climate]}${dryWinter()?" and currently dry and cold":""}`);
  const avoid=[P.avoidFrag&&"fragrance",P.avoidEO&&"essential oils",P.noClog&&"pore-clogging formulas",...P.reactions].filter(Boolean);
  if(avoid.length)you.push(`you want to avoid ${esc(avoid.join(", "))}`);
  if(P.pregnancy!==false)you.push("you'd like me to be pregnancy-cautious");
  let h=`<section class="explain" aria-label="Why these products"><div class="eyebrow">Why I recommended these</div><h3>How this plan fits you</h3>
    <p class="exlede">${NAME?`${esc(NAME)}, here's`:"Here's"} what you told me, and what I did with it.</p>
    <div class="told">${told().map(([k,v])=>`<div><span>${esc(k)}</span><b>${v}</b></div>`).join("")}</div>
    <p class="exlede">So I built a <b>three-step plan</b> where each product has one clear job: ${PL.slots.filter(s=>s.p).map(s=>`<b>${esc(s.slot.role.toLowerCase())}</b>`).join(", then ")}.</p>`;
  PL.slots.forEach((s,i)=>{if(!s.p)return;const p=s.p,act=actives(p);
    const fit=[];
    if(P.skin&&p.st.includes(P.skin))fit.push(`made for ${P.skin} skin${p.st.length<4?" specifically":""}`);
    if(humid()&&(p.fin==="matte"||/gel|oil-free|matte|invisible|aqua/i.test(p.n)))fit.push("a lightweight texture that won't feel heavy in humid weather");
    if((P.skin==="dry"||dryWinter())&&/ceramide|butyrospermum|squalane/i.test(p.i||""))fit.push("barrier-supporting ingredients for dry or wintry conditions");
    if((P.skin==="oily"||PROB==="acne")&&p.com==="low")fit.push("low risk of clogging pores");
    if(P.tone>=7&&p.c==="Sunscreen"&&/invisible|aqua|hybrid/i.test(p.n))fit.push("a sheer texture that won't leave a white cast on deeper skin");
    else if(P.tone>=7&&/niacinamide|azelaic|tranexamic|arbutin|licorice/i.test(hay(p))&&["acne","pigmentation","dullness","tanning"].includes(PROB))fit.push("a gentle way to even tone on deeper skin, which can darken after irritation");
    {const se=seasonFor();if(se&&seasonBoost(p)>0)fit.push(`a texture that suits ${se.label.toLowerCase()} in ${P.city}`)}
    const hit=p.con.filter(c=>P.concerns.includes(c)&&c!==PROB);if(hit.length)fit.push(`also targets ${hit.map(c=>PROBLEMS[c]?.label.toLowerCase()||c).join(" and ")}`);
    if(SUB&&(PREF.boost||[]).some(([re,w])=>w>0&&re.test(hay(p))))fit.push(`matches what you described ("${SUB}")`);
    const safe=[P.avoidFrag&&"no fragrance, including hidden fragrance ingredients",P.avoidEO&&"no essential oils",...P.reactions.map(r=>`no ${r}`),P.pregnancy!==false&&(p.ret||p.salPct>=2?null:"no retinoids or strong salicylic acid"),P.budget&&`under your ${rupee(P.budget)} budget`].filter(Boolean);
    const use=[s.slot.when];
    if(p.aha||p.bha&&p.leaveOn||p.ret)use.push("start 2–3 nights a week and build up");
    if(p.c==="Sunscreen")use.push("use two finger-lengths for face and neck, and reapply every 2–3 hours outdoors");
    if(p.c==="Cleanser")use.push("massage for 30 seconds, then rinse with lukewarm water");
    if(isActive(p)||P.sensitive)use.push("patch-test on your jaw for 2–3 days first, and stop if it stings or burns");
    h+=`<div class="ex"><div class="exh"><span class="stepn">${i+1}</span><div><div class="role">${esc(s.slot.role)}</div><b>${esc(p.n)}</b></div></div>
      <dl>
        <dt>What it does for you</dt><dd>${act.length?act.map(a=>`<b>${esc(a.name)}</b> ${esc(a.does)}.`).join(" "):p.c==="Sunscreen"?"":"A simple, well-matched formula for this step."}${p.c==="Sunscreen"?` SPF ${p.spf} protects against burning and tanning${p.pa?`, and ${esc(p.pa)} against the deeper UVA rays that cause dark spots`:""}. Without daily sunscreen, ${PROB==="pigmentation"||PROB==="tanning"?"spots and tan keep coming back however good the rest of the routine is":"treatments work less well and skin ages faster"}.`:""}</dd>
        ${fit.length?`<dt>Why it suits you</dt><dd><ul class="ddl">${fit.map(f=>`<li>${esc(cap(f))}</li>`).join("")}</ul></dd>`:""}
        ${safe.length?`<dt>Safety checks it passed</dt><dd><div class="spfit">${safe.map(f=>`<span>${SVG('<path d="M5 12l4 4 10-10"/>')}${esc(cap(f))}</span>`).join("")}</div></dd>`:""}
        <dt>How to use it</dt><dd><ul class="ddl">${use.map((u,k)=>`<li>${k===0?`<b>${esc(cap(u))}</b>`:esc(cap(u))}</li>`).join("")}</ul></dd>
      </dl></div>`});
  const removed=Object.entries(R.c);
  h+=`<div class="exsum"><div><h4>What I ruled out</h4><p>I looked at ${R.n} products across ${cats.map(c=>c.toLowerCase()).join(", ")}.${removed.length?" I removed every one that clashes with your answers:":" Every one passed your checks, so I ranked them all."}</p>${removed.length?`<ul>${removed.map(([k,v])=>`<li>${v} ${SAY_BLOCK[k]||k}</li>`).join("")}</ul>`:""}<p class="small muted">The rest were ranked on how well they match your concern, skin type and climate. Sponsorship plays no part in this ranking.</p></div>
    <div><h4>What to expect</h4><p>${esc(prob.expect)} Results vary from person to person.</p>${PL.ctx.ret?`<p class="small">I haven't paired your retinol with any exfoliating acid, so they won't irritate together.</p>`:""}<p class="small muted">If your skin becomes painful, swollen, or spreads, stop and see a dermatologist.</p></div></div>
  </section>`;
  return h;
}

/* ---------- side panel ---------- */
const SHORT={shelf:"Routine",problem:"Concern",follow:"Details",extra:"Also",avoid:"Avoid",react:"Reactions",preg:"Pregnancy",location:"Location",skin:"Skin type",tone:"Skin tone",budget:"Budget"};
function renderSide(){
  const j=$("journey");if(!j)return;j.innerHTML="";
  const ol=document.createElement("ol");
  STEPS.forEach((k,i)=>{const done=DONE.has(k),now=k===stepNow;const li=document.createElement("li");li.className="jn"+(done?" done":"")+(now?" now":"");
    const b=document.createElement("button");b.type="button";b.disabled=!done;b.title=done?`Change: ${STEP[k].show()}`:SHORT[k];
    b.innerHTML=`<span class="jc">${done?'<svg viewBox="0 0 16 16"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>':"Q"+(i+1)}</span><span class="jl">${esc(SHORT[k])}</span>`;
    b.setAttribute("aria-label",`Q${i+1} ${SHORT[k]}${done?", done, tap to change":now?", current question":""}`);
    if(done)b.onclick=()=>editStep(k);li.appendChild(b);ol.appendChild(li)});
  const fin=document.createElement("li");fin.className="jn final"+(STEPS.every(k=>DONE.has(k))?" done now":"");fin.innerHTML=`<span class="jbtn"><span class="jc"><svg viewBox="0 0 24 24"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" fill="currentColor"/></svg></span><span class="jl">Your plan</span></span>`;ol.appendChild(fin);
  j.appendChild(ol);
  const cur=j.querySelector(".now");if(cur)requestAnimationFrame(()=>cur.scrollIntoView({inline:"center",block:"nearest",behavior:"smooth"}));
  progress();
}
function editStep(k){DONE.delete(k);if(k==="problem"){DONE.delete("follow");DONE.delete("extra")}lockAll();botSay(`Sure, let's change your ${esc(STEP[k].side.toLowerCase())}.`);next();saveState()}
function toggleSide(force){const sd=$("side");if(!sd)return;const open=force??!sd.classList.contains("open");sd.classList.toggle("open",open);$("answersBtn")?.setAttribute("aria-expanded",String(open))}
if($("answersBtn"))$("answersBtn").onclick=()=>{if($("advisor").hidden){$("nameInput").focus();return}if(innerWidth<=900)toggleSide();else{const p=$("side").querySelector(".panel");p.classList.remove("side-flash");void p.offsetWidth;p.classList.add("side-flash");p.scrollIntoView({block:"nearest"})}};
document.addEventListener("keydown",e=>{if(e.key==="Escape")toggleSide(false)});
$("backBtn").onclick=goBack;
function goBack(){
  const blocks=[...thread.querySelectorAll(".stepblock")];const cur=blocks[blocks.length-1];
  const prev=[...STEPS].reverse().find(k=>DONE.has(k));
  if(!prev){thread.innerHTML="";CUR_BLOCK=null;nameAsked=false;stepNow=null;saveState();showWelcome();return}
  if(cur&&cur.dataset.step!==prev)cur.remove();
  const pb=[...thread.querySelectorAll(`.stepblock[data-step="${prev}"]`)].pop();if(pb)pb.remove();
  DONE.delete(prev);if(prev==="problem"){DONE.delete("follow");DONE.delete("extra");PROB=null}
  CUR_BLOCK=null;next();saveState();
}
if($("newBtn"))$("newBtn").onclick=()=>{if($("advisor").hidden){$("nameInput").focus();return}meSay("Start over");STEPS=[...DEFAULT_STEPS];P=emptyProfile();PREF={boost:[]};DONE.clear();PROB=null;SUB=null;lockAll();botSay(NAME?`Fresh start, ${esc(NAME)}. Let's go again.`:"Fresh start. Let's go again.");next();return;botSay("Okay, starting fresh.");next()};
$("deleteBtn").onclick=()=>{clearState();META={planAt:null,planProb:null,checks:[]};FOLLOW_IDX=null;P=emptyProfile();PREF={boost:[]};DONE.clear();PROB=null;SUB=null;NAME=null;nameAsked=false;STEPS=[...DEFAULT_STEPS];lockAll();toggleSide(false);botSay("Done. I've deleted all your answers.");next()};

/* =====================================================================
   3) SEASONS — what the season is in the user's city, and an opt-in nudge
      to refresh the plan when it changes
   ===================================================================== */
const MON=["January","February","March","April","May","June","July","August","September","October","November","December"];
const SEASON_INFO={
  winter:{say:"winter",label:"Winter",tip:"Air turns colder and drier, so I lean towards richer moisturisers with ceramides and gentler cleansing."},
  summer:{say:"summer",label:"Summer",tip:"Heat and sweat mean lighter gel textures and a matte, high-SPF sunscreen you'll actually reapply."},
  premonsoon:{say:"the pre-monsoon season",label:"Pre-monsoon",tip:"Humid heat builds up, so I keep textures light and pores clear."},
  monsoon:{say:"the monsoon",label:"Monsoon",tip:"High humidity means lightweight, non-clogging formulas and a sweat-resistant sunscreen. Breakouts often flare now."},
  nemonsoon:{say:"the northeast monsoon",label:"Northeast monsoon",tip:"Rain and humidity return, so I keep textures light and non-clogging."},
  post:{say:"the post-monsoon season",label:"Post-monsoon",tip:"Humidity starts dropping, so skin can feel tighter. A little more hydration helps."},
  autumn:{say:"autumn",label:"Autumn",tip:"Cooler, drier air arrives, so I add more hydration and barrier support."},
};
function seasonMap(state,climate){
  const NE=["Assam","Meghalaya","Arunachal Pradesh","Nagaland","Manipur","Mizoram","Tripura","Sikkim"];
  if(climate==="cool / hill")return["winter","winter","winter","summer","summer","summer","monsoon","monsoon","monsoon","autumn","winter","winter"];
  if(["Tamil Nadu","Puducherry"].includes(state))return["winter","winter","summer","summer","summer","monsoon","monsoon","monsoon","monsoon","nemonsoon","nemonsoon","nemonsoon"];
  if(NE.includes(state))return["winter","winter","premonsoon","premonsoon","monsoon","monsoon","monsoon","monsoon","monsoon","post","post","winter"];
  if(["Kerala","Goa","Lakshadweep","Andaman and Nicobar Islands"].includes(state))return["winter","winter","summer","summer","summer","monsoon","monsoon","monsoon","monsoon","post","post","winter"];
  return["winter","winter","summer","summer","summer","monsoon","monsoon","monsoon","monsoon","post","post","winter"];
}
function seasonFor(state=P.state,climate=P.climate,month=new Date().getMonth()){
  if(!state)return null;const m=seasonMap(state,climate),key=m[month];
  let s=month,e=month,g=0;while(m[(s+11)%12]===key&&g++<11)s=(s+11)%12;g=0;while(m[(e+1)%12]===key&&g++<11)e=(e+1)%12;
  const n=(e+1)%12;
  return{key,...SEASON_INFO[key],from:MON[s],to:MON[e],next:SEASON_INFO[m[n]].label,nextSay:SEASON_INFO[m[n]].say,nextKey:m[n],nextFrom:MON[n]};
}
function seasonCardHTML(city,state,climate){
  const s=seasonFor(state,climate);if(!s)return"";
  return`<div class="season"><div class="season-ic">${SEASON_IC[s.key]||SEASON_IC.summer}</div><div class="season-tx">
    <span class="season-eyebrow">Right now in ${esc(city)}</span><b>${esc(s.label)}</b><span class="season-when">${esc(s.from)}${s.from!==s.to?` to ${esc(s.to)}`:""}</span>
    <p>${esc(s.tip)}</p><p class="season-next">Next: <b>${esc(s.next)}</b> from ${esc(s.nextFrom)}.</p>
    <label class="agree season-opt"><input type="checkbox" data-salert ${P.seasonAlert!==false?"checked":""}> Remind me to refresh my plan when the season changes in ${esc(city)}</label></div></div>`;
}
const SEASON_IC={
  winter:SVG('<path d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9M9 4.5l3 2 3-2M9 19.5l3-2 3 2"/>'),
  summer:SVG('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
  premonsoon:SVG('<path d="M7 15a4 4 0 1 1 1-7.9A5 5 0 0 1 18 9a3.5 3.5 0 0 1-1 6.9z"/><circle cx="17" cy="5" r="2"/>'),
  monsoon:SVG('<path d="M7 13a4 4 0 1 1 1-7.9A5 5 0 0 1 18 7a3.5 3.5 0 0 1-1 6.9H7z"/><path d="M8 17l-1 3M12 17l-1 3M16 17l-1 3"/>'),
  nemonsoon:SVG('<path d="M7 13a4 4 0 1 1 1-7.9A5 5 0 0 1 18 7a3.5 3.5 0 0 1-1 6.9H7z"/><path d="M8 17l-1 3M12 17l-1 3M16 17l-1 3"/>'),
  post:SVG('<path d="M7 16a4 4 0 1 1 1-7.9A5 5 0 0 1 18 10a3.5 3.5 0 0 1-1 6.9z"/><path d="M12 2v2M4 6l1.5 1.5"/>'),
  autumn:SVG('<path d="M5 19c8 0 14-6 14-14-8 0-14 6-14 14z"/><path d="M5 19l7-7"/>'),
};
/* season nudges the ranking a little: textures that suit the weather right now */
function seasonBoost(p){
  const s=seasonFor();if(!s)return 0;const t=hay(p);let b=0;
  if(p.c==="Moisturiser"){
    if(["winter","autumn","post"].includes(s.key)&&/ceramide|squalane|butyrospermum|shea|cream/i.test(t))b+=1.5;
    if(["summer","monsoon","premonsoon","nemonsoon"].includes(s.key)){if(/gel|oil-free|water|aqua|matte/i.test(p.n))b+=1.5;if(/butter|rich|night cream/i.test(p.n))b-=1}}
  if(p.c==="Sunscreen"&&["monsoon","premonsoon","nemonsoon","summer"].includes(s.key)&&/matte|gel|aqua|sport|water/i.test(p.n))b+=1;
  if(p.c==="Cleanser"&&s.key==="winter"&&/foam|clarifying|deep/i.test(p.n))b-=0.8;
  return b;
}

/* =====================================================================
   SHARE — WhatsApp text (no private answers) and a branded PDF
   ===================================================================== */
function planShareText(){
  const prob=PROBLEMS[PROB].label.toLowerCase();const nums=["1️⃣","2️⃣","3️⃣"];
  const lines=PL.slots.map((s,i)=>s.keep?`${nums[i]} ${s.slot.role} (${s.slot.when.toLowerCase()}): keep using my ${s.keep.short.toLowerCase()}`:s.p?`${nums[i]} ${s.slot.role} (${s.slot.when.toLowerCase()}): ${s.p.n} – ${rupee(s.p.p)}`:null).filter(Boolean);
  const total=PL.slots.reduce((t,s)=>t+(s.p?.p||0),0);
  return`✨ My Aaina skin plan for ${prob}\n\n${lines.join("\n")}\n\nTotal: ${rupee(total)}\n\nTip: start one product at a time, a few days apart, and wear sunscreen every morning.\n\nMade with Aaina AI Skin Advisor · Reflect. Reveal. Radiate.`;
}
function shareBarHTML(){
  const wa="https://wa.me/?text="+encodeURIComponent(planShareText());
  return`<div class="sharebar" role="group" aria-label="Share or save your plan">
    <a class="btn wa" href="${wa}" target="_blank" rel="noopener" data-wa>${SVG('<path d="M4 20l1.3-4A8 8 0 1 1 8 18.7z"/><path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1.2-1.4-1.9-1-1 .8a4 4 0 0 1-2.2-2.2l.8-1-1-1.9z"/>')}Share on WhatsApp</a>
    <button type="button" class="btn" data-pdf>${SVG('<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>')}Save as PDF</button>
    <button type="button" class="btn ghost" data-copy>${SVG('<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>')}Copy plan</button>
    <span class="sharemsg" data-sharemsg role="status"></span>
    <p class="sharenote">Sharing includes only your products and routine, not your safety answers.</p></div>`;
}
function wireShare(box){
  const msg=box.querySelector("[data-sharemsg]");const say=t=>{msg.textContent=t;clearTimeout(say.t);say.t=setTimeout(()=>msg.textContent="",4000)};
  box.querySelector("[data-wa]").addEventListener("click",e=>{
    if(navigator.share&&matchMedia("(pointer:coarse)").matches){e.preventDefault();navigator.share({text:planShareText()}).catch(()=>{})}});
  box.querySelector("[data-copy]").onclick=async()=>{const t=planShareText();
    try{await navigator.clipboard.writeText(t);say("Plan copied. Paste it anywhere.")}
    catch{const ta=document.createElement("textarea");ta.value=t;ta.style.position="fixed";ta.style.opacity="0";document.body.appendChild(ta);ta.select();let ok=false;try{ok=document.execCommand("copy")}catch{}ta.remove();say(ok?"Plan copied. Paste it anywhere.":"Couldn't copy here. Use Share on WhatsApp instead.")}};
  box.querySelector("[data-pdf]").onclick=async e=>{const b=e.currentTarget;b.disabled=true;try{say(await savePlanPDF())}finally{b.disabled=false}};
}
async function savePlanPDF(){
  const bytes=makePlanPDF();const filename=`Aaina-skin-plan${NAME?"-"+NAME.replace(/[^\w-]/g,""):""}.pdf`;const blob=new Blob([bytes],{type:"application/pdf"});
  try{if(window.claude&&typeof window.claude.use==="function"){const dl=await Promise.race([window.claude.use("downloads"),new Promise(r=>setTimeout(()=>r(null),3000))]);
      if(dl){try{await dl.save({filename,data:blob});return"PDF saved."}catch(err){if(err&&err.code==="declined")return"";if(err&&err.code==="rate_limited")return"A save is already open. Finish that one first.";}}}}catch{}
  try{const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),4000);return"PDF downloaded."}
  catch{return"Couldn't save the PDF here. Try Copy plan instead."}
}
/* --- a small PDF writer: A4, Helvetica, text + rectangles, no libraries --- */
const HELV=[278,278,355,556,556,889,667,191,333,333,389,584,278,333,278,278,556,556,556,556,556,556,556,556,556,556,278,278,584,584,584,556,1015,667,667,722,722,667,611,778,722,278,500,667,556,833,722,778,667,778,722,667,611,722,667,944,667,667,611,278,278,278,469,556,333,556,556,500,556,556,278,556,556,222,222,500,222,833,556,556,556,556,333,500,278,556,500,722,500,500,500,334,260,334,584];
function pdfClean(s){return String(s??"").replace(/₹\s?/g,"Rs ").replace(/[–—]/g,"-").replace(/[‘’]/g,"'").replace(/[“”]/g,'"').replace(/·/g,"·").replace(/…/g,"...").replace(/[^\x20-\x7E -ÿ]/g,"")}
function pdfW(s,size,bold){let w=0;for(const ch of s){const c=ch.charCodeAt(0);w+=(c>=32&&c<=126?HELV[c-32]:556)}return w*size/1000*(bold?1.07:1)}
function pdfWrap(s,size,maxW,bold){const words=pdfClean(s).split(/\s+/).filter(Boolean),out=[];let line="";
  for(const w of words){const t=line?line+" "+w:w;if(pdfW(t,size,bold)>maxW&&line){out.push(line);line=w}else line=t}if(line)out.push(line);return out}
function makePlanPDF(){
  const W=595,H=842,M=48,CW=W-2*M;const pages=[];let ops=[],y=0;
  const rgb=h=>{const n=parseInt(h.slice(1),16);return[(n>>16&255)/255,(n>>8&255)/255,(n&255)/255].map(v=>v.toFixed(3)).join(" ")};
  const esc2=s=>s.replace(/\\/g,"\\\\").replace(/\(/g,"\\(").replace(/\)/g,"\\)");
  const text=(x,yy,s,size,{bold=false,color="#2a1420"}={})=>ops.push(`BT /${bold?"F2":"F1"} ${size} Tf ${rgb(color)} rg ${x.toFixed(1)} ${(H-yy).toFixed(1)} Td (${esc2(pdfClean(s))}) Tj ET`);
  const rect=(x,yy,w,h,color)=>ops.push(`${rgb(color)} rg ${x.toFixed(1)} ${(H-yy-h).toFixed(1)} ${w.toFixed(1)} ${h.toFixed(1)} re f`);
  const BR="#7d174c",INK="#2a1420",MUTED="#7a6470",SOFT="#fbe7ef";
  const footer=()=>{text(M,H-30,"Cosmetic advice only, not medical advice. Aaina is a fictional demo brand (PS-14).",8,{color:MUTED});text(W-M-40,H-30,`Page ${pages.length+1}`,8,{color:MUTED})};
  const newPage=()=>{if(ops.length){footer();pages.push(ops.join("\n"))}ops=[];y=M};
  const need=h=>{if(y+h>H-56){newPage();y=M}};
  const para=(s,size,{bold=false,color=INK,x=M,w=CW,gap=4}={})=>{for(const l of pdfWrap(s,size,w,bold)){need(size+gap);text(x,y+size,l,size,{bold,color});y+=size+gap}};
  // header band
  rect(0,0,W,96,BR);text(M,46,"Aaina",28,{bold:true,color:"#ffffff"});text(M,66,"REFLECT. REVEAL. RADIATE.",8.5,{color:"#f6cfe0"});
  text(W-M-pdfW("AI Skin Advisor",11,true),46,"AI Skin Advisor",11,{bold:true,color:"#ffffff"});
  const today=new Date().toLocaleDateString("en-IN",{day:"numeric",month:"long",year:"numeric"});
  text(W-M-pdfW(today,9),64,today,9,{color:"#f6cfe0"});
  y=130;const prob=PROBLEMS[PROB];
  para(`${NAME?NAME+"'s":"Your"} skin plan`,22,{bold:true});y+=2;
  para(`For ${prob.label.toLowerCase()}${SUB?` (${SUB.toLowerCase()})`:""}`,12,{color:MUTED});y+=10;
  // profile strip
  const s=seasonFor();
  const facts=[P.skin&&["Skin type",cap(P.skin)],P.tone&&["Skin tone",`${P.tone} of 10, ${MONK_LABEL[P.tone]}`],P.city&&["City",P.city],s&&["Season now",s.label],["Budget",P.budget?`Under Rs ${P.budget} each`:"No limit"]].filter(Boolean);
  need(64);rect(M,y,CW,58,SOFT);const colW=CW/facts.length;
  facts.forEach(([k,v],i)=>{text(M+12+i*colW,y+17,k.toUpperCase(),7.5,{bold:true,color:BR});pdfWrap(v,9.5,colW-16,true).slice(0,2).forEach((ln,j)=>text(M+12+i*colW,y+32+j*12,ln,9.5,{bold:true}))});y+=74;
  const checks=[P.avoidFrag&&"Fragrance-free",P.avoidEO&&"No essential oils",P.noClog&&"Won't clog pores",P.sensitive&&"Gentle for sensitive skin",P.budget&&`Each under Rs ${P.budget}`].filter(Boolean);
  if(checks.length){para("Checks every product passed: "+checks.join("  ·  "),9.5,{color:MUTED});y+=6}
  // routine
  y+=6;para("Your routine",15,{bold:true});y+=4;
  PL.slots.forEach((sl,i)=>{
    const p=sl.p,k=sl.keep;const body=[];
    if(k)body.push(["",`Keep using ${k.p?k.p.n:k.name}. It already covers this step, so there's no need to buy another.`]);
    else if(p){body.push(["Why",oneLine(p,sl.slot)]);body.push(["How to use",useList(p,sl.slot).map(cap).join(". ")+"."])}
    else body.push(["","Nothing in our range passes all your checks for this step, so I've left it out rather than bend a safety rule."]);
    const lines=body.reduce((n,[l,t])=>n+pdfWrap(t,9.5,CW-110,false).length,0);const h=44+lines*13.5+(p?14:0);
    need(h+10);rect(M,y,CW,h,"#fdf5f8");rect(M,y,4,h,BR);
    rect(M+14,y+12,20,20,BR);text(M+21,y+26,String(i+1),11,{bold:true,color:"#ffffff"});
    text(M+44,y+22,`${sl.slot.role.toUpperCase()}  ·  ${sl.slot.when}`,8.5,{bold:true,color:BR});
    const name=k?(k.p?k.p.n:cap(k.short)):p?p.n:"No product";text(M+44,y+38,pdfWrap(name,12.5,CW-140,true)[0],12.5,{bold:true});
    if(p){const pr=`Rs ${Math.round(p.p).toLocaleString("en-IN")}`;text(W-M-12-pdfW(pr,12.5,true),y+38,pr,12.5,{bold:true});text(M+44,y+52,`${p.b}  ·  ${p.c}${p.sz?"  ·  "+p.sz:""}`,8.5,{color:MUTED})}
    else if(k)text(W-M-12-pdfW("ALREADY YOURS",8,true),y+38,"ALREADY YOURS",8,{bold:true,color:BR});
    let yy=y+(p?70:56);
    for(const[l,t]of body){const ls=pdfWrap(t,9.5,CW-110,false);if(l)text(M+44,yy,l,8.5,{bold:true,color:MUTED});ls.forEach((ln,j)=>text(M+(l?110:44),yy+j*13.5,ln,9.5));yy+=ls.length*13.5}
    y+=h+10;
  });
  const total=PL.slots.reduce((t,x)=>t+(x.p?.p||0),0);const kept=PL.slots.filter(x=>x.keep).length;
  need(30);rect(M,y,CW,1,"#e8cfdb");y+=18;text(M,y,kept?`Total for the new product${3-kept>1?"s":""}`:"Total for all three",11);const tt=`Rs ${Math.round(total).toLocaleString("en-IN")}`;text(W-M-pdfW(tt,15,true),y+2,tt,15,{bold:true});y+=26;
  // shelf notes
  if((PL.shelf||[]).length){const d=document.createElement("div");d.innerHTML=shelfPlanNote();const items=[...d.querySelectorAll("li")].map(li=>li.textContent.trim()).filter(Boolean);
    if(items.length){y+=4;para("Works with what you already use",12.5,{bold:true});items.forEach(t=>para("-  "+t,9.5,{x:M+6,w:CW-6}));y+=6}}
  // first weeks
  y+=4;para("Your first few weeks",12.5,{bold:true});
  ["Start one product at a time, a few days apart, so you know how your skin feels with each.","Patch-test new products on your jaw for 2-3 days first, and stop if anything stings or burns.","Wear sunscreen every morning, even on cloudy days.",`Give the plan ${PROB==="dehydration"||PROB==="dullness"?"two to four":"six to eight"} weeks before judging it.`].forEach(t=>para("-  "+t,9.5,{x:M+6,w:CW-6}));
  if(s){y+=8;para(`Season: it's ${s.say} in ${P.city} now. ${s.next} starts in ${s.nextFrom}, which is a good time to refresh your plan.`,9.5,{color:MUTED})}
  y+=6;para("If your skin becomes painful or swollen, or the problem spreads, please see a dermatologist.",9,{color:MUTED});
  footer();pages.push(ops.join("\n"));
  // assemble
  const objs=[];const add=s=>{objs.push(s);return objs.length};
  const cat=add(""),pagesId=add(""),f1=add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"),f2=add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>");
  const kids=[];for(const c of pages){const cs=add(`<< /Length ${c.length} >>\nstream\n${c}\nendstream`);kids.push(add(`<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 ${W} ${H}] /Resources << /Font << /F1 ${f1} 0 R /F2 ${f2} 0 R >> >> /Contents ${cs} 0 R >>`))}
  objs[cat-1]=`<< /Type /Catalog /Pages ${pagesId} 0 R >>`;objs[pagesId-1]=`<< /Type /Pages /Kids [${kids.map(k=>k+" 0 R").join(" ")}] /Count ${kids.length} >>`;
  const info=add(`<< /Title (${esc2(pdfClean((NAME?NAME+"'s ":"")+"Aaina skin plan"))}) /Producer (Aaina AI Skin Advisor) >>`);
  let out="%PDF-1.4\n%âãÏÓ\n";const offs=[];
  objs.forEach((o,i)=>{offs.push(out.length);out+=`${i+1} 0 obj\n${o}\nendobj\n`});
  const xref=out.length;out+=`xref\n0 ${objs.length+1}\n0000000000 65535 f \n`+offs.map(o=>String(o).padStart(10,"0")+" 00000 n \n").join("");
  out+=`trailer\n<< /Size ${objs.length+1} /Root ${cat} 0 R /Info ${info} 0 R >>\nstartxref\n${xref}\n%%EOF`;
  const bytes=new Uint8Array(out.length);for(let i=0;i<out.length;i++)bytes[i]=out.charCodeAt(i)&255;return bytes;
}
function useList(p,slot){
  const use=[slot.when];
  if(p.aha||p.bha&&p.leaveOn||p.ret)use.push("start 2-3 nights a week and build up");
  if(p.c==="Sunscreen")use.push("use two finger-lengths for face and neck, and reapply every 2-3 hours outdoors");
  if(p.c==="Cleanser")use.push("massage for 30 seconds, then rinse with lukewarm water");
  if(isActive(p)||P.sensitive)use.push("patch-test on your jaw for 2-3 days first");
  return use;
}

/* =====================================================================
   1) SAVE & RESUME — answers are saved on this device after every step
   ===================================================================== */
const STORE_KEY="aaina.advisor.v1";
let FOLLOW_IDX=null,RESTORE_IDS=null;
let META={planAt:null,planProb:null,checks:[]};
function store(){try{return window.localStorage}catch{return null}}
function saveState(){
  const ls=store();if(!ls)return;
  try{ls.setItem(STORE_KEY,JSON.stringify({v:1,NAME,PROB,SUB,FOLLOW_IDX,P,DONE:[...DONE],STEPS,
    planIds:PL&&!stepNow?PL.slots.map(s=>s.keep?"keep":s.p?.id||null):null,META,updated:Date.now()}))}catch{}
}
function loadState(){const ls=store();if(!ls)return null;try{const d=JSON.parse(ls.getItem(STORE_KEY)||"null");return d&&d.v===1&&d.NAME!==undefined?d:null}catch{return null}}
function clearState(){const ls=store();if(ls)try{ls.removeItem(STORE_KEY)}catch{}}
const DAY=86400000;
const daysSince=t=>t?Math.floor((Date.now()-t)/DAY):0;
const agoText=t=>{const d=daysSince(t);return d<=0?"today":d===1?"yesterday":`${d} days ago`};
function dueCheck(meta){
  if(!meta||!meta.planAt)return null;const d=daysSince(meta.planAt),done=new Set((meta.checks||[]).map(c=>c.stage));
  if(d>=14&&!done.has("week2"))return"week2";if(d>=3&&!done.has("day3"))return"day3";return null;
}
function restoreState(d){
  NAME=d.NAME;nameAsked=true;PROB=d.PROB;SUB=d.SUB;FOLLOW_IDX=d.FOLLOW_IDX;PREF={boost:[]};
  if(PROB&&FOLLOW_IDX!=null&&PROBLEMS[PROB]?.follow.opts[FOLLOW_IDX])STEP.follow.apply(FOLLOW_IDX);
  P=Object.assign(emptyProfile(),d.P||{});DONE=new Set(d.DONE||[]);
  STEPS=Array.isArray(d.STEPS)&&DEFAULT_STEPS.every(k=>d.STEPS.includes(k))?d.STEPS:[...DEFAULT_STEPS];
  META=Object.assign({planAt:null,planProb:null,checks:[]},d.META||{});RESTORE_IDS=d.planIds||null;
}
function renderResume(){
  const box=$("resume");if(!box)return;const d=loadState();
  if(!d||!d.NAME||!(d.DONE||[]).length){box.hidden=true;box.innerHTML="";return}
  const steps=Array.isArray(d.STEPS)?d.STEPS:DEFAULT_STEPS,done=steps.filter(k=>(d.DONE||[]).includes(k)).length,finished=done>=steps.length&&d.PROB;
  const nextIdx=steps.findIndex(k=>!(d.DONE||[]).includes(k))+1;const prob=d.PROB&&PROBLEMS[d.PROB]?PROBLEMS[d.PROB].label.toLowerCase():null;
  const due=finished?dueCheck(d.META):null;
  const sNow=finished&&d.P?.seasonAlert&&d.P?.state?seasonFor(d.P.state,d.P.climate):null,sChanged=sNow&&d.META?.planSeason&&sNow.key!==d.META.planSeason;
  box.hidden=false;
  box.innerHTML=finished
    ?`<div class="rs-ic">${SVG('<path d="M5 12l4 4 10-10"/>')}</div><div class="rs-tx"><b>Welcome back, ${esc(d.NAME)}.</b> Your plan for <b>${esc(prob)}</b> is saved${d.META?.planAt?` (made ${agoText(d.META.planAt)})`:""}.${due?`<span class="rs-due">${due==="week2"?"Two weeks in! Time for a quick check-in.":"It's been 3 days. How are your products going?"}</span>`:""}${sChanged?`<span class="rs-due rs-season">${SEASON_IC[sNow.key]||""}${esc(sNow.label)} has started in ${esc(d.P.city)}. Want to refresh your plan for it?</span>`:""}</div>
       <div class="rs-act">${sChanged?`<button type="button" class="btn primary" data-rs="season">Refresh for ${esc(sNow.label.toLowerCase())}</button>`:""}${due?`<button type="button" class="btn${sChanged?"":" primary"}" data-rs="check">Check in now</button><button type="button" class="btn" data-rs="plan">View my plan</button>`:`<button type="button" class="btn${sChanged?"":" primary"}" data-rs="plan">View my plan</button><button type="button" class="btn" data-rs="check">Report how it's going</button>`}<button type="button" class="btn ghost" data-rs="fresh">Start fresh</button></div>`
    :`<div class="rs-ic">${SVG('<path d="M12 7v5l3 2"/><circle cx="12" cy="12" r="9"/>')}</div><div class="rs-tx"><b>Welcome back, ${esc(d.NAME)}.</b> You were on <b>question ${nextIdx} of ${steps.length}</b>${prob?` of your plan for ${esc(prob)}`:""}. Your answers are saved.<div class="rs-bar" aria-hidden="true"><span style="width:${Math.round(100*done/steps.length)}%"></span></div></div>
       <div class="rs-act"><button type="button" class="btn primary" data-rs="go">Continue where I left off</button><button type="button" class="btn ghost" data-rs="fresh">Start fresh</button></div>`;
  box.querySelectorAll("[data-rs]").forEach(b=>b.onclick=()=>{const a=b.dataset.rs;
    if(a==="fresh"){clearState();resetAll();renderResume();$("nameInput").focus();return}
    resumeFrom(d,a==="check",a==="season")});
}
function resumeFrom(d,thenCheck,seasonRefresh){
  restoreState(d);P.month=new Date().getMonth();
  if(seasonRefresh){const before=(d.planIds||[]).map(id=>id&&id!=="keep"?BY_ID[id]:null);RESTORE_IDS=(d.planIds||[]).map(id=>id==="keep"?"keep":null);
    $("welcome").hidden=true;$("advisor").hidden=false;thread.innerHTML="";CUR_BLOCK=null;
    buildPlan(true);const se=seasonFor();const ch=PL.slots.map((s,i)=>before[i]&&s.p&&before[i].id!==s.p.id?`<li>${esc(s.slot.role)}: <b>${esc(s.p.n)}</b> instead of ${esc(before[i].n)}</li>`:"").filter(Boolean);
    botSay(`<p>Welcome back, <b>${esc(NAME)}</b>! It's <b>${esc(se.say)}</b> in ${esc(P.city)} now. ${esc(se.tip)}</p>${ch.length?`<p>Here's what I changed:</p><ul class="cknotes">${ch.join("")}</ul>`:`<p>Good news: your current products <b>still suit this season</b>, so nothing needs to change.</p>`}`);
    updateTitle();renderPlan();return}
  $("welcome").hidden=true;$("advisor").hidden=false;thread.innerHTML="";CUR_BLOCK=null;
  const left=STEPS.filter(k=>!DONE.has(k)).length;
  botSay(left?`<p>Welcome back, <b>${esc(NAME)}</b>! I've kept all your answers, so let's pick up at <b>question ${STEPS.length-left+1}</b>.</p>`:`<p>Welcome back, <b>${esc(NAME)}</b>! Here's the plan we made${META.planAt?` ${agoText(META.planAt)}`:""}.</p>`);
  updateTitle();next();
  if(thenCheck&&PL)openCheckin();
}
function resetAll(){P=emptyProfile();PREF={boost:[]};DONE.clear();PROB=null;SUB=null;FOLLOW_IDX=null;PL=null;RESTORE_IDS=null;META={planAt:null,planProb:null,checks:[]};NAME=null;nameAsked=false;STEPS=[...DEFAULT_STEPS];thread.innerHTML="";CUR_BLOCK=null}

/* =====================================================================
   5) WHAT YOU ALREADY USE — build around the shelf and avoid clashes
   ===================================================================== */
const SHELF_TYPES=[
  {k:"cleanser",label:"Face wash",sub:"Any cleanser",cat:"Cleanser",con:[]},
  {k:"moist",label:"Moisturiser",sub:"Cream, gel or lotion",cat:"Moisturiser",con:["dehydration"]},
  {k:"spf",label:"Sunscreen",sub:"SPF 30 or higher",cat:"Sunscreen",con:["tanning","pigmentation"]},
  {k:"vitc",label:"Vitamin C serum",sub:"Brightening",cat:"Serum",act:["vitamin c"],con:["pigmentation","dullness","tanning"]},
  {k:"nia",label:"Niacinamide serum",sub:"Oil and marks",cat:"Serum",act:["niacinamide"],con:["acne","pigmentation","oiliness"]},
  {k:"ha",label:"Hyaluronic acid serum",sub:"Hydrating",cat:"Serum",act:["hyaluronic acid"],con:["dehydration"]},
  {k:"ret",label:"Retinol or retinoid",sub:"Including adapalene",cat:"Serum",ret:true,act:["retinol"],con:["fine lines","acne"]},
  {k:"aha",label:"Glycolic or AHA exfoliant",sub:"Toner, peel or serum",cat:"Exfoliant",acid:true,act:["glycolic acid (aha)"],con:["dullness","pigmentation"]},
  {k:"bha",label:"Salicylic acid (BHA)",sub:"Leave-on toner or serum",cat:"Exfoliant",acid:true,act:["salicylic acid (bha)"],con:["acne","oiliness"]},
  {k:"bp",label:"Benzoyl peroxide",sub:"Spot gel",cat:"Spot treatment",bp:true,act:["benzoyl peroxide"],con:["acne"]},
];
const ACT_TO_REACTION={"vitamin c":"vitamin c","niacinamide":"niacinamide","retinol":"retinoids","glycolic acid (aha)":"glycolic acid","salicylic acid (bha)":"salicylic acid","lactic acid":"lactic acid","azelaic acid":"azelaic acid"};
function shelfItems(){
  return (P.shelf||[]).map(x=>{
    if(x.id&&BY_ID[x.id]){const p=BY_ID[x.id];return{key:x.id,name:p.n,short:p.n,cat:p.c,p,ret:!!p.ret,acid:!!((p.aha||p.bha)&&p.c!=="Cleanser"),bp:/benzoyl/i.test(hay(p)),acts:actives(p).map(a=>a.name.toLowerCase()),con:p.con||[]}}
    const t=SHELF_TYPES.find(t=>t.k===x.type);if(!t)return null;
    return{key:t.k,name:`your ${t.label.toLowerCase()}`,short:t.label,cat:t.cat,ret:!!t.ret,acid:!!t.acid,bp:!!t.bp,acts:t.act||[],con:t.con||[]};
  }).filter(Boolean).map(o=>{o.warn=shelfWarnings(o);o.safe=!o.warn.length;return o});
}
function shelfWarnings(o){
  const w=[];
  if(o.p){const r=check(o.p);if(!r.ok)w.push(...r.blocks.map(b=>b[1]))}
  else{
    if(o.ret&&P.pregnancy!==false)w.push("retinoids aren't recommended while you're being pregnancy-cautious");
    for(const a of o.acts){const r=ACT_TO_REACTION[a];if(r&&P.reactions.includes(r))w.push(`it contains ${r}, which you've reacted to`)}
  }
  return uniq(w);
}
function shelfWidget(){
  const w=document.createElement("div");w.className="qbody shelf";
  const picked=new Set((P.shelf||[]).filter(x=>x.type).map(x=>x.type));const own=(P.shelf||[]).filter(x=>x.id).map(x=>x.id);
  w.innerHTML=`<div class="opts shelfopts"></div>
    <div class="shelfadd"><label for="shelfFind">Or add a product by name</label>
      <div class="shelfrow"><input id="shelfFind" type="search" list="shelfList" autocomplete="off" placeholder="Start typing, e.g. Niacinamide or P1025"><button type="button" class="btn" data-add>Add</button></div>
      <datalist id="shelfList">${CAT.map(p=>`<option value="${esc(p.n)}"></option>`).join("")}</datalist>
      <div class="shelfchips" data-chips></div><p class="small muted" data-msg hidden></p></div>
    <div class="qactions"><button type="button" class="btn primary" data-go>Continue</button><button type="button" class="btn" data-none>Nothing yet</button></div>`;
  const grid=w.querySelector(".shelfopts"),chips=w.querySelector("[data-chips]"),find=w.querySelector("#shelfFind"),msg=w.querySelector("[data-msg]"),go=w.querySelector("[data-go]");
  const count=()=>picked.size+own.length;const upd=()=>{go.textContent=count()?`Continue with ${count()}`:"Continue"};
  for(const t of SHELF_TYPES){const b=document.createElement("button");b.type="button";b.className="opt";b.setAttribute("aria-pressed",String(picked.has(t.k)));
    b.innerHTML=`<b>${esc(t.label)}</b><span>${esc(t.sub)}</span>`;b.onclick=()=>{picked.has(t.k)?picked.delete(t.k):picked.add(t.k);b.setAttribute("aria-pressed",String(picked.has(t.k)));upd()};grid.appendChild(b)}
  const drawChips=()=>{chips.innerHTML=own.map(id=>`<span class="schip">${esc(BY_ID[id].n)}<button type="button" aria-label="Remove ${esc(BY_ID[id].n)}" data-rm="${id}">×</button></span>`).join("");
    chips.querySelectorAll("[data-rm]").forEach(b=>b.onclick=()=>{own.splice(own.indexOf(b.dataset.rm),1);drawChips();upd()})};
  const add=()=>{const v=find.value.trim();if(!v)return;const p=CAT.find(p=>p.n.toLowerCase()===v.toLowerCase())||findProduct(v);
    if(!p){msg.hidden=false;msg.textContent="I couldn't find that one in our range. Pick the closest type above instead.";return}
    msg.hidden=true;if(!own.includes(p.id))own.push(p.id);find.value="";drawChips();upd()};
  w.querySelector("[data-add]").onclick=add;find.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();add()}});
  find.addEventListener("input",()=>{if(CAT.some(p=>p.n.toLowerCase()===find.value.trim().toLowerCase()))add()});
  go.onclick=()=>{const v=[...[...picked].map(type=>({type})),...own.map(id=>({id}))];answer("shelf",v,v.length?`${v.length} products`:"Nothing yet")};
  w.querySelector("[data-none]").onclick=()=>answer("shelf",[],"Nothing yet");
  drawChips();upd();return w;
}
let SHELF_ACTS=new Set();

/* =====================================================================
   4) CHECK-INS — day 3 and week 2; a bad reaction swaps the product
   ===================================================================== */
const CHECK_OPTS=[["good","Going well"],["notyet","Not started yet"],["sting","Stinging or redness"],["break","New breakouts"],["stop","Stopped using it"]];
function openCheckin(){
  if(!PL)return;const stage=dueCheck(META)||"anytime";
  const items=PL.slots.map((s,i)=>({s,i})).filter(x=>x.s.p);
  const box=document.createElement("div");box.className="q checkin";
  box.innerHTML=`<div class="row qhead">${avatar()}<div><span class="qnum">${stage==="week2"?"Week 2 check-in":stage==="day3"?"Day 3 check-in":"Check-in"}</span><h3 class="qtitle">How are your products going${nm(", ")}?</h3><p class="qhelp">Be honest, it helps. If something <b>stings, turns red or breaks you out</b>, I'll <b>swap it</b> and remember to avoid that ingredient.</p></div></div>
    <div class="qbody"><div class="cklist">${items.map(({s,i})=>`<fieldset class="ckrow" data-i="${i}"><legend><span class="role">${esc(s.slot.role)}</span><b>${esc(s.p.n)}</b></legend><div class="ckopts">${CHECK_OPTS.map(([v,l])=>`<label class="ckopt ck-${v}"><input type="radio" name="ck${i}" value="${v}"><span>${esc(l)}</span></label>`).join("")}</div></fieldset>`).join("")}</div>
    <div class="qactions"><button type="button" class="btn primary" data-save disabled>Update my plan</button><button type="button" class="btn" data-cancel>Not now</button></div></div>`;
  const save=box.querySelector("[data-save]");
  box.addEventListener("change",()=>{save.disabled=!box.querySelector("input:checked")});
  box.querySelector("[data-cancel]").onclick=()=>{box.closest(".stepblock").remove();CUR_BLOCK=null;renderPlan()};
  save.onclick=()=>{const res={};box.querySelectorAll(".ckrow").forEach(f=>{const c=f.querySelector("input:checked");if(c)res[f.dataset.i]=c.value});applyCheckin(res,stage)};
  const blk=newBlock("checkin");blk.appendChild(box);requestAnimationFrame(()=>thread.scrollTo({top:0}));
}
function applyCheckin(res,stage){
  const notes=[],swapped=[],avoidNew=[];P.excluded=P.excluded||[];
  for(const[i,v]of Object.entries(res)){const s=PL.slots[+i],p=s.p;if(!p)continue;
    if(v==="sting"||v==="break"){
      if(!P.excluded.includes(p.id))P.excluded.push(p.id);
      const main=actives(p).map(a=>ACT_TO_REACTION[a.name.toLowerCase()]).find(Boolean);const r=main&&!P.reactions.includes(main)&&(isActive(p)||v==="sting")?[main]:[];
      if(r.length){P.reactions=uniq([...P.reactions,...r]);avoidNew.push(...r)}
      else if(v==="sting")P.sensitive=true;
      if(v==="break"&&!isActive(p))P.noClog=true;
      swapped.push({i:+i,old:p,why:v==="sting"?"stung or turned red":"brought on breakouts"});
    }else if(v==="stop")notes.push(`<li><b>${esc(p.n)}</b>: no problem. If it was the texture or price, tap <b>Show another</b> on that step.</li>`);
    else if(v==="good")notes.push(`<li><b>${esc(p.n)}</b>: great, keep going. Most people notice a difference after ${PROB==="dehydration"||PROB==="dullness"?"two to four":"six to eight"} weeks.</li>`);
    else if(v==="notyet")notes.push(`<li><b>${esc(p.n)}</b>: start it when you're ready, one new product every few days.</li>`);
  }
  META.checks=[...(META.checks||[]),{stage,at:Date.now(),res:Object.fromEntries(Object.entries(res).map(([i,v])=>[PL.slots[+i].p?.id||i,v]))}];
  const keepIds=PL.slots.map(s=>s.keep?"keep":s.p?.id||null);const beforeKeep=PL.slots.map(s=>s.keep);
  for(const sw of swapped)keepIds[sw.i]=null;
  RESTORE_IDS=keepIds;
  thread.querySelector(".stepblock:last-child")?.remove();CUR_BLOCK=null;
  let h="";
  if(swapped.length){
    buildPlan(true);
    h+=`<p><b>Thanks for telling me${nm(", ")}.</b> I'm sorry it didn't suit you. Please stop using it and let your skin settle for a few days.</p><ul class="cknotes">${swapped.map(sw=>{const np=PL.slots[sw.i].p;return`<li><b>${esc(sw.old.n)}</b> ${esc(sw.why)}, so I've swapped it for <b>${np?esc(np.n):"nothing yet"}</b>${np?"":", because nothing else passes your checks"}.</li>`}).join("")}${PL.slots.map((s,i)=>beforeKeep[i]&&!s.keep&&!swapped.some(w=>w.i===i)?`<li>Because of that, please also <b>pause ${esc(beforeKeep[i].p?beforeKeep[i].p.n:beforeKeep[i].name)}</b>. I've added <b>${s.p?esc(s.p.n):"nothing yet"}</b> for your ${esc(s.slot.role.toLowerCase())} step instead.</li>`:"").join("")}${notes.join("")}</ul>${avoidNew.length?`<p>I'll also <b>avoid ${esc(uniq(avoidNew).join(", "))}</b> in every plan from now on.</p>`:""}<p class="small muted">If the redness, swelling or breakouts don't settle within a week, please see a dermatologist.</p>`;
  }else{
    h+=`<p><b>Thanks for checking in${nm(", ")}!</b></p><ul class="cknotes">${notes.join("")}</ul>`;
  }
  botSay(h);renderPlan();saveState();
}

/* ---------- typed messages: guardrails first ---------- */
function findProduct(t){const id=/\bP1\d{3}\b/i.exec(t);if(id)return BY_ID[id[0].toUpperCase()];const low=t.toLowerCase();let best=null,bl=0;for(const p of CAT){const n=p.n.toLowerCase();if(low.includes(n)&&n.length>bl){best=p;bl=n.length}}return best}
function productCheck(p){const r=check(p);let h=`<p><b>${esc(p.n)}</b> · ${esc(p.c)} · ${rupee(p.p)}</p>`;
  h+=r.ok?`<p style="color:var(--ok)"><b>This passes ${DONE.has("avoid")?"all your checks":"the checks I can run so far"}.</b>${actives(p).length?" "+actives(p).map(a=>`${esc(a.name)} ${esc(a.does)}.`).join(" "):""}</p>`:`<p style="color:var(--bad)"><b>I wouldn't recommend this one for you</b>, because ${r.blocks.map(b=>esc(b[1])).join("; ")}.</p>`;
  if(p.blankInci)h+=`<p class="small">A missing ingredient list isn't proof of safety.</p>`;
  if(!DONE.has("avoid"))h+=`<p class="small muted">Answer the safety questions for a full check.</p>`;botSay(h)}
function handleTyped(text){
  turn++;const t=text.trim();if(!t)return;
  if(!nameAsked&&!G.inject.test(t)&&!G.redflag.test(t)&&t.split(/\s+/).length<=3&&cleanName(t.replace(/^(i'?m|i am|my name is|call me)\s+/i,""))){setName(cleanName(t.replace(/^(i'?m|i am|my name is|call me)\s+/i,"")));return}
  meSay(t);
  if(G.inject.test(t)){botSay("I can't switch off my safety checks; they run outside this chat, so nothing typed here changes them. I'll only recommend products that pass your checks.","hold");return refocus()}
  if(G.redflag.test(t)){botSay("<p>That sounds like it needs a dermatologist to look at it, and I can't tell what's causing it. Please don't put new products on that area until you've been seen.</p><p>If it's spreading fast, very painful, or you have a fever or swelling near your eyes or mouth, please get medical help today.</p>","escalate");return refocus()}
  if(G.rx.test(t)){botSay("I can't advise on prescription treatments or medicines; a dermatologist can tell you if one is right for you. I can help with products from our range.","hold");return refocus()}
  if(G.fair.test(t)){botSay("I don't recommend products to change your skin tone; every tone deserves good skincare. If dark spots or tanning bother you, pick those as your concern and I'll build a plan.","hold");return refocus()}
  if(G.guarantee.test(t)&&!/\bP1\d{3}\b/.test(t)){botSay("I can't promise results; skin responds differently from person to person. I'll tell you what most people can expect and how long it usually takes.");return refocus()}
  if(G.del.test(t)){$("deleteBtn").click();return}
  const p=findProduct(t);if(p){productCheck(p);return refocus()}
  const slots=parseSlots(t);
  if(stepNow==="problem"&&slots.concerns&&slots.concerns.length){const c=slots.concerns.find(x=>PROBLEMS[x]);if(c){STEP.problem.apply(c);DONE.add("problem");P.concerns=uniq([c,...slots.concerns.filter(x=>PROBLEMS[x])]).slice(0,3);if(P.concerns.length>1)DONE.add("extra");botSay(afterNote("problem")[0]);return next()}}
  if(stepNow==="location"){const hit=findCity(t);if(hit){P.state=hit.state;P.city=hit.city;P.climate=hit.climate;DONE.add("location");botSay(afterNote("location")[0]);return next()}}
  if(stepNow==="react"&&slots.reactions){P.reactions=uniq([...P.reactions,...slots.reactions]);DONE.add("react");botSay(`Noted: I'll avoid ${esc(slots.reactions.join(", "))}.`);return next()}
  if(stepNow&&/^(none|no|nothing|no reactions)\b/i.test(t)&&["avoid","react","preg","extra"].includes(stepNow)){const s=STEP[stepNow];if(s.apply)s.apply(stepNow==="preg"?(t.toLowerCase().startsWith("no")?false:null):stepNow==="budget"?null:[]);DONE.add(stepNow);botSay("Okay.");return next()}
  if(!G.beauty.test(t)){botSay("I'm Aaina's skincare advisor, so I can only help with skin concerns and skincare products.");return refocus()}
  botSay(stepNow?"Thanks. To keep the plan accurate, please pick one of the options above.":"I can check a product (type its name), or start over with another concern.");refocus();
}
function refocus(){const q=thread.querySelector(".q:not(.answered)");if(q){thread.appendChild(q);focusEl(q)}}
function findCity(t){const low=t.toLowerCase();for(const[st,s]of Object.entries(INDIA))for(const c of Object.keys(s.c))if(new RegExp("\\b"+c.toLowerCase().replace(/[()]/g,"")+"\\b").test(low))return{state:st,city:c,climate:s.c[c]||s.d};return null}
$("askForm").addEventListener("submit",e=>{e.preventDefault();const v=$("askInput").value;$("askInput").value="";handleTyped(v.slice(0,400))});

/* ---------- welcome page wiring ---------- */
$("nameInput").addEventListener("input",()=>{$("nameGo").disabled=!cleanName($("nameInput").value)});
$("nameForm").addEventListener("submit",e=>{e.preventDefault();const n=cleanName($("nameInput").value);if(n)setName(n)});
document.querySelectorAll(".skipbtn").forEach(b=>b.addEventListener("click",()=>setName(cleanName($("nameInput").value)||null,b.dataset.start)));
$("learnBtn").addEventListener("click",()=>{const l=$("learnMore");l.hidden=!l.hidden;$("learnBtn").setAttribute("aria-expanded",String(!l.hidden))});
/* ---------- boot ---------- */
$("advIcon").innerHTML=`<span class="brandmark"></span>`;
window.addEventListener("pagehide",()=>{if(nameAsked)saveState()});
if(false)botSay(`<p>Hi, I'm Aaina's AI skin advisor. Tell me what's bothering your skin, and I'll recommend <b>three products that work together</b>, then explain exactly why I chose each one.</p><p class="small muted">About nine quick taps. I check every ingredient list against your answers and never suggest anything that clashes with them.</p>`);
next();
