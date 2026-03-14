import Link from "next/link";

export default function MarketingPage() {
  return (
    <main className="site-shell hero">
      <div className="hero-card">
        <div className="hero-grid">
          <div className="item-list">
            <div className="eyebrow">RedditFlow</div>
            <h1>Find Reddit posts where your product can truly help.</h1>
            <p className="kicker">
              RedditFlow gives you a simple path: add your product, describe your customers, find matching Reddit posts,
              and draft helpful replies without turning into spam.
            </p>
            <div className="action-row">
              <Link href="/register" className="primary-button">
                Start free
              </Link>
              <Link href="/login" className="secondary-button">
                Sign In
              </Link>
            </div>
            <div className="badge-row">
              <div className="badge">Simple step-by-step setup</div>
              <div className="badge">Find posts and communities</div>
              <div className="badge">Manual posting, AI help</div>
            </div>
          </div>
          <div className="feature-card">
            <div className="eyebrow">How it works</div>
            <h2>Start simple. Grow when you need more.</h2>
            <p>
              The main workflow is built for regular business owners, not just technical teams. Advanced settings still
              exist, but they stay out of your way.
            </p>
            <div className="stats-row">
              <div className="stat-card">
                <div className="meta-label">Step 1</div>
                <strong>Add your product</strong>
              </div>
              <div className="stat-card">
                <div className="meta-label">Step 2</div>
                <strong>Find matching posts</strong>
              </div>
              <div className="stat-card">
                <div className="meta-label">Step 3</div>
                <strong>Write a helpful reply</strong>
              </div>
            </div>
          </div>
        </div>

        <section className="section-grid">
          <div className="feature-card">
            <div className="eyebrow">Your product</div>
            <h3>Fill details from your website</h3>
            <p>Paste your site and let RedditFlow draft the first version for you.</p>
          </div>
          <div className="feature-card">
            <div className="eyebrow">Find posts</div>
            <h3>See the best matches first</h3>
            <p>Use customer search words, good-fit communities, and a simple match score.</p>
          </div>
          <div className="feature-card">
            <div className="eyebrow">Write replies</div>
            <h3>Stay human, just faster</h3>
            <p>Generate a reply draft, edit it, then post manually when you are ready.</p>
          </div>
        </section>

        <section className="pricing-grid">
          <div className="price-card">
            <div className="eyebrow">Free</div>
            <div className="price">$0</div>
            <p>One project, ten active keywords, five active subreddits.</p>
          </div>
          <div className="price-card">
            <div className="eyebrow">Starter</div>
            <div className="price">$79</div>
            <p>Three projects, broader scanning limits, and a more serious daily workflow.</p>
          </div>
          <div className="price-card">
            <div className="eyebrow">Growth</div>
            <div className="price">$199</div>
            <p>Team collaboration, webhook operations, and higher discovery ceilings.</p>
          </div>
        </section>
      </div>
    </main>
  );
}
