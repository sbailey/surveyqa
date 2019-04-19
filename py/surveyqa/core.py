"""
Core functions for DESI survey quality assurance (QA)
"""

import sys, os, shutil
import numpy as np
import bokeh
import urllib.request

import surveyqa.summary
import surveyqa.nightly

def check_offline_files():
    version = bokeh.__version__
    try:
        fh = open('../py/offline_files/bokeh{version}.js'.format(version=version), 'r')
        fh = open('../py/offline_files/bokeh_tables{version}.js'.format(version=version), 'r')
        fh = open('../py/offline_files/bokeh{version}.css'.format(version=version), 'r')
        fh = open('../py/offline_files/bokeh_tables{version}.css'.format(version=version), 'r')
    except FileNotFoundError:
        shutil.rmtree("../py/offline_files", True)
        os.mkdir("../py/offline_files")

        url_js = "https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.js".format(version=version)
        urllib.request.urlretrieve(url_js, '../py/offline_files/bokeh{version}.js'.format(version=version))

        url_tables_js = "https://cdn.pydata.org/bokeh/release/bokeh-tables-{version}.min.js".format(version=version)
        urllib.request.urlretrieve(url_tables_js, '../py/offline_files/bokeh_tables{version}.js'.format(version=version))

        url_css = "https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.css".format(version=version)
        urllib.request.urlretrieve(url_css, '../py/offline_files/bokeh{version}.css'.format(version=version))

        url_tables_css = "https://cdn.pydata.org/bokeh/release/bokeh-tables-{version}.min.css".format(version=version)
        urllib.request.urlretrieve(url_tables_css, '../py/offline_files/bokeh_tables{version}.css'.format(version=version))

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

    check_offline_files()

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
