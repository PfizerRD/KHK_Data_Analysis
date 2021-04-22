import pandas as pd
##Specific to the 1011 study
def download_aws():
    from os import makedirs, sep
    from tqdm import tqdm
    bucket = 'ecddmtic1061011amrasp99339'
    include = ['.csv']  # include files with .bin and .h5 in their names
    # exclude files with the following in their names. In this case look for full trial data
    # from APDM (.h5, in-lab) and GENEActive (.bin, at-home)
    #exclude = ['wrist', 'cortrium', 'dynamometer', 'Sit_to_stand', 'walk', 'wood', 'lumbar']
    exclude = []
    #exclude = ['.txt']

    obj_paths = get_object_paths(bucket, prefix='raw', include=include, exclude=exclude, case_sensitive=False)

    for path in tqdm(obj_paths):
        #local_path = f'/Volumes/npru-bluesky/OtherProjects/STEPP/code/s3_data/{path}'
        local_path = f'/Users/psaltd/Desktop/KHK_Analysis/data/{path}'
        #local_path = f'/Users/psaltd/Desktop/{path}'
        # only check the directory part
        makedirs(sep.join(local_path.split('/')[:-1]), exist_ok=True)
        # download from the bucket, with the bucket path, to the local path
        download_object(bucket, path, local_path)
