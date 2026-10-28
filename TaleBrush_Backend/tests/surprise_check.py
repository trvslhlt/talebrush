'''surprise_check.py - does the drawn surprise level change the story?

Generates sentences at low, medium and very high surprise from the same story opening, with the
fortune left uncontrolled, then rates each one's surprise. If the control works, the ratings rise
with the level. The ratings come from the same scorer the server uses to pick candidates, so they
show that selection works; read the printed sentences to judge whether they really feel different.

Run with: make surprise-check
'''
import json
import os
import statistics
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, '/app')
import server_llm  # noqa: E402  (runs inside the backend container)

BASE_URL = os.environ.get('BACKEND_URL', 'http://localhost:5001/')
LEVELS = [0.1, 0.5, 0.95]
SAMPLES = int(os.environ.get('SAMPLES', '6'))
STORY = ['Mara had saved for three years to open a bakery on the corner of Elm Street.',
         'On opening day, the line stretched around the block.']


def generate(level):
    payload = {
        'pre_context': json.dumps(STORY),
        'controls': json.dumps(['-1']),
        'characters': json.dumps(['Mara']),
        'temperature': json.dumps([level]),
        'regeneration': json.dumps([1]),
    }
    req = urllib.request.Request(BASE_URL + 'continuingGeneration', data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as resp:
        sentence = json.loads(json.loads(resp.read())['generated'])[0]
    rated = server_llm.score_fortune_and_surprise(' '.join(STORY), 'Mara', sentence)['surprise']
    return level, sentence, rated


with ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(generate, [lvl for lvl in LEVELS for _ in range(SAMPLES)]))

means = {}
for level in LEVELS:
    group = [(s, r) for lvl, s, r in results if lvl == level]
    means[level] = statistics.mean(r for _, r in group)
    print(f'\nSurprise {level}: rated {means[level]:.0f} on average (range {min(r for _, r in group)}–{max(r for _, r in group)})')
    for sentence, rated in group[:3]:
        print(f'  [{rated:3d}] {sentence}')

rising = means[LEVELS[0]] + 20 < means[LEVELS[-1]]
print('\nPASS: higher surprise levels give more surprising sentences' if rising else
      '\nFAIL: the lowest and highest levels are less than 20 points apart')
sys.exit(0 if rising else 1)
