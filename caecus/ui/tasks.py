import queue
import threading


class Task:
    """Run a function in a worker thread; deliver results on the Tk thread."""

    def __init__(self, app, func, on_progress=None, on_done=None, on_error=None, on_cancel=None):
        self.app, self.func = app, func
        self.on_progress, self.on_done = on_progress, on_done
        self.on_error, self.on_cancel = on_error, on_cancel
        self.cancel_event = threading.Event()
        self._queue = queue.Queue()

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
        self.app.after(100, self._poll)

    def cancel(self):
        self.cancel_event.set()

    def _run(self):
        try:
            result = self.func(progress=lambda r: self._queue.put(("progress", r)),
                               is_cancelled=self.cancel_event.is_set)
            self._queue.put(("done", result))
        except Exception as exc:  # reported on the Tk thread
            self._queue.put(("error", exc))

    def _poll(self):
        finished = False
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "progress":
                    if self.on_progress and not self.cancel_event.is_set():
                        self.on_progress(payload)
                elif kind == "done":
                    finished = True
                    if self.cancel_event.is_set():
                        if self.on_cancel:
                            self.on_cancel()
                    elif self.on_done:
                        self.on_done(payload)
                else:
                    finished = True
                    if self.on_error:
                        self.on_error(payload)
        except queue.Empty:
            pass
        if not finished:
            self.app.after(100, self._poll)
