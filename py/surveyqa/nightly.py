"""
Plots for daily DESI observing
"""

from __future__ import absolute_import, division, print_function
import sys, os
import numpy as np
import bokeh as bk

import jinja2
from bokeh.embed import components
import bokeh
import bokeh.plotting as bk
from bokeh.models import ColumnDataSource

from astropy.time import Time
from bokeh.models import HoverTool, ColorBar
from bokeh.layouts import gridplot
from astropy.table import join
from astropy.time import TimezoneInfo
import astropy.units as u
from datetime import tzinfo
from datetime import datetime
from bokeh.models.glyphs import HBar
from bokeh.models import LabelSet, FactorRange
from bokeh.palettes import viridis
from bokeh.transform import factor_cmap
from bokeh.models.widgets.tables import DataTable, TableColumn
from astropy import coordinates
from bokeh.models.widgets import NumberFormatter

#- Avoid warnings from date & coord calculations in the future
import warnings
warnings.filterwarnings('ignore', 'ERFA function.*dubious year.*')
warnings.filterwarnings('ignore', 'Tried to get polar motions for times after IERS data is valid.*')

def find_night(exposures, night):
    """
    Generates a subtable of exposures corresponding to data from a single night N and adds column TIME

    ARGS:
        exposures : Table of exposures with columns...
        night : String representing a single value in the NIGHT column of the EXPOSURES table

    Returns an astropy table object
    """
    #- Filters by NIGHT
    exposures = exposures[exposures['NIGHT'] == night]

    #- Creates DateTime objects in Arizona timezone
    mjds = np.array(exposures['MJD'])
    tzone = TimezoneInfo(utc_offset = -7*u.hour)
    times = [Time(mjd, format='mjd', scale='utc').to_datetime(timezone=tzone) for mjd in mjds]

    #- Adds times to table
    exposures['TIME'] = times

    return exposures


def get_timeseries(cds, name):
    """
    Generates times and values arrays for column `name`

    ARGS:
        cds : ColumnDataSource of exposures
        name : String corresponding to a column in CDS

    Returns numpy array objects
    """
    x = np.array(cds.data['TIME'])
    y = np.array(cds.data[name])

    return x, y


def plot_timeseries(source, name, color, tools=None, x_range=None, title=None, tooltips=None, width=400, height=150, min_border_left=50, min_border_right=50):
    """
    Plots values corresponding to NAME from SOURCE vs. time with TOOLS

    ARGS:
        source : ColumnDataSource of exposures
        name : string name of this timeseries
        color : color for plotted data points
        x_range : a range of x values to link multiple plots together

    Options:
        height, width: height and width of the graph in pixels
        x_range: x-axis range of the graph
        tools: interactive features
        title: graph title
        min_border_left, min_border_right: set minimum width of surrounding labels (in pixels)

    Returns bokeh figure object
    """

    times, values = get_timeseries(source, name)

    fig = bk.figure(width=width, height=height, tools=tools,
                    x_axis_type='datetime', x_range=x_range,
                    active_scroll='wheel_zoom', title=title,
                    x_axis_label='Time',
                    min_border_left=min_border_left,
                    min_border_right=min_border_right)
    fig.xaxis.axis_label_text_color='#ffffff'
    fig.line('TIME', name, source=source)
    r = fig.circle('TIME', name, line_color=color, fill_color='white',
                   size=6, line_width=2, hover_color='firebrick', source=source)

    #- Formatting
    fig.xgrid.grid_line_color = None
    fig.outline_line_color = None
    fig.yaxis.axis_label = name.title()
    
    if name == 'TRANSP':
        fig.yaxis.axis_label = 'Transparency'
    if name == 'HOURANGLE':
        fig.yaxis.axis_label = 'Hour Angle'
    if name == 'EXPTIME':
        fig.yaxis.axis_label = 'Exposure Time'

    #- Add hover tool
    hover = HoverTool(renderers = [r], tooltips=tooltips)
    fig.add_tools(hover)

    return fig

def get_nightlytable(exposures):
    '''
    Generates a summary table of the exposures from the night observed.

    Args:
        exposures: Table of exposures with columns...

    Returns a bokeh DataTable object.
    '''

    source = ColumnDataSource(data=dict(
        expid = np.array(exposures['EXPID']),
        flavor = np.array(exposures['FLAVOR'], dtype='str'),
        program = np.array(exposures['PROGRAM'], dtype='str'),
        exptime = np.array(exposures['EXPTIME']),
        tileid = np.array(exposures['TILEID']),
        airmass = np.array(exposures['AIRMASS']),
        seeing = np.array(exposures['SEEING']),
        transp = np.array(exposures['TRANSP']),
        sky = np.array(exposures['SKY']),
        hourangle = np.array(exposures['HOURANGLE']),  
    ))

    formatter = NumberFormatter(format='0,0.00')
    columns = [
        TableColumn(field='expid', title='Exposure ID'),
        TableColumn(field='flavor', title='Flavor'),
        TableColumn(field='program', title='Program'),
        TableColumn(field='exptime', title='Exposure Time'),
        TableColumn(field='tileid', title='Tile ID'),
        TableColumn(field='airmass', title='Airmass', formatter=formatter),
        TableColumn(field='seeing', title='Seeing', formatter=formatter),
        TableColumn(field='transp', title='Transparency', formatter=formatter),
        TableColumn(field='sky', title='Sky', formatter=formatter),
        TableColumn(field='hourangle', title='Hour Angle', formatter=formatter),
    ]

    nightly_table = DataTable(source=source, columns=columns, width=1000, sortable=True)

    return nightly_table


def getPhase(night):
    '''
    Returns the phase of the moon as a decimal given the number of nights since full_zero
    
    Args:
        night : number of nights since full_zero, an inital night of full moon
    '''
    phase = -0.5 * np.sin(np.pi/15 * (night)) + 0.5
    return phase


def phaseSign(night):
    dt = -1 * np.cos(np.pi/15*night)
    return dt


def toDatetime(night):
    '''
    Returns the night parsed into a datetime object
    
    Args:
        night: a single night given as YYYYMMDD in string representation
    '''
    n = datetime(int(night[:4]), int(night[4:6]), int(night[6:]))
    return n


def numNightsFullZero(date):
    '''
    Returns the number of nights since a specified night of the full moon,
    full_zero (11/12/2019 6:34)
    
    Args:
        night: a single night given as a datetime object
    '''
    full_zero = datetime(2019, 11, 12, 6, 34)
    diff = date - full_zero
    return diff.days


def getWedge(phase, der, fig, ra, dec):
    '''
    Given a phase of the moon, returns the bokeh rendered point to represent the phase on the skypath plot
    
    Args:
        phase: a proportion representing the phase of the moon 
            where 1 corresponds to full moon and 0 corresponds to no moon
    '''
    if (phase <= 0.25):
        return fig.arc(ra, dec, start_angle=0, end_angle=2*np.pi, radius=4, color='gold')
    elif (phase <= 0.75 and der > 0):
        return fig.wedge(ra, dec, start_angle=-np.pi/2, end_angle=np.pi/2, radius=4, color='gold')
    elif (phase <= 7.5 and der < 0):
        return fig.wedge(ra, dec, start_angle=np.pi/2, end_angle=3*np.pi/2, radius=4, color='gold')
    else:
        return fig.wedge(ra, dec, start_angle=0, end_angle=2*np.pi, radius=4, color='gold')

    
def getMoonRend(night, fig, ra, dec):
    '''
    Configures settings for getWedge and returns a bokeh rendered point to represent the phase of the moon
    on the skypath plot for a specific night
    
    Args:
        night : a single string representation of a night = YEARMMDD
        fig : a bokeh figure object from the skypath plot for the given NIGHT
        ra :  the right ascension coordinate for the moon on the given NIGHT
        dec: the declination coordinate for the moon on the given NIGHT
    '''
    n = numNightsFullZero(toDatetime(night))
    phase = getPhase(n)
    der = phaseSign(n)
    moon = getWedge(phase, der, fig, ra, dec)
    return moon


def get_moonloc(night):
    """
    Returns the location of the moon on the given NIGHT
    
    Args:
        night : night = YEARMMDD of sunset
    
    Returns a SkyCoord object
    """
    #- Re-formats night into YYYY-MM-DD HH:MM:SS 
    iso_format = night[:4] + '-' + night[4:6] + '-' + night[6:] + ' 00:00:00'
    t_midnight = Time(iso_format, format='iso') + 24*u.hour
    #- Sets timezone
    t_local = t_midnight + (-7)*u.hour
    
    #- Sets location
    kitt = coordinates.EarthLocation.of_site('Kitt Peak National Observatory')
    
    #- Gets moon coordinates
    moon_loc = coordinates.get_moon(time=t_local, location=kitt)
    
    return moon_loc


def get_skypathplot(exposures, tiles, width=600, height=300, min_border_left=50, min_border_right=50):
    """
    Generate a plot which maps the location of tiles observed on NIGHT

    ARGS:
        exposures : Table of exposures with columns specific to a single night
        tiles: Table of tile locations with columns ...

    Options:
        height, width: height and width of the graph in pixels
        min_border_left, min_border_right: set minimum width of surrounding labels (in pixels)

    Returns a bokeh figure object
    """
    #- Merges tiles data for all exposures on a single night N
    tiles_and_exps = join(exposures, tiles['STAR_DENSITY', 'EXPOSEFAC', 'OBSCONDITIONS', 'TILEID'], keys='TILEID')
    tiles_and_exps.sort('TIME')

    #- Converts data format into ColumnDataSource
    src = ColumnDataSource(data={'RA':np.array(tiles_and_exps['RA']),
                                 'DEC':np.array(tiles_and_exps['DEC']),
                                 'EXPID':np.array(tiles_and_exps['EXPID']),
                                 'PROGRAM':np.array([str(n) for n in tiles_and_exps['PROGRAM']])})

    #- Plot options
    night_name = exposures['NIGHT'][0]
    string_date = night_name[4:6] + "-" + night_name[6:] + "-" + night_name[:4]

    fig = bk.figure(width=width, height=height, title='Tiles observed on ' + string_date, 
                    min_border_left=min_border_left, min_border_right=min_border_right)
    fig.yaxis.axis_label = 'Declination (degrees)'
    fig.xaxis.axis_label = 'Right Ascension (degrees)'

    #- Plots all tiles
    unobs = fig.circle(tiles['RA'], tiles['DEC'], color='gray', size=1)

    #- Color-coding for program
    EXPTYPES = ['DARK', 'GRAY', 'BRIGHT']
    COLORS = ['red', 'blue', 'green']
    mapper = factor_cmap(field_name='PROGRAM', palette=COLORS, factors=EXPTYPES)

    #- Plots tiles observed on NIGHT
    obs = fig.scatter('RA', 'DEC', size=5, fill_alpha=0.7, legend='PROGRAM', source=src, color=mapper)
    fig.line(src.data['RA'], src.data['DEC'], color='navy', alpha=0.4)
    
    #- Stars the first point observed on NIGHT
    first = tiles_and_exps[0]
    fig.asterisk(first['RA'], first['DEC'], size=10, line_width=1.5, fill_color=None, color='orange')
    
    #- Adds moon location at midnight on NIGHT
    night = exposures['NIGHT'][0]
    moon_loc = get_moonloc(night)
    ra, dec = float(moon_loc.ra.to_string(decimal=True)), float(moon_loc.dec.to_string(decimal=True))
    moon = getMoonRend(night, fig, ra, dec)
    #fig.circle(ra, dec, size=10, color='gold')    
    

    #- Circles the first point observed on NIGHT
    first = tiles_and_exps[0]
    fig.asterisk(first['RA'], first['DEC'], size=10, line_width=1.5, fill_color=None, color='gold')

    #- Adds hover tool
    TOOLTIPS = [("(RA, DEC)", "(@RA, @DEC)"), ("EXPID", "@EXPID")]
    obs_hover = HoverTool(renderers = [obs], tooltips=TOOLTIPS)
    fig.add_tools(obs_hover)

    return fig


def overlaid_hist(all_exposures, night_exposures, attribute, color, width=300, height=150, min_border_left=50, min_border_right=50):
    """
    Generates an overlaid histogram for a single attribute comparing the distribution
    for all of the exposures vs. those from just one night

    ARGS:
        all_exposures : a table of all the science exposures
        night_exposures : a table of all the science exposures for a single night
        attribute : a string name of a column in the exposures tables
        color : color of histogram
    Options:
        height, width: height and width of the graph in pixels
        min_border_left, min_border_right: set minimum width of surrounding labels (in pixels)

    Returns a bokeh figure object
    """
    hist_all, edges_all = np.histogram(np.array(all_exposures[attribute]), density=True, bins=50)
    hist_night, edges_night = np.histogram(np.array(night_exposures[attribute]), density=True, bins=50)

    fig = bk.figure(plot_width=width, plot_height=height,
                    x_axis_label = attribute.title(), y_axis_label = 'title',
                    min_border_left=min_border_left, min_border_right=min_border_right)
    fig.quad(top=hist_all, bottom=0, left=edges_all[:-1], right=edges_all[1:], fill_color=color, alpha=0.2)
    fig.quad(top=hist_night, bottom=0, left=edges_night[:-1], right=edges_night[1:], fill_color=color, alpha=0.6)
    
    if attribute == 'TRANSP':
        fig.xaxis.axis_label = 'Transparency'
    if attribute == 'HOURANGLE':
        fig.xaxis.axis_label = 'Hour Angle'
    if attribute == 'EXPTIME':
        fig.xaxis.axis_label = 'Exposure Time'
    
    fig.yaxis.major_label_text_font_size = '0pt'
    fig.yaxis.major_tick_line_color = None  
    fig.yaxis.minor_tick_line_color = None
    fig.yaxis.axis_label_text_color = '#ffffff'
    fig.ygrid.grid_line_color = None
    fig.xgrid.grid_line_color = None
    fig.toolbar_location = None

    return fig

def makeplots(night, exposures, tiles, outdir):
    '''
    Generates summary plots for the DESI survey QA

    Args:
        night : String representing a single value in the NIGHT column of the EXPOSURES table
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...
        outdir: directory to write the files

    Writes outdir/night-*.html
    '''

    #getting path for the previous and next night links, first and last night links, link back to summary page
    [prev_str, next_str] = get_night_link(night, exposures)
    first_str = get_night_link(exposures['NIGHT'][0], exposures)[0]
    last_str = get_night_link(exposures['NIGHT'][-1], exposures)[1]
    summary_str = "summary.html"

    #- Separate calibration exposures
    all_exposures = exposures[exposures['PROGRAM'] != 'CALIB']
    all_calibs = exposures[exposures['PROGRAM'] == 'CALIB']

    #- Filter exposures to just this night and adds columns DATETIME and MJD_hour
    exposures = find_night(all_exposures, night)
    calibs = find_night(all_calibs, night)

    #- Plot options
    #title='Airmass, Seeing, Exptime vs. Time for {}/{}/{}'.format(night[4:6], night[6:], night[:4])
    TOOLS = ['box_zoom', 'reset', 'wheel_zoom']
    TOOLTIPS = [("EXPID", "@EXPID"), ("Airmass", "@AIRMASS"), ("Seeing", "@SEEING"),
                ("Exposure Time", "@EXPTIME"), ("Transparency", "@TRANSP"), ("HOURANGLE", "@HOURANGLE")]

    #- Create ColumnDataSource for linking timeseries plots
    COLS = ['EXPID', 'TIME', 'AIRMASS', 'SEEING', 'EXPTIME', 'TRANSP', 'SKY', 'HOURANGLE']
    src = ColumnDataSource(data={c:np.array(exposures[c]) for c in COLS})

    #- Get timeseries plots for several variables
    min_border_right_time = 0
    min_border_left_time = 60
    min_border_right_hist = 0
    min_border_left_hist = 70
    min_border_right_count = 0
    min_border_left_count = 70
    min_border_right_sky = 0
    min_border_left_sky = 60
    
    time_hist_plot_height = 160
    
    airmass = plot_timeseries(src, 'AIRMASS', 'green', tools=TOOLS, x_range=None, title=None, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    seeing = plot_timeseries(src, 'SEEING', 'navy', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    exptime = plot_timeseries(src, 'EXPTIME', 'darkorange', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    transp = plot_timeseries(src, 'TRANSP', 'purple', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    hourangle = plot_timeseries(src, 'HOURANGLE', 'maroon', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    brightness = plot_timeseries(src, 'SKY', 'pink', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)

    #- Convert these to the components to include in the HTML
    timeseries_script, timeseries_div = components(bk.Column(airmass, seeing, exptime, transp, hourangle, brightness))

    #making the nightly table of values
    nightlytable = get_nightlytable(exposures)
    table_script, table_div = components(nightlytable)

    #adding in the skyplot components
    skypathplot = get_skypathplot(exposures, tiles, width=600, height=250, min_border_left=min_border_left_sky, min_border_right=min_border_right_sky)
    skypathplot_script, skypathplot_div = components(skypathplot)

    #adding in the components of the exposure types bar plot
    exptypecounts = get_exptype_counts(exposures, calibs, width=250, height=250, min_border_left=min_border_left_count, min_border_right=min_border_right_count)
    exptypecounts_script, exptypecounts_div = components(exptypecounts)

    #- Get overlaid histograms for several variables
    airmasshist = overlaid_hist(all_exposures, exposures, 'AIRMASS', 'green', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    seeinghist = overlaid_hist(all_exposures, exposures, 'SEEING', 'navy', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    exptimehist = overlaid_hist(all_exposures, exposures, 'EXPTIME', 'darkorange', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    transphist = overlaid_hist(all_exposures, exposures, 'TRANSP', 'purple', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    houranglehist = overlaid_hist(all_exposures, exposures, 'HOURANGLE', 'maroon', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    brightnesshist = overlaid_hist(all_exposures, exposures, 'SKY', 'pink', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)

    #adding in the components of the overlaid histograms
    overlaidhists_script, overlaidhists_div = components(bk.Column(airmasshist, seeinghist, exptimehist, transphist, houranglehist, brightnesshist))


    #----
    #- Template HTML for this page

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
        text-align: center;
        justify: space-around;
    }

    .column {
        float: center;
        padding: 10px
    }

    .column.side {
        width = 5%;
    }

    .column.middle {
        width = 90%;
    }

    .flex-container {
        display: flex;
        flex-direction: row;
        flex-flow: row wrap;
        justify-content: center;
        padding: 10px;
    }

    p.sansserif {
        font-family: "Open Serif", Helvetica, sans-serif;
    }

    ul {
      list-style-type: none;
      margin: 0;
      padding: 0;
      overflow: hidden;
      background-color: #333;
    }

    li {
      float: right;
    }

    li a {
      display: block;
      color: white;
      text-align: center;
      padding: 20px;
      text-decoration: none;
      font-family: "Open Serif", "Arial", sans-serif;
    }

    li a:hover {
      background-color: #111;
    }
    </style>
    </head>
    """
    template += """
    <body>
        <ul>
          <li style="float:left"><a>DESI Survey QA Night {}</a></li>
          <li><a href={}>Last</a></li>
          <li><a href={}>Next</a></li>
          <li><a href={}>Previous</a></li>
          <li><a href={}>First</a></li>
          <li><a href={}>Summary Page</a></li>
        </ul>
    """.format(night, last_str, next_str, prev_str, first_str, summary_str)
    
    template += """
        <div class="flex-container">
                <div class="column middle">
                    <div class="flex-container">
                        <div>{{ skypathplot_script }} {{ skypathplot_div}}</div>
                        <div>{{ exptypecounts_script }} {{ exptypecounts_div }}</div>
                    </div>

                    <div class="flex-container">
                        <div>{{ timeseries_script }} {{ timeseries_div }}</div>
                        <div>{{ overlaidhists_script }} {{ overlaidhists_div }}</div>
                    </div>

                    <div class="flex-container">{{ table_script }}{{ table_div }}</div>
                </div>
            </div>
    </body>

    </html>
    """

    #- Convert to a jinja2.Template object and render HTML
    html = jinja2.Template(template).render(
        skypathplot_script=skypathplot_script, skypathplot_div=skypathplot_div,
        exptypecounts_script=exptypecounts_script, exptypecounts_div=exptypecounts_div,
        timeseries_script=timeseries_script, timeseries_div=timeseries_div,
        overlaidhists_script=overlaidhists_script, overlaidhists_div=overlaidhists_div,
        table_script=table_script, table_div=table_div,
        )

    #- Write output file for this night
    outfile = os.path.join(outdir, 'night-{}.html'.format(night))
    with open(outfile, 'w') as fx:
        fx.write(html)

    print('Wrote {}'.format(outfile))

def get_exptype_counts(exposures, calibs, width=300, height=300, min_border_left=50, min_border_right=50):
    """
    Generate a horizontal bar plot showing the counts for each type of
    exposure grouped by whether they have FLAVOR='science' or PROGRAM='calib'

    ARGS:
        exposures : a table of exposures which only contain those with FLAVOR='science'
        calibs : a table of exposures which only contains those with PROGRAm='calibs'
    Options:
        height, width: height and width in pixels
        min_border_left, min_border_right = set minimum width of surrounding labels (in pixels)
    """
    darks = len(exposures[exposures['PROGRAM'] == 'DARK'])
    grays = len(exposures[exposures['PROGRAM'] == 'GRAY'])
    brights = len(exposures[exposures['PROGRAM'] == 'BRIGHT'])

    arcs = len(calibs[calibs['FLAVOR'] == 'arc'])
    flats = len(calibs[calibs['FLAVOR'] == 'flat'])
    zeroes = len(calibs[calibs['FLAVOR'] == 'zero'])

    types = [('calib', 'ZERO'), ('calib', 'FLAT'), ('calib', 'ARC'),
            ('science', 'BRIGHT'), ('science', 'GRAY'), ('science', 'DARK')]
    counts = np.array([zeroes, flats, arcs, brights, grays, darks])
    COLORS = ['tan', 'orange', 'yellow', 'green', 'blue', 'red']

    src = ColumnDataSource({'types':types, 'counts':counts})

    p = bk.figure(width=width, height=height,
                  y_range=FactorRange(*types), title='Exposure Type Counts',
                  toolbar_location=None, min_border_left=min_border_left, min_border_right=min_border_right)
    p.hbar(y='types', right='counts', left=0, height=0.5, line_color='white',
           fill_color=factor_cmap('types', palette=COLORS, factors=types), source=src)


    labels = LabelSet(x='counts', y='types', text='counts', level='glyph', source=src,
                      render_mode='canvas', x_offset=5, y_offset=-7,
                      text_color='gray', text_font='tahoma', text_font_size='8pt')
    p.add_layout(labels)

    p.ygrid.grid_line_color=None
    p.xaxis.axis_label = 'label'
    p.xaxis.axis_label_text_color = '#ffffff'

    return p


def get_night_link(night, exposures):
    '''Gets the href string for the previous night and the next night for a given nightly page.
        Input:
            night: night value, string
            exposures: Table with columns...
        Output: [previous page href, next page href], elements are strings'''
    unique_nights = list(np.unique(exposures['NIGHT']))
    ind = unique_nights.index(night)

    if ind == 0:
        prev_night = night
        next_night = unique_nights[ind+1]

    if ind == (len(unique_nights)-1):
        prev_night = unique_nights[ind-1]
        next_night = night

    if ind != 0 and ind != (len(unique_nights)-1):
        prev_night = unique_nights[ind-1]
        next_night = unique_nights[ind+1]

    prev_str = "night-{}.html".format(prev_night)
    next_str = "night-{}.html".format(next_night)

    return [prev_str, next_str]
