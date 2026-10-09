"""Synthetic tools. Loopback only; separate process; gateway credential required."""
import hmac
import json
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ToolStore:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,status TEXT,version INTEGER);
            INSERT OR IGNORE INTO cases VALUES('CASE-104','Open',1);
            CREATE TABLE IF NOT EXISTS executions(id TEXT PRIMARY KEY,result TEXT);
        ''')
        self.db.commit()

    def call(self, body):
        with self.lock:
            action = body.get('action')
            if action == 'stats':
                row = self.db.execute('SELECT status,version FROM cases WHERE id=?',('CASE-104',)).fetchone()
                return {'executions': self.db.execute('SELECT COUNT(*) FROM executions').fetchone()[0],
                        'case_status':row[0], 'case_version':row[1]}
            key = body.get('execution_key')
            if not isinstance(key,str) or not key:
                raise ValueError('Execution key required')
            old = self.db.execute('SELECT result FROM executions WHERE id=?',(key,)).fetchone()
            if old:
                return json.loads(old[0])
            if action == 'knowledge.read':
                result = {'article':'Case follow-up guidance','guidance':'Verify the case, summarize approved fields, and obtain reviewer approval before updating status.'}
            elif action in ('case.read','case.update'):
                if body.get('case_id') != 'CASE-104':
                    raise ValueError('Unknown synthetic case')
                row = self.db.execute('SELECT status,version FROM cases WHERE id=?',('CASE-104',)).fetchone()
                if action == 'case.update':
                    if body.get('expected_version') != row[1]:
                        raise ValueError('Case version changed; authorize again')
                    status = body.get('status')
                    if status not in ('Under review','Resolved'):
                        raise ValueError('Status is not allowed')
                    self.db.execute('UPDATE cases SET status=?,version=version+1 WHERE id=?',(status,'CASE-104'))
                    result = {'case_id':'CASE-104','status':status,'version':row[1]+1}
                else:
                    result = {'case_id':'CASE-104','customer':'Synthetic Customer A','account_number':'SYNTHETIC-9988776655',
                              'status':row[0],'version':row[1],'summary':'Synthetic request to review a service charge.'}
            else:
                raise ValueError('Unknown tool operation')
            self.db.execute('INSERT INTO executions VALUES(?,?)',(key,json.dumps(result)))
            self.db.commit()
            return result


def main():
    # Bootstrap credential travels over the parent/child pipe, never command-line arguments.
    config = json.loads(sys.stdin.readline())
    credential = config['credential']
    store = ToolStore(config['database'])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def respond(self,code,value):
            raw=json.dumps(value).encode()
            self.send_response(code); self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def do_POST(self):
            if self.path != '/invoke':
                return self.respond(404,{'error':'Not found'})
            if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+credential):
                return self.respond(403,{'error':'GATEWAY_CREDENTIAL_REQUIRED'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<2 or n>8192: raise ValueError('Invalid payload size')
                body=json.loads(self.rfile.read(n))
                if not isinstance(body,dict): raise ValueError('Object required')
                result=store.call(body)
                self.respond(200,result)
            except (ValueError,TypeError,json.JSONDecodeError) as e:
                store.db.rollback()
                self.respond(409,{'error':str(e)})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    print(json.dumps({'port':server.server_address[1]}),flush=True)
    server.serve_forever()

if __name__=='__main__': main()
