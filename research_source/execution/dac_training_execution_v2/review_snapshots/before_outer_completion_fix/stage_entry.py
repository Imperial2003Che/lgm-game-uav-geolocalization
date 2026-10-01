"""Fresh stdlib stage parent; delegates native science to the sealed DAC control."""
import argparse
import importlib
import os
import sys
import time
from types import SimpleNamespace
import dac6_contracts as d

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request',required=True);p.add_argument('--request-sha256',required=True)
    args=p.parse_args();request,spec,release,row,plan,serial=d.request_bound(args.request,args.request_sha256)
    value=request.value;base=d.stage_directory(row['id'])
    d.require(d.Path(sys.executable).resolve()==d.Path(plan.value['environment']['executable']).resolve(),'Wrong pinned Python interpreter')
    actual={'schema':'dac-actual-worker-identity.v2','pid':os.getpid(),'started_utc':d.g.process_started(os.getpid()),
        'plan_sha256':plan.sha256,'release_sha256':serial.sha256,
        'lineage':d.g.worker_lineage(os.getpid(),value['controller_pid'],value['controller_started_utc'])}
    d.c.write(base/'worker_identity.json',actual)
    # Do not begin inner launch until the outer coordinator retained the actual
    # stage-parent handle; this closes the Windows redirector exit-before-open race.
    deadline=time.monotonic()+60
    while not (base/'parent_observed.json').exists():
        d.require(time.monotonic()<deadline,'Actual parent observation timeout')
        d.require(d.g.process_started(value['controller_pid'])==value['controller_started_utc'],'Coordinator disappeared before stage admission')
        time.sleep(.05)
    d.require(d.c.read(base/'parent_observed.json')=={'request_sha256':request.sha256,
        'worker_identity_sha256':d.sha(base/'worker_identity.json'),'controller_pid':value['controller_pid'],
        'controller_started_utc':value['controller_started_utc']},'Observation acknowledgement differs from this actual process')
    kwargs={'stage':row['stage'],'plan':str(plan.path),'plan_sha256':plan.sha256,
        'release_file':str(serial.path),'release_sha256':serial.sha256}
    if row['stage']=='train':
        pair=value['profile_binding'];kwargs.update(profile=str(d.Path(plan.value['profile_directory'])/'profile.json'),
            profile_sha256=pair['profile_sha256'],profile_receipt=str(d.Path(plan.value['profile_receipt_directory'])/'lifecycle.json'),
            profile_receipt_sha256=pair['receipt_sha256'])
    for bound in (request,spec,release,plan,serial):bound.unchanged()
    importlib.import_module('run_dac_stage').supervise_one(SimpleNamespace(**kwargs))
    for bound in (request,spec,release,plan,serial):bound.unchanged()

if __name__=='__main__':main()
