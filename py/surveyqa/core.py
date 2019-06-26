"""
Core functions for DESI survey quality assurance (QA)
"""

import sys, os, shutil
import numpy as np
import re
from os import walk
import bokeh
import urllib.request

import surveyqa.summary
import surveyqa.nightly
from pathlib import PurePath
import json

import multiprocessing as mp

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
    b_js = (path / 'bokeh-{version}.js'.format(version=version)).as_posix()
    bt_js = (path / 'bokeh_tables-{version}.js'.format(version=version)).as_posix()
    b_css = (path / 'bokeh-{version}.css'.format(version=version)).as_posix()
    bt_css = (path / 'bokeh_tables-{version}.css'.format(version=version)).as_posix()

    if os.path.isfile(b_js) and os.path.isfile(bt_js) and \
       os.path.isfile(b_css) and os.path.isfile(bt_js):
        print("Offline Bokeh files found")
    else:
        shutil.rmtree(path, True)
        os.makedirs(path, exist_ok=True)

        url_js = "https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.js".format(version=version)
        urllib.request.urlretrieve(url_js, b_js)

        url_tables_js = "https://cdn.pydata.org/bokeh/release/bokeh-tables-{version}.min.js".format(version=version)
        urllib.request.urlretrieve(url_tables_js, bt_js)

        url_css = "https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.css".format(version=version)
        urllib.request.urlretrieve(url_css, b_css)

        url_tables_css = "https://cdn.pydata.org/bokeh/release/bokeh-tables-{version}.min.css".format(version=version)
        urllib.request.urlretrieve(url_tables_css, bt_css)

        print("Downloaded offline Bokeh files")

def write_night_linkage(outdir, nights, subset):
    '''
    Generates linking.js, which helps in linking all the nightly htmls together

    Args:
        outdir : directory to write linking.js and to check for previous html files
        nights : list of nights (strings) to link together
        subset : if True : nights is a subset, and we need to include all existing html files in outdir
                 if False : nights is not a subset, and we do not need to include existing html files in outdir

    Writes outdir/linking.js, which defines a javascript function
    `get_linking_json_dict` that returns a dictionary defining the first and
    last nights, and the previous/next nights for each night.
    '''
    f = []
    f += nights
    if subset:
        f_existing = []
        for (dirpath, dirnames, filenames) in walk(outdir):
            f.extend(filenames)
            break
        regex = re.compile("night-[0-9]+.html")
        f_existing = [filename for filename in f if regex.match(filename)]
        f_existing = [i[6:14] for i in f_existing]
        f += f_existing
        f = list(dict.fromkeys(f))
        f.sort()
    file_js = dict()
    file_js["first"] = "night-"+f[0]+".html"
    file_js["last"] = "night-"+f[len(f)-1]+".html"

    for i in np.arange(len(f)):
        inner_dict = dict()
        if (len(f) == 1):
            inner_dict["prev"] = "none"
            inner_dict["next"] = "none"
        elif i == 0:
            inner_dict["prev"] = "none"
            inner_dict["next"] = "night-"+f[i+1]+".html"
        elif i == len(f)-1:
            inner_dict["prev"] = "night-"+f[i-1]+".html"
            inner_dict["next"] = "none"
        else:
            inner_dict["prev"] = "night-"+f[i-1]+".html"
            inner_dict["next"] = "night-"+f[i+1]+".html"
        file_js["n"+f[i]] = inner_dict

    outfile = os.path.join(outdir, 'linking.js')
    with open(outfile, 'w') as fp:
        fp.write("get_linking_json_dict({})".format(json.dumps(file_js)))

    print('Wrote {}'.format(outfile))

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

    nights_sub = sorted(set(exposures_sub['NIGHT']))
    write_night_linkage(outdir, nights_sub, nights != None)

    pool = mp.Pool(mp.cpu_count())

    pool.starmap(surveyqa.nightly.makeplots, [(night, exposures_sub, tiles, outdir) for night in sorted(set(exposures_sub['NIGHT']))])

    pool.close()
    pool.join()
