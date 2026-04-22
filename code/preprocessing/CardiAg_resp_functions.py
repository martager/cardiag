import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import SpanSelector, Button
import os
from scipy.signal import argrelextrema
import json

class RespEditorGUI:
    """
    GUI for manual RESP signal correction of expiration peaks and inspiration troughs, 
    as well as annotation of bad segments. 
    
    Features:
    - Add expiration peaks or inspiration troughs at the local maxima or minima of a selected span
    - Delete expiration peaks or inspiration troughs via right-click on respective markers
    - Annotate bad segments (e.g., noisy signal) using a gray overlay 
    - Save all manually corrected expiration peaks, inspiration troughs and bad segments indices to a JSON file
    
    Parameters:
    -----------
    signal : np.ndarray
        The respiration signal as a 1D numpy array.
    exp_onsets : np.ndarray
        Indices of expiration onsets (peaks) in the signal.
    insp_onsets : np.ndarray
        Indices of inspiration onsets (troughs) in the signal.
    sfreq : float
        Sampling frequency of the signal (Hz).
    save_dir : str
        Directory path where output JSON file will be saved.
    bids_base_fname : str
        BIDS-compatible filename.
    figsize : tuple
        Size of the interactive plot as a tuple (width, height). Defaults to (12,8). 
    """
        
    def __init__(self, signal, exp_onsets, insp_onsets, sfreq, save_dir, bids_base_fname, figsize=(12,8)):
        """
        Initialize the RespEditorGUI with signal data and exp/insp onsets.
        Sets up the plot, event handlers, and buttons.
        """

        self.signal = signal
        self.exp_onsets = exp_onsets.copy()
        self.insp_onsets = insp_onsets.copy()
        self.sfreq = sfreq
        self.save_dir = save_dir
        self.bids_base_fname = bids_base_fname
        self.figsize = figsize

        # Initialize list of bad segments for saving output and plotting, each as [start_idx, end_idx]
        self.bad_segments = []
        self.bad_segment_patches = [] 

        # Current editing mode: 'expiration', 'inspiration', 'bad_segment', or None
        self.current_mode = None  

        # Create figure and axes for plotting
        self.fig, self.ax = plt.subplots(figsize=self.figsize)
        self.line, = self.ax.plot(np.arange(len(signal)) / sfreq, signal, color='black')    # plot raw RESP signal
        self.exp_marker = self.ax.plot(self.exp_onsets / sfreq, signal[self.exp_onsets], 
                                       'bo', label='Expiration Onsets', picker=5)[0]        # plot expiration onsets (peaks) as blue dots
        self.insp_marker = self.ax.plot(self.insp_onsets / sfreq, signal[self.insp_onsets], 
                                        'ro', label='Inspiration Onsets', picker=5)[0]      # plot inspiration onsets (troughs) as red dots

        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Z-scored Respiration Signal")
        self.ax.legend(loc='upper right')
        self.ax.grid(True)

        # SpanSelector to select windows on the plot, triggering self.onselect
        self.span = SpanSelector(self.ax, self.onselect, 'horizontal', useblit=True,
                                 props=dict(alpha=0.5, facecolor='tab:gray'))
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)

        self.make_buttons()
        plt.show()


    def onselect(self, xmin, xmax):
        """
        After selecting a horizontal window, behavior depends on current_mode:
          - 'expiration': add one expiration peak (local maximum) in selected window
          - 'inspiration': add one inspiration trough (local minimum) in selected window
          - 'bad_segment': annotate bad segment (if two segments are overlapping, they are merged)
        """
                
        idx_min = int(xmin * self.sfreq)
        idx_max = int(xmax * self.sfreq)
        selected = np.arange(idx_min, idx_max + 1)

        # Add expiration peaks based on local maximum within selected window
        if self.current_mode == 'expiration':
            segment = self.signal[selected]
            local_max_idx = argrelextrema(segment, np.greater)[0]
            if local_max_idx.size > 0:
                peak_val_idx = local_max_idx[np.argmax(segment[local_max_idx])]
                global_max_idx = selected[peak_val_idx]
                self.exp_onsets = np.sort(np.append(self.exp_onsets, global_max_idx))
                print("Added expiration peak at:", global_max_idx)

        # Add inspiration trough based on local minimum within selected window
        elif self.current_mode == 'inspiration':
            segment = self.signal[selected]
            local_min_idx = argrelextrema(segment, np.less)[0]
            if local_min_idx.size > 0:
                trough_val_idx = local_min_idx[np.argmin(segment[local_min_idx])]
                global_min_idx = selected[trough_val_idx]
                self.insp_onsets = np.sort(np.append(self.insp_onsets, global_min_idx))
                print("Added inspiration trough at:", global_min_idx)
        
        # Annotate window as 'bad segment' with gray overlay
        elif self.current_mode == 'bad_segment':
            if (idx_max - idx_min) < 5:     # ignore selections shorter than 5 samples (likely selected by accident)
                return
            new_segment = [idx_min, idx_max]
            self.merge_bad_segments(new_segment) # merge overlapping windows
            self.update_bad_segment_patches()
            print(f"Marked bad segment: {new_segment[0]} to {new_segment[1]}")

        self.update_plot()

    def merge_bad_segments(self, new_segment):
        """
        Merge a new bad segment into existing bad segments list, if overlapping or adjacent.
        """
        updated_segments = self.bad_segments + [new_segment]
        updated_segments.sort(key=lambda x: x[0])

        merged = []
        for seg in updated_segments:
            if not merged:
                merged.append(seg)
            else:
                # If segments overlap or touch, merge by extending the end
                if seg[0] <= merged[-1][1] + 1:
                    merged[-1][1] = max(merged[-1][1], seg[1])
                else:
                    merged.append(seg)
        self.bad_segments = merged

    
    def update_bad_segment_patches(self):
        """
        Draw or update semi-transparent grey patches indicating bad segment areas.
        """
        # Clear previous patches
        for patch in self.bad_segment_patches:
            patch.remove()
        self.bad_segment_patches = []

        for start, end in self.bad_segments:
            patch = self.ax.axvspan(start / self.sfreq, end / self.sfreq, color='gray', alpha=0.3)
            self.bad_segment_patches.append(patch)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


    def on_pick(self, event):
        """
        Event handler to delete expiration peaks or inspiration troughs when right-clicking on markers.
        Uses a small tolerance window of 5 samples to find nearest onset index.
        """
                
        # Only respond to right-clicks
        if event.mouseevent.button != 3:
            return

        clicked_artist = event.artist
        xdata = clicked_artist.get_xdata()
        ind = event.ind[0]
        clicked_time = xdata[ind]
        clicked_idx = int(round(clicked_time * self.sfreq))

        def find_nearest(array, value, tolerance_samples=5):
            diffs = np.abs(array - value)
            nearest_idx = np.argmin(diffs)
            if diffs[nearest_idx] <= tolerance_samples:
                return array[nearest_idx]
            return None

        # If right-click on expiration peak, delete it from exp_onsets list
        if clicked_artist == self.exp_marker:
            match = find_nearest(self.exp_onsets, clicked_idx)
            if match is not None:
                self.exp_onsets = self.exp_onsets[self.exp_onsets != match]
                print(f"Deleted expiration onset at sample {match}")

        # If right-click on inspiration trough, delete it from insp_onsets list
        elif clicked_artist == self.insp_marker:
            match = find_nearest(self.insp_onsets, clicked_idx)
            if match is not None:
                self.insp_onsets = self.insp_onsets[self.insp_onsets != match]
                print(f"Deleted inspiration onset at sample {match}")

        self.update_plot()


    def update_plot(self):
        """
        Refresh markers for expiration and inspiration onsets on the plot.
        """
                
        # Filter out-of-bounds indices (in case something weird happens)
        valid_exp = self.exp_onsets[self.exp_onsets < len(self.signal)]
        valid_insp = self.insp_onsets[self.insp_onsets < len(self.signal)]

        self.exp_marker.set_data(valid_exp / self.sfreq, self.signal[valid_exp])
        self.insp_marker.set_data(valid_insp / self.sfreq, self.signal[valid_insp])
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


    def make_buttons(self):
        """
        Create and position interactive buttons for GUI mode control and saving.
        Buttons:
          - Add Expiration Peaks: set mode to 'expiration'
          - Add Inspiration Troughs: set mode to 'inspiration'
          - Annotate Bad Segment: set mode to 'bad_segment'
          - Clear Mode: disable selection mode
          - Save All: save all onsets and bad segments to JSON
        """
        button_width = 0.15
        button_height = 0.05

        ax_add_exp = self.fig.add_axes([0.1, 0.9, button_width, button_height])
        self.btn_add_exp = Button(ax_add_exp, 'Add Expiration Peaks')
        self.btn_add_exp.on_clicked(lambda event: self.set_mode('expiration'))

        ax_add_insp = self.fig.add_axes([0.26, 0.9, button_width, button_height])
        self.btn_add_insp = Button(ax_add_insp, 'Add Inspiration Troughs')
        self.btn_add_insp.on_clicked(lambda event: self.set_mode('inspiration'))

        ax_mark_bad = self.fig.add_axes([0.42, 0.9, button_width, button_height])
        self.btn_mark_bad = Button(ax_mark_bad, 'Annotate Bad Segment')
        self.btn_mark_bad.on_clicked(lambda event: self.set_mode('bad_segment'))

        ax_clear = self.fig.add_axes([0.58, 0.9, button_width, button_height])
        self.btn_clear = Button(ax_clear, 'Clear Mode')
        self.btn_clear.on_clicked(lambda event: self.set_mode(None))

        ax_save = self.fig.add_axes([0.74, 0.9, button_width, button_height])
        self.btn_save = Button(ax_save, 'Save All')
        self.btn_save.on_clicked(self.save_data)


    def set_mode(self, mode):
        self.current_mode = mode
        if mode:
            print(f"Mode: Add {mode}")
        else:
            print("Selection disabled.")

    def save_data(self, event):
        """
        Save current expiration and inspiration onsets and bad segments to JSON file:
          - 'expiration_onsets': list of sample indices for expiration peaks
          - 'inspiration_onsets': list of sample indices for inspiration troughs
          - 'bad_segments': list of [start_idx, end_idx] bad segment pairs
        
        File is saved as 'resp-preproc_manualcorr.json' in save_dir.
        """
        
        save_path = os.path.join(self.save_dir, 
                                 f'{self.bids_base_fname}_resp-preproc_manualcorr.json')
        
        # Structure dict for storing exp/insp onsets and bad segments
        data_to_save = {
            "expiration_onsets": self.exp_onsets.tolist(),
            "inspiration_onsets": self.insp_onsets.tolist(), 
            "bad_segments": self.bad_segments  # list of [start, end] pairs
        }

        # Dump dict into JSON
        with open(save_path, 'w') as f:
            json.dump(data_to_save, f, indent=4)

        print(f"Saved expiration onsets, inspiration onsets and bad segments to: {save_path}")
