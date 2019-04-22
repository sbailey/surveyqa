"""
Core functions for DESI survey quality assurance (QA)
"""

import sys, os, shutil
import numpy as np
import bokeh
import urllib.request

import surveyqa.summary
import surveyqa.nightly
from pathlib import PurePath

def check_offline_files(dir):
    '''
    Checks if the Bokeh .js and .css files are present (so that the page works offline).
    If they are not downloaded, they will be fetched and downloaded.

    Args:
        dir : directory of where the offline_files folder should be located.
              If not present, an offline_files folder will be genreated.
    '''
    path=(PurePath(dir) / "offline_files")
    version = bokeh.__version__
    b_js = (path / 'bokeh{version}.js'.format(version=version)).as_posix()
    bt_js = (path / 'bokeh_tables{version}.js'.format(version=version)).as_posix()
    b_css = (path / 'bokeh{version}.css'.format(version=version)).as_posix()
    bt_css = (path / 'bokeh_tables{version}.css'.format(version=version)).as_posix()
    try:
        fh = open(b_js, 'r')
        fh = open(bt_js, 'r')
        fh = open(b_css, 'r')
        fh = open(bt_js, 'r')
        print("Offline Bokeh files found")
    except FileNotFoundError:
        shutil.rmtree(path, True)
        os.mkdir(path)

        url_js = "https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.js".format(version=version)
        urllib.request.urlretrieve(url_js, b_js)

        url_tables_js = "https://cdn.pydata.org/bokeh/release/bokeh-tables-{version}.min.js".format(version=version)
        urllib.request.urlretrieve(url_tables_js, bt_js)

        url_css = "https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.css".format(version=version)
        urllib.request.urlretrieve(url_css, b_css)

        url_tables_css = "https://cdn.pydata.org/bokeh/release/bokeh-tables-{version}.min.css".format(version=version)
        urllib.request.urlretrieve(url_tables_css, bt_css)

        print("Downloaded offline Bokeh files")

def makeplots(exposures, tiles, outdir):
    '''
    Generates summary plots for the DESI survey QA

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...
        outdir: directory to write the files

    Writes outdir/summary.html and outdir/night-*.html
    '''

    check_offline_files(outdir)

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
