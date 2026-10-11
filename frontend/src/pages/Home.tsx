import { Link } from "react-router-dom";
import { Markdown } from "../components/Markdown";

const SAMPLE = "/samples/maharashtra-leave-license-mumbai";

// Lines of the illustrated agreement: [width %, highlight]. "red"/"yellow" light up as the
// scan passes, the way a real review appears.
const LINES: [number, string?][] = [
  [92], [88], [95], [60],
  [94, "red"], [90, "red"], [72, "red"],
  [91], [86], [54],
  [93], [89, "yellow"], [77, "yellow"],
  [90], [84], [66],
];

const LAWS = [
  "Maharashtra Rent Control Act, 1999",
  "Delhi Rent Control Act, 1958",
  "Transfer of Property Act, 1882",
  "Registration Act, 1908",
];

const PROBLEMS = [
  {
    title: "Lock-ins and exit penalties",
    body: "An 11-month lock-in, a month's rent as penalty, or a notice period that only binds you.",
  },
  {
    title: "Deposits with vague deductions",
    body: "“Amounts lawfully due” and “damages” decide how much of your deposit comes back.",
  },
  {
    title: "Termination without notice",
    body: "Clauses letting the landlord “re-enter forthwith” can skip the notice the law may require.",
  },
];

// Online agreement services (drafting, e-stamping) don't review an existing agreement,
// so those cells say "not offered" rather than claiming they do it badly.
type Mark = "yes" | "partly" | "no" | "na";
const COMPARISON: { feature: string; marks: [Mark, Mark, Mark, Mark] }[] = [
  { feature: "Shows the risky clauses on your own document, scans included", marks: ["yes", "no", "na", "yes"] },
  { feature: "Checks your state's rent law and links the official text", marks: ["yes", "partly", "na", "yes"] },
  { feature: "Answers questions about your exact clauses", marks: ["yes", "partly", "na", "yes"] },
  { feature: "Checked so it never invents a law, an amount or a verdict", marks: ["yes", "no", "na", "yes"] },
  { feature: "Ready in minutes, free", marks: ["yes", "yes", "no", "no"] },
];
const COLUMNS = ["LeaseLens", "General AI chatbot", "Online agreement services", "A lawyer"];

const USES = [
  {
    title: "Moving to a new city",
    body: "Your broker sends a 6-page agreement the night before. Know what to push back on.",
    ask: "How much notice do I have to give before moving out?",
  },
  {
    title: "Renewing your agreement",
    body: "Check what changed: the rent increase, the lock-in, who pays for maintenance.",
    ask: "Can the rent be increased during the term?",
  },
  {
    title: "Getting your deposit back",
    body: "See exactly what your agreement allows the landlord to deduct, and when it's due.",
    ask: "When do I get my security deposit back?",
  },
];

const FAQS = [
  {
    q: "Is this legal advice?",
    a: "No. LeaseLens points out clauses worth questioning and explains them in plain language, with the law it checked. It never tells you whether a clause is legal or enforceable. For decisions that matter, talk to a lawyer: you'll go in knowing exactly what to ask.",
  },
  {
    q: "Which states are covered?",
    a: "Rent law checks cover Maharashtra and Delhi, plus central law (the Transfer of Property Act and the Registration Act). Agreements from any other state still get every clause rated, explained and highlighted, and are clearly marked as having no state law check.",
  },
  {
    q: "What files can I upload?",
    a: "A PDF (typed, or scanned), or a photo of each page as PNG or JPG, up to 20 MB. Scanned pages and photos are read with OCR, and the highlights are placed on the image itself.",
  },
  {
    q: "What happens to my agreement?",
    a: "There's no account. Only the browser you uploaded from can open it, and the text and review are permanently deleted after 24 hours, or immediately with “Delete”. The file itself stays in your browser; our server keeps only the extracted text. Clause text is sent to an AI provider to write explanations and answers.",
  },
  {
    q: "How accurate is it?",
    a: "Clause splitting and law matching are rule-based and tested on agreements in nine states' formats. The ratings and explanations come from an AI model, and every answer is checked in code before you see it: no invented laws, no invented figures, no verdicts. It can still miss things, so treat it as a careful first read, not the last word.",
  },
  {
    q: "Does it cost anything?",
    a: "No. It's free to use, with fair-use limits per hour to keep it available for everyone.",
  },
];

const MARKS: Record<Mark, [string, string]> = {
  yes: ["✓", "Yes"],
  partly: ["~", "Varies"],
  no: ["✕", "No"],
  na: ["—", "Not offered"],
};

export function Home() {
  return (
    <div className="home">
      {/* ---------- Hero ---------- */}
      <section className="home-hero">
        <div className="home-hero-copy">
          <span className="hero-pill">
            <i /> Built for Indian rental agreements
          </span>
          <h1>
            Know what you're signing <em>before you sign it.</em>
          </h1>
          <p>
            Upload your rent agreement. LeaseLens highlights the clauses worth questioning right on
            the page, checks them against your state's rent law, and answers your questions in plain
            language.
          </p>
          <div className="hero-actions">
            <Link className="primary-button large" to="/review">
              Check my agreement — free
            </Link>
            <Link className="secondary-button large" to={SAMPLE}>
              See a live example
            </Link>
          </div>
          <ul className="trust-row">
            <li>No sign-up</li>
            <li>PDF, scan or photo</li>
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

      {/* ---------- Grounded in ---------- */}
      <section className="law-strip" aria-label="Laws LeaseLens checks against">
        <span>Checked against the actual text of</span>
        <ul>
          {LAWS.map((law) => (
            <li key={law}>⚖ {law}</li>
          ))}
        </ul>
      </section>

      {/* ---------- Problem ---------- */}
      <section className="home-section">
        <div className="section-intro">
          <span className="eyebrow">THE PROBLEM</span>
          <h2>The landlord's side writes the agreement. The risk hides in a few clauses.</h2>
          <p>
            Most tenants sign a 5–10 page agreement after a quick skim. The clauses that cost money
            later look like standard wording.
          </p>
        </div>
        <div className="problem-grid">
          {PROBLEMS.map((p) => (
            <article key={p.title} className="problem-card">
              <h3>{p.title}</h3>
              <p>{p.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ---------- Product tour ---------- */}
      <section className="home-section tour">
        <div className="section-intro centered">
          <span className="eyebrow">HOW LEASELENS HELPS</span>
          <h2>A careful first read of your agreement, in minutes</h2>
        </div>

        <div className="tour-row">
          <div className="tour-copy">
            <span className="tour-number">01</span>
            <h3>See it on your own document</h3>
            <p>
              No copied-out text to compare. Risky clauses are highlighted on your actual pages, even
              on a scan or a phone photo, so you can see exactly where they are.
            </p>
            <ul className="tour-points">
              <li>Works with any state's format, numbered or not</li>
              <li>Red to question, amber worth a look, the rest left clear</li>
            </ul>
          </div>
          <div className="tour-visual">
            <div className="mini-page">
              <p>
                <span>9. REGISTRATION.</span> This Agreement shall be registered by the Licensor with
                the office of the Sub-Registrar of Assurances…
              </p>
              <p className="mini-hl mini-yellow">
                <span>10. TERMINATION.</span> Either party may terminate this Agreement by giving one
                month's prior written notice… the Licensor shall be entitled to terminate this
                Agreement forthwith and re-enter the said premises.
              </p>
              <p>
                <span>11. INSPECTION.</span> The Licensor shall be entitled to inspect the said
                premises at reasonable times upon giving 24 hours' prior notice…
              </p>
            </div>
          </div>
        </div>

        <div className="tour-row reverse">
          <div className="tour-copy">
            <span className="tour-number">02</span>
            <h3>Every flag explained, with the law behind it</h3>
            <p>
              Each clause is explained in plain words: what it says, and why it matters to you. Where
              your state's rent law speaks to it, you get the provision and a link to its official
              text.
            </p>
            <ul className="tour-points">
              <li>Only provisions actually looked up are ever cited</li>
              <li>Clauses that affect each other are linked</li>
            </ul>
          </div>
          <div className="tour-visual">
            <div className="mini-finding">
              <div className="mini-finding-head">
                <span className="risk-dot yellow" />
                <div>
                  <strong>Termination</strong>
                  <small>Clause 10 · Worth a look</small>
                </div>
              </div>
              <div className="finding-why">
                <span>Why it matters</span>
                <p>
                  After two missed payments the landlord could end the agreement immediately, with no
                  notice or time to pay the arrears.
                </p>
              </div>
              <div className="finding-law">
                <strong>⚖ Section 15, Maharashtra Rent Control Act, 1999</strong>
                <p>Requires a written demand and 90 days before a suit for non-payment.</p>
                <span className="fake-link">Official source ↗</span>
              </div>
            </div>
          </div>
        </div>

        <div className="tour-row">
          <div className="tour-copy">
            <span className="tour-number">03</span>
            <h3>Ask anything, get answers with sources</h3>
            <p>
              “When do I get my deposit back?” Answers come only from your agreement and your state's
              law, with a worked example and the exact clauses they rely on.
            </p>
            <ul className="tour-points">
              <li>One tap: explain simply, why this rating, what to negotiate</li>
              <li>Says so when your agreement doesn't cover something</li>
            </ul>
          </div>
          <div className="tour-visual">
            <div className="mini-chat">
              <div className="msg-bubble">When do I get my deposit back?</div>
              <div className="preview-answer">
                <span className="assistant-avatar" aria-hidden>
                  L
                </span>
                <div>
                  <Markdown>
                    {`You should get it back **within 15 days of vacating**, minus amounts lawfully due.
- **Amount:** Rs. 2,00,000, interest-free.
- **Deductions:** only amounts lawfully due, like unpaid fees.
**Example:** move out on 28th February 2027 with nothing owed, and the full Rs. 2,00,000 is due within 15 days.`}
                  </Markdown>
                  <div className="chips">
                    <span className="chip">§ Clause 6 · Security deposit</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- Why different ---------- */}
      <section className="home-section">
        <div className="section-intro centered">
          <span className="eyebrow">WHY LEASELENS</span>
          <h2>Not another chatbot. A reviewer that shows its work.</h2>
          <p>
            Online agreement services draft and e-stamp agreements; they don't review yours. General
            AI chatbots summarise, but can quote the wrong state's law and can't point to your page.
          </p>
        </div>
        <div className="novelty-grid">
          <article>
            <span>01</span>
            <h3>On your original page</h3>
            <p>Every clause is located on the document you uploaded, scans and photos included. Proof, not a summary.</p>
          </article>
          <article>
            <span>02</span>
            <h3>Indian rent law, cited properly</h3>
            <p>Matched against a curated set of provisions, each linked to its official source and date checked.</p>
          </article>
          <article>
            <span>03</span>
            <h3>Checked before you see it</h3>
            <p>Code, not just instructions, blocks invented laws, invented amounts and “this is illegal” verdicts.</p>
          </article>
        </div>

        <div className="compare" role="table" aria-label="How LeaseLens compares">
          <div className="compare-row compare-head" role="row">
            <span role="columnheader" />
            {COLUMNS.map((c, i) => (
              <span key={c} role="columnheader" className={i === 0 ? "ours" : ""}>
                {c}
              </span>
            ))}
          </div>
          {COMPARISON.map((row) => (
            <div key={row.feature} className="compare-row" role="row">
              <span role="rowheader">{row.feature}</span>
              {row.marks.map((mark, i) => (
                <span key={i} role="cell" className={`mark mark-${mark} ${i === 0 ? "ours" : ""}`}>
                  <i aria-hidden>{MARKS[mark][0]}</i>
                  <em>{MARKS[mark][1]}</em>
                </span>
              ))}
            </div>
          ))}
        </div>
        <p className="compare-note">
          A lawyer remains the right call for anything serious. LeaseLens helps you know what to ask.
        </p>
      </section>

      {/* ---------- How it works ---------- */}
      <section className="home-section">
        <div className="section-intro centered">
          <span className="eyebrow">HOW IT WORKS</span>
          <h2>Three steps, about two minutes</h2>
        </div>
        <ol className="steps-simple">
          <li>
            <span className="step-icon" aria-hidden>↑</span>
            <div>
              <h3>Upload</h3>
              <p>Drop in a PDF, a scan or phone photos. No account needed.</p>
            </div>
          </li>
          <li>
            <span className="step-icon" aria-hidden>◐</span>
            <div>
              <h3>Confirm your state</h3>
              <p>We detect it from the agreement; you confirm before any law is checked.</p>
            </div>
          </li>
          <li>
            <span className="step-icon" aria-hidden>✦</span>
            <div>
              <h3>Review and ask</h3>
              <p>Go through the highlights, then ask about anything that's unclear.</p>
            </div>
          </li>
        </ol>
      </section>

      {/* ---------- Use cases ---------- */}
      <section className="home-section">
        <div className="section-intro">
          <span className="eyebrow">WHEN TO USE IT</span>
          <h2>Before the moments that cost money</h2>
        </div>
        <div className="use-grid">
          {USES.map((u) => (
            <article key={u.title} className="use-card">
              <h3>{u.title}</h3>
              <p>{u.body}</p>
              <span className="use-ask">“{u.ask}”</span>
            </article>
          ))}
        </div>
      </section>

      {/* ---------- Trust ---------- */}
      <section className="home-section trust-grid">
        <article>
          <span className="trust-icon" aria-hidden>🔒</span>
          <h3>Private by design</h3>
          <ul className="check-list">
            <li>No account, no email, no phone number</li>
            <li>Only your browser can open your agreement</li>
            <li>Permanently deleted within 24 hours, or right away</li>
            <li>Your file stays on your device; we keep only the text</li>
          </ul>
        </article>
        <article>
          <span className="trust-icon" aria-hidden>⚖</span>
          <h3>Careful by design</h3>
          <ul className="check-list">
            <li>Never says a clause is legal or illegal</li>
            <li>Cites only provisions it actually looked up</li>
            <li>Won't answer from another state's law</li>
            <li>Says “the agreement doesn't say” instead of guessing</li>
          </ul>
        </article>
      </section>

      {/* ---------- FAQ ---------- */}
      <section className="home-section faq">
        <div className="section-intro centered">
          <span className="eyebrow">QUESTIONS</span>
          <h2>Frequently asked</h2>
        </div>
        <div className="faq-list">
          {FAQS.map((f) => (
            <details key={f.q}>
              <summary>{f.q}</summary>
              <p>{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="cta-band">
        <div>
          <h2>Signing soon? Read it properly first.</h2>
          <p>Free, private, and ready in about two minutes.</p>
        </div>
        <Link className="primary-button large" to="/review">
          Check my agreement
        </Link>
      </section>
    </div>
  );
}
