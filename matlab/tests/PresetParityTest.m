classdef PresetParityTest < matlab.unittest.TestCase
% Verifies hwalker.plot.journalPreset matches publication_engine.py spec
% (CLAUDE.md authoritative table) bit-for-bit.

    methods (TestClassSetup)
        function addToolboxPath(tc) %#ok<MANU>
            addpath(fullfile(fileparts(mfilename('fullpath')), '..'));
        end
    end

    methods (Test)

        function testIEEE(tc)
            p = hwalker.plot.journalPreset('IEEE');
            tc.verifyEqual(p.col1mm, 88.9);
            tc.verifyEqual(p.col1h_mm, 70.0);
            tc.verifyEqual(p.col2mm, 181.0);
            tc.verifyEqual(p.col2h_mm, 90.0);
            tc.verifyEqual(p.font, 'Times New Roman');
            tc.verifyEqual(p.bodyPt, 8);
            tc.verifyEqual(p.strokePt, 1.0);
            tc.verifyEqual(p.dpi, 600);
            tc.verifyFalse(p.colorblindSafe);
            tc.verifyEqual(p.paletteName, 'grayscale');
        end

        function testNature(tc)
            p = hwalker.plot.journalPreset('Nature');
            tc.verifyEqual(p.col1mm, 89.0);
            tc.verifyEqual(p.col1h_mm, 60.0);
            tc.verifyEqual(p.col2mm, 183.0);
            tc.verifyEqual(p.col2h_mm, 90.0);
            tc.verifyEqual(p.font, 'Helvetica');
            tc.verifyEqual(p.bodyPt, 7);
            tc.verifyEqual(p.strokePt, 0.5);
            tc.verifyEqual(p.dpi, 300);
            tc.verifyTrue(p.colorblindSafe);
            tc.verifyEqual(p.paletteName, 'wong');
            % Wong palette specific colors
            tc.verifyEqual(round(p.palette(1,:)*255), [0, 114, 178]);
            tc.verifyEqual(round(p.palette(2,:)*255), [230, 159,   0]);
        end

        function testAPA(tc)
            p = hwalker.plot.journalPreset('APA');
            tc.verifyEqual(p.col1mm, 85.0);
            tc.verifyEqual(p.col2mm, 174.0);
            tc.verifyEqual(p.col2h_mm, 100.0);
            tc.verifyEqual(p.font, 'Arial');
            tc.verifyEqual(p.bodyPt, 10);
        end

        function testElsevier_HasOneAndAHalf(tc)
            p = hwalker.plot.journalPreset('Elsevier');
            tc.verifyEqual(p.col1mm, 90.0);
            tc.verifyEqual(p.col2mm, 190.0);
            tc.verifyEqual(p.col15mm, 140.0);
            tc.verifyEqual(p.col15h_mm, 80.0);
            tc.verifyTrue(isfinite(p.col15in));
            tc.verifyTrue(isfinite(p.col15h_in));
        end

        function testMDPI_OnlyJournalAt1000DPI(tc)
            p = hwalker.plot.journalPreset('MDPI');
            tc.verifyEqual(p.dpi, 1000);
            tc.verifyEqual(p.font, 'Palatino Linotype');
        end

        function testJNER_ColorblindSafe(tc)
            p = hwalker.plot.journalPreset('JNER');
            tc.verifyTrue(p.colorblindSafe);
            tc.verifyEqual(p.paletteName, 'wong');
        end

        function testAxesPtIsConstant(tc)
            % All journals should use the same axes spine width (matches Python)
            for n = {'IEEE','Nature','APA','Elsevier','MDPI','JNER'}
                p = hwalker.plot.journalPreset(n{1});
                tc.verifyEqual(p.axesPt, 0.6, ...
                    sprintf('%s axesPt should be 0.6', n{1}));
            end
        end

        function testBackwardCompat_Colors(tc)
            p = hwalker.plot.journalPreset('IEEE');
            tc.verifyEqual(p.colors, p.palette);   % alias
        end

        function testInchConversion(tc)
            p = hwalker.plot.journalPreset('Nature');
            tc.verifyEqual(p.col1in,   89/25.4,   'AbsTol', 1e-9);
            tc.verifyEqual(p.col1h_in, 60/25.4,   'AbsTol', 1e-9);
            tc.verifyEqual(p.col2in,   183/25.4,  'AbsTol', 1e-9);
            tc.verifyEqual(p.col2h_in, 90/25.4,   'AbsTol', 1e-9);
        end

        function testRequiredFields(tc)
            required = {'name','col1mm','col2mm','col1h_mm','col2h_mm', ...
                        'font','bodyPt','axisPt','legendPt','titlePt', ...
                        'strokePt','axesPt','gridPt','dpi','interpreter', ...
                        'palette','paletteName','colorblindSafe','bg', ...
                        'axisColor','gridColor'};
            for n = {'IEEE','Nature','APA','Elsevier','MDPI','JNER'}
                p = hwalker.plot.journalPreset(n{1});
                for f = required
                    tc.verifyTrue(isfield(p, f{1}), ...
                        sprintf('%s missing field %s', n{1}, f{1}));
                end
            end
        end

        function testRejectsUnknownJournal(tc)
            tc.verifyError(@() hwalker.plot.journalPreset('Bogus'), ...
                'hwalker:plot:unknownJournal');
        end

    end
end
