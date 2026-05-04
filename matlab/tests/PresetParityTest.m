classdef PresetParityTest < matlab.unittest.TestCase
% Verifies hwalker.plot.journalPreset values match the CLAUDE.md
% authoritative table — bit-for-bit constancy across releases.

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

        % ============================================================
        %  Robotics-domain presets
        % ============================================================
        function testRoboticsPresetsAllExist(tc)
            for n = {'TRO','RAL','TNSRE','TMECH','ICRA','IROS', ...
                     'IJRR','SciRobotics','SoftRobotics', ...
                     'FrontNeurorobot','AuRo'}
                p = hwalker.plot.journalPreset(n{1});
                tc.verifyTrue(isstruct(p));
                tc.verifyTrue(p.col1mm > 0 && p.col2mm > 0);
                tc.verifyTrue(p.bodyPt > 0);
                tc.verifyTrue(p.dpi >= 300);
            end
        end

        function testTRO_IEEEDimensions(tc)
            p = hwalker.plot.journalPreset('TRO');
            tc.verifyEqual(p.col1mm, 88.9);
            tc.verifyEqual(p.col2mm, 181.0);
            tc.verifyEqual(p.font, 'Times New Roman');
            tc.verifyTrue(p.colorblindSafe);
        end

        function testTNSRE_RehabContext(tc)
            p = hwalker.plot.journalPreset('TNSRE');
            tc.verifyEqual(p.col1mm, 88.9);
            tc.verifyTrue(p.colorblindSafe);  % medical/rehab → CB-safe
        end

        function testIROS_IsAliasOfICRA(tc)
            icra = hwalker.plot.journalPreset('ICRA');
            iros = hwalker.plot.journalPreset('IROS');
            tc.verifyEqual(icra.col1mm, iros.col1mm);
            tc.verifyEqual(icra.col2mm, iros.col2mm);
            tc.verifyEqual(icra.font, iros.font);
        end

        function testSciRobotics_HelveticaWong(tc)
            p = hwalker.plot.journalPreset('SciRobotics');
            tc.verifyEqual(p.font, 'Helvetica');
            tc.verifyTrue(p.colorblindSafe);
            tc.verifyEqual(p.paletteName, 'wong');
        end

        function testIJRR_SAGEDimensions(tc)
            p = hwalker.plot.journalPreset('IJRR');
            tc.verifyEqual(p.col1mm, 86.0);
            tc.verifyEqual(p.col2mm, 178.0);
        end

        function testListJournalsReturnsTable(tc)
            t = hwalker.plot.listJournals();
            tc.verifyTrue(istable(t));
            tc.verifyTrue(height(t) >= 17);  % 11 robotics + 6 general
            tc.verifyTrue(ismember('name', t.Properties.VariableNames));
        end

        % ============================================================
        %  Custom preset
        % ============================================================
        function testCustomPreset_FullStruct(tc)
            cust = struct('name','MyJournal', ...
                'col1mm',100, 'col1h_mm',75, 'col2mm',200, 'col2h_mm',100, ...
                'font','Arial', 'bodyPt',9, 'strokePt',0.5, ...
                'dpi',300, 'paletteName','wong');
            p = hwalker.plot.journalPreset('Custom', cust);
            tc.verifyEqual(p.name, 'MyJournal');
            tc.verifyEqual(p.col1mm, 100);
            tc.verifyEqual(p.col1h_mm, 75);
            tc.verifyEqual(p.col2mm, 200);
            tc.verifyEqual(p.font, 'Arial');
            tc.verifyEqual(p.bodyPt, 9);
            tc.verifyEqual(p.dpi, 300);
            tc.verifyEqual(round(p.col1in, 4), round(100/25.4, 4));
            % Wong palette should be applied
            tc.verifyEqual(round(p.palette(1,:)*255), [0, 114, 178]);
        end

        function testCustomPreset_PartialStruct(tc)
            % Only override col2mm — rest should fall to defaults
            p = hwalker.plot.journalPreset('Custom', ...
                struct('name','PartialJournal', 'col2mm', 175));
            tc.verifyEqual(p.col2mm, 175);
            tc.verifyEqual(p.col1mm, 88.9);   % default
            tc.verifyEqual(p.bodyPt, 8);      % default
        end

        function testCustomPreset_RejectsNonStruct(tc)
            tc.verifyError( ...
                @() hwalker.plot.journalPreset('Custom', 'bad'), ...
                'hwalker:plot:customNeedsStruct');
        end

    end
end
