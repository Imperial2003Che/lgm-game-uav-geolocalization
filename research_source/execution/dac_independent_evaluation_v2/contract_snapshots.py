"""First-read raw-byte input identities shared across nested evaluation commands."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
import hashlib
import json
from pathlib import Path

def digest(data):return hashlib.sha256(data).hexdigest()
def parse(data):return json.loads(data,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON '+x)))
def serialized_json(value):return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')

@dataclass(frozen=True)
class JsonSnapshot:
    path:Path
    raw:bytes
    @classmethod
    def read(cls,path):
        path=Path(path).resolve();before=path.stat();raw=path.read_bytes();after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or len(raw)!=after.st_size:
            raise RuntimeError('Input changed during initial read: '+str(path))
        parse(raw)
        return cls(path,raw)
    @property
    def sha256(self):return digest(self.raw)
    @property
    def value(self):return parse(self.raw)
    @property
    def artifact(self):return {'path':str(self.path),'bytes':len(self.raw),'sha256':self.sha256}
    def unchanged(self):
        if self.path.read_bytes()!=self.raw:raise RuntimeError('Input changed after its first read: '+str(self.path))

class InputSnapshots:
    def __init__(self):self.records={}
    def capture(self,path):
        path=Path(path).resolve()
        if path not in self.records:self.records[path]=JsonSnapshot.read(path)
        result=self.records[path];result.unchanged();return result
    def written(self,path,value):
        # Bind exactly the bytes save() emitted, rather than rereading a possibly
        # replaced file and assigning its new digest to the old in-memory value.
        path=Path(path).resolve();raw=serialized_json(value)
        snap=JsonSnapshot(path,raw);snap.unchanged()
        if path in self.records and self.records[path].raw!=raw:raise RuntimeError('Immutable contract output reused')
        self.records[path]=snap;return snap
    def unchanged(self):
        for snap in tuple(self.records.values()):snap.unchanged()

_CURRENT=ContextVar('dac_evaluation_input_snapshots',default=None)
@contextmanager
def snapshot_scope():
    current=_CURRENT.get()
    if current is not None:
        yield current;return
    records=InputSnapshots();token=_CURRENT.set(records)
    try:yield records
    finally:_CURRENT.reset(token)
def input_snapshot(path):
    current=_CURRENT.get()
    if current is None:raise RuntimeError('Input snapshot scope is required')
    return current.capture(path)
def input_artifact(path):return input_snapshot(path).artifact
def bind_written(path,value):
    current=_CURRENT.get()
    if current is None:raise RuntimeError('Input snapshot scope is required')
    return current.written(path,value)
def unchanged_inputs():
    current=_CURRENT.get()
    if current is None:raise RuntimeError('Input snapshot scope is required')
    current.unchanged()
def snapshot_command(function):
    @wraps(function)
    def wrapped(args):
        with snapshot_scope():
            for key in ('prepared','binding','release_file','controller_release','training_completion','training_execution_plan','membership'):
                path=getattr(args,key,None)
                if path is not None:input_snapshot(path)
            for path in getattr(args,'training_plan',[]) or []:input_snapshot(path)
            result=function(args)
            unchanged_inputs()
            return result
    return wrapped
