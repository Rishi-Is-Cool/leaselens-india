import { Link } from "react-router-dom";

const SAMPLE = "/samples/maharashtra-leave-license-mumbai";

const STEPS = [
  { icon: "↑", title: "Upload", body: "A PDF, a scan or a phone photo." },
  { icon: "◐", title: "See the highlights", body: "Risky clauses lit up on your own document." },
  { icon: "✦", title: "Ask anything", body: "Plain answers, with the clause and the law." },
];

// Lines of the illustrated agreement: [width %, highlight] — "red"/"yellow" light up as the
// scan passes, the way a real review appears.
const LINES: [number, string?][] = [
  [92], [88], [95], [60],
  [94, "red"], [90, "red"], [72, "red"],
  [91], [86], [54],
  [93], [89, "yellow"], [77, "yellow"],
  [90], [84], [66],
];

export function Home() {
  return (
    <div className="home home-simple">
      <section className="home-hero">
        <div className="home-hero-copy">
          <h1>
            Know what you're signing <em>before you sign it.</em>
          </h1>
          <p>Upload your rental agreement. We highlight the clauses worth questioning, right on the page.</p>
          <div className="hero-actions">
            <Link className="primary-button large" to="/review">
              Check my agreement
            </Link>
            <Link className="secondary-button large" to={SAMPLE}>
              See an example
            </Link>
          </div>
          <ul className="trust-row">
            <li>Free</li>
            <li>No sign-up</li>
            <li>Deleted in 24 hours</li>
          </ul>
        </div>

        <div className="hero-demo" aria-hidden>
          <div className="demo-paper">
            <div className="demo-file">
              <span>▤ rent_agreement.pdf</span>
              <span className="demo-status" />
            </div>
            <div className="demo-heading" />
            {LINES.map(([width, tone], i) => (
              <div key={i} className={`demo-line ${tone ? `demo-${tone}` : ""}`} style={{ width: `${width}%` }} />
            ))}
            <div className="demo-scan" />
          </div>
          <div className="demo-card demo-card-red">
            <span className="risk-dot red" />
            <div>
              <strong>Termination</strong>
              <small>Needs attention · no notice before eviction</small>
            </div>
          </div>
          <div className="demo-card demo-card-yellow">
            <span className="risk-dot yellow" />
            <div>
              <strong>Lock-in period</strong>
              <small>Worth a look · penalty if you leave early</small>
            </div>
          </div>
        </div>
      </section>

      <ol className="steps-simple">
        {STEPS.map((step) => (
          <li key={step.title}>
            <span className="step-icon" aria-hidden>
              {step.icon}
            </span>
            <div>
              <h2>{step.title}</h2>
              <p>{step.body}</p>
            </div>
          </li>
        ))}
      </ol>

      <p className="home-footnote">
        Checks Maharashtra and Delhi rent law, with links to the official text.{" "}
        <Link to="/how-it-works">How it works</Link>
      </p>
    </div>
  );
}
