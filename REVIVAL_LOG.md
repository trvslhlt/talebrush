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
| 2026-10-28 | — | Whole-sketch check through the interface, infilling continuity fix, README rewrite and fresh-copy check (changes 20–23) |
| 2026-10-28 | — | First browser try: blank protagonist fallback and usage notes in the README (change 24) |
| 2026-10-28 | `35652a3` | **Restoration complete:** sketching, generating, infilling and labeling all work in the browser |
| 2026-10-28 | — | Strokes that start on written sentences, and strokes over an empty story, now generate (E1–E2) |
| 2026-10-28 | — | Tooltips on the brush and eraser, and a placeholder in the empty writing area (E3–E4) |
| 2026-10-28 | — | Surprise control across its full range, and numbered explanation markers for demos (E5–E6) |
| 2026-10-28 | — | A blank protagonist name makes "you" the protagonist (E7) |

## The problem: a 2021 software stack on a 2026 runtime

The notebook was written for Colab with Python 3.8, `transformers` 4.8.2 (mid-2021) and the Flask tooling of that time. Colab now runs **Python 3.13**. Running the notebook as published failed in its first two cells:

1. **Cell 0 (install)** failed with `Failed building wheel for tokenizers`.
2. **Cell 1 (imports)** failed with `ImportError: cannot import name 'url_decode_stream' from 'werkzeug.urls'`.

The tunnel setup further down would also have failed, because it relied on an ngrok release that ngrok no longer supports.

## Changes

Changes 1–6 are in `TaleBrush_Server_Code_(public).ipynb`. Changes 7–10 are in `TaleBrush_Interface/` and changes 11–14 are in `TaleBrush_Backend/`, as part of replacing the backend with a modern LLM (see [WORKPLAN_LLM_BACKEND.md](WORKPLAN_LLM_BACKEND.md)). The front-end React code is unchanged by the restoration. Everything under **Changes** restores the original tool; work that goes beyond it is under **Enhancements**.

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

### 20. Replay a whole sketch through the interface: `make sketch-check`

**Why:** The earlier checks call the backend directly with one request at a time. In the demo, the audience sees something else: the interface sends a sketch's sentences through its own `/api/*` proxy routes, *one after another*, because each request includes the sentences generated before it. So a 5-sentence sketch takes about five times as long as one sentence. Infilling also alternates, filling one sentence from the front of the gap, then one from the back. None of this had been exercised end to end.

**Fix:** `TaleBrush_Interface/tests/sketch_check.py`, run with `make sketch-check`, replays what `TaleBrush_Generate.jsx` sends. It runs inside the interface container against the interface's own routes, so the proxy is tested too. It continues an opening sentence along a 5-point fortune curve (80, 60, 25, 10, 85), infills 2 sentences into the middle of the story, and re-labels a sentence "edited by hand". It times each step and prints the finished story, so a person can read it for continuity. Like the front end, it sends `regeneration=1`, the default unless the writer raises that slider. With only one round of candidates per sentence, an occasional miss is expected, so the check reports misses and fails only on empty or broken responses.

**Result (2026-10-28, Haiku writing and scoring, thinking off):** A 5-sentence sketch took 16.6–18.4 s, about 3.5 s per sentence, with each sentence appearing as soon as it's ready. A 2-sentence infill took 6.8–10.2 s, and a re-label took under 1 s. With the `.env.example` defaults (Sonnet writing, thinking on), the same sketch took 24.8 s. In the first run, one sentence missed: target 60, scored 40. The second run caught a real bug, which is change 21.

### 21. Infilled sentences must not refer to later events

**Why:** In the first `make sketch-check` run, the first infilled sentence read: "That weekend she cleared out the ledger, counted what remained of her savings, and realized **the review had bought her time** without yet buying her security." The review it mentions appears in a sentence *after* the gap. The prompt told the model to write a sentence that "leads naturally into" the following sentences, but never said those events hadn't happened yet, so the model treated the whole story as already known.

**Fix:** The infilling prompt now adds: "The events in these later sentences have not happened yet when your sentence takes place, so do not mention or refer back to them." On the next run, both infilled sentences set up what follows instead of referring back to it: "Before the inspector arrived, Mara had already burned the first batch of rolls, and the smell of scorched butter drifted out the open door to greet the early customers." All 7 sentences landed within 20 of their targets. This was one run, so it's evidence that the fix works, not proof that the problem can't recur.

### 22. Rewrite the README for the Docker setup

**Why:** The README's instructions still described the upstream path: open `naver-ai`'s Colab notebook (with a broken link), paste an ngrok URL into `app.py` by hand, and run `npm run production`. The models that path needs are gone, and the interface build needs Node 16 or older.

**Fix:** The top of the README now explains that this is a revival and links to this log. "Running TaleBrush" covers Docker Desktop, `cp .env.example .env`, adding the key and `make up`, with a table of the other `make` targets. The original Colab instructions are kept in a separate section, "The original pipeline (no longer runs)". It points to this fork's patched notebook and starts the interface in Docker with `ML_URL`, the same steps as "How to run it now" below. The inherited GeDi README further down is unchanged.

### 23. Check a fresh copy from scratch (no code change)

**Why:** Everything had only been run in the working copy where it was built, which can hide missing files and stale caches.

**What was done:** Every file git would commit (tracked plus untracked, minus ignored) was copied to an empty folder, and the steps were followed exactly as the new README gives them:

- `make up` with no `.env` stopped with "Missing .env. Run: cp .env.example .env, then add your ANTHROPIC_API_KEY."
- After `cp .env.example .env`, `make up` with the key still blank stopped with "ANTHROPIC_API_KEY is empty in .env."
- With the key added, `make up` started both services and the page loaded. `make test` passed every check with the default settings, and so did `make sketch-check`.
- A rebuild with `--no-cache` succeeded in 44 s. `npm ci` and `pip` still install from today's registries, and the webpack build passes on Node 16. The Docker base images were already on the machine, so a first-ever build also downloads those.
- `make clean` removed that copy's containers, images and volume. Docker Compose names resources after the folder, so the main checkout's volume was untouched.

One external dependency turned up: the page loads its icons from a Font Awesome kit (`kit.fontawesome.com/1a706cfbb1.js`) that belongs to the original authors. It still serves today, but if they cancel it, the icons will disappear.

### 24. A blank protagonist name falls back to "the protagonist"

*Replaced by E7: a blank name now makes "you" the protagonist.*

**Why:** The first browser try stopped with the alert "No context is given to generate story!". That alert is original behavior, not a revival bug. TaleBrush extends a story, so the part of the curve you draw needs a written sentence before or after it, and a curve drawn over every line of an empty story has nothing to continue. Reading that code turned up a related gap: the protagonist's name starts blank, because the original prompt that asked for it is commented out in `TaleBrush.jsx`. A writer who doesn't click the name in the side panel sends `characters: [""]`, and the backend then built prompts like "Protagonist: " with nothing after it.

**Fix:** `server_llm.py` replaces a blank name with "the protagonist", for both generation and scoring. With a blank name, a target of 15 now gives a sentence scored 15, but the model calls the character "The protagonist" literally, so naming them still matters. The interface was left unchanged, to keep the original front end as it was. Instead, the README now has a short "To write a story" section: name the protagonist, write the first sentence, then draw over the lines after it. A second try failed the same way, because of a non-obvious detail in the original chart: each line of text sits *on* a vertical gridline, so the chart's left edge is line 1. A stroke that starts at the left edge covers the opening sentence and leaves nothing before it to continue from. Each stroke is judged on its own, so a failed one doesn't carry over, but every stroke from the left edge fails the same way. The README now says to start the stroke on the first gridline. It also notes that `?task=edit` opens with a ready-made two-sentence story, and that `?task=video` replays the canned sentences from the paper's video instead of calling the model.

## Enhancements

With commit `35652a3`, the restoration is complete: the original interface runs end to end in the browser on the new backend, with the original features and behavior. Changes from here on go *beyond* the 2022 tool, for example where the original interaction was hard to use or a new model makes something possible that GPT-Neo couldn't do. They are kept separate from the restoration so the presentation can tell the two stories apart: what it took to bring the tool back, and what we added afterwards. To see the restored tool without any enhancements, check out `35652a3`.

Each enhancement is numbered E1, E2, … and has the same **Why:** and **Fix:** paragraphs as the changes above.

### E1. A stroke that starts on a written sentence continues after it

**Why:** In the first browser sessions, the most common failure was a stroke that started at the chart's left edge. The left edge is line 1, which holds the writer's opening sentence (see change 24). With nothing written before or after the stroke, the original front end stopped with "No context is given to generate story!" Starting at the left edge is the natural way to draw a curve, so writers kept hitting it, and each new stroke failed the same way.

**Fix:** In `TaleBrush.jsx`, before the original code looks for context, a stroke that would otherwise fail is checked for written sentences at its start. Those sentences are kept as they are and used as context, and only the lines after them are generated, as if the stroke had started on the first empty line. The curve over the kept sentences is reset to what it was before the stroke. This applies *only* when the stroke has no written sentences outside it. Drawing over a written sentence that has context before it is the original way to regenerate that sentence, and that still works. The alternative, moving where the chart places each line, would have changed the original layout and the paper's interaction.

### E2. An empty story gets an opening sentence

**Why:** The original tool couldn't start a story. GPT-Neo needed some text to continue, so the front end required the writer to type at least one sentence first. A Claude model can open a story from just a protagonist's name and a target fortune.

**Fix:** When nothing is written anywhere in the story, a stroke now generates from line 1 through the end of the stroke. Lines before the stroke get sentences with no fortune target. The front end calls the existing `continuing_generation` with no context lines, so no new endpoint was needed. In `server_llm.py`, an empty story asks for "the story's opening sentence, introducing" the protagonist rather than "the next sentence". `make test` now also generates from an empty story. With a target of 70, it wrote: "Mara woke before dawn to find the kettle already warm, a small kindness she had not expected from a house that had never once been kind to her." (scored 68).

**Edge cases kept from the original:** a stroke that covers only written sentences, or one whose first line is empty with a written sentence later in the stroke, still stops with the original alert, so nothing the writer typed is overwritten. These cases were worked through in the code. The rebuilt interface built and was served, Both were then confirmed in the browser.

### E3. Tooltips on the brush and eraser

**Why:** Below the chart are two unlabeled icons. A first-time user couldn't tell what the right-hand one does. In the paper's user study, a researcher explained the tools; a demo audience or a new user has no one to ask.

**Fix:** In `TaleBrush_Canvas.jsx`, each icon now has a tooltip that appears on hover. The brush says "Brush: draw the protagonist's fortune. Higher is better fortune." The eraser says "Eraser: drag across the chart to remove the fortune curve from those lines." The tooltips use the browser's built-in `title` attribute rather than a styled component, because it needs no new code or dependencies and the icons stay exactly as the original designed them.

### E4. A placeholder in the empty writing area

**Why:** On a fresh page, the writing area shows eight `>` line markers and nothing else, so nothing says where to start. With E2, a writer can also leave the story empty and let Claude write the opening, but the page gave no hint of either option.

**Fix:** While the story is empty, the first line shows light gray text: "Start Sophie's story", using the protagonist's name, or "Start your story" before a name is set. It disappears as soon as anything is typed or generated. The textarea's built-in `placeholder` couldn't be used, because the text always contains the `>` markers, so the browser never sees it as empty. Instead, `TaleBrush_TextBox_Text.jsx` draws the placeholder in a layer behind the transparent textarea, in the same font and line height, using the same layering the original uses for its sentence highlights. The layer ignores the pointer, so clicking the placeholder places the cursor in the textarea as usual.

### E5. Make the surprise control work across its full range

**Why:** In the browser, drawing in the surprise panel had no clear effect. Change 13 had turned the original temperature setting into an instruction with two thresholds: below 0.4 "predictable", above 0.8 "surprising", and nothing in between. So the middle 40% of the panel did nothing. Even at the extremes, the instruction was one line of the prompt, and the server then picked among the candidates by fortune alone. The least surprising candidate could win. Two other findings came out of reading the code. The "Surprise as stroke size/duration" option is hidden in the original interface (`display: 'none'`), and nothing reads it. Stroke speed does do something, though: a very slow stroke gives its lines two attempts instead of one.

**Fix:** In `server_llm.py`:

- **Five levels.** The surprise level maps to five instructions across the whole range: none, low, medium, high and very high.
- **Surprise is rated.** When a level is drawn, the scorer rates each candidate's surprise (0–100, against a written rubric) in the same call that rates its fortune.
- **Surprise helps choose.** The closest candidate is picked by fortune distance plus half the surprise distance. A round is accepted when fortune is within 20 and surprise within 25.
- **No cost when unused.** The interface sends 0.7 for every line without a surprise stroke. That value is treated as "not set", so plain generation sends the same requests as before, with no extra rating cost.

Offline tests with a fake model confirm the five levels, the unset value, and that surprise can change which candidate wins.

A new check, `make surprise-check`, generates 6 sentences at each of the surprise levels 0.1, 0.5 and 0.95, with no fortune target, and rates them. **Result (2026-10-28):** the average surprise ratings were 14 (range 10–15), 60 (50–70) and 89 (85–92). From the same bakery opening:

- **0.1:** "By noon, Mara had sold out of sourdough and was scrambling to bake a second batch."
- **0.5:** "A stranger in a gray coat pressed a folded letter into her palm and walked away before she could ask who had sent it."
- **0.95:** "Halfway through the morning rush, the oven timer went off and Mara discovered that the flour sacks in her storeroom had been replaced with bags of cement by someone who had been quietly watching her for months."

The same scorer rates surprise and helps choose the sentence, so the check shows that selection works rather than giving an independent measure; the sentences themselves are the better evidence. The hidden size/duration option was left as it is.

### E6. Numbered markers that explain each feature

**Why:** The interface has no labels or help, and several features are hard to discover: the chart's line positions, what the colors mean, "Generate Again", History's branches, the eraser's behavior. For a live demo, the presenter needs a way to walk through the features in order and show examples, and to point out what is new compared with the 2022 tool.

**Fix:** A new component, `TaleBrush_DemoMarker.jsx`, draws a small numbered circle that is light grey until hovered. Clicking one opens a card written like a single slide: 2–3 talking points, a one-line **Example** and, where relevant, a one-line **"Note: new in the revival"** that says what changed from the original. The first drafts were full paragraphs; in review they were cut down to points the presenter can speak to. Nine markers follow the order of a demo:

| # | Where | Explains | Note |
|---|---|---|---|
| 1 | Protagonist name | One character; fortune runs 0–100 | Blank-name fallback (change 24) |
| 2 | Writing area | One sentence per `>` line | Empty stories and the placeholder (E2, E4) |
| 3 | Chart, left | Line positions, drawing, slow strokes | Claude instead of GPT-Neo + GeDi; strokes over written lines (change 11, E1) |
| 4 | Chart, right | Green band, blue and grey lines, neutral line | Claude Haiku as the fortune scorer (change 11) |
| 5 | Where Generate Again appears | Rerunning the last stroke | — |
| 6 | Writing area, lower | Editing re-scores; filling gaps | Infill continuity fix (change 21) |
| 7 | Surprise checkbox | Drawing surprise, with real low and high examples | The rebuilt surprise control (E5) |
| 8 | History | Versions as branches; preview, switch, rename, delete | — |
| 9 | Brush and eraser | The eraser rewrites lines with no fortune target | Tooltips (E3) |

The "Generate Again" button only appears after a stroke, so marker 5 has its own fixed position next to where the button appears and is always visible. In the first version it was attached to the button and hidden with it. Only one card is open at a time. A card closes with ×, Escape, a click elsewhere or a second click on its marker. Cards near the bottom of the window open upward. Each card renders in a portal on the page body, so the chart's `overflow: hidden` can't clip it. Pointer events stop at the marker, so clicking one never starts a stroke or closes the History menu. Adding `?markers=off` to the URL hides them all.

**How it was checked:** headless Chrome, driven through the DevTools protocol, loaded the page, opened each card and drew a real stroke. Screenshots confirmed where each marker sits, including marker 5 next to "Generate Again" after the stroke. The same runs settled two claims before they went into the cards. The eraser rewrites the lines it crosses with no fortune target: lines 5 and 6 came back as new sentences. History lists versions as branches (0, 0-0, 0-0-0), each with rename and delete buttons.

### E7. A blank protagonist name makes "you" the protagonist

**Why:** The original interface wouldn't let anyone start without a name. Drawing showed "Please first specify the protagonist's name." and clicking into the writing area showed "Please first set the name of protagonist." Change 24's fallback, "the protagonist", only helped API calls, and it read awkwardly: the model wrote "The protagonist signed the lease…". Leaving the name blank is a natural way to say "make it about me".

**Fix:** A blank name now means a second-person story.

- **Front end:** the two alerts are removed. With no name, the label above the chart reads "Your fortune" (the name box's placeholder is "Your"), and the writing area already invites "Start your story" (E4).
- **Backend:** in `server_llm.py`, a blank name becomes "you". The writing prompt then says the story is told in the second person, asks for sentences that address the protagonist as "you", and phrases the target as "your fortune". The scorer is told the protagonist is the reader.
- **Popup 1:** it says a blank name means a story about you, and lists the five fortune levels.

`make test` now also generates with a blank name and checks that the sentence is about "you": "You step onto the platform just as the last train pulls away, and your ticket, you realize too late, was for yesterday." In headless Chrome, a stroke over an empty story with no name wrote three second-person sentences.

**The fortune scale already had five levels.** The scorer's rubric anchors 0 (catastrophe), 25 (bad), 50 (neutral), 75 (good) and 100 (triumph). The writing prompt uses five matching bands, and the chart's background is drawn as five bands. Only popup 1 had shown just the two ends. Popups 1 and 4 now list all five.

## How to run it now

**With the Claude backend (recommended):**

1. Install Docker Desktop and start it.
2. Copy the settings file and add a Claude API key from the Claude Console:

   ```
   cp .env.example .env
   ```

   Then set `ANTHROPIC_API_KEY=` in `.env`.
3. Run `make up`, then open `http://localhost:7082/talebrush`.

`make down` stops it, and `make` lists the other commands. Before a demo, `make sketch-check` replays a full sketch and shows how long the audience will wait.

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
- **The icons depend on the original authors' Font Awesome kit** (change 23). It works today; if it stops, the page still works, but without icons.
- `TaleBrush_Backend/server_code.ipynb`, the upstream copy, has not been patched. Only the public notebook has.
