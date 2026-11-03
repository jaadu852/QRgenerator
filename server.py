    logo_reader=ImageReader(str(logo))
    for page_start in range(0,len(ids),4):
     page_ids=ids[page_start:page_start+4]
     for j,qid in enumerate(page_ids):
      col=j%2
      row=j//2
      x=left+col*card
      y=bottom+(1-row)*card
      c.drawImage(logo_reader,x,y,width=card,height=card,preserveAspectRatio=False,mask='auto')
      qr= qrcode.QRCode(error_correction=ERROR_CORRECT_H,box_size=32,border=4)
      target=public_base(self)+'/r/'+qid
      qr.add_data(target);qr.make(fit=True)
      matrix=qr.get_matrix();n=len(matrix);scale=32
      qimg=PILImage.new('RGBA',(n*scale,n*scale),(255,255,255,0))
      dr=ImageDraw.Draw(qimg)
      for yy,rowbits in enumerate(matrix):
       for xx,dark in enumerate(rowbits):
        if dark:dr.rectangle((xx*scale,yy*scale,(xx+1)*scale-1,(yy+1)*scale-1),fill=(0,0,0,255))
      qbio=io.BytesIO();qimg.save(qbio,format='PNG',optimize=False);qbio.seek(0)
      c.drawImage(ImageReader(qbio),x+qr_x,y+qr_y,width=qr_size,height=qr_size,mask='auto')
      c.setFont('Helvetica-Bold',5.0)
      label=qid.upper()
      c.drawCentredString(x+card*0.74,y+label_y+card*0.006,label)
     c.showPage()
    c.save()
    with conn() as db:db.execute('UPDATE qr SET downloaded_at=CURRENT_TIMESTAMP WHERE batch_id=?',(bid,))
    out=pdfbuf.getvalue()
    self.send_response(200);self.send_header('Content-Type','application/pdf');self.send_header('Content-Disposition','attachment; filename="CloudKrafts-'+bid+'.pdf"');self.send_header('Content-Length',str(len(out)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(out);return
   if p=='/api/admin-qr':
    if not self.auth():return self.reply({'error':'Incorrect admin password'},401)
    qid=str(d.get('id','')).strip().lower()
    if not re.fullmatch(r'ck[0-9]{6}',qid):return self.reply({'error':'Enter a valid QR number, e.g. ck000001'},400)
    with conn() as c:
     row=c.execute('SELECT q.id,q.status,q.shop,q.url,q.pin,q.vendor_id,v.name vendor,q.batch_id FROM qr q JOIN vendors v ON v.id=q.vendor_id WHERE q.id=?',(qid,)).fetchone()
    if not row:return self.reply({'error':'QR code not found'},404)
    if d.get('action')=='save':
     status=str(d.get('status','')).strip().lower()
     shop=str(d.get('shop','')).strip()[:120]
     url=str(d.get('url','')).strip()
     if status not in ('unused','active'):return self.reply({'error':'Choose Unused or Active'},400)
     if status=='active' and not validurl(url):return self.reply({'error':'Enter a valid http:// or https:// destination link'},400)
     with conn() as c:
      if status=='unused':
       c.execute("UPDATE qr SET status='unused',shop='',url='',pin='',updated=CURRENT_TIMESTAMP WHERE id=?",(qid,))
       c.execute('INSERT INTO audit(qr,action) VALUES(?,?)',(qid,'admin_reset_unused'))
      else:
       c.execute("UPDATE qr SET status='active',shop=?,url=?,updated=CURRENT_TIMESTAMP WHERE id=?",(shop,url,qid))
       c.execute('INSERT INTO audit(qr,action) VALUES(?,?)',(qid,'admin_update_link'))
      row=c.execute('SELECT q.id,q.status,q.shop,q.url,v.name vendor,q.batch_id FROM qr q JOIN vendors v ON v.id=q.vendor_id WHERE q.id=?',(qid,)).fetchone()
     return self.reply({'ok':True,'qr':dict(row)})
    return self.reply({'qr':dict(row)})
   if p=='/api/mark-downloaded':
    bid=str(d.get('batch_id',''))
    with conn() as c:c.execute('UPDATE qr SET downloaded_at=CURRENT_TIMESTAMP WHERE batch_id=?',(bid,))
    return self.reply({'ok':True})
   if p=='/api/batch':
    n=int(d.get('count',0));v=int(d.get('vendor',0))
    if not 1<=n<=500:return self.reply({'error':'Choose 1 to 500'},400)
    with conn() as c:
     if not c.execute('SELECT id FROM vendors WHERE id=?',(v,)).fetchone():return self.reply({'error':'Vendor not found'},404)
     first_row=c.execute('SELECT COALESCE(MAX(CAST(SUBSTR(id,3) AS INTEGER)),0) AS max_id FROM qr').fetchone();first=int(first_row['max_id']);ids=['ck'+str(i).zfill(6) for i in range(first+1,first+n+1)];batch_id='B'+str(first+1).zfill(6)+'-'+secrets.token_hex(2).upper()
     c.executemany('INSERT INTO qr(id,vendor_id,batch_id) VALUES(?,?,?)',[(x,v,batch_id) for x in ids])
    return self.reply({'ids':ids,'batch_id':batch_id})
   if p=='/api/activate':
    if rate_limited(client_ip(self),'activate',limit=8):return self.reply({'error':'Too many activation attempts. Please wait before trying again.'},429)
    id=str(d.get('id','')).strip().lower();shop=str(d.get('shop','')).strip();url=str(d.get('url','')).strip();password=str(d.get('password',''));pin=str(d.get('pin',''))
    if not shop or len(shop)>120 or not validurl(url) or not pin.isdigit() or not 6<=len(pin)<=12:return self.reply({'error':'Enter shop, valid URL and a 6–12 digit PIN'},400)
    with conn() as c:
     r=c.execute('SELECT q.status,v.secret FROM qr q JOIN vendors v ON q.vendor_id=v.id WHERE q.id=?',(id,)).fetchone()
     if not r:return self.reply({'error':'QR not found'},404)
     if r['status']!='unused':return self.reply({'error':'QR already activated'},409)
     if not hmac.compare_digest(digest(password),r['secret']):return self.reply({'error':'Incorrect vendor password'},401)
     c.execute("UPDATE qr SET status='active',shop=?,url=?,pin=?,updated=CURRENT_TIMESTAMP WHERE id=? AND status='unused'",(shop,url,digest(pin),id));c.execute('INSERT INTO audit(qr,action) VALUES(?,?)',(id,'activate'))
    return self.reply({'ok':True})
   if p=='/api/manage':
    if rate_limited(client_ip(self),'manage',limit=10):return self.reply({'error':'Too many management attempts. Please wait before trying again.'},429)
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
 if PRODUCTION and (not ADMIN or ADMIN=='Admin@12345' or len(ADMIN)<14):
  raise SystemExit('Set a unique ADMIN_PASSWORD of at least 14 characters in the hosting environment.')
 if PRODUCTION and len(APP_SECRET)<32:
  raise SystemExit('Set APP_SECRET to a random value of at least 32 characters.')
 if PRODUCTION and not DATABASE_URL:
  raise SystemExit('DATABASE_URL is required in production; configure Supabase PostgreSQL.')
 if PRODUCTION and not PUBLIC_BASE_URL.startswith('https://'):
  raise SystemExit('Set PUBLIC_BASE_URL to the HTTPS production domain, e.g. https://qr.cloudkrafts.in.')
 init();print(f'CloudKrafts QR Manager listening on {HOST}:{PORT}')
 if not PRODUCTION:print('Local admin password: '+ADMIN)
 print('Server started. Stop with Ctrl+C.')
 ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
