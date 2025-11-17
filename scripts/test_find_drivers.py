import os
import importlib.util

# Load server/database.py as a module (server isn't a package here)
base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
db_path = os.path.join(base, 'server', 'database.py')
spec = importlib.util.spec_from_file_location('server_database', db_path)
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)
find_drivers = db.find_drivers

cases = [
    ("To University", "Monday", "17:44", "Beirut"),
    ("To University", "Monday", "17:47", "Beirut"),
    ("To University", "Monday", "18:00", "Beirut"),
]

for direction, day, time_str, area in cases:
    print('\nCASE:', direction, day, time_str, area)
    drivers = find_drivers(direction, day, time_str, area)
    print('Found', len(drivers), 'drivers')
    for d in drivers:
        print(d)
