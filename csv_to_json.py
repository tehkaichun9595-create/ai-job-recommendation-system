#!/usr/bin/env python3
"""CSV → JSON converter for profiles/jobs.

Usage examples:
  python3 csv_to_json.py profiles.csv profiles.json
  python3 csv_to_json.py jobs.csv jobs.json --list-skills

The converter will cast `experience` to int when present.
If `--list-skills` is provided, the `skills` column will be converted
from a comma-separated string into a list of strings.
"""
import argparse
import csv
import json
import sys


def csv_to_json(csv_path: str, json_path: str, list_skills: bool = False) -> int:
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Normalize experience
            if 'experience' in r:
                try:
                    r['experience'] = int(r['experience']) if r['experience'] not in (None, '') else 0
                except ValueError:
                    r['experience'] = 0
            # Normalize skills
            if 'skills' in r and r['skills']:
                if list_skills:
                    r['skills'] = [s.strip() for s in r['skills'].split(',') if s.strip()]
                else:
                    # keep as string but normalize spacing
                    r['skills'] = ', '.join([s.strip() for s in r['skills'].split(',') if s.strip()])
            rows.append(r)
    with open(json_path, 'w', encoding='utf-8') as j:
        json.dump(rows, j, indent=2, ensure_ascii=False)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description='Convert CSV to JSON array suitable for this project')
    parser.add_argument('csv', help='Input CSV file path')
    parser.add_argument('json', help='Output JSON file path')
    parser.add_argument('--list-skills', action='store_true', help='Convert skills column to a list (split on comma)')
    args = parser.parse_args()

    try:
        count = csv_to_json(args.csv, args.json, args.list_skills)
        print(f'Wrote {count} records to {args.json}')
    except FileNotFoundError as e:
        print(f'File not found: {e}', file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
