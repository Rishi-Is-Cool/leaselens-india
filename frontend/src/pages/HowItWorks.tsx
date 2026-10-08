import { Link } from "react-router-dom";

const PIPELINE = [
  {
    title: "Reading the document",
    body: "Text PDFs are read directly. Scanned pages and photos go through Tesseract OCR page by page, so a document mixing both still works.",
  },
  {
    title: "Finding the clauses",
    body: "A rule-based segmenter uses the page layout, clause numbering and headings to separate every clause, and keeps the title block and signature lines apart from the terms.",
  },
  {
    title: "Rating each clause",
    body: "An AI model rates every clause as Looks standard, Worth a look or Needs attention. If the AI provider is unavailable, a classifier trained on labelled Indian lease clauses takes over.",
  },
  {
    title: "Checking the law",
    body: "Each clause is matched against a curated knowledge base of 28 provisions: the Maharashtra Rent Control Act 1999, the Delhi Rent Control Act 1958 and central law, such as the Transfer of Property Act 1882 and the Registration Act 1908. The search is deterministic, not generated.",
  },
  {
    title: "Explaining it",
    body: "Plain-language explanations are written from the clause text and the provisions retrieved for it, and nothing else.",
  },
  {
    title: "Connecting clauses",
    body: "Similar clauses are shortlisted, then the AI confirms which pairs genuinely change how each other should be read.",
  },
];

const GUARDRAILS = [
  ["No legal verdicts", "Answers that call anything legal, illegal, valid or enforceable are rewritten, or replaced with a safe answer."],
  ["Only real citations", "A law is shown only if it was retrieved for your agreement. Any other law the AI mentions is removed."],
  ["No invented figures", "Amounts, dates and periods must appear in your agreement. If one doesn't, the answer is rewritten."],
  ["One state at a time", "Questions about another state's law are declined before the AI is even asked."],
];

const TEAM = [
  {
    name: "Maitry Mahesh Mohite",
    handle: "maitry-mohite",
    role: "Project lead · clause risk classifier",
  },
  {
    name: "Tanvi Yerram",
    handle: "tanviyerram08",
    role: "Statute knowledge base · law citations",
  },
  {
    name: "Rishikesh Patil",
    handle: "Rishi-Is-Cool",
    role: "Document reading & OCR · explanations · chat · web app",
  },
];

/** /how-it-works — the method, the guardrails, privacy, coverage and the team. */
export function HowItWorks() {
  return (
    <div className="page page-narrow prose-page">
      <header className="page-header">
        <span className="eyebrow">HOW IT WORKS</span>
        <h1>What happens to your agreement</h1>
        <p>
          LeaseLens combines rule-based document processing, a curated legal knowledge base and
          an AI model, with checks on everything the AI writes.
        </p>
      </header>

      <section className="prose-section">
        <h2>The review, step by step</h2>
        <ol className="timeline">
          {PIPELINE.map((step) => (
            <li key={step.title}>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="prose-section">
        <h2>Guardrails on every answer</h2>
        <p>
          Instructions to an AI are not a guarantee, so LeaseLens checks each answer in code
          before showing it.
        </p>
        <div className="guardrail-grid">
          {GUARDRAILS.map(([title, body]) => (
            <article key={title} className="card">
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="prose-section" id="privacy">
        <h2>Privacy</h2>
        <ul className="check-list">
          <li>No accounts. Your browser gets a random ID, and only that browser can open what it uploaded.</li>
          <li>Every upload is permanently deleted after 24 hours, or immediately with “Delete now”, along with its review.</li>
          <li>Clause text is sent to an AI provider (Groq) to write explanations and answer questions.</li>
          <li>Uploads and questions are rate-limited per visitor to keep the free service available.</li>
        </ul>
      </section>

      <section className="prose-section">
        <h2>Coverage</h2>
        <p>
          Law checks cover <strong>Maharashtra</strong> and <strong>Delhi</strong>, plus central
          law. Agreements from other states still get clause splitting, ratings, explanations and
          chat, clearly labelled as having no state law check, and are never answered from the
          AI's general knowledge.
        </p>
      </section>

      <section className="prose-section">
        <h2>Not legal advice</h2>
        <p>
          LeaseLens flags potential concerns and explains them. It does not tell you whether a
          clause is enforceable. Laws change and situations differ, so check anything important
          with a qualified lawyer before acting on it.
        </p>
      </section>

      <section className="prose-section" id="team">
        <h2>Team</h2>
        <div className="team-grid">
          {TEAM.map((person) => (
            <a
              key={person.handle}
              className="card team-card"
              href={`https://github.com/${person.handle}`}
              target="_blank"
              rel="noreferrer"
            >
              <img src={`https://github.com/${person.handle}.png?size=96`} alt="" loading="lazy" />
              <div>
                <strong>{person.name}</strong>
                <span>{person.role}</span>
              </div>
            </a>
          ))}
        </div>
      </section>

      <section className="cta-band">
        <div>
          <h2>Try it on your agreement</h2>
          <p>Free, no sign-up, deleted within 24 hours.</p>
        </div>
        <Link className="primary-button" to="/review">
          Review my lease
        </Link>
      </section>
    </div>
  );
}
