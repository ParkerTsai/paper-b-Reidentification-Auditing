"""v8.4.1 offline synthetic core; this module never invokes models or networking."""
from dataclasses import dataclass, asdict
from itertools import combinations
import hashlib
import json
import random
import re

VERSION = 'v8.5.0-review-only'
ARMS = ('D', 'I', 'S', 'SI', 'B', 'joint')
MECHANISMS = ('temporal', 'graph', 'boolean')
MAIN_N = 384
CODE_WIDTH = 12
BOOLEAN_MAX_ATTEMPTS = 1024
CODE_MAX_ATTEMPTS = 100000
SYSTEM = ('Solve this wholly fictional closed-world linkage task using only the supplied evidence. '
          'compatible_ids means ALL candidate codes consistent with the complete visible evidence. '
          'probabilities means the conditional probability that EACH candidate is the target, given the stated '
          'mechanism, prior and visible evidence; these are identity-event probabilities, not confidence in answering. '
          'Return JSON only. Do not provide reasoning.')
RULEBOOK = ('The pool is complete and contains 20 candidates in a 4 by 5 Cartesian product. The target is drawn '
            'uniformly after all public data, random aliases, ordering and wording have been fixed independently of it. '
            'There is no external evidence. Every alias is a unique fixed-width random string without attribute meaning. '
            'Conditional on the public data and fixed wording, release is deterministic. D reveals both coordinates; '
            'I rewrites both using invertible public constraints; S reveals only A; SI rewrites only A; B reveals only B. '
            'The joint release combines S and B about the SAME target. Temporal A comprises training-end T and duration d; '
            'B is gap g. D supplies T,P,d,h; I supplies E or its audit anchor, g,d,h; S/SI supply T or its milestone anchor,d,h; '
            'B supplies g. Temporal h is shared, independent of d, and d is a random permutation of 3,3,4,4. '
            'Graph and Boolean A/B are their public roots. All public auxiliaries and metadata are identical across arms. '
            'Only observations equal to the full visible payload have nonzero deterministic channel likelihood.')
TEMPORAL_ALIASES = {
    0: ('Training ended in ', 'Project started in ', 'Project ended in ', 'Project lasted ', 'Training lasted ', 'The gap was ', ' followed ', ' occurred in '),
    1: ('The training completion year was ', 'The project start year was ', 'The project finish year was ', 'The project duration was ', 'The training duration was ', 'The elapsed gap was ', ' came after ', ' had year '),
    2: ('Training finished in ', 'Project began in ', 'Project finished in ', 'Project duration equaled ', 'Training duration equaled ', 'The interval was ', ' was later than ', ' was dated '),
    3: ('Training completion: ', 'Project commencement: ', 'Project completion: ', 'Project activity: ', 'Training activity: ', 'Gap: ', ' succeeded ', ' took place in '),
}

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')

def seed(master, phase, world_id, purpose):
    return int.from_bytes(hashlib.sha256(canonical([master, phase, str(world_id), purpose])).digest(), 'big')

@dataclass(frozen=True)
class World:
    world_id: str
    phase: str
    mechanism: str
    structure: str
    family: int
    public: dict
    latent: dict
    codes: tuple
    order: tuple
    priority: tuple
    target: int

    def to_dict(self):
        return asdict(self)

    def record(self, t):
        if isinstance(t, bool) or not isinstance(t, int) or not 0 <= t < 20:
            raise ValueError('Target index must be an integer from 0 to 19')
        a, b = divmod(t, 5)
        if self.mechanism == 'temporal':
            T = self.latent['y'] + self.latent['offsets'][a]
            return {'id': self.codes[t], 'T': T, 'P': T + self.latent['gaps'][b],
                    'd': self.latent['durations'][a], 'h': self.public['h']}
        return {'id': self.codes[t], 'A': self.public['domains']['A']['roots'][a],
                'B': self.public['domains']['B']['roots'][b]}

    def private_truth(self, t=None):
        row = self.record(self.target if t is None else t)
        if self.mechanism == 'temporal':
            row.update(E=row['P'] + row['d'], g=row['P'] - row['T'])
        return row

class _Aliases:
    def __init__(self, rng):
        self.rng, self.used = rng, set()
    def get(self):
        for _ in range(CODE_MAX_ATTEMPTS):
            s = format(self.rng.getrandbits(48), '012x')
            if s not in self.used:
                self.used.add(s)
                return s
        raise RuntimeError('Alias rejection limit reached; generation failed')
    def many(self, n):
        return [self.get() for _ in range(n)]

def _graph_domain(n, structure, aliases, rng):
    roots = aliases.many(n)
    attrs = {x: {'load': rng.randint(1, 9), 'zone': rng.choice(['north', 'south'])} for x in roots}
    edges, paths, endpoints = [], [], {}
    if structure in ('chain', 'dev_single_edge'):
        depth = 3 if structure == 'chain' else 1
        current = roots[:]
        path = []
        for layer in range(depth):
            nxt = aliases.many(n)
            rng.shuffle(nxt)
            rel = aliases.get()
            direction = 1 if layer % 2 == 0 else -1
            for x, y in zip(current, nxt):
                edges.append({'relation': rel, 'from': x if direction == 1 else y,
                              'to': y if direction == 1 else x})
            path.append({'relation': rel, 'direction': direction})
            current = nxt
        paths.append(path)
        endpoints = {root: [terminal] for root, terminal in zip(roots, current)}
    else:
        cols = 2 if n == 4 else 3
        cells = [(i, j) for i in range(2) for j in range(cols)]
        rng.shuffle(cells)
        cells = cells[:n]
        endpoints = {x: [] for x in roots}
        for axis, count in ((0, 2), (1, cols)):
            terminals, mids = aliases.many(count), aliases.many(n)
            rng.shuffle(terminals)
            r1, r2 = aliases.get(), aliases.get()
            for root, mid, cell in zip(roots, mids, cells):
                terminal = terminals[cell[axis]]
                edges.extend([{'relation': r1, 'from': root, 'to': mid},
                              {'relation': r2, 'from': terminal, 'to': mid}])
                endpoints[root].append(terminal)
            paths.append([{'relation': r1, 'direction': 1}, {'relation': r2, 'direction': -1}])
    rng.shuffle(edges)
    return {'roots': roots, 'attributes': attrs, 'edges': edges, 'paths': paths}, endpoints

def _boolean_domain(n, k, aliases, rng):
    roots = aliases.many(n)
    choices = [list(c) for size in range(2, n - 1) for c in combinations(roots, size)]
    for attempt in range(1, BOOLEAN_MAX_ATTEMPTS + 1):
        subsets = rng.sample(choices, k)
        signatures = [tuple(root in members for members in subsets) for root in roots]
        if len(set(signatures)) == n:
            sets = []
            for members in subsets:
                members = members[:]
                rng.shuffle(members)
                sets.append({'id': aliases.get(), 'members': members})
            return {'roots': roots, 'sets': sets}, attempt
    raise RuntimeError('Boolean matrix rejection limit reached; generation failed')

def make_world(world_id, master='v8.5.0-development', phase='validation', *, mechanism_override=None, structure_override=None, family_override=None, allow_confirmatory=False):
    if phase not in ('validation', 'confirmatory'):
        raise ValueError('v8.5 permits validation or explicitly gated confirmatory phase only')
    if phase == 'confirmatory':
        if not allow_confirmatory or master == 'v8.5.0-development':
            raise ValueError('confirmatory_generation_not_authorized_by_this_offline_review')
        if any(v is not None for v in (mechanism_override, structure_override, family_override)):
            raise ValueError('confirmatory_iid_sampling_cannot_use_overrides')
    elif not str(world_id).startswith('validation-'):
        raise ValueError('validation namespace required')
    def rng(p):
        return random.Random(seed(master, phase, world_id, p))
    mechanism = rng('mechanism').choice(MECHANISMS)
    pilot_mechanisms = {'core-pilot-0000': 'temporal', 'core-pilot-0001': 'graph', 'core-pilot-0002': 'boolean'}
    if phase == 'pilot' and str(world_id) in pilot_mechanisms:
        mechanism = pilot_mechanisms[str(world_id)]
    if mechanism_override is not None:
        if mechanism_override not in MECHANISMS:raise ValueError('invalid mechanism override')
        mechanism = mechanism_override
    variant = rng('structure').randrange(2) if structure_override is None else structure_override
    family = rng('family').randrange(3) if family_override is None else family_override
    if variant not in (0,1) or family not in (0,1,2):raise ValueError('invalid validation stratum')
    aliases = _Aliases(rng('aliases'))
    codes = tuple(aliases.many(20))
    latent = {}
    if mechanism == 'temporal':
        r = rng('temporal')
        y = r.randint(1980, 2005)
        offsets = sorted([0, 6] + r.sample(range(1, 6), 2))
        gaps = sorted([1, 9] + r.sample(range(2, 9), 3))
        durations = [3, 3, 4, 4]
        rng('durations').shuffle(durations)
        shifts = [r.randint(1, 3) for _ in range(4)]
        h = rng('training_length').choice([1, 2])
        structure = ('two_event', 'four_event')[variant]
        public = {'mechanism': mechanism, 'h': h, 'shifts': shifts,
                  'allowed': {'T': [y, y + 6], 'g': [1, 9], 'd': [3, 4]},
                  'relations': 'P=T+g; E=P+d. All years are exact. Intervals are left-closed and right-open. Before means strictly earlier.'}
        latent = {'y': y, 'offsets': offsets, 'gaps': gaps, 'durations': durations}
    elif mechanism == 'graph':
        structure = ('chain', 'fork')[variant] if phase in ('validation','confirmatory') else 'dev_single_edge'
        domains, ends = {}, {}
        for d, n in (('A', 4), ('B', 5)):
            domains[d], ends[d] = _graph_domain(n, structure, aliases, rng('graph_' + d))
        public = {'mechanism': mechanism, 'domains': domains,
                  'relations': 'Each edge is directed from its from-node to its to-node. A + step follows that direction; a - step reverses it. A path must traverse all listed steps in order.',
                  'task_terminal': ends['A'][domains['A']['roots'][0]][0]}
        latent = {'endpoints': ends}
    else:
        structure = ('conjunction', 'grouped_negation')[variant] if phase in ('validation','confirmatory') else 'dev_literals'
        k = (4 if structure == 'conjunction' else 6) if phase in ('validation','confirmatory') else 3
        domains, attempts = {}, {}
        for d, n in (('A', 4), ('B', 5)):
            domains[d], attempts[d] = _boolean_domain(n, k, aliases, rng('boolean_' + d))
        public = {'mechanism': mechanism, 'domains': domains,
                  'relations': 'A listed set contains exactly its listed members. Inside means membership, outside means non-membership. No listed violation occurs means every individual listed violation is false; an empty violation list imposes no restriction.'}
        latent = {'matrix_attempts': attempts}
    order = list(range(20)); rng('candidate_order').shuffle(order)
    priority = list(codes); rng('tie_priority').shuffle(priority)
    return World(str(world_id), phase, mechanism, structure, family, public, latent, codes,
                 tuple(order), tuple(priority), rng('target').randrange(20))

def _temporal_text(w, clauses):
    source = TEMPORAL_ALIASES[0]
    target = TEMPORAL_ALIASES[w.family]
    if w.family == 1:
        clauses = clauses[1:] + clauses[:1]
    elif w.family == 2:
        clauses = list(reversed(clauses))
    elif w.family == 3:
        clauses = clauses[::2] + clauses[1::2]
    text = ' '.join(clauses)
    text = re.sub(r'(?<![0-9])1 years\b', '1 year', text)
    for old, new in zip(source, target):
        text = text.replace(old, new)
    return text

def _root_text(domain, root, family):
    return (f'The selected {domain} root is {root}.',
            f'For domain {domain}, the root is {root}.',
            f'{root} is the selected root in domain {domain}.',
            f'Domain {domain} root = {root}.')[family]

def _path_string(path):
    return ','.join(('+' if step['direction'] == 1 else '-') + step['relation'] for step in path)

def _indirect_text(w, domain, root):
    info = w.public['domains'][domain]
    if w.mechanism == 'graph':
        pieces = []
        for path, terminal in zip(info['paths'], w.latent['endpoints'][domain][root]):
            steps = _path_string(path)
            pieces.append((f'The selected {domain} root follows {steps} to {terminal}.',
                           f'For domain {domain}, following {steps} ends at {terminal}.',
                           f'{terminal} is reached from domain {domain} root along {steps}.',
                           f'Domain {domain} path {steps} = {terminal}.')[w.family])
    elif w.structure == 'grouped_negation':
        positive = ','.join(s['id'] for s in info['sets'] if root in s['members'])
        negative = ','.join(s['id'] for s in info['sets'] if root not in s['members'])
        pieces = [(f'For the selected {domain} root, none of these violations occurs: being outside any set in [{positive}]; being inside any set in [{negative}].',
                   f'For domain {domain}, every listed violation is false: outside any set in [{positive}]; inside any set in [{negative}].',
                   f'It is false that domain {domain} root is outside any set in [{positive}] or inside any set in [{negative}].')[w.family]]
    else:
        pieces = []
        for s in info['sets']:
            inside = root in s['members']; sid = s['id']
            pieces.append((f'The selected {domain} root is {"inside" if inside else "outside"} set {sid}.',
                           f'For domain {domain}, the root {"belongs" if inside else "does not belong"} to set {sid}.',
                           f'Set {sid} {"contains" if inside else "does not contain"} the selected {domain} root.',
                           f'Domain {domain} membership in {sid} = {str(inside).lower()}.')[w.family])
    return pieces

def release(w, arm, t=None):
    if arm not in ARMS:
        raise ValueError('Unknown arm')
    r = w.private_truth(t)
    if arm == 'joint':
        return release(w, 'S', t) + '\n' + release(w, 'B', t)
    if w.mechanism == 'temporal':
        T, P, E, d, h, g = (r[k] for k in ('T', 'P', 'E', 'd', 'h', 'g'))
        shifts = w.public['shifts']; depth = 2 if w.structure == 'two_event' else 4
        lengths = [f'Project lasted {d} years.', f'Training lasted {h} years.']
        if arm == 'D':
            clauses = [f'Training ended in {T}.', f'Project started in {P}.'] + lengths
        elif arm == 'I':
            clauses = ([f'Project ended in {E}.'] if depth == 2 else
                       [f'Review followed E by {shifts[0]} years.', f'Audit followed Review by {shifts[1]} years.',
                        f'Audit occurred in {E + shifts[0] + shifts[1]}.'])
            clauses += lengths + [f'The gap was {g} years.']
        elif arm == 'S':
            clauses = [f'Training ended in {T}.'] + lengths
        elif arm == 'SI':
            clauses = [f'M{j + 1} followed {"T" if j == 0 else "M" + str(j)} by {shifts[j]} years.' for j in range(depth)]
            clauses += [f'M{depth} occurred in {T + sum(shifts[:depth])}.'] + lengths
        else:
            clauses = [f'The gap was {g} years.']
        return _temporal_text(w, clauses)
    direct = arm in ('D', 'S', 'B')
    domains = ['A', 'B'] if arm in ('D', 'I') else ['B'] if arm == 'B' else ['A']
    pieces = []
    for domain in domains:
        pieces += [_root_text(domain, r[domain], w.family)] if direct else _indirect_text(w, domain, r[domain])
    if w.family == 2:
        pieces.reverse()
    return ' '.join(pieces)

def attack_payload(w, arm, t=None, knowledge='full'):
    if knowledge not in ('full', 'reduced'):
        raise ValueError('knowledge must be full or reduced')
    ids = [w.codes[i] for i in w.order]
    schema = {'type': 'object', 'required': ['compatible_ids', 'probabilities'], 'additionalProperties': False,
              'properties': {'compatible_ids': {'type': 'array', 'description': 'All and only compatible candidate IDs.',
                                               'uniqueItems': True, 'items': {'type': 'string', 'enum': ids}},
                             'probabilities': {'type': 'object', 'description': 'Identity-event probabilities. Finite values in [0,1]; sum within 0.001 of 1. All 20 IDs exactly once.',
                                               'required': ids, 'additionalProperties': False,
                                               'properties': {i: {'type': 'number', 'minimum': 0, 'maximum': 1} for i in ids}}}}
    payload = {'system': SYSTEM, 'public': w.public, 'candidates': [w.record(i) for i in w.order],
               'release': release(w, arm, t), 'schema': schema}
    if knowledge == 'full':
        payload['rulebook'] = RULEBOOK
    return payload

def hybrid_payload(w, arm, t=None):
    """One extraction call, then the independent visible constraint solver.

    Uses the same public evidence and candidate table as direct attack; API
    input/output ceilings are identical, not total computation or exact tokens.
    """
    payload = attack_payload(w, arm, t)
    event_fields = ['T', 'P', 'E', 'Review', 'Audit', 'M1', 'M2', 'M3', 'M4']
    code = {'type': 'string', 'pattern': '^[0-9a-f]{12}$'}
    domain = {'type': 'string', 'enum': ['A', 'B']}
    def clause(op, fields):
        properties = {'op': {'type': 'string', 'enum': [op]}, **fields}
        return {'type': 'object', 'required': list(properties), 'additionalProperties': False, 'properties': properties}
    all_clauses = {
        'eq': clause('eq', {'field': {'type': 'string', 'enum': event_fields + ['d', 'h', 'g']}, 'value': {'type': 'integer'}}),
        'difference': clause('difference', {'left': {'type': 'string', 'enum': event_fields}, 'right': {'type': 'string', 'enum': event_fields}, 'value': {'type': 'integer'}}),
        'root': clause('root', {'domain': domain, 'value': code}),
        'path': clause('path', {'domain': domain, 'steps': {'type': 'array', 'minItems': 1, 'maxItems': 4, 'items': {
            'type': 'object', 'required': ['relation', 'direction'], 'additionalProperties': False,
            'properties': {'relation': code, 'direction': {'type': 'integer', 'enum': [-1, 1]}}}}, 'terminal': code}),
        'member': clause('member', {'domain': domain, 'set': code, 'value': {'type': 'boolean'}}),
    }
    ops = {'temporal': ['eq', 'difference'], 'graph': ['root', 'path'], 'boolean': ['root', 'member']}[w.mechanism]
    payload['system'] = (
        'Extract all and only constraints explicitly stated in the fictional release into the specified JSON AST. '
        'Do not identify the target, infer extra facts, or output candidate probabilities. No reasoning is requested. '
        'version is 1; mechanism is the public mechanism; clauses is the list of explicit constraints. '
        'Temporal eq assigns a stated event year or scalar duration/gap; difference means left = right + value. '
        'Training completion is T, project start P, project end E, training duration h, project duration d, elapsed gap g; '
        'use event names Review, Audit and M1 through M4 exactly. '
        'Graph root assigns a stated domain root; path records signed relation steps in order and its stated terminal. '
        'Boolean member records positive/negative membership. In grouped no-violation statements, outside-list sets '
        'require membership true and inside-list sets require membership false; empty lists add no clauses. '
        'Public auxiliary facts define meanings and are not themselves release clauses. Return JSON only.')
    payload['schema'] = {'type': 'object', 'required': ['version', 'mechanism', 'clauses'], 'additionalProperties': False,
                         'properties': {'version': {'type': 'integer', 'enum': [1]},
                                        'mechanism': {'type': 'string', 'enum': [w.mechanism]},
                                        'clauses': {'type': 'array', 'minItems': 1, 'maxItems': 32,
                                                    'items': {'anyOf': [all_clauses[op] for op in ops]}}}}
    return payload


def exact_posterior(w, arm, observation=None):
    observed = canonical(attack_payload(w, arm)) if observation is None else observation
    if not isinstance(observed, bytes):
        observed = canonical(observed)
    likelihood = [int(canonical(attack_payload(w, arm, t)) == observed) for t in range(20)]
    denominator = sum(likelihood)
    if denominator == 0:
        raise ValueError('Observation is outside the full-payload channel support')
    return {w.codes[t]: likelihood[t] / denominator for t in range(20)}

def channel_partition(w, arm):
    groups = {}
    for t in range(20):
        groups.setdefault(canonical(attack_payload(w, arm, t)), []).append(t)
    return list(groups.values())

def utility_payload(w, arm, t=None):
    if arm not in ('D', 'I', 'S'):
        raise ValueError('Utility is measured only in D, I and S')
    if w.mechanism == 'temporal':
        y = w.latent['y']
        questions = [
            ('local', 'How many years did the project last?', {'op': 'value', 'field': 'd'}),
            ('local', 'How many years did the training last?', {'op': 'value', 'field': 'h'}),
            ('relational', 'How many years elapsed from training completion to project start?', {'op': 'value', 'field': 'g'}),
            ('relational', f'Did the project interval [start,end) overlap the interval [{y + 8},{y + 10})?', {'op': 'overlap', 'start': y + 8, 'end': y + 10}),
            ('operational', f'Was the project started strictly before the start deadline {y + 8}?', {'op': 'before', 'field': 'P', 'cutoff': y + 8}),
            ('operational', f'Was the project completed strictly before the completion deadline {y + 12}?', {'op': 'before', 'field': 'E', 'cutoff': y + 12})]
        rules = 'Allowed records have any integer T in the public inclusive T range, any integer g in the inclusive g range, d from the public list, and shared h. P=T+g; E=P+d. No other constraints or roster apply.'
    elif w.mechanism == 'graph':
        path = w.public['domains']['A']['paths'][0]; terminal = w.public['task_terminal']
        questions = [
            ('local', 'What load is assigned to the selected A root?', {'op': 'attribute', 'domain': 'A', 'field': 'load'}),
            ('local', 'What zone is assigned to the selected A root?', {'op': 'attribute', 'domain': 'A', 'field': 'zone'}),
            ('relational', f'Does the selected A root reach {terminal} along the path {_path_string(path)}?', {'op': 'reaches', 'domain': 'A', 'path': path, 'terminal': terminal}),
            ('relational', 'Are the selected A and B roots in the same zone?', {'op': 'same_zone'}),
            ('operational', 'A task is eligible exactly when the sum of A and B loads is at most 10. Is this task eligible?', {'op': 'load_limit', 'limit': 10}),
            ('operational', 'Dispatch to the zone of the root with the lower load; choose A on an equal load. Which zone is selected?', {'op': 'dispatch'})]
        rules = 'Every combination of one public A root and one public B root is allowed. Public directed edges, path directions and attributes define the task. No candidate IDs or roster apply.'
    else:
        sets = {d: w.public['domains'][d]['sets'] for d in ('A', 'B')}
        a0, a1, a2, az = (sets['A'][i]['id'] for i in (0, 1, 2, -1))
        b0, b1, b2, bz = (sets['B'][i]['id'] for i in (0, 1, 2, -1))
        questions = [
            ('local', f'Does the selected A root belong to set {a0}?', {'op': 'member', 'domain': 'A', 'set': a0}),
            ('local', f'Does the selected A root belong to set {a1}?', {'op': 'member', 'domain': 'A', 'set': a1}),
            ('relational', f'Is A inside set {a0} AND B inside set {b0}?', {'op': 'and', 'a_set': a0, 'b_set': b0}),
            ('relational', f'Is A outside set {az} OR B inside set {b1}?', {'op': 'or_exclude', 'a_set': az, 'b_set': b1}),
            ('operational', f'Eligibility requires A inside {a2} AND B outside {b2}. Is the task eligible?', {'op': 'eligible', 'a_set': a2, 'b_set': b2}),
            ('operational', f'Choose alpha if A is inside {az}; otherwise choose beta if B is inside {bz}; otherwise choose gamma. Which route is selected?', {'op': 'route', 'a_set': az, 'b_set': bz})]
        rules = 'Every combination of one public A root and one public B root is allowed. Sets contain exactly their listed members. Apply AND, OR and NOT with their ordinary Boolean meanings. No candidate IDs or roster apply.'
    return {'system': 'Answer the six stated fictional utility questions from the visible release and public task rules only. If the answer is not logically determined, return insufficient. Return JSON only.',
            'public': w.public, 'task_rules': rules, 'release': release(w, arm, t),
            'questions': [{'id': 'q' + str(i + 1), 'category': c, 'text': text, 'task': task} for i, (c, text, task) in enumerate(questions)],
            'schema': {'type': 'object', 'required': ['answers'], 'additionalProperties': False,
                       'properties': {'answers': {'type': 'array', 'minItems': 6, 'maxItems': 6,
                                                 'items': {'type': ['string', 'integer', 'boolean']},
                                                 'description': 'Six answers in question order. Use string insufficient if not determined.'}}}}
