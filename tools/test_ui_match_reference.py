"""Kiểm màn Rang theo mẫu và lưu ảnh tạm để kiểm tra nội bộ."""
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={"width":1440,"height":800})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("""
      window.__sent=[];
      window.__machine={bt:196.4,et:218.7,ror_bt:9.4,ror_et:7.2,gas:45,air:55,drum:62,
        drum_hz:35,sv:206,vac:-120,step:4,t_roast:0,phase:{dry:true,mai:true,dev:true},
        flags:{auto:false,gas:true,flame:true,pc_control:true},hb:1};
      window.pywebview={api:{
        link_snapshot:async()=>({state:'connected',mode:'pclink',age_ms:1,data:window.__machine}),
        link_write:async(name,value)=>{window.__sent.push([name,value]);return {ok:true,name,value}},
        link_config:async()=>({port:'FAKE',baud:9600}),
        link_begin_batch:async()=>({ok:true}),toggle_fullscreen:async()=>null
      }};
    """)
    page.goto((Path(__file__).resolve().parent.parent/'OTL Roast Lab.html').as_uri())
    page.evaluate("session={name:'Master',role:'master',perms:{}};document.getElementById('login').classList.remove('on');setTheme('dark');setAccent('ember');gotoTab('rang');setView('detail',true);setDevPin(1);loadProfile(1);startRoast();")
    page.wait_for_timeout(900)
    page.evaluate("updateBadge();window.__machine.step=9;window.__machine.t_roast=595;dsTick()")
    page.wait_for_timeout(700)
    for w,h in [(1440,800),(1366,768),(2560,1440)]:
        page.set_viewport_size({'width':w,'height':h})
        page.wait_for_timeout(180)
        for selector in ['#liveBT','#liveET','#ovBurner','#ovAir','#ovDrum','#btnIgnite','#btnDrop','#btnCool']:
            box=page.locator(selector).bounding_box()
            assert box and box['x']>=-1 and box['y']>=-1 and box['x']+box['width']<=w+1 and box['y']+box['height']<=h+1,(w,selector,box)
        assert page.locator('.chartwrap').bounding_box()['height']>h*.35
        page.locator('.match-more summary').click()
        for selector in ['#btnCharge','#modeBtn','#liveETror','#uxFocus']:
            assert page.locator(selector).is_visible(),selector
        # Từ 14/09/2026 (thợ rang dùng thử): Tăng nhiệt + Gas đang VẼ mặc định nên nhãn
        # nằm ở chú giải thanh đầu; ABT/ΔET/áp hút ít dùng vẫn ở menu "Thao tác".
        assert page.locator('.match-more-panel [data-ser="rorET"]').count()==1,'ΔET phải còn trong menu Thao tác'
        assert page.locator('.match-charthead .chartleg [data-ser="burner"]').is_visible(),'thiếu nhãn Gas ở chú giải'
        ror=page.locator('.match-charthead .chartleg [data-ser="ror"]')
        before=ror.get_attribute('class')
        ror.click()
        assert ror.get_attribute('class')!=before,'trạng thái ẩn/hiện RoR không cập nhật'
        ror.click()
        page.locator('.match-more summary').click()
    page.set_viewport_size({'width':1440,'height':800})
    page.locator('.outrow.air .pm[data-d="1"]').click()
    page.wait_for_timeout(200)
    assert page.evaluate("__sent.some(x=>x[0]==='air')"),'lệnh gió chưa đến cầu máy'
    # Nhập trực tiếp phải giữ đúng lệnh và giá trị sau khi đổi bố cục.
    for output,command,value in [('burner','gas',46),('air','air',57),('drum','drum',64)]:
        page.locator('.outrow.'+output+' .oinfo').click()
        editor=page.locator('.outrow.'+output+' input.ovedit')
        editor.fill(str(value))
        editor.press('Enter')
        page.wait_for_timeout(150)
        assert page.evaluate('([name,value])=>__sent.some(x=>x[0]===name&&x[1]===value)',[command,value]),command
    # Hủy nhập không được gửi thêm lệnh.
    page.locator('.outrow.drum .oinfo').click()
    editor=page.locator('.outrow.drum input.ovedit')
    editor.fill('99')
    count=page.evaluate('__sent.length')
    editor.press('Escape')
    assert page.evaluate('__sent.length')==count
    page.evaluate("DS.state='error';uiClearMachineValues()")
    assert page.locator('#liveBT').inner_text()=='—'
    page.evaluate('dsTick()')
    page.wait_for_timeout(600)
    page.evaluate("setView('simple',true)")
    page.wait_for_timeout(550)
    assert page.locator('.toolbar>.match-more').is_visible()
    page.evaluate("setView('detail',true)")
    page.wait_for_timeout(550)
    page.screenshot(path=str(Path(tempfile.gettempdir())/'otl-match-internal.png'))
    print('ERRORS',errors)
    print(page.evaluate("""()=>Object.fromEntries(['.chartcol','.match-charthead','.chartwrap','.rightcol','.bthero','.etcard','.clockcard','#btnIgnite','.od-aux','.outcard','.toolbar'].map(s=>{const r=document.querySelector('#pane-rang '+s).getBoundingClientRect();return [s,{x:r.x,y:r.y,w:r.width,h:r.height}]}))"""))
    assert not errors,errors
    browser.close()
