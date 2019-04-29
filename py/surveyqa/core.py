"""
Core functions for DESI survey quality assurance (QA)
"""

import sys, os
import numpy as np

import surveyqa.summary
import surveyqa.nightly

def makeplots(exposures, tiles, outdir, show_summary = "all", nights = None):
    '''
    Generates summary plots for the DESI survey QA

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...
        outdir: directory to write the files
        show_summary:
            if = "no": does not make a summary page
            if = "subset": make summary page on subset provided (if no subset provided, make summary page on all nights)
            if = "all": make summary page on all nights
            else: raises a ValueError
        nights: list of nights (as integers or strings)

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

    exposures_sub = exposures
    if nights is not None:
        nights = [str(i) for i in nights]
        exposures_sub = exposures[[x in nights for x in exposures['NIGHT']]]

    exptiles = np.unique(exposures['TILEID'])
    print('Generating QA for {} exposures on {} tiles'.format(
        len(exposures), len(exptiles)))

    if show_summary=="subset":
        surveyqa.summary.makeplots(exposures_sub, tiles, outdir)
    elif show_summary=="all":
        surveyqa.summary.makeplots(exposures, tiles, outdir)
    elif show_summary!="no":
        raise ValueError('show_summary should be "all", "subset", or "no". The value of show_summary was: {}'.format(show_summary))

    for night in sorted(set(exposures_sub['NIGHT'])):
        surveyqa.nightly.makeplots(night, exposures_sub, tiles, outdir)
