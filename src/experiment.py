# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""Session and trial flow.

Session: greeting, demographics -> instructions -> calibration ->
recording starts -> practice rounds -> learning (until criterion) ->
test -> post-task questions -> thank you, debrief letter.
Esc opens the pause screen (presentation.pause_menu).
"""

import random
import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

from psychopy import core

import calibrate
import design
import geometry
import response
from data_record import marker, trialdata
from data_record.pid import assign_pid
from config import (CENTRAL_FIXATION, COUNTERBALANCE, DEMO_TRIALS, DISPLAY,
                    GENDER_OPTIONS,
                    IMAGE_NAME_ORDER, PATHS, PHASES, POSTTASK, SCREEN_TEXT,
                    SESSION, TIMING)
from presentation import (EndSession, Presentation, RestartBlock,
                          SkipSection, check_escape,
                          set_between_blocks_recalibration,
                          set_trials_running)


def ask_demographics(pres):
    """Ask SONA ID, age (optional) and gender."""
    digits = "0123456789"
    question, hint = SCREEN_TEXT["sonaId"]
    sona_id = pres.type_answer(question, digits, hint=hint, max_len=6,
                               is_valid=lambda a: len(a) == 6)
    question, hint = SCREEN_TEXT["age"]
    age = pres.type_answer(question, digits, hint=hint, max_len=2,
                           is_valid=lambda a: 1 <= int(a) <= 99, optional=True)
    gender = pres.choose_option(SCREEN_TEXT["gender"], GENDER_OPTIONS)

    if gender == "Prefer to self-describe":
        letters = "abcdefghijklmnopqrstuvwxyz"
        typed = pres.type_answer(SCREEN_TEXT["selfDescribe"],
                                 letters + letters.upper() + " -", max_len=24)
        gender = f"self-described: {typed}"
    return {"sonaID": sona_id, "age": "" if age is None else int(age),
            "gender": gender}


def posttask_q(pres):
    """Ask the post-task questions; save the answers in the session file."""
    # Q3 image for each feature: only that feature present, e.g. 100000.png
    images = []
    for feature in IMAGE_NAME_ORDER:
        row = "".join("1" if f == feature else "0" for f in IMAGE_NAME_ORDER)
        images.append((PATHS["stimDir"] / f"{row}.png",
                       POSTTASK["q3Labels"][feature]))

    answers = {
        "q1Pattern": pres.type_long_answer(POSTTASK["q1"], "Question 1 of 4"),
        "q2Strategy": pres.type_long_answer(POSTTASK["q2"], "Question 2 of 4"),
    }
    chosen = pres.choose_images(POSTTASK["q3"], images, "Question 3 of 4")
    answers["q3Features"] = None if chosen is None else "|".join(chosen)
    answers["q4Difficulty"] = pres.rate_scale(POSTTASK["q4"], *POSTTASK["q4Ends"],
                                              progress="Question 4 of 4")

    path = trialdata.update_session(answers)
    print(f"Post-task answers added to {path}")
    return answers


def interruption_reason(e):
    """Value of the interruption column for an exception from the pause screen."""
    if getattr(e, "fixation_timeout", False):
        return "fixation_timeout"
    if isinstance(e, RestartBlock):
        return "recalibration" if e.recalibrate else "break"
    if isinstance(e, SkipSection):
        return "skip"
    return "end"                      # EndSession


def run_trial(pres, target, trial_n, block_trial_n, previous_obj, positions,
              feedback=True):
    """Run one trial and return its data row.

    Args:
        trial_n: session-wide trial number (sessionTrialN; the marker key).
        block_trial_n: trial number within the block (blockTrialN).
        positions: ring slot positions, fixed for the session
            (Session.positions; in the session file).
        previous_obj: previous target (the prime); None on a block's first trial.
        feedback: False in test blocks.

    Names appear before the object so that cue-to-gaze time does not
    include searching for them. Each event is marked right after its flip.

    If the pause screen interrupts the trial (RestartBlock, SkipSection or
    EndSession), the row so far is attached to the exception as
    e.trial_row, with outcome "interrupted" and the interruption column
    set; the exception is then raised again. Columns of events the trial
    did not reach stay empty.
    """
    times = {}

    def mark(event):
        # Three times per event: PsychoPy time and tracker time (both in
        # the trial file), and a marker in the tracker file.
        column = trialdata.MARKER_TIMES[event]
        times[column] = core.getTime() * 1000         # PsychoPy clock, ms
        times[trialdata.tracker_column(column)] = marker.tracker_time_us()
        marker.mark(event, trial=trial_n)

    def tracker_us(event):
        return times[trialdata.tracker_column(trialdata.MARKER_TIMES[event])]

    preview_ms = random.uniform(*TIMING['previewDurRange_ms'])

    # None is written as an empty cell.
    row = {
        "sessionTrialN": trial_n,
        "blockTrialN": block_trial_n,
        "targetObj": target,
        "previousObj": previous_obj,
        "name": pres.stim_set.names[target],
        "targetImage": pres.stim_set.image_code(target),
        "previewDur_ms": preview_ms,
    }

    try:
        # --- 1. central fixation -----------------------------------------
        pres.draw_fixation()
        pres.flip()
        mark("dot_on")
        # Live gaze state (live_gaze markers), from the dot until feedback
        # or blank
        response.STATES.start(trial_n, positions, pres.ring_order,
                              pres.name_radius_px, tracker_us("dot_on"))
        response.wait_for_central_fixation(pres,
                                           CENTRAL_FIXATION['centralHold_ms'])
        mark("dot_fixated")

        # --- 2. preview ---------------------------------------------------
        # Random duration, so the object onset cannot be anticipated.
        pres.draw_names(positions)
        pres.draw_fixation()
        pres.flip()
        mark("names_on")
        response.STATES.show_names(tracker_us("names_on"))
        response.wait_for_central_fixation(pres, preview_ms, positions)

        # --- 3. cue and response -----------------------------------------
        responder = response.GazeDwellResponder(positions, pres.ring_order,
                                                pres.name_radius_px)

        pres.draw_names(positions)
        pres.draw_object(target)
        pres.flip()
        mark("object_on")
        responder.start()

        # The responder is polled once per frame.
        clock = core.Clock()
        while (clock.getTime() * 1000 < TIMING['responseTimeout_ms']
               and responder.result() is None):
            check_escape()
            responder.poll()
            pres.draw_names(positions)
            pres.draw_object(target)
            pres.flip()

        outcome = responder.result()
        if outcome is None:
            mark("timeout")
        else:
            mark("selection")

        # --- 4. feedback --------------------------------------------------
        selection = None if outcome is None else outcome['selection']
        if feedback:
            pres.draw_feedback(target, selection, positions)
            pres.flip()
            mark("feedback_on")
            response.STATES.stop(tracker_us("feedback_on"))
            core.wait(TIMING['feedbackDur_ms'] / 1000)    # core.wait takes s

        # --- 5. blank interval --------------------------------------------
        pres.flip()
        mark("blank_on")
        response.STATES.stop(tracker_us("blank_on"))   # test blocks (no feedback)
        core.wait(TIMING['iti_ms'] / 1000)

    except (RestartBlock, SkipSection, EndSession) as e:
        row.update({"outcome": "interrupted",
                    "interruption": interruption_reason(e)})
        row.update(times)
        e.trial_row = row
        raise

    if outcome is None:
        result = "timeout"
    elif selection == target:
        result = "correct"
    else:
        result = "incorrect"

    row.update({
        "selectedObj": selection,
        "outcome": result,
        "selection_ms": None if outcome is None else outcome["selection_ms"],
        "selectionStart_us":
            None if outcome is None else outcome["selection_start_us"],
    })
    row.update(times)
    return row


def demo_cut(targets, stage):
    """TEST: keep the first DEMO_TRIALS[stage] targets (all if None)."""
    limit = DEMO_TRIALS[stage]
    return targets if limit is None else targets[:limit]


class Session:
    """Session-wide trial count, rows and current calibration.

    trial_n counts interrupted trials too, so trial numbers stay unique.
    calibration_n: calibrations so far (0 if calibration was skipped); each
    recalibration adds 1. The current calibration's error is written on
    every trial row.
    positions: ring slot positions (one ring rotation for the session).
    """

    def __init__(self, accuracy, positions):
        self.trial_n = 0
        self.positions = positions
        self.rows = []
        self.calibration_n = 0
        self.calibration = {}
        self.new_calibration(accuracy)

    def new_calibration(self, accuracy):
        """Count one calibration (none if accuracy is empty) and keep its error."""
        if accuracy:
            self.calibration_n += 1
        self.calibration = {
            "calibrationN": self.calibration_n,
            "calibrationErrorL_deg": calibration_error(accuracy, "left"),
            "calibrationErrorR_deg": calibration_error(accuracy, "right"),
        }


def run_block(pres, session, block_info, targets, feedback):
    """Run one block of trials; return its rows.

    block_info and the current calibration are written on every row of the
    block. An interrupted trial's row is written too, then the exception
    goes on to the caller.
    """
    rows = []
    previous_obj = None
    pres.park_mouse()                   # cursor off the participant's screen
    set_trials_running(True)
    try:
        for block_trial_n, target in enumerate(targets, start=1):
            session.trial_n += 1
            base = {**block_info, "feedback": feedback,
                    **session.calibration}
            try:
                trial = run_trial(pres, target, session.trial_n,
                                  block_trial_n, previous_obj,
                                  session.positions, feedback)
            except (RestartBlock, SkipSection, EndSession) as e:
                row = {**base, **e.trial_row}
                trialdata.write_row(row)
                session.rows.append(row)
                raise
            row = {**base, **trial}
            trialdata.write_row(row)
            session.rows.append(row)
            rows.append(row)
            previous_obj = target
    finally:
        # Runs before the caller handles RestartBlock, so Esc during a
        # recalibration is not treated as during trials.
        set_trials_running(False)
    return rows


def block_info(phase, block_n, test_attempt, seed):
    """Block columns, written on every trial row.

    block_n is None for practice (block left empty); test_attempt is None
    outside test (testAttempt left empty).
    """
    return {"phase": phase, "block": block_n, "testAttempt": test_attempt,
            "blockSeed": seed}


def block_interrupted(pres, session, info, restart, page):
    """Recalibrate if asked, then show page.

    The interrupted trial's row (interruption column) is already written.
    """
    reason = "recalibration" if restart.recalibrate else "break"
    print(f"{info['phase']} block {info['block']} interrupted ({reason}) "
          f"at trial {session.trial_n}.")
    if restart.recalibrate:
        session.new_calibration(recalibrate(pres, session.positions))
    pres.show_pages(SCREEN_TEXT[page])


def run_block_until_done(pres, session, phase, stim_set,
                         make_targets, feedback):
    """Run a practice round; if interrupted, run it again with a new seed.

    Practice rows leave block and testAttempt empty.
    """
    pres.use_set(stim_set)
    while True:
        seed = design.new_seed()
        info = block_info(phase, None, None, seed)
        try:
            return run_block(pres, session, info, make_targets(seed), feedback)
        except RestartBlock as restart:
            block_interrupted(pres, session, info, restart, "blockRestart")


def run_practice(pres, session, stim_set):
    """Practice rounds until the participant chooses to move on."""
    try:
        while True:
            run_block_until_done(
                pres, session, "practice", stim_set,
                lambda seed: demo_cut(design.shuffled_sequence(
                    seed, stim_set.objects, PHASES["practiceTrials"]),
                    "practice"),
                feedback=True)
            key = pres.show_choice(SCREEN_TEXT["practiceChoice"],
                                   ["space", "right"])
            again = key == "space"
            if not again:
                return
    except SkipSection:
        print("Practice skipped by the researcher.")


def run_learning(pres, session, phase, stim_set):
    """Learning blocks until the criterion is met.

    An interrupted block (pause screen: Continue or Recalibrate) is not
    counted: the session moves on to the next block number, the in-a-row
    count stays as it was, and only completed blocks count toward
    PHASES["learnMaxBlocks"]. If the criterion is not met by then, raises
    EndSession.
    """
    pres.use_set(stim_set)
    try:
        in_a_row = 0
        completed = 0
        block_n = 0
        while completed < PHASES["learnMaxBlocks"]:
            block_n += 1
            seed = design.new_seed()
            info = block_info(phase, block_n, None, seed)
            targets = demo_cut(design.shuffled_sequence(
                seed, stim_set.objects, PHASES["learnBlockTrials"]), "learning")
            try:
                rows = run_block(pres, session, info, targets, feedback=True)
            except RestartBlock as restart:
                block_interrupted(pres, session, info, restart, "blockNext")
                continue
            completed += 1

            n_correct = sum(row["outcome"] == "correct" for row in rows)
            proportion = n_correct / len(rows)
            if proportion >= PHASES["learnCriterion"]:
                in_a_row += 1
            else:
                in_a_row = 0
            print(f"{phase} block {block_n}: {n_correct}/{len(rows)} correct, "
                  f"{in_a_row} in a row at criterion")
            met = in_a_row >= PHASES["learnCriterionBlocks"]
            if met:
                next_part = "test"
            elif completed == PHASES["learnMaxBlocks"]:
                next_part = "end"
            else:
                next_part = "round"
            # Esc here offers Recalibrate (between blocks)
            set_between_blocks_recalibration(
                lambda: recalibrate_between_blocks(pres, session))
            try:
                pres.show_pages(SCREEN_TEXT["roundEnd"],
                                fill={"round": block_n,
                                      "percent": round(100 * proportion),
                                      "next":
                                          SCREEN_TEXT["roundEndNext"][next_part]})
            finally:
                set_between_blocks_recalibration(None)
            if met:
                return

        raise EndSession(f"{phase}: criterion not met in "
                         f"{PHASES['learnMaxBlocks']} blocks")
    except SkipSection:
        print(f"{phase} skipped by the researcher.")


def test_targets(stim_set, avoid_first=None):
    """(seed, targets) for a test block: one Euler tour.

    avoid_first: the new tour must not start with this object (the first
    object of an interrupted tour). New seeds are drawn until it does not.
    """
    while True:
        seed = design.new_seed()
        targets = demo_cut(design.trial_sequence(seed, stim_set.objects), "test")
        if targets[0] != avoid_first:
            return seed, targets


def run_test(pres, session, phase, stim_set):
    """Run one test block: one Euler tour, no feedback.

    If interrupted (Continue or Recalibrate), it starts again as the next
    attempt, with a new tour that starts from a different object.
    """
    pres.use_set(stim_set)
    try:
        attempt = 0
        avoid_first = None
        while True:
            attempt += 1
            seed, targets = test_targets(stim_set, avoid_first)
            info = block_info(phase, 1, attempt, seed)
            try:
                run_block(pres, session, info, targets, feedback=False)
                return
            except RestartBlock as restart:
                block_interrupted(pres, session, info, restart, "blockRestart")
                avoid_first = targets[0]
    except SkipSection:
        print(f"{phase} skipped by the researcher.")


def calibration_error(accuracy, eye):
    """Calibration error (deg) of one eye ("left"/"right"), or None."""
    entry = accuracy.get(eye)
    return None if entry is None else round(entry["accuracy_deg"], 3)


def run_calibration(pres):
    """Calibrate until both eyes pass (no attempt limit).

    Assumes the tracker is set to raw results and is tracking.
    Returns (accuracy, attempts).
    """
    pres.show_pages(SCREEN_TEXT["calibration"])
    attempts = 0
    while True:
        attempts += 1
        pres.park_mouse()
        accuracy = calibrate.gaze_calibration(pres.win)
        # Result per eye on the screen, e.g. "Left eye: 0.16 deg, 9 of 9 dots"
        fill = {"result": calibrate.calibration_summary(accuracy)}
        if calibrate.report_calibration(accuracy, attempts):
            print(f"PASSED on attempt {attempts}.")
            pres.show_pages(SCREEN_TEXT["calibrationDone"], fill=fill)
            return accuracy, attempts
        print(f"FAILED (attempt {attempts}); running it again. Adjust the "
              "camera or the participant if needed (Esc: pause screen).")
        pres.show_pages(SCREEN_TEXT["calibrationFailed"], fill=fill)


def recalibrate_between_blocks(pres, session):
    """Recalibrate from the pause screen on the round-end screen.

    That screen is white (text page), so the trial background is set for the
    calibration and the white restored after. The next block's rows get the
    new calibrationN and errors.
    """
    print("Recalibrating between blocks.")
    previous = list(pres.win.color)
    pres.win.color = DISPLAY["bgColour"]
    pres.win.clearBuffer()
    try:
        session.new_calibration(recalibrate(pres, session.positions))
    finally:
        pres.win.color = previous
        pres.win.clearBuffer()


def to_calibrated_mode():
    """Tracker to screen-pixel results, tracking. Set while stopped, as in
    CRS's demos; waits past the clock reset about 0.4 s after the start."""
    LiveTrack.StopTracking()
    LiveTrack.SetResultsTypeCalibrated()
    LiveTrack.ClearDataBuffer()
    LiveTrack.StartTracking()
    core.wait(0.5)


def to_raw_mode():
    """Tracker to raw results (pupil/glint vectors), tracking: calibration."""
    LiveTrack.StopTracking()
    LiveTrack.SetResultsTypeRaw()
    LiveTrack.StartTracking()


def calibrate_and_validate(pres, positions):
    """Calibrate, then validate, until the researcher accepts.

    Expects raw results and tracking; leaves screen-pixel results and
    tracking. Validation dots: the centre and the 8 ring slots (positions).
    After each validation the researcher presses right arrow (accept) or R
    (calibrate again), whether it passed or not.
    Marker (only while recording): validation_start, then validation_result
    with maxError_deg, maxEyeDistance_deg, passed and choice.
    Returns (accuracy, calibration attempts, validation marker fields).
    """
    points = [(0.0, 0.0)] + list(positions)
    labels = ["centre"] + [f"slot{i + 1}" for i in range(len(positions))]
    total_attempts = 0
    while True:
        accuracy, attempts = run_calibration(pres)
        total_attempts += attempts
        to_calibrated_mode()

        pres.show_pages(SCREEN_TEXT["validation"])
        pres.park_mouse()
        marker.mark("validation_start")
        results = calibrate.gaze_validation(pres.win, points)
        passed, fields, text = calibrate.report_validation(results, labels)

        page = [(title, body.format(result=text))
                for title, body in SCREEN_TEXT["validationResult"]]
        key = pres.show_choice(page, ["right", "r"])
        fields["choice"] = "accept" if key == "right" else "recalibrate"
        marker.mark("validation_result", **fields)
        print(f"Researcher chose: {fields['choice']}")
        if fields["choice"] == "accept":
            return accuracy, total_attempts, fields
        to_raw_mode()


def recalibrate(pres, positions):
    """Calibrate and validate again mid-session, with the data file open.

    The data file keeps recording. The tracker writes a new header line at
    each change of results type (LeftGazeX for raw, LeftScreenX for screen
    pixels), and restarts its timestamps at each StartTracking and again
    about 0.4 s later. merge.py handles both.
    """
    marker.mark("recalibration_start")
    # The marker is written with the next sample, so let one arrive first.
    core.wait(0.01)
    to_raw_mode()
    accuracy, _, _ = calibrate_and_validate(pres, positions)
    marker.mark("recalibration_end")
    return accuracy


def main():
    geometry.check_feedback_fit()
    # One ring rotation for the whole session; stops here if the setting
    # is invalid.
    rotation = geometry.ring_rotation()
    positions = geometry.ring_positions(rotation)
    design.check_design()

    # One stimulus set (plus practice). Phase 2 is disabled.
    sets = design.stimulus_sets()
    practice_set = sets["practice"]
    phase1_set = sets["phase1"]
    # PHASE 2 (disabled):
    # phase2_set = sets["phase2"]
    used_sets = [practice_set, phase1_set]
    print(f"Group cell {COUNTERBALANCE['groupCell']}: "
          f"context {phase1_set.context_label}, "
          f"object set {phase1_set.object_set}")
    # Builds one test order now, so an Euler tour problem shows up early.
    test_length = len(design.trial_sequence(1, phase1_set.objects))
    if any(v is not None for v in DEMO_TRIALS.values()):
        print(f"DEMO: blocks cut to {DEMO_TRIALS} (config.DEMO_TRIALS)")
    print(f"Practice rounds of {PHASES['practiceTrials']}; learning blocks of "
          f"{PHASES['learnBlockTrials']}; test blocks of {test_length}")

    pres = Presentation()
    screen_rate = pres.win.getActualFrameRate()    # None if it was unstable

    LiveTrack.Init()
    LiveTrack.SetResultsTypeRaw()     # calibration reads pupil/glint vectors
    LiveTrack.StartTracking()
    tracker_rate = LiveTrack.GetCaptureConfig()[2]
    tracked_eyes = LiveTrack.GetTracking()          # (left, right)

    session = None                    # set once recording starts
    accuracy = {}                     # stays empty if calibration is skipped
    calibration_attempts = 0
    first_validation = None           # marker fields of the first validation
    participant = {"age": "", "gender": ""}
    pid = "debug"                     # no demographics: no SONA ID, no key file
    try:
        # Inside the try, so Esc here still closes the window and tracker.
        pres.show_pages(SCREEN_TEXT["greeting"])
        if SESSION["yesDemographics"]:
            participant = ask_demographics(pres)
            # The SONA ID goes only into the key file, never into the data.
            pid = assign_pid(participant.pop("sonaID"))
        print(f"Participant ID: {pid}")

        pres.show_pages(SCREEN_TEXT["task"])

        pres.park_mouse()

        if SESSION["yesCalibration"]:
            accuracy, calibration_attempts, first_validation = \
                calibrate_and_validate(pres, positions)

        # From here gaze is in screen pixels centred at 0,0 (the units of
        # the calibration targets). The results type is set while tracking
        # is stopped, as in CRS's demos.
        LiveTrack.StopTracking()
        LiveTrack.SetResultsTypeCalibrated()
        LiveTrack.ClearDataBuffer()

        # Recording starts after calibration, so the file holds only
        # calibrated data.
        path = marker.open_session(pid)
        LiveTrack.StartTracking()
        print(f"Recording to {path}")

        # The tracker resets its clock about 0.4 s after recording starts;
        # wait so every marker comes after the reset.
        core.wait(0.5)

        columns = trialdata.session_columns(
            participant, accuracy,
            screen_rate, tracker_rate, tracked_eyes, used_sets,
            calibration_attempts, rotation, positions)
        # Needed later to judge where gaze was
        columns["nameSelectRadius_px"] = round(pres.name_radius_px, 2)
        columns["px_per_deg"] = round(geometry.px_per_deg(), 4)
        session_path, trials_path = trialdata.open_files(path, pid, columns)
        print(f"Session to {session_path}")
        print(f"Trials to {trials_path}")
        session = Session(accuracy, positions)

        marker.mark("session_start")
        # The first validation ran before recording; its result goes here.
        if first_validation is not None:
            marker.mark("validation_result", **first_validation)

        pres.show_pages(SCREEN_TEXT["practice"])
        run_practice(pres, session, practice_set)

        pres.show_pages(SCREEN_TEXT["learning"])
        run_learning(pres, session, "learning", phase1_set)
        pres.show_pages(SCREEN_TEXT["test"])
        run_test(pres, session, "test", phase1_set)

        # PHASE 2 (disabled):
        #   pres.show_pages(SCREEN_TEXT["learning2"])
        #   run_learning(pres, session, "learning2", phase2_set)
        #   pres.show_pages(SCREEN_TEXT["test"])
        #   run_test(pres, session, "test2", phase2_set)

        marker.mark("trials_end")
        pres.show_pages(SCREEN_TEXT["taskEnd"])
        posttask_q(pres)
        marker.mark("session_end")
        pres.show_debrief()
    except EndSession as e:
        # Data so far are on disk; the participant still gets the debrief.
        set_trials_running(False)
        marker.mark("session_ended_early")    # no-op before recording
        print(f"\nENDED EARLY: {e}")
        pres.show_debrief()
    finally:
        trialdata.close_file()
        marker.close_session()
        LiveTrack.StopTracking()
        LiveTrack.ClearDataBuffer()
        LiveTrack.Close()
        # Files are closed; the window stays until the researcher presses Esc.
        pres.show_end()
        pres.close()

    print(pid, participant)
    if session is not None:
        for r in session.rows:
            print(r["phase"], r["block"], r["testAttempt"],
                  r["sessionTrialN"], r["blockTrialN"],
                  r["targetObj"], r["outcome"], r.get("selection_ms"))


if __name__ == "__main__":
    main()
