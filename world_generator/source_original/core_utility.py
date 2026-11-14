"""Roster-free oracle answerability for explicitly defined public utility tasks.

No import of the generator; no private World, target, arm or candidate table.
The possible-record space is defined entirely by the reader's public rules.
"""
from itertools import product
import json

from core_solver import extract_constraints, consistent_record, temporal_values, walk, VisibleInputError

UTILITY_KEYS = {'system', 'public', 'task_rules', 'release', 'questions', 'schema'}
CATEGORIES = ('local', 'local', 'relational', 'relational', 'operational', 'operational')

TASK_RULES = {
    'temporal': 'Allowed records have any integer T in the public inclusive T range, any integer g in the inclusive g range, d from the public list, and shared h. P=T+g; E=P+d. No other constraints or roster apply.',
    'graph': 'Every combination of one public A root and one public B root is allowed. Public directed edges, path directions and attributes define the task. No candidate IDs or roster apply.',
    'boolean': 'Every combination of one public A root and one public B root is allowed. Sets contain exactly their listed members. Apply AND, OR and NOT with their ordinary Boolean meanings. No candidate IDs or roster apply.'
}


def _question_text(task):
    """Independent whitelist for the visible task grammar, not a generator import."""
    op = task.get('op')
    if op == 'value':
        return {'d': 'How many years did the project last?', 'h': 'How many years did the training last?',
                'g': 'How many years elapsed from training completion to project start?'}[task['field']]
    if op == 'overlap':
        return f"Did the project interval [start,end) overlap the interval [{task['start']},{task['end']})?"
    if op == 'before':
        action, deadline = ('started', 'start') if task['field'] == 'P' else ('completed', 'completion')
        return f"Was the project {action} strictly before the {deadline} deadline {task['cutoff']}?"
    if op == 'attribute':
        return f"What {task['field']} is assigned to the selected {task['domain']} root?"
    if op == 'reaches':
        path = ','.join(('+' if step['direction'] == 1 else '-') + step['relation'] for step in task['path'])
        return f"Does the selected {task['domain']} root reach {task['terminal']} along the path {path}?"
    if op == 'same_zone':
        return 'Are the selected A and B roots in the same zone?'
    if op == 'load_limit':
        return f"A task is eligible exactly when the sum of A and B loads is at most {task['limit']}. Is this task eligible?"
    if op == 'dispatch':
        return 'Dispatch to the zone of the root with the lower load; choose A on an equal load. Which zone is selected?'
    if op == 'member':
        return f"Does the selected {task['domain']} root belong to set {task['set']}?"
    if op == 'and':
        return f"Is A inside set {task['a_set']} AND B inside set {task['b_set']}?"
    if op == 'or_exclude':
        return f"Is A outside set {task['a_set']} OR B inside set {task['b_set']}?"
    if op == 'eligible':
        return f"Eligibility requires A inside {task['a_set']} AND B outside {task['b_set']}. Is the task eligible?"
    if op == 'route':
        return f"Choose alpha if A is inside {task['a_set']}; otherwise choose beta if B is inside {task['b_set']}; otherwise choose gamma. Which route is selected?"
    raise VisibleInputError('Unknown public utility question grammar')


def _validate_questions(payload):
    questions = payload['questions']
    if not isinstance(questions, list) or len(questions) != 6:
        raise VisibleInputError('Exactly six ordered questions are required')
    expected_ops = {'temporal': ('value', 'value', 'value', 'overlap', 'before', 'before'),
                    'graph': ('attribute', 'attribute', 'reaches', 'same_zone', 'load_limit', 'dispatch'),
                    'boolean': ('member', 'member', 'and', 'or_exclude', 'eligible', 'route')}[payload['public']['mechanism']]
    for i, q in enumerate(questions):
        if not isinstance(q, dict) or set(q) != {'id', 'category', 'text', 'task'}:
            raise VisibleInputError('Invalid public utility question fields')
        if q['id'] != 'q' + str(i + 1) or q['category'] != CATEGORIES[i]:
            raise VisibleInputError('Invalid question ID, order, or category')
        if not isinstance(q['task'], dict) or q['task'].get('op') != expected_ops[i]:
            raise VisibleInputError('Unexpected question operation or order')
        try:
            if q['text'] != _question_text(q['task']):
                raise VisibleInputError('Question text disagrees with the visible machine-readable task')
        except (KeyError, TypeError) as exc:
            raise VisibleInputError('Malformed public task descriptor') from exc



def possible_records(payload):
    if not isinstance(payload, dict) or set(payload) != UTILITY_KEYS:
        raise VisibleInputError('Utility reader accepts only its public six-field payload, without candidate roster')
    public = payload['public']
    if payload['task_rules'] != TASK_RULES.get(public.get('mechanism')):
        raise VisibleInputError('Unsupported or contradictory public task rules')
    _validate_questions(payload)
    constraints = extract_constraints(payload)
    if public['mechanism'] == 'temporal':
        allowed = public['allowed']
        for key in ('T', 'g'):
            bounds = allowed[key]
            if (not isinstance(bounds, list) or len(bounds) != 2 or
                    any(type(x) is not int for x in bounds) or bounds[0] > bounds[1] or bounds[1] - bounds[0] > 100):
                raise VisibleInputError('Invalid finite temporal public domain')
        if any(type(x) is not int or x <= 0 for x in allowed['d']):
            raise VisibleInputError('Invalid duration domain')
        candidates = ({'T': T, 'P': T + g, 'd': d, 'h': public['h']}
                      for T, g, d in product(range(allowed['T'][0], allowed['T'][1] + 1),
                                             range(allowed['g'][0], allowed['g'][1] + 1), allowed['d']))
    elif public['mechanism'] in ('graph', 'boolean'):
        candidates = ({'A': a, 'B': b} for a, b in product(public['domains']['A']['roots'], public['domains']['B']['roots']))
    else:
        raise VisibleInputError('Unknown public utility mechanism')
    records = [r for r in candidates if consistent_record(public, r, constraints)]
    if not records:
        raise VisibleInputError('Utility evidence has no allowed possible record')
    return records


def _membership(public, row, domain, set_id):
    matches = [s for s in public['domains'][domain]['sets'] if s['id'] == set_id]
    if len(matches) != 1:
        raise VisibleInputError('Utility task refers to an unknown or duplicate set')
    return row[domain] in matches[0]['members']


def evaluate_task(public, row, task):
    op = task['op']
    mechanism = public['mechanism']
    if mechanism == 'temporal':
        values = temporal_values(public, row)
        if op == 'value' and task['field'] in ('d', 'h', 'g'):
            return values[task['field']]
        if op == 'overlap':
            return max(values['P'], task['start']) < min(values['E'], task['end'])
        if op == 'before' and task['field'] in ('P', 'E'):
            return values[task['field']] < task['cutoff']
    elif mechanism == 'graph':
        attrs = {d: public['domains'][d]['attributes'][row[d]] for d in ('A', 'B')}
        if op == 'attribute' and task['domain'] in attrs and task['field'] in ('load', 'zone'):
            return attrs[task['domain']][task['field']]
        if op == 'reaches':
            d = task['domain']
            return task['terminal'] in walk(public['domains'][d], row[d], task['path'])
        if op == 'same_zone':
            return attrs['A']['zone'] == attrs['B']['zone']
        if op == 'load_limit':
            return attrs['A']['load'] + attrs['B']['load'] <= task['limit']
        if op == 'dispatch':
            d = 'A' if attrs['A']['load'] <= attrs['B']['load'] else 'B'
            return attrs[d]['zone']
    elif mechanism == 'boolean':
        if op == 'member':
            return _membership(public, row, task['domain'], task['set'])
        if op in ('and', 'or_exclude', 'eligible', 'route'):
            a = _membership(public, row, 'A', task['a_set'])
            b = _membership(public, row, 'B', task['b_set'])
            return {'and': lambda: a and b,
                    'or_exclude': lambda: (not a) or b,
                    'eligible': lambda: a and not b,
                    'route': lambda: 'alpha' if a else 'beta' if b else 'gamma'}[op]()
    raise VisibleInputError('Unknown utility task for the public mechanism')


def _typed_key(value):
    # Python True==1 must not collapse Boolean and numeric possible answers.
    return (type(value).__name__, json.dumps(value, ensure_ascii=False, sort_keys=True))


def evaluate_questions(payload, row):
    """Evaluate a complete record; caller supplies it explicitly for offline truth checks."""
    _validate_questions(payload)
    questions = payload['questions']
    if len(questions) != 6 or tuple(q['category'] for q in questions) != CATEGORIES:
        raise VisibleInputError('Exactly six ordered questions, two in each fixed category, are required')
    if [q['id'] for q in questions] != ['q' + str(i) for i in range(1, 7)]:
        raise VisibleInputError('Invalid utility question identifiers')
    if any(not isinstance(q.get('text'), str) or not q['text'].strip() for q in questions):
        raise VisibleInputError('Question text is required')
    return [evaluate_task(payload['public'], row, q['task']) for q in questions]


def oracle_answers(payload):
    records = possible_records(payload)
    all_answers = [evaluate_questions(payload, r) for r in records]
    result = []
    for i, question in enumerate(payload['questions']):
        values = {_typed_key(a[i]): a[i] for a in all_answers}
        ordered = [values[k] for k in sorted(values)]
        result.append({'id': question['id'], 'category': question['category'],
                       'answerable': len(ordered) == 1,
                       'answer': ordered[0] if len(ordered) == 1 else 'insufficient',
                       'possible_answers': ordered})
    return result


def score_answers(payload, response):
    """Descriptive six-task scores, never a claim of real-user utility weights.

    Correct accidental guesses on an underdetermined question are not credited as
    supported completion. Actual-world accuracy, if wanted, needs separate truth.
    """
    oracle = oracle_answers(payload)
    valid = (isinstance(response, dict) and set(response) == {'answers'} and
             isinstance(response['answers'], list) and len(response['answers']) == 6)
    if not valid:
        labels = ['format_failure'] * 6
    else:
        labels = []
        for answer, expected in zip(response['answers'], oracle):
            if type(answer) not in (str, bool, int):
                label = 'format_failure'
            elif answer == 'insufficient':
                label = 'overabstention' if expected['answerable'] else 'justified_insufficient'
            elif not expected['answerable']:
                label = 'unsupported_assertion'
            elif _typed_key(answer) == _typed_key(expected['answer']):
                label = 'correct'
            else:
                label = 'incorrect_assertion'
            labels.append(label)
    return {'labels': labels, 'supported_completion': sum(x == 'correct' for x in labels) / 6,
            'reasoning_appropriate': sum(x in ('correct', 'justified_insufficient') for x in labels) / 6,
            'categories': {category: sum(labels[i] == 'correct' for i, c in enumerate(CATEGORIES) if c == category) / 2
                           for category in ('local', 'relational', 'operational')}}
