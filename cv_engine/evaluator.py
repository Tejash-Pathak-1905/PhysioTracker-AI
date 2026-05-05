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
        self.side         = exercise_plan_row.side or "both"
        self.caution      = exercise_plan_row.caution or ""

        # Mapping for side-specific landmarks
        # Left: 11, 13, 15, 23, 25, 27 | Right: 12, 14, 16, 24, 26, 28
        self.lm_map = {
            "left":  {"sh": 11, "el": 13, "wr": 15, "hp": 23, "kn": 25, "an": 27},
            "right": {"sh": 12, "el": 14, "wr": 16, "hp": 24, "kn": 26, "an": 28},
            "both":  {"sh": 11, "el": 13, "wr": 15, "hp": 23, "kn": 25, "an": 27} # default to left if both (e.g. for squats)
        }
        self.idxs = self.lm_map.get(self.side.lower(), self.lm_map["both"])

        self.reps_completed   = 0
        self.sets_completed   = 0
        self.form_errors      = {}
        self._phase           = "INIT"
        self._feedback        = ""
        self._feedback_time   = 0
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
            self._dispatch(results.pose_landmarks.landmark, annotated)
            
            # Dynamic Skeleton Color based on Posture
            if self._feedback:
                # Red for incorrect posture
                landmark_spec = mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
                connection_spec = mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
            else:
                # Green for ideal posture
                landmark_spec = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)
                connection_spec = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2)

            mp_drawing.draw_landmarks(
                annotated, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=landmark_spec,
                connection_drawing_spec=connection_spec
            )

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
        self._feedback_time = time.time()

    def _check_torso_alignment(self, lm, sh_idx, hp_idx, kn_idx):
        """Checks if the back is relatively straight using Shoulder-Hip-Knee angle."""
        if not check_visibility(lm, [sh_idx, hp_idx, kn_idx], 0.7): return True
        sh = lm_xy(lm, sh_idx); hp = lm_xy(lm, hp_idx); kn = lm_xy(lm, kn_idx)
        angle = calculate_angle(sh, hp, kn)
        # Stricter angle for standing straight
        return angle > 155 

    def _check_shoulder_level(self, lm):
        """Checks if shoulders are parallel to the ground."""
        if not check_visibility(lm, [11, 12], 0.7): return True
        l_sh = lm_xy(lm, 11); r_sh = lm_xy(lm, 12)
        dy = abs(l_sh[1] - r_sh[1])
        return dy < 0.035 # stricter threshold for levelness

    def _check_facing_camera(self, lm):
        """Checks if the user is facing the camera, not turned sideways excessively."""
        if not check_visibility(lm, [11, 12], 0.7): return True
        l_sh_z = lm[11].z; r_sh_z = lm[12].z
        # Difference in z-coordinates of shoulders indicates turning
        return abs(l_sh_z - r_sh_z) < 0.15

    def _is_standing_straight(self, lm, allow_knee_bend=False):
        """Strict check to ensure the user is standing upright and stable."""
        idx = self.idxs
        # Allow ankles to be less visible (0.4) since they are often cut off, but hips/knees must be visible
        if not check_visibility(lm, [idx["sh"], idx["hp"], idx["kn"]], 0.65):
            return False, "Upper body and knees must be visible"
            
        sh = lm_xy(lm, idx["sh"]); hp = lm_xy(lm, idx["hp"]); kn = lm_xy(lm, idx["kn"])
        
        if not allow_knee_bend:
            if not (sh[1] < hp[1] < kn[1]):
                return False, "Must be standing upright"
        else:
            if not (sh[1] < hp[1]):
                return False, "Must remain upright"
            
        # Torso must be straight
        if calculate_angle(sh, hp, kn) < 160:
            return False, "Stand up straight, torso is bent"
            
        # Legs must be straight
        if not allow_knee_bend and check_visibility(lm, [idx["an"]], 0.5):
            an = lm_xy(lm, idx["an"])
            if calculate_angle(hp, kn, an) < 155:
                return False, "Keep your legs straight"
            
        # Check stability (hips moving horizontally too much relative to shoulders)
        if abs(sh[0] - hp[0]) > 0.15:
            return False, "Stop moving around, stand still"
            
        return True, ""

    def _is_seated(self, lm):
        """Strict check for seated exercises."""
        idx = self.idxs
        if not check_visibility(lm, [idx["sh"], idx["hp"], idx["kn"]], 0.65):
            return False, "Upper body and knees must be visible"
            
        sh = lm_xy(lm, idx["sh"]); hp = lm_xy(lm, idx["hp"]); kn = lm_xy(lm, idx["kn"])
        
        if not (sh[1] < hp[1]):
            return False, "Must be seated upright"
            
        angle = calculate_angle(sh, hp, kn)
        if angle > 130:
             return False, "You must be seated, not standing"
             
        # Torso upright check
        if abs(sh[0] - hp[0]) > 0.2:
            return False, "Sit up straight"
            
        return True, ""

    def _draw_hud(self, frame):
        h, w = frame.shape[:2]
        
        # Top HUD (Progress)
        cv2.rectangle(frame, (0, 0), (w, 60), (20, 20, 20), -1)
        cv2.putText(frame, f"Reps: {self.reps_completed}/{self.target_reps * self.target_sets}",
                    (15, 25), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), 2)
        cv2.putText(frame, f"Phase: {self._phase} | Side: {self.side.title()}",
                    (15, 50), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0,255,200), 1)
        
        # Interactive Bottom Banner (Live Posture Feedback)
        # Clear feedback if it's older than 1.5 seconds
        if self._feedback and (time.time() - self._feedback_time > 1.5):
            self._feedback = ""

        if self._feedback:
            # Red Banner for Error Correction
            cv2.rectangle(frame, (0, h - 50), (w, h), (0, 0, 200), -1)
            cv2.putText(frame, f"⚠️ ADJUST: {self._feedback.upper()}",
                        (15, h - 18), cv2.FONT_HERSHEY_DUPLEX, 0.65, (255,255,255), 2)
        else:
            # Green Banner for Ideal Posture
            cv2.rectangle(frame, (0, h - 50), (w, h), (0, 180, 0), -1)
            cv2.putText(frame, "✅ PERFECT POSTURE - KEEP GOING!",
                        (15, h - 18), cv2.FONT_HERSHEY_DUPLEX, 0.65, (255,255,255), 2)

    def _dispatch(self, lm, frame):
        standing_straight_req = ["bicep_curl", "shoulder_flexion", "shoulder_abduction", "hip_abduction"]
        standing_bend_req = ["squat", "lunge", "jumping_jacks", "single_leg_stand", "high_knees"]
        seated_req = ["knee_extension", "seated_forward_bend", "neck_lateral_flexion"]
        
        # Enforce facing camera for most exercises
        if self.exercise_id in standing_straight_req + seated_req + ["jumping_jacks", "squat"]:
            if not self._check_facing_camera(lm):
                self._log_error("not_facing", "Please face the camera directly")
                return

        # Enforce strict base postures
        if self.exercise_id in standing_straight_req:
            ok, msg = self._is_standing_straight(lm, allow_knee_bend=False)
            if not ok:
                self._log_error("bad_base_posture", msg)
                return
        elif self.exercise_id in standing_bend_req:
            ok, msg = self._is_standing_straight(lm, allow_knee_bend=True)
            if not ok:
                self._log_error("bad_base_posture", msg)
                return
        elif self.exercise_id in seated_req:
            ok, msg = self._is_seated(lm)
            if not ok:
                self._log_error("bad_base_posture", msg)
                return

        fn = getattr(self, f"_eval_{self.exercise_id}", None)
        if fn:
            fn(lm, frame)

    # ── Per-exercise evaluators ───────────────────────────────────────────
    # Each method follows the state-machine spec in the PRD.

    def _eval_squat(self, lm, frame):
        # Bilateral check: uses hip width, so we need both
        if not check_visibility(lm, [23,24,25,26,27,28, 11, 12], 0.6): return
        
        # Track the side specified (or left by default)
        idx = self.idxs
        hip = lm_xy(lm, idx["hp"]); knee = lm_xy(lm, idx["kn"]); ankle = lm_xy(lm, idx["an"])
        angle = calculate_angle(hip, knee, ankle)

        if self._phase in ("INIT","STANDING") and angle < 100:
            self._phase = "SQUATTING"
        elif self._phase == "SQUATTING" and angle > 160:
            self._phase = "STANDING"
            self.reps_completed += 1
            self._feedback = ""

        # Posture & Biomechanic Checks for Squat
        lk = lm_xy(lm, 25); rk = lm_xy(lm, 26)
        lh = lm_xy(lm, 23); rh = lm_xy(lm, 24)
        la = lm_xy(lm, 27); ra = lm_xy(lm, 28)
        
        # 1. Knee Cave (Valgus)
        if abs(lk[0]-rk[0]) < abs(lh[0]-rh[0]) * 0.9: # Knees narrower than hips (stricter)
            self._log_error("knee_cave", "Push knees outward")
            
        # 2. Torso leaning too far forward (chest falling)
        sh = lm_xy(lm, idx["sh"])
        torso_angle = calculate_angle(sh, hip, knee)
        if self._phase == "SQUATTING" and torso_angle < 80: # Stricter
            self._log_error("torso_lean", "Keep your chest up")
            
        # 3. Heels lifting (ankles moving significantly up relative to start)
        # Simplified: check if ankle y is changing drastically (difficult without depth, so we use knee over toe)
        if knee[0] > ankle[0] + 0.1: # Stricter
            self._log_error("knee_over_toe", "Shift weight to your heels")

    def _eval_shoulder_flexion(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["hp"], idx["sh"], idx["el"], idx["wr"], idx["kn"]], 0.6): return
        hip   = lm_xy(lm, idx["hp"]); sh = lm_xy(lm, idx["sh"]); el = lm_xy(lm, idx["el"])
        angle = calculate_angle(hip, sh, el)

        if self._phase in ("INIT","RESTING") and angle > 30:
            self._phase = "RAISING"
        elif self._phase == "RAISING" and angle < 20:
            self._phase = "RESTING"
            self.reps_completed += 1
            self._feedback = ""

        wr = lm_xy(lm, idx["wr"])
        if calculate_angle(sh, el, wr) < 155:
            self._log_error("elbow_bend", "Keep your arm straight")
            
        # Posture check: Torso leaning back to cheat the weight up
        if calculate_angle(sh, hip, lm_xy(lm, idx["kn"])) < 165:
            self._log_error("torso_lean", "Keep your back straight, don't lean back")

    def _eval_jumping_jacks(self, lm, frame):
        if not check_visibility(lm, [11,15,23,27], 0.6): return
        wr_l = lm_xy(lm, 15); wr_r = lm_xy(lm, 16)
        sh_l = lm_xy(lm, 11); sh_r = lm_xy(lm, 12)
        an_l = lm_xy(lm, 27); an_r = lm_xy(lm, 28)
        hp_l = lm_xy(lm, 23); hp_r = lm_xy(lm, 24)

        arms_up  = wr_l[1] < sh_l[1] - 0.15 and wr_r[1] < sh_r[1] - 0.15 # Stricter
        legs_out = abs(an_l[0]-an_r[0]) > abs(hp_l[0]-hp_r[0]) * 1.5 # Stricter

        if self._phase in ("INIT","CLOSED") and arms_up and legs_out:
            self._phase = "OPEN"
        elif self._phase == "OPEN" and not (arms_up and legs_out):
            self._phase = "CLOSED"
            self.reps_completed += 1
            self._feedback = ""

        if self._phase == "OPEN" and not arms_up:
            self._log_error("arms_not_reaching", "Raise arms above shoulders")

    def _eval_knee_extension(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["hp"], idx["kn"], idx["an"], idx["sh"]], 0.6): return
        hip   = lm_xy(lm, idx["hp"]); knee = lm_xy(lm, idx["kn"]); ankle = lm_xy(lm, idx["an"])
        angle = calculate_angle(hip, knee, ankle)

        if self._phase in ("INIT","BENT") and angle > 160:
            self._phase = "FULL"
        elif self._phase == "FULL" and angle < 90:
            self._phase = "BENT"
            self.reps_completed += 1
            self._feedback = ""

        if angle > 178:
            self._log_error("hyperextension", "Don't lock your knee")
            
        # Check if thigh is raising (cheating by using hip flexors instead of quads)
        sh = lm_xy(lm, idx["sh"])
        hip_angle = calculate_angle(sh, hip, knee)
        if self._phase == "FULL" and hip_angle < 80: # Stricter. Seated is ~90, <80 means thigh lifted.
             self._log_error("thigh_lift", "Keep your thigh still on the chair/bed")

    def _eval_bicep_curl(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["sh"], idx["el"], idx["wr"], idx["hp"], idx["kn"]], 0.6): return
        sh = lm_xy(lm, idx["sh"]); el = lm_xy(lm, idx["el"]); wr = lm_xy(lm, idx["wr"])
        angle = calculate_angle(sh, el, wr)

        if self._phase in ("INIT","EXTENDED") and angle < 50:
            self._phase = "PEAK"
        elif self._phase == "PEAK" and angle > 160:
            self._phase = "EXTENDED"
            self.reps_completed += 1
            self._feedback = ""

        # Posture & cheating checks
        hp = lm_xy(lm, idx["hp"])
        
        # 1. Elbow drift (cheating by using front deltoids)
        # Check if elbow moves significantly forward compared to shoulder/hip
        if el[0] < sh[0] - 0.05 or el[0] > sh[0] + 0.05: # Elbow drifted too much
            self._log_error("elbow_drift", "Keep your elbows tucked to your sides")
            
        # 2. Torso swinging (cheating by using momentum)
        if calculate_angle(sh, hp, lm_xy(lm, idx["kn"])) < 165:
            self._log_error("torso_swing", "Keep your back straight, do not swing")

    def _eval_shoulder_abduction(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["hp"], idx["sh"], idx["el"], idx["kn"]], 0.6): return
        hp = lm_xy(lm, idx["hp"]); sh = lm_xy(lm, idx["sh"]); el = lm_xy(lm, idx["el"])
        angle = calculate_angle(hp, sh, el)

        if self._phase in ("INIT","RESTING") and angle > 85:
            self._phase = "PEAK"
        elif self._phase == "PEAK" and angle < 15:
            self._phase = "RESTING"
            self.reps_completed += 1
            self._feedback = ""
            
        # Posture check: Torso lateral leaning (cheating by leaning away)
        # We can check shoulder level
        if not self._check_shoulder_level(lm):
            self._log_error("torso_lean", "Keep shoulders level, do not lean")

    def _eval_wall_pushup(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["sh"], idx["el"], idx["wr"], idx["hp"], idx["an"]], 0.6): return
        sh = lm_xy(lm, idx["sh"]); el = lm_xy(lm, idx["el"]); wr = lm_xy(lm, idx["wr"])
        angle = calculate_angle(sh, el, wr)

        if self._phase in ("INIT","EXTENDED") and angle < 90:
            self._phase = "CHEST_TO_WALL"
        elif self._phase == "CHEST_TO_WALL" and angle > 160:
            self._phase = "EXTENDED"
            self.reps_completed += 1
            self._feedback = ""
            
        # Posture check: Body must be in a straight line
        hp = lm_xy(lm, idx["hp"]); an = lm_xy(lm, idx["an"])
        body_angle = calculate_angle(sh, hp, an)
        if body_angle < 170: # Stricter
            self._log_error("hips_sagging", "Keep your body in a straight line from head to heels")

    def _eval_single_leg_stand(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["hp"], idx["kn"], idx["an"], idx["sh"]], 0.6): return
        # Lifted knee: knee_y < hip_y
        k_y = lm[idx["kn"]].y; h_y = lm[idx["hp"]].y

        if self._phase in ("INIT","TWO_FEET"):
            if k_y < h_y:
                self._phase    = "ONE_FOOT_LIFTED"
                self._hold_start = time.time()
        elif self._phase == "ONE_FOOT_LIFTED":
            if not (k_y < h_y):
                hold = time.time() - self._hold_start
                if hold >= 2.0:
                    self.reps_completed += 1
                self._phase = "TWO_FEET"
                self._feedback = ""
                
        # Posture check: Leaning to balance
        if not self._check_shoulder_level(lm):
            self._log_error("torso_lean", "Keep shoulders level, don't lean to balance")

    def _eval_high_knees(self, lm, frame):
        self._eval_knee_extension(lm, frame)   # reuse basic knee-height logic

    def _eval_cat_cow(self, lm, frame):
        if not check_visibility(lm, [7,11,23, 15, 27], 0.6): return
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
            
        # Posture check: Alignment of arms and legs
        wr = lm_xy(lm, 15); an = lm_xy(lm, 27)
        if abs(wr[0] - sh[0]) > 0.1: # Stricter
            self._log_error("hands_too_far", "Keep your hands directly under your shoulders")
        if abs(an[0] - hp[0]) > 0.1: # Stricter
            self._log_error("knees_too_far", "Keep your knees directly under your hips")

    def _eval_lunge(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["hp"], idx["kn"], idx["an"], idx["sh"]], 0.6): return
        hp = lm_xy(lm, idx["hp"]); kn = lm_xy(lm, idx["kn"]); an = lm_xy(lm, idx["an"])
        angle = calculate_angle(hp, kn, an)

        if self._phase in ("INIT","STANDING") and angle < 95:
            self._phase = "DOWN"
        elif self._phase == "DOWN" and angle > 160:
            self._phase = "STANDING"
            self.reps_completed += 1
            self._feedback = ""

        if kn[0] > an[0] + 0.05: # Stricter
            self._log_error("knee_over_toe", "Keep knee behind toes")
            
        # Posture check: Torso leaning forward
        if calculate_angle(lm_xy(lm, idx["sh"]), hp, kn) < 160:
            self._log_error("torso_lean", "Keep your upper body completely straight")

    def _eval_bird_dog(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["sh"], idx["hp"], idx["kn"]], 0.6): return
        hp = lm_xy(lm, idx["hp"]); sh = lm_xy(lm, idx["sh"]); kn = lm_xy(lm, idx["kn"])
        angle = calculate_angle(sh, hp, kn)

        if self._phase in ("INIT","NEUTRAL") and angle > 170:
            self._phase = "EXTENDED"
        elif self._phase == "EXTENDED" and angle < 160:
            self._phase = "NEUTRAL"
            self.reps_completed += 1
            self._feedback = ""
            
        # Posture check: Spinal arching
        # Check the angle of the back (shoulder-hip) relative to horizontal.
        if abs(sh[1] - hp[1]) > 0.1: # Stricter. Hips and shoulders should be roughly horizontal
            self._log_error("spine_not_neutral", "Keep your back flat like a table")

    def _eval_seated_forward_bend(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["sh"], idx["hp"], idx["kn"], idx["an"]], 0.6): return
        sh = lm_xy(lm, idx["sh"]); hp = lm_xy(lm, idx["hp"]); kn = lm_xy(lm, idx["kn"])
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
            
        # Posture check: Knees bending to cheat the stretch
        an = lm_xy(lm, idx["an"])
        leg_angle = calculate_angle(hp, kn, an)
        if self._phase == "HOLDING" and leg_angle < 175: # Stricter
            self._log_error("knees_bending", "Keep your legs completely straight")

    def _eval_neck_lateral_flexion(self, lm, frame):
        idx = self.idxs
        if not check_visibility(lm, [idx["sh"]], 0.6): return # ear (7/8) visibility is low usually
        ear = lm_xy(lm, 7 if self.side == "left" else 8); sh = lm_xy(lm, idx["sh"])
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
        idx = self.idxs
        if not check_visibility(lm, [idx["hp"], idx["kn"], idx["an"], idx["sh"]], 0.6): return
        hp = lm_xy(lm, idx["hp"]); kn = lm_xy(lm, idx["kn"]); an = lm_xy(lm, idx["an"])
        angle = calculate_angle(hp, kn, an)

        if self._phase in ("INIT","STANDING") and angle > 30:
            self._phase = "LIFTING"
        elif self._phase == "LIFTING" and angle < 10:
            self._phase = "STANDING"
            self.reps_completed += 1
            self._feedback = ""

        # Posture Check: Torso leaning to cheat the abduction
        if not self._check_torso_alignment(lm, idx["sh"], idx["hp"], idx["kn"]):
            self._log_error("torso_lean", "Keep your body straight, don't lean your torso away")


