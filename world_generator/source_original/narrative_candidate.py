"""Offline natural scenario candidate. No model API or executor.
Preserves the original finite population and relations; prose remains reviewable.
"""
from pathlib import Path
import ast,sys,re,json,copy,hashlib,gzip,collections
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
BASE=Path('/workspace/paper1_submission_v7_20261027/reproduction')
sys.path.insert(0,str(BASE/'restored/review_v8_5'))
from core_v85 import World,canonical,TEMPORAL_ALIASES
from payloads_v85 import attack_payload
worlds=json.loads((BASE/'core_audit/original_single_attempt/frozen_worlds.json').read_text())
maps={x['world_id']:x['mapping'] for x in json.loads((ROOT/'MAPPINGS.json').read_text())}
v=ast.parse((ROOT/'validate_all.py').read_text())
env={'copy':copy,'canonical':canonical}
exec(compile(ast.Module(body=[x for x in v.body if isinstance(x,ast.FunctionDef) and x.name=='wire'],type_ignores=[]),'wire','exec'),env)
wire=env['wire']
translation={
 '河東據點':'Riverbank Centre','北站據點':'Northgate Centre','西湖據點':'Westlake Centre','南苑據點':'Southgarden Centre',
 '閱讀服務':'Reading Programme','共餐服務':'Community Meals Programme','接駁服務':'Shuttle Programme','步道維護':'Trail Maintenance Programme','設備檢修':'Equipment Inspection Programme',
 '據點線_':'Site network: ','業務線_':'Programme network: ',
 '照明巡檢':'Lighting Inspection','座椅修護':'Seat Repair','指示牌保養':'Sign Maintenance','門禁檢測':'Access System Testing','通風檢修':'Ventilation Inspection',
 '接待培訓':'Reception Training','急救培訓':'First Aid Training','服務流程培訓':'Service Procedure Training','設備操作培訓':'Equipment Operation Training','志工協作培訓':'Volunteer Coordination Training',
 '青禾維護社':'Greenfield Maintenance','澄川維護社':'Clearwater Maintenance','新橋維護社':'Newbridge Maintenance','平溪維護社':'Brookside Maintenance','映山維護社':'Hillside Maintenance',
 '晨光培訓站':'Morninglight Training','新芽培訓站':'Newleaf Training','和風培訓站':'Breeze Training','青田培訓站':'Meadow Training','溪畔培訓站':'Riverside Training',
 '東岸服務區':'Eastbank Service Area','西橋服務區':'Westbridge Service Area','南湖服務區':'Southlake Service Area','北苑服務區':'Northgarden Service Area','中央服務區':'Central Service Area',
 '登記設備項目':'registers equipment task','登記課程項目':'registers training course','負責維護項目':'maintains task','開設課程項目':'offers course','登記服務區':'registers service area',
 '週末服務':'Weekend Service','平日服務':'Weekday Service','外展協作':'Outreach Cooperation','室內支援':'Indoor Support','巡迴安排':'Mobile Service','預約服務':'Appointment Service',
 '據點名冊':' Site Roster','業務名冊':' Programme Roster'}
pattern=re.compile('|'.join(map(re.escape,sorted(translation,key=len,reverse=True))))
def english(s):return pattern.sub(lambda x:translation[x[0]],s)
def replace(x,m):
 if isinstance(x,dict):return {replace(k,m):replace(v,m) for k,v in x.items()}
 if isinstance(x,list):return [replace(v,m) for v in x]
 if isinstance(x,str):return re.sub(r'(?<![0-9a-f])[0-9a-f]{12}(?![0-9a-f])',lambda z:m.get(z[0],z[0]),x)
 return x
def standard(p):
 p=copy.deepcopy(p)
 p['system']=p['system'].replace('All aliases have no attribute meaning.','Candidate IDs are opaque labels; names of other objects are fixed public labels. Do not infer additional facts from a name or outside knowledge.')
 return p
def natural(w,arm,t,m):
 p=replace(standard(attack_payload(w,arm,t)),m)
 r=w.record(t)
 if w.mechanism=='temporal':
  context=('These are fictional professional-training and community-project records. T is completion of professional training; P and E are the start and end of the community project. Review is the project review and Audit is the records audit. M1 to M4 are successive scheduled follow-up meetings after training completion. All dates and durations use exact whole-year units. Meetings may occur before, during, or after the project; only the stated dates and intervals determine their order. No age, job rank or employment information is available.')
  # Explicit event referents in every family; preserve clause ordering, numbers,
  # inequalities and the original source grammar.
  text=p['release']
  phrases={'Training':'Professional training','training':'professional training','Project':'Community project','project':'community project',
   'Review':'The project review','Audit':'The records audit','M1':'follow-up meeting 1','M2':'follow-up meeting 2','M3':'follow-up meeting 3','M4':'follow-up meeting 4'}
  pat=re.compile(r'\b('+ '|'.join(map(re.escape,phrases))+r')\b')
  text=pat.sub(lambda z:phrases[z[0]],text)
  text=re.sub(r'\bE\b','the project completion year',text)
  text=re.sub(r'\bT\b','the training completion year',text)
 else:
  context=('This is a fictional community-service assignment register. Each candidate is assigned one service centre (A) and one service programme (B); every listed combination is possible. Assignment does not imply employment, age, seniority or any additional personal characteristic. The two public networks are separate. The load values and zone labels are administrative fields with no unstated implications.')
  if w.mechanism=='graph':context+=' Each stated route starts again at the same assigned object; separate routes are not concatenated. Relations denote recorded registrations, maintenance responsibilities or course provision, not temporal succession.'
  else:context+=' Each roster lists all and only its members. Rosters contain centres or programmes, not people. Rosters may overlap. A name is a registration category, not evidence of any extra eligibility requirement.'
  clauses=[]
  domains=['A','B'] if arm in ('D','I') else ['A']
  if w.family==2:domains.reverse()
  for domain in domains:
   noun='assigned service centre' if domain=='A' else 'assigned service programme'
   root=r[domain];dom=w.public['domains'][domain]
   if arm in ('D','S'):clauses.append('The person\'s '+noun+' is '+m[root]+'.');continue
   if w.mechanism=='graph':
    for pi,path in enumerate(dom['paths']):
     current={root};steps=[]
     for step in path:
      edges=[e for e in dom['edges'] if e['relation']==step['relation']]
      f,to=('from','to') if step['direction']==1 else ('to','from')
      current={e[to] for e in edges if e[f] in current}
      steps.append(('follow' if step['direction']==1 else 'follow in reverse')+' the relation "'+m[step['relation']]+'"')
     assert len(current)==1
     terminal=next(iter(current))
     directions=[s['direction'] for s in path]
     relations=[m[s['relation']] for s in path]
     if len(path)==3:
      assert directions==[1,-1,1]
      assert 'registers equipment task' in relations[0] and 'maintains task' in relations[1] and 'registers service area' in relations[2]
      clauses.append('The person\'s '+noun+' registers an equipment task maintained by an organisation whose registered service area is '+m[terminal]+'.')
     elif 'registers equipment task' in relations[0]:
      assert directions==[1,-1] and 'maintains task' in relations[1]
      clauses.append('The person\'s '+noun+' registers an equipment task maintained by '+m[terminal]+'.')
     else:
      assert directions==[1,-1] and 'registers training course' in relations[0] and 'offers course' in relations[1]
      clauses.append('The person\'s '+noun+' registers a training course offered by '+m[terminal]+'.')
   else:
    positive=[m[s['id']] for s in dom['sets'] if root in s['members']]
    negative=[m[s['id']] for s in dom['sets'] if root not in s['members']]
    if w.structure=='grouped_negation':
     clauses.append('For the person\'s '+noun+', none of the following violations occurs: absence from any roster in ['+'; '.join(positive)+']; presence on any roster in ['+'; '.join(negative)+'].')
    else:
     for s in dom['sets']:clauses.append('The person\'s '+noun+(' appears on ' if root in s['members'] else ' does not appear on ')+m[s['id']]+'.')
  text=' '.join(clauses)
 # Context is a function of mechanism only, shared by all four conditions and
 # every counterfactual target. It never supplies a selected B value.
 p['public']['scenario_context']=context
 p['release']=text
 return p
checks=[];examples={};rows=0
with gzip.open(ROOT/'NATURAL_CANDIDATE_PAYLOADS.jsonl.gz','wt',encoding='utf-8') as out:
 for wid,d in sorted(worlds.items()):
  w=World(**{**d,'codes':tuple(d['codes']),'order':tuple(d['order']),'priority':tuple(d['priority'])})
  m={k:english(v) for k,v in maps[wid].items()};assert len(m)==len(set(m.values()))
  full={};chosen={}
  for arm in ['D','I','S','SI']:
   src=[];dst=[];contexts=set()
   for t in range(20):
    p=standard(attack_payload(w,arm,t));q=natural(w,arm,t,m)
    a,b=wire(p,'none'),wire(q,'none')
    assert a['response_format']==b['response_format']
    assert p['schema']==q['schema']
    assert [x['id'] for x in p['candidates']]==[x['id'] for x in q['candidates']]
    assert not re.search(r'[\u4e00-\u9fff]',json.dumps(q,ensure_ascii=False))
    low=wire(q,'low');low['reasoning']['effort']='none';assert low==b
    src.append(canonical(a));dst.append(canonical(b));contexts.add(q['public']['scenario_context'])
    rows+=1
    if t==w.target:chosen[arm]={'coded_payload':p,'lifelike_payload':q}
   assert len(contexts)==1
   part=lambda ss:[[j for j,y in enumerate(ss) if x==y] for x in ss]
   po,pn=part(src),part(dst);assert po==pn
   full[arm]=pn
   assert all(len(x)==(1 if arm in ('D','I') else 5) for x in pn)
   out.write(json.dumps({'world_id':wid,'arm':arm,**chosen[arm]},ensure_ascii=False)+'\n')
  assert full['D']==full['I'] and full['S']==full['SI']
  checks.append({'world_id':wid,'mechanism':w.mechanism,'finite_partition_equivalent':True,'candidate_identifiers_identical':True,'target_independent_context':True,'semantics_status':'TEMPLATE_AND_CASE_REVIEW_REQUIRED'})
  if w.mechanism not in examples:examples[w.mechanism]={'world_id':wid,'arms':chosen}
(ROOT/'NATURAL_VALIDATION.json').write_text(json.dumps({'status':'CANDIDATE_GENERATED_NOT_FROZEN','paired_fullinput_checks':rows,'all384_partitions_match':True,'languages':'English in both presentations','candidate_IDs':'original opaque IDs unchanged in both','semantic_review_complete':False,'checks':checks},indent=2)+'\n')
(ROOT/'NATURAL_EXAMPLES.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'paired_fullinput_checks':rows,'worlds':len(checks),'semantic_review_complete':False}))
