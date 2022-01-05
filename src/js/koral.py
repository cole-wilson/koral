import platform
import jug
import time
import sys
import requests
from base64 import b64encode, b64decode
from jug.backends.encode import encode, decode
from jug.backends.base import base_store, base_lock

IS_BROWSER = bool(platform.system() == 'Emscripten')
__version__ = "0.0.2"
_resultname= lambda i: 'r' + i.decode()
_lockname  = lambda i: 'l' + i.decode()
LOCKED = 'L'
FAILED = 'F'

class koral_store(base_store):
    def __init__(self, config):
        class Connection:
            def __getattr__(self, name):
                def wrapper(*args):
                    pickled = b64encode(encode((name, args))).decode()
                    request = requests.post(config.api.url, data=pickled)
                    raw_response = request.content.decode()
                    response = decode(b64decode(raw_response))
                    logging.info(f"{name}({', '.join(map(str, args))})\t->\t{response}")
                    return response
                wrapper.__name__ = f"<Connection().{name}>"
              return wrapper
        self.connection = Connection()
    def dump(self, object, name): return self.connection.set(_resultname(name), encode(s))
    def can_load(self, name): return self.connection.exists(_resultname(name))
    def load(self, name):
        s = self.connection.get(_resultname(name))
        if s: s = b64decode(s)
        return decode(s)
    def remove(self, name): return self.connection.delete(_resultname(name))
    def cleanup(self, active, keeplocks=False):
        existing = list(self.list())
        for act in active:
            try:
                existing.remove(_resultname(act.hash()))
            except ValueError:
                pass
        if keeplocks:
            for lock in self.listlocks():
                try:
                    existing.remove(_lockname(lock))
                except ValueError:
                    pass
        cleaned = len(existing)
        for superflous in existing:
            self.connection.delete(_resultname(superflous))
        return cleaned
    def remove_locks(self):
        locks = self.connection.keys('l*')
        for lk in locks:
            self.connection.delete(lk)
        return len(locks)
    def list(self):
        existing = self.connection.keys('r*')
        for ex in existing:
            yield ex[len('r'):]
    def listlocks(self):
        locks = self.connection.keys('l*')
        for lk in locks:
            yield lk[len('l'):]
    def getlock(self, name): return koral_lock(self.connection, name)
    def close(self): pass

class koral_lock(base_lock):
    def __init__(self, connection, name):
        self.name = _lockname(name)
        self.connection = connection
    def get(self):
        previous = self.connection.getset(self.name, LOCKED)
        if previous == FAILED:
            self.connection.set(self.name, previous)
        return (previous is None)
    def release(self):
        self.connection.delete(self.name)
    def is_locked(self):
        status = self.connection.get(self.name)
        return status is not None and status in (LOCKED, FAILED)
    def fail(self):
        status = self.connection.get(self.name)
        if status == LOCKED:
            self.connection.set(self.name, FAILED)
            return True
        elif status == FAILED:
            return True
        else:
            return False
    def is_failed(self):
        return self.connection.get(self.name) == FAILED

def setup_io():
    if not IS_BROWSER: return
    import js

    # Setup logging to JS console
    class JSLogger(logging.Handler):
        def emit(self, record):
          level = record.levelname.lower()
          levelmap = {
            "critical": js.console.error,
            "error":    js.console.error,
            "warning":  js.console.warn,
            "info":     js.console.info,
            "debug":    js.console.debug,
            "notset":   js.console.log,
          }
          if level not in levelmap: return
          levelmap[level](self.format(msg))
    root = logging.getLogger()
    root.setLevel("DEBUG")
    root.addHandler(JSLogger())

    # Mock files for text I/O
    class InputFile():
      def read(self, amount): return js.stdin(amount)
      def readline(self): return self.read(chr(10))
    class OutputFile():
      def flush(self): ...
      def write(self, text): js.writeOutput("stdout", text)
    class ErrorFile():
      def flush(self): ...
      def write(self, text): js.writeOutput("stderr", text)
    sys.stdout = OutputFile()
    sys.stderr = ErrorFile()
    sys.stdin = InputFile()

def setup_shims(config):
    def requests_adapter(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        body = request.body
        jsreq = js.XMLHttpRequest.new()
        jsreq.open(request.method.upper(), request.url, False)
        if timeout:
            jsreq.timeout = timeout * 1000
        for header, value in request.headers.items():
            jsreq.setRequestHeader(header, value)

        try:
            jsreq.send(body)
        except pyodide.JsException as err:
            raise requests.HTTPError("A JavaScript exception was raised during the processing of this request: {err.js_error}")

        response = requests.Response()
        response.status_code = jsreq.status
        headers = dict(map(lambda i: tuple(i.split(': ', 1)), jsreq.getAllResponseHeaders().split("\r\n")[:-1]))
        response.headers = headers
        response._content = jsreq.responseText
        response.req = request
        response._jsreq = jsreq
        response.connection = self
        response.url = jsreq.responseURL
        response.reason = "" if " " not in jsreq.statusText else jsreq.statusText.split(" ", 1)[1]

        return response
    requests.adapters.HTTPAdapter.send = requests_adapter

    def sleep_shim(t):
      requests.get(f"/sleep?t={t}")
    time.sleep = sleep_shim


def init(config):
    setup_shims(config)
    jug.options.set_jugdir(koral_store(config))
    setup_io(config)
