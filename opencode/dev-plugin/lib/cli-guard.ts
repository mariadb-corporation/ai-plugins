// Copyright (c) 2026, MariaDB plc.
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License, version 2.0,
// as published by the Free Software Foundation.
//
// This program is distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
// the GNU General Public License, version 2.0, for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software Foundation, Inc.,
// 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

// The MariaDB CLI guard: does a shell command use a MariaDB or MySQL
// command-line client for something the mariadb MCP server's tools do?
//
// A client run from a shell needs the password on its command line or in its
// environment, where it lands in the process list, in logs and in the
// transcript the model provider sees. A connection opened through the MCP
// server reads its password from the operating system's secret store. The
// harness integrations block such a command and hand the model blockReason().
//
// Only five clients are looked at, and each only for what a tool covers:
//   mariadb, mysql          running SQL                    -> db.execute_sql(_script)
//   mariadb-shell, mysqlsh  SQL mode                       -> db.execute_sql(_script)
//                           `-- <object> <method>` calls   -> the matching tool
//   mariadb-dump            piped into another client      -> util.copy_*
// Everything else - --version and --help, Python or JavaScript mode, a dump
// written to a file, `-- mcp setup`, an API call no tool wraps (but an msm one left to the VS Code extension) - is let through,
// so the agent keeps every feature the tools do not have yet.
//
// A port of the bash hook the Claude Code and Codex plugins ship
// (hooks/mariadb-cli-guard.sh); tests/cli-guard-cases.json at the repository
// root holds the cases every port must agree on. Shared, byte for byte, by the
// Pi extension and the OpenCode plugin.

/**
 * The `-- <object> <method>` calls of mariadb-shell / mysqlsh that an MCP tool
 * wraps: each as <object>.<method> in snake_case, as the shell names it, to
 * the MCP tool that wraps it.
 */
const COVERED_API = new Map([
  ["util.dump_instance", "util.dump_instance"],
  ["util.dump_schemas", "util.dump_schemas"],
  ["util.dump_tables", "util.dump_tables"],
  ["util.export_table", "util.export_table"],
  ["util.load_dump", "util.load_dump"],
  ["util.import_table", "util.import_table"],
  ["util.copy_instance", "util.copy_instance"],
  ["util.copy_schemas", "util.copy_schemas"],
  ["util.copy_tables", "util.copy_tables"],
  ["sandbox.deploy", "sandbox.deploy"],
  ["sandbox.start", "sandbox.start"],
  ["sandbox.stop", "sandbox.stop"],
  ["sandbox.kill", "sandbox.kill"],
  ["sandbox.delete", "sandbox.delete"],
  ["msm.create_new_project_folder", "msm.create_project"],
  ["msm.list_projects", "msm.list_projects"],
  ["msm.drop_schema_object", "msm.drop_schema_object"],
  ["msm.drop_rest_object", "msm.drop_rest_object"],
  ["msm.prepare_release", "msm.prepare_release"],
  ["msm.generate_deployment_script", "msm.generate_deployment_script"],
  ["msm.deploy_schema", "msm.deploy_schema"],
  ["msm.list_live_schema_objects", "msm.list_live_schema_objects"],
  ["msm.import_live_schema", "msm.import_live_schema"],
  ["msm.list_schema_diagrams", "msm.list_schema_diagrams"],
  ["msm.create_schema_diagram", "msm.create_schema_diagram"],
  ["msm.layout_schema_diagram", "msm.layout_schema_diagram"],
  ["msm.rename_schema_diagram", "msm.rename_schema_diagram"],
  ["msm.remove_schema_diagram", "msm.remove_schema_diagram"],
  ["rest.version", "rest.version"],
]);

/**
 * The calls of functions that live in a group of an object, as
 * `-- <object> <group> <method>` (`msm get schema-diagrams`): each as
 * <object>.<group>.<method> in snake_case, to the MCP tool that wraps it. A
 * word after the object is a group when an entry starts with it.
 */
const COVERED_NESTED_API = new Map([
  ["msm.get.project_information", "msm.get_project_information"],
  ["msm.get.released_versions", "msm.get_released_versions"],
  ["msm.get.last_released_version", "msm.get_last_released_version"],
  ["msm.get.last_deployment_version", "msm.get_last_deployment_version"],
  ["msm.get.sql_content_from_section", "msm.get_section_sql_content"],
  ["msm.get.deployment_script_versions", "msm.get_deployment_script_versions"],
  ["msm.get.schema_diagrams", "msm.get_schema_diagrams"],
  ["msm.set.development_version", "msm.set_development_version"],
  ["msm.set.section_sql_content", "msm.set_section_sql_content"],
  ["msm.set.schema_diagram", "msm.set_schema_diagram"],
  ["msm.set.schema_statements", "msm.set_schema_statements"],
  ["msm.set.rest_statements", "msm.set_rest_statements"],
  ["rest.dump.service", "rest.dump_service"],
  ["rest.dump.service_project", "rest.dump_service_project"],
  ["rest.dump.sdk_service_files", "rest.dump_sdk_service_files"],
  ["rest.dump.audit_log", "rest.dump_audit_log"],
  ["rest.get.sdk_base_classes", "rest.get_sdk_base_classes"],
  ["rest.get.sdk_options", "rest.get_sdk_options"],
  ["rest.get.sdk_service_classes", "rest.get_sdk_service_classes"],
  ["rest.get.runtime_management_code", "rest.get_runtime_management_code"],
  ["rest.get.file_mrs_script_definitions", "rest.get_file_mrs_script_definitions"],
  ["rest.get.folder_mrs_script_definitions", "rest.get_folder_mrs_script_definitions"],
  ["rest.get.folder_mrs_script_language", "rest.get_folder_mrs_script_language"],
  ["rest.load.service", "rest.load_service"],
  ["rest.load.service_project", "rest.load_service_project"],
  ["rest.load.content_set", "rest.load_content_set"],
]);

/**
 * Functions, in a group or not, whose MCP tool the server serves to the
 * MariaDB VS Code extension only (--gui), never to an agent. Still denied -
 * the server tells agents to work on MSM projects through the msm.* tools
 * only - but the denial names no tool: the user does it in the extension.
 */
const EXTENSION_ONLY_API = new Set([
  "msm.add_project",
  "msm.update_project",
  "msm.remove_project",
  "msm.edit_schema",
  "msm.update_schema_definition",
  "msm.split_sections",
  "msm.rename_schema",
  "msm.online_alter_table",
  "msm.dump_rest_sdk",
  "msm.import_workbench_model",
  "msm.get.online_alter_defaults",
  "msm.get.online_alter_settings",
  "msm.get.schema_diagram_image",
  "msm.get.object_templates",
  "msm.set.project_settings",
]);

const USE_THE_EXTENSION =
  "none is served to you for this; ask the user to do it in the MariaDB VS Code extension";

/** The groups both lists name, as <object>.<group>. */
const GROUPS = new Set([...COVERED_NESTED_API.keys(), ...EXTENSION_ONLY_API].filter((path) => {
  return path.split(".").length === 3;
}).map((path) => {
  return path.slice(0, path.lastIndexOf("."));
}));

/** What runs a command rather than being one, besides VAR=value and -options. */
const WRAPPERS = new Set([
  "sudo", "doas", "env", "command", "exec", "nohup", "time", "nice", "xargs",
  "do", "then", "else", "elif", "if", "while", "until", "!",
]);

/** Shells, and eval: their string argument is a command line of its own. */
const SHELLS = new Set(["sh", "bash", "zsh", "dash", "ksh", "eval"]);

const USE_SQL_TOOLS =
  "run the SQL with db.connect and db.execute_sql, or db.execute_sql_script " +
  "(it takes a file_path for a .sql file), instead";
const USE_COPY_TOOLS =
  "copy between servers with util.copy_instance, util.copy_schemas or " +
  "util.copy_tables instead (a dump written to a file is fine)";

/** The environment variable that turns the guard off. */
export const ALLOW_ENV = "MARIADB_PLUGIN_ALLOW_CLI";

/** A denied command: the client, and what to do instead. */
export interface Finding {
  client: string;
  use: string;
}

/** What the model is told instead of the command's output. */
export function blockReason(finding: Finding): string {
  return (
    `Blocked: \`${finding.client}\` does something the mariadb MCP server's tools do, ` +
    "and a client run from a shell puts database credentials on a command line, in " +
    "the process list, in logs and in this conversation. Use the MCP tools: " +
    `${finding.use}. ` +
    "Never ask for or pass a database password: open a server with db.connect, and " +
    "if it is not in db.list_connections, ask the user to add it with " +
    "`mariadb-shell -- mcp setup`. What no MCP tool covers is not blocked, apart from the msm functions left to the MariaDB VS Code extension. If the " +
    "user wants you to run the clients anyway, they can start the agent with " +
    `${ALLOW_ENV}=1.`
  );
}

/** The system-prompt text that says the same before the first call. */
export const SYSTEM_PROMPT_RULE =
  "MariaDB: work with databases through the mariadb MCP server's tools - SQL " +
  "with db.connect, db.execute_sql and db.execute_sql_script, local test " +
  "servers with sandbox.*, dumps, loads and copies with util.* - rather than " +
  "by running mariadb, mysql, mariadb-shell, mysqlsh or mariadb-dump from a " +
  "shell, which is blocked where a tool covers the task. A client is fine for " +
  "what no tool covers. Never ask for, or put into a command, a database " +
  "password; deploy a sandbox with a freshly generated random password, which " +
  "is stored with its connection. If a server is not in db.list_connections, " +
  "ask the user to add it with `mariadb-shell -- mcp setup`.";

/** Is the guard turned off in this environment? */
export function guardDisabled(env: Record<string, string | undefined> = process.env): boolean {
  return env[ALLOW_ENV] === "1";
}

function isInfoFlag(arg: string): boolean {
  return (
    ["--version", "-V", "--help", "-?", "-I", "--print-defaults"].includes(arg) ||
    arg.startsWith("--help=")
  );
}

/** kebab-case and camelCase both name the same method. */
function snakeCase(method: string): string {
  return method.replace(/-/g, "_").replace(/([A-Z])/g, "_$1").toLowerCase();
}

function checkShell(name: string, args: string[]): Finding | null {
  let mode = "";
  let file = "";
  let api = false;
  let object = "";
  let method = "";
  let next = "";
  for (let j = 0; j < args.length; j++) {
    const arg = args[j];
    if (api) {
      if (arg.startsWith("-")) continue;
      if (!object) object = arg;
      else if (!method) method = arg;
      else if (!next) next = arg;
      continue;
    }
    if (isInfoFlag(arg)) return null;
    if (arg === "--") api = true;
    else if (["--sql", "--sqlc", "--sqlx"].includes(arg)) mode = "sql";
    else if (arg === "--py" || arg === "--python") mode = "py";
    else if (arg === "--js" || arg === "--javascript") mode = "js";
    else if (arg === "-f" || arg === "--file") file = args[++j] ?? "";
    else if (arg.startsWith("--file=")) file = arg.slice("--file=".length);
  }

  if (api) {
    if (!method) return null;
    let path: string;
    let list: Map<string, string>;
    if (GROUPS.has(`${object}.${method}`)) {
      // A group: the method is the word after it.
      if (!next) return null;
      path = `${object}.${method}.${snakeCase(next)}`;
      list = COVERED_NESTED_API;
    } else {
      path = `${object}.${snakeCase(method)}`;
      list = COVERED_API;
    }
    if (EXTENSION_ONLY_API.has(path)) return { client: name, use: USE_THE_EXTENSION };
    const tool = list.get(path);
    return tool ? { client: name, use: `call the MCP tool ${tool} instead` } : null;
  }

  if (!mode) {
    if (file.endsWith(".sql")) mode = "sql";
    else if (file.endsWith(".py")) mode = "py";
    else if (file.endsWith(".js")) mode = "js";
  }
  // MariaDB Shell starts in SQL mode, MySQL Shell in JavaScript.
  if (!mode) mode = name === "mariadb-shell" ? "sql" : "js";
  return mode === "sql" ? { client: name, use: USE_SQL_TOOLS } : null;
}

/**
 * One simple command, split into words. Returns the command it runs (for the
 * next command of a pipeline) and the finding, if it is denied.
 */
function checkWords(words: string[], pipedFrom: string): { name: string; found: Finding | null } {
  let i = 0;
  while (i < words.length) {
    const word = words[i];
    // `command -v NAME` looks a command up rather than running it.
    if (word === "command" && (words[i + 1] === "-v" || words[i + 1] === "-V")) {
      return { name: "", found: null };
    }
    if (word.includes("=") || word.startsWith("-") || WRAPPERS.has(word)) {
      i++;
      continue;
    }
    break;
  }
  if (i >= words.length) return { name: "", found: null };

  let name = words[i].replace(/^.*[\\/]/, "");
  if (name.endsWith(".exe")) name = name.slice(0, -4);
  const args = words.slice(i + 1);

  if (SHELLS.has(name)) {
    for (const arg of args) {
      if (arg.startsWith("-")) continue;
      const found = findClient(arg);
      if (found) return { name, found };
    }
    return { name, found: null };
  }
  if (name === "mariadb" || name === "mysql") {
    if (args.some(isInfoFlag)) return { name, found: null };
    if (pipedFrom === "mariadb-dump") {
      return { name, found: { client: `mariadb-dump | ${name}`, use: USE_COPY_TOOLS } };
    }
    return { name, found: { client: name, use: USE_SQL_TOOLS } };
  }
  if (name === "mariadb-shell" || name === "mysqlsh") {
    return { name, found: checkShell(name, args) };
  }
  // mariadb-dump on its own is fine: no tool writes a .sql dump.
  return { name, found: null };
}

/**
 * The finding for a command line, or null when it may run. Splits it into
 * simple commands at the shell's separators outside quotes, and each of those
 * into words with the quotes removed; $(...) and `...` start a command of
 * their own, inside double quotes too.
 */
export function findClient(line: string): Finding | null {
  const n = line.length;
  let words: string[] = [];
  let word = "";
  let haveWord = false;
  let quote = "";
  let pipedFrom = "";

  const endWord = () => {
    if (haveWord) words.push(word);
    word = "";
    haveWord = false;
  };
  // Ends the current command; returns its finding and the command it ran.
  const endCommand = (): { name: string; found: Finding | null } => {
    endWord();
    const result = words.length > 0 ? checkWords(words, pipedFrom) : { name: "", found: null };
    words = [];
    return result;
  };

  for (let k = 0; k < n; k++) {
    const c = line[k];
    if (quote) {
      if (c === quote) {
        quote = "";
      } else if (quote === '"' && c === "\\") {
        k++;
        word += line[k] ?? "";
      } else if (quote === '"' && (line.startsWith("$(", k) || c === "`")) {
        // A substitution runs even inside double quotes: check what it runs.
        let start: number;
        let end: number;
        if (c === "`") {
          start = k + 1;
          end = start;
          while (end < n && line[end] !== "`") end++;
        } else {
          start = k + 2;
          end = start;
          let depth = 1;
          while (end < n && depth > 0) {
            if (line[end] === "(") depth++;
            else if (line[end] === ")") depth--;
            if (depth > 0) end++;
          }
        }
        const found = findClient(line.slice(start, end));
        if (found) return found;
        k = end;
      } else {
        word += c;
      }
      continue;
    }
    switch (c) {
      case "'":
      case '"':
        quote = c;
        haveWord = true;
        break;
      case "\\":
        k++;
        word += line[k] ?? "";
        haveWord = true;
        break;
      case " ":
      case "\t":
        endWord();
        break;
      case ";":
      case "&":
      case "|":
      case "(":
      case ")":
      case "{":
      case "}":
      case "`":
      case "\n": {
        const { name, found } = endCommand();
        if (found) return found;
        // A single | hands this command's output to the next one; || and
        // every other separator do not.
        const pipe = c === "|" && line[k + 1] !== "|" && line[k - 1] !== "|";
        pipedFrom = pipe ? name : "";
        break;
      }
      case "$":
        if (line[k + 1] === "(") {
          const { found } = endCommand();
          if (found) return found;
          pipedFrom = "";
          k++;
        } else {
          word += c;
          haveWord = true;
        }
        break;
      default:
        word += c;
        haveWord = true;
    }
  }
  return endCommand().found;
}
