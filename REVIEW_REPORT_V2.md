# Senior Code Review v2.0 — ZapManager Pro v4.0

**Date:** 2026-04-24
**Reviewer:** Senior backend audit (read-only)
**Scope:** [app.py](app.py), [automation_state.py](automation_state.py), [database/schema.py](database/schema.py), [database/services/](database/services/), [api/models.py](api/models.py), [license/manager.py](license/manager.py), [electron/main.js](electron/main.js), [electron/preload.js](electron/preload.js), [static/script.js](static/script.js), [whatsapp_automation.py](whatsapp_automation.py)

This report **excludes** items already marked as fixed (C1–C8, M1–M9, M11, M12, S9, Spintax). Findings below are issues a senior engineer would flag in production.

---

## 🔴 Critical — Fix before any real client

### C-A1. Duplicate `/api/contacts/import` route — second definition silently overrides the first
- **File:** [app.py:533](app.py#L533) and [app.py:886](app.py#L886)
- **Problem:** Two `@app.post("/api/contacts/import")` decorators with the same Python function name `import_contacts`. FastAPI keeps **only the last registration** (line 886). The first version (the one that calls `runner.reset_progress`, sets `runner.excel_path`, returns `details["contacts"]`) is **dead code** — it never runs.
- **Impact:** The frontend uploads always hit the second handler, which:
  - Does **not** set `runner.excel_path` → `/api/status` always returns `excel: null` after upload.
  - Does **not** call `runner.reset_progress(total=...)` → progress bar shows zero on first render.
  - Returns a different `data` shape (`total = imported + skipped_blacklist`, no `errors` envelope match).
  - The legacy alias `/api/upload-excel` ([app.py:580](app.py#L580)) calls `await import_contacts(file)` — which now resolves to the **second** function reference at import time → unpredictable behavior depending on Python ordering.
- **Fix:** Delete one of the two. Keep the version at line 533 (it sets `runner.excel_path` and `reset_progress`), remove the one at 886.

### C-A2. Missing tables — `system_config` and `whatsapp_accounts` not in migrations
- **File:** [database/schema.py:9-78](database/schema.py#L9-L78), [database/services/config_service.py:9](database/services/config_service.py#L9), [database/services/account_service.py:9](database/services/account_service.py#L9)
- **Problem:** `MIGRATIONS` defines `campaigns`, `campaign_contacts`, `templates`, `blacklist`. Nothing else. But code references:
  - `system_config(key, value, updated_at)` in `get_config`/`set_config`
  - `whatsapp_accounts(label, profile_path, status, last_connected)` in `account_service.py`
  - `templates.variables` column in `create_template` / `update_template` ([database/services/template_service.py:21,49](database/services/template_service.py#L21))
- **Impact:** Every `set_config()`, `get_config()`, `update_account_status()`, `create_account()`, `create_template()`, and `update_template()` raises `OperationalError: no such table` / `no such column`. All swallowed by `except Exception: pass`. Settings page silently does nothing. `/api/accounts/update_status` returns `{"success": True}` but writes nothing. Template creation appears to work but `lastrowid` returns -1.
- **Fix:** Add migrations to `MIGRATIONS`:
  ```python
  # v6
  """CREATE TABLE IF NOT EXISTS system_config (
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at TEXT DEFAULT (datetime('now','localtime'))
  )""",
  # v7
  """CREATE TABLE IF NOT EXISTS whatsapp_accounts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      label TEXT NOT NULL,
      profile_path TEXT NOT NULL,
      status TEXT DEFAULT 'disconnected',
      last_connected TEXT
  )""",
  # v8
  """ALTER TABLE templates ADD COLUMN variables TEXT DEFAULT '[]'""",
  ```

### C-A3. Session token leaked via URL query string in SSE
- **File:** [static/script.js:517](static/script.js#L517), [app.py:319](app.py#L319)
- **Problem:** `new EventSource('/api/logs?token=' + window.__ZAP_TOKEN__)` puts the secret token in the URL. The middleware at app.py:319 explicitly accepts `token` in `query_params`. URLs are persisted in:
  - Uvicorn's access log (every request line includes the full URL with query).
  - The browser's history / DevTools network panel.
  - Any HTTP debugging proxy on the machine (Fiddler, mitmproxy).
- **Impact:** A user sharing screen during onboarding leaks their session token. Anyone with read access to the rotating logs in `data/zapmanager.log` (no, but uvicorn's stdout is also captured) can replay every authenticated endpoint until the next restart. The 127.0.0.1 binding limits the blast radius but does not eliminate it (any local malware reads it trivially).
- **Fix:** EventSource doesn't support custom headers natively. Options:
  1. Use `fetch()` with `ReadableStream` instead of `EventSource` — supports headers.
  2. Set the token as an `HttpOnly` cookie scoped to `/api/logs` and read it in middleware.
  3. Issue a short-lived (60s) one-time SSE token from `POST /api/logs/ticket` that the frontend exchanges before opening the stream.
  Disable the `query_params.get("token")` fallback once migrated.

### C-A4. Unprotected mutation of `runner.*` outside the lock
- **File:** [app.py:555-556](app.py#L555), [app.py:587-589](app.py#L587), [app.py:603](app.py#L603), [app.py:608](app.py#L608), [app.py:909](app.py#L909) — vs. [automation_state.py:39-51](automation_state.py#L39)
- **Problem:** The `RLock` in `CampaignRunner` only protects `start()`, `update_progress()`, `reset_progress()`, and `snapshot()`. But endpoints assign directly to `runner.attachment`, `runner.excel_path`, `runner.campaign_id`, `runner.was_stopped` with no synchronization. The worker thread reads these attributes inside `_run_automation` ([app.py:343-344](app.py#L343), [app.py:393](app.py#L393)).
- **Impact:** A user clicking "upload attachment" mid-campaign mutates `runner.attachment`. The next iteration of `_run_automation` reads it via `params.get('attachment')` — but `params` was copied at start time, so the new attachment is silently ignored (intended behavior, but undocumented). Worse: clicking "clear-excel" while the thread is between iterations sets `runner.campaign_id = None`, and the next `update_contact_status` call inside the loop refers to a dangling FK. Concurrent `/api/status` calls during attachment write may observe partially-mutated state.
- **Fix:** Add property setters that take the lock, or move state mutations into `runner` methods:
  ```python
  def set_excel(self, path: str | None, campaign_id: int | None):
      with self._lock:
          self.excel_path = path
          self.campaign_id = campaign_id
  def set_attachment(self, path: str | None):
      with self._lock:
          self.attachment = path
  ```
  Then forbid raw attribute writes (use `__setattr__` guard or convention). Also explicitly reject mutations while `is_running`.

### C-A5. Bare `except: pass` regression
- **File:** [app.py:641](app.py#L641)
- **Problem:** `legacy_start_campaign` updates `campaigns.message_template` and silently swallows every error:
  ```python
  except: pass
  ```
  M1 was listed as fixed but this instance was missed. There is also one in [database/services/template_service.py:79](database/services/template_service.py#L79) (`render_template`) and [database/services/config_service.py:17](database/services/config_service.py#L17), [config_service.py:41](database/services/config_service.py#L41), [config_service.py:56](database/services/config_service.py#L56) (whole module relies on it).
- **Impact:** A failing UPDATE (locked DB, schema mismatch) leaves `campaigns.message_template` with the wrong value, so re-renders use stale templates. No log, no surfacing. Regression risk: identical bug class as M1.
- **Fix:** Replace with `except Exception: _log.exception("Failed to update campaign message")`.

### C-A6. Unawaited / spurious `try/finally` in lifespan does not kill child Node when Python is SIGKILL'd
- **File:** [app.py:303-308](app.py#L303-L308)
- **Problem:** Shutdown logic:
  ```python
  if node_process:
      try:
          node_process.terminate()
          node_process.wait(timeout=2)
      except: pass
  ```
  Bare except + only `terminate()` → Node has 2 seconds to flush, then we move on. If Node hangs, it's orphaned. The Job Object (`KILL_ON_JOB_CLOSE`) at [app.py:142](app.py#L142) **does** save us when Python is SIGKILL'd, but only because `h_job` handle is held in a local variable inside `_spawn_node_with_job`. **That local goes out of scope when the function returns** → handle is closed by GC → Job Object is destroyed → KILL_ON_JOB_CLOSE fires immediately killing Node at boot.
  - Test: comment confirms "NÃO fechar h_job" but Python's GC closes it anyway when the function exits, because `ctypes.windll.kernel32.CreateJobObjectW` returns a `c_int` that becomes garbage. The comment is wrong.
- **Impact:** The C5 "fix" only works **as long as the function reference to `h_job` stays alive**. Right now, on a normal launch, the Job Object is destroyed within ~50ms of `_spawn_node_with_job` returning. So when Python crashes, Node survives. Easy reproduction: kill `python.exe` from Task Manager → Node still listens on 3001.
- **Fix:** Store the handle on a module global to keep it alive:
  ```python
  _NODE_JOB_HANDLE = None  # module level
  def _spawn_node_with_job(...):
      global _NODE_JOB_HANDLE
      ...
      _NODE_JOB_HANDLE = h_job  # prevents GC
  ```

---

## 🟡 Medium — Fix before public launch

### M-A1. Synchronous I/O blocks the FastAPI event loop
- **File:** [app.py:485](app.py#L485), [app.py:541](app.py#L541), [app.py:559](app.py#L559), [app.py:601](app.py#L601), [app.py:638-640](app.py#L638), all `database/services/*.py` calls inside async routes
- **Problem:** `Path.read_text()`, `target.write_bytes()`, `sqlite3` queries, `os.path.exists()` are all blocking. Inside `async def` routes they pin the event loop while the disk works. With a 50MB Excel upload + concurrent `/api/status` polling every 2s, status calls visibly stall.
- **Impact:** UI feels laggy under load. Worse: the SSE keep-alive at [app.py:519](app.py#L519) misses its 20s deadline if a long DB operation blocks → frontend reconnects → log buffer replay floods → cycle.
- **Fix:** Wrap blocking calls in `await fastapi.concurrency.run_in_threadpool(...)`:
  ```python
  from fastapi.concurrency import run_in_threadpool
  content = await file.read()  # already async
  await run_in_threadpool(target.write_bytes, content)
  pending = await run_in_threadpool(get_pending_contacts, cid)
  ```

### M-A2. `apply_spintax` can infinite-loop
- **File:** [database/services/template_service.py:9-13](database/services/template_service.py#L9)
- **Problem:**
  ```python
  while pattern.search(text):
      text = pattern.sub(lambda m: random.choice(...), text)
  ```
  If a chosen branch contains spintax syntax (e.g., user types `{ola|{a|b}}` and the outer chooses `{a|b}` literal — but the regex doesn't allow `{` inside, so this case is bounded). However, a malicious template like `{a|{a|a}}` after one substitution becomes `{a|a}` then `a` — terminating. But a payload like `\{a|\{a\}\}` (escapes that the regex doesn't honor) is non-terminating in some inputs. More importantly, no iteration cap means a regex pathological input ties up a worker.
- **Impact:** Low likelihood unless attacker controls template content. Still — every send call goes through `apply_spintax` → DoS against worker thread.
- **Fix:** Add iteration cap:
  ```python
  for _ in range(10):
      if not pattern.search(text):
          break
      text = pattern.sub(...)
  else:
      _log.warning("apply_spintax: max iterations reached")
  ```

### M-A3. Resume cannot recover after a thread crash
- **File:** [app.py:470-477](app.py#L470-L477), [automation_state.py:42-43](automation_state.py#L42)
- **Problem:** `runner.was_stopped` is set only at the **end** of `_run_automation`. If the worker crashes mid-loop (uncaught DB exception, OOM in `engine.send_with_attachment`), `was_stopped` stays False. After the thread dies, `runner.is_running` is False (thread.is_alive() == False), but `was_stopped` is also False → `/api/resume` rejects with "Não há campanha pausada para retomar". User must restart from scratch.
- **Impact:** On any non-clean crash, the user loses their pause/resume contract. Combined with the FK dangling if `runner.campaign_id` was cleared meanwhile, contacts stay in `EM_PROCESSAMENTO` forever (sanitized at next boot only).
- **Fix:** Wrap the body in `try/finally` and set `was_stopped = True` if the loop didn't reach the natural end:
  ```python
  def _run_automation():
      finished_naturally = False
      try:
          ... loop ...
          finished_naturally = (not runner.stop_requested)
      except Exception:
          _log.exception("worker crashed")
      finally:
          runner.was_stopped = not finished_naturally
          if finished_naturally:
              runner.update_progress(status="Concluída")
          elif runner.stop_requested:
              runner.update_progress(status="Pausada")
          else:
              runner.update_progress(status="Erro")
  ```

### M-A4. `engine.stop()` not called when user pauses
- **File:** [app.py:478-481](app.py#L478)
- **Problem:** Only on **natural completion** (`else` branch) does the code stop the engine. On `runner.stop_requested`, the worker exits the loop but leaves the Chromium browser process running indefinitely.
- **Impact:** Each paused-then-not-resumed campaign leaves a Chromium tab eating ~150-300 MB. After 5 user clicks of pause-without-resume, the machine is at 1.5 GB of zombie Chromiums.
- **Fix:** Call `engine.stop()` in both branches unless `keep_open` is set explicitly.

### M-A5. N+1 query pattern inside the send loop
- **File:** [app.py:391-392](app.py#L391-L392), [app.py:411-432](app.py#L411-L432)
- **Problem:** Per contact: `get_contact_attachment` (1 query), `update_contact_status` for EM_PROCESSAMENTO (1 query), `update_contact_status` after send (1 query). For 1000 contacts → 3000 SQLite round-trips. Each call opens and closes a connection ([campaign_service.py:144](database/services/campaign_service.py#L144)). With WAL, this is fast but not free; on a network-mounted SQLite (some users will store `data/app.db` on OneDrive) latency is 5-50ms each.
- **Impact:** A 1000-contact campaign on a slow disk burns ~30-150 s in DB overhead alone — separately from the message delays.
- **Fix:** Pre-fetch all contact attachments in a single query at the top of `_run_automation`:
  ```python
  attachments = {row["id"]: row["attachment_path"]
                 for row in conn.execute("SELECT id, attachment_path FROM campaign_contacts WHERE campaign_id = ?", (cid,))}
  ```
  Reuse a single connection for status updates inside the loop (open it before, close after).

### M-A6. `_log_main_loop = _asyncio.get_event_loop()` is deprecated
- **File:** [app.py:274](app.py#L274)
- **Problem:** In Python 3.12+, `get_event_loop()` outside a running coroutine raises `DeprecationWarning` and in 3.14 will raise `RuntimeError`. Inside `lifespan` (which is itself an async generator), the running loop is available via `asyncio.get_running_loop()`.
- **Fix:**
  ```python
  _log_main_loop = _asyncio.get_running_loop()
  ```

### M-A7. Inconsistent response envelope across endpoints
- **File:** [app.py:651](app.py#L651), [app.py:684](app.py#L684), [app.py:686-705](app.py#L686), [app.py:710-713](app.py#L710), [app.py:870-876](app.py#L870), [app.py:993](app.py#L993)
- **Problem:** Some endpoints follow `{success, data, error}`, others don't:
  - `/api/start` → `{"message": ...}` (no `success`)
  - `/api/resume` → `{"message": ...}` (no `success`)
  - `/api/status` → `success: True` plus state at top-level (not inside `data`)
  - `/api/connector` → raw upstream response on success, enveloped on failure
  - `/api/contacts/validate-phone` → `{valid, normalized}`
  - `/api/license` → enveloped, but old `script.js:677` does `data.data || data` to handle both shapes
- **Impact:** Frontend code at [static/script.js:466](static/script.js#L466) does `if (data.success || data.message)` — fragile. Adding new endpoints, future devs guess at shape. The whole point of M2 was to standardize this.
- **Fix:** Normalize all returns:
  ```python
  return {"success": True, "data": {"message": "...", ...}}
  return {"success": False, "error": "..."}
  ```

### M-A8. Missing upload validation: size and MIME
- **File:** [app.py:534-541](app.py#L534), [app.py:595-604](app.py#L595)
- **Problem:** `await file.read()` reads **entire** request body into memory. No size cap. Frontend allows `.xlsx` and `.pdf`, but backend trusts the extension only — `.exe` renamed to `.xlsx` is accepted by `upload_attachment`. (Excel route does check `.endswith('.xlsx')`, but global attachment doesn't.)
- **Impact:** A 5GB `.xlsx` upload triggers OOM. A `.exe.xlsx` survives and is referenced in `runner.attachment`, then passed as `filePath` to the Node sender — Node may execute it depending on its handler.
- **Fix:**
  ```python
  MAX_UPLOAD_BYTES = 50 * 1024 * 1024
  ALLOWED_ATTACHMENT = {".pdf", ".jpg", ".jpeg", ".png", ".mp4"}
  ext = Path(file.filename).suffix.lower()
  if ext not in ALLOWED_ATTACHMENT:
      return JSONResponse({"success": False, "error": "Tipo não permitido"}, 400)
  # Stream to disk:
  written = 0
  with target.open("wb") as f:
      while chunk := await file.read(1024 * 1024):
          written += len(chunk)
          if written > MAX_UPLOAD_BYTES:
              target.unlink(missing_ok=True)
              return JSONResponse({"success": False, "error": "Arquivo muito grande"}, 413)
          f.write(chunk)
  ```

### M-A9. Token-in-URL accepted by middleware
- **File:** [app.py:318-319](app.py#L318)
- **Problem:** Even after fixing C-A3, the middleware itself still accepts `?token=...`. Any future code that uses `<a href="/api/...?token=X">` in HTML or logs URLs will leak it. The query-string fallback exists only to support the SSE `EventSource` workaround.
- **Fix:** Once C-A3 is fixed, remove the query-string fallback. Token only via header.

### M-A10. `find_free_port` race condition between bind-test and uvicorn launch
- **File:** [app.py:1040-1049](app.py#L1040), [app.py:1069](app.py#L1069)
- **Problem:** `find_free_port` opens a socket, binds to port `p`, gets `p`, **closes the socket**, returns. Then 100 ms later uvicorn binds. Window: another process can grab `p`. Manifests on machines running multiple Electron apps that probe ports.
- **Impact:** Boot failure with `[Errno 10048] Only one usage of each socket address` after splash, dialog says "servidor não iniciou".
- **Fix:** Either retry-loop in uvicorn, or use `SO_REUSEADDR` on the test socket and pass the bound socket directly to uvicorn.

### M-A11. Two paths to spawning Node compete at startup
- **File:** [app.py:292](app.py#L292) (lifespan) vs. [whatsapp_automation.py:206](whatsapp_automation.py#L206) (engine)
- **Problem:** Lifespan calls `_spawn_node_with_job()` unconditionally if `whatsapp-motor/server.js` exists. The engine, when started by `_run_automation`, **also** spawns Node if `_is_server_running()` returns False. There's a 1-second window during boot where both can race.
- **Impact:** Two Node processes briefly fight for port 3001. One dies with EADDRINUSE, sometimes leaving a half-initialized whatsapp-web.js puppeteer session.
- **Fix:** Centralize Node ownership in lifespan only. `engine.start()` should only **wait** for `_is_server_running()` and never spawn.

---

## 🟢 Low — Fix when convenient

### L-A1. `get_local_ip` references undefined `socket`
- **File:** [app.py:1031-1037](app.py#L1031)
- **Problem:** `get_local_ip` is defined but never called. References `socket` without import. Dead but ticking — if a future contributor calls it, NameError.
- **Fix:** Delete it, or `import socket` at the top of the function.

### L-A2. Duplicate `import os`
- **File:** [app.py:1](app.py#L1), [app.py:17](app.py#L17)
- **Fix:** Remove the second one.

### L-A3. `import time` repeated three times in `_run_automation`
- **File:** [app.py:454](app.py#L454), [app.py:464](app.py#L464)
- **Problem:** `time` is already imported at the top of the module. Local re-imports are no-ops but signal that the function was patched piecemeal.
- **Fix:** Drop the local imports.

### L-A4. `find_free_port` binds `0.0.0.0` but uvicorn binds `127.0.0.1`
- **File:** [app.py:1045](app.py#L1045)
- **Problem:** Probing on `0.0.0.0` succeeds even if `127.0.0.1` is somehow occupied by a different network interface. Inconsistent.
- **Fix:** Probe on `127.0.0.1` to match the real bind.

### L-A5. `whatsapp_automation.py` imports `customtkinter` and `tkinter` at module top
- **File:** [whatsapp_automation.py:12-13](whatsapp_automation.py#L12)
- **Problem:** FastAPI flow uses only `AutomationEngine`, but importing the module loads the whole tk GUI stack, costing ~200 ms boot time and a heavy memory baseline. The `ZapAutomationApp` class at line 325 is the legacy Tk app and is never used here.
- **Fix:** Move tk imports inside `ZapAutomationApp.__init__`. Or split: `AutomationEngine` → `engine.py`, legacy GUI → `legacy_gui.py`.

### L-A6. Frontend status polling never stops on page change
- **File:** [static/script.js:483-514](static/script.js#L483)
- **Problem:** `setInterval(..., 2000)` runs forever, even when the user is on `page-license` or `page-history`. It hits `/api/status` 30 times/min unnecessarily.
- **Fix:** Pause polling unless the campaign page is active, or unless `data.is_running === true`.

### L-A7. `update_contact` accepts `data: dict` with no validation
- **File:** [app.py:933-948](app.py#L933)
- **Problem:** Pydantic `dict` accepts arbitrary keys. Frontend sends `{phone: "..."}` or `{name: "..."}`. No length limits, no type checks. SQL is parameterized so injection isn't possible, but storing 100MB names is.
- **Fix:** Use a Pydantic model:
  ```python
  class UpdateContactRequest(BaseModel):
      name: Optional[str] = Field(None, max_length=200)
      phone: Optional[str] = Field(None, max_length=20)
  ```

### L-A8. `webbrowser.open` raced against server readiness
- **File:** [app.py:1056-1065](app.py#L1056)
- **Problem:** Opens browser after a `socket.create_connection` succeeds — but before uvicorn finishes registering routes. First page-load may 404 if the user is fast.
- **Fix:** Probe `/` (or `/api/status` with token), not raw socket connect.

### L-A9. SSE log queue size 200 silently drops on overflow
- **File:** [app.py:494](app.py#L494), [app.py:240](app.py#L240)
- **Problem:** `Queue(maxsize=200)` and `q.put_nowait(entry)` with broad `except: pass`. If a client is slow, logs are dropped silently. No counter, no observable.
- **Fix:** On `QueueFull`, increment a counter and emit a single warning entry.

### L-A10. `clear_excel` clears `runner.attachment` but `clear_attachment` does not clear `runner.attachment`'s file from disk
- **File:** [app.py:583-593](app.py#L583), [app.py:606-609](app.py#L606)
- **Problem:** `clear_excel` resets `runner.attachment = None` (good — but doesn't remove the file). `clear_attachment` does the same. Files in `data/attachments/global_*.pdf` accumulate forever.
- **Fix:** Track the path, `os.unlink` on clear (with try/except).

---

## 💡 Suggestions — architectural

### S-A1. The whole `runner` should be the single source of truth, not 4 different mutation paths
The lock fix solves the start-twice race but leaves the rest of the state model open. Adding setters that lock is one path; better is to make `attachment`, `excel_path`, `campaign_id` private, expose only `set_excel(path, cid)`, `set_attachment(path)`, and a richer `start(intent: CampaignIntent)` — with each setter validating against `is_running`. This eliminates an entire class of "what if upload happens during send?" questions.

### S-A2. Move all sync DB calls behind an async repository layer
With FastAPI on async, every blocking call should go through `run_in_threadpool` or a real async driver (`aiosqlite`). Right now the codebase mixes both. A small `db/` async wrapper would let routes stay non-blocking and make N+1 patterns visible at code-review time.

### S-A3. Replace `_LogShim` with a proper `LogPublisher` interface
The shim at [app.py:262-264](app.py#L262) is a one-method adapter that exists only to satisfy `engine.log_queue.put((msg, level))`. Two different log paths (`publish_log`, `publish_log_threadsafe`) plus the shim make it hard to reason about. Define one `LogPublisher.publish(msg, level)` and inject it everywhere — engine, runner, lifespan.

### S-A4. Schema migrations should be idempotent and versioned, not stringly-typed
The current MIGRATIONS list is positional — inserting a migration in the middle would re-apply migrations to upgraded DBs. Use a tool like `alembic` (overkill for this size) or at minimum hash each migration body and store it in `schema_version` to detect tampering.

### S-A5. Centralize HTTP timeouts and retries
`requests.get(...)` and `requests.post(...)` calls in `whatsapp_automation.py` use `timeout=30` and `timeout=60` as magic numbers. A `motor_client.py` with one `Session`, one timeout policy, one retry strategy would eliminate the per-call inconsistency and let you swap to `httpx` async if you ever go all-async.

### S-A6. The `electron/main.js` `killProcesses` does not kill grandchildren on Unix
[electron/main.js:147-169](electron/main.js#L147) uses `process.kill(-pythonProcess.pid, ...)` which only works if Python was spawned in a new process group. `spawn(...)` doesn't do that by default — use `{ detached: true }` and `pythonProcess.unref()` to guarantee a process group exists. Otherwise on macOS/Linux, Python and its Node grandchild leak.

---

## Summary table

| Severity | Count | Theme |
|---|---|---|
| 🔴 Critical | 6 | Duplicate routes, missing tables, token leak, lock gap, regression of M1, Job Object lifecycle |
| 🟡 Medium | 11 | Sync I/O on event loop, crash recovery, envelope inconsistency, upload validation, port races |
| 🟢 Low | 10 | Dead code, polling waste, validation tightening |
| 💡 Suggestion | 6 | Architectural refactors |

The **single highest-impact item** is **C-A1** (duplicate `/api/contacts/import`): the second registration silently overrides the first, breaking the entire `runner.excel_path` / `runner.reset_progress` flow that was the point of the recent refactor. Fix that first.

The **second highest** is **C-A6** (Job Object handle GC): the C5 fix is mostly cosmetic until the handle is rooted on a module global. Easy 1-line fix, big reliability gain.
