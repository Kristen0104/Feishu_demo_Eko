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
  // Keep Turbopack config explicit.
  turbopack: {},
  // 避免与家目录中其他 package-lock.json 冲突，消除多 lockfile 警告
  outputFileTracingRoot: path.join(__dirname),
  webpack(config) {
    /**
     * Defensive normalization:
     * Some environments end up with an invalid `resolve.alias` shape (seen as a ResolveOptions object),
     * which makes webpack schema validation fail on `styled-jsx/style$`.
     */
    config.resolve ??= {};

    const maybeResolveOptions = config.resolve.alias as unknown;
    if (
      maybeResolveOptions &&
      typeof maybeResolveOptions === "object" &&
      !Array.isArray(maybeResolveOptions) &&
      ("extensions" in maybeResolveOptions || "modules" in maybeResolveOptions || "mainFields" in maybeResolveOptions)
    ) {
      config.resolve = maybeResolveOptions as typeof config.resolve;
    }

    const alias = config.resolve.alias;
    if (!alias || typeof alias !== "object" || Array.isArray(alias)) {
      config.resolve.alias = {};
    }

    (config.resolve.alias as Record<string, string | false | string[]>)["styled-jsx/style$"] =
      require.resolve("styled-jsx/style");

    return config;
  },
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
