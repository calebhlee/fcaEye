# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""All experimental parameters

Sections: 
    1 session
    2 counterbalancing
    3 session structure
    4 timing
    5 gaze
    6 screen
    7 files
    8 stimuli
    9 text
    10 text screen style.

Objects are g0-g7; attributes are m0-m5.
"""

from pathlib import Path

# 1. SESSION ===============================================================

SESSION = {
    "yesConsent": True,          # False: skip the consent form (testing only)
    "yesDemographics": True,     # False: skip the demographic questions
    "yesCalibration": True,      # False: skip calibration
}

# cut down trial numbers for short demo. n trials or None for full trials
DEMO_TRIALS = {
    "practice": None,       # per practice round
    "learning": None,       # per learning block
    "test": None,           # per test block
}

# 2. COUNTERBALANCING ======================================================
# Each participant gets an object set and a ring order, from the number of
# participants already in the participant key file (design.counterbalance):
#   objectSet  = n mod 2 + 1   (ATTRIBUTE_SETS: which feature stands for
#                               which attribute)
#   ringVersion = n mod 7 + 1  (ringOrders)
# 2 and 7 share no factor, so every 14 participants get every object set
# with every ring order once.
COUNTERBALANCE = {
    # Names on the ring, slot 1 to 8 (counter-clockwise). Across the 7 orders
    # every pair of objects sits side by side exactly twice, and every object
    # sits in a different slot in each order.
    "ringOrders": [
        ["g3", "g7", "g4", "g5", "g0", "g1", "g2", "g6"],
        ["g4", "g1", "g6", "g2", "g3", "g0", "g5", "g7"],
        ["g2", "g5", "g1", "g6", "g4", "g3", "g7", "g0"],
        ["g7", "g6", "g3", "g0", "g1", "g5", "g4", "g2"],
        ["g5", "g2", "g0", "g4", "g6", "g7", "g1", "g3"],
        ["g6", "g0", "g7", "g1", "g2", "g4", "g3", "g5"],
        ["g1", "g3", "g2", "g7", "g5", "g6", "g0", "g4"],
    ],
    # Angle of slot 1 (deg), counter-clockwise from 3 o'clock; the same for
    # everyone. 22.5 = half a slot, so no name sits exactly at 3, 6, 9 or
    # 12 o'clock.
    "rotation_deg": 22.5,
}


# 3. SESSION STRUCTURE =====================================================
#   practice -> learning -> test

PHASES = {
    "practiceTrials": 1,           # trials per practice round
    "learnBlockTrials": 32,        # trials per learning block: int * n_object 
    "learnCriterion": 0.90,        # % correct trials needed in a block
    "learnCriterionBlocks": 1,     # consecutive blocks needed to reach criterion
    "learnMaxBlocks": 10,          # session ends if criterion is not met
}

# Euler tour (design.trial_sequence): each transition i -> j appears equally
# often.
EULER_TOUR = {
    "allow_stay": True,     # allow i -> i 
    "tour_repeats": 1,      # times a tour repeats in a block.
}


# 4. TRIAL TIMING (ms) =====================================================

TIMING = {
    "previewDurRange_ms": (600, 1000),  # time between name_on to object_on (random in this range)
    "feedbackDur_ms": 1500,             # feedback screen
    "iti_ms": 1000,                     # blank screen between trials
    "responseTimeout_ms": 10000,         # time allowed to select a name 
}


# 5. GAZE ==================================================================

# Central fixation before each cue
CENTRAL_FIXATION = {
    "centralHold_ms": 1500,      # gaze must stay on the dot this long
    "centralRadius_deg": 2,      # distance from centre that counts as on the dot
    "centralTimeout_ms": 20000,  # time allowed to fixate on the dot
}

# Selecting a name by looking at it
DWELL_SELECTION = {
    "dwell_ms": 1000,           # gaze hold needed to select
    "dwellRadius_deg": 1.5,     # gaze must stay within this distance of where
                                # the hold began
    "blinkTimeout_ms": 300,     # gaze loss up to this long pauses the count;
                                # longer resets it
}

# Live gaze state (recorded as whereGaze column in <stem>_gaze.csv): 
# g0-g7, centre, other or lost
# recorded during trials from dot_on to feedback.
GAZE_STATE = {
    "interval_ms": 10,          # one state per interval of tracker time
}

# Validation after every calibration (calibrate.gaze_validation): a dot at
# the centre and at each of the 8 ring slots (this session's rotation).
# Gaze per dot = median of the samples in the window after the dot appears.
# Pass: at every dot, both-eye gaze error and the distance between the two
# eyes are below the limits. The researcher then accepts or recalibrates.
VALIDATION = {
    "windowStart_ms": 500,          # window start after the dot appears
    "windowEnd_ms": 1000,           # window end; the dot disappears here
    "maxError_deg": 1.0,            # both-eye gaze to dot
    "maxEyeDistance_deg": 1.0,      # left eye to right eye
}

# Calibration (refer to CRS LiveTrack calibrate.py)
CALIBRATION = {
    "viewDist_mm": 850,             # eye to screen
    "screenSize_mm": [400, 300],    # width, height of the screen display
    "targets_deg": [                # target positions (x, y) from centre
        [-9.0,-9.0],[0,-9.0],[9.0,-9.0],
        [-9.0,0],[0,0],[9.0,0],
        [-9.0,9.0],[0,9.0],[9.0,9.0]
        ],
    "setupDelay_ms": 1200,          # wait after a target appears before
                                    # accepting a fixation
    "minFixDur_ms": 1200,           # length of a stable fixation
    "fixTimeout_ms": 5000,          # timeout for fixation
    "fixThreshold_px": 3.1,         # max spread of the pupil-glint vector
                                    # (camera px) for a stable fixation
    "fixInDot_deg": 0.3,            # target inner dot diameter
    "fixOutDot_deg": 0.6,           # target outer dot diameter
    "calibrationCriterion_deg": 0.5,# pass: error (deg) below this for both eyes
}


# 6. SCREEN AND LAYOUT (pixels unless the name says otherwise)==============

DISPLAY = {
    "size": [1024, 768],       # px
    "fullscreen": True,
    "bgColour": [0, 0, 0],     # PsychoPy rgb; 0,0,0 = grey
    "units": "pix",
    "screen" : 1,              #(0 = experimenter; 1 = stimulus monitor)
}

GEOMETRY = {
    "ringRadius": 310,               # screen centre to each name
    "objCount": 8,                   # n_objects (and names) on the ring
    "objSize_px": 120,               # object image size
    "height_name_px": 24,            # letter height of the names
    "centralDotRadius_px": 5,        # fixation dot radius
    "nameSelectMargin_deg": 1.0,     # selection circle radius = widest name's
                                     # centre-to-corner distance + this
    "feedbackNameOffset_px": 70,     # name centre to object centre in feedback
                                     # (object below the name, or above where
                                     # it would not fit)
}


# 7. FILES =================================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "stimDir": PROJECT_DIR / "stimObj",                 # object images
    "dataDir": PROJECT_DIR / "data",                    # output data files
    "fontDir": PROJECT_DIR / "src" / "fonts",          # page fonts
    "keyFile": PROJECT_DIR.parent / "participant_key" / "participant_key.csv",  # SONA ID -> PID
    "debriefLetter": PROJECT_DIR / "src" / "debrief_letter.txt",   # debrief letter txt
    "consentForm": PROJECT_DIR / "src" / "consent_form.txt",       # consent form txt

}

# 8. STIMULI ===============================================================

# Formal context
CONTEXT = {
    #     m0 m1 m2 m3 m4 m5
    "g0": [1, 1, 1, 0, 0, 0],
    "g1": [1, 0, 1, 0, 1, 0],
    "g2": [1, 1, 0, 1, 0, 0],
    "g3": [1, 0, 0, 1, 0, 1],
    "g4": [0, 0, 0, 1, 1, 1],
    "g5": [0, 1, 0, 1, 0, 1],
    "g6": [0, 0, 1, 0, 1, 1],
    "g7": [0, 1, 1, 0, 1, 0],
}

# Visual feature for each attribute, and what 1 and 0 mean (stimuli.py),
# per object set (counterbalanced). The context is the same in both sets;
# only which feature stands for which attribute differs. In set 1 the
# 3-member categories (m2+m4, m3+m5) are outline+slot and hole+circle; in
# set 2 they are colour+hole and outline+stripes, which are 2-member pairs
# in set 1 (and set 1's are 2-member pairs in set 2).
ATTRIBUTE_SETS = {
    1: {
        "m0": {"feature": "colour", 1: "orange", 0: "gray"},
        "m1": {"feature": "stripes", 1: "stripes", 0: "none"},
        "m2": {"feature": "outline", 1: "thick", 0: "none"},
        "m3": {"feature": "hole", 1: "hole", 0: "none"},
        "m4": {"feature": "slot", 1: "slot", 0: "none"},
        "m5": {"feature": "circle", 1: "circle", 0: "square"},
    },
    2: {
        "m0": {"feature": "slot", 1: "slot", 0: "none"},
        "m1": {"feature": "circle", 1: "circle", 0: "square"},
        "m2": {"feature": "hole", 1: "hole", 0: "none"},
        "m3": {"feature": "outline", 1: "thick", 0: "none"},
        "m4": {"feature": "colour", 1: "orange", 0: "gray"},
        "m5": {"feature": "stripes", 1: "stripes", 0: "none"},
    },
}

# Feature order of the digits in image file names; 1 = present.
# E.g. 100001.png = orange circle.
IMAGE_NAME_ORDER = ["colour", "stripes", "outline", "hole", "slot", "circle"]

# Object names (the same in both object sets)
NAMES = {
    "g0": "Guli",
    "g1": "Domu",
    "g2": "Vemi",
    "g3": "Zudo",
    "g4": "Tora",
    "g5": "Kesa",
    "g6": "Pino",
    "g7": "Ruba",
}

# Practice names
PRACTICE_NAMES = {
    "g0": "Dada",
    "g1": "Fifi",
    "g2": "Lolo",
    "g3": "Mimi",
    "g4": "Nunu",
    "g5": "Sasa",
    "g6": "Tete",
    "g7": "Vava",
}

# Practice objects, drawn as plain shapes. PLACEHOLDER pairing with names.
# (colour: "white"/"black", shape: "square"/"triangle", size: "big"/"small")
PRACTICE_OBJECTS = {
    "g0": ("white", "square", "big"),
    "g1": ("white", "square", "small"),
    "g2": ("white", "triangle", "big"),
    "g3": ("white", "triangle", "small"),
    "g4": ("black", "square", "big"),
    "g5": ("black", "square", "small"),
    "g6": ("black", "triangle", "big"),
    "g7": ("black", "triangle", "small"),
}
PRACTICE_SIZES = {
    "bigWidth_px": 90,      # big shape width and height (= real objects'
                            # square, 75% of objSize_px)
    "smallScale": 0.6,      # small size as a fraction of big
}

# 9. TEXT ==================================================================

SCREEN_TEXT = {
    # Greeting screen
    "greeting": [
        ("Welcome",                                                     
         "Welcome and thank you for taking part in this study.\n\n"
         "In this experiment, you will learn made-up names for visual "
         "shapes. You will choose names by looking at them, and an eye "
         "tracker will record where you look.",
         # third part: small grey note above the footer
         "Use the arrow keys to move through the instructions: "
         "\u2192 for next, \u2190 for back."),
        ("Welcome",
         "If you want to stop at any time, press Esc or let the "
         "researcher know.\n\n"),
    ],

    # Demographic questions: (question, hint under the box)
    "sonaId": ("What is your SONA ID?", ""),
    "age": ("What is your age?",
            "press Enter to skip"),
    "gender": "What is your gender?",
    "selfDescribe": "Please describe your gender",

    # Instructions. Optional third part: small trial
    # pictures as (picture, caption). Pictures: "dot", "names", "cue",
    # "correct", "incorrect". They use practice objects and names.
    "task": [
        ("Instruction",
         "On each trial, a dot appears at the centre of the screen. Look at "
         "the dot and hold your gaze on it.",
         [("dot", "")]),
        ("Instruction",
         "After a moment, several names will appear in a ring around the dot. "
         "Keep holding your gaze on the central dot until it changes into "
         "a shape.",
         [("names", "")]),
        ("Instruction",
         "One of the names belongs to the shape. "
         "Once a shape replaces the dot, look at the name that belongs to "
         "the shape and keep looking at it to make your choice. "
         "Once you hold your gaze at your chosen name long enough, your "
         "selection will be confirmed.",
         [("cue", "")]),
        ("Instruction",
         "After each choice, the shape appears next to its CORRECT name, "
         "with a green circle around them. "
         "If your choice was INCORRECT, a red X marks the name you chose.",
         [("correct", "Correct"), ("incorrect", "Incorrect")]),
        ("Instruction",
         "Before the task starts, you will go through calibration of the "
         "eye tracker."),
    ],

    "calibration": [
        ("Calibration",
         "You will go through the calibration process to adjust the "
         "eye tracker to your eyes.\n\n"
         "Small dots will appear on the screen, one at a time. Look "
         "directly at each dot until it disappears.\n\n"
         "Please keep your head still on the chin rest."),
    ],

    # Calibration result
    # success
    # {result}: error and dots acquired per eye (calibrate.calibration_summary)
    "calibrationDone": [("", "Calibration was successful.\n\n{result}")],
    # failure
    "calibrationFailed": [
        ("", "Calibration wasn't successful. We'll do it again.\n\n{result}"),
    ],

    # Before the validation dots
    "validation": [
        ("Calibration check",
         "Dots will appear again, one at a time. Look directly at each dot "
         "until it disappears."),
    ],
    # Validation result. {result}: calibrate.report_validation.
    # The researcher presses \u2192 (accept) or R (calibrate again).
    "validationResult": [
        ("Calibration check",
         "{result}\n\n[\u2192] continue        [R] calibrate again"),
    ],

    # Practice screen
    "practice": [
        ("Practice",
         "You will first practise choosing names with your eyes, with a "
         "small set of simple shapes.\n\n"
         "After each practice trial, you can choose to practise again or "
         "move on to the task."),
    ],

    # After each practice round
    "practiceChoice": [
        ("", "Press [Space] to practise again.\n\n"
             "Press [\u2192] to move on to the task."),
    ],

    # Before learning 1, after the practice
    "learning": [
        ("Learning",
         "Now you are moving on to the real task.\n\n"
         "You will learn the names of a new set of shapes. At first, you'll "
         "need to guess. After each choice, you will see whether you "
         "were correct. Use the feedback to learn which name belongs to "
         "each shape.\n\n"
         "Learning continues in rounds until you choose correctly most of "
         "the time. Please choose as quickly and accurately as you can."),
    ],
    
    # After each learning round. 
    # Fields are filled in by experiment.run_learning
    "roundEnd": [
        ("", "You chose the correct name on {percent}% of trials in round "
             "{round}.\n\n"
             "Press [\u2192] to move on to {next}."),
    ],
    "roundEndNext": {
        "round": "the next round",      # criterion not met yet
        "test": "the test",             # criterion met
        "end": "the end of this part",  # last round, criterion not met
    },

    # After criterion, before Testing phase.
    "test": [
        ("Test",
         "Now you will be tested on the names you learned.\n\n"
         "The task is the same as before, but you will not be given "
         "feedback whether your choices are correct."),
    ],

    
    # After the last test, before the post-task questions
    "taskEnd": [
        ("", "You have now finished the experiment.\n\n"
             "We will ask a few optional questions about your experience."),
    ],

    # After the post-task questions; before debrief letter.
    "thankYou": [
        ("Thank you for your participation!",
         "Please let the researcher know that you have finished.\n\n"
         "Continue to read the debrief form on the next pages."),
    ],

    # Last screen, after the debrief letter. Only Esc (the researcher) closes it.
    "callResearcher": [("", "Please call the researcher.")],

    # After the consent form pages: the page with the two buttons
    # (CONSENT_BUTTONS), clicked with the mouse.
    "consent": [("Consent", "Please click one of the options below.")],

    # Shown before an abandoned round starts again
    "blockRestart": [
        ("", "The round will start again from the beginning."),
    ],

    # Learning: shown before the next round after an interrupted round
    "blockNext": [
        ("", "We will continue with the next round."),
    ],

    # Pause screen (Esc)
    "pause": [("Paused", "Please call the researcher.")],

    # After "End session", to confirm
    "endConfirm": [
        ("End the session?",
         "The data recorded so far will be saved. Move "
         "to the debrief letter."),
    ],
}

# Page footer. "last" replaces "next" on a screen's last page.
NAV_TEXT = {"back": "\u2190  Back", "next": "Next  \u2192",
            "last": "Continue  \u2192"}

# Pause screen buttons (for the researcher)
# Consent choice buttons (the two statements of the approved consent form)
CONSENT_BUTTONS = {
    "agree": "I agree to participate in this study",
    "decline": "I do not agree to participate in this study",
}

PAUSE_BUTTONS = {
    "continue": "Continue",
    "recalibrate": "Recalibrate",
    "skip": "Skip to next section",
    "end": "End session",
    "back": "Go back",
    "endConfirm": "Yes, end the session",
}

# Gender options, in display order
GENDER_OPTIONS = [
    "Woman",
    "Man",
    "Non-binary",
    "Prefer to self-describe",
    "Prefer not to answer",
]

# Post-task questions (optional).
POSTTASK = {
    "q1": "Did you notice any pattern? If yes, please describe it.",
    "q2": "Did you use any particular way of remembering the shape-name pairs?",
    "q3": "Which visual feature(s) stood out the most?",
    # label under each feature image
    "q3Labels": {"colour": "Colour", "stripes": "Stripes", "outline": "Outline",
                 "hole": "Hole", "slot": "Notch", "circle": "Round shape"},
    "q4": "How easy or difficult was the task?",
    "q4Ends": ("Very easy", "Very difficult"),     # labels under 1 and 7
}


# 10. LOOK OF TEXT SCREENS (instructions, questions, pause, debrief)

# Text screens are white with black text; calibration and trials use
# DISPLAY["bgColour"]. Colours are hex codes. Sizes in px.
# Font bundled in src/fonts (Source Sans 3, SIL Open Font Licence).
PAGE_STYLE = {
    "titleFont": "Source Sans 3",   # titles in semibold
    "bodyFont": "Source Sans 3",
    "sheetHeight": 660,             # text area height
    "columnWidth": 640,             # text width; about 60 characters a line
    "titleHeight": 34,              # title letter height
    "bodyHeight": 23,               # body letter height
    "lineSpacing": 1.12,            # TextBox2 units: 1 = the font's own spacing
    "paper": "#FFFFFF",             # background of text screens
    "ink": "#000000",               # titles, "Next"
    "body": "#000000",              # body text
    "muted": "#6E6E6E",             # "Back", notes, picture captions
    "hairline": "#BDBDBD",          # button edges (pause screen)
    "accent": "#000000",            # button edge under the mouse, chosen option
    "hover": "#EEEEEE",             # button under the mouse
    "danger": "#9E3B33",            # "End session"
    "box": "#FFFFFF",               # typing boxes and answer options
    "boxLine": "#BDBDBD",           # their edges
    "chosen": "#E6E6E6",            # a chosen option
    "pictureScale": 0.28,           # trial picture size / real screen size
    "pictureNameHeight": 13,        # name height in pictures (above scale,
                                    # so it stays readable)
}

# Letters (consent form, debrief letter): letter heights (px), text column
# width (px) and picture width (fraction of that column). Separate from the
# other text screens. 1 deg = about 38 px at this viewing distance.
LETTER_STYLE = {
    "consent": {
        "titleHeight": 24,
        "headingHeight": 18,
        "bodyHeight": 15,
        "captionHeight": 13,
        "columnWidth": 800,
        "imageScale": 0.5,
    },
    "debrief": {
        "titleHeight": 34,
        "headingHeight": 23,
        "bodyHeight": 19,
        "captionHeight": 16,
        "columnWidth": 640,
        "imageScale": 0.8,
    },
}
