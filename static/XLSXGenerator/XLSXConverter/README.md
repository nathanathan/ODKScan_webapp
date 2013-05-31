XLSXConverter
-------------

This is a webpage that converts XLSX files into json form defintions for ODK Survey.
It is avaialbe online [here](http://uw-ictd.github.com/XLSXConverter/) via this repo's gh-pages branch.

These are some potential uses for it:

- Doing xlsx conversion within the ODK Survey code enabling users to simply drag XLSX files onto the sdcard
without converting them through a separate application.
[The FreeSpeech interview chooser](https://github.com/UW-ICTD/FreeSpeech/blob/master/boilerplate/chooserMain.js)
does automatic xlsx conversion, and it could potentially be adapted for ODK Survey.
- Offline conversions (just [download the zip](https://github.com/UW-ICTD/XLSXConverter/archive/gh-pages.zip) and open the index.html whenever you need it).
- The converter could be included in a web interface that uploads form defs to ODK Aggregate.

ODK Survey preview functionality could be added by saving the formDef json in browser storage.
ODK Survey will then be able to retrieve the json if it is hosted under the same domain.

XLSXConverter uses the [js-xlsx library](https://github.com/Niggler/js-xlsx) which is fairly new,
and I have encountered a few bugs in it. However, it is very well supported,
all the bugs I've reported have been fixed in about a day.
[The js-xlsx demo page](http://niggler.github.com/js-xlsx/)
provides a Litmus test of whether a bug is occuring in XLSXConverter or js-xlsx.

Google appscript support:
-------------------------

The `wrapper.gs` file can be used in conjunction with `underscore.js` and `XLSXConverter.js`
to create a script available inside google spreadsheets for doing conversions.
There is an example of this available [here](https://docs.google.com/spreadsheet/ccc?key=0Ak1svGcuI9iqdDRlbGdBbndBTm9VeVdjOURBdDNORnc&usp=sharing).
All the scripts need to be renamed to have the `.gs` extension,
and google appscript doesn't seem to have a clear way of managing script dependencies,
so it is necessairy to import the scripts in the following order: 

1. wrapper
2. underscore
3. XLSXConverter

Other options include putting all the scripts into a single file,
and messing around with the experimental "Manage Libraries" feature.

If ODK Survey were extended with the ability to fetch documents from google docs,
it would be possible to add a preview link.
