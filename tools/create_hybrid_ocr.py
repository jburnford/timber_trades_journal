#!/usr/bin/env python3
"""
Phase 2: Create hybrid OCR directory combining Gemini + Polaris recoveries.
For each affected date, combine all successful OCR files into a single directory.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

def main():
    base_dir = Path("/home/jic823/TTJ Forest of Numbers")
    mapping_path = base_dir / "analysis" / "polaris_ocr_mapping.json"
    output_dir = base_dir / "ocr_results" / "hybrid_recovery"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("PHASE 2: CREATE HYBRID OCR DIRECTORY")
    print("=" * 80)
    print()

    # Load OCR file mapping
    with open(mapping_path, 'r') as f:
        mapping = json.load(f)

    print(f"Affected dates: {mapping['total_affected_dates']}")
    print(f"Output directory: {output_dir}")
    print()

    # Track what we copy
    hybrid_manifest = {
        'generated': datetime.now().isoformat(),
        'source_mapping': str(mapping_path),
        'output_directory': str(output_dir),
        'dates': {}
    }

    total_files_copied = 0
    total_gemini = 0
    total_polaris = 0

    # Process each date
    for norm_date, info in sorted(mapping['dates'].items()):
        date_str = info['date_str']
        print(f"Processing: {date_str}")

        # Create date directory
        date_dir = output_dir / norm_date
        date_dir.mkdir(exist_ok=True)

        files_copied = []

        # Copy Gemini OCR files
        gemini_count = 0
        for gemini_file in info['gemini_ocr_files']:
            src_path = Path(gemini_file)
            if src_path.exists():
                # Create descriptive filename
                dest_name = f"{norm_date}_{src_path.stem}_gemini.txt"
                dest_path = date_dir / dest_name

                shutil.copy2(src_path, dest_path)
                files_copied.append({
                    'source': str(src_path),
                    'destination': str(dest_path),
                    'type': 'gemini',
                    'filename': dest_name
                })
                gemini_count += 1
                total_gemini += 1
            else:
                print(f"  WARNING: Gemini file not found: {gemini_file}")

        # Copy Polaris OCR files
        polaris_count = 0
        for polaris_file in info['polaris_ocr_files']:
            src_path = Path(polaris_file)
            if src_path.exists():
                # Create descriptive filename
                dest_name = f"{norm_date}_{src_path.stem}_polaris.txt"
                dest_path = date_dir / dest_name

                shutil.copy2(src_path, dest_path)
                files_copied.append({
                    'source': str(src_path),
                    'destination': str(dest_path),
                    'type': 'polaris',
                    'filename': dest_name
                })
                polaris_count += 1
                total_polaris += 1
            else:
                print(f"  WARNING: Polaris file not found: {polaris_file}")

        total_files_copied += len(files_copied)

        print(f"  Copied: {gemini_count} Gemini + {polaris_count} Polaris = {len(files_copied)} files")

        # Add to manifest
        hybrid_manifest['dates'][norm_date] = {
            'date_str': date_str,
            'output_directory': str(date_dir),
            'gemini_count': gemini_count,
            'polaris_count': polaris_count,
            'total_files': len(files_copied),
            'files': files_copied
        }

    print()
    print("=" * 80)
    print("HYBRID OCR DIRECTORY SUMMARY")
    print("=" * 80)
    print()
    print(f"Total dates processed: {len(hybrid_manifest['dates'])}")
    print(f"Total files copied: {total_files_copied}")
    print(f"  Gemini OCR files: {total_gemini}")
    print(f"  Polaris recovery files: {total_polaris}")
    print()

    # Add summary to manifest
    hybrid_manifest['summary'] = {
        'total_dates': len(hybrid_manifest['dates']),
        'total_files': total_files_copied,
        'gemini_files': total_gemini,
        'polaris_files': total_polaris
    }

    # Save manifest
    manifest_path = output_dir / "hybrid_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(hybrid_manifest, f, indent=2, ensure_ascii=False)

    print(f"Manifest saved to: {manifest_path}")
    print()

    # Create date list for parser
    date_list_path = output_dir / "dates_to_parse.txt"
    with open(date_list_path, 'w', encoding='utf-8') as f:
        for norm_date in sorted(hybrid_manifest['dates'].keys()):
            date_info = hybrid_manifest['dates'][norm_date]
            f.write(f"{norm_date}\t{date_info['date_str']}\t{date_info['output_directory']}\n")

    print(f"Parser date list saved to: {date_list_path}")
    print()

    print("=" * 80)
    print("PHASE 2 COMPLETE")
    print("=" * 80)
    print()
    print("Ready for Phase 3: Parse affected dates with appropriate parsers")
    print()
    print("Directory structure:")
    print(f"  {output_dir}/")
    for norm_date in sorted(list(hybrid_manifest['dates'].keys())[:5]):  # Show first 5
        date_info = hybrid_manifest['dates'][norm_date]
        print(f"    {norm_date}/ ({date_info['total_files']} files)")
    if len(hybrid_manifest['dates']) > 5:
        print(f"    ... and {len(hybrid_manifest['dates']) - 5} more date directories")

    return hybrid_manifest

if __name__ == '__main__':
    manifest = main()
