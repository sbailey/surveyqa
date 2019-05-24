import os

def make_calendar_html(nights_sub, outdir):
    html = """
    <!doctype html>
    <html lang="en">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

    <link rel="stylesheet" href="offline_files/bootstrap.css">
    <script src="offline_files/jquery_min.js"></script>
    <script src="offline_files/popper_min.js"></script>
    <script src="offline_files/bootstrap.js"></script>
    <link rel="stylesheet" href="offline_files/bootstrap-year-calendar.css">
    <script src="offline_files/bootstrap-year-calendar.js"></script>

    </head>
    <body>
      <button type="button" onclick="
        window.open('summary.html');
      ">Summary Page</button>
    <div class="container">
    <div class="calendar"></div>
    </div>
    <script>

    var list = {};
    """

    # Add an entry to the list within the calendar html. Every entry in
    # the list is rendered within a green bubble.
    for night in nights_sub:
        html += """list[(new Date({year}, {month}, {day}))] = 1;
        """.format(year = night[0:4], month = int(night[4:6])-1, day = night[6:])

    # Rendering of each entry of the list
    html += """
    $('.calendar').calendar({
    customDayRenderer: function(element, date) {
    if (date in list) {
    $(element).css('background-color', 'green');
    $(element).css('color', 'white');
    $(element).css('border-radius', '10px');
    $(element).css('opacity', '0.6');
    }
    },
    dataSource: [
    """

    # Add each night into the dataSource, to let the calendar know that there
    # is an event present on the night. The event tag is white to hide it, and just
    # display the rengering above.
    id = 0
    for night in nights_sub:
        html += """
        {{
        id : {id},
        name : "{filename}",
        startDate : new Date({year}, {month}, {day}),
        endDate : new Date({year}, {month}, {day}),
        color: "white",
        }},
        """.format(id = id, filename = "night-"+str(night)+".html", year = night[0:4], month = int(night[4:6])-1, day = night[6:])
        id += 1

    # When clicking a day, check if there is an event present, and if one is present,
    # open the filename associated with their 'name' field
    html += """
    ],
    clickDay: function(e) {
    if(e.events.length > 0) {
    window.open(e.events[0].name);
    }
    },
    });
    </script>
    </body>
    </html>
    """

    outfile = os.path.join(outdir, 'calendar.html')
    with open(outfile, 'w') as fx:
        fx.write(html)
    print('Wrote {}'.format(outfile))
