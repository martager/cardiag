# -*- coding: utf-8 -*-
"""
Name: CardiAg_beh_preprocess.py
Title: CardiAg: Behavioral Preprocessing

Author: Marta Gerosa
Created on: 31 January 2025
Last updated: 22 April 2026

Pipeline for preprocessing behavioral data from the Intentional Binding task (IBtask) used in the CardiAg study.
The IBtask consists of four conditions:
    - Baseline Action (BasA): voluntary keypress only, judge time of action
    - Baseline Tone (BasT): auditory tone only, judge time of tone
    - Operant Action (OpA): voluntary keypress followed by tone, judge time of action
    - Operant Tone (OpT): voluntary keypress followed by tone, judge time of tone

The behavioral data file (*_beh.tsv) includes the following columns:
    - subjID (numeric)
    - condition (string): experimental condition, either "BasA", "BasT", "OpA" or "OpT"
    - n_block (numeric): block number
    - n_trial (numeric): trial number 
    - act_time (numeric): time between trial onset and keypress, in seconds ("NaN" for BasT condition)
    - angle_act_report (numeric): reported clock hand position of keypress onset, in radians ("NaN" for BasT & OpT condition)
    - angle_act_real (numeric): real clock hand position of keypress onset, in radians ("NaN" for BasT condition)
    - tone_time (numeric): time between trial onset and tone onset, in seconds ("NaN" for BasA condition)
    - angle_tone_report (numeric): reported clock hand position of tone onset, in radians ("NaN" for BasA & OpA condition)
    - angle_tone_real (numeric): real clock hand position of tone onset, in radians ("NaN" for BasA condition)
    - start_angle (numeric): starting clock hand position at trial onset, in radians
    - final_angle (numeric): final clock hand position at trial offset, in radians

The following steps are included in this analysis pipeline: 
    1. DATA IMPORT AND INITIAL FORMATTING:
        1a. Load behavioral data file (*_beh.tsv)
        1b. Initialize markdown file for individual summary of beh preprocessing
        1c. Format NoResponse trials with NaNs & calculate percentage 
    2. ANGLE CONVERSION & CORRECTION: 
        - Convert original angle measures from rad to deg and "ticks" (0-59) + correct real angles for multiple clock rotations 
            2a. Action judgment trials (BasA, OpA)
            2b. Tone judgment trials (BasT, OpT)
            2c. Start and final angles (all conditions)
    3. REAL VS. REPORT ANGLE DIFFERENCES:
        - Compute distance between real and reported angles (both in ticks and deg), seperately for action and tone trials
            3a. Action trials: real vs. report angle difference (in ticks and deg)
            3b. Tone trials: real vs. report angle difference (in ticks and deg)
    4. COMPUTE JUDGMENT ERROR:
        - Compute Judgment Error (JE) as the time difference between real and reported angles (in ms), separately for action and tone trials
            4a. Action trials: Judgment Error (JE_act)
            4b. Tone trials: Judgment Error (JE_tone)
    5. COMPUTE NUMBER OF CLOCK ROTATIONS:
        - Determine number of clock rotations until keypress or tone
    6. PLOT REAL VS. REPORTED CLOCK HAND POSITIONS:
        - Plot real vs. reported clock hand positions of action/tone time, sep. per each condition (to check for systematic biases)
    7. OUTLIERS REMOVAL [not in use]: 
        7a. Method 1: +/- 3SD (default: enable_outlier_3sd = False)
        7b. Method 2 (non-parametric): median +/- MAD (default: enable_outlier_mad = False)
    8. MERGE TIMESTAMPS FROM TASK EVENTS: 
        - Merge timestamps of task events from _events.tsv file into processed behavioral results (trial, clock, keypress & tone onsets)
    9. SAVE PROCESSED BEHAVIORAL RESULTS TSV FILE: 
        - Save TSV file with processed behavioral results (*_beh_preproc.tsv) in ".\derivatives\beh-preproc\sub-XX\beh" folder
    10. INTENTIONAL BINDING MEASURES SUMMARY: Intentional Binding summary (action binding, tone binding) per each participant
    11. SAVE PARTICIPANTS BEH PREPROCESS SUMMARY (Optional): 
        - Save TSV file with summary of all participants' beh preprocessing (e.g., percent NoResp trials, wait rotations)

Returns:
    - "*_beh-preproc.tsv" in ".\derivatives\beh-preproc\sub-XX\beh" folder
    - "*_beh-preproc-summary.md" in ".\derivatives\beh-preproc\sub-XX\beh" folder
    - Four plots per participant as PNG images in ".\derivatives\beh-preproc\sub-XX\beh" folder:
        - "*_JEact-distribution.png" and "_JEtone-distribution.png"
        - "*_clockhand-act-circplot.png" and "_clockhand-tone-circplot.png"
    - (Optional) "task-CardiAgIBTask_beh-preproc-summary.tsv" in ".\derivatives\beh-preproc" folder 


"""
#%% PREPARATION

############## Import modules ##############

import pandas as pd
import math
import numpy as np
from statsmodels import robust
import seaborn as sns
import os
import matplotlib.pyplot as plt

############## General preferences ##############

# Set resolution parameters
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300

# Specify if "*_beh-preproc-summary.tsv" is needed
overall_summary = True


#%% 1. DATA IMPORT AND INITIAL FORMATTING

participant_ids = [1, 2, 3, 5, 6, 12, 13, 15, 16, 17, 18, 19, 
                   20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                   31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42,
                   43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 57]

# Specify the BIDS-compatible beh data path
wd = r'.\data'                  # directory of data storage
exp_name = 'CardiAgIBTask'      # study name
datatype_name = 'beh'           # current datatype folder according to BIDS
beh_preproc_folder = 'beh-preproc'

# Prepare the overall participants summary TSV (if selected)
if overall_summary: 
    # Specify the file path
    fname = 'task-CardiAgIBTask_beh-preproc-summary.tsv'
    fpath = os.path.join(wd, 'derivatives', beh_preproc_folder, fname)
    
    # Initialize an empty df to store overall participant data
    columns = ['participant_id', 'noresp_perc', 'avg_rotwait']
    participants_df = pd.DataFrame(columns=columns)


# Iterate through each participant
for subj in participant_ids:

    ############## 1a. Load behavioral data file (_beh.tsv) ##############
    
    subj_id = 'sub-' + str(subj) # participant ID (in BIDS format)
    tsv_fname = f'{subj_id}_task-{exp_name}_{datatype_name}.tsv'

    # Merge information into complete datapath
    behdata_dir = os.path.join(wd, subj_id, datatype_name, tsv_fname)

    print(f"------ Preprocessing {subj_id} behavioral data. ------")

    # Read TSV file into a dataframe
    IBtask_behres = pd.read_csv(behdata_dir, sep='\t', header=0)

    # Check if the BIDS directory for storing beh preproc data exists, if not create one
    beh_preproc_dir = os.path.join(wd, 'derivatives', beh_preproc_folder, subj_id, datatype_name)
    if not os.path.exists(beh_preproc_dir):
        os.makedirs(beh_preproc_dir)


    ############## 1b. Initialize markdown file for individual summary of beh preprocessing ##############

    # Create a markdown file for storing summary of participant beh preprocessing
    md_fname =  f'{subj_id}_task-{exp_name}_beh-preproc-summary.md'
    md_dir = os.path.join(beh_preproc_dir, md_fname)
    md_summary = open(md_dir, 'w')

    # Initiate title and description of markdown file
    md_summary.write(f"# Summary of Behavioral Data Preprocessing from IBTask - {subj_id}\n\n")
    md_summary.write(f"This document contains a summary of the behavioral data preprocessing from the Intentional Binding task related to {subj_id}.\n\n")


    ############## 1c. Format NoResponse trials with NaNs & calculate percentage ##############

    # Find rows where "act_time" column has a value of 999
    noresp_rows = IBtask_behres[IBtask_behres['act_time'] == 999].index

    # Replace values in specified columns with NaNs
    noresp_col2replace = ['angle_act_report', 'angle_act_real', 
                          'tone_time', 'angle_tone_report', 'angle_tone_real']
    IBtask_behres.loc[noresp_rows, noresp_col2replace] = np.nan

    # Filter the rows where act_time == 999 (no keypress within 3 clock rotations)
    noresp_trials = IBtask_behres[IBtask_behres['act_time'] == 999]

    # Calculate N and % of trials with no response across BasA, OpA, and OpT conditions
    noresp_count = noresp_trials[noresp_trials['condition'].isin(['BasA', 'OpA', 'OpT'])].shape[0]
    noresp_perc = (noresp_count / 180) * 100

    # Save the summary of NoResponse trials in the markdown file
    md_summary.write(f"## NoResponse trials\n")
    md_summary.write(f"Overall, {subj_id} did not initiate any keypress in {noresp_count} ({noresp_perc:.2f}%) trials out of 180 across all conditions.\n")

    for cond in ['BasA', 'OpA', 'OpT']:
        noresp_count_cond = noresp_trials[noresp_trials['condition'].isin([cond])].shape[0]
        noresp_perc_cond = (noresp_count_cond / 60) * 100
        md_summary.write(f"{cond}: {noresp_count_cond} ({noresp_perc_cond:.2f}%) NoResp trials out of 60.\n")
    

    #%% 2a. ANGLE CONVERSION & CORRECTION: ACTION JUDGMENT TRIALS (BasA, OpA)

    ############## Reported action angles [angle_act_report]  ##############

    # Convert the reported action angles from radians to degrees
    # (clockwise, origin at vertical "0" tick; 90 is subtracted to correct for circle origin)
    angle_act_report_deg = np.degrees(IBtask_behres['angle_act_report']) - 90    # transform from rad to deg
    angle_act_report_deg[angle_act_report_deg > 0] -= 360       # revert to account for clockwise rotation
    angle_act_report_tick = -angle_act_report_deg / 6           # transform to ticks (each tick = 6 deg)

    # Append the transformed reported action angles
    IBtask_behres['angle_act_report_deg'] = -angle_act_report_deg
    IBtask_behres['angle_act_report_tick'] = angle_act_report_tick


    ############## Real action angles [angle_act_real]  ##############

    # Convert the real action angles from radians to degrees
    # (clockwise, origin at vertical "0" tick; 90 is subtracted to correct for circle origin)
    angle_act_real_deg = np.degrees(IBtask_behres['angle_act_real']) - 90    # transform from rad to deg 
    angle_act_real_deg[angle_act_real_deg > 0] -= 360       # revert to account for clockwise rotation
    angle_act_real_tick = -angle_act_real_deg / 6           # ransform to ticks (each tick = 6 deg)

    # Append the transformed real action angles
    IBtask_behres['angle_act_real_deg'] = -angle_act_real_deg
    IBtask_behres['angle_act_real_tick'] = angle_act_real_tick

    # Define function to correct for multiple clock rotations:
    # check if a number is > 360 and then subtract the highest multiple of 360 from it
    def subtract_mult360(num):
        if num > 360:
            multiples = num // 360
            adj_num = num - (multiples * 360)
        else:
            adj_num = num
        return adj_num

    # Correct the real action angle in degrees for multiple clock rotations
    angle_act_real_deg_corr = []
    for i in range(len(angle_act_real_deg)): 
        angle_act_real_deg_corr.append(subtract_mult360(-angle_act_real_deg[i])) # subtract multiples of 360

    # Correct the real action angle in clock ticks for multiple clock rotations
    angle_act_real_tick_corr = []
    for i in range(len(angle_act_real_tick)): 
        angle_act_real_tick_corr.append(angle_act_real_deg_corr[i]/6) # each tick equals 6 degrees

    # Transform into Series object
    angle_act_real_deg_corr = pd.Series(angle_act_real_deg_corr)
    angle_act_real_tick_corr = pd.Series(angle_act_real_tick_corr)

    # Append the real BasA angles corrected for multiple clock rotations
    IBtask_behres['angle_act_real_deg_corr'] = angle_act_real_deg_corr 
    IBtask_behres['angle_act_real_tick_corr'] = angle_act_real_tick_corr


    #%% 1b. ANGLE CONVERSION & CORRECTION: TONE JUDGMENT TRIALS (BasT, OpT)

    ############## Reported tone angles [angle_tone_report]  ##############

    # Convert the reported tone angles from radians to degrees
    # (clockwise, origin at vertical "0" tick; 90 is subtracted to correct for circle origin)
    angle_tone_report_deg = np.degrees(IBtask_behres['angle_tone_report']) - 90    # transform from rad to deg
    angle_tone_report_deg[angle_tone_report_deg > 0] -= 360       # revert to account for clockwise rotation
    angle_tone_report_tick = -angle_tone_report_deg / 6           # transform to ticks (each tick = 6 deg)

    # Append the transformed reported tone angles
    IBtask_behres['angle_tone_report_deg'] = -angle_tone_report_deg
    IBtask_behres['angle_tone_report_tick'] = angle_tone_report_tick


    ############## Real tone angles [angle_tone_real]  ##############

    # Convert the real tone angles from radians to degrees
    # (clockwise, origin at vertical "0" tick; 90 is subtracted to correct for circle origin)
    angle_tone_real_deg = np.degrees(IBtask_behres['angle_tone_real']) - 90    # transform from rad to deg 
    angle_tone_real_deg[angle_tone_real_deg > 0] -= 360       # revert to account for clockwise rotation
    angle_tone_real_tick = -angle_tone_real_deg / 6           # ransform to ticks (each tick = 6 deg)

    # Append the transformed real tone angles
    IBtask_behres['angle_tone_real_deg'] = -angle_tone_real_deg
    IBtask_behres['angle_tone_real_tick'] = angle_tone_real_tick

    # Correct the real tone angle in degrees for multiple clock rotations
    angle_tone_real_deg_corr = []
    for i in range(len(angle_tone_real_deg)): 
        angle_tone_real_deg_corr.append(subtract_mult360(-angle_tone_real_deg[i])) # subtract multiples of 360

    # Correct the real tone angle in clock ticks for multiple clock rotations
    angle_tone_real_tick_corr = []
    for i in range(len(angle_tone_real_tick)): 
        angle_tone_real_tick_corr.append(angle_tone_real_deg_corr[i]/6) # each tick equals 6 degrees

    # Transform into Series object
    angle_tone_real_deg_corr = pd.Series(angle_tone_real_deg_corr)
    angle_tone_real_tick_corr = pd.Series(angle_tone_real_tick_corr)

    # Append the real tone angles corrected for multiple clock rotations
    IBtask_behres['angle_tone_real_deg_corr'] = angle_tone_real_deg_corr 
    IBtask_behres['angle_tone_real_tick_corr'] = angle_tone_real_tick_corr


    #%% 1c. ANGLE CONVERSION & CORRECTION: START & FINAL ANGLES (all conditions)

    ############## Starting angles [start_angle]  ##############

    # Convert the starting angles (trial onset) from radians to degrees
    # (clockwise, origin at vertical "0" tick; 90 is subtracted to correct for circle origin)
    start_angle_deg = np.degrees(IBtask_behres['start_angle']) - 90    # transform from rad to deg
    start_angle_deg[start_angle_deg > 0] -= 360       # revert to account for clockwise rotation
    start_angle_tick = -start_angle_deg / 6           # transform to ticks (each tick = 6 deg)

    # Append the transformed starting angles
    IBtask_behres['start_angle_deg'] = -start_angle_deg
    IBtask_behres['start_angle_tick'] = start_angle_tick


    ############## Final angles [final_angle]  ##############

    # Convert the final angles (trial offset) from radians to degrees
    # (clockwise, origin at vertical "0" tick; 90 is subtracted to correct for circle origin)
    final_angle_deg = np.degrees(IBtask_behres['final_angle']) - 90     # transform from rad to degrees and subtract 90 
    final_angle_deg[final_angle_deg > 0] -= 360         # revert to account for clockwise rotation
    final_angle_tick = -final_angle_deg / 6             # each tick equals 6 degrees

    # Append the transformed final angles
    IBtask_behres['final_angle_deg'] = -final_angle_deg
    IBtask_behres['final_angle_tick'] = final_angle_tick

    # Correct the final angle in degrees for multiple clock rotations
    final_angle_deg_corr = []
    for i in range(len(final_angle_deg)): 
        final_angle_deg_corr.append(subtract_mult360(-final_angle_deg[i])) # subtract multiples of 360

    # Correct the final angle in clock ticks for multiple clock rotations
    final_angle_tick_corr = []
    for i in range(len(final_angle_tick)): 
        final_angle_tick_corr.append(final_angle_deg_corr[i]/6) # each tick equals 6 degrees

    # Transform into Series object
    final_angle_deg_corr = pd.Series(final_angle_deg_corr)
    final_angle_tick_corr = pd.Series(final_angle_tick_corr)

    # Append the final angles corrected for multiple clock rotations
    IBtask_behres['final_angle_deg_corr'] = final_angle_deg_corr
    IBtask_behres['final_angle_tick_corr'] = final_angle_tick_corr


    #%% 3. REAL VS. REPORT ANGLE DIFFERENCES

    ############## 3a. Action trials: real vs. report angle difference (in ticks)  ##############

    # Filter rows based on the condition column: action judgment trials only
    IBtask_behres_actonly = IBtask_behres[IBtask_behres['condition'].isin(['BasA', 'OpA'])]

    # Initialize lists with NaN values for real vs. reported action angles difference (ticks)
    real2report_act_ticks = [np.nan] * len(IBtask_behres)
    real2report_act_ticks_corr = [np.nan] * len(IBtask_behres)

    # Iterate over rows of filtered IBtask_behres_actonly df
    for index, row in IBtask_behres_actonly.iterrows():
        angle_act_report_tick_col = row['angle_act_report_tick']
        angle_act_real_tick_corr_col = row['angle_act_real_tick_corr']

        # Calculate overall distance (in ticks) of real vs. reported action angles (BasA & OpA)
        # Rows of conditions with no action judgment contain NaN value
        if angle_act_report_tick_col < angle_act_real_tick_corr_col:
            real2report_act_ticks[index] = angle_act_report_tick_col + 60 - angle_act_real_tick_corr_col
        elif angle_act_report_tick_col >= angle_act_real_tick_corr_col:
            real2report_act_ticks[index] = angle_act_report_tick_col - angle_act_real_tick_corr_col

        # Correct for distances that span more than half circle
        if real2report_act_ticks[index] > 30:
            real2report_act_ticks_corr[index] = real2report_act_ticks[index] - 60
        elif real2report_act_ticks[index] <= 30:
            real2report_act_ticks_corr[index] = real2report_act_ticks[index]


    ############## 3a. Action trials: real vs. report angle difference (in degrees)  ##############

    # Initialize lists with NaN values for real vs. reported action angles difference (deg)
    real2report_act_deg = [np.nan] * len(IBtask_behres)
    real2report_act_deg_corr = [np.nan] * len(IBtask_behres)

    # Iterate over rows of filtered IBtask_behres_actonly df
    for index, row in IBtask_behres_actonly.iterrows():
        angle_act_report_deg_col = row['angle_act_report_deg']
        angle_act_real_deg_corr_col = row['angle_act_real_deg_corr']

        # Calculate overall distance (in ticks) of real vs. reported action angles (BasA & OpA)
        # Rows of conditions with no action judgment contain NaN value
        if angle_act_report_deg_col < angle_act_real_deg_corr_col:
            real2report_act_deg[index] = angle_act_report_deg_col + 360 - angle_act_real_deg_corr_col
        elif angle_act_report_deg_col >= angle_act_real_deg_corr_col:
            real2report_act_deg[index] = angle_act_report_deg_col - angle_act_real_deg_corr_col

        # Correct for distances that span more than half circle
        if real2report_act_deg[index] > 180:
            real2report_act_deg_corr[index] = real2report_act_deg[index] - 360
        elif real2report_act_deg[index] <= 180:
            real2report_act_deg_corr[index] = real2report_act_deg[index]


    # Append the differences between real and reported clock positions
    IBtask_behres['real_report_diff_act_tick'] =  real2report_act_ticks_corr
    IBtask_behres['real_report_diff_act_deg'] =  real2report_act_deg_corr


    ############## 3b. Tone trials: real vs. report angle difference (in ticks)  ##############

    # Filter rows based on the condition column: tone judgment trials only
    IBtask_behres_toneonly = IBtask_behres[IBtask_behres['condition'].isin(['BasT', 'OpT'])]

    # Initialize lists with NaN values for real vs. reported tone angles difference (ticks)
    real2report_tone_ticks = [np.nan] * len(IBtask_behres)
    real2report_tone_ticks_corr = [np.nan] * len(IBtask_behres)

    # Iterate over rows of filtered IBtask_behres_toneonly df
    for index, row in IBtask_behres_toneonly.iterrows():
        angle_tone_report_tick_col = row['angle_tone_report_tick']
        angle_tone_real_tick_corr_col = row['angle_tone_real_tick_corr']

        # Calculate overall distance (in ticks) of real vs. reported tone angles (BasA & OpA)
        # Rows of conditions with no tone judgment contain NaN value
        if angle_tone_report_tick_col < angle_tone_real_tick_corr_col:
            real2report_tone_ticks[index] = angle_tone_report_tick_col + 60 - angle_tone_real_tick_corr_col
        elif angle_tone_report_tick_col >= angle_tone_real_tick_corr_col:
            real2report_tone_ticks[index] = angle_tone_report_tick_col - angle_tone_real_tick_corr_col

        # Correct for distances that span more than half circle
        if real2report_tone_ticks[index] > 30:
            real2report_tone_ticks_corr[index] = real2report_tone_ticks[index] - 60
        elif real2report_tone_ticks[index] <= 30:
            real2report_tone_ticks_corr[index] = real2report_tone_ticks[index]


    ############## 3b. Tone trials: real vs. report angle difference (in degrees)  ##############

    # Initialize lists with NaN values for real vs. reported tone angles difference (deg)
    real2report_tone_deg = [np.nan] * len(IBtask_behres)
    real2report_tone_deg_corr = [np.nan] * len(IBtask_behres)

    # Iterate over rows of filtered IBtask_behres_toneonly df
    for index, row in IBtask_behres_toneonly.iterrows():
        angle_tone_report_deg_col = row['angle_tone_report_deg']
        angle_tone_real_deg_corr_col = row['angle_tone_real_deg_corr']

        # Calculate overall distance (in ticks) of real vs. reported tone angles (BasA & OpA)
        # Rows of conditions with no tone judgment contain NaN value
        if angle_tone_report_deg_col < angle_tone_real_deg_corr_col:
            real2report_tone_deg[index] = angle_tone_report_deg_col + 360 - angle_tone_real_deg_corr_col
        elif angle_tone_report_deg_col >= angle_tone_real_deg_corr_col:
            real2report_tone_deg[index] = angle_tone_report_deg_col - angle_tone_real_deg_corr_col

        # Correct for distances that span more than half circle
        if real2report_tone_deg[index] > 180:
            real2report_tone_deg_corr[index] = real2report_tone_deg[index] - 360
        elif real2report_tone_deg[index] <= 180:
            real2report_tone_deg_corr[index] = real2report_tone_deg[index]


    # Append the differences between real and reported clock positions
    IBtask_behres['real_report_diff_tone_tick'] =  real2report_tone_ticks_corr
    IBtask_behres['real_report_diff_tone_deg'] =  real2report_tone_deg_corr


    #%% 4. COMPUTE JUDGMENT ERROR (i.e., time difference in ms between real and reported angle)

    # Calculate ms per each degree of the clock rotation
    ms_per_degree = 2560/360

    ############## 4a. Action trials: Judgment Error (JE_act)  ##############

    # Filter rows based on the condition column: action judgment trials only
    IBtask_behres_actonly = IBtask_behres[IBtask_behres['condition'].isin(['BasA', 'OpA'])]
    IBtask_behres['JE_act'] = np.nan # initialize new column for JE in action trials

    # Convert real2report_act_deg distances from degrees to ms (i.e., JE_act)
    for index, row in IBtask_behres_actonly.iterrows():
        real_report_diff_act_deg_col = row['real_report_diff_act_deg']
        IBtask_behres.at[index, 'JE_act'] = real_report_diff_act_deg_col * ms_per_degree

    # Mean and sd of JE_act
    JE_act_mean = IBtask_behres['JE_act'].mean()
    JE_act_sd = IBtask_behres['JE_act'].std()
    JE_act_median = IBtask_behres['JE_act'].median(axis=0)

    # Distribution plot of JE for action trials
    JE_act_fig = sns.displot(IBtask_behres, x='JE_act', 
                             kde=True).set(title=f'Distribution plot of JE for action trials - {subj_id}')

    # Save the distribution plot of JE for action trials as PNG 
    JE_act_fig_fname = f'{subj_id}_task-{exp_name}_JEact-distribution.png'
    JE_act_fig_dir = os.path.join(beh_preproc_dir, JE_act_fig_fname)
    JE_act_fig.savefig(JE_act_fig_dir, format='png')

    # Write the plot into the markdown file
    md_summary.write(f"\n## Distribution Plot of JE for Action Trials \n")
    md_summary.write(f"![Distribution Plot JE Action](./{JE_act_fig_fname})\n\n")


    ############## 4b. Tone trials: Judgment Error (JE_tone)  ##############

    # Filter rows based on the condition column: tone judgment trials only
    IBtask_behres_toneonly = IBtask_behres[IBtask_behres['condition'].isin(['BasT', 'OpT'])]
    IBtask_behres['JE_tone'] = np.nan # initialize new column for JE in tone trials

    # Convert real2report_tone_deg distances from degrees to ms (i.e., JE_tone)
    for index, row in IBtask_behres_toneonly.iterrows():
        real_report_diff_tone_deg_col = row['real_report_diff_tone_deg']
        IBtask_behres.at[index, 'JE_tone'] = real_report_diff_tone_deg_col * ms_per_degree

    # Mean and sd of JE_tone
    JE_tone_mean = IBtask_behres['JE_tone'].mean()
    JE_tone_sd = IBtask_behres['JE_tone'].std()
    JE_tone_median = IBtask_behres['JE_tone'].median(axis=0)

    # Distribution plot of JE for tone trials
    JE_tone_fig = sns.displot(IBtask_behres, x='JE_tone', 
                              kde=True).set(title=f'Distribution plot of JE for tone trials - {subj_id}')
    
    # Save the distribution plot of JE for tone trials as PNG 
    JE_tone_fig_fname = f'{subj_id}_task-{exp_name}_JEtone-distribution.png'
    JE_tone_fig_dir = os.path.join(beh_preproc_dir, JE_tone_fig_fname)
    JE_tone_fig.savefig(JE_tone_fig_dir, format='png')

    # Write the plot into the markdown file
    md_summary.write(f"## Distribution Plot of JE for Tone Trials \n")
    md_summary.write(f"![Distribution Plot JE Tone](./{JE_tone_fig_fname})\n\n")


    #%% 5. COMPUTE NUMBER OF CLOCK ROTATIONS

    ############## Clock rotation number for action trials  ##############

    # Derive number of clock rotations at time of keypress (BasA, OpA & OpT conditions)
    clock_rot_act = (IBtask_behres['angle_act_real_deg'] - IBtask_behres['start_angle_deg']) / 360
    IBtask_behres['clock_rot_act'] = clock_rot_act

    clock_rot_act_mean = IBtask_behres['clock_rot_act'].mean() # mean of number of clock rotations of keypress
    clock_rot_act_time = clock_rot_act_mean * 2.560 # approx. mean waiting time of keypress in seconds

    # Write summary of clock rotation number of keypress into markdown file
    md_summary.write(f"## Number of Clock Rotations of Keypress \n")
    md_summary.write(f"On average, {subj_id} pressed the key at {clock_rot_act_mean:.2f} clock rotations (approx. wait time to keypress of {clock_rot_act_time:.2f} seconds).\n\n")

    ############## Clock rotation number for tone trials  ##############

    # Derive number of clock rotations at time of tone (BasT, OpA & OpT conditions)
    clock_rot_act = (IBtask_behres['angle_tone_real_deg'] - IBtask_behres['start_angle_deg']) / 360
    IBtask_behres['clock_rot_tone'] = clock_rot_act


    #%% 6. PLOT REAL VS. REPORTED CLOCK HAND POSITIONS (to check for systematic biases)

    # Define function to convert angles to Cartesian coordinates
    def angle_to_cartesian(angle):
        x = math.cos(angle)
        y = math.sin(angle)
        return x, y


    ############## Action trials: plots of real vs. reported angles ##############

    # Define conditions with keypress
    act_conds = ['BasA', 'OpA', 'OpT']

    # Create dictionaries to sample list of real vs. reported angles per condition
    angle_Areal_dict = {}
    angle_Areport_dict = {}

    for cond in act_conds:
        angle_Areal_dict[cond] = IBtask_behres.loc[IBtask_behres['condition'] == cond, 'angle_act_real_deg_corr'].tolist()
        angle_Areport_dict[cond] = IBtask_behres.loc[IBtask_behres['condition'] == cond, 'angle_act_report_deg'].tolist()
    
    # Create a figure and axes for each condition
    fig, axes = plt.subplots(1, len(act_conds), figsize=(3 * len(act_conds), 4))
    fig.suptitle(f'Distributions of real vs. reported clock hand positions of action time - {subj_id}', fontsize=14)

    for i, cond in enumerate(act_conds):
        ax = axes[i]

        # Plot lines for real_angle (blue)
        for angle in angle_Areal_dict[cond]:
            x, y = angle_to_cartesian(angle)
            color = 'blue'
            ax.plot([0, x], [0, y], color=color)

        # Plot lines for reported_angle (red)
        for angle in angle_Areport_dict[cond]:
            x, y = angle_to_cartesian(angle)
            color = 'red'
            ax.plot([0, x], [0, y], color=color)

        # Set axis limits and aspect ratio
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.set_aspect('equal')
        ax.set_axis_off() # Hide axes and ticks

        # Add a circle to represent the circumference
        circle = plt.Circle((0, 0), 1, fill=False)
        ax.add_artist(circle)

        # Add a legend
        ax.plot([], [], color='blue', label='Real clock hand position at action time')
        ax.plot([], [], color='red', label='Reported clock hand position at action time')
        ax.legend(loc='upper center', fontsize=5)
        ax.set_title(f'Condition: {cond}')

    plt.tight_layout() # adjust layout

    # Save the figure to a PNG file
    clockhand_act_fname = f'{subj_id}_task-{exp_name}_clockhand-act-circplot.png'
    clockhand_act_dir = os.path.join(beh_preproc_dir, clockhand_act_fname)
    plt.savefig(clockhand_act_dir, format='png')

    # Write the plot into the markdown file
    md_summary.write(f"## Clock Hand Position Distributions for Action Trials\n")
    md_summary.write(f"![Clock Hand Positions of Action](./{clockhand_act_fname})\n\n")


    ############## Tone trials: plots of real vs. reported angles ##############

    # Define conditions with tone
    tone_conds = ['BasT', 'OpA', 'OpT']

    # Create dictionaries to sample list of real vs. reported angles per condition
    angle_Treal_dict = {}
    angle_Treport_dict = {}

    for cond in tone_conds:
        angle_Treal_dict[cond] = IBtask_behres.loc[IBtask_behres['condition'] == cond, 
                                                'angle_tone_real_deg_corr'].tolist()
        angle_Treport_dict[cond] = IBtask_behres.loc[IBtask_behres['condition'] == cond, 
                                                    'angle_tone_report_deg'].tolist()

    # Create a figure and axes for each condition
    fig, axes = plt.subplots(1, len(tone_conds), figsize=(3 * len(tone_conds), 4))
    fig.suptitle(f'Distributions of real vs. reported clock hand positions of tone time - {subj_id}', fontsize=14)

    for i, cond in enumerate(tone_conds):
        ax = axes[i]

        # Plot lines for real_angle (blue)
        for angle in angle_Treal_dict[cond]:
            x, y = angle_to_cartesian(angle)
            color = 'blue'
            ax.plot([0, x], [0, y], color=color)

        # Plot lines for reported_angle (red)
        for angle in angle_Treport_dict[cond]:
            x, y = angle_to_cartesian(angle)
            color = 'red'
            ax.plot([0, x], [0, y], color=color)

        # Set axis limits and aspect ratio
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.set_aspect('equal')
        ax.set_axis_off() # Hide axes and ticks

        # Add a circle to represent the circumference
        circle = plt.Circle((0, 0), 1, fill=False)
        ax.add_artist(circle)

        # Add a legend
        ax.plot([], [], color='blue', label='Real clock hand position at tone time')
        ax.plot([], [], color='red', label='Reported clock hand position at tone time')
        ax.legend(loc='upper center', fontsize=5)
        ax.set_title(f'Condition: {cond}')

    plt.tight_layout()

    # Save the figure to a PNG file
    clockhand_tone_fname = f'{subj_id}_task-{exp_name}_clockhand-tone-circplot.png'
    clockhand_tone_dir = os.path.join(beh_preproc_dir, clockhand_tone_fname)
    plt.savefig(clockhand_tone_dir, format='png')

    # Write the plot into the markdown file
    md_summary.write(f"## Clock Hand Position Distributions for Tone Trials\n")
    md_summary.write(f"![Clock Hand Positions of Tone](./{clockhand_tone_fname})\n\n")


    #%% 7a. OUTLIERS REMOVAL - METHOD 1: +/- 3SD 

    # Enable  +/- 3SD outliers removal
    # By default set to False, as outlier removal at trial level was not preregistered
    enable_outlier_3sd = False

    if enable_outlier_3sd: 

        ############## Action trials: +/- 3SD outlier removal ##############

        # Create the 'JE_act_3sd' column with NaN values
        IBtask_behres['JE_act_3sd'] = np.nan

        # Initialize a counter for outliers
        outlier_count_3sd = 0

        # Remove JE outliers +/- 3 SD
        for i_trial in range(len(IBtask_behres['JE_act'])):
            i_value = IBtask_behres.loc[i_trial, 'JE_act']
            
            if i_value < (JE_act_mean - 3 * JE_act_sd) or i_value > (JE_act_mean + 3 * JE_act_sd):
                IBtask_behres.loc[i_trial, 'JE_act_3sd'] = np.nan
                outlier_count_3sd += 1 # Update outlier count
                
            else:
                IBtask_behres.loc[i_trial, 'JE_act_3sd'] = i_value
                
        # Print the count of outliers +/- 3SD
        print(f"{subj_id} - Number of +/- 3SD outliers detected for action trials: {outlier_count_3sd}")
                
        # Calculate mean and sd of judgement error (JE) after outlier removal
        JE_act_mean_3sd = IBtask_behres['JE_act_3sd'].mean()
        JE_act_sd_3sd = IBtask_behres['JE_act_3sd'].std()

        # Distribution plot of JE for action trials (without outliers)
        JE_act_3sd_fig = sns.displot(IBtask_behres, x='JE_act_3sd',
                                    kde=True).set(title=f'Distribution plot of JE for action trials (without +/- 3SD outliers) - {subj_id}')


        ############## Tone trials: +/- 3SD outlier removal ##############

        # Create the 'JE_tone_3sd' column with NaN values
        IBtask_behres['JE_tone_3sd'] = np.nan

        # Initialize a counter for outliers
        outlier_count_tone_3sd = 0

        # Remove JE outliers +/- 3 SD
        for i_trial in range(len(IBtask_behres['JE_tone'])):
            i_value = IBtask_behres.loc[i_trial, 'JE_tone']
            
            if i_value < (JE_tone_mean - 3 * JE_tone_sd) or i_value > (JE_tone_mean + 3 * JE_tone_sd):
                IBtask_behres.loc[i_trial, 'JE_tone_3sd'] = np.nan
                outlier_count_tone_3sd += 1 # Update outlier count
                
            else:
                IBtask_behres.loc[i_trial, 'JE_tone_3sd'] = i_value
                
        # Print the count of outliers +/- 3SD
        print(f"{subj_id} - Number of +/- 3SD outliers detected for tone trials: {outlier_count_tone_3sd}")
                
        # Calculate mean and sd of judgement error (JE) after outlier removal
        JE_tone_mean_3sd = IBtask_behres['JE_tone_3sd'].mean()
        JE_tone_sd_3sd = IBtask_behres['JE_tone_3sd'].std()

        # Distribution plot of JE for tone trials (without outliers)
        JE_tone_3sd_fig = sns.displot(IBtask_behres, x='JE_tone_3sd', 
                                    kde=True).set(title=f'Distribution plot of JE for tone trials (without +/- 3SD outliers) - {subj_id}')



    #%% 7b. OUTLIERS REMOVAL - METHOD 2: MEDIAN +/- MAD, NON-PARAMETRIC

    # Enable median +/- MAD outliers removal
    # By default set to False, as outlier removal at trial level was not preregistered
    enable_outlier_mad = False

    if enable_outlier_mad: 

        ############## Action trials: median +/- MAD outlier removal ##############

        # Filter rows based on the condition column: action trials only
        IBtask_behres_actonly = IBtask_behres[IBtask_behres['condition'].isin(['BasA', 'OpA'])]

        # Calculate the MAD of JE_act (old method)
        # JE_act_mad = abs(IBtask_behres_actonly['JE_act'] - JE_act_median).median() * 1.4826  # MAD scaling factor

        # Calculate MAD using statsmodel.robust and define outlier threshold (here 3.5x MAD)
        JE_act_mad = (IBtask_behres_actonly[['JE_act']].apply(robust.mad)).iloc[0]
        mad_act_threshold = 3.5 * JE_act_mad

        # Detect outliers based on median +/- MAD non-parametric method
        outliers_mad_act = abs(IBtask_behres_actonly['JE_act'] - JE_act_median) > mad_act_threshold

        # Create a new column "JE_act_clean_mad" and assign NaN to the outlier values
        IBtask_behres['JE_act_clean_mad'] = IBtask_behres['JE_act']
        orig_ind = IBtask_behres_actonly.index
        IBtask_behres.loc[orig_ind[outliers_mad_act], 'JE_act_clean_mad'] = np.nan

        # Print the count of outliers with the MAD outlier removal method
        print(f"{subj_id} - Number of MAD outliers detected for action trials: {outliers_mad_act.sum()}")

        # Calculate mean and sd of judgement error (JE) of action trials after MAD outlier removal
        JE_act_mean_mad = IBtask_behres['JE_act_clean_mad'].mean()
        JE_act_sd_mad = IBtask_behres['JE_act_clean_mad'].std()

        # Distribution plot of JE for action trials (after MAD outlier removal)
        JE_act_mad_fig = sns.displot(IBtask_behres, x='JE_act_clean_mad', 
                                    kde=True).set(title=f'Distribution plot of JE for action trials (without MAD outliers) - {subj_id}')


        ############## Tone trials: median +/- MAD outlier removal ##############

        # Filter rows based on the condition column: tone trials only
        IBtask_behres_toneonly = IBtask_behres[IBtask_behres['condition'].isin(['BasT', 'OpT'])]

        # Calculate the MAD of JE_tone (old method)
        # JE_tone_mad = abs(IBtask_behres_toneonly['JE_tone'] - JE_tone_median).median() * 1.4826  # MAD scaling factor

        # Calculate MAD using statsmodel.robust and define outlier threshold (here 3.5x MAD)
        JE_tone_mad = (IBtask_behres_toneonly[['JE_tone']].apply(robust.mad)).iloc[0]
        mad_tone_threshold = 3.5 * JE_tone_mad

        # Detect outliers based on median +/- MAD non-parametric method
        outliers_mad_tone = abs(IBtask_behres_toneonly['JE_tone'] - JE_tone_median) > mad_tone_threshold

        # Create a new column "JE_tone_clean_mad" and assign NaN to the outlier values
        IBtask_behres['JE_tone_clean_mad'] = IBtask_behres['JE_tone']
        orig_ind = IBtask_behres_toneonly.index
        IBtask_behres.loc[orig_ind[outliers_mad_tone], 'JE_tone_clean_mad'] = np.nan

        # Print the count of outliers with the MAD outlier removal method
        print(f"{subj_id} - Number of MAD outliers detected for tone trials: {outliers_mad_tone.sum()}")

        # Calculate mean and sd of judgement error (JE) of tone trials after MAD outlier removal
        JE_tone_mean_mad = IBtask_behres['JE_tone_clean_mad'].mean()
        JE_tone_sd_mad = IBtask_behres['JE_tone_clean_mad'].std()

        # Distribution plot of JE for tone trials (after MAD outlier removal)
        JE_tone_mad_fig = sns.displot(IBtask_behres, x='JE_tone_clean_mad', 
                                    kde=True).set(title=f'Distribution plot of JE for tone trials (without MAD outliers) - {subj_id}')


    #%% 8. MERGE TIMESTAMPS FROM TASK EVENTS

    conditions = ['BasA', 'OpA', 'BasT', 'OpT']
    
    ############## Load task events file ##############
    events_fname = f'{subj_id}_task-{exp_name}_events.tsv'
    events_dir = os.path.join(wd, subj_id, datatype_name, events_fname)

    IBtask_events = pd.read_csv(events_dir, sep='\t', header=0) # read into df

    # Iterate over each condition
    for cond in conditions: 

        # Filter IBtask_behres df based on the current condition
        filtered_behres = IBtask_behres[IBtask_behres['condition'] == cond]

        # Filter IBtask_events df based on trial onset & clock onset per current condition
        trialon = f'TrialOnset_{cond}' # trial_type name for trial onset
        clockon = f'ClockOnset_{cond}' # trial_type name for clock onset
        events_trialon = IBtask_events[IBtask_events['trial_type'] == trialon]
        events_clockon = IBtask_events[IBtask_events['trial_type'] == clockon]

        # Take corresponding onset values (in sec), derived from HW triggers, and append as new columns
        for index, row in filtered_behres.iterrows():
            row_trialon = events_trialon.iloc[index % len(events_trialon)]
            row_clockon = events_clockon.iloc[index % len(events_clockon)]
            IBtask_behres.at[index, 'trial_onset'] = row_trialon['onset']
            IBtask_behres.at[index, 'clock_onset'] = row_clockon['onset']

        # Take onset values (in sec), derived from HW triggers, for keypress onset & no resp trials for all conditions except 'BasT'
        if cond != 'BasT': # no keypress in BasT condition

            keypress = f'Keypress_{cond}'  # trial_type name for keypress
            noresp = f'NoResp_{cond}'  # trial_type name for no response trials
            events_keypress = IBtask_events[IBtask_events['trial_type'].isin([keypress, noresp])]
            events_keypress = events_keypress.sort_values(by='onset').reset_index(drop=True) # sort by onset time

            keypress_index = 0 # iterator for events_keypress
            for index, row in filtered_behres.iterrows():
                if keypress_index < len(events_keypress):
                    row_keypress = events_keypress.iloc[keypress_index]
                    IBtask_behres.at[index, 'keypress_onset'] = row_keypress['onset'] # append the keypress onset for the trial row
                    keypress_index += 1
                else:
                    IBtask_behres.at[index, 'keypress_onset'] = np.nan  # end of keypress onset data

        # Take onset values (in sec), derived from HW triggers, for tone onset for all conditions except 'BasA'
        if cond != 'BasA':  # no tone in BasA condition

            toneon = f'Tone_{cond}'  # trial_type name for tone onset
            events_toneon = IBtask_events[IBtask_events['trial_type'] == toneon]
            events_toneon = events_toneon.sort_values(by='onset').reset_index(drop=True) # sort by onset time

            toneon_index = 0  # iterator for events_toneon

            for index, row in filtered_behres.iterrows():
                keypress_onset = IBtask_behres.at[index, 'keypress_onset'] # get corresponding keypress onset time

                if cond in ['OpA', 'OpT']: # check if condition has keypress-tone pairing (OpA, OpT)
                    if not pd.isna(keypress_onset): # check for valid keypress events

                        # search for tone event within 1s of keypress_onset (liberal interval)
                        found_match = False
                        while toneon_index < len(events_toneon):
                            row_toneon = events_toneon.iloc[toneon_index]
                            tone_onset = row_toneon['onset']
                            
                            # If tone_onset is <= 1s of keypress_onset, assign it
                            if abs(tone_onset - keypress_onset) <= 1.0:
                                IBtask_behres.at[index, 'tone_onset'] = tone_onset
                                found_match = True
                                toneon_index += 1  # move to next tone event
                                break
                            elif tone_onset > keypress_onset + 1.0: # if tone_onset is > 1s after keypress_onset, stop search
                                break
                            else:
                                toneon_index += 1  # check next tone event

                        if not found_match:  # if no match is found between keypress and tone onsets, assign NaN
                            IBtask_behres.at[index, 'tone_onset'] = np.nan
                    else:
                        IBtask_behres.at[index, 'tone_onset'] = np.nan # if no valid keypress, assign NaN for tone_onset
                else:
                    # For other condition (BasT), assign next tone_onset
                    if toneon_index < len(events_toneon):
                        row_toneon = events_toneon.iloc[toneon_index]
                        tone_onset = row_toneon['onset']
                        IBtask_behres.at[index, 'tone_onset'] = tone_onset
                        toneon_index += 1 

    # Replace keypress & tone onset timestamps of NoResp trials with nan
    noresp_rows = IBtask_behres[IBtask_behres['act_time'] == 999].index
    IBtask_behres.loc[noresp_rows, ['keypress_onset', 'tone_onset']] = np.nan


    #%% 9. SAVE PROCESSED BEHAVIORAL RESULTS TSV FILE

    # Save TSV file with IBtask preprocessed behavioral results (_beh_preproc.tsv)
    beh_preproc_fname = f'{subj_id}_task-{exp_name}_beh-preproc.tsv' 
    beh_preproc_fpath = os.path.join(beh_preproc_dir, beh_preproc_fname) # directory in derivatives folder
    IBtask_behres.to_csv(beh_preproc_fpath, sep='\t', na_rep="n/a")


    #%% 10. INTENTIONAL BINDING MEASURES SUMMARY
    
    # Specify whether to use the column with or without outlier removal
    IBtask_outlier_remove = False

    ############## 10a. Action binding ##############
    
    # Define the column to use based on the condition
    JE_act_column = 'JE_act_clean_mad' if IBtask_outlier_remove else 'JE_act'

    # Calculate mJE for BasA and OpA conditions separately
    mJE_act_BasA = IBtask_behres[IBtask_behres['condition'] == 'BasA'][JE_act_column].mean()
    mJE_act_OpA = IBtask_behres[IBtask_behres['condition'] == 'OpA'][JE_act_column].mean()

    # Calculate SD of JE for BasA and OpA conditions separately
    mJE_act_BasA_sd = IBtask_behres[IBtask_behres['condition'] == 'BasA'][JE_act_column].std()
    mJE_act_OpA_sd = IBtask_behres[IBtask_behres['condition'] == 'OpA'][JE_act_column].std()

    # Calculate mean and SD of action binding
    act_binding_mean = mJE_act_OpA - mJE_act_BasA
    act_binding_sd = mJE_act_OpA_sd - mJE_act_BasA_sd

    # Write summary of action binding into markdown file
    md_summary.write(f"# Action Binding Summary\n")
    md_summary.write(f"mJE (SD) of trials in BasA condition: {mJE_act_BasA:.2f} ms ({mJE_act_BasA_sd:.2f} ms). \n")
    md_summary.write(f"mJE (SD) of trials in OpA condition: {mJE_act_OpA:.2f} ms ({mJE_act_OpA_sd:.2f} ms). \n")
    md_summary.write(f"Action binding mean (SD): {act_binding_mean:.2f} ms ({act_binding_sd:.2f} ms). \n\n")


    ############## 10b. Tone binding ##############

    # Define the column to use based on the condition
    JE_tone_column = 'JE_tone_clean_mad' if IBtask_outlier_remove else 'JE_tone'

    # Calculate mJE for BasT and OpT conditions separately
    mJE_tone_BasT = IBtask_behres[IBtask_behres['condition'] == 'BasT'][JE_tone_column].mean()
    mJE_tone_OpT = IBtask_behres[IBtask_behres['condition'] == 'OpT'][JE_tone_column].mean()
    
    # Calculate SD of JE for BasT and OpT conditions separately
    mJE_tone_BasT_sd = IBtask_behres[IBtask_behres['condition'] == 'BasT'][JE_tone_column].std()
    mJE_tone_OpT_sd = IBtask_behres[IBtask_behres['condition'] == 'OpT'][JE_tone_column].std()

    # Calculate mean and SD of tone binding
    tone_binding_mean = mJE_tone_OpT - mJE_tone_BasT
    tone_binding_sd = mJE_tone_OpT_sd - mJE_tone_BasT_sd

    # Write summary of tone binding into markdown file
    md_summary.write(f"# Tone Binding Summary\n")
    md_summary.write(f"mJE (SD) of trials in BasT condition: {mJE_tone_BasT:.2f} ms ({mJE_tone_BasT_sd:.2f} ms). \n")
    md_summary.write(f"mJE (SD) of trials in OpT condition: {mJE_tone_OpT:.2f} ms ({mJE_tone_OpT_sd:.2f} ms). \n")
    md_summary.write(f"Tone binding mean (SD): {tone_binding_mean:.2f} ms ({tone_binding_sd:.2f} ms). \n")

    ############## Save mardown file output ##############

    # Close the markdown file
    md_summary.close()

    ############## Save overall participants summary file ##############
    if overall_summary:

        # Append the results to the overall participants df
        participant_row = pd.DataFrame([{
            'participant_id': subj_id,
            'noresp_perc': round(noresp_perc,2),
            'avg_rotwait': round(clock_rot_act_mean,2)
        }])

        participants_df = pd.concat([participants_df, participant_row], ignore_index=True)
    
    
    print("------------------------------------------------------")
    print(f"Preprocessing {subj_id} behavioral data completed.")
    print("------------------------------------------------------")

#%% 11. SAVE PARTICIPANTS BEH PREPROCESS SUMMARY (Optional)

# Close overall participants summary TSV (if selected)
if overall_summary:
    participants_df.to_csv(fpath,  sep='\t', index=False)
