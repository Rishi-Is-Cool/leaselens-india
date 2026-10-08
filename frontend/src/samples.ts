// Saved sample reviews are keyed by their source filename ("01_maharashtra_leave_license_mumbai.pdf");
// pages address them by a readable slug instead.

export function sampleSlug(filename: string): string {
  return filename.replace(/^\d+_/, "").replace(/\.pdf$/i, "").replaceAll("_", "-").toLowerCase();
}

const SMALL_WORDS = new Set(["and", "of", "the"]);
const CITIES = new Set(["mumbai", "bangalore", "chennai", "lucknow", "kolkata", "chandigarh", "jaipur", "pune"]);

export function sampleTitle(filename: string): string {
  const words = sampleSlug(filename).split("-");
  // Most names end in the city ("..._mumbai"); the rest name the agreement type.
  const city = CITIES.has(words[words.length - 1]) ? words.pop()! : null;
  const title = words
    .map((w, i) => (i > 0 && SMALL_WORDS.has(w) ? w : w[0].toUpperCase() + w.slice(1)))
    .join(" ")
    .replace("Leave License", "Leave & Licence");
  return city ? `${title} · ${city[0].toUpperCase()}${city.slice(1)}` : title;
}

export const RISK_WORDING: Record<string, string> = {
  GREEN: "Looks standard",
  YELLOW: "Worth a look",
  RED: "Needs attention",
};
