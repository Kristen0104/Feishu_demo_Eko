/**
 * 启动 dev 前释放端口，避免上次未正常退出的 next 进程占用导致 EADDRINUSE。
 * 默认释放 3001（与 package.json 中 dev 脚本一致）。
 */
import { execSync } from "node:child_process";

const port = process.env.FREE_DEV_PORT ?? process.argv[2] ?? "3001";

if (process.platform === "win32") {
  console.log("[eko] skip free-dev-port on Windows（请手动结束占用该端口的进程）");
  process.exit(0);
}

try {
  const out = execSync(`lsof -nP -iTCP:${port} -sTCP:LISTEN -t`, {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "ignore"],
  }).trim();

  if (!out) {
    console.log(`[eko] port ${port} is free`);
    process.exit(0);
  }

  const pids = [...new Set(out.split(/\s+/).filter(Boolean))];
  for (const pid of pids) {
    try {
      process.kill(Number(pid), "SIGKILL");
      console.log(`[eko] freed port ${port}: killed PID ${pid}`);
    } catch {
      /* ignore */
    }
  }
} catch {
  console.log(`[eko] port ${port} looks free (no listener found)`);
}
