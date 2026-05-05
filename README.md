<div align="center">

# 💪 PhysioTracker AI

### *Your AI-Powered Physiotherapy Companion — Real-Time Form Coaching, Personalised Exercise Plans, and Progress Analytics*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Pose%20CV-0097A7?style=flat-square&logo=google&logoColor=white)](https://mediapipe.dev/)
[![Gemini AI](https://img.shields.io/badge/Gemini%202.5%20Flash-LLM-4285F4?style=flat-square&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org/)

</div>

---

## 📌 Overview

**PhysioTracker AI** is a full-stack, AI-assisted physiotherapy platform that transforms any webcam into a smart rehabilitation coach. It combines the reasoning power of **Google Gemini 2.5 Flash** with the real-time body tracking of **MediaPipe Pose** to give patients a personalised, data-driven recovery experience from home — no physiotherapist required for routine sessions.

> "Think of it as a physiotherapy clinic in your browser — your AI clinician writes the plan, and your camera enforces perfect form."

---

## 🚨 Problem Statement

Physiotherapy rehabilitation is broken for most patients:

- 🏥 **Access gap** — millions lack regular access to a physiotherapist due to cost, geography, or time.
- 📉 **Non-adherence** — up to 65% of patients do not follow home exercise programmes correctly.
- 🙈 **No form feedback** — patients do exercises unsupervised, reinforcing bad movement patterns and risking re-injury.
- 📊 **No data** — clinicians have no visibility into what patients actually do between appointments.

---

## ✅ Solution

PhysioTracker AI solves all four problems in a single, browser-based application:

| Problem | Solution |
|---|---|
| No access to a physiotherapist | Gemini AI generates a medically-aware, personalised exercise plan from a text description of the injury |
| Bad form with no correction | MediaPipe Pose analyses every frame — skeleton turns **red** on errors, **green** on perfect form |
| Low adherence | Real-time HUD counts reps, tracks sets, and shows live cues to keep patients motivated |
| No progress visibility | Analytics dashboard with adherence scores, form quality trends, and error frequency charts |

---

## ✨ Features

### 🤖 AI-Powered Plan Generation
- Describe your injury in plain language; Gemini 2.5 Flash generates a safe, prioritised, personalised exercise programme.
- Low-confidence exercises (< 0.6) are automatically filtered out before saving.
- Side-specific prescriptions (e.g., "right knee") are honoured — unilateral exercises are labelled left/right automatically.

### 🎥 Real-Time Computer Vision Coaching
- MediaPipe Pose 33-point skeleton tracked at webcam frame rate via WebRTC.
- **15 exercises** with individual biomechanical state-machine evaluators, each checking exercise-specific form errors (see full list below).
- Live HUD overlay: rep counter, current phase, and posture feedback banner.
- Dynamic skeleton colour: 🟢 **green** = correct form, 🔴 **red** = error detected.

### 📈 Analytics Dashboard
- **Adherence %** — reps completed vs. target, per session.
- **Form Score** — exponential decay algorithm (Score = 100 × e^(−0.5 × error\_ratio)) for a smooth, meaningful quality metric.
- **Consistency Score** — mathematical stability of adherence over time (low variance = high consistency).
- Interactive Plotly charts: area progression, form quality trend, radar error distribution, workout heatmap, and left vs. right limb comparison.

### 🏋️ Exercises Supported (15)

| Exercise | Type | Side-Specific | Key Checks |
|---|---|---|---|
| Squat | Rep-based | No | Knee cave, torso lean, knee-over-toe |
| Shoulder Flexion | Rep-based | Yes | Elbow bend, torso lean-back |
| Jumping Jacks | Rep-based | No | Arms reaching overhead |
| Knee Extension | Rep-based | Yes | Hyperextension, thigh lift |
| Bicep Curl | Rep-based | Yes | Elbow drift, torso swing |
| Shoulder Abduction | Rep-based | Yes | Shoulder level, lateral torso lean |
| Wall Push-Up | Rep-based | No | Body alignment (hip sag) |
| Single Leg Stand | Time-based | Yes | Shoulder level, balance lean |
| High Knees | Rep-based | No | Knee height |
| Cat-Cow Stretch | Rep-based | No | Hand/knee alignment |
| Lunge | Rep-based | Yes | Knee-over-toe, torso lean |
| Bird Dog | Rep-based | Yes | Spinal neutrality |
| Seated Forward Bend | Rep-based | No | Knee bend, hold duration |
| Neck Lateral Flexion | Rep-based | Yes | Shoulder rise |
| Hip Abduction | Rep-based | Yes | Torso lean |

---

## 🎬 Demo / Screenshots

> **Live demo:** *(Deploy to Streamlit Cloud and insert link here)*

### Application Flow

**Step 1 — Patient Intake**

> Enter your name, describe your injury in plain text, rate your pain (0–10). Gemini AI generates your personalised programme in seconds.

**Step 2 — Exercise Session**

> Your webcam streams to the MediaPipe CV engine. A live skeleton overlay tracks your body with a rep counter and real-time posture feedback banner.

**Step 3 — Analytics Reports**

> View your adherence, form quality score over time, most common form errors on a radar chart, and daily workout frequency heatmap.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend / UI** | Streamlit 1.35+, streamlit-webrtc |
| **AI / LLM** | Google Gemini 2.5 Flash (`google-genai`) |
| **Computer Vision** | MediaPipe Pose, OpenCV (headless) |
| **Video Streaming** | WebRTC via `av`, `streamlit-webrtc` |
| **Database / ORM** | SQLAlchemy 2.0 + SQLite |
| **Data & Visualisation** | Pandas, Plotly, NumPy |
| **Configuration** | python-dotenv |
| **Language** | Python 3.10+ |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        STREAMLIT BROWSER                        │
│  ┌──────────────┐  ┌──────────────────────┐  ┌───────────────┐ │
│  │  1_Intake    │  │  2_Exercise_Session  │  │   3_Reports   │ │
│  │  (LLM Plan)  │  │  (WebRTC + CV)       │  │  (Analytics)  │ │
│  └──────┬───────┘  └──────────┬───────────┘  └───────┬───────┘ │
└─────────┼────────────────────┼──────────────────────┼──────────┘
          │                    │                      │
          ▼                    ▼                      ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│   llm_client.py │  │  cv_engine/      │  │    database.py       │
│                 │  │  evaluator.py    │  │                      │
│  Google Gemini  │  │  ┌────────────┐  │  │  Users               │
│  2.5 Flash API  │  │  │ MediaPipe  │  │  │  Assessments         │
│                 │  │  │   Pose     │  │  │  ExercisePlans       │
│  Prompt →       │  │  └────────────┘  │  │  SessionLogs         │
│  JSON Plan      │  │  State Machine   │  │                      │
└─────────────────┘  │  (per exercise)  │  │  SQLite (local)      │
                     └──────────────────┘  └──────────────────────┘
```

### Key Design Decisions

- **State-machine evaluators** — Each exercise has its own phase-based state machine (e.g., `INIT → SQUATTING → STANDING`) to count reps accurately without false positives.
- **Visibility gating** — All CV checks first confirm that required landmarks have confidence ≥ 0.6 before evaluating angles, preventing spurious errors on partial occlusion.
- **LLM confidence filtering** — Gemini returns a confidence score per exercise; items below 0.6 are silently discarded before saving to the database.
- **Exponential form score** — `Score = 100 × e^(−0.5 × error_ratio)` gives a smooth, non-punishing quality metric that trends clearly over sessions.

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- A webcam
- A [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier available)

### 1. Clone the repository

```bash
git clone https://github.com/Tejash-Pathak-1905/PhysioTracker-AI.git
cd PhysioTracker-AI
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run the application

```bash
streamlit run frontend/app.py
```

The app will open at `http://localhost:8501`.

---

## 📖 Usage

### Step 1 — Intake
1. Navigate to the **Intake** page from the sidebar.
2. Enter your name (a new profile is created automatically on first visit).
3. Describe your injury or rehabilitation goal in the text area.
4. Rate your current pain level on the slider (0–10).
5. Click **"🤖 Generate My Plan"** — Gemini AI returns a prioritised exercise programme in seconds.

### Step 2 — Exercise Session
1. Navigate to the **Exercise Session** page.
2. Select an exercise from the dropdown (sorted by AI-assigned priority).
3. Read the on-screen instructions and any caution notes.
4. Click **Start** on the WebRTC widget to activate your webcam.
5. Perform the exercise — watch the skeleton feedback and rep counter.
6. Click **"✅ Complete / End Session"** to save your results, or **"🚨 End Early"** if you need to stop.

### Step 3 — Reports
1. Navigate to the **Reports** page after completing at least one session.
2. Review your KPIs: Adherence %, Form Score, Consistency Score, and total time.
3. Explore the interactive charts to identify trends and common form errors.

---

## 📁 Project Structure

```
PhysioTracker-AI/
│
├── frontend/                        # Streamlit application
│   ├── app.py                       # Entry point & home screen
│   ├── exercises.json               # Exercise catalogue (15 exercises)
│   └── pages/
│       ├── 1_Intake.py              # Patient intake & AI plan generation
│       ├── 2_Exercise_Session.py    # Live WebRTC + CV exercise tracking
│       └── 3_Reports.py            # Analytics & progress dashboard
│
├── cv_engine/                       # Computer vision module
│   ├── __init__.py
│   ├── evaluator.py                 # MediaPipe Pose evaluator & state machines
│   └── utils.py                     # Geometric helpers (angle, visibility)
│
├── database.py                      # SQLAlchemy ORM models & session management
├── llm_client.py                    # Google Gemini client & prompt engineering
├── requirements.txt
├── .env.example                     # Environment variable template
└── README.md
```

---

## 🌟 Why This Project Stands Out

| Dimension | What Makes It Different |
|---|---|
| **End-to-end integration** | LLM plan generation + CV form analysis + analytics in a single cohesive app — not just a chatbot or just a pose detector |
| **Safety-first AI** | Gemini is prompted with explicit clinical safety rules; exercises with low clinical confidence are automatically excluded |
| **Biomechanically grounded CV** | Each exercise uses its own state machine with sport-science-informed angle thresholds (e.g., knee valgus detection, torso lean, hyperextension) rather than generic pose comparison |
| **Quantified rehabilitation** | Mathematical form score and consistency metric give objective, reproducible measurements of recovery progress |
| **Zero infrastructure** | Runs entirely on a laptop — no cloud backend, no external database, no deployment required |

---

## 💡 Use Cases

- **Post-surgical home rehabilitation** — Knee replacement, ACL reconstruction, rotator-cuff repair.
- **Chronic pain management** — Lower back pain (cat-cow, bird dog), neck pain, shoulder impingement.
- **Sports injury recovery** — Gradual return-to-sport protocols with adherence tracking.
- **Remote physiotherapy support** — Clinicians can review session logs and adherence reports between appointments.
- **Elderly fall prevention** — Balance training (single leg stand) with quantified consistency scores.
- **Corporate wellness** — Guided stretching and mobility programmes for desk workers.

---

## 🗺️ Roadmap / Future Work

- [ ] **User authentication** — Secure login with password hashing (bcrypt) for multi-user environments.
- [ ] **Clinician portal** — Separate dashboard for physiotherapists to review patient progress remotely.
- [ ] **More exercises** — Expand the catalogue to 30+ exercises including resistance band, floor, and aquatic protocols.
- [ ] **Voice coaching** — Text-to-speech form cues for a more accessible, eyes-free experience.
- [ ] **Mobile support** — Progressive Web App (PWA) packaging for smartphone webcam use.
- [ ] **3D pose estimation** — Upgrade to depth-aware pose estimation for more accurate angle measurement.
- [ ] **Wearable integration** — Ingest heart rate and ROM data from smartwatches (Apple Health, Garmin).
- [ ] **PDF session reports** — Exportable progress reports for patients to share with their clinician.
- [ ] **Multi-language support** — Localise UI and LLM prompts for broader accessibility.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. **Fork** the repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a **Pull Request** with a clear description of your changes.

Please ensure your code follows existing style conventions and that any new exercise evaluators include at minimum one biomechanical form check.

---

## 👥 Contributors

| Name | Role |
|---|---|
| **Tejash Pathak** | Creator & Lead Developer |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made with ❤️ for better rehabilitation outcomes

**[⬆ Back to top](#-physiotracker-ai)**

</div>
