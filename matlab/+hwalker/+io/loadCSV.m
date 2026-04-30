function T = loadCSV(filepath)
% hwalker.io.loadCSV  Load an H-Walker firmware CSV into a table.
%
%   T = hwalker.io.loadCSV('/path/to/20260430_Robot_CBJ_TD_level_0_5_walker_high_0.csv')
%
% Handles:
%   - UTF-8 BOM (readtable auto-strips in R2020b+)
%   - Duplicate header rows (Teensy repeats headers periodically)
%   - Units row (second row contains unit strings, not data)
%   - All-whitespace / leading-space column names
%   - Missing time column → synthetic 111 Hz Time_s axis added

    % Read everything as text first so we can inspect and strip header repeats
    opts = detectImportOptions(filepath, ...
        'VariableNamingRule', 'preserve', ...
        'Delimiter', ',');
    opts = setvartype(opts, opts.VariableNames, 'char');
    try
        raw = readtable(filepath, opts);
    catch ME
        error('hwalker:io:readFail', 'Cannot read %s: %s', filepath, ME.message);
    end

    if isempty(raw)
        error('hwalker:io:emptyFile', 'File is empty: %s', filepath);
    end

    % Strip column name whitespace
    raw.Properties.VariableNames = strtrim(raw.Properties.VariableNames);

    % Remove duplicate header rows (first-column value == column name)
    firstColName = raw.Properties.VariableNames{1};
    firstColData = strtrim(raw.(firstColName));
    isDupHeader  = strcmp(firstColData, firstColName);
    if any(isDupHeader) && ~all(isDupHeader)
        raw(isDupHeader, :) = [];
    end

    % Remove units row: if row 1 is entirely non-numeric strings
    if height(raw) >= 2
        row1 = table2cell(raw(1,:));
        nNumeric = sum(cellfun(@(x) ~isnan(str2double(strtrim(char(x)))), row1));
        if nNumeric == 0
            raw(1,:) = [];
        end
    end

    % Convert all columns to double
    varNames = raw.Properties.VariableNames;
    T = table();
    for k = 1:numel(varNames)
        col = raw.(varNames{k});
        if iscell(col)
            vals = cellfun(@(x) str2double(strtrim(char(x))), col);
        else
            vals = str2double(string(col));
        end
        T.(varNames{k}) = vals;
    end

    % Add synthetic time axis if no time column present
    timeColsKnown = {'Time_ms','time_ms','Time_s','Time','time','Timestamp'};
    if ~any(ismember(T.Properties.VariableNames, timeColsKnown))
        T.Time_s = (0:height(T)-1)' / 111.0;
    end
end
