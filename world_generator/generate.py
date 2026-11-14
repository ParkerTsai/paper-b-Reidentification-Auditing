"""Portable offline adapter. New packaging code; historical sources unchanged.
No API, credential access, or networking. Refuses existing output directories.
"""
import argparse,ast,copy,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'source_original'))
from core_v85 import make_world,canonical,TEMPORAL_ALIASES
from payloads_v85 import attack_payload

def narrative_functions():
    source=ROOT/'source_original/narrative_candidate.py'
    tree=ast.parse(source.read_text())
    names={'translation','pattern'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'english','replace','standard','natural'} or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
    env={'re':re,'copy':copy,'attack_payload':attack_payload,'TEMPORAL_ALIASES':TEMPORAL_ALIASES}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),env)
    return env

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    frozen=json.loads((ROOT/'data/frozen_worlds.json').read_text())
    maps={x['world_id']:x['mapping'] for x in json.loads((ROOT/'source_original/MAPPINGS.json').read_text())}
    f=narrative_functions();checks=[];rows=[];historical_rows=[];worlds={}
    for wid,old in sorted(frozen.items()):
        w=make_world(wid,master='v8.5-confirmatory-20261019-v1',phase='confirmatory',allow_confirmatory=True)
        assert canonical(w.to_dict())==canonical(old),wid
        worlds[wid]=w.to_dict();m={k:f['english'](v) for k,v in maps[wid].items()}
        for arm in ('D','I','S','SI'):
            coded=[f['standard'](attack_payload(w,arm,t)) for t in range(20)]
            life=[f['natural'](w,arm,t,m) for t in range(20)]
            part=lambda ps:(lambda enc:[[j for j,q in enumerate(enc) if p==q] for p in enc])([canonical(p) for p in ps])
            a,b=part(coded),part(life);assert a==b
            assert all(len(s)==(1 if arm in ('D','I') else 5) for s in a)
            rows.append({'world_id':wid,'arm':arm,'coded_payload':coded[w.target],'lifelike_payload':life[w.target]})
            historical_life=copy.deepcopy(life[w.target]);historical_life['system']=attack_payload(w,arm)['system']
            historical_rows.append({'world_id':wid,'arm':arm,'coded_payload':attack_payload(w,arm),'lifelike_payload':historical_life})
            checks.append({'world_id':wid,'arm':arm,'partition_equal':True,'support_size':len(a[w.target])})
    (out/'worlds.json').write_bytes(canonical(worlds))
    (out/'payloads.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    (out/'luna_haiku_payloads.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in historical_rows))
    (out/'validation.json').write_text(json.dumps({'worlds_exactly_regenerated':len(worlds),'paired_rows':len(rows),'presentations':2*len(rows),'partition_checks':checks},indent=2))
    print(json.dumps({'worlds_exactly_regenerated':len(worlds),'paired_rows':len(rows),'presentations':2*len(rows)}))
if __name__=='__main__': main()
