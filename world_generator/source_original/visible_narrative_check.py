"""Narrow public-input parser/solver, not an LLM or general language evaluator.
No private target, world generator, latent state, mapping sidecar or old answers.
"""
import sys,copy,re,json,gzip,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/workspace/paper1_submission_v7_20261027/reproduction/restored/research')
from core_solver import solve_payload
def solve_natural(p):
 public=p['public'];mech=public['mechanism'];text=p['release']
 if mech=='temporal':
  q=copy.deepcopy(p);q['public'].pop('scenario_context')
  substitutions={'Professional training':'Training','professional training':'training','Community project':'Project','community project':'project',
   'The project review':'Review','The records audit':'Audit','follow-up meeting 1':'M1','follow-up meeting 2':'M2','follow-up meeting 3':'M3','follow-up meeting 4':'M4','the project completion year':'E','the training completion year':'T'}
  pat=re.compile('|'.join(map(re.escape,sorted(substitutions,key=len,reverse=True))))
  q['release']=pat.sub(lambda m:substitutions[m[0]],text)
  return solve_payload(q)['compatible_ids']
 clauses=[]
 for sentence in text.removesuffix('.').split('. '):
  m=re.match(r"(?:The person's|For the person's) assigned service (centre|programme)(.*)",sentence)
  if not m:raise ValueError(('unparsed_sentence',sentence))
  domain='A' if m[1]=='centre' else 'B';tail=m[2];dom=public['domains'][domain]
  if tail.startswith(' is '):
   value=tail[4:];assert value in dom['roots'];clauses.append((domain,'root',value));continue
  if mech=='graph':
   if tail.startswith(' registers an equipment task maintained by an organisation whose registered service area is '):
    end=tail.split(' whose registered service area is ',1)[1];paths=[x for x in dom['paths'] if len(x)==3]
   elif tail.startswith(' registers an equipment task maintained by '):
    end=tail.split(' maintained by ',1)[1];paths=[x for x in dom['paths'] if len(x)==2 and 'registers equipment task' in x[0]['relation']]
   elif tail.startswith(' registers a training course offered by '):
    end=tail.split(' offered by ',1)[1];paths=[x for x in dom['paths'] if len(x)==2 and 'registers training course' in x[0]['relation']]
   else:raise ValueError(('unparsed_graph',tail))
   assert len(paths)==1;clauses.append((domain,'path',(paths[0],end)))
  elif tail.startswith(', none of the following violations occurs:'):
   m=re.fullmatch(r', none of the following violations occurs: absence from any roster in \[(.*?)\]; presence on any roster in \[(.*?)\]',tail);assert m
   for contents,member in [(m[1],True),(m[2],False)]:
    for name in contents.split('; ') if contents else []:clauses.append((domain,'member',(name,member)))
  else:
   m=re.fullmatch(r' (appears|does not appear) on (.+)',tail);assert m
   clauses.append((domain,'member',(m[2],m[1]=='appears')))
 def fits(row):
  for domain,kind,v in clauses:
   root=row[domain];dom=public['domains'][domain]
   if kind=='root' and root!=v:return False
   if kind=='member':
    sets={s['id']:s['members'] for s in dom['sets']};name,member=v
    if (root in sets[name])!=member:return False
   if kind=='path':
    steps,end=v;at={root}
    for step in steps:
     f,t=('from','to') if step['direction']==1 else ('to','from')
     at={e[t] for e in dom['edges'] if e['relation']==step['relation'] and e[f] in at}
    if end not in at:return False
  return True
 return [r['id'] for r in p['candidates'] if fits(r)]
if __name__=='__main__':
 count=0;cases=[]
 with gzip.open(ROOT/'NATURAL_CANDIDATE_PAYLOADS.jsonl.gz','rt',encoding='utf-8') as f:
  for line in f:
   x=json.loads(line);a=solve_payload(x['coded_payload'])['compatible_ids'];b=solve_natural(x['lifelike_payload'])
   assert a==b,(x['world_id'],x['arm'],a,b)
   count+=1;cases.append({'world_id':x['world_id'],'arm':x['arm'],'support_size':len(b),'public_parser_agrees':True})
 result={'cases':count,'all_agree':True,'reads_private_truth':False,'scope':'Narrow declared grammar; selected target releases across all384 worlds/four arms; not human realism validation or LLM control','cases_detail':cases}
 (ROOT/'PUBLIC_SOLVER_CHECK.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='cases_detail'}))
