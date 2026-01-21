# BERDL-ENIGMA-CORAL

Tools for querying ENIGMA data from CORAL in BERDL using AI.

## Authentication

These tools use a KBase auth token. You can create one in KBase by going to
Account and then Developer Tokens.

Set the token in your environment before running any tools:

```bash
export KB_AUTH_TOKEN="your-token-here"
```

For tcsh:

```tcsh
setenv KB_AUTH_TOKEN "your-token-here"
```

For Windows PowerShell:

```powershell
$env:KB_AUTH_TOKEN = "your-token-here"
```

For Windows Command Prompt:

```bat
set KB_AUTH_TOKEN=your-token-here
```

To use a local `.env` file instead, create `.env` in the repo root with:

```
KB_AUTH_TOKEN=your-token-here
```

Then load it before running tools:

```bash
set -a
source .env
set +a
```

## Output locations

By default, table dumps and the schema markdown are written to the `schema`
directory in this repo. You can override the output directory with
`BERDL_OUTPUT_DIR`.
