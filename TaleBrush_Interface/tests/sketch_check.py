'''sketch_check.py - replay a sketch through the interface, the way the browser does.

Sends the same requests as TaleBrush_Generate.jsx, through the interface's /api/* routes (so the
proxy to the backend is tested too), one at a time as the front end does:
  1. continue the story for 5 sentences along a fortune curve,
  2. infill 2 sentences between the 2nd and 3rd, alternating front and back,
  3. re-label a sentence the writer edited by hand.
Reports the time for each step, which is what the audience waits for in a demo, and prints the
final story so you can read the infilled sentences for continuity.

Run with: make sketch-check
'''
import json
import os
import sys
import time
import urllib.request

BASE_URL = os.environ.get('INTERFACE_URL', 'http://localhost:7082/')
CHARACTER = 'Mara'
OPENING = ['Mara had saved for three years to open a bakery on the corner of Elm Street.']
CURVE = [80, 60, 25, 10, 85]  # rise, fall, disaster, recovery
INFILL_CURVE = [40, 20]


def post(route, payload):
    req = urllib.request.Request(BASE_URL + 'api/' + route, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    return data, time.time() - start


def generation_payload(pre_context, target):
    return {
        'pre_context': json.dumps(pre_context),
        'controls': json.dumps([str(target)]),
        'characters': json.dumps([CHARACTER]),
        'temperature': json.dumps([0.7]),
        'regeneration': json.dumps([1]),
    }


def generated(data):
    return json.loads(data['generated'])[0], json.loads(data['values'])[0]


# The front end sends regeneration=1 unless the writer raises that slider, so each sentence gets one
# round of candidates and an occasional miss is expected. Only empty results count as failures.
failures = []
misses = []


def report(target, sentence, value, secs):
    if not sentence:
        failures.append(target)
    elif abs(value - target) >= 20:
        misses.append(target)
    print(f'  target {target:3d} -> [{value:3d}] {secs:4.1f}s  {sentence or "(nothing generated)"}')


# 1. Continue the story along the curve, one sentence per request.
print(f'Continue: {len(CURVE)} sentences')
story = list(OPENING)
start = time.time()
for target in CURVE:
    data, secs = post('continuingGeneration', generation_payload(story, target))
    sentence, value = generated(data)
    report(target, sentence, value, secs)
    story.append(sentence)
continue_secs = time.time() - start
print(f'  total {continue_secs:.1f}s')

# 2. Infill between story[2] and story[3]; the front end alternates filling from the front and the back.
print(f'\nInfill: {len(INFILL_CURVE)} sentences between sentences 2 and 3')
pre_context, post_context = story[:3], story[3:]
targets = list(INFILL_CURVE)
is_front = True
start = time.time()
while targets:
    target = targets.pop(0) if is_front else targets.pop()
    payload = generation_payload(pre_context, target)
    payload.update(post_context=json.dumps(post_context), is_front=is_front)
    data, secs = post('infillingGeneration', payload)
    sentence, value = generated(data)
    report(target, sentence, value, secs)
    if is_front:
        pre_context.append(sentence)
    else:
        post_context.insert(0, sentence)
    is_front = not is_front
infill_secs = time.time() - start
print(f'  total {infill_secs:.1f}s')

# 3. Re-label a hand-edited sentence. The front end joins the earlier sentences with no separator.
print('\nLabel a hand-edited sentence')
edited = f'{CHARACTER} watched the oven catch fire and the flames spread to the roof.'
data, secs = post('labelSentence', {'sentence': edited, 'pre_context': ''.join(story[:3]), 'character': CHARACTER})
print(f'  [{data["value"]:3d}] {secs:4.1f}s  {edited}')
if not data['value'] < 40:
    failures.append(edited)

print(f'\nFinal story:\n  ' + '\n  '.join(pre_context + post_context))
print(f'\n5-sentence sketch: {continue_secs:.1f}s ({continue_secs / len(CURVE):.1f}s per sentence)')
total = len(CURVE) + len(INFILL_CURVE)
print(f'{total - len(misses)}/{total} sentences within 20 of their target')
print('PASS: every request worked' if not failures else
      f'FAIL: {len(failures)} request(s) came back empty or mislabeled')
sys.exit(0 if not failures else 1)
