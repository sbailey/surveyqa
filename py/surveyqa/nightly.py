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
from bokeh.palettes import Spectral6, viridis
from bokeh.transform import factor_cmap, factor_mark, linear_cmap
from bokeh.models.widgets.tables import DataTable, TableColumn
    

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


def get_timeseries(exposures, name):
    """
    Generates times and values arrays for column `name`
    
    ARGS:
        exposures : Table of exposures with columns...
        name : String corresponding to a column in EXPOSURES
    
    Returns numpy array objects
    """
    x = np.array(exposures['TIME'])
    y = np.array(exposures[name])
    
    return x, y


def plot_timeseries(times, values, name, color, x_range=None, title=None, width=400, height=150):
    """
    Plots VALUES vs. TIMES

    ARGS:
        times : array of times in hours
        values : array of values to plot
        name : string name of this timeseries
        color : color for plotted data points
        x_range : a range of x values to link multiple plots together
    
    Options:
        height, width = height and width of the graph in pixels
        x_range = x-axis range of the graph
        title = graph title

    Returns bokeh figure object
    """
    fig = bk.figure(width=width, height=height, toolbar_location=None, 
                    x_axis_type='datetime', x_range=x_range, 
                    active_scroll='wheel_zoom', title=title)
    fig.line(times, values)
    fig.circle(times, values, line_color=color, fill_color='white', size=6, line_width=2)
    
    #- Formatting
    fig.ygrid.grid_line_color = None
    fig.xgrid.grid_line_color = None
    fig.outline_line_color = None
    fig.yaxis.axis_label = name

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
    ))

    columns = [
        TableColumn(field='expid', title='Exposure ID'),
        TableColumn(field='flavor', title='Flavor'),
        TableColumn(field='program', title='Program'),
        TableColumn(field='exptime', title='Exposure Time'),
        TableColumn(field='tileid', title='Tile ID'),  
    ]

    nightly_table = DataTable(source=source, columns=columns, sortable=True)
    
    return nightly_table


def get_skypathplot(exposures, tiles, width=600, height=300):
    """
    Generate a plot which maps the location of tiles observed on NIGHT
    
    ARGS:
        exposures : Table of exposures with columns specific to a single night
        tiles: Table of tile locations with columns ...
    
    Options:
        height, width = height and width of the graph in pixels
        
    Returns a bokeh figure object
    """    
    #- Merges tiles data for all exposures on a single night N
    tiles_and_exps = join(exposures, tiles['STAR_DENSITY', 'EXPOSEFAC', 'OBSCONDITIONS', 'TILEID'], keys='TILEID')
    
    #- Create a linear range object for each element of TIME to use for color mapping
    TIMES = range(len(tiles_and_exps['TIME']))

    #- Converts data format into ColumnDataSource
    src = ColumnDataSource(data={'RA':np.array(tiles_and_exps['RA']), 
                                 'DEC':np.array(tiles_and_exps['DEC']), 
                                 'EXPID':np.array(tiles_and_exps['EXPID']),
                                 'PROGRAM':np.array([str(n) for n in tiles_and_exps['PROGRAM']]),
                                 'TIME':TIMES})
    
    #- Plot options
    night_name = exposures['NIGHT'][0]
    string_date = night_name[:4] + "-" + night_name[4:6] + "-" + night_name[6:]

    fig = bk.figure(width=width, height=height, title='Tiles observed on ' + string_date)
    fig.yaxis.axis_label = 'Declination'
    fig.xaxis.axis_label = 'Right Ascension'

    #- Plots all tiles
    unobs = fig.circle(tiles['RA'], tiles['DEC'], color='gray', size=1)
    
    #- Shape-coding for program
    EXPTYPES = ['DARK', 'GRAY', 'BRIGHT']
    MARKERS = ['hex', 'square', 'triangle']
    shapes = factor_mark(field_name='PROGRAM', markers=MARKERS, factors=EXPTYPES)
    
    #- Color-coding for time of night
    mapper = linear_cmap(field_name='TIME', palette=viridis(len(TIMES)), low=min(TIMES), high=max(TIMES))
    
    #- Plots tiles observed on NIGHT
    obs = fig.scatter('RA', 'DEC', size=8, fill_alpha=0.8, legend='PROGRAM', source=src, marker=shapes, color=mapper)
    fig.line(src.data['RA'], src.data['DEC'], color='navy', alpha=0.4)

    #- Adds hover tool, color bar
    TOOLTIPS = [("(RA, DEC)", "($x, $y)"), ("EXPID", "@EXPID")]
    obs_hover = HoverTool(renderers = [obs], tooltips=TOOLTIPS)
    colorbar = ColorBar(color_mapper=mapper['transform'], width=8,  location=(0,0))
    fig.add_layout(colorbar, 'right')
    fig.add_tools(obs_hover)

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
    #- Separate calibration exposures
    all_exposures = exposures[exposures['PROGRAM'] != 'CALIB']
    all_calibs = exposures[exposures['PROGRAM'] == 'CALIB']

    #- Filter exposures to just this night and adds columns DATETIME and MJD_hour
    exposures = find_night(all_exposures, night)
    calibs = find_night(all_calibs, night)
    
    title='Airmass, Seeing, Exptime vs. Time for {}/{}/{}'.format(night[4:6], night[6:], night[:4])
    #- Get timeseries plots for several variables
    x, y = get_timeseries(exposures, 'AIRMASS')
    airmass = plot_timeseries(x, y, 'AIRMASS', 'green', x_range=None, title=title)

    x, y = get_timeseries(exposures, 'SEEING')
    seeing = plot_timeseries(x, y, 'SEEING', 'navy', x_range=airmass.x_range)

    x, y = get_timeseries(exposures, 'EXPTIME')
    exptime = plot_timeseries(x, y, 'EXPTIME', 'darkorange', x_range=airmass.x_range)

    #- Convert these to the components to include in the HTML
    timeseries_script, timeseries_div = components(bk.Column(airmass, seeing, exptime))

    #making the nightly table of values
    nightlytable = get_nightlytable(exposures)
    table_script, table_div = components(nightlytable)
    
    #adding in the skyplot components
    skypathplot = get_skypathplot(exposures, tiles, width=600, height=300)
    skypathplot_script, skypathplot_div = components(skypathplot)
    
    
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
        padding: 20px;
        text-align: center;
        justify: space-around;
    }
 
    .column {
        float: center;
        padding: 10px
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
            <p>NIGHT: {}</p>
        </div>
    """.format(night)

    template += """
        <div class="flex-container">
                <div class="column side"></div>          
                <div class="column middle">
                    <div class="flex-container">
                        <div>{{ skypathplot_script }} {{ skypathplot_div}}</div>
                        <div>{{ exptypecounts_script }} {{ exptypecounts_div }}</div>
                    </div>    
                    
                    <div class="flex-container">
                        <div>{{ timeseries_script }} {{ timeseries_div }}</div>
                    </div> 

                    <div class="flex-container">{{ table_script }}{{ table_div }}</div>     
                </div>
                <div class="column side"></div>
            </div>
    </body>

    </html>
    """

    #- Convert to a jinja2.Template object and render HTML
    html = jinja2.Template(template).render(
        skypathplot_script=skypathplot_script, skypathplot_div=skypathplot_div,
        exptypecounts_script=exptypecounts_script, exptypecounts_div=exptypecounts_div,
        timeseries_script=timeseries_script, timeseries_div=timeseries_div,
        table_script=table_script, table_div=table_div,
        )

    #- Write output file for this night
    outfile = os.path.join(outdir, 'night-{}.html'.format(night))
    with open(outfile, 'w') as fx:
        fx.write(html)

    print('Wrote {}'.format(outfile))
