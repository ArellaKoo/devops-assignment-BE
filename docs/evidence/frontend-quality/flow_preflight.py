"""Guard the adapted local flow checks before any seed/mutation/cleanup."""
import os
from pathlib import Path
import requests
from pymongo import MongoClient


def verify():
    os.environ['MONGODB_DB']='skipq_system_test'
    backend=Path(__file__).resolve().parents[3]
    client=MongoClient('mongodb://127.0.0.1:27017')
    try:
        db=client['skipq_system_test']
        assert db.orders.count_documents({})==9 and db.orders.count_documents({'queue_number':{'$regex':'^Q-seed-'}})==9, 'Flow checks require canonical guarded seed orders, no user-created orders'
        stall=db.vendors.find_one({'name':'Charcoal Grill'})
        response=requests.post('http://127.0.0.1:5001/api/user/gettoken',json={'email':'vendor.one@skipq.test','password':'SkipQDemo2026!'},timeout=10)
        response.raise_for_status()
        response=requests.get('http://127.0.0.1:5001/api/vendor/stall',headers={'Authorization':'Bearer '+response.json()['token']},timeout=10)
        response.raise_for_status()
        assert response.json()['stall']['id']==str(stall['_id']), 'Running API must use skipq_system_test, not development data'
    finally:client.close()
    return str(backend)
