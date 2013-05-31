var appName = 'XLSXConverter';

/**
 * Transform the currently open workbook into json.
 */
function workbookToJson() {
  var sheets = SpreadsheetApp.getActiveSpreadsheet().getSheets();
  var output = {};
  _.each(sheets, function(sheet, sheetIdx) {
    var outSheet = {};
    var sheetArrays = sheet.getDataRange().getValues();
    var columnHeaders = sheetArrays[0];
    _.each(columnHeaders, function(columnHeader){
      if(columnHeader === '_rowNum') {
        throw new Error("_rowNum is not a valid column header.");
      }
    });
    var outSheet =  _.map(sheetArrays.slice(1), function(row, rowIdx) {
      //_rowNum is added to support better error messages.
      var outRow = {};//Object.create({ __rowNum__ : (rowIdx + 1) });
      outRow.prototype = { __rowNum__ : (rowIdx + 1) };
      _.each(row, function(val, valIdx) {
          outRow[columnHeaders[valIdx]] = val;
      });
      return outRow;
    });
    output[sheet.getName()] = outSheet;
  });
  return output;
}

/**
 * Converts the spreadsheet to an ODK form by serializing it into json
 * and sending it to a server.
 */
function convert() {
  var myapp = UiApp.createApplication().setTitle(appName);
  var mypanel = myapp.createVerticalPanel();
  myapp.add(mypanel);
  try {
    var processedJSON = XLSXConverter.processJSONWorkbook(workbookToJson());
    _.each(XLSXConverter.getWarnings(), function(warning) {
      //TODO: Add option to parse the warnings and error strings,
      // and highlight the rows with errors.
      mypanel.add(myapp.createHTML("Warning: " + warning));
    });
    var file = DocsList.createFile("formDef.json", JSON.stringify(processedJSON,
                                                                  function(key, value){
                                                                    //Replacer function to leave out prototypes
                                                                    if(key !== "prototype"){
                                                                      return value;
                                                                    }
                                                                  },2));
    mypanel.add(myapp.createAnchor("Download JSON", file.getUrl()));
  } catch(e){
    mypanel.add(myapp.createHTML("ERROR:"));
    mypanel.add(myapp.createHTML(String(e)));
    throw e;
  }
  SpreadsheetApp.getActiveSpreadsheet().show(myapp);
  return;
};

function showInfoPopup(responseJson) {
  var app = UiApp.createApplication().setTitle(appName + ' Info');
  var mypanel = app.createVerticalPanel();
  app.add(mypanel);
  mypanel.add(app.createHTML(appName + " is a tool for generating forms for use with ODK Survey, and other applications to come."));
  var docLink = app.createAnchor("Syntax documentation", "http://code.google.com/p/opendatakit/wiki/XLSForm2Docs");
  app.add(docLink);
  //TODO: Add settings for choosing conversion target and turning on/off spreadsheet highlighting.
  SpreadsheetApp.getActiveSpreadsheet().show(app);
}

/**
 * Adds a custom menu to the active spreadsheet.
 * The onOpen() function, when defined, is automatically invoked whenever the
 * spreadsheet is opened.
 * For more information on using the Spreadsheet API, see
 * https://developers.google.com/apps-script/service_spreadsheet
 */
function onOpen() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet();
  var entries = [{
    name : "Convert",
    functionName : "convert"
  }, {
    name : "Settings",
    functionName : "showInfoPopup"
  }];
  sheet.addMenu(appName, entries);
};
