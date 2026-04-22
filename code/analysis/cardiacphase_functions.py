import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
import seaborn as sns
import os


############## Plot individual ECG signal around task event ##############

def plot_individual_ecg_by_event(behpreproc_ecg_long, participant_id, wd, exp_name, datatype_name, 
                                 column_map, event_col, abbrev, event_label, sfreq, toff_method):
    
    # Extract column names for participant, condition, trial and block (optional)
    participant_col = column_map['participant']
    condition_col = column_map['condition']
    trial_col = column_map['trial']
    block_col = column_map.get('block', None)  # block number is optional

    # Extract T-offset delineation method
    if toff_method.lower() in ['neurokit', 'neurokit2', 'nk', 'dwt']:
        method = 'Nk2 DWT'
    elif toff_method.lower() in ['tra', 'trapezium']:
        method = 'TRA'
    elif toff_method.lower() in ['equal', 'equalize', 'equal_bins']:
        method = 'Equal'
    else:
        raise ValueError("Wrong method! T-offset delineation method should be either 'NeuroKit' or 'TRA'.")

    pref_subj_id = f'sub-{participant_id}' # selected participant ID

    # Load ECG data: if available, take cleaned ECG signal derived from BBSIG pre-processing
    # Otherwise, take raw ECG signal from rawdata folder 
    ecg_clean_fname = f'{pref_subj_id}_task-{exp_name}_ecg-cleaned.tsv.gz' # cleaned ECG file
    ecg_clean_dir = os.path.join(wd, 'derivatives', 'ecg-preproc', 
                                pref_subj_id, datatype_name, ecg_clean_fname)
    
    ecg_raw_fname = f'{pref_subj_id}_task-{exp_name}_physio.tsv.gz' # raw ECG file
    ecg_raw_dir = os.path.join(wd, pref_subj_id, datatype_name, ecg_raw_fname)

    # Load ECG data (prioritize cleaned, then raw)
    if os.path.exists(ecg_clean_dir):
        print(f'Loading cleaned ECG data: {ecg_clean_dir}')
        physio_df = pd.read_csv(ecg_clean_dir, compression='gzip', sep='\t')
        ecg_arr = physio_df['ecg_cleaned'].values
    elif os.path.exists(ecg_raw_dir):
        print(f'Cleaned ECG file not found, loading raw ECG data: {ecg_raw_dir}')
        ecg_df = pd.read_csv(ecg_raw_dir, compression='gzip', sep='\t')
        ecg_arr = ecg_df.iloc[:, 0].values  # Take first column
    else:
        print(f'Error: No ECG data found for {pref_subj_id}.')
        return
    
    # Get available trials
    participant_trials = behpreproc_ecg_long[behpreproc_ecg_long[participant_col] == participant_id]
    min_trial = participant_trials[trial_col].min()
    max_trial = participant_trials[trial_col].max()

    ######## UI components ########

    # UI: condition selector
    condition_selector = widgets.Dropdown(
        options=behpreproc_ecg_long[condition_col].unique(),
        description='Condition:',
        value=behpreproc_ecg_long[condition_col].unique()[0])

    # UI: trial selector
    trial_label = widgets.Label(value='Trial: 1')
    next_button = widgets.Button(description='Next Trial', icon='arrow-right')
    prev_button = widgets.Button(description='Previous Trial', icon='arrow-left')

    out = widgets.Output()
    
    trial_index = [min_trial] # initialize trials index from min trial

    # UI: block selector, if block column exists
    block_selector = None
    if block_col and block_col in behpreproc_ecg_long.columns:
        block_selector = widgets.ToggleButtons(
            options=sorted(behpreproc_ecg_long[block_col].unique()),
            description='Block:',
            value=sorted(behpreproc_ecg_long[block_col].unique())[0]
        )

    ######## Plot trial-based ECG signal: RR interval and sys/dia around task event  ########

    def plot_trial():

        condition = condition_selector.value # selected condition value
        trial_number = trial_index[0] # selected trial number
        block = block_selector.value if block_selector else None # selected block number (optional)

        # Filter for the specified participant, condition, trial and block (if applicable)
        search_conditions = ((behpreproc_ecg_long[participant_col] == participant_id) & 
                             (behpreproc_ecg_long[condition_col] == condition) & 
                             (behpreproc_ecg_long[trial_col] == trial_number))
        if block_col and block_col in behpreproc_ecg_long.columns:
            search_conditions &= (behpreproc_ecg_long[block_col] == block)

        row = behpreproc_ecg_long[search_conditions]

        # Check if row is empty
        if row.empty:
            trial_label.value = f"Trial: {trial_number} (No data)"
            return
        
        rr2plot = row.index[0]

        if pd.isna(behpreproc_ecg_long.at[rr2plot, event_col]):
            trial_label.value = f"Trial: {trial_number} (No response trial)"
            return

        # Define function to convert from timestamps into sample idx 
        def to_idx(col_name): 
            return int(behpreproc_ecg_long.at[rr2plot, col_name] * sfreq)
        
        # Convert general timestamps of relevant ECG features around task events to sample idx
        event2plot_idx = to_idx(event_col)                      # idx of task event (user-defined)
        rpeakpre2plot_idx = to_idx(f'Rpeak_pre_{abbrev}')       # idx of Rpeak before task event
        rpeakpost2plot_idx = to_idx(f'Rpeak_post_{abbrev}')     # idx of Rpeak after task event
        syson2plot_idx = to_idx(f'Soffset_{abbrev}')            # idx of systole onset (S-offset pre)
        diasoff2plot_idx = to_idx(f'Qonset_post_{abbrev}')      # idx of diastole offset (Q-onset post)

        # Convert timestamps of relevant T-offset and sys/dia segmentation based on selected method
        toff2plot_NK_idx = to_idx(f'Toffset_{abbrev}')             # idx of systole offset (T-offset) using NeuroKit2 DWT method
        diason2plot_NK_idx = to_idx(f'dia_onset_{abbrev}')         # idx of diastole onset (+50ms post-T-offset) using NeuroKit2 DWT method
        toff2plot_TRA_idx = to_idx(f'Toffset_TRA_{abbrev}')        # idx of systole offset (T-offset) using TRA approach 
        diason2plot_TRA_idx = to_idx(f'dia_onset_TRA_{abbrev}')    # idx of diastole onset (+50ms post-T-offset) using TRA approach 


        ######## Plot settings ########

        # Select min and max samples of ECG signal to plot
        minsample, maxsample = rpeakpre2plot_idx - 150, rpeakpost2plot_idx + 150
        ecg2plot = ecg_arr[minsample:maxsample]
        time = np.arange(minsample, maxsample) # convert into time

        # Adjust y-axis limits dynamically based on max and min amplitude of ECG
        ymin, ymax = np.min(ecg2plot) - 1, np.max(ecg2plot) + 0.5

        with out:
            out.clear_output(wait=True)
            plt.figure(figsize=(10, 6), dpi=300)

            # Draw shaded background for systole and diastole intervals
            if toff_method.lower() in ['neurokit', 'neurokit2', 'nk', 'dwt']:
                plt.axvspan(time[syson2plot_idx - minsample], time[toff2plot_NK_idx - minsample], color='#ff7f00', alpha=0.3)
                plt.axvspan(time[diason2plot_NK_idx - minsample], time[diasoff2plot_idx - minsample], color='#7AC5CD', alpha=0.3)
            elif toff_method.lower() in ['tra', 'trapezium']:
                plt.axvspan(time[syson2plot_idx - minsample], time[toff2plot_TRA_idx - minsample], color='#ff7f00', alpha=0.3)
                plt.axvspan(time[diason2plot_TRA_idx - minsample], time[diasoff2plot_idx - minsample], color='#7AC5CD', alpha=0.3)
            else:
                raise ValueError("Wrong method! T-offset delineation method should be either 'NeuroKit' or 'TRA'.")

            # Plot ECG signal
            plt.plot(time, ecg2plot, color='k', linewidth=2.5)

            # Add point for Toffset using the alternative approach (for comparison)
            if toff_method.lower() in ['neurokit', 'neurokit2', 'nk', 'dwt']:
                plt.plot(time[toff2plot_TRA_idx - minsample], ecg_arr[toff2plot_TRA_idx], 'rx', label='Trapezium Area (TRA)')
            elif toff_method.lower() in ['tra', 'trapezium']:
                plt.plot(time[toff2plot_NK_idx - minsample], ecg_arr[toff2plot_NK_idx], 'rx', label='NeuroKit2 DWT')
            else:
                raise ValueError("Wrong method! T-offset delineation method should be either 'NeuroKit' or 'TRA'.")

            # Add labels indicating R-peak pre and post 
            plt.text(rpeakpre2plot_idx, ymax - 0.25, 'R-peak pre', ha='center', color='black', fontsize='large')
            plt.text(rpeakpost2plot_idx, ymax - 0.25, 'R-peak post', ha='center', color='black', fontsize='large')
            
            # Add arrow and label indicating RR interval length
            rr_interval = behpreproc_ecg_long.at[rr2plot, f'RR_s_{abbrev}']
            rr_text = f'R-R interval ({rr_interval:.2f} s)' if not np.isnan(rr_interval) else 'R-R interval'
            midpoint = (rpeakpre2plot_idx + rpeakpost2plot_idx) / 2
            plt.annotate('', xy=(rpeakpre2plot_idx, ymin + 0.4), xytext=(rpeakpost2plot_idx, ymin + 0.4),
                         arrowprops=dict(arrowstyle='<->', color='black'))
            plt.text(midpoint, ymin + 0.45, rr_text, ha='center', color='black', fontsize='large')

            # Add line and label for onset of task event
            plt.axvline(x=event2plot_idx, ymin=0.2, ymax=0.8, color='black', linestyle=':', linewidth=2)
            plt.text(event2plot_idx, ymax - 0.5, event_label, ha='center', color='black', fontsize='large')

            # Add title specifying participant, condition, trial and block (if applicable) + chosen method for Toff delineation
            title = f'Subject: {pref_subj_id}, Condition: {condition}, Trial: {trial_number}'
            if block_col and block_selector:
                title += f', Block: {block}'
            title += f' - Toff method: {method}'
            plt.title(title, fontsize='large')

            plt.ylim(ymin, ymax)
            plt.ylabel('ECG (mV)', fontsize='large')
            plt.legend(loc='lower right', fontsize='x-small')
            plt.gca().axes.get_xaxis().set_visible(False)
            plt.gca().spines['bottom'].set_visible(False)
            sns.despine()
            plt.show()
        
        trial_label.value = f"Trial: {trial_number}"

    # UI: define function to proceed to next trial
    def next_trial(_):
        if trial_index[0] < max_trial:
            trial_index[0] += 1
            plot_trial()

    # UI: define function to go back to previous trial
    def prev_trial(_):
        if trial_index[0] > min_trial:
            trial_index[0] -= 1
            plot_trial()

    # Attach button actions
    next_button.on_click(next_trial)
    prev_button.on_click(prev_trial)

    # Observe block and condition changes
    def update_plot_on_change(_):
        trial_index[0] = 1  # reset to first trial on change
        plot_trial()
    
    block_selector.observe(update_plot_on_change, names='value')
    condition_selector.observe(update_plot_on_change, names='value')

    # Display UI
    controls = widgets.HBox([prev_button, trial_label, next_button])
    ui = widgets.VBox([block_selector, condition_selector, controls] if block_selector else [condition_selector, controls])
    display(ui, out)

    # Initial plot
    plot_trial()
