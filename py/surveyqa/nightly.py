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

def get_timeseries(exposures, tiles, name):
    '''
    PLACEHOLDER CODE: return (times, values) for column `name`
    '''
    #- Replace this with actual code to extract something meaningful...
    x = np.linspace(0, 10)
    y = np.random.normal(size=len(x))
    return x, y

def plot_timeseries(times, values, name, x_range=None):
    '''
    PLACEHOLDER CODE: plots values vs. times

    Args:
        times : array of times (TODO: what units should these be?)
        values : array of values to plot
        name : string name of this timeseries

    Returns bokeh Figure object
    '''
    fig = bk.figure(width=400, height=100, toolbar_location=None, x_range=x_range, active_scroll='wheel_zoom')
    fig.line(times, values)
    fig.circle(times, values, line_color='darkorange', fill_color='white', size=6, line_width=2)
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
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...
        outdir: directory to write the files

    Writes outdir/night-*.html
    '''

    #- Filter exposures to just this night
    #- Note: this replaces local variable but does not modify original input (good)
    exposures = exposures[exposures['NIGHT'] == night]

    #- Get timeseries plots for several variables
    x, y = get_timeseries(exposures, tiles, 'AIRMASS')
    plot1 = plot_timeseries(x, y, 'AIRMASS')

    x, y = get_timeseries(exposures, tiles, 'SEEING')
    plot2 = plot_timeseries(x, y, 'SEEING', x_range=plot1.x_range)

    x, y = get_timeseries(exposures, tiles, 'EXPTIME')
    plot3 = plot_timeseries(x, y, 'EXPTIME', x_range=plot1.x_range)

    #- Convert these to the components to include in the HTML
    timeseries_script, timeseries_div = components(bk.Column(plot1, plot2, plot3))

    #making the nightly table of values
    nightlytable = get_nightlytable(exposures)
    table_script, table_div = components(nightlytable)
    
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
            <div> SKY PATH PLOT HERE </div>
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
        timeseries_script=timeseries_script, timeseries_div=timeseries_div,
        table_script=table_script, table_div=table_div
        )

    #- Write output file for this night
    outfile = os.path.join(outdir, 'night-{}.html'.format(night))
    with open(outfile, 'w') as fx:
        fx.write(html)

    print('Wrote {}'.format(outfile))
    
