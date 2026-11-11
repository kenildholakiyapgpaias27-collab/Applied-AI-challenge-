# Learning the shade mapping from Meta Casual Conversations v2

The advisor's shade library (the 10 Aaina tones and every product shade) is the ground truth. These scripts use
a labelled face dataset only to learn **where each Aaina tone lands in real camera colour**, so the reader maps
photos onto the library more accurately. They never add a shade.

**Before you start:** request access and accept Meta's licence yourself. Its terms limit training to certain
labels and focus on evaluating models: confirm that fitting this mapping layer on the Monk labels is allowed for
your use. Evaluation (step 4's report) is the clearly permitted part.

```bash
pip install playwright numpy opencv-python   # mediapipe optional, for better face boxes
python3 inspect_dataset.py /data/ccv2 --out ccv2_report      # 1. look at the real structure; fix ccv2_report/config.json
python3 prepare_frames.py ccv2_report/config.json --out work # 2. balanced participants per tone, frames, face ovals (check work/check/)
python3 run_reader.py work/manifest.csv --out work/features.csv   # 3. run the app's own reader on every frame
python3 train_mapping.py work/features.csv --out ../../data/calibration.json --report work/report.md   # 4. learn + validate
cd ../.. && python3 build.py                                  # the page now uses data/calibration.json
```

Set `filters.country` to `India` in config.json to learn from Indian participants only (check that each tone still
has enough people; the report flags thin tones). Label meaning: the dataset's Monk values are annotators'
judgement of apparent skin tone. They are used only to place the Aaina tones in camera colour space; product
shades are matched by colour similarity inside the library.
