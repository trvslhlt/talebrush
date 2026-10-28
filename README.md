--------------------------------------------------------------------------------

Code for TaleBrush.

[Paper link](https://johnr0.github.io/assets/publications/CHI2022-TaleBrush.pdf)
[Video link](https://youtu.be/F_y6drm6af8)
[Project website link](https://johnr0.github.io/publications/TaleBrush_CHI2022/)

Partially forked from [GeDi: Generative Discriminator Guided Sequence Generation](https://arxiv.org/abs/2009.06367) and [Flask React Boilerplate](https://travis-ci.org/YaleDHLab/flask-react-boilerplate).

# Introduction

TaleBrush uses a line sketching interaction for intuitive control and sensemaking of story generation with GPT-based language models.
TaleBrush allows uses to control the protagonist's fortune. 


This fork revives TaleBrush to run on current tooling. The original models are no longer downloadable, so the model server now uses Claude for generation and fortune scoring, and the whole tool runs locally in Docker. [REVIVAL_LOG.md](REVIVAL_LOG.md) explains every change and how this backend differs from the paper's.

## Running TaleBrush

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running) and a Claude API key from the [Claude Console](https://platform.claude.com).

1. Create your settings file and add your key to it:

   ```
   cp .env.example .env
   ```

   Then set `ANTHROPIC_API_KEY=` in `.env`. Git ignores `.env`, so the key stays on your machine.

2. Build and start both services (the first build takes a few minutes):

   ```
   make up
   ```

3. Open http://localhost:7082/talebrush.

To write a story:

1. Optionally, type the protagonist's name above the chart, e.g. Mara. Leave it blank and the story is about *you*, told in the second person.
2. Optionally, write the first sentence yourself on the first line of the text box. If you leave the story empty, Claude writes the opening.
3. Draw the fortune curve: high is good fortune, low is bad. In the chart, each line of text sits on a vertical gridline: the left edge is line 1, the first gridline is line 2, and so on. If your stroke starts over sentences you've written, they're kept and the story continues after them.
4. To fill a gap between written sentences, draw over just the empty lines in between. Editing a sentence by hand re-scores it.

The small numbered circles around the page explain each feature with an example, and say what's new since the 2022 original. Click one to open it. Add `?markers=off` to the URL to hide them.

For a ready-made opening, open http://localhost:7082/talebrush?task=edit, which starts with two sentences about Jack. Don't use `?task=video`: it replays the canned sentences from the paper's video instead of calling the model.

`make down` stops TaleBrush, and `make help` lists the other targets:

| Target | What it does |
|---|---|
| `make logs` | Follow both services' logs; each generated sentence is logged with its target, score and time |
| `make test` | Check the backend's API contract (a few real model calls) |
| `make control-check` | Generate 30 sentences at fortune targets of 10, 50 and 90 and check that their scores separate |
| `make surprise-check` | Generate sentences at low, medium and high surprise and check that they get more surprising |
| `make sketch-check` | Replay a 5-sentence sketch, an infill and a re-label through the interface, timing each step |
| `make clean` | Remove the containers, images and the event-log volume |

The settings in `.env` choose the models and trade quality for speed; `.env.example` explains each one.

## The original pipeline (no longer runs)

The original backend ran GPT-Neo 2.7B with GeDi on a Colab GPU, exposed through ngrok. Its fine-tuned model files were hosted on Google Drive and have since been removed, so this path stops at the model download. The code is kept in [TaleBrush_Backend](TaleBrush_Backend) for reference, and the original instructions were:

1. Run [TaleBrush_Server_Code_(public).ipynb](TaleBrush_Server_Code_(public).ipynb) in Colab with a high-RAM GPU runtime, with your ngrok authtoken stored as the Colab secret `NGROK_AUTHTOKEN`.
2. Build and start only the interface, pointing it at the ngrok URL printed by the last cell:

   ```
   cd TaleBrush_Interface
   docker build -t talebrush-interface .
   docker run -p 7082:7082 -v talebrush-data:/data -e ML_URL=https://<printed-hostname>/ talebrush-interface
   ```

3. Open http://localhost:7082/talebrush.

<!-- We use GeDi with the secondary code as the level of the protagonist's fortune (0~100).

* Parse out protagonist for the movie summary dataset.
* Collect annotations for the protagonist's fortune.
* Improve sequential generation?


# Below is ReadMe From GeDI:

Blogpost [here](https://blog.einstein.ai/gedi/)


#### Colab Notebook on controlling topic using GeDi [here](https://colab.research.google.com/github/salesforce/GeDi/blob/master/GeDi_guided_GPT_2_XL.ipynb)     

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/salesforce/GeDi/blob/master/GeDi_guided_GPT_2_XL.ipynb)

## Updates

Sept 29, 2020: Adding support for [GeDi-guided GPT-3 generation](https://github.com/salesforce/gedi#gpt-3-generation-added-after-paper-api-access-needed) (API key needed)


## Introduction

GeDi is a method of using class-conditional language models (which we refer to as generative discriminators (GeDis)) to guide generation from other (potentially much larger) language models. This has several advantages over finetuning large language models directly including:

* significantly less training computation.
* maintaining the diversity of the original language model (If we finetune a large pretrained language model to a specific attribute dataset, we will likely reduce the broad generation capabilities of the model).
* teaching the language model what not to generate. This is especially useful for applications like detoxification.


GeDi is a form of discriminator guided generation. A discriminator that can classify an attribute could be used to guide language model generation towards that attribute by classifying the sequences that result from candidate next tokens. However, using a normal discriminator (such as [BERT](https://arxiv.org/abs/1810.04805)) to do this would be very computationally expensive during generation, since it would require feeding in every candidate next token one-by-one to the discriminator to be classified. However, using generative discriminators, we can very efficiently classify candidate next tokens during generation using Bayes rule (see Section 3.1 of the paper). As an added bonus, [generative discriminators can be used as zero shot classifiers](https://arxiv.org/abs/1703.01898), and can therefore be used to guide generation towards unseen topics.


## Dependencies

- Python 3.7, PyTorch 1.4
(We recommend creating a container using the [pytorch/pytorch:1.4-cuda10.1-cudnn7-devel](https://hub.docker.com/layers/pytorch/pytorch/1.4-cuda10.1-cudnn7-devel/images/sha256-c612782acc39256aac0637d58d297644066c62f6f84f0b88cfdc335bb25d0d22?context=explore) official pytorch docker image.)
- Run `scripts/setup.sh`:
  ```
  cd scripts
  bash setup.sh
  ```
  This will install the following:

  - Transformers v2.8.0 and its example-specific requirements mentioned [here](https://github.com/huggingface/transformers/tree/master/examples#important-note)
  - (optional) Apex (details [here](https://github.com/NVIDIA/apex#linux)) for fp16 training and generation (installing apex takes a while; comment corresponding lines in `setup.sh` if you want to skip)
  - `wget` and `unzip` (to download and unzip data and model checkpoints)

## Generating from models used in paper
- First download the models:
```
cd scripts
bash get_models.sh
```
This downloads and saves the topic, sentiment, and detoxifier models in the folder `../pretrained_models`

- To generate, use `bash run_generation.sh`, which calls `../generate_GeDi.py` with the appropriate arguments (set for topic generation by default).

Important arguments include:

* `--mode` can be set to `topic`, `sentiment`, or `detoxify`
* `--gen_type` can be set to `gedi` for GeDi guided generation, `cclm` for class conditional generation, or `gpt2` to generate from raw GPT-2
* `--gen_length` max length of generation
* `--gedi_model_name_or_path` path to GeDi model. If unused, will assume you ran `bash get_models.sh` and infer model directory from `--mode` argument
* `--filter_p` equal to 1 - \rho in Equation 7 of the paper
* `--target_p` equal to \tau from the paper
* `--disc_weight` exponent for posterior weighting (\omega in Equation 6 of the paper)
* `--fp16` converts GPT2-XL weights to fp16 for faster generation and less GPU memory usage

Running will allow you to enter control codes and prompts for generation in a continuous loop until you exit.

### Topic generation (Section 6.3 & 6.4 of the paper)
- Set `--mode topic` in `scripts/run_generation.sh`
- You will be prompted to give a topic code. The model was trained on `world`, `sports`, `business`, and `science`, but can often generate other topics zero-shot, for instance `space`, `fire`, `climate`, `education`
- If the topic code you give is more than one [BPE token](https://arxiv.org/abs/1508.07909), the model often struggles because the 4 training topics were all 1 BPE token. You will be warned that this might not work, but can proceed by hitting enter again (or can type a new topic code).
- After the topic code, you will be asked to give a prompt to the model to condition on for generation.

### Sentiment control (Section 6.1 of the paper)
- Set `--mode sentiment` in `scripts/run_generation.sh`
- The model can controllably generate positive or negative text. When generalizing to other domains such as stories, this often translates to positive/negative mood or tone of the story (since sentiment implies an opinion).
- The model is set to positive sentiment by default. You will be prompted for the opportunity to change to negative sentiment by typing `n`. Note that the negative model can be very negative, and this sometimes results in toxic or offensive samples.
- You will then be asked to give a prompt to the model to condition on for generation.

### Detoxication (Section 6.2 of the paper)
- Set `--mode detoxify` in `scripts/run_generation.sh`
- This mode can be used to avoid generating toxic or offensive text.
- You will then be asked to give a prompt to the model to condition on for generation.
- GeDi can often find a way to navigate especially aggressive prompts, but does rarely but occasionally still generate toxic text if given certain prompts. We observed this can be a problem for longer generations.

### Class-conditional LM and GPT-2 generation
- Two of the baselines we consider are generating from GPT-2 (will give same result regardless of control codes), and generating from the GeDi model directly as a class-conditional language model (instead of using it to guide generation from GPT-2).
- Set `--gen_type gpt2` to generate from GPT-2, and `--gen_type cclm` to generate directly from the GeDi as a class-conditional language model. `--gen_type cclm` corresponds to all experiments in Section 5 of the paper, and the CC-LM baselines in Section 6.1.

### GPT-3 generation (added after paper, API access needed)
- If you have your own GPT-3 API secret key, you can use GeDi to guide decoding from GPT-3.
- This is somewhat limited, since the GPT-3 API only allow access to the top 100 next token log probabilities.
- Reuses settings for controlling GPT-2 (which uses all next token log probs), retuning for GPT-3 could give better results.
- It is also slow (up to 1 second per token) because modifying GPT-3 decoding requires calling the API one token at a time.

To control sentiment from GPT-3 using your API key (should have prefix "sk"):

`pip install openai`

`python ../generate_GeDi.py --penalize_cond --gen_length 100 --mode sentiment --gpt3_api_key sk-xxxxxxxx`

You can also try changing the `--mode` or other arguments. To generate directly from GPT-3 without GeDi using our same greedy decoding scheme:

`python ../generate_GeDi.py --penalize_cond --gen_length 100 --mode sentiment --gen_type gpt2 --gpt3_api_key sk-xxxxxxx`


## Train your own GeDi

- This repository includes code to train a topic GeDi using GeDi training.
- There are some differences in this training script and the one used to train the pretrained model. The pretrained model only used half of AG news, and there were some slight differences in preprocessing.
- This runs in about 5 hours on a 16GB V100 GPU on GCP.
- First, download and process the topic data:

```
cd scripts
bash get_data.sh
```

- Then run training using:

`bash run_training.sh` which calls `../train_GeDi.py` with the appropriate arguments

- The directory for model to be saved is specified by `output_dir` argument.
- When generating from your trained GeDi, you will need to call `../generate_GeDi.py` (called from `bash run_generation.sh`) with `--gedi_model_name_or_path` set to the directory of your trained model. -->

## Citation
```
@inproceedings{10.1145/3491102.3501819,
author = {Chung, John Joon Young and Kim, Wooseok and Yoo, Kang Min and Lee, Hwaran and Adar, Eytan and Chang, Minsuk},
title = {TaleBrush: Sketching Stories with Generative Pretrained Language Models},
year = {2022},
isbn = {9781450391573},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
url = {https://doi.org/10.1145/3491102.3501819},
doi = {10.1145/3491102.3501819},
abstract = {While advanced text generation algorithms (e.g., GPT-3) have enabled writers to co-create stories with an AI, guiding the narrative remains a challenge. Existing systems often leverage simple turn-taking between the writer and the AI in story development. However, writers remain unsupported in intuitively understanding the AI’s actions or steering the iterative generation. We introduce TaleBrush, a generative story ideation tool that uses line sketching interactions with a GPT-based language model for control and sensemaking of a protagonist’s fortune in co-created stories. Our empirical evaluation found our pipeline reliably controls story generation while maintaining the novelty of generated sentences. In a user study with 14 participants with diverse writing experiences, we found participants successfully leveraged sketching to iteratively explore and write stories according to their intentions about the character’s fortune while taking inspiration from generated stories. We conclude with a reflection on how sketching interactions can facilitate the iterative human-AI co-creation process. },
booktitle = {CHI Conference on Human Factors in Computing Systems},
articleno = {209},
numpages = {19},
keywords = {story writing, controlled generation, creativity support tool, story generation, sketching},
location = {New Orleans, LA, USA},
series = {CHI '22}
}
```

## License
TaleBrush is licensed under [GPL3 LICENSE](LICENSE).
