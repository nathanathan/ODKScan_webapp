//TODO: This is getting pretty divergent from the orignal XLSX converter, consider renaming.

(function(){
    
    // Establish the root object, `window` in the browser, or `global` on the server.
    var root = this;
    
    var _ = root._;
    
    var warnings = {
        __warnings__: [],
        warn: function(rowNum, message){
            //rowNum is incremented by 1 because in excel it is not 0 based
            //there might be a better place to do this.
            this.__warnings__.push("[row:"+ (rowNum + 1) +"] " + message);
        },
        clear: function(){
            this.__warnings__ = [];
        },
        toArray: function(){
            return this.__warnings__;
        }
    };
    
    var XLSXError = function(rowNum, message){
        //rowNum is incremented by 1 because in excel it is not 0 based
        //there might be a better place to do this
        return Error("[row:"+ (rowNum + 1) +"] " + message);
    };
    /*
    Extend the given object with any number of additional objects.
    If the objects have matching keys, the values of those keys will be
    recursively merged, either by extending eachother if any are objects,
    or by being combined into an array if none are objects.
    */
    var recursiveExtend = function(obj) {
        _.each(Array.prototype.slice.call(arguments, 1), function(source) {
            if (source) {
                for (var prop in source) {
                    if (prop in obj) {
                        if (_.isObject(obj[prop]) || _.isObject(source[prop])) {
                            //If one of the values is not an object,
                            //put it in an object under the key "default"
                            //so it can be merged.
                            if(!_.isObject(obj[prop])){
                                obj[prop] = {"default" : obj[prop] };
                            }
                            if(!_.isObject(source[prop])){
                                source[prop] = {"default" : source[prop] };
                            }
                            obj[prop] = recursiveExtend(obj[prop], source[prop]);
                        } else {
                            //If neither value is an object put them in an array.
                            obj[prop] = [].concat(obj[prop]).concat(source[prop]);
                        }
                    } else {
                        obj[prop] = source[prop];
                    }
                }
            }
        });
        return obj;
    };
    /*
    [a,b,c] => {a:{b:c}}
    */
    var listToNestedDict = function(list){
        var outObj = {};
        if(list.length > 1){
            outObj[list[0]] = listToNestedDict(list.slice(1));
            return outObj;
        } else {
            return list[0];
        }
    };
    /*
    Construct a JSON object from JSON paths in the headers.
    For now only dot notation is supported.
    For example:
    {"text.english": "hello", "text.french" : "bonjour"}
    becomes
    {"text": {"english": "hello", "french" : "bonjour"}.
    */
    var groupColumnHeaders = function(row) {
        var outRow = Object.create(row.__proto__ || row.prototype);
        _.each(row, function(value, columnHeader){
            var chComponents = columnHeader.split('.');
            outRow = recursiveExtend(outRow, listToNestedDict(chComponents.concat(value)));
        });
        return outRow;
    };
    
    var parsePrompts = function(sheet){
        var type_regex = /^(\w+)\s*(\S.*)?\s*$/;
        var outSheet = [];
        var outArrayStack = [{prompts : outSheet}];
        _.each(sheet, function(row){
            var curStack = outArrayStack[outArrayStack.length - 1].prompts;
            var typeParse, typeControl, typeParam;
            var outRow = row;
            //Parse the type column:
            if('type' in outRow) {
                typeParse = outRow.type.match(type_regex);
                if(typeParse && typeParse.length > 0) {
                    typeControl = typeParse[typeParse.length - 2];
                    typeParam = typeParse[typeParse.length - 1];
                    if(typeControl === "begin"){
                        outRow.prompts = [];
                        outRow.type = typeParam;
                        //Second type parse is probably not needed, it's just
                        //there incase begin ____ statements ever need a parameter
                        var secondTypeParse = outRow.type.match(type_regex);
                        if(secondTypeParse && secondTypeParse.length > 2) {
                            outRow.type = secondTypeParse[1];
                            outRow.param = secondTypeParse[2];
                        }
                        outArrayStack.push(outRow);
                    } else if(typeControl === "end"){
                        if(outArrayStack.length <= 1){
                            throw XLSXError(row.__rowNum__, "Unmatched end statement.");
                        }
                        outArrayStack.pop();
                        return;
                    } else {
                        outRow.type = typeControl;
                        outRow.param = typeParam;
                    }
                }
            } else {
                //Skip rows without types
                return;
            }
            curStack.push(outRow);
        });
        if(outArrayStack.length > 1) {
            throw XLSXError(outArrayStack.pop().__rowNum__, "Unmatched begin statement.");
        }
        return outSheet;
    };
    
    //Remove carriage returns, trim values.
    var cleanValues = function(row){
        var outRow = Object.create(row.__proto__ || row.prototype);
        _.each(row, function(value, key){
            if(_.isString(value)){
                value = value.replace(/\r/g, "");
                value = value.trim();
            }
            outRow[key] = value;
        });
        return outRow;
    };
    
    var validateNames = function(fields){
        var nameMap = {};
        (function recurse(fields){
            _.each(fields, function(field) {
                if('prompts' in field){
                    recurse(field.prompts);
                    return;
                }
                if(field.type.match(/markup|note|pagebreak/)) {
                    //Don't need to validate these...
                    return;
                }
                if(!('name' in field)){
                    warnings.warn(field.__rowNum__, "Field without a name.");
                    return;
                }
                if(field.name in nameMap) {
                    throw XLSXError(field.__rowNum__, "Duplicate name: " + field.name);
                }
                if(!("" + field.name).match(/^[a-zA-Z][a-zA-Z_0-9]*/)){
                    warnings.warn(field.__rowNum__, "Bad XML Name: " +
                        field.name +
                        ". You will not be able to export to ODK Collect.");
                }
                nameMap[field.name] = field;
            });
        }(fields));
    };

    root.XLSXConverter = {
        processJSONWorkbook : function(wbJson){
            warnings.clear();
            _.each(wbJson, function(sheet, sheetName){
                _.each(sheet, function(row, rowIdx){
                    var reRow = groupColumnHeaders(cleanValues(row));
                    sheet[rowIdx] = reRow;
                });
            });
            
            //Process sheet names by converting from json paths to nested objects.
            var tempWb = {};
            _.each(wbJson, function(sheet, sheetName){
                var tokens = sheetName.split('.');
                var sheetObj = {};
                sheetObj[tokens[0]] = listToNestedDict(tokens.slice(1).concat([sheet]));
                recursiveExtend(tempWb, sheetObj);
            });
            wbJson = tempWb;
            
            if(!('survey' in wbJson)){
                throw Error("Missing survey sheet");
            }

            wbJson['survey'] = parsePrompts(wbJson['survey']);
            
            validateNames(wbJson['survey']);
            
            if('choices' in wbJson){
                wbJson['choices'] = _.groupBy(wbJson['choices'], 'list_name');
            }
            
            return wbJson;
        },
        //Returns the warnings from the last workbook processed.
        getWarnings: function(){
            return warnings.toArray();
        }
    };
}).call(this);
