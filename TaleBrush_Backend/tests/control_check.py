'''control_check.py - does the sketched fortune actually steer the story?

Generates sentences at low, middle and high fortune targets from the same story opening, and
reports the fortune each one scored. If control works, the three groups separate clearly.
Makes about 30 generation requests (each one a Sonnet call plus Haiku scoring calls).

Run with: make control-check
'''
import json
import os
import statistics
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE_URL = os.environ.get('BACKEND_URL', 'http://localhost:5001/')
TARGETS = [10, 50, 90]
SAMPLES = int(os.environ.get('SAMPLES', '10'))
STORY = ['Mara had saved for three years to open a bakery on the corner of Elm Street.',
         'On opening day, the line stretched around the block.']


def generate(target):
    payload = {
        'pre_context': json.dumps(STORY),
        'controls': json.dumps([str(target)]),
        'characters': json.dumps(['Mara']),
        'temperature': json.dumps([0.7]),
        'regeneration': json.dumps([1]),
    }
    req = urllib.request.Request(BASE_URL + 'continuingGeneration', data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    return target, json.loads(data['generated'])[0], json.loads(data['values'])[0]


with ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(generate, [t for t in TARGETS for _ in range(SAMPLES)]))

means = {}
for target in TARGETS:
    group = [(s, v) for t, s, v in results if t == target]
    values = [v for _, v in group]
    means[target] = statistics.mean(values)
    within = sum(abs(v - target) < 20 for v in values)
    print(f'\nTarget {target}: mean {means[target]:.0f}, range {min(values)}–{max(values)}, '
          f'{within}/{len(values)} within 20 of target')
    for sentence, value in group[:3]:
        print(f'  [{value:3d}] {sentence}')

separated = means[TARGETS[0]] + 20 < means[TARGETS[1]] < means[TARGETS[2]] - 20
print('\nPASS: the three targets separate clearly' if separated else
      '\nFAIL: the targets do not separate by at least 20 points')
sys.exit(0 if separated else 1)
