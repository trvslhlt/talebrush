# TaleBrush
# Copyright (c) 2022-present NAVER Corp.
# GPLv3

'''server_llm.py - TaleBrush model server backed by Claude.

Replaces GPT-Neo + GeDi (server_code.py), whose trained weights are no longer
available. Serves the same three endpoints with the same request and response
shapes, so the interface works unchanged.
'''
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor

import anthropic
from flask import Flask, jsonify, request

GEN_MODEL = os.environ.get('GEN_MODEL', 'claude-sonnet-5-5')
SCORE_MODEL = os.environ.get('SCORE_MODEL', 'claude-haiku-5-5')
NUM_CANDIDATES = int(os.environ.get('NUM_CANDIDATES', '3'))
MAX_ROUNDS = int(os.environ.get('MAX_ROUNDS', '3'))
# 'off' skips the models' reasoning step to cut latency; each call only writes one sentence or one number.
THINKING = os.environ.get('THINKING', 'on').lower()
# Same acceptance threshold as the original server: stop once a sentence scores within 20 of the target.
TARGET_TOLERANCE = 20
NO_CONTROL = -1

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('talebrush')

app = Flask(__name__)
pool = ThreadPoolExecutor(max_workers=8)


##
# Model calls
##

GENERATION_SCHEMA = {
    'type': 'object',
    'properties': {'candidates': {'type': 'array', 'items': {'type': 'string'}}},
    'required': ['candidates'],
    'additionalProperties': False,
}

SCORE_SCHEMA = {
    'type': 'object',
    'properties': {'fortune': {'type': 'integer'}},
    'required': ['fortune'],
    'additionalProperties': False,
}

# Errors worth retrying with another round; anything else (bad key, bad request) should fail loudly.
TRANSIENT_ERRORS = (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError,
                    anthropic.OverloadedError, anthropic.ServiceUnavailableError, anthropic.DeadlineExceededError)


class ModelRefused(Exception):
    pass


def thinking_options(model):
    '''Request options that turn thinking off for this model, or {} to leave the default (adaptive) on.'''
    if THINKING != 'off':
        return {}
    # Each model family spells "off" differently, and some can't turn it off at all.
    if model.startswith('claude-sonnet-5-5'):
        return {'thinking': {'type': 'between_tools'}}
    if model.startswith('claude-haiku-5-5'):
        return {'thinking': {'type': 'disabled'}}
    log.warning('THINKING=off is not supported for %s; leaving thinking on', model)
    return {}


class ClaudeModels:
    '''All model access goes through this class, so another provider can be swapped in.'''

    def __init__(self):
        self.client = anthropic.Anthropic()

    def generate(self, system, prompt):
        '''Return a list of candidate sentences.'''
        response = self.client.beta.messages.create(
            model=GEN_MODEL,
            max_tokens=4096,
            system=system,
            messages=[{'role': 'user', 'content': prompt}],
            output_config={'effort': 'low', 'format': {'type': 'json_schema', 'schema': GENERATION_SCHEMA}},
            # Story text can be dark when the sketched fortune is low; if a safety classifier
            # declines, let the API retry on its recommended fallback model.
            betas=['server-side-fallback-2026-07-01'],
            fallbacks='default',
            **thinking_options(GEN_MODEL),
        )
        return json.loads(_response_text(response))['candidates']

    def score(self, system, prompt):
        '''Return the protagonist's fortune as an integer from 0 to 100.'''
        response = self.client.messages.create(
            model=SCORE_MODEL,
            max_tokens=2048,
            system=system,
            messages=[{'role': 'user', 'content': prompt}],
            output_config={'effort': 'low', 'format': {'type': 'json_schema', 'schema': SCORE_SCHEMA}},
            **thinking_options(SCORE_MODEL),
        )
        return max(0, min(100, int(json.loads(_response_text(response))['fortune'])))


def _response_text(response):
    if response.stop_reason == 'refusal':
        raise ModelRefused(getattr(response.stop_details, 'category', None))
    return next(block.text for block in response.content if block.type == 'text')


models = None


def get_models():
    global models
    if models is None:
        models = ClaudeModels()
    return models


##
# Prompts
##

GENERATION_SYSTEM = (
    'You are co-writing a short story with a writer, one sentence at a time. '
    'Write plain, vivid prose that stays consistent with the story so far: the same characters, '
    'tense and point of view. Each candidate must be exactly one complete sentence, must not '
    'repeat a sentence that is already in the story, and must not include quotation marks around it.'
)

SCORE_SYSTEM = (
    "You rate how fortunate a story's protagonist is in one sentence of a story, from 0 to 100. "
    '0 = catastrophe (death, ruin, devastating loss). 25 = clearly bad (setback, danger, sadness). '
    '50 = neutral, mixed or uneventful. 75 = clearly good (progress, help, happiness). '
    '100 = triumph or great joy. Rate the protagonist\'s situation as of this sentence; '
    'use the earlier story only as context.'
)


def describe_fortune(target):
    if target < 15:
        return 'things go disastrously'
    if target < 35:
        return 'things go badly'
    if target < 65:
        return 'things are neutral or mixed'
    if target < 85:
        return 'things go well'
    return 'things go wonderfully'


def describe_surprise(surprise):
    '''The interface's "surprise" control used to set sampling temperature, which the API no longer accepts.'''
    if surprise < 0.4:
        return 'Keep the sentence predictable and conventional for the story.'
    if surprise > 0.8:
        return 'Make the sentence surprising: take the story somewhere unexpected.'
    return ''


def generation_prompt(before, after, protagonist, target, surprise):
    lines = [f'Protagonist: {protagonist}', '', 'Story so far:', ' '.join(before) or '(The story has not started yet.)']
    if after:
        lines += ['', 'The sentence you write goes immediately before these sentences, and must lead naturally into them:',
                  ' '.join(after)]
    lines += ['', f'Write {NUM_CANDIDATES} different candidates for the next sentence.']
    if target != NO_CONTROL:
        lines.append(f"In the sentence, {protagonist}'s fortune should be about {target}/100: "
                     f'{describe_fortune(target)} for {protagonist}.')
    surprise_hint = describe_surprise(surprise)
    if surprise_hint:
        lines.append(surprise_hint)
    return '\n'.join(lines)


def score_prompt(pre_context, protagonist, sentence):
    return '\n'.join([f'Protagonist: {protagonist}', '', 'Earlier story:', pre_context.strip() or '(none)',
                      '', 'Sentence to rate:', sentence])


##
# Generation with re-ranking
##

def clean_sentence(text):
    return ' '.join(text.split()).strip().strip('"“”').strip()


def score_fortune(pre_context, protagonist, sentence):
    return get_models().score(SCORE_SYSTEM, score_prompt(pre_context, protagonist, sentence))


def generate_sentence(before, after, characters, target, surprise, rounds):
    '''Generate candidates, score them, and return (sentence, fortune) closest to the target.

    Mirrors the original server's loop: keep going until a sentence lands within
    TARGET_TOLERANCE of the target or the regeneration budget runs out.
    '''
    protagonist = characters[0] if characters else 'the protagonist'
    prompt = generation_prompt(before, after, protagonist, target, surprise)
    score_context = ' '.join(before)
    best = None  # (distance, sentence, fortune)
    for _ in range(max(1, min(rounds, MAX_ROUNDS))):
        try:
            candidates = [c for c in map(clean_sentence, get_models().generate(GENERATION_SYSTEM, prompt)) if c]
            fortunes = list(pool.map(lambda s: score_fortune(score_context, protagonist, s), candidates))
        except (ModelRefused, *TRANSIENT_ERRORS) as e:
            log.warning('generation round failed: %r', e)
            continue
        for sentence, fortune in zip(candidates, fortunes):
            distance = 0 if target == NO_CONTROL else abs(fortune - target)
            if best is None or distance < best[0]:
                best = (distance, sentence, fortune)
        if best is not None and best[0] < TARGET_TOLERANCE:
            break
    if best is None:
        # The interface treats an empty sentence as "nothing generated".
        return '', 50
    return best[1], best[2]


##
# API routes
##

def parse_generation_request(data):
    return {
        'pre_context': json.loads(data['pre_context']),
        'controls': [int(c) for c in json.loads(data['controls'])],
        'characters': json.loads(data['characters']),
        'temperature': [float(t) for t in json.loads(data['temperature'])],
        'regeneration': [int(r) for r in json.loads(data.get('regeneration', '[1]'))],
    }


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/labelSentence', methods=['POST'])
def label_sentence():
    start = time.time()
    data = request.get_json(force=True)
    value = score_fortune(data['pre_context'], data['character'], data['sentence'])
    log.info('labelSentence value=%d (%.1fs)', value, time.time() - start)
    return jsonify({'value': value})


@app.route('/continuingGeneration', methods=['POST'])
def continuing_generation():
    start = time.time()
    req = parse_generation_request(json.loads(request.get_data()))
    sentence, value = generate_sentence(req['pre_context'], [], req['characters'], req['controls'][0],
                                        req['temperature'][0], req['regeneration'][0])
    log.info('continuingGeneration target=%d value=%d (%.1fs) %r', req['controls'][0], value, time.time() - start, sentence)
    return jsonify({'generated': json.dumps([sentence]), 'values': json.dumps([value])})


@app.route('/infillingGeneration', methods=['POST'])
def infilling_generation():
    start = time.time()
    data = json.loads(request.get_data())
    req = parse_generation_request(data)
    post_context = json.loads(data['post_context'])
    sentence, value = generate_sentence(req['pre_context'], post_context, req['characters'], req['controls'][0],
                                        req['temperature'][0], req['regeneration'][0])
    log.info('infillingGeneration is_front=%s target=%d value=%d (%.1fs) %r', data.get('is_front'),
             req['controls'][0], value, time.time() - start, sentence)
    return jsonify({'generated': json.dumps([sentence]), 'values': json.dumps([value])})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5001')), threaded=True)
