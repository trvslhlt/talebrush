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

**Testing so far:** The endpoints were tested offline with a fake model, using payloads copied from the interface's code, and the SDK calls were checked against a local stub API. That covers request parsing, selection, the retry cap, refusals and the response format. Testing against the live API needs an API key and is the next step.

### 15. Keep the API key in an ignored `.env` file

**Why:** The new backend needs a Claude API key, and this repository is public. It has already leaked one credential (see change 4), so the key needs a place that can't end up in a commit.

**Fix:** Settings live in a `.env` file at the repo root, which `.gitignore` already excludes. A committed `.env.example` lists every setting with comments: the API key (left blank), the two model names, and the candidate and round limits. To set up, copy it to `.env` and paste in a key.

## How to run it now

1. Open the notebook in Colab: `https://colab.research.google.com/github/trvslhlt/talebrush/blob/main/TaleBrush_Server_Code_(public).ipynb`
2. Pick a GPU runtime with high RAM. GPT-Neo 2.7B and the GeDi model are loaded together.
3. Add the `NGROK_AUTHTOKEN` secret, then run all cells.
4. Build and start the interface, pointing it at the tunnel URL printed by the last cell:

   ```
   cd TaleBrush_Interface
   docker build -t talebrush-interface .
   docker run -p 7082:7082 -v talebrush-data:/data -e ML_URL=https://<printed-hostname>/ talebrush-interface
   ```

5. Open `http://localhost:7082/talebrush`.

Until the model files are recovered (see below), this path stops at the download cells. The planned LLM backend will replace it with a single `make up`.

## Known open items

- **Blocker: the trained model files are no longer available.** The notebook downloads five Google Drive files: the fortune GeDi model, three prompt embeddings (continuation, infilling from the front, infilling from the back) and the fortune recognizer. As of 2026-10-26, all five return "Page Not Found". A known-public Drive file loads fine, so the check itself works. We found no mirror on Hugging Face, and no issues are filed on the upstream repo. Retraining isn't practical, because the repo includes only SST sentiment data, not the fortune-annotated story data the models were trained on. The way forward is to ask the original authors for the files.
- **Cells after the downloads are untested on current Colab.** These cells load GPT-Neo and GeDi. They may still hit problems with today's PyTorch or NumPy. Separately, `gdown` warns that the `--id` flag is deprecated. That's harmless, but the flag can be dropped.
- The top-level `README.md` still points to the upstream `naver-ai` notebook, not to this fork's patched one.
- `TaleBrush_Backend/server_code.ipynb`, the upstream copy, has not been patched. Only the public notebook has.
