import sys
import os
import time
import datetime
import csv
import json
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler

#-----------------------ASSUMPTIONS------------------------#
# -python file and labview file are in same folder and are the only items in that folder
# -the only file that will be getting saved is the log b/c this script opens and edits the file that gets saved
# -will need to know location of python and the log, to input into system exec.vi 
# -have to download a special UTF8 add on / plug-in 
# -will this tool be resetted each day? each week? never? 
# morning shift 7-15 , afternoon shift 15-23, night shift 23 - 7
#----------------------------------------------------------#

#-----------------------GLOBALS----------------------------#
log_data = {}
time_data = []
test_results = []
date_regex = r"\d\d_\d\d_\d\d\d\d"
result_data = {"Tests": 0, "Passes": 0, "Fails": 0, "Consecutive Fails": 0, "Yield": 0, "Average Test Time": 0,
"Last Test Time": 0, "Shortest Test Time": 0, "Tests per Hour": 0, "First Shift": 0, "Second Shift": 0, "Third Shift": 0 }
#----------------------------------------------------------#


class handler(FileSystemEventHandler):
    def on_created(self,event):
        self.parse(event)
    
    def on_modified(self,event):
        self.parse(event)

    def parse(self, event):
        time.sleep(1)
        file_path = event.src_path
        print(file_path)
        with open(file_path, "r") as f:
            csv_content = csv.DictReader(f)
            handle_log(csv_content)
            #parse and retrieve results
        sys.exit(0)

def handle_log(log):
    global log_data
    count = 0
    log_data = log
    cons_fail = 0
    sum_of_test_time = datetime.timedelta(hours=0,minutes=0,seconds=0)
    shortest_test_time = datetime.timedelta(hours=23,minutes=59,seconds=59)

    for row in log:
        count+=1
        result_data["Tests"]+=1
        test_results.append(row['TestStatus'])

        if row['TestStatus'] == 'Pass':
            result_data["Passes"]+=1
            cons_fail = 0
        
        elif row['TestStatus'] == 'Fail':
            result_data["Fails"]+=1
            cons_fail += 1
        
        if row['TestTime'] != "" and row['TestTime'] != "STR" and row['TestTime'] != "nop":
            test_time = test_time_handler(row['StartTime'],row['StartDate'],row['EndTime'],row['EndDate'])
            if test_time < shortest_test_time:
                shortest_test_time = test_time
            sum_of_test_time+= test_time
        
        if count > 4:
            shift = getShift((row['StartTime']))
            if shift == 1:
                result_data['First Shift'] += 1
            elif shift == 2:
                result_data['Second Shift'] += 1
            elif shift == 3:
                result_data['Third Shift'] += 1

        last_row = row
    
    if last_row['TestStatus'] == 'Fail':
        result_data['Consecutive Fails'] = cons_fail
    
    result_data["Tests"] = result_data["Tests"] - 4 #to accomadate first 4 empty cells
    result_data['Yield'] = getYield(result_data['Passes'],result_data['Tests'])
    result_data["Average Test Time"] = str(round_time(sum_of_test_time/result_data["Tests"]))
    result_data['Last Test Time'] = str(round_time(test_time))
    result_data['Shortest Test Time'] = str(shortest_test_time)
    result_data['Tests per Hour'] = float(tests_per_hour(result_data["Tests"],sum_of_test_time))
    
    print(json.dumps(result_data))
    
def getYield(passes,tests):
    return(round((passes/tests)*100,2))

def test_time_handler(start_time,start_date,end_time,end_date):
    end_time = end_time.split(":")
    start_time = start_time.split(":")

    start_date = start_date.split("/")
    end_date = end_date.split("/")

    start = datetime.datetime(year = int(start_date[2]),month= int(start_date[0]), day= int(start_date[1]),
    hour = int(start_time[0]),minute= int(start_time[1]),second= int(start_time[2]))

    end = datetime.datetime(year = int(end_date[2]),month= int(end_date[0]), day= int(end_date[1]),
    hour = int(end_time[0]),minute= int(end_time[1]),second= int(end_time[2]))

    elapsed_time = end - start
    return(elapsed_time)

def round_time(val):
    val = val - datetime.timedelta(microseconds=val.microseconds)
    return(val)

def tests_per_hour(tests,total_time):
    hours = total_time.seconds/60/60
    return(round(tests/hours,2))

def getShift(start_time):
    start = start_time.split(":")
    if 7 <= int(start[0]) < 15:
        return(1)
    elif 15 <= int(start[0]) < 23:
        return(2)
    else:
        return(3)

def main():
    path = sys.argv[1] if len(sys.argv) >1 else '.'
    event_handler = handler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive = False)
    observer.daemon = False
    observer.start()

if __name__ == "__main__":
    main()