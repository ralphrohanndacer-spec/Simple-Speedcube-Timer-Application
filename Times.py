#For sqlite3 and time formatting
from Puzzle import calculate_wca_average, calculate_wca_ao100
import sqlite3
import time

#Create the .db and tables if not exists
def init_db():
    conn = sqlite3.connect('speedcube.db')
    cursor = conn.cursor()

    # 1. Create the solves table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tab TEXT,
            tab_id INTEGER,
            puzzle TEXT,
            final_time_ms INTEGER,
            scramble TEXT,
            has_inspection_penalty INTEGER,
            is_dnf INTEGER,
            has_time_limit REAL,
            timestamp INTEGER,
            UNIQUE (tab, tab_id)
        )
    """)

    # 2. Create the average_records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS average_records (
            record_type TEXT,
            puzzle TEXT,
            tab TEXT,
            tab_id INTEGER,
            average REAL,
            timestamp INTEGER,
            PRIMARY KEY (record_type, puzzle, tab)
        )
    """)

    conn.commit()
    conn.close()

#A class with a function formats the solve data into a dictionary
class Solve:
    def __init__(self, tab, puzzle, final_time_ms, scramble, has_inspection_penalty, is_dnf, has_time_limit, timestamp, tab_id=None):
        self.tab = tab
        self.tab_id = tab_id
        self.puzzle = puzzle
        self.final_time_ms = final_time_ms
        self.scramble = scramble
        self.has_inspection_penalty = has_inspection_penalty
        self.is_dnf = is_dnf
        self.has_time_limit = has_time_limit
        self.timestamp = timestamp


    def data_dict(self):
        data_dict = {
            "tab": self.tab,
            "tab_id": self.tab_id,
            "puzzle": self.puzzle,
            "final_time_ms": self.final_time_ms,
            "scramble": self.scramble,
            "has_inspection_penalty": self.has_inspection_penalty,
            "is_dnf": self.is_dnf,
            "has_time_limit": self.has_time_limit,
            "timestamp": self.timestamp
        }
        return data_dict

#Formats the solve time into a readable time with milliseconds
def format_solve_time(ms_total):
    #Just to make sure it handles such values
    if ms_total in ["-", "DNF"]:
        return ms_total

    hours = ms_total // 3600000
    remaining = ms_total % 3600000
    minutes = remaining // 60000
    remaining %= 60000
    seconds = remaining // 1000
    msec = (remaining % 1000) // 10

    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}.{msec:02}"
    if minutes > 0:
        return f"{minutes:02}:{seconds:02}.{msec:02}"
    return f"{seconds:02}.{msec:02}"

#Checks the solve time so it can be formatted safely using format solve time
def check_solve_time(solve_data):
    if solve_data["is_dnf"] == 1:
        solve_time = "DNF"
    elif solve_data["has_inspection_penalty"] == 2:
        solve_time = format_solve_time(solve_data["final_time_ms"]) + " +2"
    else:
        solve_time = format_solve_time(solve_data["final_time_ms"])

    return solve_time

#Inserts new solve data dictionary
def insert_solve_data(data_dict):
    conn = sqlite3.connect('speedcube.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO solves (tab, tab_id, puzzle, final_time_ms, scramble, has_inspection_penalty, is_dnf, has_time_limit, timestamp) 
        VALUES (
            :tab, 
            (SELECT COALESCE(MAX(tab_id), 0) + 1 FROM solves WHERE tab = :tab), 
            :puzzle, 
            :final_time_ms, 
            :scramble, 
            :has_inspection_penalty, 
            :is_dnf, 
            :has_time_limit, 
            :timestamp    
        )
    """, data_dict)

    conn.commit()
    conn.close()

#Fetches all the tab data, with order DESC / ASC
def fetch_tab_data(current_tab, order="DESC"):
    conn = sqlite3.connect('speedcube.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if order.upper() == "ASC":
        cursor.execute("SELECT * FROM solves WHERE tab=:tab ORDER BY tab_id ASC", {"tab": current_tab})
    else:
        cursor.execute("SELECT * FROM solves WHERE tab=:tab ORDER BY tab_id DESC", {"tab": current_tab})

    tab_data = cursor.fetchall()

    conn.close()
    return tab_data

#Deletes all the tab data
def clear_tab_data(current_tab):
    conn = sqlite3.connect('speedcube.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM solves WHERE tab=:tab", {"tab": current_tab})

    conn.commit()
    conn.close()

#Fetches specific solve data in a tab by its tab id
def fetch_data_by_id(current_tab, tab_id):
    conn = sqlite3.connect('speedcube.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM solves WHERE tab=:tab AND tab_id=:tab_id", {"tab": current_tab,"tab_id": tab_id})

    data = cursor.fetchone()
    conn.close()

    return data if data else None

#Deletes specific solve data in a tab by its tab id
def delete_data_by_id(current_tab, tab_id):
    conn = sqlite3.connect('speedcube.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM solves WHERE tab=:tab AND tab_id=:tab_id", {"tab": current_tab,"tab_id": tab_id})

    conn.commit()
    conn.close()

#Gets a list of solve data and returns its solve time and scramble only
def get_solve_list(list_data):
    solves_data = []
    for data in list_data:
        solve_time = check_solve_time(data)
        scramble = data["scramble"]
        solves_data.append([solve_time, scramble])

    return solves_data

#Fetches the single best in all the tab solves
def fetch_single_best(current_tab):
    conn = sqlite3.connect('speedcube.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM solves WHERE tab=:tab AND final_time_ms > 0 and is_dnf != 1 "
                   "ORDER BY final_time_ms ASC, tab_id ASC LIMIT 1",
                   {"tab": current_tab})

    single_best = cursor.fetchone()
    conn.close()

    return single_best if single_best else None

#Loops through all the tab data passed, and stores and updates average best
def store_average_best(tab_data, puzzle, current_tab):
    for index, data in enumerate(tab_data):

        if index >= 4:
            ao5_list = tab_data[index - 4: index + 1]
            ao5_ave = calculate_wca_average(ao5_list)

            if isinstance(ao5_ave, int):
                update_average_best("Ao5", puzzle, current_tab, data["tab_id"], ao5_ave)

        if index >= 11:
            ao12_list = tab_data[index - 11: index + 1]
            ao12_ave = calculate_wca_average(ao12_list)

            if isinstance(ao12_ave, int):
                update_average_best("Ao12", puzzle, current_tab, data["tab_id"], ao12_ave)

        if index >= 99:
            ao100_list = tab_data[index - 99: index + 1]
            ao100_ave = calculate_wca_ao100(ao100_list)

            if isinstance(ao100_ave, int):
                update_average_best("Ao100", puzzle, current_tab, data["tab_id"], ao100_ave)

#Checks if the new time passed is faster than the stored average best, and updates it. (In a specific tab)
def update_average_best(record_type, puzzle, current_tab, tab_id, new_time):

    conn = sqlite3.connect('speedcube.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    data_dict = {"record_type": record_type, "puzzle": puzzle, "tab": current_tab}

    cursor.execute("SELECT average FROM average_records WHERE record_type=:record_type AND puzzle=:puzzle AND tab=:tab",
                   data_dict)

    best = cursor.fetchone()
    timestamp = int(time.time())

    time_to_return = None

    if best is None or float(new_time) < best["average"]:
        cursor.execute("INSERT OR REPLACE INTO average_records (record_type, puzzle, tab, tab_id, average, timestamp) "
                       "VALUES (:record_type, :puzzle, :tab, :tab_id, :average, :timestamp)",
                       {
                           "record_type": record_type,
                           "puzzle": puzzle,
                           "tab": current_tab,
                           "tab_id": tab_id,
                           "average": new_time,
                           "timestamp": timestamp
                       }
                       )
        conn.commit()
        time_to_return = float(new_time)
    else:
        time_to_return = float(best["average"])

    conn.close()

    return time_to_return

#Fetches the average best in the tab solve
def fetch_average_best(record_type, puzzle, current_tab):
    conn = sqlite3.connect('speedcube.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM average_records WHERE record_type=:record_type AND puzzle=:puzzle AND tab=:tab",
                   {"record_type": record_type, "puzzle": puzzle, "tab": current_tab})

    average_best = cursor.fetchone()
    conn.close()

    return average_best if average_best else None

#Deletes all the average data
def clear_average_data(puzzle, current_tab):
    conn = sqlite3.connect('speedcube.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM average_records WHERE puzzle=:puzzle AND tab=:tab", {"puzzle": puzzle, "tab": current_tab})

    conn.commit()
    conn.close()

#Adds/subtract 2000 ms of a specific solve data under conditions
def plus_two_solve(current_tab, tab_id, final_time_ms, inspection_status, dnf_status):
    conn = sqlite3.connect('speedcube.db')
    cursor = conn.cursor()

    if dnf_status == 1:
        new_time_ms = final_time_ms + 2000
        cursor.execute("UPDATE solves SET final_time_ms=:final_time_ms, has_inspection_penalty=:has_inspection_penalty, is_dnf=:is_dnf "
                       "WHERE tab=:tab AND tab_id=:tab_id",
                       {"tab": current_tab, "tab_id": tab_id, "final_time_ms": new_time_ms,
                        "has_inspection_penalty": 2, "is_dnf": 0})

    elif inspection_status == 2:
        new_time_ms = final_time_ms - 2000
        cursor.execute("UPDATE solves SET final_time_ms=:final_time_ms, has_inspection_penalty=:has_inspection_penalty "
                       "WHERE tab=:tab AND tab_id=:tab_id",
                       {"tab": current_tab, "tab_id": tab_id, "final_time_ms": new_time_ms,
                        "has_inspection_penalty": 0})
    else:
        new_time_ms = final_time_ms + 2000
        cursor.execute("UPDATE solves SET final_time_ms=:final_time_ms, has_inspection_penalty=:has_inspection_penalty "
                       "WHERE tab=:tab AND tab_id=:tab_id",
                       {"tab": current_tab, "tab_id": tab_id, "final_time_ms": new_time_ms,
                        "has_inspection_penalty": 2})

    conn.commit()
    conn.close()

#DNFs a specific solve data under conditions
def dnf_solve(current_tab, tab_id, final_time_ms ,inspection_status, dnf_status):
    conn = sqlite3.connect('speedcube.db')
    cursor = conn.cursor()

    if inspection_status == 2:
        new_time_ms = final_time_ms - 2000
        cursor.execute("UPDATE solves SET final_time_ms=:final_time_ms, has_inspection_penalty=:has_inspection_penalty, is_dnf=:is_dnf "
                       "WHERE tab=:tab AND tab_id=:tab_id",
                       {"tab": current_tab, "tab_id": tab_id, "final_time_ms": new_time_ms,
                        "has_inspection_penalty": 0, "is_dnf": 1})
    elif dnf_status == 1:
        cursor.execute("UPDATE solves SET is_dnf=:is_dnf "
                       "WHERE tab=:tab AND tab_id=:tab_id",
                       {"tab": current_tab, "tab_id": tab_id, "is_dnf": 0})
    else:
        cursor.execute("UPDATE solves SET is_dnf=:is_dnf "
                       "WHERE tab=:tab AND tab_id=:tab_id",
                       {"tab": current_tab, "tab_id": tab_id, "is_dnf": 1})

    conn.commit()
    conn.close()