ODK Scan XLSX Form generator
--------------------------------------------------------------------------------

This is a client-side javascript application for generating scannable paper forms
from XLSX spreadsheets. Scannable in the sense that the app generates a template
that can be used with ODK Scan to automatically read which bubbles are filled in
like a scantron test.

There is some documentation [here](http://uw-ictd.github.io/XLSXGenerator/documentation.html)

Developer info
--------------------------------------------------------------------------------

### Overview:

XLSX Generator is all client side JavaScript. There is no server component,
so you can download and open it from your filesystem.

The pipeline is as followes.
The XLSX file is converted to JSON with some basic processing to nest
groups and parse type parameters (in XLSXConverter).
Next, that JSON is preprocessed in app.js script then
fed into Handlebars templates (in index.html) to generate the form's HTML structure.
After the HTML is rendered,
jQuery is used to construct the template.json based on it's layout,
and html2canvas is used to draw the form.jpg.
Finally, all the json and jpgs for all the pages
gets zipped into a single file that is made available for download.

### Testing:

The test.html page will generate a form from the scanExample.xlsx file in this
repo and compare it with the output in the testExpectedOutput folder.
It will print a json diff and a visual form image diff at the bottom of the page.
*However*, if you run the test in FireFox, you will see some differences,
because the expected output was generated in Chrome. Furthermore, you may see minor
1px difference in positioning with different window sizes.

### Additional Notes:

* Multiple segments per field in the JSON output appears to be unnecessairy.