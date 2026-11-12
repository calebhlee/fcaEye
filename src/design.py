# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""Counterbalancing, stimulus sets, trial orders, and design checks.

An object's image file name is its CONTEXT row, mapped to features by
ATTRIBUTE_SETS[object set] and written in IMAGE_NAME_ORDER (see stimuli.py).
"""

import random
import sys
from dataclasses import dataclass

from config import (ATTRIBUTE_SETS, COUNTERBALANCE, DEMO_TRIALS, EULER_TOUR,
                    GEOMETRY, IMAGE_NAME_ORDER, NAMES, PATHS, PHASES,
                    PRACTICE_NAMES, PRACTICE_OBJECTS, PROJECT_DIR)
from config import CONTEXT

# eulerTours/ sits at the project root, outside src/
sys.path.insert(0, str(PROJECT_DIR))
from eulerTours import euler


def object_image(obj, object_set):
    """Image file name for one object in an object set, e.g. "111000.png".

    The same CONTEXT row gives a different file in each object set.
    """
    attributes = ATTRIBUTE_SETS[object_set]
    ft = {}
    for attr, value in zip(attributes, CONTEXT[obj]):
        ft[attributes[attr]["feature"]] = value
    return "".join(str(ft[feature]) for feature in IMAGE_NAME_ORDER) + ".png"


def counterbalance(n_participants):
    """(object set, ring version, ring order, rotation) for the next
    participant, given how many are already in the key file.

    objectSet = n mod (number of sets) + 1; ringVersion = n mod (number of
    ring orders) + 1. With 2 sets and 7 orders, every 14 participants get
    each set with each order once.
    """
    n = n_participants
    object_set = n % len(ATTRIBUTE_SETS) + 1
    ring_version = n % len(COUNTERBALANCE["ringOrders"]) + 1
    ring_order = list(COUNTERBALANCE["ringOrders"][ring_version - 1])
    return (object_set, ring_version, ring_order,
            float(COUNTERBALANCE["rotation_deg"]))


@dataclass
class StimulusSet:
    """Names, context and images for the practice or one phase.

    All sets use labels g0-g7, so trial files keep the same columns.

    label:      "practice" or "task"
    context:    {object: attribute row}; None for the practice
    images:     {object: image file name}; None for the practice
    ring_order: objects in ring-slot order
    """
    label: str
    names: dict
    context: dict | None
    images: dict | None
    ring_order: list
    stim_dir: object = None
    object_set: int | None = None

    @property
    def objects(self):
        return list(self.names)

    def image_code(self, obj):
        """Image file shown for obj, without ".png", e.g. "000111" (feature
        digits in IMAGE_NAME_ORDER), or "" for the practice. Differs between
        object sets for the same object; its CONTEXT row does not."""
        if self.images is None:
            return ""
        return self.images[obj].removesuffix(".png")


def stimulus_sets(ring_order, object_set):
    """{label: StimulusSet} for the practice and the task.

    ring_order, object_set: this session's (counterbalance); the practice
    keeps its own fixed order.
    """
    return {
        "practice": StimulusSet("practice", PRACTICE_NAMES, None, None,
                                list(PRACTICE_NAMES)),
        "task": StimulusSet(
            label="task",
            names=NAMES,
            context=CONTEXT,
            images={obj: object_image(obj, object_set) for obj in CONTEXT},
            ring_order=list(ring_order),
            stim_dir=PATHS["stimDir"],
            object_set=object_set,
        ),
    }


def new_seed():
    """Seed for one block; saved so the block's order can be rebuilt."""
    return random.randint(1, 9999)


def shuffled_sequence(seed, objects, n_trials):
    """n_trials targets in random order, each object as equally often as possible.

    Uses its own random generator, so the seed does not fix other random
    values (preview jitter, rotation).
    """
    repeats = -(-n_trials // len(objects))          # rounded up
    sequence = list(objects) * repeats
    random.Random(seed).shuffle(sequence)
    return sequence[:n_trials]


def trial_sequence(seed, objects=None):
    """Test-block targets from an Euler tour, e.g. ["g3", "g0", "g5", ...].

    Each transition i -> j appears exactly tour_repeats times. The same
    seed always gives the same sequence.
    """
    if objects is None:
        objects = list(CONTEXT)

    # euler.py uses the shared random generator. Restore its state after,
    # so this seed does not fix preview jitter or ring rotation.
    saved_state = random.getstate()
    random.seed(seed)
    try:
        tour = euler.Euler(stimuli=len(objects),
                           stim_repeat=EULER_TOUR["allow_stay"],
                           seq_repeats=EULER_TOUR["tour_repeats"])
        labels = tour.get_sequence()
    finally:
        random.setstate(saved_state)

    # euler.py labels are "0", "1", ...: positions in objects
    return [objects[int(label)] for label in labels]


def attributes_text(attributes):
    """Attribute coding as one cell, e.g. "m0:colour[1=orange/0=gray];...".

    No commas, so the cell stays readable in a plain text editor.
    """
    return ";".join(f"{attr}:{spec['feature']}[1={spec[1]}/0={spec[0]}]"
                    for attr, spec in attributes.items())


def check_design():
    """Raise an error before anything opens if the config values do not fit."""
    n_attributes = len(CONTEXT["g0"])
    expected = [f"m{j}" for j in range(n_attributes)]
    for set_n, attributes in ATTRIBUTE_SETS.items():
        if list(attributes) != expected:
            raise ValueError(f"ATTRIBUTE_SETS[{set_n}] keys must be {expected} "
                             "in this order, to match the columns of CONTEXT; "
                             f"they are {list(attributes)}")
        features = [spec["feature"] for spec in attributes.values()]
        if sorted(features) != sorted(IMAGE_NAME_ORDER):
            raise ValueError(f"ATTRIBUTE_SETS[{set_n}] must use each of "
                             f"{IMAGE_NAME_ORDER} exactly once; it uses "
                             f"{features}")

    if list(CONTEXT) != list(NAMES):
        raise ValueError("CONTEXT and NAMES must list the same objects "
                         "in the same order")
    if len(CONTEXT) != GEOMETRY["objCount"]:
        raise ValueError(f"CONTEXT has {len(CONTEXT)} objects but "
                         f"GEOMETRY['objCount'] is {GEOMETRY['objCount']}")

    for obj, row in CONTEXT.items():
        if len(row) != n_attributes or any(v not in (0, 1) for v in row):
            raise ValueError(f"CONTEXT[{obj!r}] = {row}: it needs "
                             f"{n_attributes} values, each 0 or 1")

    for k, ring in enumerate(COUNTERBALANCE["ringOrders"], start=1):
        if sorted(ring) != sorted(CONTEXT):
            raise ValueError(f"COUNTERBALANCE['ringOrders'] order {k} = {ring}: "
                             f"it must hold each of {list(CONTEXT)} exactly once")
    rotation = COUNTERBALANCE["rotation_deg"]
    if isinstance(rotation, bool) or not isinstance(rotation, (int, float)):
        raise ValueError("COUNTERBALANCE['rotation_deg'] must be a number "
                         f"of degrees; it is {rotation!r}")

    if not isinstance(EULER_TOUR["allow_stay"], bool):
        raise ValueError("EULER_TOUR['allow_stay'] must be True or False; "
                         f"it is {EULER_TOUR['allow_stay']!r}")
    repeats = EULER_TOUR["tour_repeats"]
    if not isinstance(repeats, int) or repeats < 1:
        raise ValueError("EULER_TOUR['tour_repeats'] must be a whole number "
                         f"of 1 or more; it is {repeats!r}")

    n_objects = len(CONTEXT)
    if PHASES["learnBlockTrials"] % n_objects != 0:
        raise ValueError(f"PHASES['learnBlockTrials'] = "
                         f"{PHASES['learnBlockTrials']} must be a multiple of "
                         f"{n_objects}, so each object appears equally often")
    if not isinstance(PHASES["practiceTrials"], int) or PHASES["practiceTrials"] < 1:
        raise ValueError("PHASES['practiceTrials'] must be a whole number "
                         f"of 1 or more; it is {PHASES['practiceTrials']!r}")
    if not 0 < PHASES["learnCriterion"] <= 1:
        raise ValueError("PHASES['learnCriterion'] is a proportion, "
                         "between 0 and 1")
    if PHASES["learnCriterionBlocks"] > PHASES["learnMaxBlocks"]:
        raise ValueError("PHASES['learnCriterionBlocks'] is larger than "
                         "PHASES['learnMaxBlocks']: the criterion could never "
                         "be met")
    for stage, limit in DEMO_TRIALS.items():
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise ValueError(f"DEMO_TRIALS[{stage!r}] must be None or a "
                             f"whole number of 1 or more; it is {limit!r}")
    if list(PRACTICE_OBJECTS) != list(PRACTICE_NAMES):
        raise ValueError("PRACTICE_OBJECTS must list the same objects as "
                         "PRACTICE_NAMES, in the same order")
    allowed = ({"white", "black"}, {"square", "triangle"}, {"big", "small"})
    for obj, features in PRACTICE_OBJECTS.items():
        if len(features) != 3 or any(f not in a for f, a in zip(features, allowed)):
            raise ValueError(f"PRACTICE_OBJECTS[{obj!r}] = {features}: use "
                             "(white/black, square/triangle, big/small)")
    if len(set(PRACTICE_OBJECTS.values())) != len(PRACTICE_OBJECTS):
        raise ValueError("PRACTICE_OBJECTS: two objects look the same")
    for label, names in (("PRACTICE_NAMES", PRACTICE_NAMES),):
        if list(names) != list(CONTEXT):
            raise ValueError(f"{label} must use the same object labels "
                             "as CONTEXT")

    for set_n in ATTRIBUTE_SETS:
        images = {obj: object_image(obj, set_n) for obj in CONTEXT}

        # Equal rows give equal images. A formal context allows this, so only
        # warn; but participants cannot tell such objects apart.
        seen = {}
        for obj, image in images.items():
            if image in seen:
                print(f"WARNING: object set {set_n}: {seen[image]} and {obj} "
                      f"have the same row in CONTEXT, so both show {image}")
            seen.setdefault(image, obj)

        missing = [image for image in images.values()
                   if not (PATHS["stimDir"] / image).exists()]
        if missing:
            raise FileNotFoundError(f"object set {set_n}: not in "
                                    f"{PATHS['stimDir']}: {missing}")
