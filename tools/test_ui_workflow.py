"""Kiểm hồi quy luồng rang và cá nhân hóa, dùng cầu giả, không điều khiển máy."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
APP = Path(__file__).resolve().parent.parent / 'OTL Roast Lab.html'


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1366, 'height': 768})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(APP.as_uri())
        page.evaluate("document.getElementById('login').classList.remove('on');SND.on=false;gotoTab('hoso')")
        page.locator('#uxProfSearch').fill('khong-co-ho-so-nay')
        assert page.locator('.profcard').count() == 0
        page.locator('#uxProfSearch').fill('')
        page.locator('.ux-select input').nth(0).check()
        page.locator('.ux-select input').nth(1).check()
        page.locator('#uxProfCompare').click()
        assert page.locator('#batchCompare').is_visible()
        assert page.locator('#cmpTable tbody tr').count() == 4
        page.evaluate("closeCompare();loadProfile(0);R.phase='RUNNING'")
        profile = page.evaluate('R.profName')
        page.evaluate('loadProfile(1)')
        assert page.evaluate('R.profName') == profile
        assert page.evaluate('R.phase') == 'RUNNING'
        print('ĐẠT: tìm hồ sơ, so sánh 2 hồ sơ, chặn đổi hồ sơ giữa mẻ')

        page.evaluate("""async()=>{
          R.phase='IDLE';window.pywebview={api:{db_batch_list:async()=>[]}};
          await renderHistory();
        }""")
        assert page.locator('#histBody .code').count() == 0
        assert 'Chưa có mẻ' in page.locator('#uxHistStatus').inner_text()
        page.evaluate("window.pywebview.api.db_batch_list=async()=>{throw Error('offline')};renderHistory()")
        page.wait_for_function("document.getElementById('uxHistStatus').textContent.includes('Không đọc được')")
        assert page.locator('#histBody .code').count() == 0
        page.evaluate("""async()=>{
          window.historyRequests=[];
          window.pywebview.api.db_batch_list=async(...args)=>{historyRequests.push(args);return Array.from({length:51},(_,i)=>({id:args[4]+i+1,code:'#B-'+i,prof_name:'Mẻ kiểm tra',drop_sec:600,drop_temp:200,dev_pct:15,started_at:'2026-09-06 10:00:00',status:'DONE',live:1}));};
          await renderHistory();uxHistoryPage(1);
        }""")
        page.wait_for_function('historyRequests.at(-1)[4]===50')
        page.evaluate("document.getElementById('uxHistSearch').value='Đậm';uxHistoryFilter(true)")
        page.wait_for_function("historyRequests.at(-1)[1]==='Đậm'&&historyRequests.at(-1)[4]===0")
        page.evaluate("""async()=>{
          let old;window.pywebview.api.db_batch_list=()=>new Promise(r=>old=r);
          const pending=renderHistory();window.pywebview.api.db_batch_list=async()=>[];
          await renderHistory();old([{id:999,prof_name:'Kết quả cũ'}]);await pending;
        }""")
        assert 'Kết quả cũ' not in page.locator('#histBody').inner_text()
        print('ĐẠT: kho rỗng/lỗi không hiện mẻ mẫu; phân trang, lọc và chống kết quả cũ ghi đè')

        page.evaluate("""()=>{
          window.pywebview.api.link_snapshot=()=>new Promise(()=>{});
          DS.state='connected';DS.snap={bt:123.4,et:140,drum:50,gas:30,air:40,vac:0,ror_bt:0,ror_et:0,flags:{}};uxPreheat();phStart();
        }""")
        assert page.locator('#phCur').inner_text() == '123.4°C'
        assert page.evaluate('PH.timer') is None
        page.evaluate("DS.state='error';uxPreheat()")
        assert page.locator('#phCur').inner_text() == '—'
        page.evaluate("""async()=>{
          DS.state='connected';DS.snap={gas:40,flags:{}};LIC_BLOCK=false;
          window.pywebview.api.link_write=async()=>({ok:true});await machCmd('gas',40);
          uxConfirmSnapshot();
        }""")
        assert page.evaluate('UX.command.state') == 'queued'
        page.evaluate('UX.snapshotSeq++;uxConfirmSnapshot()')
        assert page.evaluate('UX.command.state') == 'confirmed'
        page.evaluate("""async()=>{
          await machCmd('ignite',0);UX.snapshotSeq++;DS.snap.flags={gas:null};uxConfirmSnapshot();
        }""")
        assert page.evaluate('UX.command.state') == 'queued'
        page.evaluate('UX.command.at-=11000;uxTick()')
        assert page.evaluate('UX.command.state') == 'timeout'
        page.evaluate("""()=>{const old=uxCommandStart('gas',20);uxCommandStart('gas',50);uxCommandUpdate('gas','failed',old)}""")
        assert page.evaluate('UX.command.state') == 'sending'
        print('ĐẠT: làm nóng theo BT thật; xác nhận lệnh cần snapshot mới, không coi cờ null là TẮT')

        page.evaluate("""async()=>{
          DS.state='error';DS.snap=null;
          window.pywebview.api.db_batch_finish=async()=>({ok:true,id:42});
          window.pywebview.api.db_batch_list=async()=>[];
          R.phase='RUNNING';R.elapsed=0;R.mileT={};seriesReset();finishRoast();
        }""")
        assert page.locator('#doneTemp').inner_text() == '—'
        assert page.locator('#doneDev').inner_text() == '—'
        page.evaluate("""async()=>{
          R.phase='RUNNING';R.elapsed=600;R.mileT={FCs:480};
          Object.assign(SERIES,{t:[0,100,200,300,400,500,600],bt:[160,90,120,150,180,195,200],et:[180,110,140,170,200,210,220],gas:[30,30,30,30,30,30,30],air:[40,40,40,40,40,40,40],drum:[50,50,50,50,50,50,50]});
          finishRoast();await Promise.resolve();
        }""")
        page.wait_for_function('UX.completed.id===42')
        assert page.locator('#doneDev').inner_text() == '20%'
        assert page.locator('#uxDoneCurve svg').count() == 1
        count = page.evaluate('loadProfiles().length')
        page.evaluate('uxDoneBaseline()')
        assert page.evaluate('loadProfiles().length') == count + 1
        assert page.evaluate('loadProfiles().at(-1).bgBatch') == 42
        page.evaluate('uxDoneBaseline()')
        assert page.evaluate('loadProfiles().length') == count + 1
        page.evaluate("""async()=>{
          document.getElementById('uxDoneNote').value='Ghi chú phải giữ';
          window.pywebview.api.inv_cup_add=async()=>({ok:false});await uxDoneNoteSave();
        }""")
        assert page.locator('#uxDoneNote').input_value() == 'Ghi chú phải giữ'
        page.evaluate("""async()=>{
          window.pywebview.api.inv_cup_add=async d=>{window.savedNote=d;return {ok:true}};await uxDoneNoteSave();
        }""")
        assert page.evaluate('savedNote.target_id') == 42
        assert page.locator('#uxDoneNote').input_value() == ''
        print('ĐẠT: tổng kết không bịa nhiệt/DTR, lưu baseline không trùng, ghi chú lỗi vẫn được giữ')

        page.evaluate("personalOpen();window.goodStyle=uxStyleCapture()")
        assert page.evaluate("async()=>{const s=uxStyleCapture();s.personal.opacity=1000;return await uxStyleApply(s)}") is False
        page.evaluate("""async()=>{
          const s=uxStyleCapture();s.theme='dark';s.accent='teal';s.personal.wall='forest';
          s.otl_cfg2='không được nhập';await uxStyleApply(s);
        }""")
        assert page.evaluate('PERSONAL.wall') == 'forest'
        assert page.evaluate("localStorage.getItem('otl_cfg2')") != 'không được nhập'
        page.locator('#uxStyleName').fill('Phong cách <riêng>')
        page.evaluate('uxStyleSave()')
        assert page.locator('#uxSavedStyles').inner_text().startswith('Phong cách <riêng>')
        assert page.locator('#uxSavedStyles rieng').count() == 0
        page.evaluate("""async()=>{
          session={name:'Thợ A'};uxAccountLoad();setTheme('light');uxAccountSave();
          session={name:'Thợ B'};uxAccountLoad();setTheme('dark');uxAccountSave();
          session={name:'Thợ A'};uxAccountLoad();
        }""")
        page.wait_for_function("document.documentElement.dataset.theme==='light'")
        print('ĐẠT: gói phong cách được kiểm tra, không nhập cấu hình máy, nhớ theo tài khoản')
        page.evaluate("""async()=>{
          window.pywebview.api.style_export=async bundle=>{window.exportedStyle=bundle;return {ok:true}};
          await uxStyleExport();
        }""")
        assert page.evaluate('exportedStyle.format') == 'otl-style'
        assert page.evaluate("Object.keys(exportedStyle.style).includes('otl_cfg2')") is False
        page.evaluate("""async()=>{
          const before=personalRead('otl_theme'),set=Storage.prototype.setItem;
          Storage.prototype.setItem=function(k,v){if(k===PERSONAL_KEY)throw new DOMException('quota','QuotaExceededError');return set.call(this,k,v)};
          const v=uxStyleCapture();v.theme=before==='dark'?'light':'dark';window.quotaResult=await uxStyleApply(v);
          Storage.prototype.setItem=set;window.quotaKept=personalRead('otl_theme')===before;
        }""")
        assert page.evaluate('quotaResult') is False
        assert page.evaluate('quotaKept') is True
        print('ĐẠT: xuất qua cầu desktop; nhập phong cách gặp lỗi dung lượng khôi phục cài đặt cũ')
        page.evaluate("personalClose();session=null;window.pywebview=null;R.phase='IDLE';loadProfile(0);setRoastPhase('RUNNING');gotoTab('rang')")
        for width, height in [(1920, 1080), (1366, 768), (1280, 800)]:
            page.set_viewport_size({'width': width, 'height': height})
            for extra in (False, True):
                page.evaluate("""on=>{
                  document.getElementById('vacCard').style.display=on?'':'none';
                  document.getElementById('burnerFlame').classList.toggle('show',on);
                }""", extra)
                page.wait_for_timeout(100)
                result = page.evaluate("""()=>{
                  const parent=document.querySelector('.rangbody').getBoundingClientRect();
                  return [...document.querySelectorAll('.outrow .pm,#btnIgnite,.clockcard')].every(el=>{
                    const r=el.getBoundingClientRect();return r.bottom<=parent.bottom+1&&r.top>=parent.top&&r.height>=43.9;
                  });
                }""")
                assert result, (width, height, extra)
        print('ĐẠT: đồng hồ và nút điều khiển không bị cắt, kể cả khi bật áp hút/chỉ báo lửa')
        assert not errors, errors
        browser.close()
    print('TẤT CẢ ĐẠT')


if __name__ == '__main__':
    main()
