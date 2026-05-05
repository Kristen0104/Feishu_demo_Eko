type CookieOptions = {
  maxAgeSeconds?: number;
};

function isSecureContext(): boolean {
  return typeof window !== "undefined" && window.location.protocol === "https:";
}

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;

  const encodedName = encodeURIComponent(name);
  const prefix = `${encodedName}=`;
  const match = document.cookie
    .split("; ")
    .find((pair) => pair.startsWith(prefix));
  if (!match) return null;

  const value = match.slice(prefix.length);
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function setCookie(name: string, value: string, options?: CookieOptions): void {
  if (typeof document === "undefined") return;

  const parts = [
    `${encodeURIComponent(name)}=${encodeURIComponent(value)}`,
    "path=/",
    "sameSite=lax",
  ];

  if (typeof options?.maxAgeSeconds === "number") {
    parts.push(`max-age=${Math.max(0, Math.floor(options.maxAgeSeconds))}`);
  }

  if (isSecureContext()) {
    parts.push("secure");
  }

  document.cookie = parts.join("; ");
}

export function deleteCookie(name: string): void {
  setCookie(name, "", { maxAgeSeconds: 0 });
}
