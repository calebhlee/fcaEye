# AI usage: code co-written with Claude Opus 5.5.
# Research questions, experimental design and program requirements came from Caleb and Britt.

"""LiveTrack gaze calibration."""

import contextlib
import io
import sys
sys.path.insert(0, r"C:\Users\Public\Documents\CRS LiveTrack Python Bindings")
import LiveTrack

import math
import time

import numpy as np
from psychopy import visual

import geometry
from config import CALIBRATION, VALIDATION
from presentation import check_escape


def gaze_calibration(win):
    """Run one calibration pass and return the accuracy per eye.

    Needs LiveTrack.Init(), SetResultsTypeRaw() and StartTracking() first:
    the fixation check reads raw pupil/glint vectors.

    Returns e.g. {"left": {"accuracy_deg": 0.34, "n_points": 9}, ...}.
    An eye that is not tracked or timed out is left out.
    """
    targets_deg = np.array(CALIBRATION["targets_deg"])
    n_targets = targets_deg.shape[0]

    view_dist_mm = CALIBRATION["viewDist_mm"]

    px_per_deg = geometry.px_per_deg()

    target_pos_px = targets_deg * px_per_deg

    order = np.arange(n_targets)
    np.random.shuffle(order)
    target_pos_px = target_pos_px[order]

    fix_dot_in_px = CALIBRATION["fixInDot_deg"] * px_per_deg
    fix_dot_out_px = CALIBRATION["fixOutDot_deg"] * px_per_deg
    min_dur_ms = CALIBRATION["minFixDur_ms"]
    setup_delay_ms = CALIBRATION["setupDelay_ms"]
    fix_timeout_ms = CALIBRATION["fixTimeout_ms"]
    fix_threshold_px = CALIBRATION["fixThreshold_px"]

    _, _, sample_rate, _, _ = LiveTrack.GetCaptureConfig()
    fix_dur_samples = round(min_dur_ms / 1000 * sample_rate)   # rate is per s

    track_left, track_right = LiveTrack.GetTracking()

    vect_x_left = [None] * n_targets
    vect_y_left = [None] * n_targets
    glint_x_left = [None] * n_targets
    glint_y_left = [None] * n_targets
    vect_x_right = [None] * n_targets
    vect_y_right = [None] * n_targets
    glint_x_right = [None] * n_targets
    glint_y_right = [None] * n_targets

    outer = visual.Circle(win, units="pix", radius=fix_dot_out_px / 2,
                          fillColor=[-1, -1, -1], lineColor=[-1, -1, -1])
    inner = visual.Circle(win, units="pix", radius=fix_dot_in_px / 2,
                          fillColor=[1, 1, 1], lineColor=[-1, -1, -1])

    for i, (tx, ty) in enumerate(target_pos_px):
        outer.pos = [tx, ty]
        inner.pos = [tx, ty]
        outer.draw()
        inner.draw()
        win.flip()

        got_fix_left = False
        got_fix_right = False
        t0 = time.time()

        while True:
            check_escape()
            elapsed = (time.time() - t0) * 1000       # ms
            d = LiveTrack.GetBufferedEyePositions(0, fix_dur_samples, 0)

            # Only judge a full window; max()/min() fail on an empty buffer.
            if len(d) >= fix_dur_samples:
                vect_x = LiveTrack.GetFieldAsList(d, "VectX")
                vect_y = LiveTrack.GetFieldAsList(d, "VectY")
                glint_x = LiveTrack.GetFieldAsList(d, "GlintX")
                glint_y = LiveTrack.GetFieldAsList(d, "GlintY")
                tracked = LiveTrack.GetFieldAsList(d, "Tracked")
                vect_x_r = LiveTrack.GetFieldAsList(d, "VectXRight")
                vect_y_r = LiveTrack.GetFieldAsList(d, "VectYRight")
                glint_x_r = LiveTrack.GetFieldAsList(d, "GlintXRight")
                glint_y_r = LiveTrack.GetFieldAsList(d, "GlintYRight")
                tracked_r = LiveTrack.GetFieldAsList(d, "TrackedRight")

                pg_dist_left = max(max(vect_x) - min(vect_x),
                                   max(vect_y) - min(vect_y))
                pg_dist_right = max(max(vect_x_r) - min(vect_x_r),
                                    max(vect_y_r) - min(vect_y_r))

                settled = elapsed > setup_delay_ms

                if (not got_fix_left and settled
                        and pg_dist_left <= fix_threshold_px and all(tracked)):
                    vect_x_left[i] = np.median(vect_x)
                    vect_y_left[i] = np.median(vect_y)
                    glint_x_left[i] = np.median(glint_x)
                    glint_y_left[i] = np.median(glint_y)
                    got_fix_left = True
                    print(f"Target {i + 1}: left eye fixation acquired")

                if (not got_fix_right and settled
                        and pg_dist_right <= fix_threshold_px and all(tracked_r)):
                    vect_x_right[i] = np.median(vect_x_r)
                    vect_y_right[i] = np.median(vect_y_r)
                    glint_x_right[i] = np.median(glint_x_r)
                    glint_y_right[i] = np.median(glint_y_r)
                    got_fix_right = True
                    print(f"Target {i + 1}: right eye fixation acquired")

            if (got_fix_left or not track_left) and (got_fix_right or not track_right):
                win.flip()
                break

            if elapsed > fix_timeout_ms:
                if not got_fix_left and track_left:
                    print(f"Target {i + 1}: left eye timed out")
                if not got_fix_right and track_right:
                    print(f"Target {i + 1}: right eye timed out")
                win.flip()
                break

    # Drop missed targets per eye, so one eye's miss keeps the other's data.
    idx_left = [i for i in range(n_targets) if vect_x_left[i] is not None]
    idx_right = [i for i in range(n_targets) if vect_x_right[i] is not None]

    def calibrate_eye(eye_index, idx, vx, vy, gx, gy):
        """Fit one eye. eye_index is 0 for left, 1 for right."""
        if not idx:
            return None

        tgt_x = [float(target_pos_px[i][0]) for i in idx]
        tgt_y = [float(target_pos_px[i][1]) for i in idx]
        vect_x = [float(vx[i]) for i in idx]
        vect_y = [float(vy[i]) for i in idx]
        glint_x = [float(gx[i]) for i in idx]
        glint_y = [float(gy[i]) for i in idx]

        # The fit runs in the CRS library. The glint reference is the
        # median over all targets.
        cal_err = LiveTrack.CalibrateDevice(
            eye_index, len(idx), tgt_x, tgt_y, vect_x, vect_y,
            view_dist_mm, np.median(glint_x), np.median(glint_y),
        )

        # cal_err is a summed squared error in pixels; RMS is sqrt(err / n).
        accuracy_px = math.sqrt(float(cal_err) / len(idx))
        return {"accuracy_deg": accuracy_px / px_per_deg,
                "n_points": len(idx)}

    result = {}

    if track_left:
        entry = calibrate_eye(0, idx_left, vect_x_left, vect_y_left,
                              glint_x_left, glint_y_left)
        if entry is not None:
            result["left"] = entry

    if track_right:
        entry = calibrate_eye(1, idx_right, vect_x_right, vect_y_right,
                              glint_x_right, glint_y_right)
        if entry is not None:
            result["right"] = entry

    win.flip()
    return result


def report_calibration(result, attempt=1):
    """Print the accuracy for the experimenter; return True if it passes.

    Passes only if both eyes were calibrated, each eye has all targets
    (a missed target fails the calibration), and each error is below
    CALIBRATION["calibrationCriterion_deg"] (screening criterion).
    The screen shows calibration_summary (experiment.run_calibration).
    """
    threshold = CALIBRATION["calibrationCriterion_deg"]
    n_targets = len(CALIBRATION["targets_deg"])
    print(f"\n--- Calibration attempt {attempt} "
          f"(criterion: both eyes < {threshold} deg, "
          f"all {n_targets} targets) ---")

    missing = [eye for eye in ("left", "right") if eye not in result]
    for eye in missing:
        print(f"{eye}: not calibrated  [FAIL]")

    passed = not missing
    for eye, entry in result.items():
        ok = (entry["accuracy_deg"] < threshold
              and entry["n_points"] == n_targets)
        passed = passed and ok
        line = (f"{eye}: {entry['accuracy_deg']:.2f} deg "
                f"from {entry['n_points']} of {n_targets} targets  "
                f"[{'PASS' if ok else 'FAIL'}]")
        print(line)

    return passed


def calibration_summary(result):
    """Calibration result per eye as screen text, e.g.
    "Left eye: 0.16 deg, 9 of 9 dots acquired".
    """
    n_targets = len(CALIBRATION["targets_deg"])
    lines = []
    for eye in ("left", "right"):
        entry = result.get(eye)
        if entry is None:
            lines.append(f"{eye.capitalize()} eye: not calibrated")
        else:
            lines.append(f"{eye.capitalize()} eye: "
                         f"{entry['accuracy_deg']:.2f} deg, "
                         f"{entry['n_points']} of {n_targets} dots acquired")
    return "\n".join(lines)


# ---------------------------------------------------------------- validation

def _read_buffer():
    """All samples since the last read (calibrated results), print silenced."""
    with contextlib.redirect_stdout(io.StringIO()):
        return LiveTrack.GetBufferedEyePositions(1, -1, 1)


def _median_point(points):
    """Median (x, y) of a list of points, or None if the list is empty."""
    if not points:
        return None
    return (float(np.median([x for x, _ in points])),
            float(np.median([y for _, y in points])))


def gaze_validation(win, points_px):
    """Show each point once (random order); return the gaze measured there.

    Needs SetResultsTypeCalibrated() and StartTracking() first: gaze must be
    in screen pixels. Each dot stays VALIDATION["windowEnd_ms"]; gaze is
    the median of the samples from windowStart_ms to windowEnd_ms after the
    dot appeared (tracker time). A fixed window, not "wait until gaze is on
    the dot": with a bad calibration gaze never reads on the dot.

    Returns one dict per point, in the order of points_px:
        target  (x, y) px
        left, right, both   median gaze (x, y) px, or None if not tracked
        n       samples in the window with at least one eye tracked
    """
    px_per_deg = geometry.px_per_deg()
    start_us = VALIDATION["windowStart_ms"] * 1000
    end_us = VALIDATION["windowEnd_ms"] * 1000

    outer = visual.Circle(win, units="pix",
                          radius=CALIBRATION["fixOutDot_deg"] * px_per_deg / 2,
                          fillColor=[-1, -1, -1], lineColor=[-1, -1, -1])
    inner = visual.Circle(win, units="pix",
                          radius=CALIBRATION["fixInDot_deg"] * px_per_deg / 2,
                          fillColor=[1, 1, 1], lineColor=[-1, -1, -1])

    order = np.random.permutation(len(points_px))
    results = [None] * len(points_px)
    for i in order:
        x, y = points_px[i]
        outer.pos = inner.pos = [x, y]
        outer.draw()
        inner.draw()
        win.flip()
        _read_buffer()                              # samples before the dot
        onset_us = LiveTrack.GetLastResult().Timestamp

        left, right, both = [], [], []
        t0 = time.perf_counter()
        # Keep the dot up until the window has passed (+50 ms for samples
        # still on their way to the PC).
        while (time.perf_counter() - t0) * 1000 < VALIDATION["windowEnd_ms"] + 50:
            check_escape()
            for s in _read_buffer():
                if not onset_us + start_us <= s.Timestamp < onset_us + end_us:
                    continue
                eyes = []
                if s.Tracked:
                    left.append((s.GazeX, s.GazeY))
                    eyes.append((s.GazeX, s.GazeY))
                if s.TrackedRight:
                    right.append((s.GazeXRight, s.GazeYRight))
                    eyes.append((s.GazeXRight, s.GazeYRight))
                if eyes:
                    both.append((sum(e[0] for e in eyes) / len(eyes),
                                 sum(e[1] for e in eyes) / len(eyes)))
            outer.draw()
            inner.draw()
            win.flip()

        results[i] = {"target": (x, y), "left": _median_point(left),
                      "right": _median_point(right),
                      "both": _median_point(both), "n": len(both)}
    win.flip()
    return results


def report_validation(results, labels):
    """Print the validation per dot; return (passed, marker fields, screen text).

    Passes if, at every dot, the both-eye error is below
    VALIDATION["maxError_deg"] and the distance between the eyes is below
    VALIDATION["maxEyeDistance_deg"]. A dot without gaze from both eyes fails.
    """
    px_per_deg = geometry.px_per_deg()
    max_error = VALIDATION["maxError_deg"]
    max_distance = VALIDATION["maxEyeDistance_deg"]

    def deg(a, b):
        return None if a is None or b is None else math.dist(a, b) / px_per_deg

    print(f"\n--- Validation (limits: error < {max_error} deg, "
          f"eye distance < {max_distance} deg) ---")
    passed = True
    errors, distances = [], []
    for label, r in zip(labels, results):
        error = deg(r["both"], r["target"])
        distance = deg(r["left"], r["right"])
        ok = (error is not None and distance is not None
              and error < max_error and distance < max_distance)
        passed = passed and ok
        if error is not None:
            errors.append(error)
        if distance is not None:
            distances.append(distance)
        left = deg(r["left"], r["target"])
        right = deg(r["right"], r["target"])

        def show(v):
            return "  -  " if v is None else f"{v:.2f}"
        print(f"{label:>7}: error {show(error)} (L {show(left)}, "
              f"R {show(right)}), eye distance {show(distance)} deg, "
              f"{r['n']} samples  [{'PASS' if ok else 'FAIL'}]")

    worst_error = max(errors) if errors else None
    worst_distance = max(distances) if distances else None
    print("Validation PASSED." if passed else "Validation FAILED.")

    def fmt(v):
        return "none" if v is None else f"{v:.2f}"
    fields = {"maxError_deg": fmt(worst_error),
              "maxEyeDistance_deg": fmt(worst_distance),
              "passed": passed}
    n_fail = sum(1 for label, r in zip(labels, results)
                 if not (deg(r["both"], r["target"]) is not None
                         and deg(r["left"], r["right"]) is not None
                         and deg(r["both"], r["target"]) < max_error
                         and deg(r["left"], r["right"]) < max_distance))
    text = (f"Largest error: {fmt(worst_error)} deg (limit {max_error})\n"
            f"Largest distance between the eyes: {fmt(worst_distance)} deg "
            f"(limit {max_distance})\n"
            f"Dots within the limits: {len(results) - n_fail} of {len(results)}"
            f"\n\n{'PASSED' if passed else 'NOT PASSED'}")
    return passed, fields, text
