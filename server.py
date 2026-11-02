import os,sqlite3,json,secrets,hashlib,hmac,io,ipaddress,urllib.parse,threading,webbrowser
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DB=ROOT/'local-data.sqlite3'
HOST=os.environ.get('CK_HOST','127.0.0.1'); PORT=int(os.environ.get('CK_PORT','8765'))
ADMIN=os.environ.get('CK_ADMIN_PASSWORD','Admin@12345')
def digest(s):return hashlib.pbkdf2_hmac('sha256',s.encode(),b'ck-local-demo',180000).hex()
def conn():
 c=sqlite3.connect(DB,timeout=20);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA journal_mode=WAL');return c
def init():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS vendors(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,contact TEXT,secret TEXT NOT NULL,password_local TEXT DEFAULT '');CREATE TABLE IF NOT EXISTS qr(id TEXT PRIMARY KEY,vendor_id INTEGER NOT NULL REFERENCES vendors(id),status TEXT NOT NULL DEFAULT 'unused',shop TEXT DEFAULT '',url TEXT DEFAULT '',pin TEXT DEFAULT '',batch_id TEXT DEFAULT '',downloaded_at TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP,updated TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,qr TEXT,action TEXT,at TEXT DEFAULT CURRENT_TIMESTAMP);''')
  # Safe schema upgrades for databases created by earlier test versions
  for table,col,definition in [('vendors','password_local',"TEXT DEFAULT ''"),('qr','batch_id',"TEXT DEFAULT ''"),('qr','downloaded_at',"TEXT DEFAULT ''")]:
   cols=[x['name'] for x in c.execute(f'PRAGMA table_info({table})')]
   if col not in cols:c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {definition}')
def validurl(v):
 try:
  u=urllib.parse.urlparse(v);return u.scheme in ('http','https') and bool(u.hostname) and '.' in u.hostname and not u.username and not u.password
 except:return False
class Handler(BaseHTTPRequestHandler):
 def log_message(self,fmt,*args): print('[HTTP] '+(fmt % args))

 def reply(self,obj,status=200):
  b=json.dumps(obj).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def html(self):
  b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def auth(self):return hmac.compare_digest(self.headers.get('X-Admin-Password',''),ADMIN)
 def data(self):
  n=int(self.headers.get('Content-Length','0'))
  if n>15000:raise ValueError('Request too large')
  return json.loads(self.rfile.read(n) or b'{}')
 def do_GET(self):
  try:return self._do_GET()
  except Exception as e:
   import traceback
   print('[GET ERROR]',repr(e));traceback.print_exc()
   try:return self.reply({'error':str(e)},500)
   except Exception:return
 def _do_GET(self):
  p=urllib.parse.urlparse(self.path).path

  if p.startswith('/r/'):
   id=p[3:];
   with conn() as c:r=c.execute('SELECT status,url FROM qr WHERE id=?',(id,)).fetchone()
   if not r:self.send_response(404);self.end_headers();self.wfile.write(b'Unknown QR');return
   if r['status']=='active' and validurl(r['url']):
    self.send_response(302);self.send_header('Location',r['url']);self.send_header('Cache-Control','no-store');self.end_headers();return
   self.send_response(302);self.send_header('Location','/activate?id='+urllib.parse.quote(id));self.end_headers();return
  if p=='/logo.png':
   f=ROOT/'logo.png'
   if not f.exists():
    self.send_response(404);self.send_header('Content-Type','text/plain; charset=utf-8');self.end_headers();self.wfile.write(b'Please place logo.png in the same folder as server.py');return
   b=f.read_bytes();self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p.startswith('/assets/'):
   name=p[len('/assets/'):]
   if name not in ('review-card-blue.jpg','review-card-black.jpg','review-card-blue-uhd.jpg','review-card-black-uhd.jpg','review-card-blue-vector.svg','review-card-black-vector.svg','review-card-blue-exact.png'):
    return self.reply({'error':'Not found'},404)
   f=ROOT/'assets'/name
   b=f.read_bytes();mime='image/svg+xml; charset=utf-8' if name.endswith('.svg') else ('image/png' if name.endswith('.png') else 'image/jpeg')
   self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if p=='/api/data':
   if not self.auth():return self.reply({'error':'Incorrect admin password'},401)
   with conn() as c:
    vendors=[dict(x) for x in c.execute('SELECT v.id,v.name,v.contact,v.password_local password,(SELECT COUNT(*) FROM qr WHERE vendor_id=v.id) total,(SELECT COUNT(*) FROM qr WHERE vendor_id=v.id AND status="active") active FROM vendors v ORDER BY id DESC')]
    qr=[dict(x) for x in c.execute('SELECT q.id,q.status,q.shop,q.url,q.updated,q.batch_id,q.downloaded_at,v.name vendor FROM qr q JOIN vendors v ON q.vendor_id=v.id ORDER BY q.id DESC LIMIT 1000')]
    batches=[dict(x) for x in c.execute('SELECT batch_id,v.name vendor,COUNT(*) quantity,MIN(q.id) first_id,MAX(q.id) last_id,MAX(downloaded_at) downloaded_at FROM qr q JOIN vendors v ON q.vendor_id=v.id WHERE batch_id != \"\" GROUP BY batch_id,v.name ORDER BY batch_id DESC')]
    totals=dict(c.execute('SELECT COUNT(*) total,COUNT(*) FILTER(WHERE status="unused") unused,COUNT(*) FILTER(WHERE status="active") active FROM qr').fetchone())
   return self.reply({'vendors':vendors,'qr':qr,'batches':batches,'totals':totals})
  if p=='/api/qr.svg':
   import qrcode
   from qrcode.constants import ERROR_CORRECT_H
   id=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('id',[''])[0]
   if not id.startswith('ck') or not id[2:].isdigit():return self.reply({'error':'Invalid QR'},400)
   target='http://'+self.headers.get('Host',f'{HOST}:{PORT}')+'/r/'+id
   qr=qrcode.QRCode(error_correction=ERROR_CORRECT_H,border=4,box_size=1)
   qr.add_data(target);qr.make(fit=True);matrix=qr.get_matrix();n=len(matrix)
   # Vector path: remains razor-sharp at any print/zoom size. White background includes a proper quiet zone.
   path=''.join(f'M{x},{y}h1v1h-1z' for y,row in enumerate(matrix) for x,val in enumerate(row) if val)
   svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="{n}" height="{n}" shape-rendering="crispEdges"><rect width="{n}" height="{n}" fill="#fff"/><path d="{path}" fill="#000"/></svg>'
   out=svg.encode('utf-8');self.send_response(200);self.send_header('Content-Type','image/svg+xml');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(out)));self.end_headers();self.wfile.write(out);return
  if p=='/api/qr.png':
   import qrcode
   from qrcode.constants import ERROR_CORRECT_H
   from PIL import Image, ImageDraw
   id=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('id',[''])[0]
   if not id.startswith('ck') or not id[2:].isdigit():return self.reply({'error':'Invalid QR'},400)
   target='http://'+self.headers.get('Host',f'{HOST}:{PORT}')+'/r/'+id
   qr=qrcode.QRCode(error_correction=ERROR_CORRECT_H,box_size=32,border=4)
   qr.add_data(target);qr.make(fit=True);matrix=qr.get_matrix()
   n=len(matrix);scale=32
   image=Image.new('RGBA',(n*scale,n*scale),(255,255,255,0))
   draw=ImageDraw.Draw(image)
   for yy,row in enumerate(matrix):
    for xx,dark in enumerate(row):
     if dark:draw.rectangle((xx*scale,yy*scale,(xx+1)*scale-1,(yy+1)*scale-1),fill=(0,0,0,255))
   b=io.BytesIO();image.save(b,format='PNG',optimize=False);out=b.getvalue()
   self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(out)));self.end_headers();self.wfile.write(out);return
  return self.html()
 def do_POST(self):
  try:
   p=urllib.parse.urlparse(self.path).path;d=self.data()
   if p=='/api/login':return self.reply({'ok':self.auth()}) if self.auth() else self.reply({'error':'Incorrect admin password'},401)
   if p in ('/api/vendor','/api/vendor-update','/api/batch','/api/reset','/api/mark-downloaded') and not self.auth():return self.reply({'error':'Incorrect admin password'},401)
   if p=='/api/vendor':
    name=str(d.get('name','')).strip();secret=str(d.get('password',''))
    if len(name)<2 or len(secret)<8:return self.reply({'error':'Vendor name and password of at least 8 characters required'},400)
    with conn() as c:c.execute('INSERT INTO vendors(name,contact,secret,password_local) VALUES(?,?,?,?)',(name,str(d.get('contact','')),digest(secret),secret))
    return self.reply({'ok':True})
   if p=='/api/vendor-update':
    v=int(d.get('id',0));name=str(d.get('name','')).strip();password=str(d.get('password',''))
    if len(name)<2 or len(password)<8:return self.reply({'error':'Name and password (minimum 8 characters) required'},400)
    with conn() as c:
     if not c.execute('UPDATE vendors SET name=?,contact=?,secret=?,password_local=? WHERE id=?',(name,str(d.get('contact','')),digest(password),password,v)).rowcount:return self.reply({'error':'Vendor not found'},404)
    return self.reply({'ok':True})
   if p=='/api/mark-downloaded':
    bid=str(d.get('batch_id',''))
    with conn() as c:c.execute('UPDATE qr SET downloaded_at=CURRENT_TIMESTAMP WHERE batch_id=?',(bid,))
    return self.reply({'ok':True})
   if p=='/api/batch':
    n=int(d.get('count',0));v=int(d.get('vendor',0))
    if not 1<=n<=500:return self.reply({'error':'Choose 1 to 500'},400)
    with conn() as c:
     if not c.execute('SELECT id FROM vendors WHERE id=?',(v,)).fetchone():return self.reply({'error':'Vendor not found'},404)
     first=c.execute('SELECT COALESCE(MAX(CAST(SUBSTR(id,3) AS INTEGER)),0) FROM qr').fetchone()[0];ids=['ck'+str(i).zfill(6) for i in range(first+1,first+n+1)];batch_id='B'+str(first+1).zfill(6)+'-'+secrets.token_hex(2).upper()
     c.executemany('INSERT INTO qr(id,vendor_id,batch_id) VALUES(?,?,?)',[(x,v,batch_id) for x in ids])
    return self.reply({'ids':ids,'batch_id':batch_id})
   if p=='/api/activate':
    id=str(d.get('id','')).strip().lower();shop=str(d.get('shop','')).strip();url=str(d.get('url','')).strip();password=str(d.get('password',''));pin=str(d.get('pin',''))
    if not shop or len(shop)>120 or not validurl(url) or not pin.isdigit() or not 6<=len(pin)<=12:return self.reply({'error':'Enter shop, valid URL and a 6–12 digit PIN'},400)
    with conn() as c:
     r=c.execute('SELECT q.status,v.secret FROM qr q JOIN vendors v ON q.vendor_id=v.id WHERE q.id=?',(id,)).fetchone()
     if not r:return self.reply({'error':'QR not found'},404)
     if r['status']!='unused':return self.reply({'error':'QR already activated'},409)
     if not hmac.compare_digest(digest(password),r['secret']):return self.reply({'error':'Incorrect vendor password'},401)
     c.execute('UPDATE qr SET status="active",shop=?,url=?,pin=?,updated=CURRENT_TIMESTAMP WHERE id=? AND status="unused"',(shop,url,digest(pin),id));c.execute('INSERT INTO audit(qr,action) VALUES(?,?)',(id,'activate'))
    return self.reply({'ok':True})
   if p=='/api/manage':
    id=str(d.get('id','')).strip().lower();pin=str(d.get('pin',''))
    with conn() as c:
     r=c.execute('SELECT shop,url,pin,status FROM qr WHERE id=?',(id,)).fetchone()
     if not r or r['status']!='active' or not hmac.compare_digest(digest(pin),r['pin']):return self.reply({'error':'Incorrect QR ID or management PIN'},401)
     if d.get('action')=='view':return self.reply({'shop':r['shop'],'url':r['url']})
     url=str(d.get('url','')).strip()
     if not validurl(url):return self.reply({'error':'Invalid destination URL'},400)
     c.execute('UPDATE qr SET url=?,updated=CURRENT_TIMESTAMP WHERE id=?',(url,id));c.execute('INSERT INTO audit(qr,action) VALUES(?,?)',(id,'update'))
    return self.reply({'ok':True})
   return self.reply({'error':'Unknown endpoint'},404)
  except Exception as e:
   import traceback
   print('[API ERROR]',repr(e));traceback.print_exc()
   try:return self.reply({'error':str(e)},500)
   except Exception:return

if __name__=='__main__':
 init();print(f'CloudKrafts local demo: http://{HOST}:{PORT}');print('Admin password: '+ADMIN);print('Keep this window open. Ctrl+C to stop.')
 ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
