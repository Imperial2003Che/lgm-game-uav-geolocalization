"""Retry only Windows sharing/access errors from the unchanged state writer.

Keep the controller and its lock alive. A pending publication blocks control-flow
advancement; it never changes a scientific result or declares completion itself.
"""
import datetime
import functools
import json
import os
from pathlib import Path
import time

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def wrap(writer, *, diagnostic_path, provenance, sleeper=time.sleep):
    diagnostic_path = Path(diagnostic_path)
    def diagnostic(event):
        line=json.dumps(event,ensure_ascii=False)+'\n'
        # stderr remains an independent record if the diagnostic path is busy.
        try:
            with diagnostic_path.open('a',encoding='utf-8') as stream:
                stream.write(line); stream.flush()
        except OSError:
            import sys
            try:
                print(line.rstrip(),file=sys.stderr,flush=True)
            except (OSError, ValueError):
                # A denied or closed diagnostic stream must not abandon the
                # original writer's retry or the controller's active child.
                # This diagnostic cannot be retained if both sinks fail.
                pass
    @functools.wraps(writer)
    def save(path, value):
        # The supplied object is the controller's durable state, not science output.
        value['state_io_compatibility']=provenance
        attempts=0
        while True:
            try:
                result=writer(path,value)
                if attempts:
                    diagnostic({'event':'state_publication_recovered','time':utc(),'pid':os.getpid(),
                                'path':str(path),'failed_attempts':attempts})
                return result
            except PermissionError as error:
                if getattr(error,'winerror',None) not in (5,32,33): raise
                attempts+=1
                if attempts==1 or attempts%12==0:
                    diagnostic({'event':'state_publication_waiting','time':utc(),'pid':os.getpid(),
                                'path':str(path),'attempts':attempts,'winerror':error.winerror,
                                'control_flow_blocked_until_published':True})
                # No timeout abandons a live child. Persistent denial remains
                # visible in this log and prevents the next job from starting.
                sleeper(min(5.0,0.1*(2**min(attempts-1,6))))
    return save
