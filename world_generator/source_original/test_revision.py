import unittest,json,sys,math
from pathlib import Path
P=Path(__file__).resolve().parent
from core_v85 import make_world
from payloads_v85 import attack_payload,wire,MODELS,COMMON_CHARTER
from metrics_v85 import score_with_baselines
class RevisionTests(unittest.TestCase):
 def setUp(self):
  self.ids=[f'{i:012x}' for i in range(20)];self.q={k:float(i==0) for i,k in enumerate(self.ids)};self.priority=list(self.ids);self.uniform={'compatible_ids':self.ids,'probabilities':{k:.05 for k in self.ids}}
 def test_baseline_policies_differ(self):
  s=score_with_baselines(json.dumps(self.uniform),self.ids,self.q,self.ids[0],self.priority)
  self.assertEqual(s['A'],1);self.assertAlmostEqual(s['e'],.05);self.assertEqual(s['uniform_fixed_priority_conditional_success'],1);self.assertEqual(s['uniform_random_decision_expected_success'],.05)
  self.assertAlmostEqual(s['posterior_squared_error'],.95);self.assertEqual(s['decision_regret_uniform_ties_bounds'],s['oracle_gap_bounds'])
 def test_non_degenerate_posterior_policy_difference(self):
  q={k:.2 if i<5 else 0. for i,k in enumerate(self.ids)}
  s=score_with_baselines(json.dumps(self.uniform),self.ids,q,self.ids[3],self.priority)
  self.assertEqual(s['uniform_fixed_priority_conditional_success'],.2);self.assertAlmostEqual(s['e'],.05);self.assertEqual(s['A'],0)
 def test_invalid_not_repaired(self):
  bad={'compatible_ids':self.ids,'probabilities':{k:.052 for k in self.ids}}
  s=score_with_baselines(json.dumps(bad),self.ids,self.q,self.ids[0],self.priority)
  self.assertEqual(s['A'],0);self.assertIsNone(s['posterior_squared_error']);self.assertFalse(s['normalization_applied']);self.assertIsNone(s['posterior_total_variation'])
 def test_missing_is_not_zero(self):
  for status in ['unissued','transport_unknown']:
   s=score_with_baselines(None,self.ids,self.q,self.ids[0],self.priority,status=status)
   self.assertIsNone(s['A']);self.assertIsNone(s['e']);self.assertEqual(s['A_bounds'],[0,1]);self.assertEqual(s['decision_regret_uniform_ties_bounds'],[0,1])
 def test_set_error_does_not_erase_probability(self):
  answer={'compatible_ids':[self.ids[0],self.ids[0]],'probabilities':self.q}
  s=score_with_baselines(json.dumps(answer),self.ids,self.q,self.ids[0],self.priority)
  self.assertFalse(s['compatible_ids_valid']);self.assertTrue(s['usable_probabilities']);self.assertEqual(s['A'],1)
 def test_prior_and_role_are_fixed(self):
  w=make_world('validation-test',mechanism_override='graph',structure_override=1,family_override=2)
  for arm in ['D','I','S','SI','B','joint']:
   full=attack_payload(w,arm);reduced=attack_payload(w,arm,explanation=False)
   self.assertEqual(full['system'],reduced['system']);self.assertIn(COMMON_CHARTER,full['system'])
   full.pop('mechanism_explanation');self.assertEqual(full,reduced)
   for m in MODELS.values():
    req=wire(reduced,m);self.assertEqual([x['role'] for x in req['messages']],['system','user']);self.assertNotIn('system',json.loads(req['messages'][1]['content']))
 def test_confirmatory_not_accidentally_generated(self):
  with self.assertRaises(ValueError):make_world('confirmatory-v85-main-0000',master='fresh',phase='confirmatory')
  with self.assertRaises(ValueError):make_world('confirmatory-v85-main-0000',master='fresh',phase='confirmatory',allow_confirmatory=True,mechanism_override='graph')
 def test_schedule_denominators(self):
  rows=json.loads((P/'core_main_schedule_plan.json').read_text())['calls'];self.assertEqual(len(rows),6144)
  self.assertEqual(len({r['world_id'] for r in rows}),384)
  self.assertEqual(sum(r['task']=='utility' for r in rows),1152)
  for m in MODELS.values():
   direct=[r for r in rows if r['model_id']==m and r['variant']=='direct'];self.assertEqual(len(direct),1536)
   for world in {r['world_id'] for r in direct}:self.assertEqual({r['arm'] for r in direct if r['world_id']==world},{'D','I','S','SI'})
  self.assertTrue(all(r['execution_permitted'] is False for r in rows))
if __name__=='__main__':unittest.main()
