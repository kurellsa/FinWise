# Claude Instructions

## General Behavior
- Ask clarifying questions when requirements are ambiguous before writing code
- Prefer editing existing files over creating new ones
- Keep solutions simple and focused — do not add unrequested features, refactors, or abstractions
- Do not auto-commit changes unless explicitly asked
- Mark tasks complete only when fully done, not partially

## Security (Top Priority)

Security is non-negotiable. Apply these rules in every task, without exception.

### Secrets & Credentials
- **Never** hardcode API keys, passwords, tokens, or secrets in any file
- All credentials must live in `.env` — never anywhere else
- Never log, print, or expose secret values in output, errors, or comments
- Before running any script that uses credentials, confirm `.env` is gitignored
- If a secret is accidentally exposed, flag it immediately so it can be rotated

### Input & Data Handling
- Treat all external input (user input, API responses, scraped data) as untrusted
- Sanitize and validate inputs before using them in scripts or commands
- Never construct shell commands, SQL queries, or file paths using raw external input (prevents injection attacks)
- Avoid `eval()`, `exec()`, or dynamic code execution with user-supplied data

### Code & Dependency Safety
- Do not introduce new dependencies without checking they are actively maintained and widely trusted
- Prefer well-known, minimal libraries over obscure ones
- Never disable security checks (e.g., `verify=False` in HTTP requests, `--no-verify` in git) without explicit user approval
- Flag any code patterns that could introduce OWASP Top 10 vulnerabilities (injection, broken auth, sensitive data exposure, etc.)

### File & System Operations
- Scope file operations to the project directory — never write outside it without asking
- Do not delete files without explicit user confirmation
- Avoid operations with a large blast radius (recursive deletes, overwriting configs) without user approval

### Before Running Any Script
Ask yourself:
1. Does this script touch credentials or sensitive data?
2. Could it make irreversible changes (delete, overwrite, send data externally)?
3. Does it make paid API calls?

If yes to any — **check with the user first**.

### When You Spot a Security Issue
1. Stop and flag it clearly before proceeding
2. Explain the risk in plain terms
3. Propose a safe fix
4. Only continue after the user approves the fix
