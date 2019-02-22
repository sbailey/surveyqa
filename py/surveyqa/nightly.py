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

def get_plot1(exposures, tiles, width=300, height=200):
    '''
    Placeholder for generating some plot
    '''
    fig = bk.figure(width=width, height=height)
    x = np.sort(np.random.uniform(0, 1, size=20))
    y = np.random.uniform(size=len(x))
    fig.line(x, y)
    fig.circle(x, y, color='darkred')
    fig.yaxis.axis_label = 'blat'
    return fig

def get_plot2(exposures, tiles, width=300, height=200):
    '''
    Placeholder for generating some plot
    '''
    fig = bk.figure(width=width, height=height)
    x = np.sort(np.random.uniform(0, 1, size=20))
    y = np.random.uniform(size=len(x))
    fig.line(x, y)
    fig.circle(x, y, color='darkred')
    fig.yaxis.axis_label = 'foo'
    return fig

def makeplots(night, exposures, tiles, outdir):
    '''
    Generates summary plots for the DESI survey QA

    Args:
        exposures: Table of exposures with columns ...
        tiles: Table of tile locations with columns ...
        outdir: directory to write the files

    Writes outdir/night-*.html
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

        <h1>Night {}</h1>
    """.format(night)

    template += """
        {{ script1 }}
    
        {{ div1 }}

        {{ script2 }}
    
        {{ div2 }}

        <p>etc.  Add more plots...</p>
    
    </body>

    </html>
    """

    exposures = exposures[exposures['NIGHT'] == night]

    outfile = os.path.join(outdir, 'night-{}.html'.format(night))

    plot1 = get_plot1(exposures, tiles)
    script1, div1 = components(plot1)

    plot2 = get_plot2(exposures, tiles)
    script2, div2 = components(plot2)

    #- Convert to a jinja2.Template object and render HTML
    html = jinja2.Template(template).render(
        script1=script1, div1=div1,
        script2=script2, div2=div2,
        )

    #- Write output file for this night
    with open(outfile, 'w') as fx:
        fx.write(html)

    print('Wrote {}'.format(outfile))
    
    