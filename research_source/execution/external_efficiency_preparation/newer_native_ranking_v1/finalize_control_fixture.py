"""Preserve the initial fixture/report; correct only the failure-injection point."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE/'review_bridge.py').read_text(encoding='utf-8')
old="""        def rank(*_):
            value = Rank()
            if mismatch and actions and actions[-1][0] == 'saved': value.values = [0, 1, 2]
            return value
"""
new="""        ranking_calls = 0
        def rank(*_):
            nonlocal ranking_calls
            ranking_calls += 1
            value = Rank()
            if mismatch and ranking_calls == 2: value.values = [0, 1, 2]
            return value
"""
assert source.count(old)==1
source=source.replace(old,new).replace("output = HERE / 'CONTROL_REVIEW.json'", "output = HERE / 'CONTROL_REVIEW_FINAL.json'")
with (HERE/'review_bridge_final.py').open('x',encoding='utf-8',newline='\n') as stream:
    stream.write(source)
