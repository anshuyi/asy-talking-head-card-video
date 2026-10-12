"""Local, source-preserving talking-head card-video pipeline. No cloud calls."""
from pathlib import Path
import argparse,contextlib,hashlib,importlib.util,json,math,os,shutil,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.1.0'

def renderer():
 spec=importlib.util.spec_from_file_location('asy_card_renderer',ROOT/'scripts/card_renderer.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 q=p.with_name(p.name+'.new');q.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');q.replace(p)
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(args,**kw):
 r=subprocess.run([str(x) for x in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw)
 if r.returncode:raise RuntimeError(r.stderr.decode('utf-8',errors='replace')[-5000:])
 return r.stdout
def config(path=None):
 p=Path(path or os.environ.get('ASY_CARD_CONFIG') or Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'asy-card-video/runtime.json').resolve()
 if not p.is_file():raise ValueError('缺少本机配置：'+str(p))
 c=read(p);c['_path']=str(p)
 for k in ('ffmpeg','ffprobe'):
  val=c.get(k,k);found=shutil.which(val) or (str(Path(val).resolve()) if Path(val).is_file() else None)
  if not found:raise ValueError('缺少依赖：'+k)
  c[k]=found
 sys.path[:0]=c.get('python_paths',[])
 os.environ['PYTHONPATH']=os.pathsep.join(c.get('python_paths',[]))
 os.environ['PATH']=os.pathsep.join(c.get('cuda_dirs',[])+[str(Path(c['ffmpeg']).parent),os.environ.get('PATH','')])
 c['_handles']=[os.add_dll_directory(d) for d in c.get('cuda_dirs',[]) if os.name=='nt']
 return c
def probe(path,c):return json.loads(run([c['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',path]))
def dimensions(meta):
 v=next((s for s in meta['streams'] if s['codec_type']=='video'),None)
 a=next((s for s in meta['streams'] if s['codec_type']=='audio'),None)
 if not v or not a:raise ValueError('需要同时包含真人画面和声音的视频；未发现视频或音轨')
 if v.get('sample_aspect_ratio','1:1') not in ('1:1','0:1','N/A'):raise ValueError('非方形像素：请先建立等时长规范化副本')
 if abs(float(v.get('start_time',0))-float(a.get('start_time',0)))>1/30:raise ValueError('音视频起点不同：先建立保留同步关系的规范化副本')
 if any(abs(float(s.get('rotation',0)))%360 for s in v.get('side_data_list',[])) or abs(float(v.get('tags',{}).get('rotate',0)))%360:raise ValueError('存在旋转元数据：请先建立规范化副本再初始化')
 dur=max(float(meta['format'].get('duration',0)),float(v.get('duration',0)),float(a.get('duration',0)))
 if not math.isfinite(dur) or dur<=0:raise ValueError('时长无效')
 return v,a,dur
def source(p):
 d=read(p/'source.json');s=Path(d['path'])
 if not s.is_file() or sha(s)!=d['sha256']:raise ValueError('源文件丢失或变化，不能复用旧项目')
 return d,s
def init(p,src,c):
 src=Path(src).resolve()
 if not src.is_file():raise ValueError('源文件不存在')
 if p==ROOT or ROOT in p.parents:raise ValueError('项目产物不能写入技能包')
 if p.exists() and any(p.iterdir()):raise ValueError('项目目录非空，请使用独立新目录')
 meta=probe(src,c);v,a,dur=dimensions(meta)
 p.mkdir(parents=True,exist_ok=True)
 for d in ('qa','tmp','out','previews'): (p/d).mkdir()
 save(p/'source.json',{'path':str(src),'sha256':sha(src),'duration':dur,'width':v['width'],'height':v['height'],'audio_codec':a['codec_name'],'sample_rate':a.get('sample_rate'),'channels':a.get('channels'),'version':VERSION})
 save(p/'qa/source-probe.json',meta)
 # Explicitly unreviewed defaults; no speaker-specific crop is silently inherited.
 size=min(v['width'],v['height']);crop={'x':(v['width']-size)//2,'y':(v['height']-size)//2,'size':size,'reviewed':False,'reason':''}
 save(p/'timeline.json',{'duration':dur,'header':'口播图解','crop':crop,'transcript_review':{'status':'machine','method':'尚未转写','unresolved':[]},'captions':[],'scenes':[]})
 print('已初始化：'+str(p),flush=True)

@contextlib.contextmanager
def asr_lock(c):
 lock=Path(c['_path']).with_name('card-asr.lock');lock.parent.mkdir(parents=True,exist_ok=True)
 with lock.open('a+b') as f:
  if f.tell()==0:f.write(b'1');f.flush()
  f.seek(0)
  if os.name=='nt':
   import msvcrt
   try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
   except OSError:raise ValueError('另一个转写正在运行，请稍后继续')
  else:
   import fcntl
   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:yield
  finally:
   f.seek(0)
   if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
   else:fcntl.flock(f,fcntl.LOCK_UN)

def transcribe(p,c,replace=False):
 d,s=source(p);out=p/'transcript-machine.json'
 if out.exists() and not replace:raise ValueError('已有转写；要重新识别请显式--replace')
 with asr_lock(c):
  from faster_whisper import WhisperModel
  m=WhisperModel(c.get('model','large-v3-turbo'),device=c.get('device','cuda'),compute_type=c.get('compute_type','float16'),local_files_only=True)
  # Force ASR input to audio only; pixels and burned captions are inaccessible here.
  wav=p/'tmp/asr-input.wav'
  run([c['ffmpeg'],'-v','error','-y','-i',s,'-map','0:a:0','-vn','-ac','1','-ar','16000',wav])
  try:
   lang=c.get('language','zh')
   segs,info=m.transcribe(str(wav),language=lang,word_timestamps=True,vad_filter=True,condition_on_previous_text=False,beam_size=5,initial_prompt='以下是简体中文口播。' if lang=='zh' else None)
   rows=[{'start':g.start,'end':g.end,'text':g.text,'avg_logprob':g.avg_logprob,'no_speech_prob':g.no_speech_prob,'words':[{'start':w.start,'end':w.end,'text':w.word,'probability':w.probability} for w in g.words or []]} for g in segs]
   if not rows or not any(x['text'].strip() for x in rows):raise ValueError('没有识别到可靠口播，请检查音轨')
   if any(not(0<=g['start']<g['end']<=d['duration']+.2) for g in rows):raise ValueError('识别时间轴越界，需局部重识别，未写入成功记录')
   if out.exists():shutil.copy2(out,p/f'transcript-machine-{time.time_ns()}.bak.json')
   save(out,{'status':'machine','input':'audio-only','source_sha256':d['sha256'],'duration':info.duration,'segments':rows})
   print('已完成音轨转写：'+str(len(rows))+'段；尚未人工校对',flush=True)
  finally:
   if wav.is_file():wav.unlink()

def validate(d,src,draft=False,require_review=False):
 def need(ok,msg):
  if not ok:raise ValueError(msg)
 def num(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
 def interval(o,lo,hi):return num(o.get('start')) and num(o.get('end')) and lo<=o['start']<o['end']<=hi+.001
 def text(v,n):return isinstance(v,str) and 0<len(v.strip())<=n
 dur=d.get('duration');need(num(dur) and abs(dur-src['duration'])<=1/30,'时间线必须保持源时长')
 need(text(d.get('header'),18),'header应为1—18字符')
 cr=d.get('crop',{});need(all(num(cr.get(k)) for k in ('x','y','size')),'crop必须提供数值x/y/size')
 need(cr['size']>=32 and cr['x']>=0 and cr['y']>=0 and cr['x']+cr['size']<=src['width'] and cr['y']+cr['size']<=src['height'],'裁切框越出原视频')
 need(all(float(cr[k]).is_integer() and int(cr[k])%2==0 for k in ('x','y','size')),'crop坐标和尺寸必须为偶数整数')
 review=d.get('transcript_review',{});need(review.get('status') in ('machine','draft','reviewed') and isinstance(review.get('unresolved'),list) and text(review.get('method'),1000),'缺少转写核验记录')
 if require_review:need(cr.get('reviewed') is True and text(cr.get('reason'),1000),'必须先预览人物取景并记录检查依据')
 if not draft:need(review.get('status')=='reviewed' and not review['unresolved'],'未核清的转写只能出候选片，不能标正式')
 caps=d.get('captions');need(isinstance(caps,list) and bool(caps),'缺少字幕')
 last=0
 for a in caps:
  need(interval(a,0,dur) and a['start']>=last-.001,'字幕交叉、越界或时长无效');last=a['end']
  need(text(a.get('text'),80),'字幕为空或过长，需按原声分段')
  need(isinstance(a.get('source_span'),list) and len(a['source_span'])==2 and all(num(x) for x in a['source_span']) and 0<=a['source_span'][0]<a['source_span'][1]<=dur+.001,'字幕缺少有效音轨依据')
  if a.get('display') is False:need(text(a.get('hidden_reason'),300),'关闭字幕必须说明引用替代位置')
 scenes=d.get('scenes');need(isinstance(scenes,list) and bool(scenes),'缺少内容分镜')
 last=0
 for s in scenes:
  need(interval(s,0,dur) and abs(s['start']-last)<.002,'场景必须连续覆盖全片');last=s['end']
  need(s.get('mode') in ('flow','causal','compare','cards','quote','statement'),'未知图解类型')
  need(isinstance(s.get('title'),list) and 1<=len(s['title'])<=2 and all(text(x,16) for x in s['title']),'标题需1—2行，每行不超过16字符')
  need(text(s.get('purpose'),300),'缺少图解目的')
  need(isinstance(s.get('source_span'),list) and len(s['source_span'])==2 and all(num(x) for x in s['source_span']) and 0<=s['source_span'][0]<s['source_span'][1]<=dur+.001,'场景缺少音轨依据')
  for k,n in [('tag',28),('note',28)]:need(text(s.get(k),n),k+'缺少或过长')
  need(isinstance(s.get('side'),list) and len(s['side'])==2 and all(text(x,12) for x in s['side']),'side需两条不超过12字符的说明')
  items=s.get('items',[]);limit={'flow':4,'causal':4,'compare':2,'cards':3,'quote':2,'statement':2}[s['mode']]
  need(1<=len(items)<=limit,'图解项目数量不合适')
  for it in items:
   need(num(it.get('at')) and s['start']<=it['at']<s['end'],'项目出现时间超出场景')
   need(text(it.get('label'),28) and (not it.get('detail') or text(it['detail'],32)),'图解标签过长或为空')
 need(abs(last-dur)<.002,'场景未覆盖片尾')

def build(p,c,draft=True,review=False):
 src,_=source(p);d=read(p/'timeline.json');validate(d,src,draft,review)
 font=Path(c.get('font_file',''))
 if not font.is_file():raise ValueError('请配置实际存在的中文字体文件')
 html=(ROOT/'templates/card.html').read_text(encoding='utf-8')
 html=html.replace('__FONT_URL__',font.resolve().as_uri()).replace('__DATA_JSON__',json.dumps(d,ensure_ascii=False).replace('<','\\u003c'))
 (p/'index.html').write_text(html,encoding='utf-8');return src,d

def compose(p,bg,out,c,still=None):
 src,s=source(p);d=read(p/'timeline.json');r=d['crop'];x,y,z=[int(r[k]) for k in ('x','y','size')]
 filt=f"[1:v]setpts=PTS-STARTPTS,crop={z}:{z}:{x}:{y},scale=360:360,setsar=1,format=yuva420p,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='255*clip(180-sqrt(pow(X-179.5,2)+pow(Y-179.5,2)),0,1)'[person];[0:v][person]overlay=120:930:eof_action=repeat,format=yuv420p[v]"
 args=[c['ffmpeg'],'-v','error','-y','-i',bg]
 if still is not None:args+=['-ss',str(still)]
 args+=['-i',s,'-filter_complex',filt,'-map','[v]']
 if still is not None:args+=['-frames:v','1',out]
 else:args+=['-map','1:a:0','-c:v','libx264','-preset','fast','-crf','18','-r','30','-c:a', 'copy' if src['audio_codec']=='aac' else 'aac','-movflags','+faststart',out]
 run(args)

def preview(p,c):
 src,d=build(p,c)
 with renderer().card_page(p) as pg:
  times=sorted(set(round(s['start']+(s['end']-s['start'])*f,3) for s in d['scenes'] for f in (.05,.5,.95)))
  for i,t in enumerate(times):
   pg.evaluate('t=>window.render(t)',t);bg=p/f'tmp/frame-{i:03}.png';pg.screenshot(path=str(bg));compose(p,bg,p/f'previews/frame-{i:03}.jpg',c,t)
  # Check all displayed text variants, including the longest subtitles.
  for cap in d['captions']:pg.evaluate('t=>window.render(t)',(cap['start']+cap['end'])/2)
 save(p/'qa/preview.json',{'times':times,'timeline_sha256':sha(p/'timeline.json'),'status':'rendered; visual inspection still required'})
 print(f'已生成{len(times)}张预览，所有字幕实际字宽检查通过',flush=True)

def filename(name):
 if not name or Path(name).name!=name or '/' in name or '\\' in name or ':' in name or not name.endswith('.mp4'):raise ValueError('输出名必须是项目内的.mp4文件名')
 return name
def render(p,c,name,draft=False):
 name=filename(name)
 if draft and 'draft' not in name.lower() and '候选' not in name:raise ValueError('候选片文件名必须含draft或候选')
 src,d=build(p,c,draft,True);out=p/'out'/name
 if out.exists():raise ValueError('成片已存在，请用新的版本名，不覆盖认可版本')
 graphics=renderer().render_cards(p,d['duration'],c['ffmpeg'])
 tmp=p/'tmp/composed.mp4';compose(p,graphics,tmp,c);tmp.replace(out)
 save(p/'qa'/f'{name}.render.json',{'output_sha256':sha(out),'timeline_sha256':sha(p/'timeline.json'),'source_sha256':src['sha256'],'draft':draft,'version':VERSION,'template_sha256':sha(ROOT/'templates/card.html')})
 print('已导出：'+str(out),flush=True)

def audio_hash(path,c):
 pr=subprocess.Popen([c['ffmpeg'],'-v','error','-i',str(path),'-map','0:a:0','-f','s16le','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 h=hashlib.sha256();n=0
 while True:
  block=pr.stdout.read(1024*1024)
  if not block:break
  h.update(block);n+=len(block)
 if pr.wait():raise ValueError('声音解码失败')
 return h.hexdigest(),n
def check(p,c,name):
 name=filename(name);src,s=source(p);out=p/'out'/name
 rec=read(p/'qa'/f'{name}.render.json')
 if rec['timeline_sha256']!=sha(p/'timeline.json') or rec['output_sha256']!=sha(out):raise ValueError('成片或时间线已变化，检查不能沿用旧渲染记录')
 meta=probe(out,c);v,a,dur=dimensions(meta)
 if (v['width'],v['height'])!=(1080,1440) or v['r_frame_rate']!='30/1' or v['codec_name']!='h264' or a['codec_name']!='aac':raise ValueError('导出规格不符')
 if abs(dur-src['duration'])>1/30+.01:raise ValueError('成片时长偏差超过允许值')
 run([c['ffmpeg'],'-v','error','-i',out,'-f','null','-'])
 h1,n1=audio_hash(s,c);h2,n2=audio_hash(out,c)
 if src['audio_codec']=='aac' and h1!=h2:raise ValueError('原AAC音轨发生变化')
 if abs(n1-n2)>int(src.get('sample_rate') or 48000)*int(src.get('channels') or 2)*2*.1:raise ValueError('音轨长度异常')
 result={'decode':'passed','dimensions':[v['width'],v['height']],'duration':dur,'source_unchanged':True,'audio_pcm_identical':h1==h2,'audio_length_delta_bytes':n2-n1,'continuous_listening':'not performed by automated check','output_sha256':sha(out),'timeline_sha256':sha(p/'timeline.json'),'draft':rec['draft']}
 save(p/'qa'/f'{name}.check.json',result);print(json.dumps(result,ensure_ascii=False),flush=True)

def main():
 a=argparse.ArgumentParser();a.add_argument('--config');sub=a.add_subparsers(dest='cmd',required=True)
 for cmd in ('init','transcribe','validate','preview','render','check'):
  q=sub.add_parser(cmd);q.add_argument('--project',required=True)
  if cmd=='init':q.add_argument('--source',required=True)
  if cmd=='transcribe':q.add_argument('--replace',action='store_true')
  if cmd in ('validate','render'):q.add_argument('--draft',action='store_true')
  if cmd in ('render','check'):q.add_argument('--name',required=True)
 args=a.parse_args();p=Path(args.project).resolve();c=config(args.config)
 if args.cmd=='init':init(p,args.source,c)
 elif args.cmd=='transcribe':transcribe(p,c,args.replace)
 elif args.cmd=='validate':
  src,_=source(p);validate(read(p/'timeline.json'),src,args.draft);print('结构与时间轴检查通过；不代表成片视听验收')
 elif args.cmd=='preview':preview(p,c)
 elif args.cmd=='render':render(p,c,args.name,args.draft)
 elif args.cmd=='check':check(p,c,args.name)
if __name__=='__main__':
 try:main()
 except Exception as e:print(type(e).__name__+': '+str(e),file=sys.stderr);sys.exit(1)
