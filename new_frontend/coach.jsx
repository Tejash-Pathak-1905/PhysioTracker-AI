/* global React */
const { useState, useEffect, useRef, useMemo } = React;

// ─── EXERCISE LIBRARY (subset, mirrored from codebase exercises.json) ───
const EXERCISES = {
  shoulder_flexion: {
    name: "Shoulder Flexion",
    sub: "Front Raise",
    target_reps: 10, sets: 3,
    cues: [
      "Stand tall, arm relaxed at your side",
      "Breathe in. Begin lifting your arm forward",
      "Rise to shoulder height — pause for one breath",
      "Lower with control, exhaling all the way down",
    ],
    watch_for: ["elbow_bend", "torso_lean"],
    encouragement: [
      "Beautiful — that's the rhythm we're looking for.",
      "Keep that elbow soft, like holding a glass of water.",
      "You're moving with intention. That's what matters.",
    ],
    color: "#7BA68C",
  },
  squat: {
    name: "Bodyweight Squat",
    sub: "Lower body foundation",
    target_reps: 10, sets: 3,
    cues: [
      "Feet shoulder-width, toes slightly out",
      "Sit back as if reaching for a chair behind you",
      "Lower until thighs are parallel — or as deep as feels safe",
      "Drive through your heels to stand tall",
    ],
    watch_for: ["knee_cave", "torso_lean"],
    encouragement: [
      "Lovely depth. Your knees are tracking beautifully.",
      "Chest proud — imagine a string lifting your sternum.",
      "That's the one. Find that groove and stay there.",
    ],
    color: "#7BA68C",
  },
  bicep_curl: {
    name: "Bicep Curl",
    sub: "Elbow flexor strengthening",
    target_reps: 12, sets: 3,
    cues: [
      "Elbows tucked close, like they're glued to your ribs",
      "Curl up — squeeze at the top",
      "Lower slowly. The way down is where strength is built",
    ],
    watch_for: ["elbow_drift", "torso_swing"],
    encouragement: [
      "No swing, all control. Exactly right.",
      "Feel the contraction — that's the muscle waking up.",
    ],
    color: "#7BA68C",
  },
};

const FORM_CUES = {
  knee_cave: { soft: "Push your knees gently outward", icon: "⤳" },
  torso_lean: { soft: "Stay tall through your chest", icon: "↑" },
  elbow_bend: { soft: "Let your arm be long and soft", icon: "—" },
  elbow_drift: { soft: "Tuck your elbow back to your side", icon: "←" },
  torso_swing: { soft: "Anchor your core, no momentum", icon: "◉" },
};

// ─── SHARED PRIMITIVES ───
const Skeleton = ({ status = "good", phase = 0 }) => {
  // Simple stylized human silhouette using SVG; phase 0..1 controls arm/limb
  const stroke = status === "good" ? "#7BA68C" : "#C97C5D";
  const a = phase; // 0 = down, 1 = up
  const armX = 100, armY = 110;
  const handX = armX + Math.sin(a * Math.PI * 0.55) * 70;
  const handY = armY - Math.cos(a * Math.PI * 0.55) * 70 + 30;
  return (
    <svg viewBox="0 0 200 280" style={{ width: "100%", height: "100%" }}>
      {/* dotted reference */}
      <g stroke="#E8E5DD" strokeWidth="1" strokeDasharray="2 4" fill="none">
        <line x1="100" y1="20" x2="100" y2="270" />
        <line x1="20" y1="180" x2="180" y2="180" />
      </g>
      <circle cx="100" cy="55" r="18" fill="none" stroke={stroke} strokeWidth="2.5" />
      <line x1="100" y1="73" x2="100" y2="180" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      {/* shoulders */}
      <line x1="78" y1="95" x2="122" y2="95" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      {/* moving arm */}
      <line x1={armX} y1={armY - 15} x2={handX} y2={handY} stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      <circle cx={handX} cy={handY} r="4" fill={stroke} />
      {/* resting arm */}
      <line x1="78" y1="95" x2="68" y2="165" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" opacity="0.5" />
      {/* hips + legs */}
      <line x1="82" y1="180" x2="118" y2="180" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      <line x1="88" y1="180" x2="82" y2="260" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      <line x1="112" y1="180" x2="118" y2="260" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      {/* joint dots */}
      {[[100, 73], [78, 95], [122, 95], [armX, armY - 15], [82, 180], [118, 180], [88, 220], [112, 220]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3" fill={stroke} />
      ))}
    </svg>
  );
};

const RingProgress = ({ value, total, size = 120, label, sub }) => {
  const r = size / 2 - 8;
  const c = 2 * Math.PI * r;
  const pct = Math.min(1, value / total);
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EFEDE6" strokeWidth="3" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#7BA68C" strokeWidth="3"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 0.5s ease" }} />
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center"
      }}>
        <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 34, lineHeight: 1, color: "#1A1A18" }}>{label}</div>
        {sub && <div style={{ fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", color: "#8A8678", marginTop: 4 }}>{sub}</div>}
      </div>
    </div>
  );
};

// ─── LANDING / WELCOME ───
const Landing = ({ onStart, userName }) => (
  <div style={{ maxWidth: 720, margin: "0 auto", padding: "80px 32px", textAlign: "center" }}>
    <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#8A8678", marginBottom: 24 }}>
      PhysioTracker · AI-guided recovery
    </div>
    <h1 style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400, fontSize: 64, lineHeight: 1.05, letterSpacing: "-0.02em", margin: "0 0 24px", color: "#1A1A18" }}>
      Recovery that meets you<br />where you are today.
    </h1>
    <p style={{ fontSize: 17, lineHeight: 1.6, color: "#5A574E", maxWidth: 520, margin: "0 auto 48px" }}>
      A patient companion that watches your form, counts every rep, and adapts gently — so you can focus on healing, not on the screen.
    </p>
    <button onClick={onStart} className="primary-btn">
      {userName ? `Continue, ${userName}` : "Begin your intake"}
      <span style={{ marginLeft: 10 }}>→</span>
    </button>
    <div style={{ marginTop: 96, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 32, textAlign: "left" }}>
      {[
        { n: "01", t: "Tell us how you feel", d: "A short conversation about your injury, your pain, your goals." },
        { n: "02", t: "Move with a coach", d: "Your camera becomes a quiet partner — counting, correcting, encouraging." },
        { n: "03", t: "See your story", d: "Not charts of failure. A timeline of small, returning strength." },
      ].map((s) => (
        <div key={s.n} style={{ borderTop: "1px solid #E8E5DD", paddingTop: 16 }}>
          <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 22, color: "#7BA68C", marginBottom: 8 }}>{s.n}</div>
          <div style={{ fontSize: 15, fontWeight: 500, color: "#1A1A18", marginBottom: 6 }}>{s.t}</div>
          <div style={{ fontSize: 13, lineHeight: 1.55, color: "#7A7668" }}>{s.d}</div>
        </div>
      ))}
    </div>
  </div>
);

// ─── INTAKE (conversational, multi-step) ───
const Intake = ({ onComplete }) => {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [complaint, setComplaint] = useState("");
  const [pain, setPain] = useState(4);
  const [side, setSide] = useState("");
  const [generating, setGenerating] = useState(false);

  const canNext = [name.trim(), complaint.trim().length > 8, true, true][step];

  const finish = async () => {
    setGenerating(true);
    setTimeout(() => {
      onComplete({ name, complaint, pain, side });
    }, 2400);
  };

  if (generating) {
    return (
      <div style={{ minHeight: "70vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 48 }}>
        <div className="thinking-dot" />
        <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 32, color: "#1A1A18", marginTop: 32, textAlign: "center", maxWidth: 480 }}>
          Reading what you shared with care…
        </div>
        <div style={{ fontSize: 14, color: "#8A8678", marginTop: 16, textAlign: "center", maxWidth: 420, lineHeight: 1.6 }}>
          Pairing your complaint with the safest exercises in our library. This usually takes a moment.
        </div>
        <div style={{ marginTop: 48, display: "flex", flexDirection: "column", gap: 10, alignItems: "flex-start" }}>
          {["Reviewing your pain pattern", "Checking contraindications", "Sequencing a gentle starting plan"].map((t, i) => (
            <div key={i} className="check-line" style={{ animationDelay: `${i * 0.6}s` }}>
              <span className="check">✓</span>{t}
            </div>
          ))}
        </div>
      </div>
    );
  }

  const steps = [
    {
      q: "What should we call you?",
      hint: "Just a first name is fine.",
      body: (
        <input className="text-input" placeholder="Your name" value={name}
          onChange={e => setName(e.target.value)} autoFocus />
      ),
    },
    {
      q: "Tell us what's going on.",
      hint: "In your own words. The more specific, the better we can help.",
      body: (
        <textarea className="text-input" rows={5} value={complaint} onChange={e => setComplaint(e.target.value)}
          placeholder="e.g. My right shoulder has been sore since I started a new job at a desk three weeks ago. It hurts most when I reach overhead." />
      ),
    },
    {
      q: "How's the pain right now?",
      hint: "On most days, in the last week. Be honest — there's no wrong answer.",
      body: (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 24, marginTop: 32 }}>
            <span style={{ fontSize: 12, color: "#8A8678", letterSpacing: "0.12em", textTransform: "uppercase" }}>Barely there</span>
            <input type="range" min="1" max="10" value={pain} onChange={e => setPain(+e.target.value)}
              className="pain-slider" style={{ flex: 1 }} />
            <span style={{ fontSize: 12, color: "#8A8678", letterSpacing: "0.12em", textTransform: "uppercase" }}>Significant</span>
          </div>
          <div style={{ textAlign: "center", marginTop: 32 }}>
            <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 96, lineHeight: 1, color: "#1A1A18" }}>{pain}</div>
            <div style={{ fontSize: 13, color: "#7A7668", marginTop: 8 }}>
              {pain <= 3 ? "Manageable. We'll keep things moving." :
                pain <= 6 ? "Noticeable. We'll move slowly and often." :
                  "Considerable. We'll prioritize comfort and gentle range."}
            </div>
          </div>
        </div>
      ),
    },
    {
      q: "Which side, if it matters?",
      hint: "Skip if it's both, or central.",
      body: (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 24 }}>
          {[["left", "Left side"], ["right", "Right side"], ["both", "Both / central"]].map(([k, l]) => (
            <button key={k} onClick={() => setSide(k)} className={"choice-btn " + (side === k ? "active" : "")}>
              {l}
            </button>
          ))}
        </div>
      ),
    },
  ];

  const cur = steps[step];
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "64px 32px", minHeight: "70vh" }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 56 }}>
        {steps.map((_, i) => (
          <div key={i} style={{ flex: 1, height: 2, background: i <= step ? "#7BA68C" : "#EFEDE6", transition: "background 0.4s" }} />
        ))}
      </div>
      <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#8A8678", marginBottom: 16 }}>
        Step {step + 1} of {steps.length}
      </div>
      <h2 style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400, fontSize: 44, lineHeight: 1.1, color: "#1A1A18", margin: "0 0 12px" }}>
        {cur.q}
      </h2>
      <p style={{ fontSize: 15, color: "#7A7668", margin: "0 0 36px", lineHeight: 1.6 }}>{cur.hint}</p>
      <div>{cur.body}</div>
      <div style={{ marginTop: 56, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button onClick={() => setStep(s => Math.max(0, s - 1))} className="ghost-btn" disabled={step === 0}>
          ← Back
        </button>
        <button onClick={() => {
          if (step === steps.length - 1) finish();
          else setStep(s => s + 1);
        }} className="primary-btn" disabled={!canNext}>
          {step === steps.length - 1 ? "Build my plan" : "Continue"} <span style={{ marginLeft: 8 }}>→</span>
        </button>
      </div>
    </div>
  );
};

// ─── PLAN OVERVIEW ───
const PlanOverview = ({ profile, onStartSession }) => {
  const plan = [
    { id: "shoulder_flexion", confidence: 0.92, why: "Restores anterior deltoid range without overhead load." },
    { id: "bicep_curl", confidence: 0.81, why: "Reinforces elbow stability around the affected joint." },
    { id: "squat", confidence: 0.74, why: "Keeps the rest of you strong while the shoulder heals." },
  ];
  return (
    <div style={{ maxWidth: 880, margin: "0 auto", padding: "64px 32px" }}>
      <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#8A8678", marginBottom: 16 }}>
        Your plan, {profile.name}
      </div>
      <h2 style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400, fontSize: 48, lineHeight: 1.1, color: "#1A1A18", margin: "0 0 32px", maxWidth: 640 }}>
        Three small movements. Built around what you told us.
      </h2>
      <div style={{ background: "#FAFAF7", border: "1px solid #EFEDE6", borderRadius: 4, padding: 28, marginBottom: 48 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: "#7BA68C", marginBottom: 10 }}>What we heard</div>
        <div style={{ fontSize: 17, lineHeight: 1.6, color: "#2A2A28", fontFamily: "'Instrument Serif', serif", fontStyle: "italic" }}>
          "{profile.complaint}"
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.65, color: "#5A574E", marginTop: 18, paddingTop: 18, borderTop: "1px dashed #E8E5DD" }}>
          We'll start light. Your pain at <strong>{profile.pain}/10</strong> tells us to favor range over load. Expect to feel <em>worked</em>, not <em>worn</em>. If anything sharpens, stop — we'll adjust.
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 1, background: "#EFEDE6", border: "1px solid #EFEDE6", borderRadius: 4, overflow: "hidden" }}>
        {plan.map((p, i) => {
          const ex = EXERCISES[p.id];
          return (
            <div key={p.id} style={{ background: "#FFFFFF", padding: "28px 32px", display: "grid", gridTemplateColumns: "60px 1fr auto", alignItems: "center", gap: 24 }}>
              <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 32, color: "#7BA68C" }}>0{i + 1}</div>
              <div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 6 }}>
                  <div style={{ fontSize: 19, fontWeight: 500, color: "#1A1A18" }}>{ex.name}</div>
                  <div style={{ fontSize: 12, color: "#8A8678" }}>{ex.sets} sets × {ex.target_reps} reps</div>
                </div>
                <div style={{ fontSize: 13, color: "#7A7668", lineHeight: 1.55, maxWidth: 480 }}>{p.why}</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                <div style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "#8A8678" }}>Confidence</div>
                <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 24, color: "#1A1A18" }}>{Math.round(p.confidence * 100)}%</div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 48, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontSize: 13, color: "#7A7668", maxWidth: 380, lineHeight: 1.6 }}>
          You can pause any exercise at any time. Your camera stays on your device — nothing leaves it.
        </div>
        <button onClick={() => onStartSession(plan)} className="primary-btn">
          Start with shoulder flexion <span style={{ marginLeft: 8 }}>→</span>
        </button>
      </div>
    </div>
  );
};

// ─── EXERCISE SESSION (the heart of the prototype) ───
const ExerciseSession = ({ exerciseId, onFinish, profile }) => {
  const ex = EXERCISES[exerciseId];
  const total = ex.target_reps * ex.sets;
  const [state, setState] = useState("preview"); // preview | countdown | active | rest | done
  const [reps, setReps] = useState(0);
  const [setNum, setSetNum] = useState(1);
  const [phase, setPhase] = useState(0); // 0..1
  const [direction, setDirection] = useState(1);
  const [feedback, setFeedback] = useState(null); // form error key or null
  const [coachLine, setCoachLine] = useState(ex.cues[0]);
  const [countdown, setCountdown] = useState(3);
  const [restLeft, setRestLeft] = useState(20);
  const [errors, setErrors] = useState({});
  const phaseRef = useRef(0);
  const dirRef = useRef(1);

  // Countdown
  useEffect(() => {
    if (state !== "countdown") return;
    if (countdown <= 0) { setState("active"); return; }
    const t = setTimeout(() => setCountdown(c => c - 1), 800);
    return () => clearTimeout(t);
  }, [state, countdown]);

  // Active animation loop — fakes a rep cycle
  useEffect(() => {
    if (state !== "active") return;
    let raf;
    const tick = () => {
      phaseRef.current += dirRef.current * 0.012;
      if (phaseRef.current >= 1) { phaseRef.current = 1; dirRef.current = -1; }
      if (phaseRef.current <= 0 && dirRef.current === -1) {
        phaseRef.current = 0; dirRef.current = 1;
        setReps(r => {
          const nr = r + 1;
          // occasional fake form error
          if (Math.random() < 0.22) {
            const k = ex.watch_for[Math.floor(Math.random() * ex.watch_for.length)];
            setFeedback(k);
            setErrors(e => ({ ...e, [k]: (e[k] || 0) + 1 }));
            setTimeout(() => setFeedback(null), 1800);
          } else {
            setCoachLine(ex.encouragement[nr % ex.encouragement.length]);
          }
          return nr;
        });
      }
      setPhase(phaseRef.current);
      setDirection(dirRef.current);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [state, ex]);

  // Rep -> set logic
  useEffect(() => {
    if (state !== "active") return;
    if (reps > 0 && reps % ex.target_reps === 0) {
      if (setNum >= ex.sets) {
        setState("done");
      } else {
        setState("rest");
        setRestLeft(20);
      }
    }
  }, [reps, state]);

  // Rest countdown
  useEffect(() => {
    if (state !== "rest") return;
    if (restLeft <= 0) {
      setSetNum(s => s + 1);
      setState("active");
      return;
    }
    const t = setTimeout(() => setRestLeft(r => r - 1), 1000);
    return () => clearTimeout(t);
  }, [state, restLeft]);

  // Update cue based on phase
  useEffect(() => {
    if (state !== "active") return;
    const cueIdx = direction === 1 ? Math.min(ex.cues.length - 1, Math.floor(phase * ex.cues.length)) : 0;
    if (!feedback) {
      // soft cue cycling
    }
  }, [phase, direction, state]);

  // ─── PREVIEW ───
  if (state === "preview") {
    return (
      <div style={{ maxWidth: 920, margin: "0 auto", padding: "48px 32px" }}>
        <button onClick={onFinish} className="ghost-btn" style={{ marginBottom: 32 }}>← Back to plan</button>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#8A8678", marginBottom: 14 }}>
              Exercise · Set 1 of {ex.sets}
            </div>
            <h2 style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400, fontSize: 52, lineHeight: 1.05, color: "#1A1A18", margin: "0 0 8px" }}>
              {ex.name}
            </h2>
            <div style={{ fontSize: 15, color: "#7A7668", marginBottom: 32 }}>{ex.sub} · {ex.target_reps} reps × {ex.sets} sets</div>
            <div style={{ background: "#FAFAF7", border: "1px solid #EFEDE6", padding: 24, borderRadius: 4, marginBottom: 32 }}>
              <div style={{ fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: "#7BA68C", marginBottom: 14 }}>How to move</div>
              <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 14 }}>
                {ex.cues.map((c, i) => (
                  <li key={i} style={{ display: "flex", gap: 14, fontSize: 14, color: "#2A2A28", lineHeight: 1.55 }}>
                    <span style={{ fontFamily: "'Instrument Serif', serif", fontSize: 16, color: "#7BA68C", minWidth: 20 }}>{i + 1}</span>
                    {c}
                  </li>
                ))}
              </ol>
            </div>
            <div style={{ fontSize: 13, color: "#7A7668", lineHeight: 1.6, marginBottom: 32 }}>
              When you press start, your camera will turn on. Stand back so we can see your full body — about a step further than arm's length.
            </div>
            <button onClick={() => { setState("countdown"); setCountdown(3); }} className="primary-btn">
              I'm ready — turn on camera <span style={{ marginLeft: 8 }}>→</span>
            </button>
          </div>
          <div style={{ background: "#FAFAF7", borderRadius: 4, padding: 32, aspectRatio: "3/4", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ width: "100%", height: "100%" }}>
              <Skeleton status="good" phase={0.4} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── COUNTDOWN ───
  if (state === "countdown") {
    return (
      <div style={{ minHeight: "75vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#8A8678", marginBottom: 32 }}>
          Find your starting position
        </div>
        <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 200, lineHeight: 1, color: "#1A1A18" }}>
          {countdown > 0 ? countdown : "Go"}
        </div>
        <div style={{ fontSize: 15, color: "#7A7668", marginTop: 32, maxWidth: 380, textAlign: "center", lineHeight: 1.6 }}>
          Take one slow breath. Whenever you're ready.
        </div>
      </div>
    );
  }

  // ─── REST ───
  if (state === "rest") {
    return (
      <div style={{ minHeight: "75vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 32 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#7BA68C", marginBottom: 24 }}>
          Set {setNum} complete · Rest
        </div>
        <h2 style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400, fontSize: 64, lineHeight: 1.1, color: "#1A1A18", margin: "0 0 32px", textAlign: "center", maxWidth: 600 }}>
          That was {setNum === 1 ? "a great start" : setNum === 2 ? "even better" : "your strongest yet"}.
        </h2>
        <div style={{ width: 220, height: 220, position: "relative", marginBottom: 24 }}>
          <RingProgress value={20 - restLeft} total={20} size={220} label={restLeft} sub="seconds" />
        </div>
        <div style={{ fontSize: 14, color: "#7A7668", maxWidth: 420, textAlign: "center", lineHeight: 1.6, marginBottom: 32 }}>
          Roll your shoulders. Take a sip of water. Set {setNum + 1} starts in a moment — or skip when you feel ready.
        </div>
        <button onClick={() => { setSetNum(s => s + 1); setState("active"); }} className="ghost-btn">
          Skip rest →
        </button>
      </div>
    );
  }

  // ─── DONE ───
  if (state === "done") {
    const totalErrors = Object.values(errors).reduce((a, b) => a + b, 0);
    return (
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "80px 32px", textAlign: "center" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#7BA68C", marginBottom: 24 }}>
          Exercise complete
        </div>
        <h2 style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400, fontSize: 64, lineHeight: 1.05, color: "#1A1A18", margin: "0 0 24px" }}>
          You showed up.<br />That's the whole thing.
        </h2>
        <p style={{ fontSize: 16, color: "#5A574E", lineHeight: 1.65, maxWidth: 520, margin: "0 auto 56px" }}>
          {totalErrors === 0
            ? "And your form was steady the whole way through. Tomorrow's session will feel a little easier because of this one."
            : `We noticed your form drift a few times — that's normal as muscles fatigue. We'll work on it together next time.`}
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 32, textAlign: "center", marginBottom: 56 }}>
          {[
            { l: "Reps completed", v: reps, sub: `of ${total}` },
            { l: "Form check-ins", v: totalErrors, sub: "moments to refine" },
            { l: "Time moving", v: "4:12", sub: "minutes" },
          ].map((s, i) => (
            <div key={i}>
              <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 48, color: "#1A1A18" }}>{s.v}</div>
              <div style={{ fontSize: 11, letterSpacing: "0.16em", textTransform: "uppercase", color: "#8A8678", marginTop: 6 }}>{s.l}</div>
              <div style={{ fontSize: 12, color: "#A8A496", marginTop: 4 }}>{s.sub}</div>
            </div>
          ))}
        </div>
        <button onClick={onFinish} className="primary-btn">Continue → next exercise</button>
      </div>
    );
  }

  // ─── ACTIVE SESSION ───
  const setReps_ = reps - (setNum - 1) * ex.target_reps;
  const fbCue = feedback ? FORM_CUES[feedback] : null;

  return (
    <div className="session-stage">
      {/* Camera/skeleton viewport */}
      <div className="camera-pane">
        <div className="camera-bg">
          {/* fake camera grain */}
          <div className="grain" />
          <div style={{ position: "relative", width: 360, height: 480 }}>
            <Skeleton status={feedback ? "warn" : "good"} phase={phase} />
            {/* subtle motion trail */}
            <div className="motion-trail" style={{ opacity: direction === 1 ? 0.3 : 0 }}>
              <Skeleton status={feedback ? "warn" : "good"} phase={Math.max(0, phase - 0.15)} />
            </div>
          </div>
          {/* HUD top */}
          <div className="hud-top">
            <div>
              <div className="hud-label">Set</div>
              <div className="hud-val">{setNum} / {ex.sets}</div>
            </div>
            <div className="hud-status">
              <span className={"dot " + (feedback ? "warn" : "good")} />
              {feedback ? "Adjusting" : "Tracking well"}
            </div>
            <button onClick={onFinish} className="hud-exit">End session ✕</button>
          </div>
          {/* Form feedback banner */}
          {feedback && (
            <div className="feedback-banner">
              <span className="fb-icon">{fbCue.icon}</span>
              <span>{fbCue.soft}</span>
            </div>
          )}
          {/* Phase indicator */}
          <div className="phase-strip">
            <div className="phase-fill" style={{ height: `${phase * 100}%`, background: feedback ? "#C97C5D" : "#7BA68C" }} />
          </div>
        </div>
      </div>

      {/* Coach side panel */}
      <aside className="coach-pane">
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#8A8678", marginBottom: 12 }}>
            {ex.sub}
          </div>
          <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 36, lineHeight: 1.05, color: "#1A1A18" }}>
            {ex.name}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "center", marginBottom: 32 }}>
          <RingProgress value={setReps_} total={ex.target_reps} size={180} label={setReps_} sub={`of ${ex.target_reps}`} />
        </div>

        <div className="coach-bubble">
          <div style={{ fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: "#7BA68C", marginBottom: 10 }}>
            {feedback ? "Gentle adjustment" : "Coach"}
          </div>
          <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 22, lineHeight: 1.3, color: "#1A1A18" }}>
            {feedback ? FORM_CUES[feedback].soft : coachLine}
          </div>
        </div>

        <div style={{ marginTop: 32, paddingTop: 24, borderTop: "1px solid #EFEDE6" }}>
          <div style={{ fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: "#8A8678", marginBottom: 14 }}>
            Movement phase
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {["Lifting", "Holding at top", "Lowering"].map((p, i) => {
              const active = (direction === 1 && phase < 0.85 && i === 0) ||
                (phase >= 0.85 && i === 1) ||
                (direction === -1 && phase < 0.85 && i === 2);
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 12,
                  fontSize: 13, color: active ? "#1A1A18" : "#A8A496",
                  fontWeight: active ? 500 : 400, transition: "all 0.3s"
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: 3, background: active ? "#7BA68C" : "#D8D5CC" }} />
                  {p}
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ marginTop: "auto", paddingTop: 32, fontSize: 12, color: "#A8A496", lineHeight: 1.6 }}>
          Camera processing happens on your device. Pause anytime by stepping out of frame.
        </div>
      </aside>
    </div>
  );
};

// ─── REPORTS ───
const Reports = ({ onRestart, profile }) => {
  const days = Array.from({ length: 14 }).map((_, i) => ({
    label: ["M", "T", "W", "T", "F", "S", "S"][i % 7],
    minutes: i < 5 ? 0 : Math.max(0, Math.round(8 + Math.sin(i * 0.7) * 4 + (i - 5) * 0.6)),
    completed: i >= 5,
    isToday: i === 13,
  }));
  const max = Math.max(...days.map(d => d.minutes), 16);

  return (
    <div style={{ maxWidth: 880, margin: "0 auto", padding: "64px 32px" }}>
      <div style={{ fontSize: 11, letterSpacing: "0.24em", textTransform: "uppercase", color: "#8A8678", marginBottom: 16 }}>
        Your story so far
      </div>
      <h2 style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 400, fontSize: 56, lineHeight: 1.05, color: "#1A1A18", margin: "0 0 16px" }}>
        Nine days in.<br />Your shoulder is listening.
      </h2>
      <p style={{ fontSize: 16, color: "#5A574E", lineHeight: 1.6, maxWidth: 580, marginBottom: 56 }}>
        You've shown up 9 of the last 14 days. Your form drift on shoulder flexion has dropped by more than half. That's not a number — that's tissue remodeling. Keep going.
      </p>

      {/* Adherence ribbon */}
      <div style={{ marginBottom: 56 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 24 }}>
          <div style={{ fontSize: 13, letterSpacing: "0.16em", textTransform: "uppercase", color: "#8A8678" }}>
            Two weeks of movement
          </div>
          <div style={{ fontSize: 13, color: "#7A7668" }}>9 of 14 days</div>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "flex-end", height: 140 }}>
          {days.map((d, i) => (
            <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <div style={{
                width: "100%",
                height: `${(d.minutes / max) * 100}%`,
                minHeight: d.completed ? 6 : 2,
                background: d.isToday ? "#1A1A18" : d.completed ? "#7BA68C" : "#EFEDE6",
                borderRadius: 2,
                transition: "all 0.5s",
              }} />
              <div style={{ fontSize: 10, color: d.isToday ? "#1A1A18" : "#A8A496", fontWeight: d.isToday ? 500 : 400 }}>{d.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Form drift improvement */}
      <div style={{ background: "#FAFAF7", border: "1px solid #EFEDE6", borderRadius: 4, padding: 32, marginBottom: 32 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: "#7BA68C", marginBottom: 18 }}>
          What's getting easier
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {[
            { name: "Keeping arm straight", was: 8, now: 2 },
            { name: "Staying tall through chest", was: 5, now: 3 },
            { name: "Tucking elbows on curls", was: 6, now: 1 },
          ].map((m, i) => (
            <div key={i}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 14, color: "#1A1A18" }}>{m.name}</span>
                <span style={{ fontSize: 12, color: "#7A7668" }}>{m.was} → {m.now} reminders / session</span>
              </div>
              <div style={{ position: "relative", height: 6, background: "#EFEDE6", borderRadius: 3 }}>
                <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${(1 - m.now / m.was) * 100}%`, background: "#7BA68C", borderRadius: 3, transition: "width 0.8s" }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Coach reflection */}
      <div style={{ borderLeft: "2px solid #7BA68C", paddingLeft: 24, margin: "48px 0", maxWidth: 560 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase", color: "#7BA68C", marginBottom: 12 }}>
          A note from your coach
        </div>
        <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 22, fontStyle: "italic", lineHeight: 1.4, color: "#2A2A28" }}>
          "{profile.name || "You"}, your range is opening up. I'd like to introduce a wall push-up next week — small load, steady control. Only if your pain stays at 3 or below."
        </div>
      </div>

      <div style={{ marginTop: 56, display: "flex", gap: 16 }}>
        <button onClick={onRestart} className="primary-btn">Today's session →</button>
        <button onClick={onRestart} className="ghost-btn">Adjust plan</button>
      </div>
    </div>
  );
};

window.PT = { Landing, Intake, PlanOverview, ExerciseSession, Reports, EXERCISES };
