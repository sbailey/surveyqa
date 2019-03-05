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
        TableColumn(field='calib', title='Calibrations'),
    ]

    summary_table = DataTable(source=source, columns=columns, sortable=True)
    
    return summary_table

def get_surveyprogress(exposures, tiles, width=300, height=300):
    '''
    Generates a plot of survey progress vs. time

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...

    Options:
        width, height: plot width and height in pixels

    Returns bokeh Figure object

    NOTE: This is just a placeholder.  It doesn't actually plot survey progress yet
    '''
    fig = bk.figure(width=width, height=height)
    x = np.linspace(0, 100)
    y = np.cumsum(np.random.uniform(size=len(x)))
    fig.line(x, y)
    fig.title.text = 'Placeholder: Survey Progress'

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
    .flex-container {
        display: flex;
        flex-direction: row;
        flex-flow: row wrap;    
    }
    </style>
    </head>
    """
    
    template += """
    <body>

        <h1>DESI Survey QA</h1>
        <p>Through night {}</p>
    """.format(max(exposures['NIGHT']))
    
    template += """
        <p>Progress: </p>
        <div class="flex-container">
            <div>{{ skyplot_script }} {{ skyplot_div }}</div>
            <div>{{ progress_script }} {{ progress_div }}</div>
            <div>{{ progress_script_1 }} {{ progress_div_1 }}</div>
        </div>
        
        <p>Histograms: </p>
        
        <div class="flex-container">
            <div>HISTOGRAMS GO HERE</div>
            <div>AND HERE</div>
            <div>AND HERE</div>
        </div>
        
        <p>Summary Table: </p>
        
        {{ summarytable_script }}
        
        {{ summarytable_div }}

        <p>etc.  Add more plots...</p>

    </body>

    </html>
    """

    skyplot = get_skyplot(exposures, tiles)
    skyplot_script, skyplot_div = components(skyplot)

    progressplot = get_surveyprogress(exposures, tiles)
    progress_script, progress_div = components(progressplot)
    
    progressplot_1 = get_surveyprogress(exposures, tiles)
    progress_script_1, progress_div_1 = components(progressplot_1)
    
    summarytable = get_summarytable(exposures)
    summarytable_script, summarytable_div = components(summarytable)

    #- Convert to a jinja2.Template object and render HTML
    html = jinja2.Template(template).render(
        skyplot_script=skyplot_script, skyplot_div=skyplot_div,
        progress_script=progress_script, progress_div=progress_div,
        progress_script_1=progress_script_1, progress_div_1=progress_div_1,
        summarytable_script=summarytable_script, summarytable_div=summarytable_div, 
        )
    
    outfile = os.path.join(outdir, 'summary.html')
    with open(outfile, 'w') as fx:
        fx.write(html)
    
    print('Wrote summary QA to {}'.format(outfile))
