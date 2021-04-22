import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pytz
import numpy as np
from Code.Preprocessing.Visualizations import *

def read_cgm_data(row):
    #CGM
    try:
        cgm_df = pd.read_csv(row.filename.item())
    except ValueError:
        pass
    ##Below we convert to UNIX but pd.datetime may be enough

    cgm_df['datetime'] = pd.to_datetime(cgm_df.TimeWhenRecordCapturedFormatted_w_Offset)
    try:
        cgm_df['datetime'] = [x.tz_convert('America/Los_Angeles') for x in cgm_df.datetime]
    except TypeError:
        cgm_df['datetime'] = [x.tz_localize('America/Los_Angeles') for x in cgm_df.datetime]

    return cgm_df

def read_JanAI_data(row):
    ##JanID
    try:
        jai_df = pd.read_csv(row.filename.item())
    except ValueError:
        pass
    ##Data is in UTC
    jai_df['event_datetime'] = pd.to_datetime(jai_df.event_timestamp)
    jai_df['insert_datetime'] = pd.to_datetime(jai_df.insert_timestamp)
    try:
        jai_df['event_datetime'] = [x.tz_localize('America/Los_Angeles') for x in jai_df.event_datetime]
    except TypeError:
        #jai_df['event_datetime'] = [x.tz_convert('America/Los_Angeles') for x in jai_df.event_datetime] #might have time conversion issue
        jai_df['event_datetime'] = [x.tz_localize(None).tz_localize('America/Los_Angeles') for x in jai_df.event_datetime]
        pass
    try:
        jai_df['insert_datetime'] = [x.tz_localize('America/Los_Angeles') for x in jai_df.insert_datetime]
    except TypeError:
        #jai_df['insert_datetime'] = [x.tz_convert('America/Los_Angeles') for x in jai_df.insert_datetime] ##has 8hr time conversion...
        jai_df['insert_datetime'] = [x.tz_localize(None).tz_localize('America/Los_Angeles') for x in jai_df.insert_datetime]
        pass

    return jai_df

def correct_jai_entries(summary_jai_df):
    #1. Group by the entries on the same day and time
    counts = summary_jai_df.groupby(['subject', 'visit', 'event_days']).count()['insert_days']
    counts = pd.DataFrame(counts)
    repeated_measures = counts[counts.insert_days > 1].reset_index() ## find repeated measures
    repeated_measures.columns = ['subject', 'visit', 'event_days', 'insert_counts']
    repeated_measures_df = repeated_measures.merge(summary_jai_df)
    #use the input time for these
    one_hr_filter = repeated_measures_df[repeated_measures_df['input-event'] > .05] ## if longer than 1hr beterrn entry
    first_entries = repeated_measures_df.sort_values('id').groupby(by=['subject', 'visit', 'event_days']).first(3)
    first_entries = first_entries.reset_index()

    ### Group repeated measures by the event day and then find the difference in entry time
    d = repeated_measures_df.assign(output=repeated_measures_df.sort_values('id').groupby(by=['subject',
                                                                                              'visit',
                                                                                              'event_days']
                                                                                          )['insert_days'].apply(lambda x: x - x.iloc[0]))
    #If difference in entry time is greater than 1hr, We should use the Input time
    subd = d[d.output > 0.05]
    ##Filter out the one entry in logic (Subject 61w16 event at 2.71 with large delay in entry)
    subd = subd[subd['input-event'] < 8]
    ##TODO: Label these with Flag2 (Possible error with the app, use input time) #Use Input time


    ### filter out subd from the whole janAI dataset
    subd_wo = subd.drop(columns='output') ##need to remove the output column for the merge
    common = summary_jai_df.merge(subd_wo, how='outer')
    subd_wo['flag'] = 2
    subd_wo['final_time'] = subd_wo.insert_days

    common.insert_counts = common.insert_counts.replace(np.nan, 1000)
    filter2 = common[common.insert_counts == 1000] ### this is to find the rows which are not part of the repeated measure filter

    ##filter out the entries that are over 6hr from last entry
    sixhr_filter = filter2[filter2['input-event'] > 0.25] ### filtering whats left from filter 2 on entries over 6hr from input
    #TODO: Label these with Flag3 (Guessing - Most likely recall) #Use Eventitme, but we are skeptical
    sixhr_filter['flag'] = 3
    sixhr_filter['final_time'] = sixhr_filter.event_days


    ##TODO: Everything else is Flag1 (trust the eventtime)
    Flag1 = filter2[filter2['input-event'] < 0.25]
    Flag1['flag'] = 1
    Flag1['final_time'] = Flag1.event_days

    final_JanAI_data = pd.concat([Flag1, subd_wo, sixhr_filter])

    return final_JanAI_data

def errored_jai():
    import json

    columns = ['id', 'type', 'event_timestamp', 'insert_timestamp', 'data']  # ,'images','saveforlater_id']

    with open(path + 'c1061011_food-diary_januaryai_nonsensitive_20200610_10241038-week16.csv', 'r') as f:
        lines = f.readlines()

    cleaned_lines = []
    for line in lines:
        *p1, p2 = line.split(",", 4)
        json_str = p2.rsplit("}", 1)[0] + "}"
        data = json.loads(json_str)

        p1 = list(p1) + [data]
        cleaned_lines.append(p1)

    df = pd.DataFrame(cleaned_lines)
    df.columns = columns

def get_visit_start_time(subject, visit):
    '''
    Get the start time of visit from PDH/JAI
    :param subject: Subject ID
    :param visit: Visit number
    :return: The start time of visit
    '''
    csv = '/Users/psaltd/Desktop/KHK_Analysis/data/raw/KHK_visit_start_date.csv'
    df = pd.read_csv(csv)
    sub_df = df[(df.Subject == int(subject)) & (df.Visit == visit)]

    return sub_df.Date.item()

def aggregate_khk_data(path):
    '''
    Collect the file information for the KHK Data

    :param path: Path to data
    :return: Dataframe of data information (studyID, subjecID, visit, sensortype, sensor, date, filename, path
    '''
    files = os.listdir(path)

    file_info_df = []
    for f in files:
        if 'cgm' in f:
            [studyID, sensor, sensortype, ns, date, end] = f.split('_')
        elif 'Edited' in f:
            [studyID, sensortype, sensor, ns, date, end] = f.split('_')
        else:
            continue
        [subjID, end] = end.split('-')
        [visit, _] = end.split('.')

        row = {'StudyID': studyID, 'subject': subjID, 'visit': visit, 'sensortype': sensortype,
               'sensor': sensor, 'date': date, 'end': end, 'filename': path + f}

        file_info_df.append(row)

    file_info_df = pd.DataFrame(file_info_df)
    file_info_df = file_info_df.sort_values(by=['subject', 'date'])

    return file_info_df

if __name__ == '__main__':
    path ='/Users/psaltd/Desktop/KHK_Analysis/data/raw/'

    file_info_df = aggregate_khk_data(path)
    subjects = list(set(list(file_info_df.subject)))
    visits = list(set(list(file_info_df.visit)))
    summary_jai = []
    for s in subjects:
        for v in visits:
            #s = '10241061'
            #v = 'Week16'
            subfolder = file_info_df[(file_info_df.subject == s) & (file_info_df.visit == v)]
            if subfolder.shape[0] < 2:
                continue
            else:
                jai_res = plot_cgm_jai(subfolder)
                summary_jai.append(jai_res)

    summary_jai_df = pd.concat(summary_jai)



