import type { SourcePlatform } from "@/api/types";

/**
 * Which platform a pasted string looks like, or null if it is not a usable link.
 *
 * A deliberately loose mirror of the server's `detect_platform`. The server is the authority — this
 * only decides whether to *offer* the clipboard card, so being generous costs nothing (the server
 * says no) while being strict would hide a link the server would have accepted.
 */
const HOSTS: [RegExp, SourcePlatform][] = [
  [/(^|\.)tiktok\.com$/, "tiktok"],
  [/(^|\.)instagram\.com$/, "instagram"],
  [/(^|\.)(youtube\.com|youtu\.be)$/, "youtube"],
  [/(^|\.)pinterest\.[a-z.]+$/, "pinterest"],
  [/(^|\.)pin\.it$/, "pinterest"],
];

export function detectPlatform(candidate: string): SourcePlatform | null {
  let host: string;
  try {
    host = new URL(candidate.trim()).hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    // Not a URL at all — someone copied a sentence. No card, no error.
    return null;
  }

  for (const [pattern, platform] of HOSTS) {
    if (pattern.test(host)) return platform;
  }
  // Any other http(s) host is a blog until the server says otherwise.
  return host.includes(".") ? "web" : null;
}
