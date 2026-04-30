// @ts-nocheck
import path from "path";

const projectRoot = path.resolve(process.cwd());

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Fix workspace-root inference when multiple lockfiles exist on this machine.
  outputFileTracingRoot: projectRoot,
  turbopack: {
    root: projectRoot,
  },
};

export default nextConfig;
