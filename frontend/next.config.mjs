import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const backendRewriteOrigin =
  process.env.BACKEND_PROXY?.replace(/\/$/, "") ||
  process.env.NEXT_PUBLIC_EKO_API_BASE?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const ngrokDevOrigins = [
  "*.ngrok-free.dev",
  "*.ngrok-free.app",
  "*.ngrok.app",
  process.env.NGROK_HOST ? process.env.NGROK_HOST.replace(/^https?:\/\//, "") : null,
].filter(Boolean);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ngrokDevOrigins,
  outputFileTracingRoot: __dirname,
  transpilePackages: ["tldraw", "@tldraw/editor", "@tldraw/store", "@tldraw/tlschema", "@tldraw/state", "@tldraw/utils"],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendRewriteOrigin}/api/v1/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${backendRewriteOrigin}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
