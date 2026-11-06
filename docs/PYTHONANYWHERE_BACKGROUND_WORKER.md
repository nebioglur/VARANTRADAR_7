# PythonAnywhere background market-data worker

The WSGI app serves requests only. PythonAnywhere does not support persistent
background threads in web workers, so recurring scans run in a separate
Always-on task.

## Configure the task

1. In PythonAnywhere, open **Tasks** and add an **Always-on task**. This feature
   requires a paid account.
2. Run the worker with the same Python version and virtualenv used by the web
   app. For example:

   ```bash
   /home/varantradarpro/.virtualenvs/varantradar/bin/python /home/varantradarpro/VARANTRADAR_7/pythonanywhere_worker.py
   ```

   Replace the virtualenv path if the Web tab shows a different one.
3. Run exactly one copy of this worker; stop any older task that starts the same
   dashboard scanner or simulation loops.
4. Make the task use the same production environment variables as the web app,
   especially `DATABASE_URL` or `SUPABASE_DB_URL` when configured. Both
   processes must read and write the same durable dashboard cache.
5. Reload the web app from the **Web** tab after pulling the code.
6. Open `/api/ping`. The response must show the current Git commit in `build`
   and `worker.running: true`. `worker.last_seen` should advance about once a
   minute.

The worker runs the existing dashboard scanner and five-minute intraday data
collector. No generated or fallback prices are introduced. A failed provider
fetch leaves the last good cache intact and its freshness indicator becomes
stale after 30 minutes.

Free PythonAnywhere accounts do not have Always-on tasks. Their scheduled task
limits cannot provide the recurring intraday refresh this app requires.
