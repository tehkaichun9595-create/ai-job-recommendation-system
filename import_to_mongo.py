#!/usr/bin/env python3
"""Import local JSON `profiles.json` and `jobs.json` into MongoDB.

Usage:
  python3 import_to_mongo.py --config config.py --drop

Requires `config.py` with `MONGO_URI` defined (see `config.example.py`).
"""
import argparse
import json
import os
import sys

try:
    import pymongo
except Exception:
    pymongo = None


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='Import JSON files into MongoDB')
    parser.add_argument('--profiles', default='profiles.json', help='Profiles JSON path (default: profiles.json)')
    parser.add_argument('--jobs', default='jobs.json', help='Jobs JSON path (default: jobs.json)')
    parser.add_argument('--drop', action='store_true', help='Drop target collections before import')
    parser.add_argument('--dry-run', action='store_true', help='Only show counts; do not write to DB')
    args = parser.parse_args()

    if pymongo is None:
        print('pymongo is not installed. Install requirements with `pip install -r requirements.txt`', file=sys.stderr)
        sys.exit(2)

    # Load MONGO_URI from config.py
    if not os.path.exists('config.py'):
        print('Missing `config.py`. Copy `config.example.py` to `config.py` and set MONGO_URI.', file=sys.stderr)
        sys.exit(2)

    try:
        from config import MONGO_URI
    except Exception as e:
        print(f'Failed to import MONGO_URI from config.py: {e}', file=sys.stderr)
        sys.exit(2)

    profiles = []
    jobs = []
    try:
        profiles = load_json(args.profiles)
    except FileNotFoundError:
        print(f'Profiles file not found: {args.profiles}', file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON in profiles file: {e}', file=sys.stderr)
        sys.exit(2)

    try:
        jobs = load_json(args.jobs)
    except FileNotFoundError:
        print(f'Jobs file not found: {args.jobs}', file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON in jobs file: {e}', file=sys.stderr)
        sys.exit(2)

    print(f'Profiles: {len(profiles)} records')
    print(f'Jobs: {len(jobs)} records')

    if args.dry_run:
        print('Dry run: no data will be written to MongoDB')
        sys.exit(0)

    # Connect to MongoDB and insert
    client = pymongo.MongoClient(MONGO_URI)
    db = client.get_database('alumni_database')

    if args.drop:
        print('Dropping collections `profiles` and `jobs`')
        try:
            db.profiles.drop()
            db.jobs.drop()
        except Exception as e:
            print(f'Warning: failed to drop collections: {e}')

    if profiles:
        try:
            db.profiles.insert_many(profiles)
            print(f'Inserted {len(profiles)} profiles')
        except Exception as e:
            print(f'Error inserting profiles: {e}', file=sys.stderr)
    else:
        print('No profiles to insert')

    if jobs:
        try:
            db.jobs.insert_many(jobs)
            print(f'Inserted {len(jobs)} jobs')
        except Exception as e:
            print(f'Error inserting jobs: {e}', file=sys.stderr)
    else:
        print('No jobs to insert')

    client.close()


if __name__ == '__main__':
    main()
