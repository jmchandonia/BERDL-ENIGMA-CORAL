# Systemd Service

Place the unit file here:
`/etc/systemd/system/duckdb-mcp-server.service`

Create a www-data-owned venv and install deps:
```bash
sudo mkdir -p /var/lib/duckdb-mcp
sudo chown www-data:www-data /var/lib/duckdb-mcp
sudo -u www-data mkdir -p /var/lib/duckdb-mcp/venv
sudo -u www-data /lab/bin/uv venv /var/lib/duckdb-mcp/venv
sudo -u www-data UV_PROJECT_ENV=/var/lib/duckdb-mcp/venv /lab/bin/uv sync --project /scratch/jmc/BERDL-ENIGMA-CORAL/duckdb-mcp-server --python /var/lib/duckdb-mcp/venv/bin/python
```

Start and enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable duckdb-mcp-server
sudo systemctl start duckdb-mcp-server
```

Check status:
```bash
sudo systemctl status duckdb-mcp-server
```

DuckDB path:
- Default is `/scratch/jmc/linkml-coral/cdm_store_bricks_full.db`.
- Override via `Environment=DUCKDB_PATH=...` in the unit file.
