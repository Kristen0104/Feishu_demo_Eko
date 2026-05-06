/** Tiny SVG placeholders for demo <img> tags (no external assets). */

export function svgPptSlide(opts: { slideNumber: number; title: string; subtitle?: string }): string {
  const { slideNumber, title, subtitle } = opts;
  const sub = subtitle ?? `Job demo · Slide ${slideNumber}`;
  const gid = `g${slideNumber}`;
  const t = escapeXml(title);
  const s = escapeXml(sub);
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="${gid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#eff6ff"/>
      <stop offset="100%" stop-color="#dbeafe"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#${gid})"/>
  <rect x="48" y="48" width="1184" height="624" rx="28" fill="#ffffff" stroke="#bfdbfe" stroke-width="2"/>
  <text x="96" y="140" font-family="ui-sans-serif, system-ui" font-size="22" fill="#64748b">Slide ${slideNumber}</text>
  <text x="96" y="220" font-family="ui-sans-serif, system-ui" font-size="40" font-weight="700" fill="#0f172a">${t}</text>
  <text x="96" y="280" font-family="ui-sans-serif, system-ui" font-size="20" fill="#64748b">${s}</text>
  <text x="96" y="620" font-family="ui-sans-serif, system-ui" font-size="16" fill="#94a3b8">Eko 前端演示数据（无后端）</text>
</svg>`;
}

export function svgBoardPreview(opts: { label: string }): string {
  const label = escapeXml(opts.label);
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0b1020"/>
      <stop offset="100%" stop-color="#1e1b4b"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="675" fill="url(#bg)"/>
  <rect x="40" y="40" width="1120" height="595" rx="24" fill="#0f172a" stroke="#334155" stroke-width="2"/>
  <circle cx="200" cy="200" r="70" fill="#22d3ee" opacity="0.35"/>
  <circle cx="520" cy="260" r="110" fill="#a78bfa" opacity="0.35"/>
  <rect x="320" y="380" width="520" height="120" rx="16" fill="#1e293b" stroke="#475569"/>
  <text x="80" y="120" font-family="ui-sans-serif, system-ui" font-size="28" font-weight="700" fill="#f8fafc">飞书画板预览（演示）</text>
  <text x="80" y="170" font-family="ui-sans-serif, system-ui" font-size="18" fill="#94a3b8">${label}</text>
</svg>`;
}

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
