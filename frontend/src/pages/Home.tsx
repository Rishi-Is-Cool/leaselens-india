import { Link } from "react-router-dom";
import { Markdown } from "../components/Markdown";

const SAMPLE = "/samples/maharashtra-leave-license-mumbai";

const STEPS = [
  {
    title: "Upload",
    body: "A PDF, or a scan or phone photo of the agreement. Scanned pages are read with OCR.",
  },
  {
    title: "Every clause, separated",
    body: "The agreement is split into its individual clauses, so nothing hides in a wall of text.",
  },
  {
    title: "Rated and checked",
    body: "Each clause is rated by how much attention it deserves and matched to your state's rental law.",
  },
  {
    title: "Ask anything",
    body: "Get answers about your own agreement, with the clauses and laws they come from.",
  },
];

const FEATURES = [
  {
    icon: "◐",
    title: "Clause-by-clause ratings",
    body: "Looks standard, Worth a look or Needs attention: see straight away which terms to question before you sign.",
  },
  {
    icon: "⚖",
    title: "The actual law, linked",
    body: "Maharashtra and Delhi rent control law and central law, each provision linked to its official source with the date we last checked it.",
  },
  {
    icon: "¶",
    title: "Plain-language explanations",
    body: "What each clause says and why it matters, written for tenants, not lawyers.",
  },
  {
    icon: "✦",
    title: "Answers about your lease",
    body: "Ask “when do I get my deposit back?” and get an answer from your own agreement, with an example and its sources.",
  },
  {
    icon: "↔",
    title: "Clauses to read together",
    body: "Finds terms that change each other's meaning, like a notice clause and the deposit deductions it triggers.",
  },
  {
    icon: "◇",
    title: "Private by design",
    body: "No account. Only your browser can open your upload, and it is deleted within 24 hours, or right away.",
  },
];

const DEMO_ANSWER = `You should get your deposit back **within 15 days of vacating**, minus any amounts lawfully due.
- **Amount:** Rs. 2,00,000, interest-free and refundable.
- **Deductions:** only amounts lawfully due, such as unpaid licence fees.
**Example:** if you move out on 28th February 2027 with nothing owed, the full Rs. 2,00,000 should come back within 15 days.`;

export function Home() {
  return (
    <div className="home">
      <section className="home-hero">
        <div className="home-hero-copy">
          <span className="eyebrow">FOR TENANTS IN INDIA</span>
          <h1>
            Know what your rental agreement says <em>before you sign it.</em>
          </h1>
          <p>
            LeaseLens reads your agreement clause by clause, flags the terms worth questioning,
            checks them against your state's rent law and answers your questions in plain
            language.
          </p>
          <div className="hero-actions">
            <Link className="primary-button large" to="/review">
              Review my lease
            </Link>
            <Link className="secondary-button large" to={SAMPLE}>
              See a sample review
            </Link>
          </div>
          <ul className="trust-row">
            <li>Free</li>
            <li>No sign-up</li>
            <li>Deleted within 24 hours</li>
          </ul>
        </div>

        <div className="home-hero-preview" aria-hidden>
          <div className="preview-card">
            <div className="preview-head">
              <span className="risk-dot red" /> Clause 10 · Termination
              <span className="preview-badge">Needs attention</span>
            </div>
            <p className="preview-quote">
              “…in the event the Licensee defaults in payment of the license fee for two
              consecutive months, the Licensor shall be entitled to terminate this Agreement
              forthwith and re-enter the said premises.”
            </p>
            <div className="preview-why">
              <span>Why this matters</span>
              There is no notice period or time to pay arrears before you could be asked to leave.
            </div>
            <div className="preview-law">⚖ Section 15, Maharashtra Rent Control Act, 1999 ↗</div>
          </div>
          <div className="preview-chat">
            <div className="msg-bubble">When do I get my deposit back?</div>
            <div className="preview-answer">
              <span className="assistant-avatar" aria-hidden>
                L
              </span>
              <div>
                <Markdown>{DEMO_ANSWER}</Markdown>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="section-intro">
          <span className="eyebrow">HOW IT WORKS</span>
          <h2>From a dense document to clear answers in a few minutes</h2>
        </div>
        <ol className="steps">
          {STEPS.map((step, i) => (
            <li key={step.title}>
              <span className="step-number">{i + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="home-section">
        <div className="section-intro">
          <span className="eyebrow">WHAT YOU GET</span>
          <h2>Everything you'd want to ask a lawyer about, laid out first</h2>
        </div>
        <div className="feature-grid">
          {FEATURES.map((f) => (
            <article key={f.title} className="feature">
              <span className="feature-icon" aria-hidden>
                {f.icon}
              </span>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="home-section safety">
        <div>
          <span className="eyebrow">BUILT TO BE CAREFUL</span>
          <h2>It tells you what to look at, never what's “legal”</h2>
          <p>
            Every answer is checked before you see it. LeaseLens won't give a legal verdict, cite a
            law it didn't actually look up, or invent an amount or date your agreement doesn't
            contain. It also won't answer from another state's law.
          </p>
          <Link className="text-link" to="/how-it-works">
            How LeaseLens works →
          </Link>
        </div>
        <ul className="safety-list">
          <li>
            <strong>Sources on every answer</strong>
            <span>Each answer links to the clauses and official provisions it used.</span>
          </li>
          <li>
            <strong>Your state, confirmed by you</strong>
            <span>We guess the state from the agreement, and you confirm it before anything is checked.</span>
          </li>
          <li>
            <strong>Honest when unsure</strong>
            <span>If the agreement doesn't say, the answer says so instead of guessing.</span>
          </li>
        </ul>
      </section>

      <section className="cta-band">
        <div>
          <h2>Signing soon? Read it properly first.</h2>
          <p>It takes a couple of minutes, and nothing is kept.</p>
        </div>
        <Link className="primary-button large" to="/review">
          Review my lease
        </Link>
      </section>
    </div>
  );
}
