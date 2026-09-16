import json,os,sys,subprocess,webbrowser,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'_support/project.json').read_text(encoding='utf-8'))
os.chdir(ROOT)
check='--check' in sys.argv; no_open='--no-open' in sys.argv
mode=CFG['mode']; output=ROOT/CFG['output']
if mode=='placeholder':
 print('This project does not have an implemented application yet. See _support/STATUS.md.');sys.exit(0 if check else 1)
for entry in CFG['code']:
 if not (ROOT/entry).exists():raise SystemExit('Missing code: '+entry)
if mode=='static':
 if not output.exists():raise SystemExit('Missing HTML output')
 if not check and not no_open:webbrowser.open(output.as_uri())
 print('OK: '+str(output));sys.exit(0)
for module in CFG['imports']:__import__(module)
env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+str(ROOT);env['PORTAL_LOCAL']='1'
if check:
 print('OK: '+CFG['project']+' | code and Python imports | '+CFG['output']);sys.exit(0)
cmd=[sys.executable,'-X','utf8',*CFG['args']]
if no_open and CFG['project']=='finance-market-making-dashboard':cmd.append('--no-open')
if '--offline' in sys.argv and CFG['project']=='finance-nav-dashboard':cmd.append('--skip-codal-refresh')
if mode in ('server','news','codal'):
 url='http://127.0.0.1:'+str(CFG['port'])+'/'+CFG.get('url_path','')
 def ready():
  try:
   with urllib.request.urlopen(url,timeout=2) as r:return r.status==200
  except Exception:return False
 if not ready():
  log=ROOT/'_support/run.log'
  with log.open('ab') as f:
   process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=f,stderr=f,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
  for _ in range(40):
   if ready():break
   if process.poll() is not None:raise SystemExit('Startup failed. See _support/run.log')
   time.sleep(.5)
  else:raise SystemExit('Server did not respond. See _support/run.log')
 if not no_open:webbrowser.open(url)
 print('Running: '+url);sys.exit(0)
if no_open:env.update(NAV_NO_BROWSER='1',MARKET_MAKING_NO_OPEN='1',PORTFOLIO_NO_OPEN='1')
result=subprocess.run(cmd,cwd=ROOT,env=env)
if result.returncode:sys.exit(result.returncode)
if mode=='export':
 if not output.exists():raise SystemExit('Expected output was not created: '+str(output))
 if not no_open and CFG['project'] in ('finance-nav-dashboard','finance-pars-aryan-budget'):webbrowser.open(output.as_uri())
 print('Output: '+str(output))
