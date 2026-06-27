# SafeHaven Concierge 🛡️ (Concierge Track)

SafeHaven Concierge is a production-grade, zero-trust, multi-agent supervisor system designed to handle sensitive document decryption workflows securely. It wraps around a custom **FastMCP background server** to mitigate typical LLM file access vulnerabilities—such as Local File Inclusion (LFI), path traversal exploits, and prompt credential leaks—by decoupling sensitive keys entirely from the LLM's direct context window.

Agent initialized with `agents-cli` version `0.5.1`.

## 📂 Project Structure

```
safehaven-agent/
├── app/                        # Core agent logic
│   ├── agent.py                # Multi-agent supervisor & node graph orchestration
│   ├── agent_runtime_app.py    # Main application runtime file
│   └── mcp_decryption_server.py # Unified AES-256 Fernet MCP Decryption Server
├── tests/
│   └── unit/
│       └── test_supervisor.py  # Comprehensive security & isolation boundary unit tests
├── pyproject.toml              # Dependencies & package configurations
└── README.md                   # Project documentation
```

## 🔒 The Security Story & Architecture

Traditional AI assistants often execute tools by passing raw text keys or unverified file paths straight to subprocess commands, opening the door to resource leaks and path traversal injection. SafeHaven neutralizes these threats through a custom three-layer security model:

1. **Pre-Execution Security Node & PII Scrubbing:** Before a prompt ever reaches the core reasoning agents, an adversarial filter intercepts the text stream. It blocks directory backtracking sequences (`..`) and malicious bypass keywords (`bypass safety`), extracts sensitive decryption keys into an isolated memory segment (`ctx.state`), and scrubs the raw keys out of the prompt window (replacing them with `[SCRUBBED_KEY]`).
2. **In-Memory Tool Isolation:** To prevent performance lag and execution hangs from running raw shell subprocesses, the `execution_agent` securely passes variables from isolated memory directly to local execution loops.
3. **Absolute Path Confinement:** Inside `mcp_decryption_server.py`, incoming file paths are anchored using `os.path.abspath(os.path.normpath(...))`. The application uses `os.path.commonpath` comparisons to ensure any attempt to traverse outside the workspace boundaries triggers an immediate rejection.
4. **URL-Safe Fernet Key Derivation:** Plain text passphrases are securely processed into a stable 32-byte hash using SHA-256 and wrapped in URL-safe Base64 encoding to initialize the underlying cryptographic engine safely without runtime exceptions.

---

## 🚀 Requirements & Quick Start

Ensure you have the following installed in your local system environment:
* **uv**: Python package manager
* **agents-cli**: Google Agents CLI tool

### 1. Synchronize Dependencies
Install required workspace packages:
```bash
agents-cli install
```

### 2. Run the Automated Security Tests
A comprehensive test suite validates backtracking protection, boundary enforcement checks, PII context scrubbing logic, state variable parsing, and secure decryption pipelines:

```powershell
.\.venv\Scripts\python.exe -m unittest tests/unit/test_supervisor.py
```

---

## 🛠️ Execution Commands

Open separate terminal windows inside your project root folder (`safehaven-agent`) to run the system:

| Target Component | Command | Description |
| --- | --- | --- |
| **Terminal 1: MCP Server** | `.\.venv\Scripts\python.exe -m app.mcp_decryption_server` | Boots the secure background tool server over standard I/O communication channels. |
| **Terminal 2: Agent App** | `.\.venv\Scripts\python.exe -m app.agent_runtime_app` | Launches your core multi-agent runtime application graph. |
| **Interactive Terminal** | `agents-cli playground` | Launches the interactive local playground developer environment. |
| **Direct Prompt Run** | `agents-cli run "Decrypt secret.enc with key SV_SAFE_2026"` | Executes a specific isolated target prompt string through the full zero-trust pipeline. |

---

## 📊 Telemetry & Observability

Built-in telemetry exports natively to Cloud Trace, BigQuery, and Cloud Logging when running in a cloud configuration environment. For offline or local developer environments, errors and tracing payloads are securely routed as text strings back to the supervisor node to maintain protocol stability.