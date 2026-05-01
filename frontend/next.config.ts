import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 避免与家目录中其他 package-lock.json 冲突，消除多 lockfile 警告
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
