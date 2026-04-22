# CardiAg – code

    Last update:    April 22, 2026
    Author(s):      Marta Gerosa
    Email:          gerosa [at] cbs.mpg.de



## Folders

| Folder            | Description |
|----------         |-------------|
| `\analysis`       | Jupyter notebooks for analyzing the behavioral data of the intentional binding task in relation to cardio-respiratory activity. |
| `\preprocessing`  | Python scripts and Jupyter notebooks for preprocessing the behavioral, ECG and RESP data. This should normally not be necessary to re-run (as it includes manual steps performed on individual subject data). **We recommend to directly download and use the preprocessed data for the main analyses.** |


## Preprocessing

We recommend not to re-run the preprocessing script and refer directly to the already preprocessed data stored in `data/derivatives/`. 

| File   | Description |
|----------|-------------|
| `CardiAg_beh_preproc.py` | Preprocessing of the behavioral data from the Intentional Binding (IB) task, including angle conversion and correction, judgement error (JE) computation, and subject-level summary of behavioral performance (incl. plots of real vs. reported clock hand positions and JE distribution).  |
| `CardiAg_ecg_preproc.ipynb` | Preprocessing of the raw electrocardiogram (ECG) data, developed as part of the Brain-Body Analysis Special Interest Group (BBSIG). This includes: (optional) flipping and filtering, R-peak detection, R-peak manual correction using Systole's `Editor`, QRS delineation and T-wave offset detection, HR interpolation. The main output containing the preprocessed ECG data (`*_ecg-preproc.json`) is stored for each subject in `data/derivatives/ecg-preproc/sub-xx/`. |
| `CardiAg_ecg_resp_preproc_quality.ipynb` | Extracting relevant features from the ECG and RESP preprocessing specifically related to the main blocks (i.e., pre- and post-task baseline, plus task experimental conditions - BasA, OpA, BasT, OpT - without breaks). This includes the percentage of manually corrected R-peaks and expiration/inspiration onsets, the percentage of noisy segments in the main blocks, as well as the respiratory rate (RResp) and respiratory cycle duration in the pre- & post-task baseline. |
| `CardiAg_resp_functions.py` | Python helper function to the `CardiAg_resp_preproc.ipynb` notebook, used to produce the custom-made `RespEditorGUI` for the interactive visualization and manual correction of expiration/inspiration onsets on the RESP signal. |
| `CardiAg_resp_preproc.ipynb` | Preprocessing of the raw respiration (RESP) data. This includes: (optional) flipping, smoothing and z-scoring, expiration and inspiration onset detection, expiration/inspiration onset manual correction sing the custom-made `RespEditorGUI`, and respiratory phase vector computation. The main output containing the preprocessed RESP data (`*_resp-preproc.json`) is stored for each subject in `data/derivatives/resp-preproc/sub-xx/`. |


## Main analysis

The codebase for the main analysis is listed in the recommended order of usage. 

| File   | Description | Produces |
|----------|-------------| -------------|
| `cardiacphase_functions.py` | Python helper function to the `CardiAg_cardiac_phase_analysis.ipynb` notebook, used to produce an interactive visualization of the ECG signal at the trial level, based on a given condition, block and trial number, with systole/diastole segmentation and T-wave offset location. | n/a |
| `CardiAg_demographics.ipynb` | Overview of demographic data for the participants included in the sample at each analysis step. | n/a |
| `CardiAg_beh_analysis.ipynb` | 1. Main analysis of the behavioral data from the intentional binding task, including the computation of the mean judgment error (mJE) for action (`JE_act`) and tone (`JE_tone`) trials, and the action and tone binding measures at the group level. | Figure 2a-b |
| `CardiAg_cardiac_phase_analysis.ipynb` | 2. Main analysis of the cardiac data from the intentional binding task, including: extraction of trial-level relevant ECG features around action/tone onset and binning into systole/diastole, recomputation of T-wave offset using the Trapezium Area approach, binary analysis using normalized cardiac phase ratios, binary analysis using cardiac phase binning of intentional binding, circular analysis of action onsets across the cardiac cycle, and lastly pre- and post-action R-R interval changes. | Figure S1-S2, Figure 3b-e, Figure 7a-b, Figure 3a, Figure 6a, ExData Figure 1 |
| `CardiAg_resp_phase_analysis.ipynb` | 3. Main analysis of the respiratory data from the intentional binding task, including: extraction of trial-level relevant RESP features around action/tone onset and binning into expiration/inspiration, binary analysis using normalized respiratory phase ratios, binary analysis using respiratory phase binning of intentional binding, circular analysis of action onsets across the respiratory cycle, and lastly pre- and post-action respiratory cycle changes. | Figure S3b, Figure 4b-e, Figures 7c-d, Figure 4a, ExData Figure 2, ExData Figure 3 |
| `CardiAg_cardioresp_phase_analysis.ipynb` | 4. Main analysis of the cardio-respiratory data from the intentional binding task, including: cardio-respiratory phase effects on intentional binding, Phase Locking Value (PLV) analysis, and R-R interval changes across respiratory cycle. | Figure 5c, Figure S3c |
| `CardiAg_raincloud_plots.ipynb` | 5. Creating the raincloud plots for the cardiac phase analysis, pre- and post-action R-R interval changes, respiratory phase analysis and cardio-respiratory analysis. Before running this script, perform the corresponding analysis scripts from step 1 to 4 above. | Figure 3c-d, Figure 4c-d, Figure 5a-b, Figure 6b-c |

## Contact

For questions regarding this project, please contact:

**Marta Gerosa**

Max Planck Institute for Human Cognitive and Brain Sciences, Dept. Neurology

gerosa [at] cbs.mpg.de 


## Copyright/license

MIT License

Copyright (c) 2026, Marta Gerosa

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
