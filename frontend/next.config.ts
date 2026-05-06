import path from "path";
import type { NextConfig } from "next";

/** Forward `/api/v1/*` to FastAPI so the browser can use same-origin relative URLs (no CORS). Prefer BACKEND_PROXY in `.env.local`. */
const backendRewriteOrigin =
  process.env.BACKEND_PROXY?.replace(/\/$/, "") ||
  process.env.NEXT_PUBLIC_EKO_API_BASE?.replace(/\/$/, "") ||
  "";

const ngrokDevOrigins = [
  "*.ngrok-free.dev",
  "*.ngrok-free.app",
  "*.ngrok.app",
  process.env.NGROK_HOST ? process.env.NGROK_HOST.replace(/^https?:\/\//, "") : null,
].filter((origin): origin is string => Boolean(origin));

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ngrokDevOrigins,
  // 避免与家目录中其他 package-lock.json 冲突，消除多 lockfile 警告
  outputFileTracingRoot: path.join(__dirname),
  // Keep dev startup fast and stable on local machines.
  transpilePackages: [],
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
