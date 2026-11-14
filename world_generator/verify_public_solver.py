"""Portable adapter for the original narrow public-input solver.
Only reads supplied payloads, never frozen worlds, target labels or mapping files.
"""
import argparse,ast,copy,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'source_original'))
from core_solver import solve_payload
source=ROOT/'source_original/visible_narrative_check.py'
tree=ast.parse(source.read_text())
env={'copy':copy,'re':re,'solve_payload':solve_payload}
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='solve_natural'],type_ignores=[]),str(source),'exec'),env)
ap=argparse.ArgumentParser();ap.add_argument('payloads_jsonl');args=ap.parse_args();count=0
for line in Path(args.payloads_jsonl).open():
    row=json.loads(line)
    a=solve_payload(row['coded_payload'])['compatible_ids']
    b=env['solve_natural'](row['lifelike_payload'])
    assert a==b,(row['world_id'],row['arm'])
    count+=1
print(json.dumps({'public_input_solver_cases':count,'all_agree':True,'uses_hidden_truth':False}))
