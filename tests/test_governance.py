import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from pathlib import Path
import sys
import urllib.request
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from governance import Engine
from app import make_server

class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.e=Engine(self.temp.name)
    def tearDown(self): self.e.close(); self.temp.cleanup()
    def count(self): return self.e.tool.request({'action':'stats'})['executions']
    def pending(self):
        grant=self.e.new_grant()
        body={'action':'case.update','case_id':'CASE-104','status':'Under review','expected_version':1}
        result=self.e.invoke(self.e.token('coordinator'),grant,body)
        return grant,body,result['approval_id']
    def test_happy_path_masks_fields(self):
        result=self.e.scenario('happy')
        self.assertEqual(result['tool_executions_delta'],2)
        payload=result['steps'][-1]['result']
        self.assertEqual(payload['account_number'],'[MASKED]'); self.assertNotIn('customer',payload)
        self.assertNotIn('9988776655',json.dumps(self.e.snapshot()))
    def test_unknown_identity_has_no_execution(self):
        r=self.e.scenario('unknown'); self.assertEqual(r['steps'][0]['reason'],'INVALID_AGENT_IDENTITY'); self.assertEqual(self.count(),0)
    def test_resource_scope_has_no_execution(self):
        self.assertEqual(self.e.scenario('scope')['steps'][0]['reason'],'RESOURCE_OUTSIDE_GRANT'); self.assertEqual(self.count(),0)
    def test_destination_denied_without_external_request(self):
        self.assertEqual(self.e.scenario('exfiltration')['steps'][0]['reason'],'UNAPPROVED_DESTINATION'); self.assertEqual(self.count(),0)
    def test_delegation_cannot_expand(self):
        self.assertEqual(self.e.scenario('delegation')['steps'][0]['reason'],'DELEGATION_SCOPE_EXPANSION'); self.assertEqual(self.count(),0)
    def test_grant_expiry(self):
        self.assertEqual(self.e.scenario('expiry')['steps'][0]['reason'],'GRANT_EXPIRED'); self.assertEqual(self.count(),0)
    def test_parent_suspension_revokes_child(self):
        result=self.e.scenario('revocation'); self.assertEqual(result['steps'][-1]['reason'],'GRANT_REVOKED'); self.assertEqual(self.count(),0)
    def test_wrong_grant_subject(self):
        g=self.e.new_grant(); r=self.e.invoke(self.e.token('researcher'),g,{'action':'knowledge.read','case_id':'CASE-104'})
        self.assertEqual(r['reason'],'WRONG_GRANT_SUBJECT')
    def test_purpose_and_field_validation(self):
        g=self.e.new_grant(); token=self.e.token('coordinator')
        self.assertEqual(self.e.invoke(token,g,{'action':'case.read','case_id':'CASE-104','purpose':'bulk_export'})['reason'],'PURPOSE_MISMATCH')
        self.assertEqual(self.e.invoke(token,g,{'action':'case.read','case_id':'CASE-104','extra':'anything'})['reason'],'UNAPPROVED_FIELD')
    def test_direct_tool_rejects_missing_credential(self):
        r=self.e.scenario('bypass'); self.assertEqual(r['steps'][0]['reason'],'GATEWAY_CREDENTIAL_REQUIRED'); self.assertEqual(self.count(),0)
    def test_approval_executes_once(self):
        _,_,a=self.pending(); self.assertEqual(self.count(),0)
        self.assertEqual(self.e.approve(a,'demo-reviewer')['outcome'],'allowed')
        self.assertEqual(self.e.approve(a,'demo-reviewer')['reason'],'APPROVAL_ALREADY_USED_OR_CLOSED'); self.assertEqual(self.count(),1)
    def test_separation_of_duties_and_role(self):
        _,_,a=self.pending()
        self.assertEqual(self.e.approve(a,'demo-employee')['reason'],'SELF_APPROVAL_DENIED')
        self.assertEqual(self.e.approve(a,'someone','employee')['reason'],'REVIEWER_ROLE_REQUIRED'); self.assertEqual(self.count(),0)
    def test_approval_binds_exact_request(self):
        _,body,a=self.pending(); body['status']='Resolved'
        self.assertEqual(self.e.approve(a,'demo-reviewer',override_body=body)['reason'],'APPROVAL_REQUEST_CHANGED'); self.assertEqual(self.count(),0)
    def test_approval_rechecks_revocation(self):
        _,_,a=self.pending(); self.e.suspend('coordinator')
        self.assertEqual(self.e.approve(a,'demo-reviewer')['reason'],'GRANT_REVOKED'); self.assertEqual(self.count(),0)
    def test_stale_case_version_not_overwritten(self):
        _,_,a=self.pending(); _,_,b=self.pending()
        self.assertEqual(self.e.approve(a,'demo-reviewer')['outcome'],'allowed')
        self.assertEqual(self.e.approve(b,'demo-reviewer')['outcome'],'failed'); self.assertEqual(self.count(),1)
    def test_concurrent_approval_has_one_side_effect(self):
        _,_,a=self.pending()
        with ThreadPoolExecutor(2) as pool: results=list(pool.map(lambda _:self.e.approve(a,'demo-reviewer'),range(2)))
        self.assertEqual(sum(r['outcome']=='allowed' for r in results),1); self.assertEqual(self.count(),1)
    def test_tool_idempotency(self):
        payload={'action':'case.update','case_id':'CASE-104','status':'Under review','expected_version':1,'execution_key':'test-key'}
        first=self.e.tool.request(payload); second=self.e.tool.request(payload)
        self.assertEqual(first,second); self.assertEqual(self.count(),1)
    def test_cycle_denied(self):
        g=self.e.new_grant(); self.assertEqual(self.e.delegate(self.e.token('coordinator'),g,'coordinator',['case.read'])['reason'],'DELEGATION_CYCLE')
    def test_reactivation_does_not_revive_old_grant(self):
        g=self.e.new_grant(); self.e.suspend('coordinator'); self.e.reactivate('coordinator')
        self.assertEqual(self.e.valid_grant(g)[1],'GRANT_REVOKED'); self.assertIsNone(self.e.valid_grant(self.e.new_grant())[1])
    def test_operator_role_required(self):
        self.assertEqual(self.e.suspend('coordinator','employee')['reason'],'OPERATOR_ROLE_REQUIRED')
        self.assertEqual(self.e.agent('coordinator')['state'],'active')
    def test_unavailable_tool_returns_unknown(self):
        self.e.tool.close(); g=self.e.new_grant()
        r=self.e.invoke(self.e.token('coordinator'),g,{'action':'case.read','case_id':'CASE-104'})
        self.assertEqual(r['outcome'],'unknown')

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.e=Engine(self.temp.name)
        self.server=make_server(self.e,0); self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
        self.client=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(CookieJar()))
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.e.close(); self.temp.cleanup()
    def request(self,path,body=None,csrf='',origin=None):
        headers={}
        if body is not None: headers={'Content-Type':'application/json','X-CSRF-Token':csrf}
        if origin: headers['Origin']=origin
        req=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        try:
            with self.client.open(req) as r: return r.status,r.read()
        except urllib.error.HTTPError as e: return e.code,e.read()
    def test_static_assets_are_local_and_available(self):
        for path in ('/','/app.js','/style.css'): self.assertEqual(self.request(path)[0],200)
        self.assertNotIn(b'https://',self.request('/')[1])
    def test_session_and_csrf_required(self):
        self.assertEqual(self.request('/api/state')[0],401)
        status,raw=self.request('/api/session',{'persona':'employee'}); session=json.loads(raw)
        self.assertEqual(status,200)
        self.assertEqual(self.request('/api/scenario',{'name':'happy'})[0],403)
        self.assertEqual(self.request('/api/scenario',{'name':'happy'},session['csrf'])[0],200)
    def test_cross_origin_session_creation_blocked(self):
        self.assertEqual(self.request('/api/session',{'persona':'operator'},origin='https://unapproved.invalid')[0],403)
    def test_http_role_not_taken_from_body(self):
        _,raw=self.request('/api/session',{'persona':'employee'}); session=json.loads(raw)
        _,raw=self.request('/api/suspend',{'agent':'coordinator','role':'operator'},session['csrf'])
        self.assertEqual(json.loads(raw)['reason'],'OPERATOR_ROLE_REQUIRED')

if __name__=='__main__': unittest.main(verbosity=2)
