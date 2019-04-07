"""
Summary plots of DESI survey progress and QA
"""

import sys, os
import numpy as np

import jinja2
from bokeh.embed import components
import bokeh
import bokeh.plotting as bk
from bokeh.models import ColumnDataSource, LinearColorMapper, ColorBar, HoverTool, CustomJS, HTMLTemplateFormatter, NumeralTickFormatter
from bokeh.models.widgets import NumberFormatter
from bokeh.models.widgets.tables import DataTable, TableColumn
from bokeh.layouts import gridplot
from bokeh.transform import transform
from astropy.time import Time, TimezoneInfo
from astropy.table import Table, join
from datetime import datetime, tzinfo
import astropy.units as u
from collections import Counter, OrderedDict

#- Avoid warnings from date & coord calculations in the future
import warnings
warnings.filterwarnings('ignore', 'ERFA function.*dubious year.*')
warnings.filterwarnings('ignore', 'Tried to get polar motions for times after IERS data is valid.*')

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

def get_skyplot(exposures, tiles, width=500, height=250, min_border_left=50, min_border_right=50):
    '''
    Generates sky plot of DESI survey tiles and progress. Colorcoded by night each tile was first
    observed, uses nights_first_observed function defined previously in this module to retrieve
    night each tile was first observed.

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...

    Options:
        width, height: plot width and height in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]
    tiles_sorted = Table(np.sort(tiles, order='TILEID'))
    observed_tiles = np.in1d(tiles_sorted['TILEID'], exposures_nocalib['TILEID'])
    observed_exposures = np.in1d(exposures_nocalib['TILEID'], tiles_sorted['TILEID'])
    tiles_shared = tiles_sorted[observed_tiles]
    exposures_shared = exposures_nocalib[observed_exposures]

    tiles_unique, indx = np.unique(exposures_shared['TILEID'], return_index=True)
    nights = exposures_shared['NIGHT'][indx]
    nights_int = np.array(nights).astype(int)

    mjd = exposures_shared['MJD'][indx]
    mjd_int = np.array(mjd).astype(int)

    expid = exposures_shared['EXPID'][indx]
    expid_int = np.array(expid).astype(int)

    source = ColumnDataSource(data=dict(
        RA = tiles_sorted['RA'],
        DEC = tiles_sorted['DEC'],
        TILEID = tiles_sorted['TILEID'],
        PROGRAM = tiles_sorted['PROGRAM'].astype(str),
        PASS = tiles_sorted['PASS'].astype(int),
        NIGHT = ["NA" for _ in np.ones(len(tiles['TILEID']))],
        MJD = ["NA" for _ in np.ones(len(tiles['TILEID']))],
        EXPID = ["NA" for _ in np.ones(len(tiles['TILEID']))]
    ))

    source_obs = ColumnDataSource(data=dict(
        RA_obs = tiles_shared['RA'],
        DEC_obs = tiles_shared['DEC'],
        TILEID = tiles_shared['TILEID'],
        PROGRAM = tiles_shared['PROGRAM'].astype(str),
        PASS = tiles_shared['PASS'].astype(int),
        NIGHT = nights_int,
        MJD = mjd_int,
        EXPID = expid_int
    ))

    hover = HoverTool(
            tooltips="""
                <font face="Arial" size="0">
                <font color="blue"> TILEID: </font> @TILEID <br>
                <font color="blue"> PROGRAM/PASS: </font> @PROGRAM / @PASS <br>
                <font color="blue"> 1ST NIGHT/EXPID: </font> @NIGHT / @EXPID
                </font>
            """
        )

    color_mapper = LinearColorMapper(palette="Viridis256", low=mjd_int.min(), high=mjd_int.max())

    #making figure
    fig = bk.figure(width=width, height=height, min_border_left=min_border_left, min_border_right=min_border_right)

    #unobserved tiles
    fig.circle('RA', 'DEC', source=source, color='gray', radius=0.25)

    #observed tiles
    fig.circle('RA_obs', 'DEC_obs', color=transform('MJD', color_mapper), size=3, alpha=0.85, source=source_obs)
    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12, location=(0,0), title='MJD', width=5)
    fig.add_layout(color_bar, 'right')

    fig.xaxis.axis_label = 'RA [degrees]'
    fig.yaxis.axis_label = 'Declination [degrees]'
    fig.title.text = 'Observed Tiles, Nightly Progress'

    fig.add_tools(hover)

    return fig

def get_median(attribute, exposures):
    '''Get the median value for a given attribute for all nights for all exposures taken each night.
    Input:
        attributes: one of the labels in the exposure column, string
        exposures: table with the exposures data
    Output:
        returns a numpy array of the median values for each night
    '''
    medians = []
    for n in np.unique(exposures['NIGHT']):
        # exp_night = exposures[exposures['NIGHT'] == n]
        # attrib = exp_night[attribute]
        ii = (exposures['NIGHT'] == n)
        attrib = np.asarray(exposures[attribute])[ii]
        medians.append(np.ma.median(attrib))  #- use masked median

    return np.array(medians)

def get_summarytable(exposures):
    '''
    Generates a summary table of key values for each night observed. Uses collections.Counter(), OrderedDict()

    Args:
        exposures: Table of exposures with columns...

    Returns a bokeh DataTable object.
    '''
    nights = np.unique(exposures['NIGHT'])

    isbright = (exposures['PROGRAM'] == 'BRIGHT')
    isgray = (exposures['PROGRAM'] == 'GRAY')
    isdark = (exposures['PROGRAM'] == 'DARK')
    iscalib = (exposures['PROGRAM'] == 'CALIB')

    num_nights = len(nights)
    brights = list()
    grays = list()
    darks = list()
    calibs = list()
    totals = list()
    for n in nights:
        thisnight = exposures['NIGHT'] == n
        totals.append(np.count_nonzero(thisnight))
        brights.append(np.count_nonzero(thisnight & isbright))
        grays.append(np.count_nonzero(thisnight & isgray))
        darks.append(np.count_nonzero(thisnight & isdark))
        calibs.append(np.count_nonzero(thisnight & iscalib))

    med_air = get_median('AIRMASS', exposures)
    med_seeing = get_median('SEEING', exposures)
    med_exptime = get_median('EXPTIME', exposures)
    med_transp = get_median('TRANSP', exposures)
    med_sky = get_median('SKY', exposures)

    source = ColumnDataSource(data=dict(
        nights = list(nights),
        totals = totals,
        brights = brights,
        grays = grays,
        darks = darks,
        calibs = calibs,
        med_air = med_air,
        med_seeing = med_seeing,
        med_exptime = med_exptime,
        med_transp = med_transp,
        med_sky = med_sky,
    ))

    formatter = NumberFormatter(format='0,0.00')
    template_str = '<a href="night-<%= nights %>.html"' + ' target="_blank"><%= value%></a>'

    columns = [
        TableColumn(field='nights', title='NIGHT', width=100, formatter=HTMLTemplateFormatter(template=template_str)),
        TableColumn(field='totals', title='Total', width=50),
        TableColumn(field='brights', title='Bright', width=50),
        TableColumn(field='grays', title='Gray', width=50),
        TableColumn(field='darks', title='Dark', width=50),
        TableColumn(field='calibs', title='Calibs', width=50),
        TableColumn(field='med_exptime', title='Median Exp. Time', width=100),
        TableColumn(field='med_air', title='Median Airmass', width=100, formatter=formatter),
        TableColumn(field='med_seeing', title='Median Seeing', width=100, formatter=formatter),
        TableColumn(field='med_sky', title='Median Sky', width=100, formatter=formatter),
        TableColumn(field='med_transp', title='Median Transparency', width=115, formatter=formatter),
    ]

    summary_table = DataTable(source=source, columns=columns, width=900, sortable=True, fit_columns=False)
    return summary_table

def nights_last_observed(exposures):
    '''
    Generates a table of the last exposure for every unique TILEID.
    Mainly serves as a helper function for get_surveyprogress()

    Args:
        exposures: Table of exposures

    Returns Table object
    '''
    def last(arr):
        return arr[len(arr)-1]
    return exposures.group_by("TILEID").groups.aggregate(last)

tzone = TimezoneInfo(utc_offset = -7*u.hour)
t1 = Time(58821, format='mjd', scale='utc')
t = t1.to_datetime(timezone=tzone)

def get_surveyprogress(exposures, tiles, line_source, hover_follow, width=250, height=250, min_border_left=50, min_border_right=50):
    '''
    Generates a plot of survey progress (EXPOSEFAC) vs. time

    Args:
        exposures: Table of exposures with columns "PROGRAM", "TILEID", "MJD"
        tiles: Table of tile locations with columns "TILEID", "EXPOSEFAC", "PROGRAM"
        line_source: line_source for the horizontal gray cursor-tracking line
        hover_follow: HoverTool object for the horizontal gray cursor-tracking line

    Options:
        width, height: plot width and height in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]

    tne = join(nights_last_observed(exposures_nocalib["TILEID", "MJD"]), tiles, keys="TILEID", join_type='inner')
    tne.sort('MJD')

    def bgd(string):
        w = tne["PROGRAM"] == string
        if not any(w):
            return ([], [])
        tne_d = tne[w]
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
            names=["D", "G", "B"],
            tooltips=[
                ("DATE", "@date"),
                ("TOTAL PERCENTAGE", "@y")
            ]
        )

    fig1 = bk.figure(plot_width=width, plot_height=height, title = "Progress(ExposeFac Weighted) vs Time", x_axis_label = "Time", y_axis_label = "Fraction", x_axis_type="datetime", min_border_left=min_border_left, min_border_right=min_border_right)
    fig1.xaxis.axis_label_text_color = '#ffffff'
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

    fig1.line('x', 'y', source=source_d, line_width=2, color = "red", legend = "DARK", name = "D")
    fig1.line('x', 'y', source=source_g, line_width=2, color = "blue", legend = "GREY", name = "G")
    fig1.line('x', 'y', source=source_b, line_width=2, color = "green", legend = "BRIGHT", name = "B")
    fig1.line('x', 'y', source=source_line, line_width=2, color = "grey", line_dash = "dashed")
    fig1.segment(x0='x', y0=0, x1='x', y1=1, color='grey', line_width=1, source=line_source)

    fig1.legend.location = "top_left"
    fig1.legend.click_policy="hide"
    fig1.legend.spacing = 0
    fig1.legend.label_text_font_size = '7pt'
    fig1.legend.glyph_height = 10
    fig1.legend.glyph_width = 10

    fig1.add_tools(hover)
    fig1.add_tools(hover_follow)
    return fig1

def get_surveyTileprogress(exposures, tiles, line_source, hover_follow, width=250, height=250, min_border_left=50, min_border_right=50):
    '''
    Generates a plot of survey progress (total tiles) vs. time

    Args:
        exposures: Table of exposures with columns "PROGRAM", "MJD", "TILEID"
        tiles: Table of tile locations with columns "TILEID", "PROGRAM"
        line_source: line_source for the horizontal gray cursor-tracking line
        hover_follow: HoverTool object for the horizontal gray cursor-tracking line

    Options:
        width, height: plot width and height in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]
    exposures_nocalib = nights_last_observed(exposures_nocalib["TILEID", "MJD", "PROGRAM"])
    exposures_nocalib.sort('MJD')

    tzone = TimezoneInfo(utc_offset = -7*u.hour)

    def bgd(string):
        w = exposures_nocalib["PROGRAM"] == string
        if not any(w):
            return ([], [])
        tne_d = exposures_nocalib[w]
        x_d = np.array(tne_d['MJD'])
        s = 0
        y_d = np.array([])
        for i in x_d:
            s += 1
            y_d = np.append(y_d, s)
        if x_d == []:
            return ([], [])
        t1 = Time(x_d, format='mjd', scale='utc')
        t = t1.to_datetime(timezone=tzone)
        return (t, y_d)

    hover = HoverTool(
            names=["G", "D", "B"],
            tooltips=[
                ("DATE", "@date"),
                ("# tiles", "@y")
            ]
        )

    fig = bk.figure(plot_width=width, plot_height=height, title = "# tiles vs time", x_axis_label = "Time",
                    y_axis_label = "# tiles", x_axis_type="datetime", min_border_left=min_border_left, min_border_right=min_border_right)
    fig.xaxis.axis_label_text_color = '#ffffff'
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
    fig.line('x', 'y', source=source_d, line_width=2, color = "red", legend = "DARK", name = "D")
    fig.line('x', 'y', source=source_g, line_width=2, color = "blue", legend = "GRAY", name = "G")
    fig.line('x', 'y', source=source_b, line_width=2, color = "green", legend = "BRIGHT", name = "B")
    fig.segment(x0='x', y0=0, x1='x', y1=8000, color='grey', line_width=1, source=line_source)

    fig.legend.location = "top_left"
    fig.legend.click_policy="hide"
    fig.legend.spacing = 0
    fig.legend.label_text_font_size = '7pt'
    fig.legend.glyph_height = 10
    fig.legend.glyph_width = 10

    fig.add_tools(hover)
    fig.add_tools(hover_follow)
    return fig

def get_linked_progress_plots(exposures, tiles, width=300, height=300, min_border_left=50, min_border_right=50):
    '''
    Generates linked progress plots of frac(EXPOSEFAC) vs. time, and (total # of tiles) vs. time

    Args:
        exposures: Table of exposures with columns "PROGRAM", "MJD", "TILEID"
        tiles: Table of tile locations with columns "TILEID", "EXPOSEFAC", "PROGRAM"

    Options:
        width, height: plot width and height in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels

    Returns bokeh Layout object
    '''

    # Data Source for the curser-following vertical line on the progress plots
    first_expose = np.min(exposures['MJD'])
    startend = np.array([first_expose, first_expose + 365.2422*5])
    startend_t = Time(startend, format='mjd', scale='utc')
    startend_t = startend_t.to_datetime(timezone=tzone)

    line_source = ColumnDataSource(data=dict(x=[t], lower=[startend_t[0]], upper=[startend_t[1]]))

    # js code is used as the callback for the HoverTool
    js = '''
    /// get mouse data (location of pointer in the plot)
    var geometry = cb_data['geometry'];

    /// get the current value of x in line_source
    var data = line_source.data;
    var x = data['x'];

    /// if the mouse is indeed hovering over the plot, change the line_source value
    if (isFinite(geometry.x) && (geometry.x >= data['lower'][0]) && (geometry.x <= data['upper'][0])) {
      x[0] = geometry.x
      line_source.change.emit();
    }
    '''

    hover_follow = HoverTool(tooltips=None,
                          point_policy='follow_mouse',
                          callback=CustomJS(code=js, args={'line_source': line_source}))

    surveyprogress = get_surveyprogress(exposures, tiles, line_source, hover_follow, width=width, height=height, min_border_left=min_border_left, min_border_right=min_border_right)
    tileprogress = get_surveyTileprogress(exposures, tiles, line_source, hover_follow, width=width, height=height, min_border_left=min_border_left, min_border_right=min_border_right)
    return gridplot([surveyprogress, tileprogress], ncols=2, plot_width=width, plot_height=height, toolbar_location='right')

def get_hist(exposures, attribute, color, width=250, height=250, min_border_left=50, min_border_right=50):
    '''
    Generates a histogram of the attribute provided for the given exposures table

    Args:
        exposures: Table of exposures with columns "PROGRAM" and attribute
        attribute: String; must be the label of a column in exposures
        color: String; color of the histogram

    Options:
        width, height: plot width and height in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]

    hist, edges = np.histogram(exposures_nocalib[attribute], density=True, bins=50)

    fig_0 = bk.figure(plot_width=width, plot_height=height,
                    x_axis_label = attribute.title(),
                    min_border_left=min_border_left, min_border_right=min_border_right,
                    title = 'title')

    fig_0.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color=color, alpha=0.5)
    fig_0.toolbar_location = None
    fig_0.title.text_color = '#ffffff'
    fig_0.yaxis.major_label_text_font_size = '0pt'
    
    if attribute == 'TRANSP':
        fig_0.xaxis.axis_label = 'Transparency'

    if attribute == 'HOURANGLE':
        fig_0.xaxis.axis_label = 'Hour Angle'

    return fig_0

def get_exposuresPerTile_hist(exposures, color, width=250, height=250, min_border_left=50, min_border_right=50):
    '''
    Generates a histogram of the number of exposures per tile for the given
    exposures table

    Args:
        exposures: Table of exposures with column "TILEID"
        color: String; color of the histogram

    Options:
        width, height: plot width and height in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]

    exposures_nocalib["ones"] = 1
    exposures_nocalib = exposures_nocalib["ones", "TILEID"]
    exposures_nocalib = exposures_nocalib.group_by("TILEID")
    exposures_nocalib = exposures_nocalib.groups.aggregate(np.sum)

    hist, edges = np.histogram(exposures_nocalib["ones"], density=True, bins=np.arange(0, np.max(exposures_nocalib["ones"])+1))

    fig_3 = bk.figure(plot_width=width, plot_height=height,
                    x_axis_label = "# Exposures per Tile",
                    title = 'title',
                    min_border_left=min_border_left, min_border_right=min_border_right)
    fig_3.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="orange", alpha=0.5)
    fig_3.toolbar_location = None
    fig_3.title.text_color = '#ffffff'
    fig_3.yaxis.major_label_text_font_size = '0pt'
    
    return fig_3

def get_exposeTimes_hist(exposures, width=500, height=300, min_border_left=50, min_border_right=50):
    '''
    Generates three overlaid histogram of the exposure times for the given
    exposures table. Each of the histograms correspond to different
    PROGRAM type: DARK, GREY, BRIGHT

    Args:
        exposures: Table of exposures with columns "PROGRAM", "EXPTIME"

    Options:
        width, height: plot width and height in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]

    fig = bk.figure(plot_width=width, plot_height=height, title = 'title', x_axis_label = "Exposure Time", min_border_left=min_border_left, min_border_right=min_border_right)

    def exptime_dgb(program, color):
        '''
        Adds a histogram to fig that correspond to the program of the argument with the color provided.
        The histogram will be exposure time per exposure.

        Args:
            program: String of the desired program name
            color: Color of histogram
        '''
        w = exposures_nocalib["PROGRAM"] == program
        if not any(w):
            return
        a = exposures_nocalib[w]
        hist, edges = np.histogram(a["EXPTIME"], density=True, bins=50)
        fig.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color=color, alpha=0.5, legend = program)

    exptime_dgb("DARK", "red")
    exptime_dgb("GRAY", "blue")
    exptime_dgb("BRIGHT", "green")

    fig.legend.click_policy="hide"
    fig.toolbar_location = None
    fig.yaxis[0].formatter = NumeralTickFormatter(format="0.000")
    fig.yaxis.major_label_orientation = np.pi/4
    fig.yaxis.major_label_text_font_size = '0pt'
    fig.legend.label_text_font_size = '8.5pt'
    fig.legend.glyph_height = 15
    fig.legend.glyph_width = 15
    fig.title.text_color = '#ffffff'
    
    return fig

def get_moonplot(exposures, width=250, height=250, min_border_left=50, min_border_right=50):
    '''
    Generates a scatter plot of MOONFRAC vs MOONALT. Each point is then colored
    with a gradient corresponding to its MOONSEP.

    Args:
        exposures: Table of exposures with columns "MOONFRAC", "MOONALT", "MOONSEP"

    Options:
        width, height: plot width and height in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels

    Returns bokeh Figure object
    '''
    p = bk.figure(plot_width=width, plot_height=height, x_axis_label = "Moon Fraction",
     y_axis_label = "Moon Altitude", min_border_left=min_border_left, min_border_right=min_border_right)

    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]
    color_mapper = LinearColorMapper(palette="Magma256", low=0, high=180)

    source = ColumnDataSource(data=dict(
            MOONFRAC = exposures_nocalib["MOONFRAC"],
            MOONALT = exposures_nocalib["MOONALT"],
            MOONSEP = exposures_nocalib["MOONSEP"]
        ))

    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12, location=(0,0), width=5)
    p.add_layout(color_bar, 'right')
    p.title.text = 'Moon Fraction vs Moon Altitude, colored with MOONSEP'

    p.circle("MOONFRAC", "MOONALT", color=transform('MOONSEP', color_mapper), alpha=0.5, source=source)
    return p

def get_expTimePerTile(exposures, width=250, height=250, min_border_left=50, min_border_right=50):
    '''
    Generates three overlaid histogram of the total exposure time per tile for the given
    exposures table. Each of the histograms correspond to different
    PROGRAM type: DARK, GREY, BRIGHT

    Args:
        exposures: Table of exposures with columns "PROGRAM", "EXPTIME"

    Options:
        width, height: plot width and height in pixels
        min_border_left, min_border_right: set minimum width for external labels in pixels

    Returns bokeh Figure object
    '''
    keep = exposures['PROGRAM'] != 'CALIB'
    exposures_nocalib = exposures[keep]
    exposures_nocalib = exposures_nocalib["PROGRAM", "TILEID", "EXPTIME"]

    fig = bk.figure(plot_width=width, plot_height=height, title = 'title', x_axis_label = "Total Exposure Time", min_border_left=min_border_left, min_border_right=min_border_right)
    fig.yaxis.major_label_text_font_size = '0pt'
    fig.xaxis.major_label_orientation = np.pi/4
    fig.title.text_color = '#ffffff'

    def sum_or_first(i):
        if type(i[0]) is str:
            return i[0]
        return np.sum(i)

    def total_exptime_dgb(program, color):
        '''
        Adds a histogram to fig that correspond to the program of the argument with the color provided.
        The histogram will be Total Exposure Time per Tile.

        Args:
            program: String of the desired program name
            color: Color of histogram
        '''
        # a = exposures_nocalib.group_by("TILEID").groups.aggregate(sum_or_first)
        # a = a[a["PROGRAM"] == program]
        thisprogram = (exposures_nocalib["PROGRAM"] == program)
        a = exposures_nocalib["TILEID", "EXPTIME"][thisprogram].group_by("TILEID").groups.aggregate(np.sum)

        hist, edges = np.histogram(a["EXPTIME"], density=True, bins=50)
        fig.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color=color, alpha=0.5, legend = program)


    total_exptime_dgb("DARK", "red")
    total_exptime_dgb("GRAY", "blue")
    total_exptime_dgb("BRIGHT", "green")

    fig.legend.click_policy="hide"
    fig.yaxis[0].formatter = NumeralTickFormatter(format="0.000")
    fig.yaxis.major_label_orientation = np.pi/4
    fig.legend.label_text_font_size = '8.5pt'
    fig.legend.glyph_height = 15
    fig.legend.glyph_width = 15

    return fig

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
        padding: 10px;
        text-align: left;
        justify: space-around;
    }

    .column {
        float: center;
    }

    .column.side {
        width = 10%;
    }

    .column.middle {
        width = 80%;
    }

    .flex-container {
        display: flex;
        flex-direction: row;
        flex-flow: row wrap;
        justify-content: flex-start;
        padding: 10px;
        align-items: flex-end;
    }

    p.sansserif {
        font-family: "Open Serif", Helvetica, sans-serif;
    }
    </style>
    </head>
    """

    template += """
    <body>
        <div class="flex-container">
            <div class="column side"></div>
            <div class="column middle">
                <div class="header">
                    <p class='sansserif'>DESI Survey QA through {}</p>
        </div>
    """.format(max(exposures['NIGHT']))

    template += """
                <div class="flex-container">
                    <div>{{ skyplot_script }} {{ skyplot_div }}</div>
                    <div>{{ progress_script }} {{ progress_div }}</div>
                </div>

                <div class="header">
                    <p class="sansserif">Observing Conditions</p>
                </div>

                <div class="flex-container">
                    <div>{{ airmass_script }} {{ airmass_div }}</div>
                    <div>{{ seeing_script }} {{ seeing_div }}</div>
                    <div>{{ transp_hist_script }} {{ transp_hist_div }}</div>
                    <div>{{ exposePerTile_hist_script }} {{ exposePerTile_hist_div }}</div>
                    <div>{{ brightness_script }} {{ brightness_div }}</div>
                    <div>{{ hourangle_script }} {{ hourangle_div }}</div>
                    <div>{{ exptime_script }} {{ exptime_div }}</div>
                    <div>{{ expTimePerTile_script }} {{ expTimePerTile_div }}</div>
                    <div>{{ moonplot_script }} {{ moonplot_div }}</div>
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

    min_border = 30

    skyplot = get_skyplot(exposures, tiles, 500, 250, min_border_left=min_border, min_border_right=min_border)
    skyplot_script, skyplot_div = components(skyplot)

    progressplot = get_linked_progress_plots(exposures, tiles, 250, 250, min_border_left=min_border, min_border_right=min_border)
    progress_script, progress_div = components(progressplot)

    summarytable = get_summarytable(exposures)
    summarytable_script, summarytable_div = components(summarytable)

    seeing_hist = get_hist(exposures, "SEEING", "navy", 250, 250, min_border_left=min_border, min_border_right=min_border)
    seeing_script, seeing_div = components(seeing_hist)

    airmass_hist = get_hist(exposures, "AIRMASS", "green", 250, 250, min_border_left=min_border, min_border_right=min_border)
    airmass_script, airmass_div = components(airmass_hist)

    transp_hist = get_hist(exposures, "TRANSP", "purple", 250, 250, min_border_left=min_border, min_border_right=min_border)
    transp_hist_script, transp_hist_div = components(transp_hist)

    exposePerTile_hist = get_exposuresPerTile_hist(exposures, "orange", 250, 250, min_border_left=min_border, min_border_right=min_border)
    exposePerTile_hist_script, exposePerTile_hist_div = components(exposePerTile_hist)

    exptime_hist = get_exposeTimes_hist(exposures, 250, 250, min_border_left=min_border, min_border_right=min_border)
    exptime_script, exptime_div = components(exptime_hist)

    moonplot = get_moonplot(exposures, 500, 250, min_border_left=min_border, min_border_right=min_border)
    moonplot_script, moonplot_div = components(moonplot)

    brightnessplot = get_hist(exposures, "SKY", "maroon", 250, 250, min_border_left=min_border, min_border_right=min_border)
    brightness_script, brightness_div = components(brightnessplot)

    hourangleplot = get_hist(exposures, "HOURANGLE", "magenta", 250, 250, min_border_left=min_border, min_border_right=min_border)
    hourangle_script, hourangle_div = components(hourangleplot)

    expTimePerTile_plot = get_expTimePerTile(exposures, 250, 250, min_border_left=min_border, min_border_right=min_border)
    expTimePerTile_script, expTimePerTile_div = components(expTimePerTile_plot)

    #- Convert to a jinja2.Template object and render HTML
    html = jinja2.Template(template).render(
        skyplot_script=skyplot_script, skyplot_div=skyplot_div,
        progress_script=progress_script, progress_div=progress_div,
        summarytable_script=summarytable_script, summarytable_div=summarytable_div,
        airmass_script=airmass_script, airmass_div=airmass_div,
        seeing_script=seeing_script, seeing_div=seeing_div,
        exptime_script=exptime_script, exptime_div=exptime_div,
        transp_hist_script=transp_hist_script, transp_hist_div=transp_hist_div,
        exposePerTile_hist_script=exposePerTile_hist_script, exposePerTile_hist_div=exposePerTile_hist_div,
        brightness_script=brightness_script, brightness_div=brightness_div,
        hourangle_script=hourangle_script, hourangle_div=hourangle_div,
        expTimePerTile_script=expTimePerTile_script, expTimePerTile_div=expTimePerTile_div,
        moonplot_script=moonplot_script, moonplot_div=moonplot_div,
        )

    outfile = os.path.join(outdir, 'summary.html')
    with open(outfile, 'w') as fx:
        fx.write(html)

    print('Wrote summary QA to {}'.format(outfile))
