"""Supplementary frontend quality regressions, separate from assessed Q6(a).

Real UI logins, real API menus/carts and isolated browser contexts. Deliberate
held/faulted/empty HTTP responses exercise pending/error/queue recovery.
Only the guarded seed actor's cart and one availability flag may be changed;
original BSON documents are restored and orders must remain unchanged.
No H01-H11 implementation and no frontend unit/component test suite.
"""
import argparse
import json
import os
import re
from pathlib import Path

import requests
from playwright.sync_api import expect, sync_playwright
from pymongo import MongoClient

API='http://127.0.0.1:5001'
WEB='http://127.0.0.1:5173'
PASSWORD='SkipQDemo2026!'
ITEM='Charcoal Chicken Rice'
OUT=Path(__file__).parent


def login(page,role='diner',expected=None):
    page.goto(WEB+'/login')
    page.get_by_label('Email').fill(role+'.one@skipq.test')
    page.get_by_label('Password').fill(PASSWORD)
    page.get_by_role('button',name='Sign in',exact=True).click()
    expect(page).to_have_url(WEB+(expected or ('/diner/stalls' if role=='diner' else '/vendor/menu')))


def contrast(page):
    def linear(v):
        v=v/255
        return v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4
    colors=page.locator('nav a').evaluate_all("links=>links.map(a=>({label:a.innerText,fg:getComputedStyle(a).color,bg:getComputedStyle(a.closest('nav')).backgroundColor}))")
    assert colors,'Persona navigation must exist'
    for row in colors:
        lum=[]
        for name in ['fg','bg']:
            rgb=[int(n) for n in re.findall(r'\d+',row[name])[:3]]
            lum.append(sum(linear(v)*weight for v,weight in zip(rgb,[.2126,.7152,.0722])))
        ratio=(max(lum)+.05)/(min(lum)+.05)
        assert ratio>=4.5,f"Unreadable navigation: {row['label']} contrast {ratio:.2f}:1"


def pending_login(page):
    page.goto(WEB+'/login')
    page.get_by_label('Email').fill('diner.one@skipq.test')
    page.get_by_label('Password').fill(PASSWORD)
    held=[]
    page._quality_held=held
    page.route('**/api/user/gettoken',lambda route: held.append(route) if route.request.method=='POST' else route.continue_())
    button=page.get_by_role('button',name='Sign in',exact=True)
    button.evaluate('button=>{button.click();button.click();}')
    expect(page.get_by_role('button',name='Signing in…',exact=True)).to_be_disabled(timeout=2500)
    page.screenshot(path=str(OUT/'signin-pending-diagnostic.png'))
    assert len(held)==1,f'Expected one sign-in request, got {len(held)}'
    held.pop().continue_()
    expect(page).to_have_url(WEB+'/diner/stalls')


def return_path(page):
    page.goto(WEB+'/diner/orders')
    expect(page).to_have_url(WEB+'/login')
    page.get_by_label('Email').fill('diner.one@skipq.test')
    page.get_by_label('Password').fill(PASSWORD)
    page.get_by_role('button',name='Sign in',exact=True).click()
    expect(page).to_have_url(WEB+'/diner/orders',timeout=2500)


def failed_load(page):
    login(page)
    page.route('**/api/diner/cart',lambda route: route.abort('connectionfailed'))
    page.goto(WEB+'/diner/cart')
    expect(page.get_by_role('alert').first).to_contain_text('could not be reached')
    expect(page.get_by_text('Loading your cart…',exact=True)).to_have_count(0,timeout=2500)
    retry=page.get_by_role('button',name='Try again',exact=True)
    expect(retry).to_be_visible()
    page.screenshot(path=str(OUT/'failed-cart-read-diagnostic.png'))
    page.unroute('**/api/diner/cart')
    retry.click()
    expect(page.get_by_text(ITEM,exact=True)).to_be_visible()


def failed_read(page,role,path,endpoint):
    login(page,role)
    page.route('**'+endpoint,lambda route:route.abort('connectionfailed'))
    page.goto(WEB+path)
    expect(page.get_by_role('alert').first).to_contain_text('could not be reached')
    expect(page.locator('main')).not_to_contain_text('Loading')
    retry=page.get_by_role('button',name='Try again',exact=True)
    expect(retry).to_be_visible()
    page.unroute('**'+endpoint)
    retry.click()
    expect(retry).to_have_count(0)


def sold_out(page,db,item,checkout=False,removed=False):
    db.menu_items.update_one({'_id':item['_id']},{'$set':{'is_active':False} if removed else {'is_available':False}})
    try:
        login(page)
        page.goto(WEB+('/diner/checkout' if checkout else '/diner/cart'))
        expect(page.get_by_text('Sold out',exact=True).first).to_be_visible(timeout=2500)
        if checkout:
            expect(page.get_by_role('button',name='Pay $6.50',exact=True)).to_be_disabled()
        else:
            expect(page.get_by_role('button',name='Increase quantity of '+ITEM,exact=True)).to_be_disabled()
            expect(page.get_by_role('button',name='Remove '+ITEM+' from the cart',exact=True)).to_be_enabled()
            assert page.get_by_role('link',name='Continue to checkout',exact=True).count()==0,'Do not offer checkout for a known sold-out cart'
    finally:
        db.menu_items.replace_one({'_id':item['_id']},item)


def closed_cart(page,db,stall,checkout=False):
    db.vendors.update_one({'_id':stall['_id']},{'$set':{'is_open':False}})
    try:
        login(page)
        page.goto(WEB+('/diner/checkout' if checkout else '/diner/cart'))
        expect(page.get_by_text('Charcoal Grill is currently closed.',exact=True)).to_be_visible(timeout=2500)
        if checkout:
            expect(page.get_by_role('button',name='Pay $6.50',exact=True)).to_be_disabled()
        else:
            expect(page.get_by_role('button',name='Increase quantity of '+ITEM,exact=True)).to_be_disabled()
            expect(page.get_by_role('button',name='Remove '+ITEM+' from the cart',exact=True)).to_be_enabled()
            assert page.get_by_role('link',name='Continue to checkout',exact=True).count()==0
    finally:
        db.vendors.replace_one({'_id':stall['_id']},stall)


def pending_checkout(page):
    login(page)
    page.goto(WEB+'/diner/checkout')
    pay=page.get_by_role('button',name='Pay $6.50',exact=True)
    expect(pay).to_be_visible()
    held=[]
    page._quality_held=held
    page.route('**/api/diner/orders',lambda route: held.append(route) if route.request.method=='POST' else route.continue_())
    pay.click()
    expect(page.get_by_role('button',name='Processing payment…',exact=True)).to_be_disabled()
    expect(page.get_by_label('Card',exact=True)).to_be_disabled(timeout=2500)
    expect(page.get_by_label('Simulate this payment failing (demo control)')).to_be_disabled()
    expect(page.get_by_role('button',name='Refresh',exact=True)).to_be_disabled()
    assert page.get_by_role('link',name='Edit cart',exact=True).count()==0,'Do not offer editing during payment'
    assert len(held)==1
    held.pop().abort('connectionfailed')
    expect(page.get_by_role('alert').first).to_contain_text('could not be reached')
    expect(page.get_by_label('Card',exact=True)).to_be_enabled()


def pending_vendor(page):
    login(page,'vendor')
    row=page.locator('.list-group-item').filter(has_text=ITEM)
    button=row.get_by_role('button',name='Mark sold out',exact=True)
    expect(button).to_be_visible()
    held=[]
    page._quality_held=held
    page.route('**/api/vendor/menu/*',lambda route: held.append(route) if route.request.method=='PATCH' else route.continue_())
    button.evaluate('button=>{button.click();button.click();}')
    expect(button).to_be_disabled()
    assert len(held)==1,f'Overlapping vendor requests: {len(held)}'
    held.pop().abort('connectionfailed')
    expect(button).to_be_enabled()


def incoming_queue(page):
    login(page,'vendor')
    show_actual=[False]
    def initial_empty(route):
        if not show_actual[0]:
            route.fulfill(status=200,content_type='application/json',headers={'Access-Control-Allow-Origin':WEB},body=json.dumps({'items':[]}))
        else:
            route.continue_()
    page.route('**/api/vendor/orders',initial_empty)
    page.goto(WEB+'/vendor/orders')
    expect(page.get_by_text('No paid orders for this stall yet.',exact=True)).to_be_visible()
    # All initial/StrictMode requests see an empty queue, then incoming
    # real orders become visible only if the mounted queue keeps polling.
    show_actual[0]=True
    expect(page.locator('.list-group-item').first).to_be_visible(timeout=6500)


def mobile_cart(page):
    login(page)
    page.set_viewport_size({'width':375,'height':720})
    page.goto(WEB+'/diner/cart')
    expect(page.get_by_text(ITEM,exact=True)).to_be_visible()
    sizes=page.evaluate('({viewport:innerWidth,content:document.documentElement.scrollWidth})')
    assert sizes['content']<=sizes['viewport']+1,f'Cart needs horizontal scrolling: {sizes}'


def root_entry(page):
    page.goto(WEB+'/')
    expect(page.get_by_role('heading',name='SkipQ sign-in',exact=True)).to_be_visible(timeout=2500)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only');args=parser.parse_args()
    database=os.environ.get('SKIPQ_SYSTEM_DB','skipq_system_test')
    assert re.fullmatch(r'skipq_system_test(?:_[a-z0-9]+)?',database)
    client=MongoClient(os.environ.get('MONGODB_HOST','mongodb://127.0.0.1:27017'))
    db=client[database];user=db.users.find_one({'email':'diner.one@skipq.test'})
    assert user is not None
    stall=db.vendors.find_one({'name':'Charcoal Grill'})
    item=db.menu_items.find_one({'vendor':stall['_id'],'name':ITEM})
    assert item and item['is_available'] and stall['is_open']
    original_cart=db.carts.find_one({'diner':user['_id']}); original_orders=list(db.orders.find({}))
    response=requests.post(API+'/api/user/gettoken',json={'email':'diner.one@skipq.test','password':PASSWORD},timeout=10); response.raise_for_status()
    headers={'Authorization':'Bearer '+response.json()['token']}
    diner_order=db.orders.find_one({'diner':user['_id']})
    vendor_order=db.orders.find_one({'vendor':stall['_id']})
    checks={
      'root_entry':root_entry,'nav_diner':lambda p:(login(p),contrast(p)),
      'nav_vendor':lambda p:(login(p,'vendor'),contrast(p)),
      'pending_login':pending_login,'return_path':return_path,'failed_load':failed_load,
      'cart_sold_out':lambda p:sold_out(p,db,item),
      'checkout_sold_out':lambda p:sold_out(p,db,item,True),
      'cart_removed':lambda p:sold_out(p,db,item,removed=True),
      'checkout_removed':lambda p:sold_out(p,db,item,True,True),
      'cart_closed':lambda p:closed_cart(p,db,stall),
      'checkout_closed':lambda p:closed_cart(p,db,stall,True),
      'pending_checkout':pending_checkout,'pending_vendor':pending_vendor,
      'incoming_queue':incoming_queue,'mobile_cart':mobile_cart}
    for name,role,path,endpoint in [
        ('read_stalls','diner','/diner/stalls','/api/diner/stalls'),
        ('read_menu','diner','/diner/stalls/'+str(stall['_id']),'/api/diner/stalls/'+str(stall['_id'])+'/menu'),
        ('read_checkout','diner','/diner/checkout','/api/diner/cart'),
        ('read_diner_orders','diner','/diner/orders','/api/diner/orders?view=all'),
        ('read_diner_detail','diner','/diner/orders/'+str(diner_order['_id']),'/api/diner/orders/'+str(diner_order['_id'])),
        ('read_vendor_menu','vendor','/vendor/menu','/api/vendor/menu'),
        ('read_vendor_orders','vendor','/vendor/orders','/api/vendor/orders'),
        ('read_vendor_detail','vendor','/vendor/orders/'+str(vendor_order['_id']),'/api/vendor/orders/'+str(vendor_order['_id'])),
    ]:
        checks[name]=lambda p,role=role,path=path,endpoint=endpoint:failed_read(p,role,path,endpoint)
    results=[]
    try:
        db.carts.delete_many({'diner':user['_id']})
        response=requests.post(API+'/api/diner/cart/items',headers=headers,json={'item_id':str(item['_id']),'quantity':1},timeout=10)
        assert response.status_code==201,response.text
        assert db.carts.find_one({'diner':user['_id']})['items'][0]['quantity']==1,'API must target the guarded DB'
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            try:
                for name,check in checks.items():
                    if args.only and not re.search(args.only,name):continue
                    context=browser.new_context(viewport={'width':1280,'height':720});page=context.new_page();page.set_default_timeout(10000)
                    try:
                        check(page);print('PASS '+name,flush=True);results.append({'check':name,'result':'PASS'})
                    except Exception as error:
                        print('FAIL '+name+': '+str(error),flush=True);results.append({'check':name,'result':'FAIL','detail':str(error)})
                    finally:
                        for route in getattr(page,'_quality_held',[]):
                            try:route.abort('connectionfailed')
                            except Exception:pass
                        context.close()
            finally:browser.close()
    finally:
        db.menu_items.replace_one({'_id':item['_id']},item)
        db.vendors.replace_one({'_id':stall['_id']},stall)
        db.carts.delete_many({'diner':user['_id']})
        if original_cart is not None:db.carts.insert_one(original_cart)
        assert db.carts.find_one({'diner':user['_id']})==original_cart,'Cart restoration failed'
        assert list(db.orders.find({}))==original_orders,'Order records changed'
        client.close(); print('CLEANUP PASS: original cart/item restored; order records unchanged',flush=True)
    return int(any(result['result']=='FAIL' for result in results))

if __name__=='__main__':raise SystemExit(main())
