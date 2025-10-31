// Reagent-ology Addon: NFC → Queue → SSE → Display (g↔ml auto)
(function(){
  const API_BASE = window.REAGENTOLOGY_API_BASE || "http://127.0.0.1:8000";

  // ---------- Helpers ----------
  function $(sel, ctx){ return (ctx||document).querySelector(sel); }
  function displayQty(r){
    if (r && r.current_ml != null) return `${r.current_ml.toFixed(2)} ml`;
    if (r && r.current_net_g != null) return `${r.current_net_g.toFixed(2)} g`;
    if (r && r.Quantity != null) return `${r.Quantity} ${r.unit || ''}`.trim();
    return '-';
  }

  // ---------- NFC overlay ----------
  function ensureOverlay(){
    if ($('#nfc-overlay')) return $('#nfc-overlay');
    const wrap = document.createElement('div');
    wrap.id = 'nfc-overlay';
    wrap.style.cssText = `position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.55);
      display:none;align-items:center;justify-content:center;font-family:sans-serif;`;
    wrap.innerHTML = `
      <div style="background:#0b2239;color:#fff;max-width:600px;width:90%;border-radius:12px;
                  box-shadow:0 10px 30px rgba(0,0,0,.4);overflow:hidden">
        <div style="padding:16px 20px;border-bottom:1px solid rgba(255,255,255,.15);font-weight:700">
          NFC 측정
        </div>
        <div style="padding:20px">
          <div id="nfc-status" style="font-size:16px;line-height:1.5">측정 요청을 준비 중…</div>
          <div id="nfc-result" style="margin-top:12px;font-size:15px"></div>
        </div>
        <div style="padding:14px 20px;border-top:1px solid rgba(255,255,255,.15);text-align:right">
          <button id="nfc-close" style="padding:8px 14px;border:0;border-radius:8px;background:#6aa9ff;color:#001f3f;cursor:pointer">닫기</button>
        </div>
      </div>`;
    document.body.appendChild(wrap);
    $('#nfc-close', wrap).addEventListener('click', ()=>{
      wrap.style.display='none';
      history.replaceState(null, '', location.origin + '/');
    });
    return wrap;
  }

  function getTagUidFromPath(){
    const parts = (location.pathname||'').split('/').filter(Boolean);
    if(parts.length>=2 && parts[0]==='r') return parts[1];
    return null;
  }

  async function startNfcFlow(tagUid){
    const overlay = ensureOverlay();
    overlay.style.display='flex';
    const $status = $('#nfc-status', overlay);
    const $result = $('#nfc-result', overlay);

    // A) Enqueue
    try{
      const r = await fetch(`${API_BASE}/api/queue`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({tag_uid: tagUid})
      });
      if(!r.ok) throw new Error('enqueue failed');
      $status.textContent = `저울 측정 대기중… (UID: ${tagUid})`;
    }catch(e){
      $status.textContent = '등록 실패: 서버 연결 또는 태그 정보 확인';
      return;
    }

    const refreshByTag = async ()=>{
      try{
        const res = await fetch(`${API_BASE}/api/reagents/by-tag/${encodeURIComponent(tagUid)}`);
        if(!res.ok) return;
        const d = await res.json();
        const qty = displayQty(d);
        $status.textContent = '측정 완료';
        $result.innerHTML = `
          <div><b>${d.name}</b></div>
          <div>현재 잔량: <b>${qty}</b></div>
          <div style="opacity:.8;margin-top:6px">용기무게(tare): ${d.tare_g} g</div>`;

        // Detail page live update (if elements exist)
        const qEl = document.getElementById('detail-quantity');
        if(qEl) qEl.textContent = qty;
      }catch{}
    };

    // B) SSE try
    let sseActive = false;
    try{
      const es = new EventSource(`${API_BASE}/api/sse/${encodeURIComponent(tagUid)}`);
      es.onmessage = (ev)=>{
        sseActive = true;
        try{
          const data = JSON.parse(ev.data||'{}');
          if(data.updated) refreshByTag();
        }catch{}
      };
      es.onerror = ()=>{ try{es.close();}catch{} };
    }catch{}

    // C) Fallback polling if SSE not active
    if(!sseActive){
      const tm = setInterval(refreshByTag, 2000);
      setTimeout(()=>clearInterval(tm), 120000);
    }
  }

  function boot(){
    const tag = getTagUidFromPath();
    if(tag) startNfcFlow(tag);
  }

  // Expose utils globally (optional)
  window.ReagentologyAddon = { displayQty, startNfcFlow, API_BASE };

  // Boot when DOM ready
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
