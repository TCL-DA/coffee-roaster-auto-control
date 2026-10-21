/* Khung chat dùng pixel thực ngoài stage co giãn; dữ liệu mô hình chỉ hiện bằng textContent. */
(() => {
  if (window.otlAssistantOpen) return;
  const web = !!window._OTL_WEBCLONE;
  const style = document.createElement('style');
  style.textContent = `
  #ra-panel{position:fixed;inset:16px 16px 16px auto;margin:0;width:min(520px,calc(100vw - 32px));height:calc(100dvh - 32px);max-width:none;max-height:none;padding:0;border:1px solid var(--hair,#444);border-radius:16px;background:var(--panel,#16161b);color:var(--txt,#f2f2f3);font:16px/1.5 var(--f-ui,system-ui);z-index:99999;box-shadow:0 12px 50px #0006;overflow:hidden}
  #ra-panel[open]{display:flex;flex-direction:column}
  #ra-panel *{box-sizing:border-box}
  #ra-panel header,#ra-panel footer{padding:14px 18px;flex:none;background:var(--panel,#16161b)}
  #ra-panel header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--hair,#444)}
  #ra-panel h2{font-size:22px;margin:0;font-weight:600}
  #ra-panel h3{font-size:17px;margin:8px 0}
  #ra-panel button,#ra-panel input,#ra-panel select,#ra-panel textarea{font:inherit;color:inherit;border-radius:8px;border:1px solid var(--hair,#444);background:var(--inset,#222);min-height:44px;padding:8px 12px;max-width:100%}
  #ra-panel button{cursor:pointer;white-space:normal;line-height:1.3}
  #ra-panel button:disabled{opacity:.5;cursor:wait}
  #ra-panel :focus-visible{outline:2px solid var(--accent,#f2761a);outline-offset:2px}
  #ra-panel .ra-primary{background:var(--accent,#f2761a);color:var(--accent-ink,#1a0f04);font-weight:600}
  #ra-panel .ra-scroll{overflow-y:auto;overscroll-behavior:contain;flex:1;min-height:0;padding:12px 18px}
  #ra-panel .ra-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  #ra-panel .ra-message{padding:12px 14px;border:1px solid var(--hair,#444);border-radius:10px;white-space:pre-wrap;overflow-wrap:anywhere;margin-bottom:12px}
  #ra-panel .ra-user{background:var(--inset,#222)}
  #ra-panel .ra-error,#ra-error{color:var(--red-ink,#ef9999)}
  #ra-panel .ra-meta{font-size:14px;color:var(--dim,#bbb);margin:6px 0;white-space:pre-wrap}
  #ra-panel details{border-bottom:1px solid var(--hair,#444);padding:10px 0;margin-bottom:12px}
  #ra-panel summary{min-height:44px;cursor:pointer;padding:10px 0;font-weight:600}
  #ra-panel label{display:block;margin:10px 0 4px}
  #ra-panel label input,#ra-panel label select{display:block;width:100%;margin-top:4px}
  #ra-panel .ra-limits{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
  #ra-panel .ra-limits input{width:100%;min-width:0}
  #ra-panel textarea{display:block;resize:vertical;width:100%;min-height:70px;max-height:150px;margin-bottom:8px}
  #ra-panel footer{border-top:1px solid var(--hair,#444)}
  #ra-panel #ra-pending{border:1px solid var(--accent,#f2761a);padding:12px;border-radius:10px;margin:12px 0}
  #ra-panel #ra-pending[hidden]{display:none}
  #ra-panel pre{font:14px/1.5 var(--f-mono,monospace);white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0}
  #ra-indicator{position:fixed;top:8px;left:50%;transform:translateX(-50%);z-index:99998;padding:10px 16px;min-height:44px;border:1px solid var(--accent,#f2761a);border-radius:9px;background:var(--panel,#16161b);color:var(--txt,#fff);font:16px system-ui;cursor:pointer}
  @media(max-width:600px){#ra-panel{inset:0;width:100vw;height:100dvh;border-radius:0}#ra-panel header,#ra-panel footer{padding:10px 12px}#ra-panel .ra-scroll{padding:10px 12px}}
  `;
  document.head.append(style);
  const panel = document.createElement('dialog');
  panel.id = 'ra-panel';
  panel.setAttribute('aria-labelledby', 'ra-title');
  panel.innerHTML = `
    <header><h2 id="ra-title">Trợ lý Roast Lab</h2><button id="ra-close" aria-label="Đóng khung trợ lý">Đóng</button></header>
    <div class="ra-scroll">
      <p class="ra-meta" id="ra-status" role="status" aria-live="polite">Đang kết nối trợ lý…</p>
      <p class="ra-meta">Hỏi về mẻ rang, soạn hồ sơ hoặc kiểm kho. AI đọc dữ liệu khi cần; bạn quyết định quyền thay đổi.</p>
      <details id="ra-settings"><summary>Thiết lập AI</summary>
        <p class="ra-meta">Dịch vụ AI cần Internet và tài khoản API có hạn mức. Nội dung chat và kết quả công cụ cần thiết được gửi tới dịch vụ bạn chọn.</p>
        <label>Dịch vụ<select id="ra-provider"><option value="openai">OpenAI</option><option value="anthropic">Anthropic Claude</option></select></label>
        <label>Tên mô hình<input id="ra-model" maxlength="100" placeholder="Tên mô hình trong tài khoản API của bạn"></label>
        <label>Khóa API<input id="ra-key" type="password" autocomplete="off" placeholder="Để trống để giữ khóa đã lưu"></label>
        <p class="ra-meta">Khóa được mã hóa theo tài khoản Windows, không gửi tới trình duyệt LAN.</p>
        <button id="ra-save-config">Lưu thiết lập AI</button>
      </details>
      <details id="ra-permissions"><summary>Quyền của trợ lý</summary>
        <label>Chế độ<select id="ra-mode">
          <option value="A">A · Duyệt mọi thay đổi</option><option value="B">B · Tự sửa dữ liệu, lệnh máy cần duyệt</option>
          <option value="C">C · Điều khiển có giới hạn, nạp/xả cần duyệt</option><option value="D">D · Chạy kế hoạch đã duyệt</option>
        </select></label>
        <div class="ra-limits"><label>Gas tối đa (%)<input id="ra-gas" type="number" min="0" max="100" value="50"></label>
        <label>Gió tối đa (%)<input id="ra-air" type="number" min="0" max="100" value="100"></label>
        <label>Trống tối đa (%)<input id="ra-drum" type="number" min="0" max="100" value="100"></label></div>
        <p class="ra-meta">C/D cấp phiên 15 phút. D chỉ thực hiện các bước đã duyệt, tối đa 14 phút. Khi bạn điều khiển máy, AI tạm dừng; bấm Tiếp tục để giao lại. Chọn chế độ mới sẽ hủy đề xuất/kế hoạch cũ.</p>
        <button id="ra-set-mode">Áp dụng quyền cho phiên</button>
      </details>
      <details><summary>Skill nghiệp vụ</summary><div id="ra-skills"></div></details>
      <div class="ra-row"><button id="ra-new">Hội thoại mới</button><button id="ra-pause">Tạm dừng AI</button><button id="ra-resume" hidden>Tiếp tục</button></div>
      <div id="ra-messages" aria-label="Nội dung hội thoại"></div>
      <section id="ra-pending" hidden aria-labelledby="ra-pending-title"><h3 id="ra-pending-title">Chờ bạn duyệt</h3>
        <p class="ra-meta">Duyệt chỉ áp dụng cho nội dung bên dưới. Đề xuất hết hạn sau 2 phút.</p>
        <pre id="ra-proposal"></pre><div class="ra-row"><button id="ra-approve" class="ra-primary">Duyệt và thực hiện</button><button id="ra-reject">Từ chối</button></div></section>
    </div>
    <footer><p id="ra-error" role="alert"></p><label for="ra-input">Tin nhắn</label><textarea id="ra-input" maxlength="4000" placeholder="Ví dụ: phân tích mẻ gần nhất và đề nghị cải thiện"></textarea>
      <div class="ra-row"><button id="ra-send" class="ra-primary">Gửi</button><span class="ra-meta">Ctrl + Enter để gửi</span></div>
    </footer>`;
  document.body.append(panel);
  const indicator = document.createElement('button');
  indicator.id = 'ra-indicator'; indicator.hidden = true; document.body.append(indicator);
  const el = id => document.getElementById(id);
  let state = null, poll = null, lastMessages = '', pendingId = '', configLoaded = false, sending = false, lastFocus;
  async function call(action, payload = {}) {
    let result;
    if (web) {
      const token = sessionStorage.getItem('otl_webtok') || '';
      if (!token) throw new Error('Đăng nhập PIN web trước khi dùng trợ lý.');
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 12000);
      try {
        const r = await fetch('/api/v1/assistant', {method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+token}, body:JSON.stringify({action,payload}), signal:controller.signal});
        result = await r.json();
      } finally { clearTimeout(timer); }
    } else {
      const api = window.pywebview?.api;
      if (!api?.assistant_action) throw new Error('Bản app này chưa nạp trợ lý. Mở lại bản EXE chính đã cập nhật.');
      result = await api.assistant_action(action, payload);
    }
    if (!result?.ok) throw new Error(result?.err || result?.msg || 'Không thực hiện được yêu cầu.');
    return result;
  }
  const labels = {name:'Lệnh / tên',value:'Giá trị',gas:'Gas (%)',air:'Gió (%)',drum:'Trống (%)',sv:'Nhiệt đặt (°C)',vac:'Áp hút (Pa)',charge:'Nạp hạt',drop:'Xả mẻ',escape:'Xả liệu',ignite:'Đánh lửa',cool:'Làm nguội',after_s:'Sau khi duyệt (giây)',chargeT:'Nhiệt nạp (°C)',temp:'Nhiệt xả (°C)',time:'Thời gian',notes:'Ghi chú',note:'Lý do',kg:'Thay đổi tồn (kg)',qty_kg:'Khối lượng đơn (kg)',customer:'Khách hàng',profile:'Hồ sơ',id:'Mã',roast:'Mức rang'};
  function proposal(p) {
    if (p.tool === 'propose_plan') return p.args.summary+'\nThời điểm tính từ lúc bấm Duyệt:\n'+p.args.steps.map((s,i)=>`${i+1}. Sau ${s.after_s}s: ${labels[s.name]||s.name} = ${s.value}`).join('\n');
    return Object.entries(p.args).map(([k,v])=>`${labels[k]||k}: ${k==='name'?(labels[v]||v):v}`).join('\n');
  }
  function render(s) {
    state = s;
    const activePlan = s.plan?.status === 'running';
    el('ra-status').textContent = !s.configured ? 'Chưa cấu hình dịch vụ AI.' :
      s.paused ? 'AI đã tạm dừng. Bạn đang nắm quyền thao tác.' : activePlan ? `Đang chạy kế hoạch · đã gửi ${s.plan.index}/${s.plan.steps.length} bước · phiên còn ${s.grant_seconds}s` :
      s.pending ? 'Đang chờ bạn duyệt.' : s.busy ? 'AI đang xử lý… Bạn có thể tạm dừng bất kỳ lúc nào.' : `Sẵn sàng · chế độ ${s.mode} · ${s.model}`;
    el('ra-send').disabled = sending || s.busy || !!s.pending || s.paused || activePlan || !s.configured;
    el('ra-resume').hidden = !s.paused;
    el('ra-settings').hidden = web; el('ra-permissions').hidden = web;
    if (!configLoaded) {
      el('ra-provider').value=s.provider;el('ra-model').value=s.model;el('ra-mode').value=s.mode;
      configLoaded=true;
    }
    const stamp=JSON.stringify(s.messages);
    if(stamp!==lastMessages){
      const box=el('ra-messages');box.replaceChildren();
      for(const m of s.messages){const p=document.createElement('div');p.className='ra-message ra-'+m.role;
        const who=document.createElement('strong');who.textContent=m.role==='user'?'Bạn':m.role==='assistant'?'Trợ lý':'Trạng thái';
        const text=document.createElement('div');text.textContent=m.text;p.append(who,text);box.append(p);}
      lastMessages=stamp;
      // Cập nhật kho hồ sơ ở app sau kết quả công cụ, không tự chuyển màn Rang.
      if(s.messages.some(m=>m.role==='tool') && typeof window.profDiskInit==='function') window.profDiskInit();
    }
    el('ra-pending').hidden=!s.pending;
    if(s.pending?.id!==pendingId){pendingId=s.pending?.id||'';el('ra-proposal').textContent=s.pending?proposal(s.pending):'';}
    const box=el('ra-skills');if(!box.childElementCount)for(const skill of s.skills){const p=document.createElement('p');p.className='ra-meta';p.textContent=skill.description;box.append(p);}
    indicator.hidden=!(activePlan||s.paused||s.pending);
    indicator.textContent=activePlan?'AI đang chạy kế hoạch · Mở / Tạm dừng':s.pending?'AI đang chờ duyệt':'AI đang tạm dừng';
  }
  async function action(name, payload, button) {
    el('ra-error').textContent='';if(button)button.disabled=true;
    try {const s=await call(name,payload);render(s);return true;}
    catch(e){el('ra-error').textContent=e.message||'Không nhận được phản hồi. Kiểm tra trạng thái trước khi gửi lại.';return false;}
    finally {if(button)button.disabled=false;}
  }
  async function refresh(){try{render(await call('state'));}catch(e){el('ra-error').textContent=e.message;}}
  window.otlAssistantOpen=async()=>{
    lastFocus=document.activeElement;
    document.getElementById('usermenu')?.classList.remove('on');
    if(!panel.open)panel.show();
    el('ra-input').focus();await refresh();
    if(!poll)poll=setInterval(()=>{if(panel.open||state?.plan?.status==='running'||state?.busy)refresh();},1500);
  };
  indicator.onclick=window.otlAssistantOpen;
  el('ra-close').onclick=()=>{panel.close();lastFocus?.focus();};
  panel.addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();panel.close();lastFocus?.focus();}},true);
  el('ra-save-config').onclick=async()=>{const key=el('ra-key').value;el('ra-key').value='';await action('configure',{provider:el('ra-provider').value,model:el('ra-model').value,key},el('ra-save-config'));};
  el('ra-set-mode').onclick=()=>{
    for(const k of ['gas','air','drum'])if(!el('ra-'+k).reportValidity())return;
    action('mode',{mode:el('ra-mode').value,limits:{gas:Number(el('ra-gas').value),air:Number(el('ra-air').value),drum:Number(el('ra-drum').value)}},el('ra-set-mode'));
  };
  el('ra-new').onclick=()=>action('clear',{},el('ra-new'));
  el('ra-pause').onclick=()=>action('pause',{},el('ra-pause'));
  el('ra-resume').onclick=()=>action('resume',{},el('ra-resume'));
  el('ra-approve').onclick=()=>action('approve',{id:pendingId},el('ra-approve'));
  el('ra-reject').onclick=()=>action('reject',{id:pendingId},el('ra-reject'));
  async function send(){
    const input=el('ra-input'),text=input.value.trim();if(!text||sending||el('ra-send').disabled)return;
    sending=true;el('ra-send').disabled=true;
    try{if(await action('chat',{text,request_id:Date.now().toString(36)+'-'+Math.random().toString(36).slice(2)},null))input.value='';}
    finally{sending=false;if(state)render(state);}
  }
  el('ra-send').onclick=send;
  el('ra-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&e.ctrlKey){e.preventDefault();send();}});
  const menu=document.getElementById('usermenu');
  if(menu){const button=document.createElement('button');button.id='ra-open';button.className='umrow';button.textContent='Trợ lý AI';button.onclick=window.otlAssistantOpen;menu.prepend(button);}
})();
