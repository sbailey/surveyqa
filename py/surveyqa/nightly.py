"""
Plots for daily DESI observing
"""

from __future__ import absolute_import, division, print_function
import sys, os
import numpy as np

import jinja2
from bokeh.embed import components
import bokeh
import bokeh.plotting as bk
from bokeh.models import ColumnDataSource

from astropy.time import Time
from bokeh.models import HoverTool, ColumnDataSource
from bokeh.layouts import gridplot
from astropy.table import join


def find_night(exposures, night):
    """
    Generates a subtable of exposures corresponding to data from a single night N and adds columns DATETIME and MJD_hour
    
    ARGS:
        exposures : Table of exposures with columns
        night : A string representing a single value in the NIGHT column of the EXPOSURES table
    """
    exposures = exposures[exposures['NIGHT'] == night]

    mjds = Time(np.array(exposures['MJD']), format='mjd')
    exposures['DATETIME'] = mjds
    mjd_ints = np.array(exposures['MJD']).astype(int)
    mjd_hours = (np.array(exposures['MJD']) - mjd_ints) * 24
    exposures['MJD_hour'] = mjd_hours
    return exposures


def get_timeseries(exposures, tiles, name):
    '''
    Generates times and values arrays for column `name`
    '''
    x = np.array(exposures['MJD_hour'])
    y = np.array(exposures[name])
    return x, y


def plot_timeseries(times, values, name, color, x_range=None):
    '''
    Plots VALUES vs. TIMES

    Args:
        times : array of times in hours
        values : array of values to plot
        name : string name of this timeseries
        color : color for plotted data points
        x_range : a range of x values to link multiple plots together

    Returns bokeh Figure object
    '''
    fig = bk.figure(width=400, height=250, toolbar_location=None, x_range=x_range, active_scroll='wheel_zoom')
    fig.line(times, values)
    fig.circle(times, values, line_color=color, fill_color='white', size=6, line_width=2)
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
    from bokeh.models.widgets.tables import DataTable, TableColumn
    
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

    #- Filter exposures to just this night and adds columns DATETIME and MJD_hour
    #- Note: this replaces local variable but does not modify original input (good)
    exposures = find_night(exposures, night)

    #- Get timeseries plots for several variables
    x, y = get_timeseries(exposures, tiles, 'AIRMASS')
    airmass = plot_timeseries(x, y, 'AIRMASS', 'darkorange')

    x, y = get_timeseries(exposures, tiles, 'SEEING')
    seeing = plot_timeseries(x, y, 'SEEING', 'navy', x_range=airmass.x_range)

    x, y = get_timeseries(exposures, tiles, 'EXPTIME')
    exptime = plot_timeseries(x, y, 'EXPTIME', 'green', x_range=airmass.x_range)


    #- Convert these to the components to include in the HTML
    timeseries_script, timeseries_div = components(bk.Column(airmass, seeing, exptime))

    #making the nightly table of values
    nightlytable = get_nightlytable(exposures)
    table_script, table_div = components(nightlytable)
    
    #adding in the skyplot components
    skypathplot = get_skypathplot(exposures, tiles, night)
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
    .flex-container {
        display: flex;
        flex-flow: row wrap;
        justify-content: space-between;
    }
    </style>
    </head>
    """
    template += """
    <body>

        <h1>Night {}</h1>
    """.format(night)

    template += """
        <div class="flex-container">
            <div>{{ skypathplot_script }} {{ skypathplot_div}}</div>
            <div> NIGHTLY TOTALS BAR CHART HERE </div>
        </div>
        
        <div class="flex-container">
            <div>{{ timeseries_script }} {{ timeseries_div }}</div>
            <div> NIGHT VS. SUMMARY HISTOGRAMS HERE </div>
        </div>
        
        <p>Night Summary Table: </p>
        
        {{ table_script }} 
        
        {{ table_div }}
        
        <p>etc.  Add more plots...</p>
    
    </body>

    </html>
    """

    #- Convert to a jinja2.Template object and render HTML
    html = jinja2.Template(template).render(
        skypathplot_script=skypathplot_script, skypathplot_div=skypathplot_div,
        timeseries_script=timeseries_script, timeseries_div=timeseries_div,
        table_script=table_script, table_div=table_div
        )

    #- Write output file for this night
    outfile = os.path.join(outdir, 'night-{}.html'.format(night))
    with open(outfile, 'w') as fx:
        fx.write(html)

    print('Wrote {}'.format(outfile))
    

    
def get_skypathplot(exposures, tiles, night, width=600, height=300):
    """
    Generate a plot which maps the location of tiles observed on NIGHT
    
    ARGS:
        exposures : Table of exposures with columns ...
        tiles: Table of tile locations with columns ...
        night : String representing a single value in the NIGHT column of the EXPOSURES table
        
    Options:
        height, width = height and width of the graph in pixels
        
    Returns a bokeh figure object
    """
    exposures = find_night(exposures, night)
    
    #merges tiles data for all exposures on a single night N
    tiles_and_exps = join(exposures, tiles['STAR_DENSITY', 'EXPOSEFAC', 'OBSCONDITIONS', 'TILEID'], keys='TILEID')
    
    #converts data format into ColumnDataSource
    src = ColumnDataSource(data={'RA':np.array(tiles_and_exps['RA']), 
                                 'DEC':np.array(tiles_and_exps['DEC']), 
                                 'EXPID':np.array(tiles_and_exps['EXPID'])})
    
    #plot options
    night_name = exposures['NIGHT'][0]
    string_date = night_name[:4] + "-" + night_name[4:6] + "-" + night_name[6:]

    fig = bk.figure(width=width, height=height, title='Tiles observed on ' + string_date)
    fig.yaxis.axis_label = 'Declination'
    fig.xaxis.axis_label = 'Right Ascension'

    #plots of all tiles
    unobs = fig.circle(tiles['RA'], tiles['DEC'], color='gray', size=1)

    #plots tiles observed on NIGHT
    obs = fig.circle('RA', 'DEC', color='blue', size=3, legend='Observed', source=src)
    fig.line(src.data['RA'], src.data['DEC'], color='black')

    #adds hover tool
    TOOLTIPS = [("(RA, DEC)", "($x, $y)"), ("EXPID", "@EXPID")]
    obs_hover = HoverTool(renderers = [obs], tooltips=TOOLTIPS)
    fig.add_tools(obs_hover)

    #shows plot
    return fig
    