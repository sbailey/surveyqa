"""
Summary plots of DESI survey progress and QA
"""

import sys, os
import numpy as np

import jinja2
from bokeh.embed import components
import bokeh
import bokeh.plotting as bk
from bokeh.models import ColumnDataSource, LinearColorMapper, ColorBar, HoverTool
from bokeh.transform import transform
from astropy.time import Time, TimezoneInfo
from astropy.table import Table, join
from datetime import datetime, tzinfo
import astropy.units as u

def nights_first_observed(exposures, tiles):
    '''
    Generates a list of the first night on which each tile was observed (mainly for use in color coding the skyplot).
    Uses numpy.unique, numpy.array

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns...

    Returns two arrays:
        array of float values (meaning exact time of first exposure taken)
        array of integer values (the night, not the exact time)'''

    tiles_unique, indx = np.unique(exposures['TILEID'], return_index=True)
    nights = exposures['MJD'][indx]
    nights = nights[1:len(nights)]
    nights_int = np.array(nights.astype(int))

    return nights, nights_int

def get_skyplot(exposures, tiles, width=600, height=300):
    '''
    Generates sky plot of DESI survey tiles and progress. Colorcoded by night each tile was first
    observed, uses nights_first_observed function defined previously in this module to retrieve
    night each tile was first observed.

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...

    Options:
        width, height: plot width and height in pixels

    Returns bokeh Figure object
    '''
    observed = np.in1d(tiles['TILEID'], exposures['TILEID'])
    nights, nights_int = nights_first_observed(exposures, tiles)

    source = ColumnDataSource(data=dict(
    RA = tiles['RA'],
    DEC = tiles['DEC']))

    source_obs = ColumnDataSource(data=dict(
        RA_obs = tiles['RA'][observed],
        DEC_obs = tiles['DEC'][observed],
        MJD = nights_int
    ))

    color_mapper = LinearColorMapper(palette="Viridis256", low=nights_int.min(), high=nights_int.max())

    ##making figure
    fig = bk.figure(width=600, height=300)

    #unobserved tiles
    fig.circle('RA', 'DEC', source=source, color='gray', radius=0.25)

    #observed tiles
    fig.circle('RA_obs', 'DEC_obs', color=transform('MJD', color_mapper), size=3, alpha=0.85, source=source_obs)
    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12, location=(0,0), title='MJD')
    fig.add_layout(color_bar, 'right')

    fig.xaxis.axis_label = 'RA [degrees]'
    fig.yaxis.axis_label = 'Declination [degrees]'
    fig.title.text = 'Observed Tiles, Nightly Progress'

    return fig

def get_summarytable(exposures):
    '''
    Generates a summary table of key values for each night observed. Uses collections.Counter()

    Args:
        exposures: Table of exposures with columns...

    Returns a bokeh DataTable object.
    '''
    from bokeh.models.widgets.tables import DataTable, TableColumn
    from collections import Counter

    night = exposures['NIGHT']
    night_exps_total = np.array(Counter(night).values())

    #list of counts of each program for each night
    dct = []
    for n in list(Counter(exposures['NIGHT']).keys()):
        keep = exposures['NIGHT'] == n
        nights_selected = exposures[keep]
        program_freq = Counter(nights_selected['PROGRAM'])
        dct.append(program_freq)

    #get the values out of the dictionaries above (in a specified order so we can splice later)
    counts = []
    for d in dct:
        for key in ['BRIGHT', 'GRAY', 'DARK', 'CALIB']:
            counts.append(d[key])

    #lists of counts of each program for each night
    brights = np.array([counts[i] for i in np.arange(0,len(counts), 4)])
    grays = np.array([counts[i] for i in np.arange(1,len(counts), 4)])
    darks = np.array([counts[i] for i in np.arange(2,len(counts), 4)])
    calibs = np.array([counts[i] for i in np.arange(3,len(counts), 4)])

    source = ColumnDataSource(data=dict(
        nights = list(Counter(exposures['NIGHT']).keys()),
        totals = list(Counter(exposures['NIGHT']).values()),
        brights = brights,
        grays = grays,
        darks = darks,
        calibs = calibs
    ))

    columns = [
        TableColumn(field='nights', title='NIGHT'),
        TableColumn(field='totals', title='Total Exposures'),
        TableColumn(field='brights', title='Bright Exposures'),
        TableColumn(field='grays', title='Gray Exposures'),
        TableColumn(field='darks', title='Dark Exposures'),
        TableColumn(field='calibs', title='Calibrations'),
    ]

    summary_table = DataTable(source=source, columns=columns, sortable=True)

    return summary_table

def nights_last_observed(exposures):
    def last(arr):
        return arr[len(arr)-1]
    return exposures.group_by("TILEID").groups.aggregate(last)

def get_surveyprogress(exposures, tiles, width=300, height=300):
    '''
    Generates a plot of survey progress vs. time

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...

    Options:
        width, height: plot width and height in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]

    tne = join(nights_last_observed(exposures_nocalib["TILEID", "MJD"]), tiles, keys="TILEID", join_type='inner')
    tne.sort('MJD')

    tzone = TimezoneInfo(utc_offset = -7*u.hour)

    def bgd(string):
        tne_d = tne[tne["PROGRAM"] == string]
        x_d = np.array(tne_d['MJD'])
        y_d1 = np.array(tne_d['EXPOSEFAC'])
        s = 0
        y_d = np.array([])
        for i in y_d1:
            s += i
            y_d = np.append(y_d, s)
        y_d = y_d/np.sum(tiles[tiles["PROGRAM"] == string]["EXPOSEFAC"])
        t1 = Time(x_d, format='mjd', scale='utc')
        t = t1.to_datetime(timezone=tzone)
        return (t, y_d)

    hover = HoverTool(
            tooltips=[
                ("DATE", "@date"),
                ("TOTAL PERCENTAGE", "@y")
            ]
        )

    fig1 = bk.figure(plot_width=width, plot_height=height, title = "Progress(ExposeFac Weighted) vs Time", x_axis_label = "Time", y_axis_label = "Fraction", x_axis_type="datetime")
    x_d, y_d = bgd("DARK")
    x_g, y_g = bgd("GRAY")
    x_b, y_b = bgd("BRIGHT")

    source_d = ColumnDataSource(
            data=dict(
                x=x_d,
                y=y_d,
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in x_d],
            )
        )
    source_g = ColumnDataSource(
            data=dict(
                x=x_g,
                y=y_g,
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in x_g],
            )
        )
    source_b = ColumnDataSource(
            data=dict(
                x=x_b,
                y=y_b,
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in x_b],
            )
        )

    startend = np.array([np.min(tne['MJD']), np.min(tne['MJD']) + 365.2422*5])
    t1 = Time(startend, format='mjd', scale='utc')
    t = t1.to_datetime(timezone=tzone)
    source_line = ColumnDataSource(
            data=dict(
                x=t,
                y=[0, 1],
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in t],
            )
        )

    fig1.xaxis.major_label_orientation = np.pi/4

    fig1.line('x', 'y', source=source_d, line_width=2, color = "red", legend = "DARK")
    fig1.line('x', 'y', source=source_g, line_width=2, color = "blue", legend = "GREY")
    fig1.line('x', 'y', source=source_b, line_width=2, color = "green", legend = "BRIGHT")
    fig1.line('x', 'y', source=source_line, line_width=2, color = "grey", line_dash = "dashed")

    fig1.legend.location = "top_left"
    fig1.legend.click_policy="hide"
    fig1.legend.spacing = 0

    fig1.add_tools(hover)
    return fig1

def get_surveyTileprogress(exposures, tiles, width=300, height=300):
    '''
    Generates a plot of survey progress vs. time

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...

    Options:
        width, height: plot width and height in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]
    exposures_nocalib = nights_last_observed(exposures_nocalib["TILEID", "MJD", "PROGRAM"])
    exposures_nocalib.sort('MJD')

    tzone = TimezoneInfo(utc_offset = -7*u.hour)

    def bgd(string):
        tne_d = exposures_nocalib[exposures_nocalib["PROGRAM"] == string]
        x_d = np.array(tne_d['MJD'])
        s = 0
        y_d = np.array([])
        for i in x_d:
            s += 1
            y_d = np.append(y_d, s)
        t1 = Time(x_d, format='mjd', scale='utc')
        t = t1.to_datetime(timezone=tzone)
        return (t, y_d)

    hover = HoverTool(
            tooltips=[
                ("DATE", "@date"),
                ("# tiles", "@y")
            ]
        )

    fig = bk.figure(plot_width=width, plot_height=height, title = "# tiles vs time", x_axis_label = "Time",
                    y_axis_label = "# tiles", x_axis_type="datetime")
    x_d, y_d = bgd("DARK")
    x_g, y_g = bgd("GRAY")
    x_b, y_b = bgd("BRIGHT")

    source_d = ColumnDataSource(
            data=dict(
                x=x_d,
                y=y_d,
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in x_d],
            )
        )
    source_g = ColumnDataSource(
            data=dict(
                x=x_g,
                y=y_g,
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in x_g],
            )
        )
    source_b = ColumnDataSource(
            data=dict(
                x=x_b,
                y=y_b,
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in x_b],
            )
        )

    startend = np.array([np.min(exposures_nocalib['MJD']), np.min(exposures_nocalib['MJD']) + 365.2422*5])
    t1 = Time(startend, format='mjd', scale='utc')
    t = t1.to_datetime(timezone=tzone)
    source_line_d = ColumnDataSource(
            data=dict(
                x=t,
                y=[0, len(tiles[tiles["PROGRAM"] == "DARK"])],
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in t],
            )
        )

    source_line_g = ColumnDataSource(
            data=dict(
                x=t,
                y=[0, len(tiles[tiles["PROGRAM"] == "GRAY"])],
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in t],
            )
        )

    source_line_b = ColumnDataSource(
            data=dict(
                x=t,
                y=[0, len(tiles[tiles["PROGRAM"] == "BRIGHT"])],
                date=[t1.strftime("%a, %d %b %Y %H:%M") for t1 in t],
            )
        )

    fig.xaxis.major_label_orientation = np.pi/4

    fig.line('x', 'y', source=source_line_d, line_width=2, color = "red", line_dash = "dashed", alpha = 0.5)
    fig.line('x', 'y', source=source_line_g, line_width=2, color = "blue", line_dash = "dashed", alpha = 0.5)
    fig.line('x', 'y', source=source_line_b, line_width=2, color = "green", line_dash = "dashed", alpha = 0.5)
    fig.line('x', 'y', source=source_d, line_width=2, color = "red", legend = "DARK")
    fig.line('x', 'y', source=source_g, line_width=2, color = "blue", legend = "GRAY")
    fig.line('x', 'y', source=source_b, line_width=2, color = "green", legend = "BRIGHT")

    fig.legend.location = "top_left"
    fig.legend.click_policy="hide"
    fig.legend.spacing = 0

    fig.add_tools(hover)
    return fig

def get_hist(exposures, attribute, color, width=300, height=300):
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]

    hist, edges = np.histogram(exposures_nocalib[attribute], density=True, bins=50)

    fig_0 = bk.figure(plot_width=width, plot_height=height, title = attribute + " Histogram",
                    x_axis_label = attribute, y_axis_label = "Distribution")
    fig_0.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color=color, alpha=0.5)
    return fig_0

def get_exposuresPerTile_hist(exposures, color, width=300, height=300):
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]

    exposures_nocalib["ones"] = 1
    exposures_nocalib = exposures_nocalib["ones", "TILEID"]
    exposures_nocalib = exposures_nocalib.group_by("TILEID")
    exposures_nocalib = exposures_nocalib.groups.aggregate(np.sum)

    hist, edges = np.histogram(exposures_nocalib["ones"], density=True, bins=np.arange(0, np.max(exposures_nocalib["ones"])+1))

    fig_3 = bk.figure(plot_width=width, plot_height=height, title = "# Exposures per Tile Histogram",
                    x_axis_label = "# Exposures per Tile", y_axis_label = "Distribution")
    fig_3.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="orange", alpha=0.5)
    return fig_3

def get_exposeTimes_hist(exposures, width=600, height=400):
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]

    fig = bk.figure(plot_width=width, plot_height=height, title = "Exposure Times Histogram",
                    x_axis_label = "Exposure Time", y_axis_label = "Distribution")

    def exptime_dgb(string, color):
        a = exposures_nocalib[exposures_nocalib["PROGRAM"] == string]
        hist, edges = np.histogram(a["EXPTIME"], density=True, bins=50)
        fig.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color=color, alpha=0.5, legend = string)

    exptime_dgb("DARK", "red")
    exptime_dgb("GRAY", "blue")
    exptime_dgb("BRIGHT", "green")

    fig.legend.click_policy="hide"
    return fig

def get_moonplot(exposures, width=500, height=300):
    p = bk.figure(plot_width=width, plot_height=height, x_axis_label = "MOONFRAC", y_axis_label = "MOONALT")

    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]
    color_mapper = LinearColorMapper(palette="Magma256", low=np.min(exposures_nocalib["MOONSEP"]), high=np.max(exposures_nocalib["MOONSEP"]))

    source = ColumnDataSource(data=dict(
            MOONFRAC = exposures_nocalib["MOONFRAC"],
            MOONALT = exposures_nocalib["MOONALT"],
            MOONSEP = exposures_nocalib["MOONSEP"]
        ))

    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12, location=(0,0), title='MOONSEP')
    p.add_layout(color_bar, 'right')

    p.circle("MOONFRAC", "MOONALT", color=transform('MOONSEP', color_mapper), alpha=0.5, source=source)
    return p

def makeplots(exposures, tiles, outdir):
    '''
    Generates summary plots for the DESI survey QA

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...
        outdir: directory to write the files

    Writes outdir/summary.html
    '''

    #- Generate HTML header separately so that we can get the right bokeh
    #- version in there without mucking up the python string formatting
    header = """
    <!DOCTYPE html>
    <html lang="en-US">

    <link
        href="https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.css"
        rel="stylesheet" type="text/css"
    >
    <link
        href="https://cdn.pydata.org/bokeh/release/bokeh-tables-{version}.min.css"
        rel="stylesheet" type="text/css"
    >
    <script
        src="https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.js"
    ></script>
    <script src="https://cdn.pydata.org/bokeh/release/bokeh-tables-{version}.min.js"
    ></script>
    """.format(version=bokeh.__version__)

    #- Now add the HTML body with template placeholders for plots
    template = header + """
    <head>
    <style>
    body {
        margin: 0;
    }

    .header {
        font-family: "Open Serif", Arial, Helvetica, sans-serif;
        background-color: #f1f1f1;
        padding: 20px;
        text-align: center;
        justify: space-around;
    }

    .column {
        float: center;
        padding: 10px
    }

    .column.side {
        width = 20%;
    }

    .column.middle {
        width = 60%;
    }

    .flex-container {
        display: flex;
        flex-direction: row;
        flex-flow: row wrap;
        justify-content: space-around;
        padding: 20px;
    }

    p.sansserif {
        font-family: "Open Serif", Helvetica, sans-serif;
    }
    </style>
    </head>
    """

    template += """
    <body>
        <div class="header">
            <h1>DESI SURVEY QA</h1>
            <p>Through night {}</p>
        </div>
    """.format(max(exposures['NIGHT']))

    template += """
        <div class="flex-container">
            <div class="column side"></div>
            <div class="column middle">
                <div class="header">
                    <p class="sansserif">Progress Graphs</p>
                </div>

                <div class="flex-container">
                    <div>{{ skyplot_script }} {{ skyplot_div }}</div>
                    <div>{{ progress_script }} {{ progress_div }}</div>
                    <div>{{ progress_script_1 }} {{ progress_div_1 }}</div>
                    <div>{{ moonplot_script }} {{ moonplot_div }}</div>
                </div>

                <div class="header">
                    <p class="sansserif">Histograms</p>
                </div>

                <div class="flex-container">
                    <div>{{ airmass_script }} {{airmass_div }}</div>
                    <div>{{ seeing_script }} {{ seeing_div }}</div>
                    <div>{{ transp_hist_script }} {{ transp_hist_div }}</div>
                    <div>{{ exposePerTile_hist_script }} {{ exposePerTile_hist_div }}</div>
                    <div>{{ exptime_script }} {{ exptime_div }}</div>
                </div>

                <div class="header">
                    <p class="sansserif">Summary Table</p>
                </div>

                <div class="flex-container">
                    {{ summarytable_script }}
                    {{ summarytable_div }}
                </div>
            </div>
            <div class="column side"></div>
        </div>
    </body>

    </html>
    """

    skyplot = get_skyplot(exposures, tiles)
    skyplot_script, skyplot_div = components(skyplot)

    progressplot = get_surveyprogress(exposures, tiles)
    progress_script, progress_div = components(progressplot)

    progressplot_1 = get_surveyTileprogress(exposures, tiles)
    progress_script_1, progress_div_1 = components(progressplot_1)

    summarytable = get_summarytable(exposures)
    summarytable_script, summarytable_div = components(summarytable)

    seeing_hist = get_hist(exposures, "SEEING", "navy")
    seeing_script, seeing_div = components(seeing_hist)

    airmass_hist = get_hist(exposures, "AIRMASS", "green")
    airmass_script, airmass_div = components(airmass_hist)

    transp_hist = get_hist(exposures, "TRANSP", "purple")
    transp_hist_script, transp_hist_div = components(transp_hist)

    exposePerTile_hist = get_exposuresPerTile_hist(exposures, "orange")
    exposePerTile_hist_script, exposePerTile_hist_div = components(exposePerTile_hist)

    exptime_hist = get_exposeTimes_hist(exposures)
    exptime_script, exptime_div = components(exptime_hist)

    moonplot = get_moonplot(exposures)
    moonplot_script, moonplot_div = components(moonplot)

    #- Convert to a jinja2.Template object and render HTML
    html = jinja2.Template(template).render(
        skyplot_script=skyplot_script, skyplot_div=skyplot_div,
        progress_script=progress_script, progress_div=progress_div,
        progress_script_1=progress_script_1, progress_div_1=progress_div_1,
        summarytable_script=summarytable_script, summarytable_div=summarytable_div,
        airmass_script=airmass_script, airmass_div=airmass_div,
        seeing_script=seeing_script, seeing_div=seeing_div,
        exptime_script=exptime_script, exptime_div=exptime_div,
        transp_hist_script=transp_hist_script, transp_hist_div=transp_hist_div,
        exposePerTile_hist_script=exposePerTile_hist_script, exposePerTile_hist_div=exposePerTile_hist_div,
        moonplot_script=moonplot_script, moonplot_div=moonplot_div
        )

    outfile = os.path.join(outdir, 'summary.html')
    with open(outfile, 'w') as fx:
        fx.write(html)

    print('Wrote summary QA to {}'.format(outfile))
