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

    D = exposures["MJD"] - 51544.5
    LST = (168.86072948111115 + 360.98564736628623 * D) % 360
    exposures["HOURANGLE"] = LST - exposures["RA"]

    def change_range(i):
        if i > 180:
            return i - 360
        if i < -180:
            return 360 + i
        return i

    exposures["HOURANGLE"] = [change_range(i) for i in exposures["HOURANGLE"]]

    exptiles = np.unique(exposures['TILEID'])
    print('Generating QA for {} exposures on {} tiles'.format(
        len(exposures), len(exptiles)))

    surveyqa.summary.makeplots(exposures, tiles, outdir)

    for night in sorted(set(exposures['NIGHT'])):
        surveyqa.nightly.makeplots(night, exposures, tiles, outdir)
