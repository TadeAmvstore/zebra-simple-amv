from flask import Flask,request,jsonify,send_file
from PIL import Image,ImageOps
import fitz,io,os,json,socket,threading,webbrowser,ipaddress
app=Flask(__name__)
BASE=os.path.dirname(__file__); DATA=os.path.join(os.environ.get('LOCALAPPDATA',BASE),'ZebraSimpleAMV'); os.makedirs(DATA,exist_ok=True); CFG=os.path.join(DATA,'impresoras.json'); DPI=203
VERSION='1.1.1'
@app.get('/api/version')
def version():return jsonify({'version':VERSION,'repository':'TadeAmvstore/zebra-simple-amv'})
@app.get('/amv_logo.png')
def logo(): return send_file(os.path.join(BASE,'amv_logo.png'),mimetype='image/png')
@app.get('/favicon.svg')
def favicon():
 return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#252b32"/><circle cx="32" cy="32" r="21" fill="none" stroke="white" stroke-width="3"/><path d="M11 32h42M32 11c-14 13-14 29 0 42M32 11c14 13 14 29 0 42" fill="none" stroke="white" stroke-width="3"/></svg>',200,{'Content-Type':'image/svg+xml'}
@app.get('/')
def home():return open(os.path.join(BASE,'index.html'),encoding='utf8').read()
@app.route('/api/printers',methods=['GET','POST'])
def printers():
 if request.method=='GET':
  if os.path.exists(CFG):return jsonify(json.load(open(CFG,encoding='utf8')))
  old=os.path.join(BASE,'impresoras.json')
  if os.path.exists(old):return jsonify(json.load(open(old,encoding='utf8')))
  return jsonify([{'name':f'Zebra {i+1}','ip':ip} for i,ip in enumerate(['192.168.98.104','192.168.98.15','192.168.98.14','192.168.98.161'])])
 data=request.get_json()
 if not isinstance(data,list) or len(data)!=4:return 'Se necesitan cuatro impresoras',400
 for p in data:
  if len(str(p.get('name','')))>60:return 'Nombre demasiado largo',400
  if p.get('ip'):ipaddress.ip_address(p['ip'])
 with open(CFG,'w',encoding='utf8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
 return 'Guardado'
def image_and_pages():
 upload=request.files['file']; data=upload.read()
 if len(data)>30*1024*1024:raise ValueError('Archivo demasiado grande (máximo 30 MB)')
 pdf=data[:5]==b'%PDF-' or upload.filename.lower().endswith('.pdf')
 if pdf:
  doc=fitz.open(stream=data,filetype='pdf'); count=len(doc);page=int(request.form.get('page',0))
  if page<0 or page>=count:raise ValueError('Página inválida')
  pix=doc[page].get_pixmap(matrix=fitz.Matrix(3,3),alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);doc.close()
 else:
  im=Image.open(io.BytesIO(data));im.load();im=ImageOps.exif_transpose(im).convert('RGB');count=1
 return im,count,pdf
@app.post('/api/info')
def info():
 try:
  _,count,pdf=image_and_pages();return jsonify({'pages':count,'pdf':pdf})
 except Exception as e:return str(e),400
@app.post('/api/preview')
def preview():
 try:
  im,_,_=image_and_pages();im.thumbnail((1100,1500));b=io.BytesIO();im.save(b,'PNG');b.seek(0);return send_file(b,mimetype='image/png')
 except Exception as e:return str(e),400
def zpl(im,wmm,hmm,scale,rotation,copies):
 w=round(wmm*DPI/25.4);h=round(hmm*DPI/25.4)
 if not (80<=w<=1600 and 80<=h<=2400):raise ValueError('Tamaño de etiqueta fuera de rango')
 im=im.rotate(-rotation,expand=True)
 fit=min(w/im.width,h/im.height)*scale/100
 im=im.resize((max(1,round(im.width*fit)),max(1,round(im.height*fit))),Image.Resampling.LANCZOS)
 canvas=Image.new('L',(w,h),255);canvas.paste(ImageOps.grayscale(im),((w-im.width)//2,(h-im.height)//2))
 mono=canvas.point(lambda v:0 if v<160 else 255).convert('1');raw=mono.tobytes();rb=(w+7)//8
 # PIL 1-bit uses 1 for white; invert bytes for Zebra graphic black=1
 packed=bytes(v^255 for v in raw)
 return f'^XA^PW{w}^LL{h}^FO0,0^GFA,{len(packed)},{len(packed)},{rb},{packed.hex().upper()}^FS^PQ{copies}^XZ'
@app.post('/api/print')
def printing():
 try:
  im,_,_=image_and_pages();w=float(request.form['width']);h=float(request.form['height']);scale=float(request.form['scale']);rot=int(request.form['rotation']);copies=int(request.form['copies']);ip=request.form['ip']
  ipaddress.ip_address(ip)
  if not (10<=scale<=200 and rot in (0,90,180,270) and 1<=copies<=999):raise ValueError('Configuración inválida')
  data=zpl(im,w,h,scale,rot,copies).encode('ascii')
  with socket.create_connection((ip,9100),timeout=8) as s:s.sendall(data)
  return 'Trabajo enviado a la impresora.'
 except Exception as e:return 'Error: '+str(e),400
@app.post('/api/batch/info')
def batch_info():
 try:
  files=request.files.getlist('files')
  if not 1<=len(files)<=10:raise ValueError('Seleccioná entre 1 y 10 PDF')
  result=[]
  for f in files:
   data=f.read()
   if len(data)>30*1024*1024:raise ValueError(f'{f.filename}: máximo 30 MB')
   if not data.startswith(b'%PDF-'):raise ValueError(f'{f.filename}: solo se permiten PDF')
   with fitz.open(stream=data,filetype='pdf') as doc:
    if len(doc)<1:raise ValueError('PDF vacío')
    result.append({'name':f.filename,'pages':len(doc)})
  return jsonify({'files':result,'total_pages':sum(x['pages'] for x in result)})
 except Exception as e:return str(e),400

@app.post('/api/batch/print')
def batch_print():
 try:
  files=request.files.getlist('files')
  if not 1<=len(files)<=10:raise ValueError('Seleccioná entre 1 y 10 PDF')
  w=float(request.form['width']);h=float(request.form['height']);scale=float(request.form['scale']);rot=int(request.form['rotation']);copies=int(request.form['copies']);ip=request.form['ip']
  ipaddress.ip_address(ip)
  if not (10<=scale<=200 and rot in (0,90,180,270) and 1<=copies<=999):raise ValueError('Configuración inválida')
  # Validar todos los archivos antes de imprimir para evitar tandas parcialmente inválidas.
  docs=[]
  try:
   for f in files:
    data=f.read()
    if len(data)>30*1024*1024 or not data.startswith(b'%PDF-'):raise ValueError(f'{f.filename}: PDF inválido o mayor a 30 MB')
    doc=fitz.open(stream=data,filetype='pdf')
    if len(doc)<1:doc.close();raise ValueError('PDF vacío')
    docs.append((f.filename,doc))
   total=sum(len(d) for _,d in docs)
   if total>100:raise ValueError('Máximo 100 páginas por tanda')
   # Una conexión por página: se informa el avance real de envíos, no impresión física.
   sent=0
   for name,doc in docs:
    for pg in doc:
     pix=pg.get_pixmap(matrix=fitz.Matrix(3,3),alpha=False)
     im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
     payload=zpl(im,w,h,scale,rot,copies).encode('ascii')
     try:
      with socket.create_connection((ip,9100),timeout=8) as sock:sock.sendall(payload)
     except OSError as e:raise RuntimeError(f'Enviadas {sent} de {total} páginas. Error en {name}: {e}')
     sent+=1
   return jsonify({'sent':sent,'total':total,'message':f'{sent} de {total} páginas enviadas a la Zebra.'})
  finally:
   for _,doc in docs:doc.close()
 except Exception as e:return jsonify({'error':str(e)}),400

if __name__=='__main__':
 threading.Timer(1,lambda:webbrowser.open('http://127.0.0.1:8765')).start()
 app.run('127.0.0.1',8765,debug=False)
