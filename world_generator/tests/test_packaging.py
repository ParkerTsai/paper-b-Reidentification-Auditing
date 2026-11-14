"""Offline disclosure smoke tests, no model clients."""
import ast,json,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R));import generate
class PackagingTests(unittest.TestCase):
 def test_historical_world(self):
  f=json.loads((R/'data/frozen_worlds.json').read_text());k=sorted(f)[0]
  w=generate.make_world(k,master='v8.5-confirmatory-20261019-v1',phase='confirmatory',allow_confirmatory=True)
  self.assertEqual(generate.canonical(w.to_dict()),generate.canonical(f[k]))
 def test_renderer_functions(self):
  self.assertEqual(set(['english','replace','standard','natural'])-set(generate.narrative_functions()),set())
 def test_no_network_imports(self):
  t=ast.parse((R/'generate.py').read_text())
  imports=[a.name for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names]
  self.assertFalse(set(imports)&{'requests','urllib','httpx','openai','anthropic','socket'})
if __name__=='__main__': unittest.main()
