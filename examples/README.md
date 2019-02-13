Getting Started
===============

### Request a DESI wiki account

https://desi.lbl.gov/trac/register

This gives you access to DESI collaboration information.


## Install Anaconda Python on your computer

https://www.anaconda.com/distribution/

Create an "Anaconda environment", which allows you to keep your DESI work
independent of other work on your laptop.
```
conda create -n desi python=3.6 numpy scipy astropy bokeh matplotlib=2.1.2 jupyterlab
```

To use switch to this environment, you'll need to run this every time
you open a new terminal window:
```
conda activate desi
```
That may seems like a pain, but it allows us to install or upgrade arbitrary
packages in that environment without risking the stable environment that you
use for your classes.

## Start a jupyter lab notebook

```
jupyter lab 00_GettingStarted.ipynb
```

## Example files

This directory contains some example data files:

  * `exposures.fits` : 200 simulated days of observations
  * `desi-tiles.fits` : pre-defined locations on the sky (tiles) to point
    the telescope.

Eventually these data will come from elsewhere, but they are included here
for testing and development without requiring external DESI dependencies (yet).

