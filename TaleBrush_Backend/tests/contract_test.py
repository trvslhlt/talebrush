'''contract_test.py - check that a running backend answers the way the interface expects.

Sends payloads shaped like the ones in TaleBrush_Interface/src/components/TaleBrush/TaleBrush_Generate.jsx
(fields JSON-encoded inside a JSON body) and checks the response shapes. Makes a handful of real
model calls, so it needs a valid API key and costs a little.

Run with: make test
'''
import json
import re
import os
import sys
import time
import urllib.request

BASE_URL = os.environ.get('BACKEND_URL', 'http://localhost:5001/')
STORY = ['Mara had saved for three years to open a bakery on the corner of Elm Street.',
         'On opening day, the line stretched around the block.']
failures = []


def post(path, payload):
    req = urllib.request.Request(BASE_URL + path, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    start = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read()), time.time() - start


def check(name, condition, detail=''):
    print(('PASS ' if condition else 'FAIL ') + name + (f'  {detail}' if detail else ''))
    if not condition:
        failures.append(name)


def check_generation(name, data, elapsed):
    generated = json.loads(data['generated'])
    values = json.loads(data['values'])
    check(f'{name}: one sentence returned', len(generated) == 1 and isinstance(generated[0], str) and generated[0],
          f'({elapsed:.1f}s) {generated!r}')
    check(f'{name}: one value from 0 to 100', len(values) == 1 and 0 <= values[0] <= 100, f'values={values}')


data, elapsed = post('labelSentence', {'sentence': 'A pipe burst overnight and flooded the kitchen.',
                                       'pre_context': ' '.join(STORY), 'character': 'Mara'})
check('labelSentence: value from 0 to 100', 0 <= data['value'] <= 100, f"({elapsed:.1f}s) value={data['value']}")
check('labelSentence: a disaster scores low', data['value'] < 40, f"value={data['value']}")

generation = {
    'pre_context': json.dumps(STORY),
    'controls': json.dumps(['15']),
    'characters': json.dumps(['Mara']),
    'temperature': json.dumps([0.7]),
    'regeneration': json.dumps([1]),
}
data, elapsed = post('continuingGeneration', generation)
check_generation('continuingGeneration', data, elapsed)

data, elapsed = post('infillingGeneration', dict(generation, controls=json.dumps(['85']),
                                                 post_context=json.dumps(['By evening, every shelf was empty.']),
                                                 is_front=True))
check_generation('infillingGeneration', data, elapsed)

data, elapsed = post('continuingGeneration', dict(generation, controls=json.dumps(['-1'])))
check_generation('continuingGeneration without a fortune target', data, elapsed)

# Enhancement E2: the interface now asks for an opening sentence when the story is empty.
data, elapsed = post('continuingGeneration', dict(generation, pre_context=json.dumps([]), controls=json.dumps(['70'])))
check_generation('continuingGeneration of an empty story', data, elapsed)

# Enhancement E7: a blank protagonist name makes "you" the protagonist.
data, elapsed = post('continuingGeneration', dict(generation, pre_context=json.dumps([]), characters=json.dumps([''])))
check_generation('continuingGeneration with a blank protagonist', data, elapsed)
sentence = json.loads(data['generated'])[0]
check('blank protagonist: the story is about "you"', re.search(r"\byou(r|rs|rself)?\b", sentence, re.I), repr(sentence))

print(f'\n{len(failures)} failed' if failures else '\nAll checks passed')
sys.exit(1 if failures else 0)
