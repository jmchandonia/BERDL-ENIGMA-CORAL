# Systemd Service

Place the unit file here:
`/etc/systemd/system/duckdb-mcp-server.service`

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
