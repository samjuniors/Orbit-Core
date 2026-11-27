# Orbit Core for Claude Code

Orbit Core adds a local MCP server, specialist-agent definitions and the Orbit workflow skill to Claude Code. It is designed to help with project discovery, bounded codebase audits, source-review signals, task planning, evidence tracking and project-scoped workflow coordination.

## What is included

- The orbit-core-mcp stdio MCP server, launched from this plugin's runtime directory.
- Orbit specialist-agent definitions and the Orbit skill with supporting workflow references.
- Read-only discovery and audit tools, plus explicitly guarded task and workflow actions.
- Optional lifecycle-hook configuration kept separate from the default plugin hooks.

## Requirements

- Claude Code with plugin support.
- Python 3.10 or later available on PATH.
- If the default Python executable is not the intended interpreter, configure the ORBIT_PYTHON environment variable to point to it.

The plugin MCP manifest starts runtime/orbit_mcp.py using the configured Python executable. The server runs locally as a standard input/output MCP process.

## Installation and validation

In Claude Code, install the marketplace plugin with:

    /plugin install orbit-core --marketplace samjuniors/Orbit-Core

Install Orbit Core through the Orbit Core marketplace entry in Claude Code. Review the permissions and tools exposed by the plugin before using write-capable actions.

Validate the plugin directory from the repository root:

    claude plugin validate plugins/claude-code/orbit-core

The marketplace manifest is at .claude-plugin/marketplace.json.

## Safe-use notes

- A local MCP server does not mean the language model is offline. Model requests follow the provider and account configuration of the Claude Code host.
- Write-capable Orbit actions require their documented confirmation and revision checks. Do not remove those checks or grant broad host permissions to bypass a denial.
- The optional lifecycle-hook file under hooks/optional/ is not automatically activated. Review it and explicitly opt in only if lifecycle event recording is wanted.
- Project audit results are evidence and review signals, not automatic proof that a defect exists or that a project is secure.
- Model recommendations do not switch the active Claude model, infer account quota, or grant tools.
- Orbit does not automatically merge, publish, deploy, change host permissions, or expand a task's approved write scope.

## Data and privacy

The MCP server runs on the local machine and maintains its own bounded project/workflow records. Context that Claude Code sends to its configured model provider remains subject to that provider's data handling and the user's Claude Code configuration. Review project content and provider settings before using the plugin with sensitive repositories.

## Support

Report reproducible defects and security concerns in the Orbit Core GitHub repository. Include the Orbit version, Claude Code version, operating system, relevant tool name and a minimal reproduction. Do not attach secrets, access tokens or private source files unless they are necessary and safe to disclose.

Orbit Core is licensed under the MIT License.


