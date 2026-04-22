# CardiAg - Cardio-respiratory rhythms shape when we act and how we experience the outcomes of our actions

[![Python.pm](https://img.shields.io/badge/python-3.11-blue.svg?maxAge=259200)](#)
[![🚀 scilaunch](https://img.shields.io/badge/based%20on-🚀%20scilaunch-salmon "🚀")](https://shescher.github.io/scilaunch/)
[![Static Badge](https://img.shields.io/badge/based_on-%F0%9F%A7%A0_BBSIG%20v0.0.1-lightseagreen)](https://github.com/martager/bbsig)
[![version](https://img.shields.io/badge/version-0.1-yellow.svg?maxAge=259200)](#)
![Last update](https://img.shields.io/badge/last_update-Apr_22,_2026-green)


📖 **Publication:** *to be updated*

💽 **Data:** *to be updated*

📑 **Preprint:** *to be updated*


## Project description

In the CardiAg study, we investigated whether and how *Cardio*respiratory fluctuations influence voluntary action initiation and Sense of *Ag*ency (SoA), i.e., the feeling of controlling one’s actions and their outcomes, by combining electrocardiography (ECG) and respiratory (RESP) recordings during an intentional binding task (Haggard et al., 2002). 

## Project structure

If you want to reproduce the statistics (or the preprocessing steps) reported in the paper, we suggest that you follow these steps: 

### Get started
1. Download the data set from [Edmond – The Open Research Data Repository of the Max Planck Society](*to be updated*)  
    There are data-specific `README.md` and `dataset_description.json` files on Edmond which explain what the single folders and files contain, as well as which scripts were used to produced the derivative data. 
2. Clone this repository to a clean local directory. 
3. Replace the `data/` folder with the actual data which you downloaded in step 1 and unzipped. 
4. Create the dedicated virtual environment using the provided `cardiag_env.yml` (see below). 
5. Now you should be ready to go!

The complete folder structure should look like this: 

```
cardiag/
├── data/                                   # BIDS-formatted data 
|   ├── derivatives/                        # derivative data
|   |   ├── beh-preproc/                    # preprocessed behavioral data
|   |   ├── cardiac-phase-analysis/         # cardiac phase analysis data
|   |   ├── cardioresp-phase-analysis/      # cardioresp phase analysis data
|   |   ├── ecg-preproc/                    # preprocessed cardiac (ECG) data
|   |   ├── resp-phase-analysis/            # respiratory phase analysis data
|   |   └── resp-preproc/                   # preprocessed respiration data
|   ├── sub-<id>                            # subject-specific raw data
|   |   └── beh
|   |   |   └── ...
|   ├── dataset_description.json            # BIDS dataset description
|   ├── participants.tsv                    # participant characteristics
|   └── participants.json                   # participant characteristics (metadata)
├── code/                                   # scripts
|   ├── analysis/                           # main analysis scripts
|   └── preprocessing/                      # preprocessing scripts
├── results/                                # outputs
|   └── datavisualization/                  # data visualization (plots)
├── cardiag_env.yml                         # YAML file to create dedicated venv
├── LICENSE
└── README.md
```

### Create the dedicated virtual environment

To run the preprocessing and analysis scripts, it is best to have a dedicated environment setup that guarantees the correct functioning of the packages. The current virtual environment was largely based on the Brain-Body Analysis Special Interest Group (BBSIG) v0.0.1 setup ([read more here](https://martager.github.io/bbsig/setup-bbsig-env/)), with the addition of some extra packages. To create the dedicated virtual environment `cardiag_env`, based on Python 3.11, follow these steps: 

1. Download the `cardiag_env.yml` from the current repository
2. Using the terminal, cd into that directory: 
    ```
    cd /path/to/cardiag_env.yml
    ```
3. Type the following command: 
    ```
    conda env create -f cardiag_env.yml
    ```
4. Activate the newly created environment: 
    ```
    conda activate cardiag_env
    ```
5. When opening a Jupyter notebook, select `cardiag_env` as Python kernel

A detailed list of the packages included in the `cardiag_env` environment is included in the YAML file. 

### Shortcuts

Code relevant for the preprocessing of ECG, RESP and behavioral data can be found in [/code/preprocessing](/code/preprocessing). Most of the main statistical analysis, including main results and supplementary results, are performed in [/code/analysis](/code/preprocessing). We recommend proceeding to perform the main statistical analysis on the already preprocessed beh/ECG/RESP data stored in the respective folders under `/data/derivatives`. 


> **⚠️ Important**  
If you run into any problems, please do not hesitate to contact us (e.g., via email) or open an issue here. Much of the code is acceptably well documented and the Jupyter notebooks should (theoretically) run from top to bottom. If you want to work with the code, we are happy to support you in getting it to work.

## Preregistration

This project was preregistered on the Open Science Framework (OSF):

*Gerosa, M., Haggard, P., Villringer, A., & Gaebler, M. (2024, July 8). CardiAg - The influence of CARDIorespiratory phase locking on voluntary action initiation and sense of AGency. https://doi.org/10.17605/OSF.IO/Z7G9H*

## Contributors/Collaborators

- Marta Gerosa ([https://orcid.org/0009-0003-6184-8072](https://orcid.org/0009-0003-6184-8072))
- Patrick Haggard ([https://orcid.org/0000-0001-7798-793X](https://orcid.org/0000-0001-7798-793X))
- Arno Villringer ([https://orcid.org/0000-0003-2604-2404](https://orcid.org/0000-0003-2604-2404))
- Michael Gaebler ([https://orcid.org/0000-0002-4442-5778](https://orcid.org/0000-0002-4442-5778))

The preprocessing and analysis scripts used in this project were development versions of the published (or soon-to-be-published) pipelines of the Brain-Body Analysis Special Interest Group (BBSIG) v0.0.1. When using or adapting any BBSIG pipeline in your research work, please cite us in your publication as follows: 

*Gerosa M., Agrawal N., Ciston A.B., Fischer A., Fourcade A., Koushik A., Neubauer M., Patyczek A., Piejka A., Reinwarth E., Roellecke L., Shum Y.H., Verschooren S., Gaebler M. (2025). Brain-Body Analysis Special Interest Group (BBSIG) (Version 0.0.1) [Computer software]. https://doi.org/10.5281/zenodo.15212797*

## Contact

For questions regarding this project, please contact:

**Marta Gerosa**

Max Planck Institute for Human Cognitive and Brain Sciences, Dept. Neurology

gerosa [at] cbs.mpg.de 


***

*Based on the [🚀 scilaunch](https://shescher.github.io/scilaunch/ "🚀") project structure.*
