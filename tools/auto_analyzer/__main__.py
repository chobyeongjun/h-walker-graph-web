"""
H-Walker Auto Analyzer — CLI entry point.

Usage:
    python -m tools.auto_analyzer data/위치고정.CSV -o output/ --style default
    python -m tools.auto_analyzer file1.CSV file2.CSV --style ieee --analysis force
    python -m tools.auto_analyzer data/*.CSV --no-graphs --format json
"""

import argparse
import json
import csv
import os
import sys
import time

from . import __version__
from .analyzer import analyze_file, compare_results, result_to_dict
from .plotter import generate_all_plots


def main():
    parser = argparse.ArgumentParser(
        prog='auto_analyzer',
        description='H-Walker Automated Gait Analysis & Graph Generation',
    )
    parser.add_argument('csv_files', nargs='+', help='CSV file paths (1-4 files)')
    parser.add_argument('-o', '--output-dir', default='./output',
                        help='Output directory (default: ./output)')
    parser.add_argument('--style', default='default',
                        choices=['default', 'ieee', 'nature', 'elsevier'],
                        help='Journal style preset (default: default)')
    parser.add_argument('--analysis', nargs='+', default=['all'],
                        choices=['force', 'imu', 'gait', 'fft', 'all'],
                        help='Analysis types to run (default: all)')
    parser.add_argument('--no-graphs', action='store_true',
                        help='Skip graph generation, output stats only')
    parser.add_argument('--format', dest='out_format', default='both',
                        choices=['json', 'csv', 'both'],
                        help='Output format (default: both)')
    parser.add_argument('--lang', default='en', choices=['en', 'ko'],
                        help='Label language (default: en)')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    # Validate inputs
    if len(args.csv_files) > 4:
        parser.error('Maximum 4 CSV files supported for comparison')

    for f in args.csv_files:
        if not os.path.isfile(f):
            parser.error(f'File not found: {f}')

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"H-Walker Auto Analyzer v{__version__}")
    print(f"  Style: {args.style}")
    print(f"  Analysis: {', '.join(args.analysis)}")
    print(f"  Output: {os.path.abspath(args.output_dir)}")
    print()

    # Analyze each file
    t0 = time.time()
    results = []
    for filepath in args.csv_files:
        print(f"Analyzing: {filepath}")
        try:
            r = analyze_file(filepath, analyses=args.analysis)
            results.append(r)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
    print()

    if not results:
        print("No files were successfully analyzed.")
        sys.exit(1)

    # Save statistics
    if args.out_format in ('json', 'both'):
        summary = {
            'version': __version__,
            'style': args.style,
            'analysis': args.analysis,
            'files': [result_to_dict(r) for r in results],
        }
        if len(results) >= 2:
            summary['comparison'] = compare_results(results)

        json_path = os.path.join(args.output_dir, 'summary.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"Saved: {json_path}")

    if args.out_format in ('csv', 'both'):
        csv_path = os.path.join(args.output_dir, 'stats.csv')
        _write_stats_csv(results, csv_path)
        print(f"Saved: {csv_path}")

    # Generate plots
    if not args.no_graphs:
        print("\nGenerating plots...")
        saved = generate_all_plots(results, args.style, args.output_dir)
        print(f"  {len(saved)} plots saved to {os.path.join(args.output_dir, 'plots/')}")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")


def _write_stats_csv(results, csv_path: str):
    """Write a flat CSV table of key statistics."""
    rows = []
    for r in results:
        row = {
            'filename': r.filename,
            'duration_s': round(r.duration_s, 2),
            'sample_rate': round(r.sample_rate, 1),
            'L_n_strides': r.left_stride.n_strides,
            'R_n_strides': r.right_stride.n_strides,
            'L_stride_time_mean': round(r.left_stride.stride_time_mean, 4),
            'L_stride_time_std': round(r.left_stride.stride_time_std, 4),
            'R_stride_time_mean': round(r.right_stride.stride_time_mean, 4),
            'R_stride_time_std': round(r.right_stride.stride_time_std, 4),
            'L_stride_length_mean': round(r.left_stride.stride_length_mean, 4),
            'L_stride_length_std': round(r.left_stride.stride_length_std, 4),
            'R_stride_length_mean': round(r.right_stride.stride_length_mean, 4),
            'R_stride_length_std': round(r.right_stride.stride_length_std, 4),
            'L_cadence': round(r.left_stride.cadence, 1),
            'R_cadence': round(r.right_stride.cadence, 1),
            'L_stance_pct': round(r.left_stride.stance_pct_mean, 1),
            'R_stance_pct': round(r.right_stride.stance_pct_mean, 1),
            'L_force_rmse': round(r.left_force_tracking.rmse, 3),
            'R_force_rmse': round(r.right_force_tracking.rmse, 3),
            'L_force_mae': round(r.left_force_tracking.mae, 3),
            'R_force_mae': round(r.right_force_tracking.mae, 3),
            'stride_time_symmetry': round(r.stride_time_symmetry, 2),
            'force_symmetry': round(r.force_symmetry, 2),
            'L_fatigue_pct': round(r.left_fatigue, 2),
            'R_fatigue_pct': round(r.right_fatigue, 2),
        }
        rows.append(row)

    if rows:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


if __name__ == '__main__':
    main()
