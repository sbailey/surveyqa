# Style Guide

This is a non-exhaustive list of style suggestions, but covers a few topics
that Stephen cares about and aren't always common...

## Always include docstrings

```
def fitline(x, y):
    """
    Fits y = a*x + b and returns (a, b)
    
    Args:
        x : array of floats
        y : array of floats, same length as x

    Returns tuple of coefficients (a, b)
    """
    # code...
```

Get in the habit of writing the docstring at the same time as you write a function or class,
not as a separate "now I'm going to write documentation" step.  Users of your function (including
your future self) should be able to know how to call your function and what it returns by reading
the docstring, without having to read the code to tell the types of the inputs and what they mean.

Also see https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings

## Separate I/O, calculations, and plotting

```
#- Calculation
def calc_tiles_vs_time(exposures):
    """TODO: docstring..."""
    ...
    return time, ntiles

#- Plotting
def plot_progress(time, ntiles):
    """TODO: docstring..."""
    fig = bokeh.plotting.figure()
    ...
    return fig

#- I/O
exposures = Table.read('exposures.fits')

time, ntiles = calc_tiles_vs_time(exposures)
fig = plot_progress(time, ntiles)

# write figure to HTML file...
```

Benefits:
  * Separates potentially expensive calculations from faster plotting that you may want
    to iterate on many times while tweaking style
  * Allows you to reuse plotting code (e.g. in a script to write a file vs. a notebook to display)
  * Simplifies testing (calculation doesn't do I/O or leave behind unnecessary plot files)
  * Easier to swap other data formats or data sources

## Use git branches and GitHub pull requests

Make a branch:
```
git checkout -b my_new_feature
```

Add your code then commit:
```
git commit -am "Adds my new feature"
```

Push your branch to GitHub:
```
git push origin my_new_feature
```

Open a "pull request" at https://github.com/sbailey/surveyqa for others to review your code
and comment *before* it gets merged into master.

Getting bogged down on this feature?  Save your work and switch to another branch to continue
on a different feature:
```
git commit -am "work in progress on my new feature"
git checkout master
git checkout -b another_feature
# do work, switch back when ready...
git checkout my_new_feature
```

Get updates from others after their pull requests have been merged:
```
git checkout master
git pull
```

If you are using a GUI/IDE interface to git, there should be the equivalent of all of these steps.

Aim for 1 feature per pull request rather than mega-dumps of lots of work.  This makes it easier to merge
in the pieces that are ready to go, while separately addressing any problematic pieces without blocking
the others.

## Avoid state when possible

Treat functions like mathematical functions, where the same inputs always produce the same
outputs and don't depend upon the state of something else that may have changed (or not) earlier
in the program.  This is also true (and more commonly problematic) for classes: try to avoid
having the results of a member function depend upon the past history of what was done with an object.

This makes the code easier to test and debug.  It also makes it *much* easier to
parallelize, though that benefit probably doesn't apply to this particular project.

If a function does depend upon the state of something other than its direct inputs, or if it changes
any of its inputs (e.g. sorting or filtering a table), make that very very clear in the docstring.

## Further reading

* https://google.github.io/styleguide/pyguide.html
* https://desi.lbl.gov/trac/wiki/Computing/Software/Guidelines
* https://desi.lbl.gov/trac/wiki/Computing/UsingGit



