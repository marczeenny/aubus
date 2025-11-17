#!/usr/bin/env python3
import sqlite3
import argparse
from datetime import datetime, timedelta

DB = 'aubus.db'

parser = argparse.ArgumentParser(description='Inspect aubus.db schedules/users')
parser.add_argument('--day', required=True)
parser.add_argument('--area', required=False)
parser.add_argument('--direction', required=False)
parser.add_argument('--time', required=False)
parser.add_argument('--radius-mins', type=int, default=30, help='Show schedule times within +/- minutes')
args = parser.parse_args()

conn = sqlite3.connect(DB)
c = conn.cursor()

print('*** Users (first 50)')
for row in c.execute('SELECT id, name, username, is_driver, area FROM users LIMIT 50'):
    print(row)

print('\n*** Distinct schedule areas/directions/days (sample)')
for row in c.execute('SELECT DISTINCT area, direction, day FROM schedules ORDER BY area, direction, day'):
    print(row)

if args.day and args.direction and args.area:
    print(f"\n*** Schedules matching day={args.day}, direction={args.direction}, area={args.area}")
    q = 'SELECT id, user_id, day, time, direction, area FROM schedules WHERE day=? AND direction=? AND area=? ORDER BY time'
    rows = list(c.execute(q, (args.day, args.direction, args.area)))
    if not rows:
        print('No exact matching schedule rows found for those filters.')
    for r in rows:
        print(r)

# show schedules within +/- radius of given time
if args.time:
    try:
        t = datetime.strptime(args.time, '%H:%M')
    except Exception as e:
        print(f'Failed to parse time: {e}')
        conn.close()
        exit(1)
    lower = (t - timedelta(minutes=args.radius_mins)).time().strftime('%H:%M')
    upper = (t + timedelta(minutes=args.radius_mins)).time().strftime('%H:%M')
    print(f"\n*** Schedules within +/-{args.radius_mins} minutes ({lower} - {upper}) on day={args.day} and area={args.area} and direction={args.direction}")
    q2 = '''SELECT id, user_id, day, time, direction, area FROM schedules WHERE day=? AND direction=? AND area=? AND time BETWEEN ? AND ? ORDER BY time'''
    rows2 = list(c.execute(q2, (args.day, args.direction, args.area, lower, upper)))
    if not rows2:
        print('No schedule rows within time window.')
    for r in rows2:
        print(r)

# show all schedules for the day (first 200) to inspect formatting
print('\n*** Sample schedules for day (first 200 rows)')
for row in c.execute('SELECT id, user_id, day, time, direction, area FROM schedules WHERE day=? ORDER BY time LIMIT 200', (args.day,)):
    print(row)

conn.close()
print('\nDone.')
