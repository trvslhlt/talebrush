Issues
1. Manually changing text can leave the story in an inconsistent state
2. Manually adding new lines breaks the UI
3. No way to stop the generation. Interaction blocked 

Model Changes
1. Claude replaced the sentence generator (GPT-Neo plus a tuned prompt embedding).
2. Word-level steering by GeDi was replaced by stating the target fortune in the prompt.
3. The trained fortune scorer was replaced by a Haiku prompt with a rubric. Overall, general model ability replaced three components trained on custom data.
4. The generate–score–select loop is unchanged.
5. Surprise went from a continuous sampling temperature to five prompt levels, and it's now also rated and used when choosing among candidates.