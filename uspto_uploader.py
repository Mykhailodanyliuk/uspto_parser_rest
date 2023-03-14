import json
import datetime
import shutil
import time
import requests
import wget
from zipfile import ZipFile
import os
import pandas as pd


def create_directory(path_to_dir, name):
    mypath = f'{path_to_dir}/{name}'
    if not os.path.isdir(mypath):
        os.makedirs(mypath)


def delete_directory(path_to_directory):
    if os.path.exists(path_to_directory):
        shutil.rmtree(path_to_directory)


def get_request_data(url, verify=False):
    response = requests.get(url, verify=verify)
    if response.status_code == 200:
        return response
    else:
        time.sleep(10)
        get_request_data(url, verify=False)


def upload_patents_data(file, collection_rest_url):
    for line in open(file, 'r', encoding='utf-8'):
        patent = json.loads(line)
        response = requests.get(f'{collection_rest_url}?id={patent.get("id")}')
        if response.status_code == 200:
            response_json = json.loads(response.text)
            is_in_database = False if response_json.get('total') == 0 else True
            if not is_in_database:
                requests.post(collection_rest_url, json=patent)


def upload_all_uspto_zips(zip_files_rest_url, uspto_data_col_url):
    start_date = "2016-01-01"
    current_date = datetime.datetime.today().strftime('%Y-%m-%d')
    current_directory = os.getcwd()
    for i in range(1000):
        if start_date > current_date:
            break
        from_date = pd.to_datetime(start_date) + pd.DateOffset(months=i)
        from_date = from_date.strftime('%m-%d-%Y')
        to_date = pd.to_datetime(start_date) + pd.DateOffset(months=i + 1)
        to_date = to_date.strftime('%m-%d-%Y')
        url = f'https://developer.uspto.gov/ibd-api/v1/weeklyarchivedata/searchWeeklyArchiveData?fromDate={from_date}&toDate={to_date}'
        request_data = get_request_data(url)
        directory_name = 'uspto'
        path_to_directory = f'{current_directory}/{directory_name}'
        delete_directory(path_to_directory)
        create_directory(current_directory, directory_name)
        for file_data in json.loads(request_data.text):
            zip_file_link = (file_data.get('archiveDownloadURL'))
            response = requests.get(f'{zip_files_rest_url}?name={zip_file_link}')
            if response.status_code == 200:
                response_json = json.loads(response.text)
                is_in_database = False if response_json.get('total') == 0 else True
                if not is_in_database:
                    zip_file_name = zip_file_link[-37:]
                    path_to_zip_file = f'{path_to_directory}/{zip_file_name}'
                    try:
                        wget.download(zip_file_link, path_to_zip_file)
                    except:
                        break
                    with ZipFile(path_to_zip_file, 'r') as zip:
                        file_path = zip.namelist()[0]
                        zip.extract(file_path, path_to_directory)
                    upload_patents_data(f'{path_to_directory}/{file_path}', uspto_data_col_url)
                    delete_directory(path_to_directory)
                    requests.post(f'{zip_files_rest_url}', json={'name': zip_file_link})


if __name__ == '__main__':
    while True:
        start_time = time.time()
        zip_collection_rest_url = 'http://62.216.33.167:21005/api/downloaded_zips'
        uspto_col_url = 'http://62.216.33.167:21005/api/uspto_data'
        upload_all_uspto_zips(zip_collection_rest_url, uspto_col_url)
        work_time = int(time.time() - start_time)
        time.sleep(abs(work_time % 14400 - 14400))
