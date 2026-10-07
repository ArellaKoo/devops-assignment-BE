from pathlib import Path
import json
from playwright.sync_api import sync_playwright, expect
OUT=Path(__file__).parent/'frontend-quality-final'; OUT.mkdir(exist_ok=True)
with sync_playwright() as pw:
 browser=pw.chromium.launch()
 findings=[]
 for role,email,home in [('diner','diner.one@skipq.test','/diner/stalls'),('vendor','vendor.one@skipq.test','/vendor/menu')]:
  context=browser.new_context(viewport={'width':1280,'height':720})
  page=context.new_page(); errors=[]; page.on('pageerror', lambda err: errors.append(str(err)))
  page.goto('http://127.0.0.1:5173/login'); page.get_by_label('Email').fill(email); page.get_by_label('Password').fill('SkipQDemo2026!'); page.get_by_role('button',name='Sign in',exact=True).click(); expect(page).to_have_url('http://127.0.0.1:5173'+home)
  page.wait_for_function("document.querySelector('section .list-group-item')")
  paths= ['/diner/stalls','/diner/cart','/diner/checkout','/diner/orders'] if role=='diner' else ['/vendor/menu','/vendor/menu/new','/vendor/orders']
  links=page.locator('section a').evaluate_all('(links)=>links.map(a=>a.pathname)')
  if role=='diner': paths.insert(1,next(path for path in links if path.startswith('/diner/stalls/')))
  page.goto('http://127.0.0.1:5173/'+role+'/orders'); page.wait_for_function("document.querySelector('section .list-group-item a')"); paths.append(page.locator('section .list-group-item a').first.get_attribute('href'))
  for width in [1280,375,320]:
   page.set_viewport_size({'width':width,'height':720})
   for index,path in enumerate(paths):
    page.goto('http://127.0.0.1:5173'+path); page.wait_for_function("document.querySelector('section') && !/Loading/.test(document.querySelector('section').innerText)")
    name=f'{role}-{width}-{index}'; page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
    result=page.evaluate("""()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,nav:[...document.querySelectorAll('nav a')].map(a=>({label:a.innerText,color:getComputedStyle(a).color,bg:getComputedStyle(a.closest('nav')).backgroundColor})),brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).map(i=>i.alt),overflows:[...document.querySelectorAll('section *,nav *')].filter(e=>e.getBoundingClientRect().right>innerWidth+2).slice(0,8).map(e=>({tag:e.tagName,text:e.innerText?.slice(0,70)}))})""")
    findings.append({'path':path,'capture':name,**result})
  findings.append({'role':role,'pageErrors':errors}); context.close()
 browser.close(); (OUT/'audit.json').write_text(json.dumps(findings,indent=2)); print('Layout captures:',len([r for r in findings if 'capture' in r]),'Overflow paths:',[r['path'] for r in findings if r.get('scroll',0)>r.get('width',0)],'Page errors:',sum(len(r.get('pageErrors',[])) for r in findings))
