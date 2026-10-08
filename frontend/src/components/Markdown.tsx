import ReactMarkdown from "react-markdown";

// Chat answers are Markdown written by a model. Only the handful of elements an answer
// needs are rendered; anything else (links, images, raw HTML, headings) is reduced to its
// text, so a reply can never inject a link or markup into the page.
const ALLOWED = ["p", "strong", "em", "ul", "ol", "li", "code", "br"];

const BULLET = /^\s*([-*]|\d+[.)])\s/;

/** Answers write one idea per line ("**Example:** …", then "**Tip:** …") with single line
 *  breaks, which Markdown would merge into one paragraph, or fold into the bullet above
 *  (lazy continuation). Each such line becomes a paragraph of its own. */
function separateTrailingLines(text: string): string {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  return lines
    .map((line, i) =>
      i > 0 && line.trim() && lines[i - 1].trim() && !BULLET.test(line) && !/^\s/.test(line)
        ? `\n${line}`
        : line,
    )
    .join("\n");
}

export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown allowedElements={ALLOWED} unwrapDisallowed skipHtml>
        {separateTrailingLines(children)}
      </ReactMarkdown>
    </div>
  );
}
