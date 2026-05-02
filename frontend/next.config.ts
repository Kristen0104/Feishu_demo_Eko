import path from "path";
import type { NextConfig } from "next";

/** Forward `/api/v1/*` to FastAPI so the browser can use same-origin relative URLs (no CORS). Prefer BACKEND_PROXY in `.env.local`. */
const backendRewriteOrigin =
  process.env.BACKEND_PROXY?.replace(/\/$/, "") ||
  process.env.NEXT_PUBLIC_EKO_API_BASE?.replace(/\/$/, "") ||
  "";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 避免与家目录中其他 package-lock.json 冲突，消除多 lockfile 警告
  outputFileTracingRoot: path.join(__dirname),
  transpilePackages: ["tldraw", "@tldraw/editor", "@tldraw/store", "@tldraw/tlschema", "@tldraw/state", "@tldraw/utils"],
  async rewrites() {
    if (!backendRewriteOrigin) return [];
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendRewriteOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
