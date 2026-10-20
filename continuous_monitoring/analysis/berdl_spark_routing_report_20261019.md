# BERDL Spark Connect routes user `jmc` to another user's cluster

**Reported by:** John-Marc Chandonia (KBase user `jmc`)

**Summary:** since at least 2026-10-19 21:43Z, every off-cluster Spark Connect
session for user `jmc` is rejected with:

```
grpc status: StatusCode.PERMISSION_DENIED
details: User 'jmc' is not authorized to access this cluster. This cluster belongs to 'praba_kbase'.
```

The same client code and route last worked at 2026-10-17 01:59Z. No change was
made on the client side between then and the first failure, apart from
restarts during troubleshooting.

## Client and route

| | |
|---|---|
| Client hosts | dipa (Debian 13, Linux 6.12, Python 3.13.5); the same error also occurs from a second host, stout |
| Libraries | pyspark 4.1.1 (Spark Connect), spark_connect_remote 0.2.0, berdl_remote 0.1.0, grpcio 1.84.0 |
| Network path | SSH SOCKS tunnel through `ac.jmchandonia@login1.berkeley.kbase.us` (`-D 1338`), then pproxy HTTP→SOCKS on 127.0.0.1:8123, with `grpc_proxy`/`https_proxy` set to it |
| Connection | `spark_connect_remote.create_spark_session(host_template=<host>, port=443, use_ssl=True, kbase_token=<jmc token>)`, i.e. `sc://<host>:443/;use_ssl=true;x-kbase-token=<redacted>` |
| Hosts tried | `metrics.berdl.kbase.us` and `spark.berdl.kbase.us`; both give the same error |
| Token | Valid. `spark_connect_remote` validates it as user `jmc`, and the server error names `jmc` too. It expires 2026-10-28. |

## Observations (UTC)

| Time | Event |
|---|---|
| 2026-10-17 01:38–01:59 | Last successful sessions: a 1.47M-row load and a daily append into `enigma.continuous_monitoring`. |
| 2026-10-19 21:43 | First observed failure: PERMISSION_DENIED, cluster belongs to `praba_kbase`. |
| 2026-10-19 21:58–22:00 | Same error in a full scheduled-style run, after the Hub server was confirmed running (`berdl-remote login`, then `spawn`, "Server is ready"). |
| 2026-10-19 22:08:38–22:08:39 | Diagnostics before the restart: same error on both hosts. Hub API reports server `default` ready, started 22:06:34Z. |
| 2026-10-19 22:08:47 | Stopped the Hub server (`DELETE /hub/api/users/jmc/server`, HTTP 204) and confirmed it stopped. |
| 2026-10-19 22:08:48–22:09:51 | Fresh `berdl-remote login` (OK), fresh `spawn` ("Server is ready", new kernel), and a fresh SSH tunnel and pproxy. |
| 2026-10-19 22:10:52 | 60 s after the new server came up: same PERMISSION_DENIED (`praba_kbase`) on both hosts. Hub API reports the new server ready, started 22:08:49Z. |

## Other notes

- JupyterHub REST calls work normally from the same route: user API, spawn,
  stop and token creation.
- The kernel WebSocket used by `berdl-remote python`/`shell` returned
  `403 Forbidden` with an HTML body (about 5.7 KB, with `accept-ch:
  Sec-CH-UA-*` headers). This looks like a Cloudflare challenge page, so the
  check of in-cluster Spark from inside the user's Jupyter pod could not run.
- It looks as though the Spark Connect gateway, or its routing table, maps
  `jmc`'s session to the Spark Connect service of user `praba_kbase` instead
  of `jmc`'s own.

## Reproduce

```python
from spark_connect_remote import create_spark_session
spark = create_spark_session(host_template="metrics.berdl.kbase.us", port=443, use_ssl=True, kbase_token=TOKEN)
spark.sql("SELECT current_user()").collect()
# -> SparkConnectGrpcException PERMISSION_DENIED: User 'jmc' is not authorized to access this cluster. This cluster belongs to 'praba_kbase'.
```

The diagnostic script is `continuous_monitoring/analysis/berdl_spark_diag.py`
in BERDL-ENIGMA-CORAL; run it with `--restart` to repeat the restart sequence.
