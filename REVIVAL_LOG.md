# TaleBrush Revival Log

A record of what it took to get the 2022 TaleBrush backend running again on present-day Google Colab, and why each change was needed.

**Original project:** [naver-ai/TaleBrush](https://github.com/naver-ai/TaleBrush) — *TaleBrush: Sketching Stories with Generative Pretrained Language Models* (CHI 2022). TaleBrush lets a writer sketch a line for the protagonist's fortune. A GPT-Neo 2.7B model, steered by a GeDi discriminator, then writes story sentences that follow the line.

## Timeline

| Date | Commit | What |
|---|---|---|
| 2022-07-13 | `e19c3b2` | Original code imported (Kang Min Yoo, NAVER AI) |
| 2026-10-26 | `6dbe56c` | Added the authors' public Colab notebook, `TaleBrush_Server_Code_(public).ipynb` |
| 2026-10-26 | `482e0ce` | Patched the notebook to run on current Colab (details below) |

## The problem: a 2021 software stack on a 2026 runtime

The notebook was written for Colab with Python 3.8, `transformers` 4.8.2 (mid-2021) and the Flask tooling of that time. Colab now runs **Python 3.13**. Running the notebook as published failed in its first two cells:

1. **Cell 0 (install)** failed with `Failed building wheel for tokenizers`.
2. **Cell 1 (imports)** failed with `ImportError: cannot import name 'url_decode_stream' from 'werkzeug.urls'`.

The tunnel setup further down would also have failed, because it relied on an ngrok release that ngrok no longer supports.

## Changes

All changes are in `TaleBrush_Server_Code_(public).ipynb`. The model code, the model weights and the front end are unchanged.

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

## How to run it now

1. Open the notebook in Colab: `https://colab.research.google.com/github/trvslhlt/talebrush/blob/main/TaleBrush_Server_Code_(public).ipynb`
2. Pick a GPU runtime with high RAM. GPT-Neo 2.7B and the GeDi model are loaded together.
3. Add the `NGROK_AUTHTOKEN` secret, then run all cells.
4. Copy the hostname printed by the last cell into `TaleBrush_Interface/server/app.py`, replacing `[PLACEHOLDER]`.
5. Start the front end with `npm run production` from `TaleBrush_Interface`.

## Known open items

- **Blocker: the trained model files are no longer available.** The notebook downloads five Google Drive files: the fortune GeDi model, three prompt embeddings (continuation, infilling from the front, infilling from the back) and the fortune recognizer. As of 2026-10-26, all five return "Page Not Found". A known-public Drive file loads fine, so the check itself works. We found no mirror on Hugging Face, and no issues are filed on the upstream repo. Retraining isn't practical, because the repo includes only SST sentiment data, not the fortune-annotated story data the models were trained on. The way forward is to ask the original authors for the files.
- **Cells after the downloads are untested on current Colab.** These cells load GPT-Neo and GeDi. They may still hit problems with today's PyTorch or NumPy. Separately, `gdown` warns that the `--id` flag is deprecated. That's harmless, but the flag can be dropped.
- The top-level `README.md` still points to the upstream `naver-ai` notebook, not to this fork's patched one.
- `TaleBrush_Backend/server_code.ipynb`, the upstream copy, has not been patched. Only the public notebook has.
