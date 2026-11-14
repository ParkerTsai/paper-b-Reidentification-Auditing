"""Revised deterministic prompt specification, offline only. No networking."""
import copy,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from core_v85 import attack_payload as original_attack,hybrid_payload as original_hybrid,utility_payload as original_utility
COMMON_CHARTER=('This is a wholly synthetic closed-world task. The supplied pool contains all 20 candidates. '
 'The target is drawn uniformly from these 20 candidates after all public data, candidate records, random aliases, '
 'candidate ordering and wording have been fixed independently of the target. There is no external evidence. '
 'Conditional on the public data and fixed wording, the release is deterministic. Condition on the entire visible '
 'payload; only targets that would produce this same observation have positive channel likelihood. '
 'All aliases have no attribute meaning. Use the supplied public relations to interpret the release.')
PROBABILITY_CONTRACT=(' Return probabilities for all 20 candidate IDs exactly once. Each probability must be finite '
 'and between 0 and 1. The sum must be within 0.001 of 1. compatible_ids must contain all and only compatible '
 'candidate IDs with no duplicates. These are target identity-event probabilities, not confidence in your answer. '
 'Check these requirements before returning JSON.')
MECHANISM_EXPLANATION=('The candidate pool is a 4 by 5 Cartesian product. Direct complete release states both '
 'coordinates; indirect complete release rewrites both through invertible public relations. Partial release '
 'states or rewrites only coordinate A; B-only states only B; joint release combines A and B about the same target. '
 'Temporal A is training-end T and project duration d; B is gap g; shared training duration h is independent of d. '
 'Use P=T+g and E=P+d together with any stated event or milestone constraints. Graph and Boolean coordinates '
 'are the public A/B roots. This paragraph explains the mechanism and does not add new observations about the target.')
ROLES=('system','user')
MODELS={'M1':'openai/gpt-6-luna','M2':'anthropic/claude-haiku-5.5'}
ROUTES={MODELS['M1']:('azure','max_completion_tokens'),MODELS['M2']:('google-vertex/global','max_tokens')}
def attack_payload(world,arm,target=None,explanation=True):
 p=original_attack(world,arm,target,knowledge='reduced');p['system']+=' '+COMMON_CHARTER+PROBABILITY_CONTRACT
 if explanation:p['mechanism_explanation']=MECHANISM_EXPLANATION
 return p

def hybrid_payload(world,arm,target=None):
 p=original_hybrid(world,arm,target);p.pop('rulebook',None);p['mechanism_explanation']=MECHANISM_EXPLANATION
 p['system']+=' '+COMMON_CHARTER
 return p

def utility_payload(world,arm,target=None):return original_utility(world,arm,target)
def api_schema(schema):
 s=copy.deepcopy(schema)
 def walk(x):
  if isinstance(x,dict):
   x.pop('uniqueItems',None)
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(s);return s

def wire(payload,model,utility=False):
 p=copy.deepcopy(payload);instruction=p.pop('system');route,cap=ROUTES[model]
 return {'model':model,'messages':[{'role':'system','content':instruction},{'role':'user','content':json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)}],cap:700 if utility else 1200,'stream':False,'reasoning':{'effort':'none'},'provider':{'only':[route],'order':[route],'allow_fallbacks':False,'require_parameters':True,'zdr':True,'data_collection':'deny','max_price':{'prompt':0.1,'completion':0.5}},'response_format':{'type':'json_schema','json_schema':{'name':'core_v85','strict':True,'schema':api_schema(payload['schema'])}}}

def channel_posterior(world,arm,target,explanation=True):
 observations=[attack_payload(world,arm,t,explanation) for t in range(20)]
 def enc(p):return json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False)
 chosen=enc(observations[target]);support=[t for t,p in enumerate(observations) if enc(p)==chosen]
 return {world.codes[t]:(1/len(support) if t in support else 0) for t in range(20)}
