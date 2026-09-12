import { spawn, spawnSync } from "node:child_process";
import dns from "node:dns";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

dns.setDefaultResultOrder("ipv4first");

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const backendDir = path.resolve(frontendDir, "..", "backend");
const isWin = process.platform === "win32";
const nextArgs = process.argv.slice(2);

function venvPython() {
  return isWin
    ? path.join(backendDir, ".venv", "Scripts", "python.exe")
    : path.join(backendDir, ".venv", "bin", "python");
}

function systemPythons() {
  return isWin ? ["py", "python", "python3"] : ["python3", "python"];
}

async function backendHealthy() {
  for (const url of ["http://127.0.0.1:8000/health", "http://localhost:8000/health"]) {
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch {
      // keep trying
    }
  }
  return false;
}

function run(command, args, cwd) {
  return spawnSync(command, args, { cwd, stdio: "inherit", shell: isWin });
}

function ensureVenv() {
  if (existsSync(venvPython())) return;
  console.log("[dev] Creating backend/.venv …");
  let created = false;
  for (const cmd of systemPythons()) {
    const result = run(cmd, ["-m", "venv", ".venv"], backendDir);
    if (result.status === 0 && existsSync(venvPython())) {
      created = true;
      break;
    }
  }
  if (!created) {
    throw new Error(
      "Could not create backend/.venv. Install Python 3, then run: cd backend && python -m venv .venv",
    );
  }
  console.log("[dev] Installing backend requirements …");
  const pip = run(venvPython(), ["-m", "pip", "install", "-r", "requirements.txt"], backendDir);
  if (pip.status !== 0) {
    throw new Error("pip install failed. From backend/, run: .venv/bin/pip install -r requirements.txt");
  }
}

async function waitForHealth(timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await backendHealthy()) return true;
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  return false;
}

function spawnProc(command, args, cwd) {
  return spawn(command, args, {
    cwd,
    stdio: "inherit",
    shell: isWin,
    env: process.env,
  });
}

const children = [];

function shutdown() {
  for (const child of children) {
    if (child && !child.killed) child.kill("SIGTERM");
  }
}

process.on("SIGINT", () => {
  shutdown();
  process.exit(0);
});
process.on("SIGTERM", () => {
  shutdown();
  process.exit(0);
});

if (await backendHealthy()) {
  console.log("[dev] FastAPI already running on port 8000");
} else {
  ensureVenv();
  console.log("[dev] Starting FastAPI on http://127.0.0.1:8000");
  const backend = spawnProc(
    venvPython(),
    ["-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
    backendDir,
  );
  children.push(backend);
  backend.on("exit", (code) => {
    if (code && code !== 0) {
      console.error(`[dev] FastAPI exited with code ${code}`);
    }
  });
  const ready = await waitForHealth();
  if (!ready) {
    shutdown();
    throw new Error(
      "FastAPI did not become ready on port 8000. Check the backend terminal output above.",
    );
  }
}

console.log("[dev] Starting Next.js …");
const nextBin = path.join(frontendDir, "node_modules", ".bin", isWin ? "next.cmd" : "next");
const frontend = spawnProc(nextBin, ["dev", ...nextArgs], frontendDir);
children.push(frontend);
frontend.on("exit", (code) => {
  shutdown();
  process.exit(code ?? 0);
});
