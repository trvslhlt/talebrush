# TaleBrush Revival Log

A record of what it took to get the 2022 TaleBrush project running again on present-day tooling, and why each change was needed.

**Original project:** [naver-ai/TaleBrush](https://github.com/naver-ai/TaleBrush) — *TaleBrush: Sketching Stories with Generative Pretrained Language Models* (CHI 2022). TaleBrush lets a writer sketch a line for the protagonist's fortune. A GPT-Neo 2.7B model, steered by a GeDi discriminator, then writes story sentences that follow the line.

## Timeline

| Date | Commit | What |
|---|---|---|
| 2022-07-13 | `e19c3b2` | Original code imported (Kang Min Yoo, NAVER AI) |
| 2026-10-26 | `6dbe56c` | Added the authors' public Colab notebook, `TaleBrush_Server_Code_(public).ipynb` |
| 2026-10-26 | `482e0ce` | Patched the notebook to run on current Colab (details below) |
| 2026-10-28 | — | Revived the interface server and containerized it with Docker (changes 7–10) |
| 2026-10-28 | — | Added a Claude-backed model server to replace GPT-Neo + GeDi (changes 11–15) |
| 2026-10-28 | — | One-command startup with Docker Compose and a Makefile; first live tests and latency tuning (changes 16–19) |

## The problem: a 2021 software stack on a 2026 runtime

The notebook was written for Colab with Python 3.8, `transformers` 4.8.2 (mid-2021) and the Flask tooling of that time. Colab now runs **Python 3.13**. Running the notebook as published failed in its first two cells:

1. **Cell 0 (install)** failed with `Failed building wheel for tokenizers`.
2. **Cell 1 (imports)** failed with `ImportError: cannot import name 'url_decode_stream' from 'werkzeug.urls'`.

The tunnel setup further down would also have failed, because it relied on an ngrok release that ngrok no longer supports.

## Changes

Changes 1–6 are in `TaleBrush_Server_Code_(public).ipynb`. Changes 7–10 are in `TaleBrush_Interface/` and changes 11–14 are in `TaleBrush_Backend/`, as part of replacing the backend with a modern LLM (see [WORKPLAN_LLM_BACKEND.md](WORKPLAN_LLM_BACKEND.md)). The front-end React code is unchanged.

### 1. Install `transformers` 4.8.2 without the `tokenizers` package

**Why:** `transformers==4.8.2` requires `tokenizers<0.11`. That version has no prebuilt package for Python 3.13, so pip tries to compile it from its Rust source. The compile fails because the 2021 Rust code doesn't build with current Rust.

**Fix:** TaleBrush never uses the Rust tokenizer. It only uses `GPT2Tokenizer`, which is written in pure Python. Also, `transformers` 4.8.2 only checks the `tokenizers` version when that package is installed. So the notebook now:

```python
!pip uninstall -y tokenizers                 # Colab ships a newer one that would fail the version check
!pip install transformers==4.8.2 --no-deps   # skip the tokenizers<0.11 requirement
!pip install sacremoses "huggingface_hub==0.0.12"
```

We kept `transformers` pinned at 4.8.2 rather than upgrading it. The backend's custom `modeling_gpt2.py`, `modeling_gptneo.py` and `modeling_utils.py` import internal `transformers` APIs from that release.

### 2. Replace `flask_api` with plain Flask

**Why:** `flask_api` is no longer maintained. It imports `url_decode_stream`, which Werkzeug (Flask's underlying library) removed in version 2.3.

**Fix:** `FlaskAPI(__name__)` became `Flask(__name__)`. Recent Flask converts returned dicts to JSON automatically, so the routes work unchanged. The one exception was `/labelSentence`, which read the request body from `flask_api`'s parsed `request.data`. It now calls `request.get_json(force=True)`. We also added a `jsonify` import: the routes called it, but nothing imported it.

### 3. Replace `flask_ngrok` with `pyngrok`

**Why:** `flask_ngrok` downloads a version 2 ngrok client, and ngrok's service no longer accepts version 2 clients. Without a working tunnel, the front end can't reach the backend running in Colab.

**Fix:** The last cell now opens the tunnel itself with `pyngrok`, then starts Flask on port 5000. It also prints the exact hostname to use in place of `[PLACEHOLDER]` in `TaleBrush_Interface/server/app.py`.

### 4. Read the ngrok authtoken from a Colab secret

**Why:** Commit `6dbe56c` stored an ngrok authtoken in plaintext in cell 0, in a public repository. Any token that has been committed to a public repo should be treated as exposed.

**Fix:** The token is no longer in the notebook. Cell 0 reads it with `google.colab.userdata.get('NGROK_AUTHTOKEN')`. To set it, add a Colab secret named `NGROK_AUTHTOKEN` using the key icon in the left sidebar. The old token is still in the git history of `6dbe56c`, so it has to be revoked in the ngrok dashboard.

### 5. Clone this fork instead of upstream

**Why:** The notebook ran `git clone` on `naver-ai/TaleBrush` to get the backend's Python modules. Any fix to those modules in this fork, which later cells may need, would never reach Colab. It also tied the demo to the upstream repo staying online.

**Fix:** The clone cell now runs `git clone https://github.com/trvslhlt/talebrush.git TaleBrush`. The fork's folder name is lowercase, so the clone names the folder `TaleBrush` explicitly. That keeps the following `%cd TaleBrush` step working.

### 6. Cleared stale outputs

The saved error output in cells 0 and 1 was removed, so the notebook opens clean.

### 7. Build the front end with Node 16, inside Docker

**Why:** The front end is built with webpack 4 (2019). On any current Node, the build fails:

```
Error: error:0308010C:digital envelope routines::unsupported
```

Node 17 moved to OpenSSL 3, which no longer allows the MD4 hash that webpack 4 uses to name its output files. We confirmed this by running the same build on Node 22. The development machine has Node 26.

**Fix:** `TaleBrush_Interface/Dockerfile` builds the front end in a `node:16` stage, where `npm ci && npm run build` succeeds unchanged. A second stage, on a slim Python image, serves the built files and the API with Flask. The alternatives were the `--openssl-legacy-provider` workaround or upgrading webpack and its plugins. Both mean changing the host setup or the build config; the container pins the toolchain without touching either. `.dockerignore` keeps the local `node_modules` and `build` folders out of the image.

### 8. Update the interface server to current Flask

**Why:** `TaleBrush_Interface/requirements.txt` pinned Flask 0.12.2 (2017), which doesn't run on current Python, and `server/app.py` used `_app_ctx_stack`, which Flask 3 removed. The file also didn't list `requests`, even though `app.py` imports it to forward model calls, and pinned packages the server never used (`pymongo`, `gunicorn`, `pylint`, `pytest`).

**Fix:** `requirements.txt` now lists only Flask 3, Flask-Cors and `requests`. The database connection is stored on `flask.g`, the documented replacement for `_app_ctx_stack`.

### 9. Read the backend URL from an environment variable

**Why:** Connecting the interface to the model server meant hand-editing `ML_URL = 'http://[PLACEHOLDER]/'` in `server/app.py` each time a new ngrok tunnel started.

**Fix:** `ML_URL` comes from an environment variable and defaults to `http://localhost:5001/`. Inside Docker it's set to `http://backend:5001/`, the address of the new backend service.

### 10. Create the event-log database automatically

**Why:** The interface logs each user action to a SQLite database through `/api/storeEvent`. That database had to be created by hand from `config.sql`, and its path was fixed inside the code folder, where a container's files would be lost on rebuild.

**Fix:** The database path comes from the `DATABASE_PATH` environment variable; in Docker it's `/data/database.db`, on a volume that survives rebuilds. On startup, the server creates the table from `config.sql` if it's missing.

### 11. Replace GPT-Neo + GeDi with Claude

**Why:** The original model server can't run, because its trained files (the fortune GeDi model, three prompt embeddings and the fortune recognizer) are no longer available (see Known open items). Retraining isn't practical without the fortune-annotated data.

**Fix:** A new server, `TaleBrush_Backend/server_llm.py`, does the same three jobs with Claude, behind the same three endpoints:

| Endpoint | Original (2022) | Now |
|---|---|---|
| `/continuingGeneration` | GPT-Neo 2.7B + a tuned prompt embedding, steered token by token by GeDi toward the target fortune | Claude Sonnet 5.5 is asked for 3 candidate next sentences at the target fortune |
| `/infillingGeneration` | GPT-Neo + front or back infilling embeddings, steered by GeDi | Claude Sonnet 5.5 is given the sentences before and after, and writes the one in between |
| `/labelSentence` | GPT-Neo + a recognition embedding and a trained score head | Claude Haiku 5.5 rates the protagonist's fortune from 0 to 100 against a written rubric |

The original server's selection loop is kept: generate, score, and accept a sentence once its score is within 20 of the sketched target, otherwise try again up to the user's regeneration setting, returning the closest attempt. To keep the interface responsive, each round asks for 3 candidates in one call and scores them in parallel, and rounds are capped at 3.

**How this differs from the paper:** TaleBrush's research contribution was steering at the token level: GeDi adjusted the probability of every next word toward the target fortune. The new backend steers with instructions ("Anna's fortune should be about 20/100: things go badly") and then re-ranks finished sentences by score. The interface and the interaction are the original; the method under them is not.

The old server, `server_code.py`, and the Colab notebook are untouched, so the original pipeline still works if the model files are recovered.

### 12. Choose one model for writing and another for scoring

**Why:** The two jobs have different needs. Generated sentences are what the audience reads, and the instruction has several parts: stay consistent with the story, hit the target fortune and, when infilling, lead into the next sentence. Scoring is a narrow rating task, but it makes most of the calls: about 3 per generated sentence, plus one for every sentence the writer types. It also sits inside the retry loop, so its delay multiplies.

**Fix:** Claude Sonnet 5.5 writes, and Claude Haiku 5.5 scores. Both run at low reasoning effort, because each call produces a single sentence or a single number. Both models can be changed through the `GEN_MODEL` and `SCORE_MODEL` environment variables without code changes. The planned control check (generate at targets 10, 50 and 90, then score) will show whether Haiku's scores are consistent enough; if not, scoring moves to Sonnet.

### 13. Turn the "surprise" control into an instruction

**Why:** The interface's surprise slider originally set the sampling temperature: higher values made GPT-Neo's word choices more random. The current Claude API no longer accepts a `temperature` setting (it was removed in API version 2026-10-21), so the value can't be passed through.

**Fix:** The slider value becomes part of the prompt. Below 0.4, the model is asked for a predictable, conventional sentence; above 0.8, for a surprising turn. In between, which includes the default of 0.7, no extra instruction is added.

### 14. Make model failures recoverable

**Why:** A live demo depends on an external API. Temporary failures such as rate limits or an overloaded service shouldn't crash a request, and a safety classifier could decline to write a very dark sentence when the sketched fortune is near zero.

**Fix:**

- Model responses use structured outputs, so candidates and scores always arrive as valid JSON.
- Generation requests opt into the API's server-side fallback: if a classifier declines, the API retries on its recommended fallback model within the same call.
- A temporary error or a refusal costs one round; the next round tries again.
- If every round fails, the server returns an empty sentence, which the interface already handles as "nothing generated".
- Configuration errors, such as a missing or invalid API key, are not retried. They fail with a clear error in the logs.
- Each request is logged with the target, the score it reached, the sentence and how long it took.

**Testing so far:** The endpoints were tested offline with a fake model, using payloads copied from the interface's code, and the SDK calls were checked against a local stub API. That covers request parsing, selection, the retry cap, refusals and the response format. The live tests are under change 17.

### 15. Keep the API key in an ignored `.env` file

**Why:** The new backend needs a Claude API key, and this repository is public. It has already leaked one credential (see change 4), so the key needs a place that can't end up in a commit.

**Fix:** Settings live in a `.env` file at the repo root, which `.gitignore` already excludes. A committed `.env.example` lists every setting with comments: the API key (left blank), the two model names, and the candidate and round limits. To set up, copy it to `.env` and paste in a key.

### 16. Start everything with `make up`

**Why:** Running TaleBrush meant building two images, starting two containers, wiring the interface to the backend and passing in the API key, all by hand. For a demo, startup needs to be one step that works the same way every time.

**Fix:** `docker-compose.yml` defines both services. The backend reads its settings from `.env` and reports readiness on `/health`. The interface waits until the backend is healthy, finds it at `http://backend:5001/` and keeps its event log on a named volume. Both ports are bound to `localhost` only, because anyone who can reach the backend can spend API credit. The `Makefile` wraps the common commands:

| Command | What it does |
|---|---|
| `make up` | Checks that `.env` has a key, builds if needed, starts both services and prints the URL |
| `make down` / `make logs` | Stops the services / follows their logs |
| `make build` | Rebuilds the images |
| `make test` | Runs the contract tests against the live backend |
| `make control-check` | Checks that fortune targets actually steer generation |
| `make clean` | Removes the containers, images and event-log volume |

Running `make` alone lists these commands.

### 17. Test the backend against the live API

**Why:** The offline tests used a fake model, so they couldn't show that the real models follow the prompts, or how long a request takes.

**Fix:** `TaleBrush_Backend/tests/contract_test.py`, run with `make test`, sends payloads shaped like the interface's to each endpoint and checks the responses. It uses only the Python standard library and runs inside the backend container. `tests/control_check.py`, run with `make control-check`, generates 10 sentences at each of the fortune targets 10, 50 and 90 and checks that the scores separate. It also reports the average and slowest time per sentence and which models were used, so different `.env` settings can be compared on speed and accuracy in one run.

**Results (2026-10-28):** All contract checks passed on the first live run:

| Request | Target | Scored | Time |
|---|---|---|---|
| Rate "A pipe burst overnight and flooded the kitchen." | — | 15 | 2.6 s |
| Continue the story | 15 | 15 | 6.7 s |
| Fill in a sentence | 85 | 84 | 4.0 s |
| Continue, no target | — | 90 | 4.4 s |
| Continue, through the interface's proxy | 50 | 55 | 4.9 s |

For the target of 15, the model wrote: "Mara slid the first tray of croissants from the oven and found them pale and doughy in the middle, because the old oven she had bought secondhand had quietly died halfway through the night."

**Control check (2026-10-28):** From the same two-sentence opening about Mara's bakery, 10 sentences were generated at each target. Every one of the 30 scored within 20 points of its target:

| Target | Mean score | Range | Within 20 of target | Average time (slowest) |
|---|---|---|---|---|
| 10 | 10 | 6–15 | 10/10 | 5.5 s (8.8 s) |
| 50 | 55 | 40–62 | 10/10 | 3.8 s (4.2 s) |
| 90 | 90 | 88–92 | 10/10 | 3.8 s (4.1 s) |

Sample sentences from the same opening:

- **Target 10, scored 12:** "Before she could ring up the first customer, the ancient oven let out a metallic groan and died, leaving two hundred unbaked loaves slumped on the trays."
- **Target 50, scored 60:** "Mara watched the crowd through the fogged front window, thrilled by the numbers but dreading the moment her single oven ran out of loaves before noon."
- **Target 90, scored 90:** "By noon Mara had sold every croissant on the shelves, and she stood in the doorway with flour on her cheeks, laughing at how easily the morning had gone."

No generation round failed, and no request was declined, even at target 10. The low target was the slowest, probably because a few of its sentences needed a second round to get close enough. Note that the same model family both writes and scores. The check shows that the instruction-based steering and the scorer agree; it isn't an independent measure of fortune. A small human rating of the sentences would be the stronger test.

### 18. Compare Sonnet and Haiku as the writing model

**Why:** In a live demo, every sentence makes the audience wait. A sentence took about 4.4 seconds on average with Claude Sonnet 5.5 writing, and the slowest took 8.8 seconds. The writing model is a one-line setting in `.env`, so it was worth measuring whether the faster Claude Haiku 5.5 could write without losing control.

**Fix:** None needed in the code. `GEN_MODEL` was switched to `claude-haiku-5-5` and `make control-check` was run again, with the same opening and targets as the Sonnet run (Haiku scored in both):

| | Sonnet writing | Haiku writing |
|---|---|---|
| Target 10: mean score (within 20 of target) | 10 (10/10) | 10 (10/10) |
| Target 50: mean score (within 20 of target) | 55 (10/10) | 53 (10/10) |
| Target 90: mean score (within 20 of target) | 90 (10/10) | 90 (10/10) |
| Average time per sentence | 4.4 s | 3.5 s |
| Slowest sentence | 8.8 s | 6.3 s |

Haiku was about 20% faster with the same accuracy, and no round failed in either run. Writing turned out to be only part of the wait; the rest is likely scoring, the models' brief thinking, and network round trips. A sample of Haiku's writing at target 10 (scored 8): "Halfway through the morning, Mara discovered that she had mixed up the salt and the sugar in every batch of dough, and the line outside began to melt away one disgusted customer at a time."

The trade-off is prose quality, which the numbers can't measure; Sonnet's sentences tended to be longer and more detailed. `.env.example` still defaults to Sonnet.

### 19. Add a switch to turn off the models' thinking

**Why:** Current Claude models reason briefly before they answer, even at the lowest effort setting. Each call here writes one sentence or one number, so that step might be pure delay. Turning it off isn't one setting across models: Claude Sonnet 5.5 uses `between_tools`, Claude Haiku 5.5 uses `disabled`, and Claude Opus 5.5 can't turn thinking off at all.

**Fix:** A `THINKING` setting in `.env`, which defaults to `on`, so the original behavior is unchanged. With `THINKING=off`, `server_llm.py` sends the right option for each model, and for a model that can't turn thinking off it logs a warning and leaves thinking on. A stub-API test confirmed the exact option sent for Sonnet, Haiku and Opus. `make control-check` now also prints the thinking setting, so every run records what was tested.

**Result:** With Haiku writing and scoring, turning thinking off made scoring a single sentence faster (2.6 s to 1.6 s), but a full generated sentence improved only slightly, from 3.5 s to 3.3 s on average. The slowest dropped from 6.3 s to 5.2 s. Accuracy held: all 30 sentences were within 20 of target, with means of 10, 47 and 89. Across the three runs:

| | Sonnet, thinking on | Haiku, thinking on | Haiku, thinking off |
|---|---|---|---|
| Average time per sentence | 4.4 s | 3.5 s | 3.3 s |
| Slowest sentence | 8.8 s | 6.3 s | 5.2 s |
| Sentences within 20 of target | 30/30 | 30/30 | 30/30 |

Most of the remaining time is the two model calls each sentence needs one after the other: writing the candidates, then scoring them. Removing the separate scoring call, by having the writer rate its own candidates, would be the next step, at the cost of a less independent score.

## How to run it now

**With the Claude backend (recommended):**

1. Install Docker Desktop and start it.
2. Copy the settings file and add a Claude API key from the Claude Console:

   ```
   cp .env.example .env
   ```

   Then set `ANTHROPIC_API_KEY=` in `.env`.
3. Run `make up`, then open `http://localhost:7082/talebrush`.

`make down` stops it, and `make` lists the other commands.

**With the original GPT-Neo + GeDi pipeline:** this path stops at the notebook's download cells until the model files are recovered (see below).

1. Open the notebook in Colab: `https://colab.research.google.com/github/trvslhlt/talebrush/blob/main/TaleBrush_Server_Code_(public).ipynb`
2. Pick a GPU runtime with high RAM. GPT-Neo 2.7B and the GeDi model are loaded together.
3. Add the `NGROK_AUTHTOKEN` secret, then run all cells.
4. Build and start only the interface, pointing it at the tunnel URL printed by the last cell:

   ```
   cd TaleBrush_Interface
   docker build -t talebrush-interface .
   docker run -p 7082:7082 -v talebrush-data:/data -e ML_URL=https://<printed-hostname>/ talebrush-interface
   ```

5. Open `http://localhost:7082/talebrush`.

## Known open items

- **Blocker: the trained model files are no longer available.** The notebook downloads five Google Drive files: the fortune GeDi model, three prompt embeddings (continuation, infilling from the front, infilling from the back) and the fortune recognizer. As of 2026-10-26, all five return "Page Not Found". A known-public Drive file loads fine, so the check itself works. We found no mirror on Hugging Face, and no issues are filed on the upstream repo. Retraining isn't practical, because the repo includes only SST sentiment data, not the fortune-annotated story data the models were trained on. The way forward is to ask the original authors for the files.
- **Cells after the downloads are untested on current Colab.** These cells load GPT-Neo and GeDi. They may still hit problems with today's PyTorch or NumPy. Separately, `gdown` warns that the `--id` flag is deprecated. That's harmless, but the flag can be dropped.
- The top-level `README.md` still points to the upstream `naver-ai` notebook, not to this fork's patched one.
- `TaleBrush_Backend/server_code.ipynb`, the upstream copy, has not been patched. Only the public notebook has.
