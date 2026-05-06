import { execSync, spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const PORT = "3001";
const cwd = process.cwd();

function killPortListeners(port) {
  try {
    const pids = execSync(`lsof -nP -iTCP:${port} -sTCP:LISTEN -t`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    })
      .trim()
      .split(/\s+/)
      .filter(Boolean);

    if (!pids.length) {
      console.log(`[eko] port ${port} is free`);
      return;
    }

    for (const pid of [...new Set(pids)]) {
      try {
        process.kill(Number(pid), "SIGKILL");
        console.log(`[eko] killed stale PID ${pid} on ${port}`);
      } catch {
        /* ignore */
      }
    }
  } catch {
    console.log(`[eko] port ${port} looks free (no listener found)`);
  }
}

function run() {
  killPortListeners(PORT);

  const nextBin = resolve(cwd, "node_modules", ".bin", "next");
  const command = existsSync(nextBin) ? nextBin : "next";

  // Bind IPv4 all interfaces so http://127.0.0.1:PORT and http://localhost:PORT both work.
  // (-H localhost alone often binds only ::1 on macOS → browser IPv4 gets ERR_CONNECTION_REFUSED.)
  console.log(`[eko] Starting Next on 0.0.0.0:${PORT} → open http://localhost:${PORT} or http://127.0.0.1:${PORT}`);

  const child = spawn(
    command,
    ["dev", "--webpack", "-H", "0.0.0.0", "-p", PORT],
    {
      stdio: "inherit",
      env: {
        ...process.env,
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  );

  child.on("exit", (code) => {
    process.exit(code ?? 0);
  });
}

run();
