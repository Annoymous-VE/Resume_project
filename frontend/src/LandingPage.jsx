import React, { useEffect, useRef } from "react";

export default function LandingPage({ children }) {
  const revealRefs = useRef([]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    revealRefs.current.forEach((el) => {
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const addRevealRef = (el) => {
    if (el && !revealRefs.current.includes(el)) {
      revealRefs.current.push(el);
    }
  };

  const scrollToGetStarted = () => {
    document.getElementById("get-started")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="landing-page">
      {/* ═══════════════════════════════════════════
          Hero Section
          ═══════════════════════════════════════════ */}
      <section className="landing-hero">
        <div className="landing-hero-mesh" aria-hidden="true" />

        <div className="landing-hero-content">
          <div className="landing-hero-badge">
            <span className="landing-hero-badge-dot" />
            AI-Powered Case Study Generator
          </div>

          <h1 className="landing-hero-title">
            Turn Your Resume Into
            <span className="landing-hero-gradient-text">
              {" "}Professional Technical Case Studies
            </span>
          </h1>

          <p className="landing-hero-subtitle">
            Upload your resume and let our AI conduct an adaptive interview to
            extract the engineering depth from your projects — then generate
            publication-ready case studies in seconds.
          </p>

          <div className="landing-hero-actions">
            <button
              className="landing-hero-cta"
              onClick={scrollToGetStarted}
              type="button"
            >
              Get Started — It's Free
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 5v14" />
                <path d="m19 12-7 7-7-7" />
              </svg>
            </button>
          </div>

          <div className="landing-hero-trust">
            <span className="landing-trust-pill">✦ Secure cloud storage</span>
            <span className="landing-trust-pill">📄 PDF, DOCX, TXT</span>
            <span className="landing-trust-pill">⬇️ Export PDF & Word</span>
          </div>
        </div>

        {/* Scroll Indicator */}
        <div className="landing-scroll-indicator" aria-hidden="true">
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>

        <div className="landing-hero-fade" aria-hidden="true" />
      </section>

      {/* ═══════════════════════════════════════════
          How It Works
          ═══════════════════════════════════════════ */}
      <section className="landing-section" ref={addRevealRef}>
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <span className="landing-section-eyebrow">How It Works</span>
            <h2 className="landing-section-title">
              From Resume to Case Study in 4 Steps
            </h2>
            <p className="landing-section-desc">
              Our streamlined process transforms your existing resume into
              detailed, interview-backed technical case studies.
            </p>
          </div>

          <div className="landing-steps-track">
            {STEPS_DATA.map((step, idx) => (
              <React.Fragment key={step.num}>
                {idx > 0 && <div className="landing-step-connector" />}
                <div className="landing-step-card">
                  <div className="landing-step-num">{step.num}</div>
                  <div className="landing-step-icon">{step.icon}</div>
                  <h3 className="landing-step-title">{step.title}</h3>
                  <p className="landing-step-desc">{step.desc}</p>
                </div>
              </React.Fragment>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          Features
          ═══════════════════════════════════════════ */}
      <section className="landing-section landing-section-alt" ref={addRevealRef}>
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <span className="landing-section-eyebrow">Features</span>
            <h2 className="landing-section-title">Why This Tool Stands Out</h2>
            <p className="landing-section-desc">
              Built from the ground up for software engineers who want to
              showcase their deepest technical work.
            </p>
          </div>

          <div className="landing-features-grid">
            {FEATURES_DATA.map((feature, idx) => (
              <div
                key={idx}
                className={`landing-feature-card ${feature.accentClass}`}
              >
                <div className="landing-feature-icon-wrap">
                  <span className="landing-feature-icon">{feature.icon}</span>
                </div>
                <h3 className="landing-feature-title">{feature.title}</h3>
                <p className="landing-feature-desc">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          Get Started — Existing Upload Form
          ═══════════════════════════════════════════ */}
      <section
        className="landing-section landing-get-started"
        id="get-started"
        ref={addRevealRef}
      >
        <div className="landing-section-inner">
          <div className="landing-section-header">
            <span className="landing-section-eyebrow">Get Started</span>
            <h2 className="landing-section-title">
              Ready to Build Your Case Study?
            </h2>
            <p className="landing-section-desc">
              Upload your resume below and let our AI do the heavy lifting. No
              account needed.
            </p>
          </div>
          <div className="landing-upload-wrapper">{children}</div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          Footer
          ═══════════════════════════════════════════ */}
      <footer className="landing-footer">
        <p>
          Resume-to-Technical-Case-Study · Built with AI-powered adaptive
          interviews
        </p>
      </footer>
    </div>
  );
}

/* ─── Static Data ─── */

const STEPS_DATA = [
  {
    num: "01",
    icon: (
      <svg
        width="28"
        height="28"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
    ),
    title: "Upload Resume",
    desc: "Drop your PDF, DOCX, or text resume — our parser handles any format and layout.",
  },
  {
    num: "02",
    icon: (
      <svg
        width="28"
        height="28"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="14" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </svg>
    ),
    title: "AI Detection",
    desc: "Semantic extraction automatically identifies your technical projects, technologies, and contributions.",
  },
  {
    num: "03",
    icon: (
      <svg
        width="28"
        height="28"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
    title: "Smart Interview",
    desc: "An AI tech lead asks focused questions to fill knowledge gaps — typically just 3–5 quick rounds.",
  },
  {
    num: "04",
    icon: (
      <svg
        width="28"
        height="28"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
    title: "Case Study",
    desc: "Get a polished, exportable technical case study — ready for portfolios or job applications.",
  },
];

const FEATURES_DATA = [
  {
    accentClass: "accent-blue",
    icon: "🔍",
    title: "Intelligent Extraction",
    desc: "Layout-aware parsing detects projects, technologies, and contributions from any resume format — no templates needed.",
  },
  {
    accentClass: "accent-green",
    icon: "🤖",
    title: "Adaptive AI Interview",
    desc: "An AI senior tech lead asks only the most impactful questions, with real-time knowledge tracking across 8 criteria dimensions.",
  },
  {
    accentClass: "accent-purple",
    icon: "📄",
    title: "Publication-Ready Output",
    desc: "Export as PDF, Word, or Markdown — professionally formatted case studies ready for portfolios, LinkedIn, or job applications.",
  },
];
