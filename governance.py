"""Offline governance demo. Standard library only; synthetic data, explicit limits."""
import hashlib
import json
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

POLICY_VERSION='demo-policy-1'
AGENTS=[
 ('coordinator','Case coordinator','Demo Service Team','case_assistance',['knowledge.read','case.read','case.update']),
 ('researcher','Knowledge agent','Demo Knowledge Team','case_assistance',['knowledge.read']),
 ('casewriter','Case update agent','Demo Operations Team','case_assistance',['case.read','case.update']),
]

def uid(prefix): return prefix+'-'+secrets.token_hex(6)
def canonical(data): return json.dumps(data,sort_keys=True,separators=(',',':'))
def digest(data): return hashlib.sha256(canonical(data).encode()).hexdigest()

class ToolClient:
    def __init__(self,directory):
        self.credential=secrets.token_urlsafe(32)
        self.process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('tool_server.py'))],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.process.stdin.write(json.dumps({'credential':self.credential,'database':str(Path(directory)/'tools.sqlite3')})+'\n')
        self.process.stdin.flush()
        ready=self.process.stdout.readline()
        if not ready:
            raise RuntimeError('Local tool process could not start. Verify local Python/loopback is permitted.')
        self.url='http://127.0.0.1:'+str(json.loads(ready)['port'])+'/invoke'
        # Ignore environment proxy settings; all tool requests stay on loopback.
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(self,body,authenticated=True):
        headers={'Content-Type':'application/json'}
        if authenticated: headers['Authorization']='Bearer '+self.credential
        req=urllib.request.Request(self.url,data=json.dumps(body).encode(),headers=headers,method='POST')
        try:
            with self.opener.open(req,timeout=5) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            return {'error':json.load(e).get('error','TOOL_ERROR'),'http_status':e.code}
    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=3)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
        for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
            if stream: stream.close()

class Engine:
    def __init__(self,directory):
        self.directory=Path(directory); self.directory.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.db=sqlite3.connect(str(self.directory/'governance.sqlite3'),check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,name TEXT,owner TEXT,purpose TEXT,actions TEXT,state TEXT);
          CREATE TABLE IF NOT EXISTS grants(id TEXT PRIMARY KEY,agent TEXT,parent TEXT,actions TEXT,case_id TEXT,expires REAL,revoked INTEGER,depth INTEGER,run TEXT);
          CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY,agent TEXT,grant_id TEXT,body TEXT,digest TEXT,requester TEXT,expires REAL,state TEXT,result TEXT,policy TEXT);
          CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE,at REAL,kind TEXT,agent TEXT,run TEXT,decision TEXT,reason TEXT,details TEXT);
        ''')
        for agent,name,owner,purpose,actions in AGENTS:
            self.db.execute('INSERT OR IGNORE INTO agents VALUES(?,?,?,?,?,?)',(agent,name,owner,purpose,json.dumps(actions),'active'))
        # A restarted demo requires fresh task authority. Do not silently resume pending writes.
        self.db.execute('UPDATE grants SET revoked=1')
        self.db.execute("UPDATE approvals SET state='expired' WHERE state='pending'")
        self.db.execute("UPDATE approvals SET state='unknown' WHERE state='executing'")
        self.db.commit()
        self.tokens={secrets.token_urlsafe(32):a[0] for a in AGENTS}
        self.tool=ToolClient(self.directory)
        self.event('system.started',details={'policy':POLICY_VERSION,'mode':'offline-scripted','network_isolation':'not_configured'})
    def close(self):
        self.tool.close(); self.db.close()
    def token(self,agent):
        return next(token for token,subject in self.tokens.items() if subject==agent)
    def event(self,kind,agent='',run='',decision='',reason='',details=None):
        self.db.execute('INSERT INTO events(id,at,kind,agent,run,decision,reason,details) VALUES(?,?,?,?,?,?,?,?)',
            (uid('ev'),time.time(),kind,agent,run,decision,reason,json.dumps(details or {})))
        self.db.commit()
    def agent(self,agent):
        return self.db.execute('SELECT * FROM agents WHERE id=?',(agent,)).fetchone()
    def new_grant(self,agent='coordinator',actions=None,case_id='CASE-104',ttl=300):
        with self.lock:
            row=self.agent(agent)
            if row is None or row['state']!='active': raise ValueError('Agent not active')
            actions=actions if actions is not None else json.loads(row['actions'])
            if not set(actions)<=set(json.loads(row['actions'])): raise ValueError('Scope exceeds agent eligibility')
            grant,run=uid('grant'),uid('run')
            self.db.execute('INSERT INTO grants VALUES(?,?,?,?,?,?,?,?,?)',(grant,agent,None,json.dumps(actions),case_id,time.time()+ttl,0,0,run))
            self.event('task.started',agent,run,details={'grant':grant,'purpose':row['purpose'],'actions':actions,'case_id':case_id,'requester':'demo-employee'})
            return grant
    def valid_grant(self,grant_id,subject=None):
        grant=self.db.execute('SELECT * FROM grants WHERE id=?',(grant_id,)).fetchone()
        if grant is None: return None,'UNKNOWN_GRANT'
        if subject is not None and grant['agent']!=subject: return grant,'WRONG_GRANT_SUBJECT'
        current=grant; seen=set()
        while current:
            if current['id'] in seen: return grant,'DELEGATION_CYCLE'
            seen.add(current['id'])
            if current['revoked']: return grant,'GRANT_REVOKED'
            if current['expires']<=time.time(): return grant,'GRANT_EXPIRED'
            record=self.agent(current['agent'])
            if record is None or record['state']!='active': return grant,'AGENT_SUSPENDED'
            if current['parent']:
                current=self.db.execute('SELECT * FROM grants WHERE id=?',(current['parent'],)).fetchone()
                if current is None: return grant,'PARENT_GRANT_MISSING'
            else: current=None
        return grant,None
    def deny(self,reason,agent='',grant=None,details=None):
        decision=uid('decision'); run=grant['run'] if grant else ''
        self.event('decision.denied',agent,run,decision,reason,details)
        return {'outcome':'denied','reason':reason,'decision_id':decision,'run_id':run,'policy_version':POLICY_VERSION}
    def delegate(self,token,parent_id,child,actions):
        with self.lock:
            subject=self.tokens.get(token)
            if not subject: return self.deny('INVALID_AGENT_IDENTITY')
            parent,err=self.valid_grant(parent_id,subject)
            if err: return self.deny(err,subject,parent)
            row=self.agent(child)
            if row is None or row['state']!='active': return self.deny('CHILD_NOT_ACTIVE',subject,parent)
            if parent['depth']>=2: return self.deny('DELEGATION_DEPTH',subject,parent)
            current=parent
            while current:
                if current['agent']==child: return self.deny('DELEGATION_CYCLE',subject,parent)
                current=self.db.execute('SELECT * FROM grants WHERE id=?',(current['parent'],)).fetchone() if current['parent'] else None
            if not set(actions)<=set(json.loads(parent['actions'])) or not set(actions)<=set(json.loads(row['actions'])):
                return self.deny('DELEGATION_SCOPE_EXPANSION',subject,parent)
            grant,run=uid('grant'),uid('run')
            self.db.execute('INSERT INTO grants VALUES(?,?,?,?,?,?,?,?,?)',(grant,child,parent_id,json.dumps(actions),parent['case_id'],parent['expires'],0,parent['depth']+1,run))
            self.event('delegation.created',subject,parent['run'],details={'child_agent':child,'child_run':run,'grant':grant,'parent_grant':parent_id,'actions':actions})
            return {'outcome':'allowed','grant_id':grant,'run_id':run}
    def validate(self,token,grant_id,body):
        subject=self.tokens.get(token)
        if not subject: return '',None,'INVALID_AGENT_IDENTITY'
        grant,err=self.valid_grant(grant_id,subject)
        if err: return subject,grant,err
        if not isinstance(body,dict): return subject,grant,'INVALID_SCHEMA'
        action=body.get('action')
        if body.get('destination','internal')!='internal': return subject,grant,'UNAPPROVED_DESTINATION'
        if body.get('purpose','case_assistance')!='case_assistance': return subject,grant,'PURPOSE_MISMATCH'
        fields={'action','case_id','destination','purpose'}
        if action=='case.update': fields|={'status','expected_version'}
        if set(body)-fields: return subject,grant,'UNAPPROVED_FIELD'
        if action not in json.loads(grant['actions']): return subject,grant,'ACTION_OUTSIDE_GRANT'
        if body.get('case_id')!=grant['case_id']: return subject,grant,'RESOURCE_OUTSIDE_GRANT'
        if action=='case.update' and (body.get('status') not in ('Under review','Resolved') or type(body.get('expected_version')) is not int):
            return subject,grant,'INVALID_UPDATE'
        return subject,grant,None
    def invoke(self,token,grant_id,body,requester='demo-employee'):
        with self.lock:
            subject,grant,err=self.validate(token,grant_id,body)
            if err: return self.deny(err,subject,grant)
            decision=uid('decision')
            if body['action']=='case.update':
                approval=uid('approval')
                binding={'agent':subject,'grant':grant_id,'body':body,'policy':POLICY_VERSION}
                self.db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?,?,?)',(approval,subject,grant_id,canonical(body),digest(binding),requester,time.time()+600,'pending',None,POLICY_VERSION))
                self.event('decision.approval_required',subject,grant['run'],decision,'CASE_WRITE_REVIEW',{'approval_id':approval,'action':'case.update','case_id':body['case_id'],'proposed_status':body['status']})
                return {'outcome':'requires_approval','approval_id':approval,'decision_id':decision,'run_id':grant['run'],'reason':'CASE_WRITE_REVIEW'}
            self.event('decision.allowed',subject,grant['run'],decision,'PURPOSE_SCOPE_ALLOWED',{'action':body['action'],'policy':POLICY_VERSION})
            return self.execute(subject,grant,body,decision,uid('execution'))
    def execute(self,subject,grant,body,decision,key):
        self.event('tool.dispatch',subject,grant['run'],decision,details={'action':body['action'],'execution_key':key})
        try: result=self.tool.request({**body,'execution_key':key})
        except (OSError,TimeoutError,ValueError):
            self.event('tool.unknown',subject,grant['run'],decision,'TOOL_UNAVAILABLE',{'execution_key':key})
            return {'outcome':'unknown','reason':'TOOL_UNAVAILABLE','decision_id':decision}
        if result.get('error'):
            self.event('tool.failed',subject,grant['run'],decision,'TOOL_REJECTED',{'execution_key':key})
            return {'outcome':'failed','reason':'TOOL_REJECTED','decision_id':decision}
        if body['action']=='case.read':
            # Field projection is enforced before the response reaches the scripted agent or UI.
            result={k:result[k] for k in ('case_id','status','version','summary')}
            result['account_number']='[MASKED]'
            self.event('data.masked',subject,grant['run'],decision,'RESTRICTED_FIELDS_FILTERED',{'fields':['customer','account_number']})
        self.event('tool.completed',subject,grant['run'],decision,'SUCCESS',{'action':body['action'],'execution_key':key})
        return {'outcome':'allowed','decision_id':decision,'run_id':grant['run'],'result':result}
    def approve(self,approval_id,reviewer,role='reviewer',override_body=None):
        with self.lock:
            a=self.db.execute('SELECT * FROM approvals WHERE id=?',(approval_id,)).fetchone()
            if a is None: return self.deny('UNKNOWN_APPROVAL')
            if role!='reviewer': return self.deny('REVIEWER_ROLE_REQUIRED')
            if reviewer==a['requester']: return self.deny('SELF_APPROVAL_DENIED')
            if a['state']!='pending': return self.deny('APPROVAL_ALREADY_USED_OR_CLOSED')
            if a['expires']<=time.time(): return self.deny('APPROVAL_EXPIRED')
            body=json.loads(a['body']) if override_body is None else override_body
            binding={'agent':a['agent'],'grant':a['grant_id'],'body':body,'policy':POLICY_VERSION}
            if digest(binding)!=a['digest']: return self.deny('APPROVAL_REQUEST_CHANGED')
            subject,grant,err=self.validate(self.token(a['agent']),a['grant_id'],body)
            if err: return self.deny(err,subject,grant)
            decision=uid('decision')
            self.db.execute("UPDATE approvals SET state='executing' WHERE id=?",(approval_id,))
            self.event('approval.accepted',subject,grant['run'],decision,details={'approval_id':approval_id,'reviewer':reviewer,'policy':POLICY_VERSION})
            result=self.execute(subject,grant,body,decision,approval_id)
            state={'allowed':'succeeded','failed':'failed'}.get(result['outcome'],'unknown')
            self.db.execute('UPDATE approvals SET state=?,result=? WHERE id=?',(state,canonical(result),approval_id)); self.db.commit()
            return result
    def suspend(self,agent,role='operator'):
        with self.lock:
            if role!='operator': return self.deny('OPERATOR_ROLE_REQUIRED')
            if self.agent(agent) is None: return self.deny('UNKNOWN_AGENT')
            self.db.execute("UPDATE agents SET state='suspended' WHERE id=?",(agent,))
            self.db.execute('UPDATE grants SET revoked=1 WHERE agent=?',(agent,))
            self.event('agent.suspended',agent,reason='DEMO_OPERATOR_ACTION')
            return {'outcome':'suspended','agent':agent}
    def reactivate(self,agent,role='operator'):
        with self.lock:
            if role!='operator': return self.deny('OPERATOR_ROLE_REQUIRED')
            if self.agent(agent) is None: return self.deny('UNKNOWN_AGENT')
            self.db.execute("UPDATE agents SET state='active' WHERE id=?",(agent,))
            self.event('agent.activated',agent,reason='DEMO_OPERATOR_REVIEW')
            return {'outcome':'active','agent':agent,'note':'Previous grants remain revoked'}
    def scenario(self,name):
        with self.lock:
            before=self.tool.request({'action':'stats'})['executions']
            token=self.token('coordinator'); steps=[]
            if name=='bypass':
                response=self.tool.request({'action':'case.update','case_id':'CASE-104','status':'Resolved','expected_version':1,'execution_key':uid('bypass')},False)
                self.event('bypass.blocked',reason=response.get('error','UNEXPECTED'),details={'http_status':response.get('http_status')})
                steps=[{'outcome':'denied' if response.get('http_status')==403 else 'failed','reason':response.get('error','UNEXPECTED')}]
            elif name=='unknown':
                steps=[self.invoke('invalid-credential','invalid-grant',{'action':'case.read'})]
            else:
                try: grant=self.new_grant()
                except ValueError: return {'scenario':name,'steps':[self.deny('AGENT_SUSPENDED','coordinator')],'tool_executions_delta':0}
                read={'action':'case.read','case_id':'CASE-104'}
                if name=='happy':
                    child=self.delegate(token,grant,'researcher',['knowledge.read']); steps.append(child)
                    if child['outcome']=='allowed': steps.append(self.invoke(self.token('researcher'),child['grant_id'],{'action':'knowledge.read','case_id':'CASE-104'}))
                    steps.append(self.invoke(token,grant,read))
                elif name=='approval':
                    child=self.delegate(token,grant,'casewriter',['case.update']); steps.append(child)
                    version=self.tool.request({'action':'stats'})['case_version']
                    if child['outcome']=='allowed': steps.append(self.invoke(self.token('casewriter'),child['grant_id'],{'action':'case.update','case_id':'CASE-104','status':'Under review','expected_version':version}))
                elif name=='exfiltration': steps=[self.invoke(token,grant,{**read,'destination':'unapproved-external'})]
                elif name=='scope': steps=[self.invoke(token,grant,{**read,'case_id':'CASE-999'})]
                elif name=='delegation': steps=[self.delegate(token,grant,'researcher',['case.update'])]
                elif name=='expiry':
                    self.db.execute('UPDATE grants SET expires=? WHERE id=?',(time.time()-1,grant)); self.db.commit()
                    steps=[self.invoke(token,grant,read)]
                elif name=='revocation':
                    child=self.delegate(token,grant,'researcher',['knowledge.read']); steps.append(child)
                    steps.append(self.suspend('coordinator'))
                    if child['outcome']=='allowed': steps.append(self.invoke(self.token('researcher'),child['grant_id'],{'action':'knowledge.read','case_id':'CASE-104'}))
                else: raise ValueError('Unknown scenario')
            after=self.tool.request({'action':'stats'})['executions']
            return {'scenario':name,'steps':steps,'tool_executions_delta':after-before,
                    'boundary':'application credential check; network isolation not configured'}
    def snapshot(self):
        with self.lock:
            agents=[dict(r) for r in self.db.execute('SELECT * FROM agents')]
            for a in agents: a['actions']=json.loads(a['actions'])
            approvals=[dict(r) for r in self.db.execute('SELECT id,agent,body,requester,expires,state FROM approvals ORDER BY rowid DESC LIMIT 50')]
            for a in approvals: a['body']=json.loads(a['body'])
            events=[dict(r) for r in self.db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT 150')]
            for e in events: e['details']=json.loads(e['details'])
            return {'agents':agents,'approvals':approvals,'events':events,'tool':self.tool.request({'action':'stats'}),
                    'policy':POLICY_VERSION,'mode':'Offline scripted agents','network_isolation':False,
                    'counts':{'events':self.db.execute('SELECT COUNT(*) FROM events').fetchone()[0],
                              'denied':self.db.execute("SELECT COUNT(*) FROM events WHERE kind IN ('decision.denied','bypass.blocked')").fetchone()[0]}}

