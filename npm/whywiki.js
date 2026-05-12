#!/usr/bin/env node

const { spawn } = require("node:child_process");
const os = require("node:os");
const path = require("node:path");

const candidates = process.platform === "win32"
  ? ["python.exe", "python3.exe"]
  : ["python3", "python"];
const packageRoot = path.resolve(__dirname, "..");

function buildEnv(baseEnv) {
  const pythonPath = baseEnv.PYTHONPATH
    ? `${packageRoot}${path.delimiter}${baseEnv.PYTHONPATH}`
    : packageRoot;

  return Object.assign({}, baseEnv, {
    PYTHONPATH: pythonPath,
    WHYWIKI_DATA_DIR: baseEnv.WHYWIKI_DATA_DIR || path.join(os.homedir(), ".whywiki")
  });
}

function exitFromChild(code, signal, proc = process) {
  if (signal) {
    try {
      proc.kill(proc.pid, signal);
    } catch (error) {
      proc.exit(128);
    }
    return;
  }

  proc.exit(code === null ? 1 : code);
}

function run(index, passthrough, env) {
  if (index >= candidates.length) {
    console.error("WhyWiki could not find Python. Install Python 3.10+ and run again.");
    process.exit(1);
  }

  const child = spawn(candidates[index], ["-m", "whywiki.cli"].concat(passthrough), {
    env,
    stdio: "inherit"
  });

  child.on("error", () => run(index + 1, passthrough, env));
  child.on("exit", exitFromChild);
}

function main(argv) {
  const defaultServe = argv.length === 0;
  const passthrough = defaultServe ? ["serve", "--host", "127.0.0.1", "--port", "8765"] : argv;
  const env = buildEnv(process.env);

  run(0, passthrough, env);
}

if (require.main === module) {
  main(process.argv.slice(2));
}

module.exports = {
  buildEnv,
  exitFromChild
};
