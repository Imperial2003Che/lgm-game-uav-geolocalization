"""Preserve frozen artifact spellings only for proved identical file objects.

No path prefix replacement, filesystem mutation or source-hash relaxation.
Equal content in two different files is insufficient for alias compatibility.
"""
import hashlib
import os
from pathlib import Path

def require(ok,message):
    if not ok:raise RuntimeError(message)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def compare_evidence(expected,actual,location='$'):
    require(type(expected) is type(actual),'Evidence type changed: '+location)
    if isinstance(expected,dict):
        require(set(expected)==set(actual),'Evidence keys changed: '+location)
        if set(expected)=={'path','bytes','sha256'}:
            require(type(expected['bytes']) is int and type(actual['bytes']) is int
                    and expected['bytes']==actual['bytes'] and expected['sha256']==actual['sha256'],
                    'Artifact size/hash changed: '+location)
            require(isinstance(expected['path'],str) and isinstance(actual['path'],str),'Invalid artifact path')
            old,current=Path(expected['path']),Path(actual['path'])
            require(os.path.samefile(old,current),'Different file objects: '+location)
            before=current.stat();observed=sha(current);after=current.stat()
            require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
                    (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
                    and after.st_size==expected['bytes'] and observed==expected['sha256'],
                    'Artifact changed during identity validation: '+location)
            if expected['path']==actual['path']:return []
            return [{'location':location,'recorded_path':expected['path'],'current_path':actual['path'],
                     'same_file':True,'file_device':after.st_dev,'file_id':after.st_ino,
                     'bytes':after.st_size,'sha256':observed}]
        rows=[]
        for key in expected:rows.extend(compare_evidence(expected[key],actual[key],location+'.'+str(key)))
        return rows
    if isinstance(expected,list):
        require(len(expected)==len(actual),'Evidence list length changed: '+location)
        rows=[]
        for index,(left,right) in enumerate(zip(expected,actual)):
            rows.extend(compare_evidence(left,right,location+'['+str(index)+']'))
        return rows
    require(expected==actual,'Non-artifact evidence changed: '+location)
    return []

def stable_source_evidence(original,prepared_snapshot):
    """Return original prepared representation after proving exact equivalence."""
    def guarded():
        prepared_snapshot.unchanged()
        expected=prepared_snapshot.value()['sources']
        observed=original()
        aliases=compare_evidence(expected,observed)
        prepared_snapshot.unchanged()
        guarded.latest_aliases=aliases
        return expected
    guarded.latest_aliases=[]
    return guarded
