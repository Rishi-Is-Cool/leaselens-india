import { useEffect, useMemo, useRef, useState } from "react";
import type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";
import type { Highlights, RiskLabel } from "../api";
import { RISK_WORDING } from "../samples";

export type DocumentSource = { kind: "pdf" | "image"; data: Blob | string };
export type Focus = { clauseId: string; nonce: number };

type Props = {
  source: DocumentSource;
  highlights: Highlights;
  /** Rating per clause; clauses without one (review not run yet) are not coloured. */
  risks: Record<string, RiskLabel>;
  selected: string | null;
  focus: Focus | null;
  scanning?: boolean;
  onSelect?: (clauseId: string) => void;
  onUnavailable?: () => void;
};

// Boxes are drawn slightly larger than the words they cover, like a highlighter stroke.
const PAD_X = 0.004;
const PAD_Y = 0.003;

let pdfjsPromise: Promise<typeof import("pdfjs-dist")> | null = null;

/** PDF.js is large, so it loads only when a document is actually shown. */
function loadPdfjs() {
  pdfjsPromise ??= Promise.all([import("pdfjs-dist"), import("pdfjs-dist/build/pdf.worker.min.mjs?url")]).then(
    ([pdfjs, worker]) => {
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
      return pdfjs;
    },
  );
  return pdfjsPromise;
}

async function bytes(data: Blob | string): Promise<ArrayBuffer> {
  if (typeof data !== "string") return data.arrayBuffer();
  const response = await fetch(data);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.arrayBuffer();
}

/** The original document, page by page, with each clause highlighted where it appears. */
export function DocumentViewer({ source, highlights, risks, selected, focus, scanning, onSelect, onUnavailable }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    // Rounded so tiny layout jitter doesn't re-render every page.
    const measure = (width: number) => setWidth(Math.round(width / 8) * 8);
    // Measured once straight away too: browsers hold ResizeObserver callbacks while a tab
    // isn't being painted (opened in the background), which would leave the pages blank.
    measure(element.clientWidth - parseFloat(getComputedStyle(element).paddingLeft) * 2);
    const observer = new ResizeObserver(([entry]) => measure(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setPdf(null);
    setImageUrl(null);
    if (source.kind === "image") {
      objectUrl = typeof source.data === "string" ? null : URL.createObjectURL(source.data);
      setImageUrl(objectUrl ?? (source.data as string));
    } else {
      Promise.all([loadPdfjs(), bytes(source.data)])
        .then(([pdfjs, data]) => pdfjs.getDocument({ data }).promise)
        .then((doc) => {
          if (!cancelled) setPdf(doc);
        })
        .catch(() => !cancelled && onUnavailable?.());
    }
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
    // onUnavailable is a callback from the parent; reloading on its identity would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source]);

  // Group every clause's boxes by page once.
  const byPage = useMemo(() => {
    const pages = new Map<number, { clauseId: string; boxes: number[][] }[]>();
    for (const [clauseId, boxes] of Object.entries(highlights)) {
      const perPage = new Map<number, number[][]>();
      for (const box of boxes) perPage.set(box[0], [...(perPage.get(box[0]) ?? []), box]);
      for (const [page, list] of perPage) pages.set(page, [...(pages.get(page) ?? []), { clauseId, boxes: list }]);
    }
    return pages;
  }, [highlights]);

  useEffect(() => {
    if (!focus || !containerRef.current) return;
    const target = containerRef.current.querySelector<HTMLElement>(`[data-clause="${focus.clauseId}"]`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focus]);

  const overlay = (page: number) => (
    <PageOverlay
      clauses={byPage.get(page) ?? []}
      risks={risks}
      selected={selected}
      scanning={scanning}
      onSelect={onSelect}
    />
  );

  return (
    <div className="doc-viewer" ref={containerRef}>
      {source.kind === "image" && imageUrl && (
        <div className="doc-page">
          <img src={imageUrl} alt="Your uploaded lease" onError={() => onUnavailable?.()} />
          {overlay(1)}
        </div>
      )}
      {source.kind === "pdf" && !pdf && <div className="doc-page doc-page-loading" />}
      {pdf &&
        width > 0 &&
        Array.from({ length: pdf.numPages }, (_, i) => (
          <PdfPage key={i} pdf={pdf} number={i + 1} width={width}>
            {overlay(i + 1)}
          </PdfPage>
        ))}
    </div>
  );
}

function PdfPage({
  pdf,
  number,
  width,
  children,
}: {
  pdf: PDFDocumentProxy;
  number: number;
  width: number;
  children: React.ReactNode;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderRef = useRef<ReturnType<PDFPageProxy["render"]> | null>(null);
  const [ratio, setRatio] = useState(1.414);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const page = await pdf.getPage(number);
      // PDF.js refuses a second render into a canvas still being drawn, so a resize waits
      // for the previous (cancelled) render to wind down first.
      await renderRef.current?.promise.catch(() => undefined);
      if (cancelled || !canvasRef.current) return;
      const base = page.getViewport({ scale: 1 });
      setRatio(base.height / base.width);
      const viewport = page.getViewport({ scale: (width / base.width) * Math.min(window.devicePixelRatio || 1, 2) });
      const canvas = canvasRef.current;
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      renderRef.current = page.render({ canvasContext: canvas.getContext("2d")!, viewport });
      await renderRef.current.promise.catch(() => undefined);
    })();
    return () => {
      cancelled = true;
      renderRef.current?.cancel();
    };
  }, [pdf, number, width]);

  return (
    <div className="doc-page" style={{ aspectRatio: `1 / ${ratio}` }}>
      <canvas ref={canvasRef} aria-label={`Page ${number}`} />
      {children}
    </div>
  );
}

function PageOverlay({
  clauses,
  risks,
  selected,
  scanning,
  onSelect,
}: {
  clauses: { clauseId: string; boxes: number[][] }[];
  risks: Record<string, RiskLabel>;
  selected: string | null;
  scanning?: boolean;
  onSelect?: (clauseId: string) => void;
}) {
  return (
    <div className="doc-overlay">
      {clauses.map(({ clauseId, boxes }) => {
        const risk = risks[clauseId]?.toLowerCase() ?? "none";
        const isSelected = selected === clauseId;
        const first = boxes[0];
        const last = boxes[boxes.length - 1];
        const label = `Clause ${clauseId.replace("c", "")}${risks[clauseId] ? ` · ${RISK_WORDING[risks[clauseId]]}` : ""}`;
        return (
          <div key={clauseId} className={`hl-group hl-${risk} ${isSelected ? "hl-selected" : ""}`}>
            {(risk === "red" || risk === "yellow") && (
              <span
                className="hl-margin"
                style={{ top: `${(first[2] - PAD_Y) * 100}%`, height: `${(last[4] - first[2] + 2 * PAD_Y) * 100}%` }}
              />
            )}
            {boxes.map((box, i) => (
              <button
                key={i}
                type="button"
                data-clause={i === 0 ? clauseId : undefined}
                className="hl"
                title={label}
                aria-label={i === 0 ? label : undefined}
                tabIndex={i === 0 && onSelect ? 0 : -1}
                onClick={() => onSelect?.(clauseId)}
                style={{
                  left: `${(box[1] - PAD_X) * 100}%`,
                  top: `${(box[2] - PAD_Y) * 100}%`,
                  width: `${(box[3] - box[1] + 2 * PAD_X) * 100}%`,
                  height: `${(box[4] - box[2] + 2 * PAD_Y) * 100}%`,
                }}
              />
            ))}
          </div>
        );
      })}
      {scanning && <div className="scan-line" aria-hidden />}
    </div>
  );
}

/** Fallback when the original file isn't available in this browser: the lease's text laid
 *  out as a page, with the same highlights and the same click-to-select behaviour. */
export function TextDocument({
  clauses,
  risks,
  selected,
  focus,
  scanning,
  onSelect,
  notice,
}: {
  clauses: { clause_id: string; section_heading?: string | null; text: string }[];
  risks: Record<string, RiskLabel>;
  selected: string | null;
  focus: Focus | null;
  scanning?: boolean;
  onSelect?: (clauseId: string) => void;
  notice?: React.ReactNode;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!focus || !containerRef.current) return;
    containerRef.current
      .querySelector<HTMLElement>(`[data-clause="${focus.clauseId}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focus]);

  return (
    <div className="doc-viewer" ref={containerRef}>
      {notice}
      <div className="doc-page doc-text-page">
        {clauses.map((clause) => {
          const risk = risks[clause.clause_id]?.toLowerCase() ?? "none";
          return (
            <p key={clause.clause_id} className="doc-text-clause">
              {clause.section_heading && <strong className="doc-text-heading">{clause.section_heading}</strong>}
              <button
                type="button"
                data-clause={clause.clause_id}
                className={`text-hl hl-${risk} ${selected === clause.clause_id ? "hl-selected" : ""}`}
                onClick={() => onSelect?.(clause.clause_id)}
              >
                {clause.text}
              </button>
            </p>
          );
        })}
        {scanning && <div className="scan-line" aria-hidden />}
      </div>
    </div>
  );
}
