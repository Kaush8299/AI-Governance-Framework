"""Local demonstration server. Not a production web server or enterprise identity system."""
import argparse
import json
import secrets
import sys
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from governance import Engine

ROOT=Path(__file__).resolve().parent
SCENARIOS={'happy','approval','exfiltration','scope','delegation','expiry','revocation','bypass','unknown'}
PERSONAS={'employee':('demo-employee','employee'),'reviewer':('demo-reviewer','reviewer'),
          'operator':('demo-operator','operator'),'auditor':('demo-auditor','auditor')}

def make_server(engine,port=8765):
    sessions={}; session_lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        server_version='GovernanceDemo/0.2'
        def log_message(self,*args): pass
        def send(self,code,value,content_type='application/json',cookie=None):
            raw=value if isinstance(value,bytes) else json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type',content_type); self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if cookie: self.send_header('Set-Cookie',cookie)
            self.end_headers(); self.wfile.write(raw)
        def valid_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def session(self):
            try:
                cookies=SimpleCookie(self.headers.get('Cookie',''))
                sid=cookies['demo_session'].value if 'demo_session' in cookies else ''
            except Exception: return None
            with session_lock: return sessions.get(sid)
        def do_GET(self):
            if not self.valid_host(): return self.send(403,{'error':'HOST_NOT_ALLOWED'})
            path=urlsplit(self.path).path
            if path=='/api/health': return self.send(200,{'status':'ready','mode':'offline-demo','external_calls':False})
            files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
            if path in files:
                name,ctype=files[path]; return self.send(200,(ROOT/'web'/name).read_bytes(),ctype)
            session=self.session()
            if not session: return self.send(401,{'error':'SELECT_DEMO_PERSONA'})
            try:
                if path=='/api/session': return self.send(200,session)
                if path=='/api/state': return self.send(200,engine.snapshot())
                if path=='/api/export': return self.send(200,{'notice':'Synthetic demo evidence. Recent 150 events; database retains full history.',**engine.snapshot()})
                self.send(404,{'error':'NOT_FOUND'})
            except (OSError,ValueError): self.send(503,{'error':'LOCAL_TOOL_UNAVAILABLE'})
        def do_POST(self):
            if not self.valid_host(): return self.send(403,{'error':'HOST_NOT_ALLOWED'})
            origin=self.headers.get('Origin')
            allowed=(f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}')
            if origin is not None and origin not in allowed: return self.send(403,{'error':'ORIGIN_NOT_ALLOWED'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.send(415,{'error':'JSON_REQUIRED'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<2 or n>8192: raise ValueError('Invalid request length')
                body=json.loads(self.rfile.read(n))
                if not isinstance(body,dict): raise ValueError('Object required')
            except (ValueError,TypeError): return self.send(400,{'error':'INVALID_JSON_OBJECT'})
            path=urlsplit(self.path).path
            if path=='/api/session':
                persona=body.get('persona')
                if persona not in PERSONAS: return self.send(400,{'error':'UNKNOWN_PERSONA'})
                actor,role=PERSONAS[persona]; sid=secrets.token_urlsafe(32)
                session={'actor':actor,'role':role,'persona':persona,'csrf':secrets.token_urlsafe(24)}
                with session_lock:
                    if len(sessions)>100: sessions.clear()
                    sessions[sid]=session
                return self.send(200,session,cookie=f'demo_session={sid}; HttpOnly; SameSite=Strict; Path=/')
            session=self.session()
            if not session: return self.send(401,{'error':'SELECT_DEMO_PERSONA'})
            if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf']): return self.send(403,{'error':'CSRF_TOKEN_REQUIRED'})
            role=session['role']
            try:
                if path=='/api/scenario':
                    if role not in ('employee','operator'): return self.send(403,{'error':'EMPLOYEE_OR_OPERATOR_REQUIRED'})
                    name=body.get('name')
                    if name not in SCENARIOS: return self.send(400,{'error':'UNKNOWN_SCENARIO'})
                    return self.send(200,engine.scenario(name))
                if path=='/api/approve':
                    return self.send(200,engine.approve(body.get('approval_id',''),session['actor'],role))
                if path in ('/api/suspend','/api/reactivate'):
                    fn=engine.suspend if path.endswith('suspend') else engine.reactivate
                    return self.send(200,fn(body.get('agent',''),role))
                self.send(404,{'error':'NOT_FOUND'})
            except (OSError,ValueError,TypeError): self.send(503,{'error':'LOCAL_SERVICE_UNAVAILABLE_OR_INVALID_REQUEST'})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

def main():
    parser=argparse.ArgumentParser(description='Offline Agent Governance Demo')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--data-dir',default=str(ROOT/'data'))
    parser.add_argument('--check',action='store_true',help='Check runtime modules and local loopback binding')
    args=parser.parse_args()
    if sys.version_info<(3,10): parser.error('Python 3.10 or later required')
    if args.check:
        import socket,sqlite3
        with socket.socket() as s: s.bind(('127.0.0.1',0))
        print('Python, SQLite, and loopback binding: OK. No external network or package installation required.')
        return
    engine=None; server=None
    try:
        engine=Engine(args.data_dir); server=make_server(engine,args.port)
        print(f'Open http://127.0.0.1:{server.server_port} in your browser.',flush=True)
        print('Synthetic data | scripted agents | local demo personas | no external calls',flush=True)
        print('Keep this terminal open. Press Ctrl+C to stop.',flush=True)
        server.serve_forever()
    except KeyboardInterrupt: pass
    except OSError as e:
        print('Cannot start local demo. Check approved Python, local loopback access, and whether the port is in use.',file=sys.stderr)
        print(str(e),file=sys.stderr)
        sys.exit(1)
    finally:
        if server: server.server_close()
        if engine: engine.close()

if __name__=='__main__': main()
