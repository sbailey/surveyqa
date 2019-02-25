"""
Core functions for DESI survey quality assurance (QA)
"""

import sys, os
import numpy as np

import surveyqa.summary
import surveyqa.nightly

def makeplots(exposures, tiles, outdir):
    '''
    Generates summary plots for the DESI survey QA

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...
        outdir: directory to write the files

    Writes outdir/summary.html and outdir/night-*.html
    '''
    exptiles = np.unique(exposures['TILEID'])
    print('Generating QA for {} exposures on {} tiles'.format(
        len(exposures), len(exptiles)))
        
    surveyqa.summary.makeplots(exposures, tiles, outdir)

    for night in sorted(set(exposures['NIGHT'])):
        surveyqa.nightly.makeplots(night, exposures, tiles, outdir)