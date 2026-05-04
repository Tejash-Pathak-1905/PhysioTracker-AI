"""
cv_engine/evaluator.py  –  Dispatcher that routes to per-exercise logic.
"""
import math
import time, json
import cv2, mediapipe as mp
from .utils import check_visibility, lm_xy, calculate_angle

mp_pose    = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


class ExerciseEvaluator:
    """
    Wraps a MediaPipe Pose session.
    Call .process_frame(bgr_frame) in each streamlit-webrtc callback.
    Call .get_session_log() when the session ends.
    """

    def __init__(self, exercise_plan_row):
        self.exercise_id  = exercise_plan_row.exercise_id
        self.target_reps  = exercise_plan_row.target_reps
        self.target_sets  = exercise_plan_row.target_sets
        self.caution      = exercise_plan_row.caution or ""

        self.reps_completed   = 0
        self.sets_completed   = 0
        self.form_errors      = {}
        self._phase           = "INIT"
        self._feedback        = ""
        self._start_time      = time.time()

        self._pose = mp_pose.Pose(
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )

    # ── public ────────────────────────────────────────────────────────────
    def process_frame(self, bgr_frame):
        """Runs pose estimation + exercise logic. Returns annotated frame."""
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        results = self._pose.process(rgb)
        annotated = bgr_frame.copy()

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                annotated, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
            )
            lm = results.pose_landmarks.landmark
            self._dispatch(lm, annotated)

        self._draw_hud(annotated)
        return annotated

    def get_session_log(self) -> dict:
        return {
            "exercise_id":      self.exercise_id,
            "reps_completed":   self.reps_completed,
            "duration_seconds": int(time.time() - self._start_time),
            "form_errors":      json.dumps(self.form_errors),
        }

    def is_complete(self) -> bool:
        return self.reps_completed >= self.target_reps * self.target_sets

    # ── internals ─────────────────────────────────────────────────────────
    def _log_error(self, key: str, msg: str):
        self.form_errors[key] = self.form_errors.get(key, 0) + 1
        self._feedback = msg

    def _draw_hud(self, frame):
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 0), -1)
        cv2.putText(frame, f"Reps: {self.reps_completed}/{self.target_reps * self.target_sets}",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame, f"Phase: {self._phase}",
                    (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,200), 1)
        if self._feedback:
            cv2.putText(frame, self._feedback,
                        (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,80,255), 2)

    def _dispatch(self, lm, frame):
        fn = getattr(self, f"_eval_{self.exercise_id}", None)
        if fn:
            fn(lm, frame)

    # ── Per-exercise evaluators ───────────────────────────────────────────
    # Each method follows the state-machine spec in the PRD.

    def _eval_squat(self, lm, frame):
        if not check_visibility(lm, [23,25,27], 0.6): return
        hip   = lm_xy(lm, 23); knee = lm_xy(lm, 25); ankle = lm_xy(lm, 27)
        angle = calculate_angle(hip, knee, ankle)

        if self._phase in ("INIT","STANDING") and angle < 100:
            self._phase = "SQUATTING"
        elif self._phase == "SQUATTING" and angle > 160:
            self._phase = "STANDING"
            self.reps_completed += 1
            self._feedback = ""

        # secondary checks
        lk = lm_xy(lm, 25); rk = lm_xy(lm, 26)
        lh = lm_xy(lm, 23); rh = lm_xy(lm, 24)
        if abs(lk[0]-rk[0]) < abs(lh[0]-rh[0]):
            self._log_error("knee_cave", "Push knees outward")

    def _eval_shoulder_flexion(self, lm, frame):
        if not check_visibility(lm, [11,13,15,23], 0.6): return
        hip   = lm_xy(lm, 23); sh = lm_xy(lm, 11); el = lm_xy(lm, 13)
        angle = calculate_angle(hip, sh, el)

        if self._phase in ("INIT","RESTING") and angle > 30:
            self._phase = "RAISING"
        elif self._phase == "RAISING" and angle < 20:
            self._phase = "RESTING"
            self.reps_completed += 1
            self._feedback = ""

        wr = lm_xy(lm, 15)
        if calculate_angle(sh, el, wr) < 140:
            self._log_error("elbow_bend", "Keep your arm straight")

    def _eval_jumping_jacks(self, lm, frame):
        if not check_visibility(lm, [11,15,23,27], 0.6): return
        wr_l = lm_xy(lm, 15); wr_r = lm_xy(lm, 16)
        sh_l = lm_xy(lm, 11); sh_r = lm_xy(lm, 12)
        an_l = lm_xy(lm, 27); an_r = lm_xy(lm, 28)
        hp_l = lm_xy(lm, 23); hp_r = lm_xy(lm, 24)

        arms_up  = wr_l[1] < sh_l[1] and wr_r[1] < sh_r[1]
        legs_out = abs(an_l[0]-an_r[0]) > abs(hp_l[0]-hp_r[0]) * 1.3

        if self._phase in ("INIT","CLOSED") and arms_up and legs_out:
            self._phase = "OPEN"
        elif self._phase == "OPEN" and not (arms_up and legs_out):
            self._phase = "CLOSED"
            self.reps_completed += 1
            self._feedback = ""

        if self._phase == "OPEN" and not arms_up:
            self._log_error("arms_not_reaching", "Raise arms above shoulders")

    def _eval_knee_extension(self, lm, frame):
        if not check_visibility(lm, [23,25,27], 0.6): return
        hip   = lm_xy(lm, 23); knee = lm_xy(lm, 25); ankle = lm_xy(lm, 27)
        angle = calculate_angle(hip, knee, ankle)

        if self._phase in ("INIT","BENT") and angle > 160:
            self._phase = "FULL"
        elif self._phase == "FULL" and angle < 90:
            self._phase = "BENT"
            self.reps_completed += 1
            self._feedback = ""

        if angle > 178:
            self._log_error("hyperextension", "Don't lock your knee")

    def _eval_bicep_curl(self, lm, frame):
        if not check_visibility(lm, [11,13,15], 0.6): return
        sh = lm_xy(lm, 11); el = lm_xy(lm, 13); wr = lm_xy(lm, 15)
        angle = calculate_angle(sh, el, wr)

        if self._phase in ("INIT","EXTENDED") and angle < 50:
            self._phase = "PEAK"
        elif self._phase == "PEAK" and angle > 160:
            self._phase = "EXTENDED"
            self.reps_completed += 1
            self._feedback = ""

        hp = lm_xy(lm, 23)
        if abs(el[0] - hp[0]) > 0.05:
            self._log_error("elbow_drift", "Keep elbows tucked")

    def _eval_shoulder_abduction(self, lm, frame):
        if not check_visibility(lm, [23,11,13], 0.6): return
        hp = lm_xy(lm, 23); sh = lm_xy(lm, 11); el = lm_xy(lm, 13)
        angle = calculate_angle(hp, sh, el)

        if self._phase in ("INIT","RESTING") and angle > 85:
            self._phase = "PEAK"
        elif self._phase == "PEAK" and angle < 15:
            self._phase = "RESTING"
            self.reps_completed += 1
            self._feedback = ""

    def _eval_wall_pushup(self, lm, frame):
        if not check_visibility(lm, [11,13,15], 0.6): return
        sh = lm_xy(lm, 11); el = lm_xy(lm, 13); wr = lm_xy(lm, 15)
        angle = calculate_angle(sh, el, wr)

        if self._phase in ("INIT","EXTENDED") and angle < 90:
            self._phase = "CHEST_TO_WALL"
        elif self._phase == "CHEST_TO_WALL" and angle > 160:
            self._phase = "EXTENDED"
            self.reps_completed += 1
            self._feedback = ""

    def _eval_single_leg_stand(self, lm, frame):
        if not check_visibility(lm, [23,25,27], 0.6): return
        # Lifted knee: knee_y < hip_y  (y is inverted in image space)
        lk_y = lm[25].y; lh_y = lm[23].y
        rk_y = lm[26].y; rh_y = lm[24].y

        if self._phase in ("INIT","TWO_FEET"):
            if lk_y < lh_y or rk_y < rh_y:
                self._phase    = "ONE_FOOT_LIFTED"
                self._hold_start = time.time()
        elif self._phase == "ONE_FOOT_LIFTED":
            if not (lk_y < lh_y or rk_y < rh_y):
                hold = time.time() - self._hold_start
                if hold >= 2.0:
                    self.reps_completed += 1
                self._phase = "TWO_FEET"
                self._feedback = ""

    def _eval_high_knees(self, lm, frame):
        self._eval_knee_extension(lm, frame)   # reuse basic knee-height logic

    def _eval_cat_cow(self, lm, frame):
        if not check_visibility(lm, [7,11,23], 0.6): return
        ear = lm_xy(lm, 7); sh = lm_xy(lm, 11); hp = lm_xy(lm, 23)
        angle = calculate_angle(ear, sh, hp)

        if self._phase in ("INIT","NEUTRAL") and angle < 155:
            self._phase = "CAT"
        elif self._phase == "CAT" and angle > 185:
            self._phase = "COW"
        elif self._phase == "COW" and 155 <= angle <= 185:
            self._phase = "NEUTRAL"
            self.reps_completed += 1
            self._feedback = ""

    def _eval_lunge(self, lm, frame):
        if not check_visibility(lm, [23,25,27], 0.6): return
        hp = lm_xy(lm, 23); kn = lm_xy(lm, 25); an = lm_xy(lm, 27)
        angle = calculate_angle(hp, kn, an)

        if self._phase in ("INIT","STANDING") and angle < 95:
            self._phase = "DOWN"
        elif self._phase == "DOWN" and angle > 160:
            self._phase = "STANDING"
            self.reps_completed += 1
            self._feedback = ""

        if kn[0] > an[0] + 0.05:
            self._log_error("knee_over_toe", "Keep knee behind toes")

    def _eval_bird_dog(self, lm, frame):
        if not check_visibility(lm, [11,23,25,15,27], 0.6): return
        # Simplified: check opposite arm/leg extension via shoulder-hip-knee angle
        hp = lm_xy(lm, 23); sh = lm_xy(lm, 11); kn = lm_xy(lm, 25)
        angle = calculate_angle(sh, hp, kn)

        if self._phase in ("INIT","NEUTRAL") and angle > 170:
            self._phase = "EXTENDED"
        elif self._phase == "EXTENDED" and angle < 160:
            self._phase = "NEUTRAL"
            self.reps_completed += 1
            self._feedback = ""

    def _eval_seated_forward_bend(self, lm, frame):
        if not check_visibility(lm, [11,23,25], 0.6): return
        sh = lm_xy(lm, 11); hp = lm_xy(lm, 23); kn = lm_xy(lm, 25)
        angle = calculate_angle(sh, hp, kn)

        if self._phase in ("INIT","UPRIGHT") and angle > 140:
            self._phase = "HOLDING"
            self._hold_start = time.time()
        elif self._phase == "HOLDING" and angle < 90:
            if time.time() - self._hold_start < 1.0:
                self._log_error("bouncing", "Hold the stretch for at least 1 second")
            self._phase = "UPRIGHT"
            self.reps_completed += 1
            self._feedback = ""

    def _eval_neck_lateral_flexion(self, lm, frame):
        if not check_visibility(lm, [7,11], 0.6): return
        ear = lm_xy(lm, 7); sh = lm_xy(lm, 11)
        # Tilt: horizontal ratio of ear relative to shoulder
        dx = abs(ear[0] - sh[0]); dy = abs(ear[1] - sh[1])
        angle = math.degrees(math.atan2(dx, dy)) if dy > 0 else 0

        if self._phase in ("INIT","NEUTRAL") and angle > 20:
            self._phase = "TILTING"
        elif self._phase == "TILTING" and angle < 5:
            self._phase = "NEUTRAL"
            self.reps_completed += 1
            self._feedback = ""

        if lm[11].y < lm[11].y - 0.03:     # shoulder rise heuristic
            self._log_error("shoulder_rise", "Keep shoulder down")

    def _eval_hip_abduction(self, lm, frame):
        if not check_visibility(lm, [23,25,27], 0.6): return
        hp = lm_xy(lm, 23); kn = lm_xy(lm, 25); an = lm_xy(lm, 27)
        angle = calculate_angle(hp, kn, an)

        if self._phase in ("INIT","STANDING") and angle > 30:
            self._phase = "LIFTING"
        elif self._phase == "LIFTING" and angle < 10:
            self._phase = "STANDING"
            self.reps_completed += 1
            self._feedback = ""


