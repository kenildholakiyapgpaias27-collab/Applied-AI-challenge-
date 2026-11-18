/* Ask Aaina — RAG retrieval
 *
 * Pure client-side. Loads the pre-built embedding index from AAINA_EMBEDDINGS
 * (inlined by build.py), embeds the user query via OpenAI, computes cosine
 * similarity in JS, and fuses with the rule engine via Reciprocal Rank Fusion.
 *
 * Public API exposed on window.AAINA_RAG:
 *   available()               -> bool  (true if an index is loaded and matches the catalogue)
 *   embedQuery(text, key)     -> Promise<Float32Array | null>   (null on failure)
 *   search(vec, topN=50)      -> [{id, score}]  (cosine, highest first)
 *   fuse(engineRanked, ragRanked, topN=10) -> [productId]  (RRF)
 *
 * Does NOT pick products on its own. It gives the chat a candidate set the
 * engine then validates (hard constraints) and re-ranks (RRF).
 * See docs/CATALOGUE_STRUCTURE.md §4 and docs/CHATBOT_GUARDRAILS.md §1.
 */
(function(){
  "use strict";

  var IDX = (typeof AAINA_EMBEDDINGS !== "undefined") ? AAINA_EMBEDDINGS : null;
  var CAT_V = (typeof CAT_VERSION !== "undefined") ? CAT_VERSION : null;

  // -------- index load + sanity --------
  var VECS = null;    // Float32Array of (N * DIM)
  var IDS  = null;    // [productId]
  var NORMS= null;    // Float32Array(N) — pre-computed L2 norms
  var DIM  = 0;

  function loadIndex(){
    if (!IDX || !IDX.items || !IDX.items.length) return false;
    if (CAT_V && IDX.cat_hash && IDX.cat_hash !== CAT_V) {
      // stale index — refuse to use it rather than return wrong products
      console.warn("[aaina-rag] embedding index is stale (cat_hash mismatch); retrieval disabled");
      return false;
    }
    DIM = IDX.dim;
    var N = IDX.items.length;
    VECS  = new Float32Array(N * DIM);
    IDS   = new Array(N);
    NORMS = new Float32Array(N);
    for (var i = 0; i < N; i++) {
      var it = IDX.items[i];
      IDS[i] = it.id;
      var v = it.vec;
      var base = i * DIM;
      var sum = 0;
      for (var j = 0; j < DIM; j++) {
        var x = v[j];
        VECS[base + j] = x;
        sum += x * x;
      }
      NORMS[i] = Math.sqrt(sum) || 1;
    }
    return true;
  }

  var READY = loadIndex();

  function available(){ return !!READY; }

  // -------- query embedding --------
  function embedQuery(text, apiKey){
    if (!apiKey) return Promise.resolve(null);
    return fetch("https://api.openai.com/v1/embeddings", {
      method: "POST",
      headers: { "Content-Type":"application/json", "Authorization":"Bearer "+apiKey },
      body: JSON.stringify({ model: (IDX && IDX.model) || "text-embedding-3-small", input: text })
    }).then(function(r){ return r.json(); }).then(function(data){
      if (!data || !data.data || !data.data[0]) return null;
      var v = data.data[0].embedding;
      if (!v || v.length !== DIM) return null;
      var out = new Float32Array(DIM);
      var sum = 0;
      for (var i = 0; i < DIM; i++) { out[i] = v[i]; sum += v[i]*v[i]; }
      var n = Math.sqrt(sum) || 1;
      for (var k = 0; k < DIM; k++) out[k] /= n;
      return out;
    }).catch(function(){ return null; });
  }

  // -------- cosine search --------
  // qvec is assumed unit-normalised (embedQuery does this)
  function search(qvec, topN){
    if (!READY || !qvec) return [];
    topN = topN || 50;
    var N = IDS.length;
    var scores = new Float32Array(N);
    for (var i = 0; i < N; i++) {
      var base = i * DIM;
      var dot = 0;
      for (var j = 0; j < DIM; j++) dot += VECS[base + j] * qvec[j];
      scores[i] = dot / NORMS[i];
    }
    // top-N selection (partial sort — fine at N=806)
    var idx = new Array(N);
    for (var i2 = 0; i2 < N; i2++) idx[i2] = i2;
    idx.sort(function(a,b){ return scores[b] - scores[a]; });
    var out = [];
    for (var k = 0; k < Math.min(topN, N); k++) {
      out.push({ id: IDS[idx[k]], score: scores[idx[k]] });
    }
    return out;
  }

  // -------- Reciprocal Rank Fusion --------
  // Both inputs are arrays of product IDs in descending order of their own score.
  // Products present in only one list still count — they just score lower.
  // Products rejected by engine.check() should be absent from engineRanked.
  function fuse(engineRanked, ragRanked, topN){
    var K = 60;
    topN = topN || 10;
    var scores = {};
    (engineRanked || []).forEach(function(id, r){
      scores[id] = (scores[id] || 0) + 1 / (K + r + 1);
    });
    (ragRanked || []).forEach(function(id, r){
      // Only include RAG picks that the engine also accepted (hard-constraint safety).
      if (engineRanked && engineRanked.indexOf(id) === -1) return;
      scores[id] = (scores[id] || 0) + 1 / (K + r + 1);
    });
    var ids = Object.keys(scores);
    ids.sort(function(a,b){ return scores[b] - scores[a]; });
    return ids.slice(0, topN);
  }

  window.AAINA_RAG = {
    available:   available,
    embedQuery:  embedQuery,
    search:      search,
    fuse:        fuse,
    dim:         function(){ return DIM; },
    size:        function(){ return IDS ? IDS.length : 0; }
  };
})();
