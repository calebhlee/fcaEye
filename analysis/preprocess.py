# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""Turn one session's tracker file into data for fixation/saccade detection.

Replaces merge.py and detection.py.

Step 1 (this part): tracker file -> one table of samples, labelled by trial.
    read_tracker   all screen-position blocks of the LiveTrack file
    read_markers   the event markers in the Comment column
    gaze_point     gazeX, gazeY: average of both eyes (one eye if the other
                   is lost); eyesUsed says which
    cut_trials     sessionTrialN and trialEvent for every sample in a trial
                   window (dot_on up to blank_on); other samples are dropped
    trial_time     time_ms: ms since that trial's dot_on (tracker clock)

Step 2 (to come): join the trial file, pymovements detection, save files.

Run (from the project folder):
    python analysis/preprocess.py                       # every session in data/
    python analysis/preprocess.py data/P137c4286_20261108
"""

import io
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

# Trial events (as in src/data_record/trialdata.MARKER_TIMES). A trial window
# starts at dot_on; trialEvent is the latest of these at each sample.
TRIAL_EVENTS = ["dot_on", "dot_fixated", "names_on", "object_on",
                "selection", "timeout", "feedback_on", "blank_on"]

# Markers that end a trial window early (an interrupted trial), besides
# blank_on (the normal end) and the next dot_on.
WINDOW_ENDERS = ["fixation_timeout", "pause_on", "recalibration_start",
                 "trials_end", "session_end", "session_ended_early"]


# ---------------------------------------------------------------- reading

def read_tracker(path):
    """All screen-position samples of a LiveTrack file, as one table.

    The file has a header line ("Timestamp, ...") at the start and again at
    each change of results type. Blocks whose header has LeftGazeX are raw
    camera values (during a recalibration) and are dropped; blocks with
    LeftScreenX are screen pixels (centre = 0, y up), the ones we use.

    clockSegment goes up by 1 at each new block and each time Timestamp
    goes down (the tracker restarts its clock at StartTracking).
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    header_rows = [i for i, line in enumerate(lines)
                   if line.startswith("Timestamp")]

    blocks = []
    for k, start in enumerate(header_rows):
        end = header_rows[k + 1] if k + 1 < len(header_rows) else len(lines)
        if "LeftGazeX" in lines[start] or end - start < 2:
            continue                    # raw camera block, or no samples
        block = pd.read_csv(io.StringIO("\n".join(lines[start:end])),
                            skipinitialspace=True, dtype={"Comment": str})
        block.columns = block.columns.str.strip()
        block["block"] = k
        blocks.append(block)

    samples = pd.concat(blocks, ignore_index=True)
    samples["Comment"] = samples["Comment"].fillna("").str.strip()

    new_block = samples["block"].diff().fillna(0) != 0
    clock_restart = samples["Timestamp"].diff().fillna(0) < 0
    samples["clockSegment"] = (new_block | clock_restart).cumsum()
    return samples.drop(columns="block")


def read_markers(samples):
    """Every marker as (row, event name, {field: value}).

    A marker is text such as "event=object_on trial=12" in the Comment
    column; it lands on the first sample after it was sent.
    """
    markers = []
    for row, text in samples["Comment"].items():
        if not text.startswith("event="):
            continue
        fields = dict(part.split("=", 1) for part in text.split() if "=" in part)
        event = fields.pop("event")
        markers.append((row, event, fields))
    return markers


# ---------------------------------------------------------------- gaze

def gaze_point(samples):
    """Add gazeX, gazeY (average of both eyes) and eyesUsed.

    The tracker writes (0, 0) for an eye it lost. Such an eye is left out;
    if both are lost, gazeX and gazeY are empty (NaN) and eyesUsed is
    "none". The same rule as the live gaze check in the experiment.
    """
    eyes = {}
    for side in ("Left", "Right"):
        x = samples[f"{side}ScreenX"].to_numpy(dtype=float)
        y = samples[f"{side}ScreenY"].to_numpy(dtype=float)
        lost = (x == 0) & (y == 0)
        eyes[side] = (np.where(lost, np.nan, x), np.where(lost, np.nan, y), lost)

    (lx, ly, left_lost), (rx, ry, right_lost) = eyes["Left"], eyes["Right"]
    # nanmean: the mean of the values that are not NaN (one eye if the other
    # is lost). With both NaN it warns and gives NaN, which is what we want.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        samples["gazeX"] = np.nanmean([lx, rx], axis=0)
        samples["gazeY"] = np.nanmean([ly, ry], axis=0)

    samples["eyesUsed"] = np.select(
        [~left_lost & ~right_lost, ~left_lost, ~right_lost],
        ["both", "left", "right"], default="none")
    return samples


# ---------------------------------------------------------------- trials

def cut_trials(samples, markers):
    """Label each sample with sessionTrialN and trialEvent; drop the rest.

    A trial window starts at its dot_on marker and ends just before
    blank_on (the normal end), or at a WINDOW_ENDERS marker or the next
    dot_on (an interrupted trial). trialEvent is the latest TRIAL_EVENTS
    marker at each sample, e.g. "object_on" from the object onset on.
    """
    n = len(samples)
    trial_n = np.full(n, -1)                    # -1 = not in a trial window
    trial_event = np.full(n, "", dtype=object)

    open_trial = None                           # (trial number, start row)
    events_in_window = []                       # (row, event) in that window

    def close(end_row):
        trial, start = open_trial
        trial_n[start:end_row] = trial
        # trialEvent: fill forward from each event marker inside the window
        for row, event in events_in_window:
            trial_event[row:end_row] = event

    for row, event, fields in markers:
        ends_window = (event == "blank_on" or event in WINDOW_ENDERS
                       or event == "dot_on")
        if open_trial is not None and ends_window:
            close(row)
            open_trial, events_in_window = None, []
        if event == "dot_on":
            open_trial = (int(fields["trial"]), row)
        if open_trial is not None and event in TRIAL_EVENTS:
            events_in_window.append((row, event))
    if open_trial is not None:                  # file ended inside a trial
        close(n)

    samples["sessionTrialN"] = trial_n
    samples["trialEvent"] = trial_event
    return samples[samples["sessionTrialN"] >= 0].reset_index(drop=True)


def trial_time(samples):
    """Add time_ms: ms since that trial's dot_on, from the tracker clock.

    Each trial lies within one clock segment, so clock restarts do not
    affect it (checked: an error is raised if a trial spans two segments).
    """
    spans = samples.groupby("sessionTrialN")["clockSegment"].nunique()
    if (spans > 1).any():
        raise ValueError("trials spanning two clock segments: "
                         f"{list(spans[spans > 1].index)}")
    start_us = samples.groupby("sessionTrialN")["Timestamp"].transform("first")
    samples["time_ms"] = (samples["Timestamp"] - start_us) / 1000
    return samples


def load_samples(session_dir):
    """Step 1 for one session folder: the labelled sample table."""
    session_dir = Path(session_dir)
    samples = read_tracker(session_dir / f"{session_dir.name}.csv")
    markers = read_markers(samples)
    samples = gaze_point(samples)
    samples = cut_trials(samples, markers)
    samples = trial_time(samples)
    columns = ["sessionTrialN", "time_ms", "trialEvent", "gazeX", "gazeY",
               "eyesUsed", "Timestamp", "clockSegment"]
    return samples[columns]


# ---------------------------------------------------------------- checks

def check_step1(session_dir, samples):
    """Print the step-1 checks for one session."""
    session_dir = Path(session_dir)
    trials = pd.read_csv(session_dir / f"{session_dir.name}_trials.csv")
    in_file = set(trials["sessionTrialN"])
    in_samples = set(samples["sessionTrialN"])
    first = samples.groupby("sessionTrialN").first()

    print(f"\n== {session_dir.name}")
    print(f"trials in trial file: {len(in_file)}; with a sample window: "
          f"{len(in_file & in_samples)}; missing: {sorted(in_file - in_samples)}")
    print(f"every window starts at dot_on: "
          f"{(first['trialEvent'] == 'dot_on').all()}")
    print(f"samples in trial windows: {len(samples)} "
          f"({len(samples) * 2 / 1000 / 60:.1f} min at 500 Hz)")
    print("eyes used (% of samples):",
          (samples["eyesUsed"].value_counts(normalize=True) * 100)
          .round(2).to_dict())


def session_dirs(args):
    if args:
        return [Path(a) for a in args]
    return sorted(p for p in DATA_DIR.iterdir() if p.is_dir())


if __name__ == "__main__":
    for folder in session_dirs(sys.argv[1:]):
        check_step1(folder, load_samples(folder))
