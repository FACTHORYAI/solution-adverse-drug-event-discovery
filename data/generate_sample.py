"""Generate the synthetic sample: invented forum and support-call texts about drugs and side effects.

Everything here is invented. No real person, conversation or record is used. The texts are put
together from sentence templates and two small vocabularies (drugs and side effects); the rows an
extraction model would return are written from the same templates, so they are exact. Run it
from the repository root:

    uv run python data/generate_sample.py

It writes data/sample/*.parquet (ade_events, ade_classification, entities, assertions,
relations, graph_nodes, graph_edges) and tests/recorded_answers.json. The same seed always gives
the same files.

How the labels are set:

- is_ade is true when the text reports a side effect that someone had: assertion Present,
  Possible or Someone_else. It is false for Absent, Hypothetical and Conditional texts and for
  texts that report no side effect at all (questions, dosing, praise).
- An extracted relation is "1" when the text ties the side effect to the drug, whatever its
  assertion status, and "0" for a pair the text denies or keeps apart (a second drug the text
  says is not the cause, or an effect the text says did not happen).
- ade_classification is the label with about 6 percent of the texts flipped, chosen with a fixed
  seed. These predictions are invented so that accuracy and the confusion matrix mean something;
  they are not the output of a model.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from adverse_drug_event_discovery.jobs import REGISTRY, call_run
from adverse_drug_event_discovery.schemas import (
    ADE_CLASSIFICATION,
    ADE_EVENTS,
    ASSERTIONS,
    ENTITIES,
    RELATIONS,
)

SEED = 20251115
N_TEXTS = 300
FLIPPED_SHARE = 0.06
REPO = Path(__file__).resolve().parent.parent

# How many texts of each kind (they add up to N_TEXTS).
MIX = {
    "present": 95,
    "absent": 30,
    "possible": 25,
    "hypothetical": 30,
    "conditional": 15,
    "someone_else": 30,
    "no_ade": 75,
}

# drug -> (weight, [(side effect, weight), ...]). The weights make some drugs and some
# drug-side effect pairs much more common than others, so the pair analyses show a pattern.
# fmt: off
DRUGS: dict[str, tuple[int, list[tuple[str, int]]]] = {
    "metformin": (12, [("nausea", 9), ("diarrhea", 7), ("stomach pain", 3), ("loss of appetite", 4)]),
    "ibuprofen": (12, [("stomach pain", 9), ("heartburn", 6), ("nausea", 2), ("dizziness", 1)]),
    "lisinopril": (10, [("dry cough", 14), ("dizziness", 3), ("headache", 1), ("rash", 1)]),
    "atorvastatin": (10, [("muscle pain", 10), ("joint pain", 3), ("fatigue", 2)]),
    "sertraline": (9, [("nausea", 5), ("insomnia", 4), ("sweating", 3), ("dry mouth", 2), ("headache", 2)]),
    "amoxicillin": (8, [("rash", 9), ("diarrhea", 5), ("itching", 2), ("hives", 2), ("nausea", 2)]),
    "prednisone": (6, [("weight gain", 8), ("insomnia", 5), ("anxiety", 2), ("sweating", 2), ("blurred vision", 1)]),
    "amlodipine": (6, [("swollen ankles", 10), ("dizziness", 3), ("headache", 2), ("palpitations", 1), ("fatigue", 1)]),
    "gabapentin": (6, [("drowsiness", 8), ("dizziness", 6), ("blurred vision", 2), ("weight gain", 2)]),
    "tramadol": (6, [("nausea", 6), ("drowsiness", 5), ("constipation", 5), ("dizziness", 3), ("vomiting", 2), ("dry mouth", 1)]),
    "omeprazole": (5, [("headache", 4), ("diarrhea", 3), ("nausea", 2), ("constipation", 2)]),
    "warfarin": (5, [("bruising", 12), ("headache", 1), ("hair loss", 1)]),
    "naproxen": (5, [("heartburn", 6), ("stomach pain", 4), ("headache", 2), ("itching", 1)]),
    "citalopram": (4, [("nausea", 5), ("dry mouth", 3), ("drowsiness", 3), ("insomnia", 2), ("sweating", 2)]),
    "losartan": (4, [("dizziness", 6), ("fatigue", 3), ("headache", 2)]),
    "metoprolol": (4, [("fatigue", 7), ("dizziness", 3), ("vivid dreams", 2)]),
    "ciprofloxacin": (4, [("tendon pain", 7), ("diarrhea", 4), ("nausea", 3), ("rash", 1)]),
    "Zyrtec": (4, [("drowsiness", 8), ("dry mouth", 4), ("headache", 1)]),
    "levothyroxine": (3, [("palpitations", 5), ("hair loss", 3), ("tremor", 3), ("insomnia", 3), ("sweating", 2)]),
    "simvastatin": (3, [("muscle pain", 8), ("joint pain", 2), ("headache", 1)]),
    "azithromycin": (3, [("diarrhea", 7), ("stomach pain", 3), ("vomiting", 3), ("nausea", 3)]),
    "Prozac": (3, [("insomnia", 5), ("anxiety", 4), ("nausea", 3), ("loss of appetite", 3), ("headache", 2)]),
    "Xanax": (3, [("drowsiness", 7), ("fatigue", 3), ("dizziness", 2)]),
    "Ventolin": (2, [("tremor", 8), ("palpitations", 4), ("headache", 2)]),
    "Singulair": (2, [("vivid dreams", 6), ("headache", 3), ("anxiety", 2)]),
}
# fmt: on
DRUG_NAMES = list(DRUGS)
DRUG_WEIGHTS = [weight for weight, _ in DRUGS.values()]

# A few side effects read better with an article ("a rash"); the extracted text is the bare name.
ARTICLE = {"rash": "a ", "headache": "a ", "dry cough": "a ", "tremor": "a "}

WHEN = ["last week", "two weeks ago", "a few days ago", "after my operation", "last month"]
ONSET = ["a day later", "within a few hours", "by the weekend", "two days in"]
DURATION = ["a few days", "two weeks", "six weeks", "three months", "about a year"]
TAILS = ["", "", "", " Anyone else?", " Not great.", " I might ring the pharmacy.", " Thanks."]

# Templates. {d} is a drug, {a} a side effect with its article, {t} the bare side effect.
# {d1}, {d2}, {a1}, {a2}, {t1}, {t2} are the two drugs and two side effects of the longer texts.
# fmt: off
PRESENT = [
    "I started {d} {when} and {onset} I developed {a}. Is this normal?",
    "Since I began taking {d} I keep getting {a}.",
    "Every time I take {d} I end up with {a}.",
    "Hi, I am calling about my {d}. Ever since the first dose I have had {a} and I would like to know whether I should stop.",
    "Took {d} this morning and about an hour later I had {a}.",
    "The {d} is working for my condition but it gives me {a} every single day.",
    "I have been on {d} for {dur} and the {t} just keeps getting worse.",
    "Support call: caller reports {a} after starting {d}. Advised to contact the prescriber.",
    "Switched to {d} {when} and now I have {a}. Going back to my old tablets.",
    "My doctor put me on {d} and I have had {a} ever since.",
]
PRESENT_TWO_ADES = [
    "After starting {d} I developed {a1} and {a2}. Should I call my doctor?",
    "Lately {d} gives me {a1} and also {a2}.",
    "Two weeks on {d}: {a1} the first days, now {a2} as well.",
]
PRESENT_TWO_DRUGS_ONE_CAUSE = [
    "I take {d1} and {d2} together. Since I added the {d2} I have had {a}.",
    "I take {d1} every morning and {d2} at night. The {t} started after the {d2}, never with the {d1}.",
]
PRESENT_TWO_DRUGS_BOTH = [
    "I am on {d1} and {d2} and since starting them both I have had {a}, so it could be either one.",
]
ABSENT = [
    "I have been on {d} for {dur} and I have had no {t} at all.",
    "Worried about {t} with {d}, but nothing so far. No {t} at all.",
    "Doctor asked if {d} gives me any {t}. It does not, I have been fine.",
    "Good news: I started {d} {when} and did not get any {t}.",
    "Caller says the {d} has not caused {t}; no side effects reported.",
]
ABSENT_TWO_ADES = [
    "No {t1} or {t2} on {d} so far, which surprised me.",
]
POSSIBLE = [
    "I think the {t} might be from the {d}, but I am not sure.",
    "Not certain, but maybe {d} is behind my {t}? It started around the same time.",
    "Could my {t} be caused by {d}? I have had it on and off since I started.",
    "Perhaps it is the {d}, but I have been having {a} lately and cannot tell why.",
    "Caller wonders whether {d} is the reason for the {t}; no one has confirmed it yet.",
]
HYPOTHETICAL = [
    "I'm worried {d} might cause {a}. Has anyone had that?",
    "I read online that {d} can cause {a}. Should I be concerned?",
    "The leaflet for {d} lists {t} as a side effect. I am about to start it and wondering what to expect.",
    "Starting {d} tomorrow. What if I get {a}? Should I take it with food?",
    "My pharmacist said {d} could cause {a} in some people.",
]
CONDITIONAL = [
    "The pharmacist told me that if I take {d} on an empty stomach I will get {a}.",
    "If I take {d} with grapefruit juice I will probably get {a}, so I avoid it.",
    "My doctor said {a} could only happen if I take {d} together with alcohol.",
    "The leaflet says {d} causes {t} only if the dose is doubled.",
    "If I ever need to stop {d} suddenly, I was warned I might get {a}.",
]
SOMEONE_ELSE = [
    "My mum gets {a} from {d}. Does anyone know if there is an alternative?",
    "My husband's {d} gives him {a} that will not go away.",
    "My son started {d} last week and has had {a} ever since.",
    "A friend of mine stopped taking {d} because of {a}.",
    "Caller says her father developed {a} after starting {d}.",
]
NO_ADE_ONE_DRUG = [
    "Can I take {d} with food or does it have to be on an empty stomach?",
    "How long does {d} take to start working?",
    "Is it fine to have coffee while I am on {d}?",
    "My doctor said to take {d} twice a day. Is it fine to take it at breakfast and dinner?",
    "What time of day do you take your {d}? I keep forgetting my evening dose.",
    "Support call: caller asks how to store {d} and whether it can be kept in the fridge.",
    "Does the pharmacy sell {d} in larger packs?",
    "Honestly my {d} has been great, no complaints and I would recommend asking your doctor about it.",
    "Three months on {d} and I feel so much better. Thank you all for the advice.",
    "Just wanted to say the {d} is working well and the nurse was really kind on the phone.",
    "I have been on {d} for {dur} and my check-up went fine.",
]
NO_ADE_TWO_DRUGS = [
    "Can I take {d1} and {d2} on the same day or should I space them out?",
    "I take {d1} in the morning and {d2} in the evening. Is that a good order?",
]
NO_ADE_NO_DRUG = [
    "Does anyone know when the pharmacy opens on Sunday?",
    "Can someone explain how to use the spacer with my inhaler?",
    "I need to book a repeat prescription review. Who do I call?",
    "How do I read the expiry date on the box?",
    "Is there a way to get my prescriptions delivered?",
    "Where can I find a pill organiser that has a week of compartments?",
    "Support call: caller wants to change the pharmacy on their account.",
    "Does anyone have tips for remembering to take tablets every day?",
]
# fmt: on


def _drug(rng: random.Random, exclude: str = "") -> str:
    while True:
        drug = rng.choices(DRUG_NAMES, weights=DRUG_WEIGHTS)[0]
        if drug != exclude:
            return drug


def _ade(rng: random.Random, drug: str, exclude: str = "") -> str:
    options = [(ade, weight) for ade, weight in DRUGS[drug][1] if ade != exclude]
    return rng.choices([ade for ade, _ in options], weights=[w for _, w in options])[0]


def _confidence(rng: random.Random) -> float:
    return round(rng.uniform(0.84, 0.99), 2)


def _phrase(ade: str) -> str:
    return ARTICLE.get(ade, "") + ade


def _spec(
    rng: random.Random,
    text: str,
    is_ade: bool,
    drugs: list[str],
    ades: list[str],
    status: dict[str, str],
    links: list[tuple[str, str, str]],
) -> dict:
    """One text with the rows an extraction model would return for it.

    status maps each side effect to its assertion; links are (side effect, drug, relation).
    """
    mentions = [(drug, "DRUG") for drug in drugs] + [(ade, "ADE") for ade in ades]
    for chunk, _ in mentions:
        assert chunk in text, (chunk, text)
    mentions.sort(key=lambda mention: text.index(mention[0]))
    entities = [
        {"chunk": chunk, "entity": entity, "confidence": _confidence(rng)}
        for chunk, entity in mentions
    ]
    assertions = [
        {"chunk": chunk, "assertion": status[chunk], "confidence": _confidence(rng)}
        for chunk, entity in mentions
        if entity == "ADE"
    ]
    relations = [
        {
            "relation": relation,
            "entity1": "ADE",
            "chunk1": ade,
            "entity2": "DRUG",
            "chunk2": drug,
            "confidence": _confidence(rng),
        }
        for ade, drug, relation in links
    ]
    return {
        "text": text,
        "is_ade": is_ade,
        "entities": entities,
        "assertions": assertions,
        "relations": relations,
    }


def _single(
    rng: random.Random,
    templates: list[str],
    status: str,
    is_ade: bool,
    relation: str,
    tails: bool = False,
) -> dict:
    """A text about one drug and one side effect with a given assertion."""
    drug = _drug(rng)
    ade = _ade(rng, drug)
    text = rng.choice(templates).format(
        d=drug,
        a=_phrase(ade),
        t=ade,
        when=rng.choice(WHEN),
        onset=rng.choice(ONSET),
        dur=rng.choice(DURATION),
    )
    if tails:
        text += rng.choice(TAILS)
    return _spec(rng, text, is_ade, [drug], [ade], {ade: status}, [(ade, drug, relation)])


def _present(rng: random.Random) -> dict:
    roll = rng.random()
    if roll < 0.12:  # one drug, two side effects
        drug = _drug(rng)
        first = _ade(rng, drug)
        second = _ade(rng, drug, exclude=first)
        text = rng.choice(PRESENT_TWO_ADES).format(d=drug, a1=_phrase(first), a2=_phrase(second))
        return _spec(
            rng,
            text,
            True,
            [drug],
            [first, second],
            {first: "Present", second: "Present"},
            [(first, drug, "1"), (second, drug, "1")],
        )
    if roll < 0.28:  # two drugs, one side effect
        second = _drug(rng)
        first = _drug(rng, exclude=second)
        ade = _ade(rng, second)
        if rng.random() < 0.6:  # the text says which drug it is
            text = rng.choice(PRESENT_TWO_DRUGS_ONE_CAUSE).format(
                d1=first, d2=second, a=_phrase(ade), t=ade
            )
            links = [(ade, second, "1"), (ade, first, "0")]
        else:  # the text cannot tell them apart
            text = rng.choice(PRESENT_TWO_DRUGS_BOTH).format(d1=first, d2=second, a=_phrase(ade))
            links = [(ade, first, "1"), (ade, second, "1")]
        return _spec(rng, text, True, [first, second], [ade], {ade: "Present"}, links)
    return _single(rng, PRESENT, "Present", True, "1", tails=True)


def _absent(rng: random.Random) -> dict:
    if rng.random() < 0.2:
        drug = _drug(rng)
        first = _ade(rng, drug)
        second = _ade(rng, drug, exclude=first)
        text = rng.choice(ABSENT_TWO_ADES).format(d=drug, t1=first, t2=second)
        return _spec(
            rng,
            text,
            False,
            [drug],
            [first, second],
            {first: "Absent", second: "Absent"},
            [(first, drug, "0"), (second, drug, "0")],
        )
    return _single(rng, ABSENT, "Absent", False, "0")


def _no_ade(rng: random.Random, no_drug_texts: list[str]) -> dict:
    roll = rng.random()
    if no_drug_texts and roll < 0.11:
        return _spec(rng, no_drug_texts.pop(), False, [], [], {}, [])
    if roll < 0.25:
        second = _drug(rng)
        first = _drug(rng, exclude=second)
        text = rng.choice(NO_ADE_TWO_DRUGS).format(d1=first, d2=second)
        return _spec(rng, text, False, [first, second], [], {}, [])
    drug = _drug(rng)
    text = rng.choice(NO_ADE_ONE_DRUG).format(d=drug, dur=rng.choice(DURATION))
    return _spec(rng, text, False, [drug], [], {}, [])


def _make_text(rng: random.Random, kind: str, no_drug_texts: list[str]) -> dict:
    if kind == "present":
        return _present(rng)
    if kind == "absent":
        return _absent(rng)
    if kind == "possible":
        return _single(rng, POSSIBLE, "Possible", True, "1", tails=True)
    if kind == "hypothetical":
        return _single(rng, HYPOTHETICAL, "Hypothetical", False, "1")
    if kind == "conditional":
        return _single(rng, CONDITIONAL, "Conditional", False, "1")
    if kind == "someone_else":
        return _single(rng, SOMEONE_ELSE, "Someone_else", True, "1")
    return _no_ade(rng, no_drug_texts)


def _check_task_names(answers: dict[str, dict[str, str]]) -> None:
    """The recorded-answer keys must be the `task:` lines of the prompts."""
    prompts = REPO / "src" / "adverse_drug_event_discovery" / "text" / "prompts"
    tasks = set()
    for path in prompts.glob("*.md"):
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("task:"), path
        tasks.add(first_line.removeprefix("task:").strip())
    assert tasks == set(answers), (tasks, set(answers))


def generate() -> dict:
    rng = random.Random(SEED)
    assert sum(MIX.values()) == N_TEXTS
    kinds = [kind for kind, count in MIX.items() for _ in range(count)]
    rng.shuffle(kinds)
    no_drug_texts = list(NO_ADE_NO_DRUG)
    rng.shuffle(no_drug_texts)
    specs: list[dict] = []
    seen: set[str] = set()
    for kind in kinds:
        for _attempt in range(100):
            spec = _make_text(rng, kind, no_drug_texts)
            if spec["text"] not in seen:
                break
        else:
            message = f"Could not make a new {kind} text"
            raise RuntimeError(message)
        seen.add(spec["text"])
        specs.append(spec)
    flipped = set(random.Random(SEED + 1).sample(range(N_TEXTS), round(N_TEXTS * FLIPPED_SHARE)))

    events, classification, entities, assertions, relations = [], [], [], [], []
    answers: dict[str, dict[str, str]] = {
        "classify_ade": {},
        "extract_entities": {},
        "extract_assertions": {},
        "extract_relations": {},
    }
    for index, spec in enumerate(specs):
        text_id = f"text-{index + 1:04d}"
        text = spec["text"]
        predicted = spec["is_ade"] != (index in flipped)
        events.append({"text_id": text_id, "text": text, "is_ade": spec["is_ade"]})
        classification.append({"text_id": text_id, "predicted_ade": predicted})
        entities += [{"text_id": text_id, **row} for row in spec["entities"]]
        assertions += [{"text_id": text_id, "entity": "ADE", **row} for row in spec["assertions"]]
        relations += [{"text_id": text_id, **row} for row in spec["relations"]]
        answers["classify_ade"][text] = json.dumps({"predicted_ade": predicted})
        answers["extract_entities"][text] = json.dumps(spec["entities"])
        answers["extract_assertions"][text] = json.dumps(spec["assertions"])
        answers["extract_relations"][text] = json.dumps(spec["relations"])
    _check_task_names(answers)
    return {
        "ade_events": events,
        "ade_classification": classification,
        "entities": entities,
        "assertions": assertions,
        "relations": relations,
        "answers": answers,
    }


def main() -> None:
    data = generate()
    tables = {
        "ade_events": pa.Table.from_pylist(data["ade_events"], schema=ADE_EVENTS),
        "ade_classification": pa.Table.from_pylist(
            data["ade_classification"], schema=ADE_CLASSIFICATION
        ),
        "entities": pa.Table.from_pylist(data["entities"], schema=ENTITIES),
        "assertions": pa.Table.from_pylist(data["assertions"], schema=ASSERTIONS),
        "relations": pa.Table.from_pylist(data["relations"], schema=RELATIONS),
    }
    spec = REGISTRY["build_knowledge_graph"]
    tables.update(call_run(spec, tables, spec.params_cls(), None))
    sample_dir = REPO / "data" / "sample"
    for name, table in tables.items():
        pq.write_table(table, sample_dir / f"{name}.parquet")
        print(f"{name}: {table.num_rows} rows")
    answers_path = REPO / "tests" / "recorded_answers.json"
    answers_path.write_text(json.dumps(data["answers"], indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
