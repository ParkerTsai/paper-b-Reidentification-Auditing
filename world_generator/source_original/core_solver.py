"""Independent, deterministic solver for the frozen visible v8.4.1 language.

This module consumes only public dictionaries, visible candidate records and release
text. It does not import the synthetic data generator. Its intentionally narrow
grammar is a symbolic baseline, not a general natural-language understanding system.

JSON AST: {"version": 1, "mechanism": str, "clauses": [clause, ...]}.
Clauses are eq(field,value), difference(left,right,value), root(domain,value),
path(domain,steps,terminal), or member(domain,set,value). A path's steps are
{"relation": alias, "direction": 1|-1}; membership values are actual booleans.
The grouped-negation grammar is normalized to a conjunction of member clauses.
All listed clauses are conjoined. No executable expressions are accepted.
"""

import re


class VisibleInputError(ValueError):
    """The visible payload is malformed, unsupported, or has empty support."""


_ALIAS_PATTERN = r"[0-9a-f]{12}"
_ALIAS_RE = re.compile(_ALIAS_PATTERN)
_EVENT_PATTERN = r"(?:T|P|E|Review|Audit|M[1-4])"
_TEMPORAL_FIELDS = frozenset(("T", "P", "E", "g", "d", "h", "Review", "Audit",
                              "M1", "M2", "M3", "M4"))
_RELATIONS = {
    "temporal": "P=T+g; E=P+d. All years are exact. Intervals are left-closed and right-open. Before means strictly earlier.",
    "graph": "Each edge is directed from its from-node to its to-node. A + step follows that direction; a - step reverses it. A path must traverse all listed steps in order.",
    "boolean": "A listed set contains exactly its listed members. Inside means membership, outside means non-membership. No listed violation occurs means every individual listed violation is false; an empty violation list imposes no restriction.",
}


def _fail(message):
    raise VisibleInputError(message)


def _mapping(value, label, required, optional=()):
    if not isinstance(value, dict):
        _fail(label + " must be an object")
    keys = set(value)
    if not set(required) <= keys or keys - set(required) - set(optional):
        _fail(label + " has missing or unknown fields")
    return value


def _array(value, label, nonempty=True):
    if not isinstance(value, (list, tuple)) or (nonempty and not value):
        _fail(label + " must be " + ("a nonempty array" if nonempty else "an array"))
    return value


def _integer(value, label, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(label + " must be an integer")
    if minimum is not None and value < minimum:
        _fail(label + " is below its allowed range")
    if maximum is not None and value > maximum:
        _fail(label + " is above its allowed range")
    return value


def _alias(value, label):
    if not isinstance(value, str) or _ALIAS_RE.fullmatch(value) is None:
        _fail(label + " must be a 12-character lowercase hexadecimal alias")
    return value


def _aliases(values, label):
    _array(values, label)
    for value in values:
        _alias(value, label)
    if len(set(values)) != len(values):
        _fail(label + " contains duplicate aliases")
    return set(values)


def _validate_steps(path, relations, label="path"):
    _array(path, label)
    for step in path:
        _mapping(step, label + " step", ("relation", "direction"))
        _alias(step["relation"], "path relation")
        if step["relation"] not in relations:
            _fail("Path refers to an unknown relation")
        direction = _integer(step["direction"], "path direction")
        if direction not in (-1, 1):
            _fail("Path direction must be +1 or -1")


def _validate_graph_domain(info):
    _mapping(info, "graph domain", ("roots", "attributes", "edges", "paths"))
    roots = _aliases(info["roots"], "roots")
    _mapping(info["attributes"], "root attributes", roots)
    for attributes in info["attributes"].values():
        _mapping(attributes, "attributes", ("load", "zone"))
        _integer(attributes["load"], "load", 1, 9)
        if attributes["zone"] not in ("north", "south"):
            _fail("Unknown root zone")
    _array(info["edges"], "edges")
    relations, nodes, seen = set(), set(roots), set()
    for edge in info["edges"]:
        _mapping(edge, "edge", ("relation", "from", "to"))
        for field in ("relation", "from", "to"):
            _alias(edge[field], "edge " + field)
        triple = (edge["relation"], edge["from"], edge["to"])
        if triple in seen:
            _fail("Duplicate graph edge")
        seen.add(triple)
        relations.add(edge["relation"])
        nodes.update((edge["from"], edge["to"]))
    if relations & nodes:
        _fail("Graph relations and nodes must have distinct aliases")
    _array(info["paths"], "public paths")
    for path in info["paths"]:
        _validate_steps(path, relations)
    return roots, nodes, relations


def _validate_boolean_domain(info):
    _mapping(info, "Boolean domain", ("roots", "sets"))
    roots = _aliases(info["roots"], "roots")
    _array(info["sets"], "sets")
    identifiers, subsets = set(), set()
    for item in info["sets"]:
        _mapping(item, "set", ("id", "members"))
        sid = _alias(item["id"], "set ID")
        if sid in identifiers or sid in roots:
            _fail("Set IDs must be unique and distinct from roots")
        identifiers.add(sid)
        members = _aliases(item["members"], "set members")
        if not members <= roots:
            _fail("Set contains a root outside its domain")
        if len(members) < 2 or len(roots - members) < 2:
            _fail("Each set must include and exclude at least two roots")
        frozen = frozenset(members)
        if frozen in subsets:
            _fail("Duplicate public subsets are unsupported")
        subsets.add(frozen)
    signatures = {tuple(root in s["members"] for s in info["sets"]) for root in roots}
    if len(signatures) != len(roots):
        _fail("Public Boolean signatures must distinguish all roots")
    return roots, identifiers


def _validate_public(public):
    if not isinstance(public, dict):
        _fail("public must be an object")
    mechanism = public.get("mechanism")
    if not isinstance(mechanism, str) or mechanism not in _RELATIONS:
        _fail("Unknown public mechanism")
    if public.get("relations") != _RELATIONS[mechanism]:
        _fail("Unsupported or missing public relation definitions")
    if mechanism == "temporal":
        _mapping(public, "temporal public", ("mechanism", "h", "shifts", "allowed", "relations"))
        _integer(public["h"], "shared training duration", 1, 2)
        shifts = _array(public["shifts"], "public shifts")
        if len(shifts) != 4:
            _fail("Exactly four public shifts are required")
        for shift in shifts:
            _integer(shift, "public shift", 1, 3)
        allowed = _mapping(public["allowed"], "allowed", ("T", "g", "d"))
        for field in ("T", "g"):
            bounds = _array(allowed[field], "allowed " + field)
            if len(bounds) != 2:
                _fail("Allowed integer ranges need two inclusive endpoints")
            for bound in bounds:
                _integer(bound, "range endpoint")
            if bounds[0] > bounds[1]:
                _fail("Reversed allowed range")
        if allowed["T"][1] - allowed["T"][0] != 6:
            _fail("The public T range must span seven integer years")
        if list(allowed["g"]) != [1, 9]:
            _fail("Unsupported public gap range")
        _array(allowed["d"], "allowed project durations")
        for duration in allowed["d"]:
            _integer(duration, "allowed project duration")
        if len(allowed["d"]) != 2 or set(allowed["d"]) != {3, 4}:
            _fail("Allowed project durations must be 3 and 4")
    else:
        extra = ("task_terminal",) if mechanism == "graph" else ()
        _mapping(public, mechanism + " public", ("mechanism", "domains", "relations") + extra)
        _mapping(public["domains"], "domains", ("A", "B"))
        domain_aliases = []
        for domain, size in (("A", 4), ("B", 5)):
            info = public["domains"][domain]
            if mechanism == "graph":
                roots, nodes, relations = _validate_graph_domain(info)
                domain_aliases.append(nodes | relations)
                if domain == "A":
                    _alias(public["task_terminal"], "task terminal")
                    if public["task_terminal"] not in nodes:
                        _fail("Task terminal is outside domain A")
            else:
                roots, identifiers = _validate_boolean_domain(info)
                domain_aliases.append(roots | identifiers)
            if len(roots) != size:
                _fail("Public root counts must be 4 for A and 5 for B")
        if domain_aliases[0] & domain_aliases[1]:
            _fail("Domain aliases must not overlap")
    return mechanism


def _temporal_values(public, row):
    _mapping(row, "temporal record", ("T", "P", "d", "h"), ("id", "g", "E"))
    for field in ("T", "P", "d", "h"):
        _integer(row[field], "record " + field)
    if "id" in row:
        _alias(row["id"], "candidate ID")
    values = {field: row[field] for field in ("T", "P", "d", "h")}
    values["g"] = row["P"] - row["T"]
    values["E"] = row["P"] + row["d"]
    for field in ("g", "E"):
        if field in row:
            _integer(row[field], "record " + field)
            if row[field] != values[field]:
                _fail("Provided derived temporal field contradicts the public equations")
    allowed = public["allowed"]
    if not allowed["T"][0] <= values["T"] <= allowed["T"][1]:
        _fail("Record T lies outside the public range")
    if not allowed["g"][0] <= values["g"] <= allowed["g"][1]:
        _fail("Record gap lies outside the public range")
    if values["d"] not in allowed["d"] or values["h"] != public["h"]:
        _fail("Record duration contradicts the public domain")
    shifts = public["shifts"]
    values["Review"] = values["E"] + shifts[0]
    values["Audit"] = values["Review"] + shifts[1]
    previous = values["T"]
    for index, shift in enumerate(shifts, 1):
        previous += shift
        values["M" + str(index)] = previous
    return values


def temporal_values(public, row):
    """Return all derived event years and durations for a complete T/P/d/h row."""
    if _validate_public(public) != "temporal":
        _fail("temporal_values requires the temporal mechanism")
    return _temporal_values(public, row)


def _walk(info, root, path):
    current = {root}
    for step in path:
        source, destination = ("from", "to") if step["direction"] == 1 else ("to", "from")
        current = {edge[destination] for edge in info["edges"]
                   if edge["relation"] == step["relation"] and edge[source] in current}
    return current


def walk(public_domain, root, path):
    """Traverse every signed edge step and return all reachable endpoint aliases."""
    roots, _, relations = _validate_graph_domain(public_domain)
    _alias(root, "path root")
    if root not in roots:
        _fail("Path origin is not a public root")
    _validate_steps(path, relations)
    return _walk(public_domain, root, path)


_TEMPORAL_ASSIGNMENTS = (
    ("T", ("Training ended in ", "The training completion year was ", "Training finished in ", "Training completion: "), ""),
    ("P", ("Project started in ", "The project start year was ", "Project began in ", "Project commencement: "), ""),
    ("E", ("Project ended in ", "The project finish year was ", "Project finished in ", "Project completion: "), ""),
    ("d", ("Project lasted ", "The project duration was ", "Project duration equaled ", "Project activity: "), " years"),
    ("h", ("Training lasted ", "The training duration was ", "Training duration equaled ", "Training activity: "), " years"),
    ("g", ("The gap was ", "The elapsed gap was ", "The interval was ", "Gap: "), " years"),
)
_ASSIGNMENT_RE = [(field, re.compile("(?:" + "|".join(map(re.escape, prefixes)) + ")([0-9]+)" +
                                   (r" years?" if suffix else "")))
                  for field, prefixes, suffix in _TEMPORAL_ASSIGNMENTS]
_DIFFERENCE_RE = re.compile("(" + _EVENT_PATTERN + ") (?:followed|came after|was later than|succeeded) (" + _EVENT_PATTERN + ") by ([0-9]+) years?")
_ANCHOR_RE = re.compile("(" + _EVENT_PATTERN + ") (?:occurred in|had year|was dated|took place in) ([0-9]+)")
_ROOT_RES = (
    re.compile(r"The selected ([AB]) root is (" + _ALIAS_PATTERN + r")"),
    re.compile(r"For domain ([AB]), the root is (" + _ALIAS_PATTERN + r")"),
    re.compile(r"(" + _ALIAS_PATTERN + r") is the selected root in domain ([AB])"),
    re.compile(r"Domain ([AB]) root = (" + _ALIAS_PATTERN + r")"),
)
_PATH_PATTERN = r"[+-]" + _ALIAS_PATTERN + r"(?:,[+-]" + _ALIAS_PATTERN + r")*"
_PATH_RES = (
    re.compile(r"The selected ([AB]) root follows (" + _PATH_PATTERN + r") to (" + _ALIAS_PATTERN + r")"),
    re.compile(r"For domain ([AB]), following (" + _PATH_PATTERN + r") ends at (" + _ALIAS_PATTERN + r")"),
    re.compile(r"(" + _ALIAS_PATTERN + r") is reached from domain ([AB]) root along (" + _PATH_PATTERN + r")"),
    re.compile(r"Domain ([AB]) path (" + _PATH_PATTERN + r") = (" + _ALIAS_PATTERN + r")"),
)
_MEMBER_RES = (
    re.compile(r"The selected ([AB]) root is (inside|outside) set (" + _ALIAS_PATTERN + r")"),
    re.compile(r"For domain ([AB]), the root (belongs|does not belong) to set (" + _ALIAS_PATTERN + r")"),
    re.compile(r"Set (" + _ALIAS_PATTERN + r") (contains|does not contain) the selected ([AB]) root"),
    re.compile(r"Domain ([AB]) membership in (" + _ALIAS_PATTERN + r") = (true|false)"),
)
_ALIAS_LIST_PATTERN = r"(?:" + _ALIAS_PATTERN + r"(?:," + _ALIAS_PATTERN + r")*)?"
_GROUP_RES = (
    re.compile(r"For the selected ([AB]) root, none of these violations occurs: being outside any set in \[(" + _ALIAS_LIST_PATTERN + r")\]; being inside any set in \[(" + _ALIAS_LIST_PATTERN + r")\]"),
    re.compile(r"For domain ([AB]), every listed violation is false: outside any set in \[(" + _ALIAS_LIST_PATTERN + r")\]; inside any set in \[(" + _ALIAS_LIST_PATTERN + r")\]"),
    re.compile(r"It is false that domain ([AB]) root is outside any set in \[(" + _ALIAS_LIST_PATTERN + r")\] or inside any set in \[(" + _ALIAS_LIST_PATTERN + r")\]"),
)


def _parse_sentence(mechanism, sentence):
    if mechanism == "temporal":
        for field, pattern in _ASSIGNMENT_RE:
            match = pattern.fullmatch(sentence)
            if match:
                return [{"op": "eq", "field": field, "value": int(match[1])}]
        match = _DIFFERENCE_RE.fullmatch(sentence)
        if match:
            return [{"op": "difference", "left": match[1], "right": match[2], "value": int(match[3])}]
        match = _ANCHOR_RE.fullmatch(sentence)
        if match:
            return [{"op": "eq", "field": match[1], "value": int(match[2])}]
    else:
        for index, pattern in enumerate(_ROOT_RES):
            match = pattern.fullmatch(sentence)
            if match:
                domain, value = (match[2], match[1]) if index == 2 else (match[1], match[2])
                return [{"op": "root", "domain": domain, "value": value}]
        if mechanism == "graph":
            for index, pattern in enumerate(_PATH_RES):
                match = pattern.fullmatch(sentence)
                if match:
                    domain, path, terminal = ((match[2], match[3], match[1]) if index == 2 else match.groups())
                    steps = [{"relation": piece[1:], "direction": 1 if piece[0] == "+" else -1}
                             for piece in path.split(",")]
                    return [{"op": "path", "domain": domain, "steps": steps, "terminal": terminal}]
        else:
            match = next((match for pattern in _GROUP_RES
                          if (match := pattern.fullmatch(sentence)) is not None), None)
            if match:
                clauses = []
                for group, positive in ((match[2], True), (match[3], False)):
                    identifiers = group.split(",") if group else []
                    if len(identifiers) != len(set(identifiers)):
                        _fail("Duplicate set in a grouped-negation clause")
                    clauses.extend({"op": "member", "domain": match[1], "set": sid, "value": positive}
                                   for sid in identifiers)
                if not clauses:
                    _fail("Empty grouped-negation clause")
                return clauses
            for index, pattern in enumerate(_MEMBER_RES):
                match = pattern.fullmatch(sentence)
                if match:
                    if index == 2:
                        sid, word, domain = match.groups()
                    elif index == 3:
                        domain, sid, word = match.groups()
                    else:
                        domain, word, sid = match.groups()
                    return [{"op": "member", "domain": domain, "set": sid,
                             "value": word in ("inside", "belongs", "contains", "true")}]
    _fail("Unsupported visible release clause: " + sentence)


def _validate_constraints(public, constraints):
    _mapping(constraints, "constraints", ("version", "mechanism", "clauses"))
    _integer(constraints["version"], "AST version")
    if constraints["version"] != 1 or constraints["mechanism"] != public["mechanism"]:
        _fail("Unsupported AST version or mismatched mechanism")
    clauses = _array(constraints["clauses"], "constraint clauses")
    mechanism = public["mechanism"]
    equalities = {}
    for clause in clauses:
        if not isinstance(clause, dict):
            _fail("Every AST clause must be an object")
        op = clause.get("op")
        key, value = None, None
        if mechanism == "temporal" and op == "eq":
            _mapping(clause, "equality", ("op", "field", "value"))
            if not isinstance(clause["field"], str) or clause["field"] not in _TEMPORAL_FIELDS:
                _fail("Unknown temporal field")
            _integer(clause["value"], "equality value")
            key, value = ("eq", clause["field"]), clause["value"]
        elif mechanism == "temporal" and op == "difference":
            _mapping(clause, "event difference", ("op", "left", "right", "value"))
            for side in ("left", "right"):
                if not isinstance(clause[side], str) or re.fullmatch(_EVENT_PATTERN, clause[side]) is None:
                    _fail("Unknown event in difference constraint")
            _integer(clause["value"], "event difference")
            key, value = ("difference", clause["left"], clause["right"]), clause["value"]
        elif mechanism in ("graph", "boolean") and op in ("root", "path", "member"):
            if clause.get("domain") not in ("A", "B"):
                _fail("Unknown constraint domain")
            info = public["domains"][clause["domain"]]
            if op == "root":
                _mapping(clause, "root constraint", ("op", "domain", "value"))
                _alias(clause["value"], "constraint root")
                if clause["value"] not in info["roots"]:
                    _fail("Root constraint references a root outside its domain")
                key, value = ("root", clause["domain"]), clause["value"]
            elif mechanism == "graph" and op == "path":
                _mapping(clause, "path constraint", ("op", "domain", "steps", "terminal"))
                relations = {edge["relation"] for edge in info["edges"]}
                _validate_steps(clause["steps"], relations)
                _alias(clause["terminal"], "path terminal")
                nodes = set(info["roots"]) | {edge[field] for edge in info["edges"] for field in ("from", "to")}
                if clause["terminal"] not in nodes:
                    _fail("Unknown path terminal")
            elif mechanism == "boolean" and op == "member":
                _mapping(clause, "membership constraint", ("op", "domain", "set", "value"))
                _alias(clause["set"], "constraint set")
                if clause["set"] not in {item["id"] for item in info["sets"]}:
                    _fail("Membership refers to an unknown set")
                if not isinstance(clause["value"], bool):
                    _fail("Membership value must be a Boolean")
                key, value = ("member", clause["domain"], clause["set"]), clause["value"]
            else:
                _fail("Constraint operation does not apply to this mechanism")
        else:
            _fail("Unknown constraint operation")
        if key is not None:
            if key in equalities and equalities[key] != value:
                _fail("Contradictory visible constraint clauses")
            equalities[key] = value
    return clauses


def extract_constraints(payload):
    """Strictly parse release text; public/release are the only required keys."""
    if not isinstance(payload, dict) or "public" not in payload or "release" not in payload:
        _fail("Payload requires public and release fields")
    public = payload["public"]
    mechanism = _validate_public(public)
    release = payload["release"]
    if not isinstance(release, str) or not release.strip():
        _fail("Release must be a nonempty string")
    normalized = " ".join(release.split())
    if not normalized.endswith("."):
        _fail("Every release clause must end with a full stop")
    sentences = normalized[:-1].split(".")
    if any(not sentence.strip() for sentence in sentences):
        _fail("Empty release clause")
    clauses = []
    for sentence in sentences:
        clauses.extend(_parse_sentence(mechanism, sentence.strip()))
    constraints = {"version": 1, "mechanism": mechanism, "clauses": clauses}
    _validate_constraints(public, constraints)
    return constraints


def _validate_record(public, row):
    if public["mechanism"] == "temporal":
        return _temporal_values(public, row)
    _mapping(row, "root record", ("A", "B"), ("id",))
    if "id" in row:
        _alias(row["id"], "candidate ID")
    for domain in ("A", "B"):
        _alias(row[domain], "record root")
        if row[domain] not in public["domains"][domain]["roots"]:
            _fail("Record root lies outside its public domain")
    return row


def _consistent(public, values, clauses):
    for clause in clauses:
        op = clause["op"]
        if op == "eq":
            compatible = values[clause["field"]] == clause["value"]
        elif op == "difference":
            compatible = values[clause["left"]] - values[clause["right"]] == clause["value"]
        elif op == "root":
            compatible = values[clause["domain"]] == clause["value"]
        elif op == "path":
            info = public["domains"][clause["domain"]]
            compatible = clause["terminal"] in _walk(info, values[clause["domain"]], clause["steps"])
        else:  # Only a validated member operation can reach this branch.
            info = public["domains"][clause["domain"]]
            members = next(item["members"] for item in info["sets"] if item["id"] == clause["set"])
            compatible = (values[clause["domain"]] in members) == clause["value"]
        if not compatible:
            return False
    return True


def consistent_record(public, row, constraints):
    """Test one allowed record; id is optional and malformed inputs raise."""
    _validate_public(public)
    clauses = _validate_constraints(public, constraints)
    return _consistent(public, _validate_record(public, row), clauses)


def solve_constraints(public, candidates, constraints):
    """Evaluate a JSON AST against the complete visible 20-record uniform pool."""
    mechanism = _validate_public(public)
    clauses = _validate_constraints(public, constraints)
    _array(candidates, "candidates")
    if len(candidates) != 20:
        _fail("The complete candidate pool must contain exactly 20 records")
    ids, rows, coordinates = [], [], set()
    for candidate in candidates:
        if not isinstance(candidate, dict) or "id" not in candidate:
            _fail("Each candidate requires an ID")
        identifier = _alias(candidate["id"], "candidate ID")
        if identifier in ids:
            _fail("Candidate IDs must be unique")
        ids.append(identifier)
        values = _validate_record(public, candidate)
        rows.append(values)
        coordinate = ((values["T"], values["d"], values["h"]), values["g"]) if mechanism == "temporal" else (values["A"], values["B"])
        if coordinate in coordinates:
            _fail("Candidate coordinate combinations must be unique")
        coordinates.add(coordinate)
    a_values = {coordinate[0] for coordinate in coordinates}
    b_values = {coordinate[1] for coordinate in coordinates}
    if len(a_values) != 4 or len(b_values) != 5 or coordinates != {(a, b) for a in a_values for b in b_values}:
        _fail("Candidates must form the complete 4-by-5 Cartesian product")
    if mechanism == "temporal":
        if len({a[0] for a in a_values}) != 4 or sorted(a[1] for a in a_values) != [3, 3, 4, 4]:
            _fail("Invalid temporal A coordinates")
        if {min(a[0] for a in a_values), max(a[0] for a in a_values)} != set(public["allowed"]["T"]):
            _fail("Temporal candidate years must include both public range endpoints")
        if min(b_values) != 1 or max(b_values) != 9:
            _fail("Temporal candidate gaps must include 1 and 9")
    compatible = [identifier for identifier, values in zip(ids, rows) if _consistent(public, values, clauses)]
    if not compatible:
        _fail("Visible evidence has empty candidate support")
    support = set(compatible)
    probability = 1.0 / len(compatible)
    return {"compatible_ids": compatible,
            "probabilities": {identifier: probability if identifier in support else 0.0 for identifier in ids}}


def solve_payload(payload):
    """Parse visible release text and return its compatible IDs and posterior."""
    constraints = extract_constraints(payload)
    if "candidates" not in payload:
        _fail("Attack solving requires visible candidates")
    return solve_constraints(payload["public"], payload["candidates"], constraints)
