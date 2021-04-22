import matplotlib.pyplot as plt
import seaborn as sns
import pytz
from Code.Preprocessing.data_ingestion import *
from matplotlib.lines import Line2D

def plot_cgm_jai(subfolder):
    path = '/Users/psaltd/Desktop/KHK_Analysis/data/raw/'
    s = subfolder.subject.unique().item()
    v = subfolder.visit.unique().item()
    visit_start = get_visit_start_time(s, v)
    cgm_row = subfolder[subfolder.sensor == 'cgm']
    cgm_df = read_cgm_data(cgm_row)
    cgm_df['days'] = ((cgm_df.datetime - pd.to_datetime(visit_start).tz_localize('America/Los_Angeles')).astype('timedelta64[m]')/60)/24
    jai_row = subfolder[subfolder.sensor == 'januaryaiEdited']

    try:
        jai_df = read_JanAI_data(jai_row)
        jai_df['insert_days'] = ((jai_df.insert_datetime -
                                  pd.to_datetime(visit_start).tz_localize('America/Los_Angeles')).astype('timedelta64[m]')/60)/24
        jai_df['event_days'] = ((jai_df.event_datetime -
                                 pd.to_datetime(visit_start).tz_localize('America/Los_Angeles')).astype('timedelta64[m]')/60)/24
    except TypeError:
        pass

    jai_df['input-event'] = jai_df.insert_days - jai_df.event_days
    jai_df['subject'] = subfolder.subject.unique().item()
    jai_df['visit'] = subfolder.visit.unique().item()
    jai_df = correct_jai_entries(jai_df)

    #plt.figure()
    #plt.subplot(211)
    plt.grid(True)
    plt.plot(cgm_df.days, cgm_df.CGM, label='CGM', color='orange', alpha=0.7)
    jai_types = list(set(list(jai_df.type)))
    flag_types = list(set(list(jai_df.flag)))
    plt.figure(1, figsize=(10,6))
    for j in jai_types:
        for f in flag_types:
            sub_df = jai_df[(jai_df.type == j) & (jai_df.flag == f)]
            if j == 'water':
                c = 'blue'
                h = np.mean(cgm_df.CGM) * 0.5
            elif j == 'activity':
                c = 'red'
                h = np.mean(cgm_df.CGM) * 0.25
            else:
                c = 'green'
                h = np.mean(cgm_df.CGM)

            if f == 1:
                ls = '-'
                conf = ' - Know'
            elif f == 2:
                ls = '--'
                conf = ' - Default to Past'
            else:
                ls = ':'
                conf = ' - Past Recall'
            #plt.subplot(211)
            #sub_jai = jai_df[jai_df.type == t]

            plt.eventplot(sub_df.final_time, color=c, label=(j+conf), lineoffsets=h, #lineoffsets=np.mean(cgm_df.CGM),
                          linelengths=50, linestyles=ls, alpha = 0.7, linewidths=2.5)

    plt.legend(loc='upper right', ncol=1,# bbox_to_anchor=(1.5, 1),
               prop={'size': 7})

    #Todo: Make plots larger and wider
    #plt.xticks(rotation='vertical')
    plt.xlabel('day')
    plt.ylim([0, np.mean(cgm_df.CGM) * 2])
    plt.xlim([0, 16])
    plt.ylabel('mg/dL')
    plt.title('%s - %s CGM vs Food Dairy' % (s, v))
    plt.tight_layout(True)
    plt.savefig(path + '%s - %s CGM vs Food Dairy.png' % (s, v))
    plt.close()

    #Distribution of time between food consumption and entry
    plt.figure(2)
    plt.grid(True)
    sns.histplot(data=jai_df, x='input-event', bins=14, hue='type')
    #plt.hist(jai_df['input-event'], 250)
    plt.xlabel('Min (input time - event)')
    plt.title('Difference in entry vs meal time for %s - %s' % (s,v))
    plt.savefig(path + 'Unique %s - %s Consumption vs Entry in Food Dairy.png' % (s, v))
    plt.tight_layout(True)
    plt.close()

    '''
    plt.figure(3)
    plt.grid(True)
    sns.scatterplot(data=jai_df, x='event_days', y='insert_days', hue='type')
    plt.plot(jai_df.event_days, jai_df.event_days, color = 'red', label='Entered at Meal')
    plt.legend()
    #plt.xticks(rotation='vertical')
    plt.xlabel('Event Time  (day)')
    plt.ylabel('Insert Time (day)')
    plt.tight_layout(True)
    plt.savefig(path + 'Scatter Plot %s - %s Consumption vs Entry in Food Dairy.png' % (s, v))
    plt.close()
    '''

    nlevels = jai_df.shape[0]
    addition = 20/nlevels
    jai_df = jai_df.reset_index()
    plt.figure(3)
    for index, row in jai_df.iterrows():
        if row.type == 'water':
            c = 'blue'
        elif row.type == 'activity':
            c = 'red'
        else:
            c = 'green'
        array = [row.event_days, row.insert_days]
        heights = ['event', 'insert']
        plt.scatter(array, heights, label=row.type, color = c, alpha=0.3, linewidths=3)
        #plt.legend(['water', 'food', 'activity'])
        plt.plot(array, heights, color = 'grey', alpha=0.7)

    legend_elements = [Line2D([0], [0], marker='o', color='w', markerfacecolor='blue',
                                label='water', alpha=0.4),
                       Line2D([0], [0], marker='o', color='w', markerfacecolor='red',
                              label='activity', alpha=0.4),
                       Line2D([0], [0], marker='o', color='w', markerfacecolor='green',
                              label='food', alpha=0.4)]

    plt.legend(handles=legend_elements, loc=7,# bbox_to_anchor=(1.2, 1),
               prop={'size': 7})
    plt.xlabel('days')
    plt.grid(True)
    plt.tight_layout(True)
    plt.subplots_adjust(top=0.95)
    plt.title('(Event time vs Input time) - %s - %s' % (s, v))
    plt.savefig(path + 'Connection plot (Event time vs Input time) - %s - %s.png' % (s, v))
    plt.close()