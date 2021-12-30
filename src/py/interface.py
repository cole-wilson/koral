import js
from base64 import b64encode as btoa, b64decode as atob
from jug.backends.encode import encode, decode
from jug.backends.base import base_store, base_lock

def _resultname(name):
    if type(name) != str:
        name = name.decode()
    return 'r' + name

def _lockname(name):
    if type(name) != str:
        name = name.decode()
    return 'l' + name

LOCKED = 'L'
FAILED = 'F'

class Connection:
    def __getattr__(self, name):
        def wrapper(*args):
            pickled = btoa(encode((name, args))).decode()
            raw_response = js.get(pickled)
            response = decode(atob(raw_response))
            js.console.info(f"{name}({', '.join(map(str, args))})\t->\t{response}")
            return response
        wrapper.__name__ = f"<Connection().{name}>"
        return wrapper

class koral_store(base_store):
    def __init__(self):
        self.connection = Connection()

    def dump(self, object, name):
        s = encode(object)
        self.connection.set(_resultname(name), s)

    def can_load(self, name):
        return self.connection.exists(_resultname(name))

    def load(self, name):
        s = self.connection.get(_resultname(name))
        if s:
            s = b64decode(s)
        return decode(s)

    def remove(self, name):
        return self.connection.delete(_resultname(name))

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
        locks = self.connection.keys('lock:*')
        for lk in locks:
            self.connection.delete(lk)
        return len(locks)

    def list(self):
        existing = self.connection.keys('result:*')
        for ex in existing:
            yield ex[len('result:'):]

    def listlocks(self):
        locks = self.connection.keys('lock:*')
        for lk in locks:
            yield lk[len('lock:'):]


    def getlock(self, name):
        return koral_lock(self.connection, name)


    def close(self):
        self.connection.disconnect()


class koral_lock(base_lock):
    def __init__(self, koral, name):
        self.name = _lockname(name)
        self.connection = koral


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
