"""
Summary plots of DESI survey progress and QA
"""

import sys, os
import numpy as np

import jinja2
from bokeh.embed import components
import bokeh
import bokeh.plotting as bk

def get_skyplot(exposures, tiles, width=600, height=300):
    '''
    Generates sky plot of DESI survey tiles and progress

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...

    Options:
        width, height: plot width and height in pixels

    Returns bokeh Figure object
    
    NOTE: This is just a placeholder.  Replace it with something better.
    '''
    fig = bk.figure(width=width, height=height)
    fig.circle(tiles['RA'], tiles['DEC'], color='gray', size=1)

    observed = np.in1d(tiles['TILEID'], exposures['TILEID'])
    fig.circle(tiles['RA'][observed], tiles['DEC'][observed], color='red', size=3)
    fig.xaxis.axis_label = 'RA [degrees]'
    fig.yaxis.axis_label = 'Declination [degrees]'
    fig.title.text = 'Placeholder: Observed Tiles'

    return fig

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
    <script 
        src="https://cdn.pydata.org/bokeh/release/bokeh-{version}.min.js"
    ></script>
    """.format(version=bokeh.__version__)

    #- Now add the HTML body with template placeholders for plots
    template = header + """
    <body>

        <h1>DESI Survey QA</h1>
        <p>Through night {}</p>
    """.format(max(exposures['NIGHT']))
    
    template += """
    
        {{ skyplot_script }}
    
        {{ skyplot_div }}

        {{ progress_script }}
    
        {{ progress_div }}

        <p>etc.  Add more plots...</p>

    </body>

    </html>
    """

    skyplot = get_skyplot(exposures, tiles)
    skyplot_script, skyplot_div = components(skyplot)

    progressplot = get_surveyprogress(exposures, tiles)
    progress_script, progress_div = components(progressplot)

    #- Convert to a jinja2.Template object and render HTML
    html = jinja2.Template(template).render(
        skyplot_script=skyplot_script, skyplot_div=skyplot_div,
        progress_script=progress_script, progress_div=progress_div,
        )
    
    outfile = os.path.join(outdir, 'summary.html')
    with open(outfile, 'w') as fx:
        fx.write(html)
    
    print('Wrote summary QA to {}'.format(outfile))
