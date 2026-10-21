# -*- coding: utf-8 -*-
"""Đo công việc nền thừa và kiểm hồi quy nhãn động, hộp biểu đồ.

Chạy: python tools/test_ui_performance.py
Đặt OTL_APP_HTML để đối chiếu bản sao trước khi sửa; không nối máy thật.
"""
import json
import os
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
APP = Path(os.environ.get("OTL_APP_HTML", ROOT / "OTL Roast Lab.html"))


def main():
    errors = []

    def check(name, ok, detail=None):
        print(("ĐẠT " if ok else "HỎNG ") + name,
              json.dumps(detail, ensure_ascii=False) if detail is not None else "")
        if not ok:
            errors.append(name)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        js_errors = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))
        page.goto(APP.as_uri())
        page.wait_for_timeout(1800)
        # Bỏ màn đăng nhập trong trang thử riêng; không đọc/sửa tài khoản thật.
        page.evaluate("""() => {
          document.getElementById('login').classList.remove('on');
          gotoTab('rang');
          window.__perf={fullScans:0,scans:0,scanMs:0,mutations:0};
          const scan=a11yQuet;
          window.a11yQuet=function(root){const t=performance.now();
            try{return scan(root);}finally{
              __perf.scans++;if(root===document)__perf.fullScans++;
              __perf.scanMs+=performance.now()-t;
            }};
          new MutationObserver(ms=>__perf.mutations+=ms.length)
            .observe(document.body,{childList:true,subtree:true});
        }""")
        page.wait_for_timeout(5000)
        idle = page.evaluate("() => __perf")
        check("Không quét toàn trang khi nhàn rỗi", idle["fullScans"] == 0, idle)

        repeated = page.evaluate("""() => {
          const el=document.getElementById('liveBT');txt('liveBT','123.4');
          const o=new MutationObserver(()=>{});o.observe(el,{childList:true});
          for(let i=0;i<1000;i++)txt('liveBT','123.4');
          const mutations=o.takeRecords().length;o.disconnect();
          txt('liveBT',null);const empty=el.textContent==='';
          txt('liveBT',0);const zero=el.textContent==='0';
          txt('liveBT','—');const missing=el.classList.contains('nodata');
          txt('liveBT',123.4);const restored=!el.classList.contains('nodata');
          return {mutations,empty,zero,missing,restored};
        }""")
        check("1.000 lần ghi cùng giá trị không thay DOM", repeated["mutations"] == 0, repeated)
        check("Giữ số 0, giá trị rỗng và dấu thiếu dữ liệu",
              all(repeated[k] for k in ("empty", "zero", "missing", "restored")))

        canvas_resets = page.evaluate("""() => {
          const d=Object.getOwnPropertyDescriptor(HTMLCanvasElement.prototype,'width');
          const h=Object.getOwnPropertyDescriptor(HTMLCanvasElement.prototype,'height');
          let n=0;
          Object.defineProperty(HTMLCanvasElement.prototype,'width',{configurable:true,
            get:d.get,set(v){n++;return d.set.call(this,v);}});
          Object.defineProperty(HTMLCanvasElement.prototype,'height',{configurable:true,
            get:h.get,set(v){n++;return h.set.call(this,v);}});
          for(let i=0;i<10;i++)drawChart();
          Object.defineProperty(HTMLCanvasElement.prototype,'width',d);
          Object.defineProperty(HTMLCanvasElement.prototype,'height',h);
          return n;
        }""")
        check("Vẽ lặp cùng kích thước không cấp lại backing store", canvas_resets <= 2,
              canvas_resets)

        account_save = page.evaluate("""() => {
          const oldSession=session,oldImage=personalImage,oldStamp=UX.accountStamp,
            oldDirty=UX.accountDirty,oldMap=localStorage.getItem('otl_personal_accounts');
          session={name:'__perf__'};personalImage='x'.repeat(120000);
          UX.accountStamp='';UX.accountDirty=true;
          const stringify=JSON.stringify;let styleCalls=0;
          JSON.stringify=function(v,...args){
            if(v&&typeof v==='object'&&Object.prototype.hasOwnProperty.call(v,'wallpaper'))styleCalls++;
            return stringify.call(this,v,...args);
          };
          uxAccountSave();for(let i=0;i<20;i++)uxAccountSave();
          JSON.stringify=stringify;
          if(oldMap==null)localStorage.removeItem('otl_personal_accounts');
          else localStorage.setItem('otl_personal_accounts',oldMap);
          session=oldSession;personalImage=oldImage;UX.accountStamp=oldStamp;UX.accountDirty=oldDirty;
          return {styleCalls,dirtyAfterSave:UX.accountDirty};
        }""")
        check("Không stringify lại gói phong cách khi không đổi",
              account_save["styleCalls"] == 1 and account_save["dirtyAfterSave"] is False,
              account_save)

        page.evaluate("""() => {
          const box=document.createElement('div');box.id='perfFixture';
          document.body.append(box);
          const control=document.createElement('div');control.id='perfControl';
          control.setAttribute('onclick','window.__perfClicks=(window.__perfClicks||0)+1');
          control.textContent='Kiểm bàn phím';box.append(control);
          const field=document.createElement('div');field.className='pefield';
          field.innerHTML='<label class="pel">Nhiệt thử</label>';box.append(field);
          window.__perfField=field;
          const dialog=document.createElement('div');dialog.id='perfDialog';dialog.className='overlay';
          dialog.innerHTML='<div><h2>Hộp thử</h2><button>Đóng</button></div>';box.append(dialog);
        }""")
        page.wait_for_timeout(150)
        page.evaluate("""() => {
          const input=document.createElement('input');input.id='perfInput';__perfField.append(input);
        }""")
        page.wait_for_timeout(150)
        labels = page.evaluate("""() => {
          const control=document.getElementById('perfControl'),input=document.getElementById('perfInput');
          const label=document.getElementById(input.getAttribute('aria-labelledby'));
          const dialog=document.querySelector('#perfDialog [role=dialog]');
          return {tab:control.getAttribute('tabindex'),role:control.getAttribute('role'),
            label:label?.textContent,dialog:!!dialog,
            title:dialog&&document.getElementById(dialog.getAttribute('aria-labelledby'))?.textContent};
        }""")
        check("Phần tử động, nhãn thêm sau và dialog vẫn truy cập được",
              labels == {"tab": "0", "role": "button", "label": "Nhiệt thử",
                         "dialog": True, "title": "Hộp thử"}, labels)
        page.locator('#perfControl').focus()
        page.keyboard.press('Enter')
        page.keyboard.press('Space')
        check("Enter và Space vẫn kích hoạt điều khiển động",
              page.evaluate("()=>window.__perfClicks") == 2)
        page.evaluate("()=>document.getElementById('perfFixture').remove()")

        # Canvas ẩn không được tạo vòng RAF vô hạn, kể cả nhiều yêu cầu cùng lúc.
        page.evaluate("""() => {
          window.__hiddenDraws=0;const draw=drawBatchCurve;
          window.drawBatchCurve=function(...args){__hiddenDraws++;return draw(...args);};
          for(let i=0;i<5;i++)drawBatchCurve('bdCanvas',[]);
        }""")
        page.wait_for_timeout(1100)
        hidden = page.evaluate("()=>__hiddenDraws")
        check("Năm yêu cầu vẽ canvas đóng không lặp theo frame", hidden <= 10, hidden)

        # Phản hồi API cũ về sau khi đóng không được cập nhật thống kê hay bắt đầu vẽ.
        page.evaluate("""() => {
          window.__statsResolve=null;
          window.pywebview={api:{
            link_snapshot:async()=>({state:'disconnected',data:null}),
            db_batch_stats:()=>new Promise(r=>window.__statsResolve=r),
            db_batch_curve:async()=>({t:[0,60],bt:[100,150],et:[110,160]}),
          }};
          window.__batchJob=openBatch(901);closeBatch();
          window.__beforeCloseDraws=__hiddenDraws;
          window.__beforeCloseStats=document.getElementById('bdStats').innerHTML;
        }""")
        page.evaluate("""async()=>{
          __statsResolve({total_sec:60,drop_temp:150});await __batchJob;
        }""")
        page.wait_for_timeout(250)
        stale = page.evaluate("""()=>({
          extraDraws:__hiddenDraws-__beforeCloseDraws,
          statsUnchanged:document.getElementById('bdStats').innerHTML===__beforeCloseStats,
          closed:!document.getElementById('batchDetail').classList.contains('on')
        })""")
        check("Đóng chi tiết khi API còn chờ bỏ kết quả cũ",
              stale == {"extraDraws": 0, "statsUnchanged": True, "closed": True}, stale)

        page.evaluate("""async()=>{
          pywebview.api.db_batch_stats=async()=>({total_sec:60,drop_temp:150});
          await openBatch(902);
        }""")
        page.wait_for_timeout(400)
        reopened = page.evaluate("""()=>{
          const cv=document.getElementById('bdCanvas');
          return {open:document.getElementById('batchDetail').classList.contains('on'),
            stats:document.getElementById('bdStats').textContent.includes('150'),
            pixels:cv.width>0&&cv.height>0&&cv.getContext('2d')
              .getImageData(0,0,cv.width,cv.height).data.some(v=>v!==0)};
        }""")
        check("Mở lại chi tiết vẫn có số liệu và đường cong", all(reopened.values()), reopened)

        page.evaluate("""()=>{
          closeBatch();window.__originalZoomOpen=zoomOpen;
          window.zoomOpen=(source,open)=>setTimeout(open,80);
          openBatch(903);closeBatch();
        }""")
        page.wait_for_timeout(180)
        check("Chuyển cảnh đang chờ không mở lại hộp vừa đóng",
              page.evaluate("()=>!document.getElementById('batchDetail').classList.contains('on')"))
        page.evaluate("async()=>{await openBatch(904);}")
        page.wait_for_timeout(150)
        check("API trả nhanh trước chuyển cảnh vẫn hiện thống kê",
              page.evaluate("""()=>document.getElementById('batchDetail').classList.contains('on')&&
                document.getElementById('bdStats').textContent.includes('150')"""))
        page.evaluate("()=>{window.zoomOpen=__originalZoomOpen;}")

        page.evaluate("""()=>{
          closeBatch();HIST_SEL.clear();HIST_SEL.add(901);HIST_SEL.add(902);
          pywebview.api.db_batches_curves=()=>new Promise(r=>window.__compareResolve=r);
          window.__compareJob=openCompare();closeCompare();
          window.__beforeCompareDraws=__hiddenDraws;
          window.__beforeCompareTable=document.getElementById('cmpTable').innerHTML;
        }""")
        page.evaluate("""async()=>{__compareResolve({});await __compareJob;}""")
        compare = page.evaluate("""()=>({
          extraDraws:__hiddenDraws-__beforeCompareDraws,
          tableUnchanged:document.getElementById('cmpTable').innerHTML===__beforeCompareTable
        })""")
        check("Đóng so sánh khi API còn chờ bỏ kết quả cũ",
              compare == {"extraDraws": 0, "tableUnchanged": True}, compare)

        # Hai luồng dùng chung hộp so sánh phải cùng bỏ lượt tải đã bị thay thế.
        page.evaluate("""()=>{
          window.__oldLoadProfiles=loadProfiles;
          window.loadProfiles=()=>[{name:'Hồ sơ cũ A',bgBatch:801},{name:'Hồ sơ cũ B',bgBatch:802}];
          UX.profileSel.clear();UX.profileSel.add(0);UX.profileSel.add(1);
          UX.profileCurves.clear();window.__profileResolvers=[];
          pywebview.api.db_batch_curve=()=>new Promise(r=>__profileResolvers.push(r));
          window.__profileJob=uxCompareProfiles();closeCompare();
          pywebview.api.db_batches_curves=async()=>({});
          window.__currentCompareJob=openCompare();
        }""")
        page.evaluate("""async()=>{
          await __currentCompareJob;
          window.__currentLegend=document.getElementById('cmpLegend').innerHTML;
          window.__currentTable=document.getElementById('cmpTable').innerHTML;
          __profileResolvers.forEach(r=>r({t:[0,60],bt:[100,150]}));await __profileJob;
        }""")
        check("Phản hồi hồ sơ cũ không ghi đè lượt so sánh mẻ mới",
              page.evaluate("""()=>document.getElementById('cmpLegend').innerHTML===__currentLegend&&
                document.getElementById('cmpTable').innerHTML===__currentTable"""))
        page.evaluate("()=>{closeCompare();window.loadProfiles=__oldLoadProfiles;}")
        check("Không phát sinh lỗi JavaScript", not js_errors, js_errors)
        browser.close()
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
