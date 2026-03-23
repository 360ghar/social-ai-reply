import Link from "next/link";

export default function MarketingPage() {
  return (
    <main className="site-shell">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-card">
          <div className="hero-grid">
            {/* Left Column */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                gap: "var(--space-2xl)",
              }}
            >
              <div>
                <div className="eyebrow">AI Visibility Platform</div>
                <h1
                  style={{
                    fontSize: "48px",
                    fontWeight: 700,
                    lineHeight: 1.2,
                    color: "var(--brand)",
                    marginBottom: "var(--space-lg)",
                  }}
                >
                  See How AI Talks About Your Brand
                </h1>
                <p
                  style={{
                    fontSize: "18px",
                    color: "var(--muted)",
                    lineHeight: 1.6,
                    maxWidth: "500px",
                  }}
                >
                  Monitor brand mentions across ChatGPT, Perplexity, Gemini, and Claude. Get real-time insights on
                  share of voice, citations, and competitive positioning in AI responses.
                </p>
              </div>

              {/* CTA Buttons */}
              <div style={{ display: "flex", gap: "var(--space-lg)", flexWrap: "wrap" }}>
                <Link
                  href="/register"
                  className="primary-button"
                  style={{
                    padding: "12px 32px",
                    fontSize: "16px",
                    fontWeight: 600,
                  }}
                >
                  Get Started Free
                </Link>
                <a
                  href="#features"
                  className="secondary-button"
                  style={{
                    padding: "12px 32px",
                    fontSize: "16px",
                    fontWeight: 600,
                  }}
                >
                  See Demo
                </a>
              </div>

              {/* Trust Badges */}
              <div className="badge-row">
                <div className="badge">No credit card required</div>
                <div className="badge">Setup in 2 minutes</div>
                <div className="badge">100% Free</div>
              </div>
            </div>

            {/* Right Column - Hero Illustration */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "linear-gradient(135deg, var(--surface) 0%, rgba(15, 52, 96, 0.05) 100%)",
                borderRadius: "var(--radius-xl)",
                minHeight: "400px",
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: "-40%",
                  right: "-20%",
                  width: "400px",
                  height: "400px",
                  background: "radial-gradient(circle, rgba(233, 69, 96, 0.1) 0%, transparent 70%)",
                  borderRadius: "50%",
                }}
              />
              <div
                style={{
                  position: "relative",
                  zIndex: 1,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "64px",
                    fontWeight: 700,
                    color: "var(--accent)",
                    marginBottom: "var(--space-md)",
                  }}
                >
                  🔍
                </div>
                <p style={{ color: "var(--muted)", fontSize: "14px" }}>AI Visibility Dashboard</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof Bar */}
      <section
        style={{
          background: "var(--card)",
          borderTop: "1px solid var(--border)",
          borderBottom: "1px solid var(--border)",
          padding: "var(--space-3xl) var(--space-xl)",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "var(--space-2xl)",
            textAlign: "center",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "28px",
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              500+
            </div>
            <p style={{ color: "var(--muted)", marginTop: "var(--space-sm)" }}>Brands Tracked</p>
          </div>
          <div>
            <div
              style={{
                fontSize: "28px",
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              1M+
            </div>
            <p style={{ color: "var(--muted)", marginTop: "var(--space-sm)" }}>AI Responses Analyzed</p>
          </div>
          <div>
            <div
              style={{
                fontSize: "28px",
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              98%
            </div>
            <p style={{ color: "var(--muted)", marginTop: "var(--space-sm)" }}>Uptime</p>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section
        style={{
          maxWidth: "1200px",
          margin: "var(--space-3xl) auto",
          padding: "0 var(--space-xl)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "var(--space-3xl)" }}>
          <div className="eyebrow">How It Works</div>
          <h2
            style={{
              fontSize: "36px",
              fontWeight: 700,
              color: "var(--brand)",
              marginTop: "var(--space-md)",
            }}
          >
            Three Simple Steps to AI Visibility
          </h2>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: "var(--space-2xl)",
          }}
        >
          {/* Step 1 */}
          <div
            className="card"
            style={{
              padding: "var(--space-2xl)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                background: "var(--accent)",
                borderRadius: "var(--radius-lg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: "24px",
                fontWeight: 700,
                marginBottom: "var(--space-lg)",
              }}
            >
              1
            </div>
            <h3
              style={{
                fontSize: "20px",
                fontWeight: 600,
                color: "var(--brand)",
                marginBottom: "var(--space-md)",
              }}
            >
              Set Up Your Profile
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6 }}>
              Add your brand profile and competitors. We analyze your positioning across AI models in seconds.
            </p>
          </div>

          {/* Step 2 */}
          <div
            className="card"
            style={{
              padding: "var(--space-2xl)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                background: "var(--accent)",
                borderRadius: "var(--radius-lg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: "24px",
                fontWeight: 700,
                marginBottom: "var(--space-lg)",
              }}
            >
              2
            </div>
            <h3
              style={{
                fontSize: "20px",
                fontWeight: 600,
                color: "var(--brand)",
                marginBottom: "var(--space-md)",
              }}
            >
              Monitor AI Responses
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6 }}>
              Our system monitors how ChatGPT, Perplexity, Gemini, and Claude respond to relevant queries.
            </p>
          </div>

          {/* Step 3 */}
          <div
            className="card"
            style={{
              padding: "var(--space-2xl)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                background: "var(--accent)",
                borderRadius: "var(--radius-lg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontSize: "24px",
                fontWeight: 700,
                marginBottom: "var(--space-lg)",
              }}
            >
              3
            </div>
            <h3
              style={{
                fontSize: "20px",
                fontWeight: 600,
                color: "var(--brand)",
                marginBottom: "var(--space-md)",
              }}
            >
              Get Actionable Insights
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6 }}>
              Track share of voice, citations, and sentiment. Find opportunities where competitors lead.
            </p>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section
        id="features"
        style={{
          maxWidth: "1200px",
          margin: "var(--space-3xl) auto",
          padding: "0 var(--space-xl)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "var(--space-3xl)" }}>
          <div className="eyebrow">Capabilities</div>
          <h2
            style={{
              fontSize: "36px",
              fontWeight: 700,
              color: "var(--brand)",
              marginTop: "var(--space-md)",
            }}
          >
            Everything You Need for AI Visibility
          </h2>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: "var(--space-2xl)",
          }}
        >
          {/* Feature 1 */}
          <div className="feature-card">
            <div className="eyebrow">Monitor</div>
            <h3 style={{ fontSize: "20px", fontWeight: 600, color: "var(--brand)", marginTop: "var(--space-md)" }}>
              AI Visibility Tracking
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6, marginTop: "var(--space-md)" }}>
              Monitor brand mentions across ChatGPT, Perplexity, Gemini, and Claude in real-time.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="feature-card">
            <div className="eyebrow">Analyze</div>
            <h3 style={{ fontSize: "20px", fontWeight: 600, color: "var(--brand)", marginTop: "var(--space-md)" }}>
              Citation Intelligence
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6, marginTop: "var(--space-md)" }}>
              Track which sources AI models recommend and how often your brand appears in responses.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="feature-card">
            <div className="eyebrow">Discover</div>
            <h3 style={{ fontSize: "20px", fontWeight: 600, color: "var(--brand)", marginTop: "var(--space-md)" }}>
              Source Gap Analysis
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6, marginTop: "var(--space-md)" }}>
              Find where competitors appear in AI responses but you don't. Identify content gaps.
            </p>
          </div>

          {/* Feature 4 */}
          <div className="feature-card">
            <div className="eyebrow">Engage</div>
            <h3 style={{ fontSize: "20px", fontWeight: 600, color: "var(--brand)", marginTop: "var(--space-md)" }}>
              Reddit Engagement
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6, marginTop: "var(--space-md)" }}>
              Find and respond to relevant Reddit conversations where your audience actively discusses solutions.
            </p>
          </div>

          {/* Feature 5 */}
          <div className="feature-card">
            <div className="eyebrow">Create</div>
            <h3 style={{ fontSize: "20px", fontWeight: 600, color: "var(--brand)", marginTop: "var(--space-md)" }}>
              Content Studio
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6, marginTop: "var(--space-md)" }}>
              AI-powered reply drafts with your brand voice. Edit and publish with confidence.
            </p>
          </div>

          {/* Feature 6 */}
          <div className="feature-card">
            <div className="eyebrow">Benchmark</div>
            <h3 style={{ fontSize: "20px", fontWeight: 600, color: "var(--brand)", marginTop: "var(--space-md)" }}>
              Smart Analytics
            </h3>
            <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: 1.6, marginTop: "var(--space-md)" }}>
              Track share of voice trends and benchmark your AI visibility against competitors.
            </p>
          </div>
        </div>
      </section>

      {/* Comparison Section */}
      <section
        style={{
          maxWidth: "1200px",
          margin: "var(--space-3xl) auto",
          padding: "var(--space-3xl) var(--space-xl)",
          background: "linear-gradient(135deg, var(--surface) 0%, rgba(15, 52, 96, 0.03) 100%)",
          borderRadius: "var(--radius-xl)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "var(--space-3xl)" }}>
          <h2
            style={{
              fontSize: "36px",
              fontWeight: 700,
              color: "var(--brand)",
            }}
          >
            More Than Just Social Listening
          </h2>
          <p style={{ color: "var(--muted)", marginTop: "var(--space-lg)", fontSize: "18px" }}>
            RedditFlow evolved beyond Reddit. Monitor AI responses, track citations, and compete for visibility where
            your customers actually search.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "var(--space-2xl)",
          }}
        >
          <div>
            <h3
              style={{
                fontSize: "18px",
                fontWeight: 600,
                color: "var(--muted)",
                marginBottom: "var(--space-lg)",
              }}
            >
              Traditional Tools
            </h3>
            <ul style={{ listStyle: "none" }}>
              <li
                style={{
                  padding: "var(--space-md) 0",
                  borderBottom: "1px solid var(--border)",
                  color: "var(--muted)",
                  fontSize: "14px",
                }}
              >
                ✓ Social media monitoring
              </li>
              <li
                style={{
                  padding: "var(--space-md) 0",
                  borderBottom: "1px solid var(--border)",
                  color: "var(--muted)",
                  fontSize: "14px",
                }}
              >
                ✓ Manual Reddit searches
              </li>
              <li
                style={{
                  padding: "var(--space-md) 0",
                  borderBottom: "1px solid var(--border)",
                  color: "var(--muted)",
                  fontSize: "14px",
                }}
              >
                ✓ Sentiment analysis
              </li>
            </ul>
          </div>

          <div>
            <h3
              style={{
                fontSize: "18px",
                fontWeight: 600,
                color: "var(--brand)",
                marginBottom: "var(--space-lg)",
              }}
            >
              RedditFlow (AI Edition)
            </h3>
            <ul style={{ listStyle: "none" }}>
              <li
                style={{
                  padding: "var(--space-md) 0",
                  borderBottom: "1px solid var(--border)",
                  color: "var(--brand)",
                  fontSize: "14px",
                  fontWeight: 600,
                }}
              >
                ✓ AI visibility tracking
              </li>
              <li
                style={{
                  padding: "var(--space-md) 0",
                  borderBottom: "1px solid var(--border)",
                  color: "var(--brand)",
                  fontSize: "14px",
                  fontWeight: 600,
                }}
              >
                ✓ Citation intelligence
              </li>
              <li
                style={{
                  padding: "var(--space-md) 0",
                  borderBottom: "1px solid var(--border)",
                  color: "var(--brand)",
                  fontSize: "14px",
                  fontWeight: 600,
                }}
              >
                ✓ Share of voice & benchmarks
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section
        style={{
          maxWidth: "800px",
          margin: "var(--space-3xl) auto",
          padding: "var(--space-3xl) var(--space-xl)",
          textAlign: "center",
          background: "linear-gradient(135deg, var(--brand) 0%, var(--blue) 100%)",
          borderRadius: "var(--radius-xl)",
          color: "white",
        }}
      >
        <h2 style={{ fontSize: "36px", fontWeight: 700, marginBottom: "var(--space-md)" }}>
          Ready to Own Your AI Visibility?
        </h2>
        <p style={{ fontSize: "18px", lineHeight: 1.6, marginBottom: "var(--space-2xl)", opacity: 0.9 }}>
          Completely free. No credit card required. Get insights in 2 minutes.
        </p>
        <div style={{ display: "flex", gap: "var(--space-lg)", justifyContent: "center", flexWrap: "wrap" }}>
          <Link
            href="/register"
            className="primary-button"
            style={{
              padding: "12px 32px",
              fontSize: "16px",
              fontWeight: 600,
              background: "var(--accent)",
              color: "white",
            }}
          >
            Get Started Free
          </Link>
          <a
            href="mailto:hello@redditflow.ai"
            className="secondary-button"
            style={{
              padding: "12px 32px",
              fontSize: "16px",
              fontWeight: 600,
              background: "rgba(255, 255, 255, 0.1)",
              color: "white",
              border: "1px solid rgba(255, 255, 255, 0.3)",
            }}
          >
            Schedule Demo
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--border)",
          marginTop: "var(--space-3xl)",
          padding: "var(--space-3xl) var(--space-xl)",
          background: "var(--surface)",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "var(--space-2xl)",
            marginBottom: "var(--space-3xl)",
          }}
        >
          <div>
            <h4 style={{ fontWeight: 700, marginBottom: "var(--space-lg)", color: "var(--brand)" }}>Product</h4>
            <ul style={{ listStyle: "none" }}>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <Link href="/app/visibility" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  AI Visibility
                </Link>
              </li>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <Link href="/app/discovery" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  Discovery
                </Link>
              </li>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <Link href="/app/content" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  Content Studio
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 style={{ fontWeight: 700, marginBottom: "var(--space-lg)", color: "var(--brand)" }}>Company</h4>
            <ul style={{ listStyle: "none" }}>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <a href="#" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  About
                </a>
              </li>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <a href="#" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  Blog
                </a>
              </li>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <a href="#" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  Careers
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h4 style={{ fontWeight: 700, marginBottom: "var(--space-lg)", color: "var(--brand)" }}>Legal</h4>
            <ul style={{ listStyle: "none" }}>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <a href="#" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  Privacy Policy
                </a>
              </li>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <a href="#" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  Terms of Service
                </a>
              </li>
              <li style={{ marginBottom: "var(--space-md)" }}>
                <a href="#" style={{ color: "var(--muted)", fontSize: "14px" }}>
                  Contact
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div
          style={{
            borderTop: "1px solid var(--border)",
            paddingTop: "var(--space-2xl)",
            textAlign: "center",
            color: "var(--muted)",
            fontSize: "14px",
          }}
        >
          <p>&copy; 2026 RedditFlow. All rights reserved. | Monitoring AI visibility for your brand.</p>
        </div>
      </footer>
    </main>
  );
}
