# Systemd Service

Place the unit file here:
`/etc/systemd/system/duckdb-mcp-server.service`

Create a www-data-owned app directory and install deps:
```bash
sudo mkdir -p /var/lib/duckdb-mcp/app
sudo rsync -a --exclude .venv /scratch/jmc/BERDL-ENIGMA-CORAL/duckdb-mcp-server/ /var/lib/duckdb-mcp/app/
sudo chown -R www-data:www-data /var/lib/duckdb-mcp/app
sudo rm -rf /var/lib/duckdb-mcp/app/.venv
sudo -u www-data /lab/bin/uv sync --project /var/lib/duckdb-mcp/app
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

Optional schema comments:
- Set `Environment=DUCKDB_SCHEMA_MARKDOWN_PATH=/path/to/enigma_coral_schema.md`
  to provide column comments for the schema endpoint.
