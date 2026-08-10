// MariaDB dev extension for the Pi coding agent (pi.dev).
//
// Two moving parts make up this plugin:
//   1. Skills — vendored under ./skills and declared via the package.json `pi`
//      field, so pi loads them contextually. This extension does not touch them.
//   2. The native mariadb-shell MCP server — reached through `pi-mcp-adapter`
//      (a dependency of this package). The adapter connects to MCP servers listed
//      in an mcp.json config; this extension wires our launcher into that config.
//
// The heavy lifting of registering the server lives in scripts/setup-pi-mcp.sh
// (the single source of truth, usable from a plain shell too). This extension
// exposes it as the `/mariadb-mcp-setup` command and, on session start, nudges
// the user to run it when the server isn't configured yet.

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);

// The name this plugin registers with pi-mcp-adapter (must match the setup script).
const MCP_SERVER_NAME = "mariadb";

// Plugin root = the dir holding package.json, one level up from src/. Resolved
// from import.meta.url so it is correct wherever pi installs the package.
const PLUGIN_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SETUP_SCRIPT = join(PLUGIN_ROOT, "scripts", "setup-pi-mcp.sh");

// The mcp.json files pi-mcp-adapter reads, in its precedence order. We only need
// to know whether *any* of them already defines our server.
function adapterConfigPaths(): string[] {
  const xdg = process.env.XDG_CONFIG_HOME || join(homedir(), ".config");
  return [
    join(xdg, "mcp", "mcp.json"),
    join(homedir(), ".agents", "mcp.json"),
    join(homedir(), ".agents", "mcp", "mcp.json"),
    resolve(process.cwd(), ".mcp.json"),
    resolve(process.cwd(), ".pi", "mcp.json"),
  ];
}

function mariadbServerConfigured(): boolean {
  for (const p of adapterConfigPaths()) {
    if (!existsSync(p)) continue;
    try {
      const json = JSON.parse(readFileSync(p, "utf8"));
      if (json?.mcpServers?.[MCP_SERVER_NAME]) return true;
    } catch {
      // Ignore malformed config files — treat as "not configured".
    }
  }
  return false;
}

export default function (pi: ExtensionAPI) {
  // `/mariadb-mcp-setup [--global | --project | --config PATH]`
  // Register the mariadb-shell MCP server with pi-mcp-adapter by delegating to
  // scripts/setup-pi-mcp.sh, so the command and the CLI stay in lock-step.
  pi.registerCommand("mariadb-mcp-setup", {
    description:
      "Register the MariaDB (mariadb-shell) MCP server with pi-mcp-adapter. " +
      "Args are passed to setup-pi-mcp.sh (default: global ~/.config/mcp/mcp.json; " +
      "--project writes ./.mcp.json).",
    handler: async (args, ctx) => {
      const scriptArgs = args.trim() ? args.trim().split(/\s+/) : [];
      try {
        const { stdout } = await execFileAsync("bash", [SETUP_SCRIPT, ...scriptArgs]);
        ctx.ui.notify(
          `${stdout.trim() || "MariaDB MCP server configured."} ` +
            `Run "/mcp reconnect ${MCP_SERVER_NAME}" or restart pi to pick it up.`,
          "info",
        );
      } catch (err: unknown) {
        const detail =
          (err as { stderr?: string })?.stderr ||
          (err as { message?: string })?.message ||
          String(err);
        ctx.ui.notify(`MariaDB MCP setup failed: ${detail}`, "error");
      }
    },
  });

  // Nudge the user once per session if the MCP server isn't wired up yet. Skills
  // work regardless; this only concerns the live mariadb-shell connection.
  pi.on("session_start", async (_event, ctx) => {
    if (!mariadbServerConfigured()) {
      ctx.ui.notify(
        'MariaDB skills loaded. Run "/mariadb-mcp-setup" to enable the ' +
          "mariadb-shell MCP server via pi-mcp-adapter.",
        "info",
      );
    }
  });
}
