# Workplan: replace the TaleBrush backend with a modern LLM

**Goal:** the original TaleBrush interface runs locally against a new backend, both in Docker and started with one `make up`. The backend uses a modern LLM for generation and fortune scoring, replacing GPT-Neo, GeDi and the tuned weights that are no longer available (see [REVIVAL_LOG.md](REVIVAL_LOG.md)). No GPU, Colab or ngrok is needed.

Mark items done by changing `[ ]` to `[x]`.

## What the code tells us

- **The front end won't need changes.** All model calls go through three proxy routes in `TaleBrush_Interface/server/app.py`, which forward to `ML_URL`. The other calls, in `TaleBrush_Canvas.jsx`, come after an early `return` and never run.
- **Each request asks for one sentence.** The front end loops over the sketch and sends one target fortune per call.
- **The interface needs reviving too.** It pins Flask 0.12.2 and uses `_app_ctx_stack`, which current Flask removed. It also builds with webpack 4, which usually fails on Node 17+ with an OpenSSL error. Building inside a container with Node 16 avoids that, regardless of the Node version on the host.

## Target layout

```
docker-compose.yml          two services: backend, interface
Makefile                    up, down, logs, build, test, control-check, clean
.env.example                ANTHROPIC_API_KEY and model names (copy to .env, which git ignores)
TaleBrush_Backend/
  Dockerfile                slim Python image, runs server_llm.py on port 5001
  server_llm.py             new LLM backend
  requirements_llm.txt
TaleBrush_Interface/
  Dockerfile                stage 1: Node 16 webpack build; stage 2: Python serving Flask on port 7082
```

## Phase 0: get the interface running in a container (prerequisite)

- [x] Replace `_app_ctx_stack` with `flask.g` in `server/app.py`.
- [x] Update `TaleBrush_Interface/requirements.txt` to current Flask, Flask-Cors and `requests`, and drop the unused pins (`pymongo`, `gunicorn`, old `pylint`/`pytest`).
- [x] Change `ML_URL` to read from an environment variable that defaults to `http://localhost:5001/`, instead of editing `[PLACEHOLDER]` by hand.
- [x] Make the SQLite database path configurable through an environment variable, so it can live on a Docker volume. Create the database from `config.sql` on first start if it's missing; the `/api/storeEvent` logging route needs it.
- [x] Write `TaleBrush_Interface/Dockerfile`. Stage 1 uses `node:16` to run `npm ci && npm run build`; stage 2 uses a slim Python image to copy in `build/` and `server/` and run Flask on port 7082 bound to `0.0.0.0`.
- [x] Add a `.dockerignore` that excludes `node_modules` and `build`.
- [x] **Done when:** `docker build` succeeds and `/talebrush` loads from the running container. Generation calls are expected to fail until Phase 2. *(Checked over HTTP: the page, JS bundle and CSS return 200, and `/api/storeEvent` writes to SQLite on the volume. Still to do: open the page in a browser.)*

## Phase 1: decide the model setup

- [x] Confirm the provider. Recommended: the Claude API, with `ANTHROPIC_API_KEY` set in `.env`. *(Confirmed 2026-10-28.)*
- [x] Confirm the generation model. Recommended: `claude-sonnet-5-5`, configurable through `.env`.
- [x] Confirm the scoring model. Recommended: `claude-haiku-5-5`, configurable through `.env`.
- [x] Keep the model calls behind a small interface, so a local model (e.g. Ollama) could be added later. A local backend itself is out of scope.

## Phase 2: build the new backend

**New file:** `TaleBrush_Backend/server_llm.py`, a Flask app on port 5001. The original `server_code.py` and the notebook stay untouched.

It must match the existing API exactly:

| Endpoint | Input (fields arrive as JSON-encoded strings) | Output |
|---|---|---|
| `POST /labelSentence` | `sentence`, `pre_context`, `character` | `{"value": 0–100}` |
| `POST /continuingGeneration` | `pre_context[]`, `controls[0]` (target 0–100), `characters[]`, `temperature[0]`, `regeneration[0]` | `{"generated": "[\"…\"]", "values": "[n]"}` |
| `POST /infillingGeneration` | the same, plus `post_context[]` and `is_front` | the same |

- [x] Write `score_fortune(pre_context, character, sentence)`. It asks the model for an integer rating with a structured output and clamps it to 0–100. A short rubric in the prompt anchors the scale (0 = disaster, 50 = neutral, 100 = triumph).
- [x] Write `generate_sentence(before, after, characters, target, temperature)`. It returns exactly one sentence, and the prompt describes the target fortune in words as well as numbers (e.g. "about 20/100: things go badly for Anna"). With `after` empty it continues the story; otherwise it writes the sentence that bridges `before` and `after`. If the target is `-1` (no control), it leaves out the fortune instruction.
- [x] Add re-ranking with the original logic. Generate, score, and stop when the score is within 20 of the target or the retry limit `regeneration[0]` is reached, then return the closest attempt.
- [x] Cut latency by asking for about 3 candidates in one call and scoring them in parallel, rather than looping one at a time.
- [x] Make it robust: strip quotes and leftover text so the output is a single sentence, return an empty string after repeated failures (the front end already handles that), and log each request with how long it took.
- [x] Implement `/labelSentence`.
- [x] Implement `/continuingGeneration`.
- [x] Implement `/infillingGeneration`.
- [x] Add a `GET /health` endpoint for the compose healthcheck.
- [x] Write `TaleBrush_Backend/requirements_llm.txt`, separate from the 2021 dependencies.
- [x] Write `TaleBrush_Backend/Dockerfile`: a slim Python image that installs `requirements_llm.txt` and copies in only `server_llm.py`, not the large 2021 model code and data.

*Phase 2 status (2026-10-28): implemented and tested offline (a fake model for the endpoints, a local stub API for the exact SDK requests). Not yet run against the live API: that needs `ANTHROPIC_API_KEY` and happens in Phase 4.*

## Phase 3: compose and Makefile

- [ ] Write `docker-compose.yml` with a `backend` service (port 5001, env from `.env`, healthcheck on `/health`) and an `interface` service (port 7082, `ML_URL=http://backend:5001/`, a named volume for the SQLite database, starts after `backend` is healthy).
- [x] Write `.env.example` with `ANTHROPIC_API_KEY=`, `GEN_MODEL=` and `SCORE_MODEL=`, and add `.env` to `.gitignore`.
- [ ] Write the `Makefile`:
  - [ ] `make up`: fails with a clear message if `.env` is missing, starts the services detached, and prints `http://localhost:7082/talebrush`.
  - [ ] `make down` and `make logs`.
  - [ ] `make build`: rebuilds the images.
  - [ ] `make test`: runs the contract tests against the running backend.
  - [ ] `make control-check`: runs the fortune-separation check.
  - [ ] `make clean`: removes containers, images and volumes.
  - [ ] `make help`: the default target; lists the other targets.
- [ ] **Done when:** from a fresh clone, `cp .env.example .env`, adding the key and running `make up` gives a working app.

## Phase 4: verify

- [ ] **Contract tests (`make test`):** a script that sends sample payloads to each endpoint, copied from the front-end code, and checks the response shape, including the double JSON encoding.
- [ ] **Control check (`make control-check`):** generate 10 sentences at each target of 10, 50 and 90, then score them. The average scores should clearly separate. This is the evidence that fortune control works.
- [ ] **End to end:** run `make up`, sketch a fortune curve, generate, infill, and check the sentence labels.
- [ ] **Latency:** time one sketch with 5 sentences. If it's too slow for a live demo, lower the number of candidates or retries.
- [ ] **Clean-clone check:** clone the repo into a new folder and follow only the README's instructions.

## Phase 5: document

- [ ] Add a section to `REVIVAL_LOG.md` covering why the backend was replaced (the model files are gone), how it differs from the paper, and the move to Docker. The paper steered generation token by token with GeDi; this uses instructions and re-ranking.
- [ ] Rewrite the README run instructions: install Docker Desktop, `cp .env.example .env`, add the key, `make up`. Keep the original Colab instructions as a separate "original pipeline" section.

## Risks

- **Scoring drift:** the LLM's sense of "fortune 70" may not match the original model's. The Phase 4 control check shows how big the gap is, and the rubric can be tuned.
- **Old npm dependencies:** even on Node 16, some 2019-era packages may fail to install or have problems with `package-lock.json`. The fallback is an even older Node image (e.g. `node:14`), or `npm install` instead of `npm ci`.
- **Apple Silicon:** some old npm packages with native builds may lack ARM64 binaries. The fallback is `platform: linux/amd64` for the build stage, which is slower but works.
- **Live demo:** it depends on the network, the API and Docker Desktop running. Run through the demo in advance, start the containers before presenting and keep a recording as backup.

## Rough effort

| Phase | Estimate |
|---|---|
| 0: interface revival and container | 1–2 hours |
| 2: backend | about half a day, together with phase 4 |
| 3: compose and Makefile | about 1 hour |
| 4: verification | (included with phase 2) |
| 5: documentation | about an hour |
