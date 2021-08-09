import argparse
from concurrent import futures
import json
import logging
import os
from os import path as osp
import re
import sys
import time

import requests

logger = logging.getLogger(__name__)

def read_json_file(fname):
    with open(fname, 'r') as fp:
        return json.load(fp)

def make_cloudfront_request(resource, class_pid, cookies, extras={}, set_cookies=False):
    DOMAIN = 'https://d3k4p2smfceopy.cloudfront.net'
    url = DOMAIN + '/' + resource
    logger.debug(f"making request to url: {url}")
    for i in range(5):
        try:
            params_d = dict(extras)
            params_d['ClassPID'] = class_pid
            r = requests.get(url, params=params_d, cookies=cookies)
            r.raise_for_status()
            if set_cookies:
                for cookie in r.cookies:
                    cookies[cookie.name] = cookie.value
            return r
        except requests.exceptions.ConnectionError:
            logger.warning("too many requests. going to sleep.")
            time.sleep(5)

def chunks_from_m3u8(m3u8):
    p = re.compile("#EXT")
    return [chunk for chunk in m3u8.splitlines() if not p.match(chunk)]

def download_chunk(resource_prefix, chunk, class_pid, cookies):
    chunk_resource = f"{resource_prefix}/{chunk}"
    logger.debug(f"download_chunk called on {chunk}")
    chunk_req = make_cloudfront_request(chunk_resource, class_pid, cookies)
    return chunk_req.content

# chunks is a list
def future_download_chunks(resource_prefix, chunks, class_pid, cookies, fout, num_workers=None):
    executor = futures.ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix='video_downloader')
    batch = 10
    n_chunks = len(chunks)
    n_batches = n_chunks // batch + (1 if not n_chunks % batch == 0 else 0)
    for chunk_batch in range(n_chunks // batch + (1 if not n_chunks % batch == 0 else 0)):
        percent_done = chunk_batch / n_batches
        if chunk_batch != 0 and round((chunk_batch - 1) / n_batches, 1) != round(percent_done, 1):
            percent_done = int(percent_done * 100)
            logger.info(f"completion: {percent_done}%")
        start = chunk_batch * batch
        downloaded_chunk_futures = [executor.submit(download_chunk, resource_prefix, chunk, class_pid, cookies) for chunk in chunks[start:start + batch]]
        for dc_future in downloaded_chunk_futures:
            fout.write(dc_future.result())

def highest_resolution_from_m3u8(m3u8):
    p = re.compile('/(\d+)p/')
    matches = filter(lambda x: x is not None, (p.search(line) for line in m3u8.splitlines()))
    return max(int(m.groups(1)[0]) for m in matches)

# takes in video blob
# downloads video
def download_video_file(video_json, cookies, class_pid, outdir):
    hlsfilekey = video_json['videoHLSFileKey']
    logger.info(f"downloading {video_json['videoTitle']}")
    cookie_request_resource = "P/Data/VideoUrl/" + video_json['videoFileKey'].replace('-', '').replace('.', '') + "_-index.m3u8"
    q_params = {'dist': 'cz1-chatter',
                'key': hlsfilekey + '/index.m3u8',
                'cookie': 'true'}

    video_streams_resp = make_cloudfront_request(cookie_request_resource, class_pid, cookies, extras=q_params, set_cookies=True)
    resolution = highest_resolution_from_m3u8(video_streams_resp.text)

    video_path_md_resource = f"{hlsfilekey}/{resolution}p/{hlsfilekey}.m3u8"
    md_req = make_cloudfront_request(video_path_md_resource, class_pid, cookies)
    chunks = chunks_from_m3u8(md_req.text)
    vname = video_json['videoFileName']
    with open(osp.join(outdir, vname), 'wb') as fout:
        resource_prefix = f"{hlsfilekey}/{resolution}p"
        future_download_chunks(resource_prefix, chunks, class_pid, cookies, fout, num_workers=5)

def parse_cookies_arg(cookies_arg):
    pairs = cookies_arg.split(';')
    cookies = {}
    for pair in pairs:
        key, val = pair.strip().split('=')
        cookies[key] = val
    return cookies

def filter_video_list(video_list, pattern):
    p = re.compile(pattern)
    return [v for v in video_list if p.search(v['videoTitle'])]

def make_path(d):
    try:
        os.makedirs(d)
    except FileExistsError:
        pass

def get_args(command_line):
    parser = argparse.ArgumentParser(description='Download video files in json manifest file.')
    parser.add_argument('json_file', metavar='json_file', help='path to the json video list file')
    parser.add_argument('--cookies', dest='cookies', required=True, type=parse_cookies_arg,
                        help='required. cookies to use for the web requests to cloudfront. format is: key1=val2; key2=val2;... keyn=valn')
    parser.add_argument('--pattern', dest='pattern', default='',
                        help='optional. if set, only video files which match this regex in the video list will be downloaded')
    parser.add_argument('--class_pid', dest='class_pid', required=True,
                        help='required. the class id.')
    parser.add_argument('--out_dir', dest='out_dir', default='.',
                        help='optional. directory to save files to.')
    parser.add_argument('-v', '--verbose', action='store_const', const=True, default=False)
    return parser.parse_args()

def main():
    args = get_args(sys.argv)
    if (args.verbose):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    video_list = read_json_file(args.json_file)['data']
    if (args.pattern):
        video_list = filter_video_list(video_list, args.pattern)
    
    make_path(args.out_dir)
    for video in video_list:
        download_video_file(video, args.cookies, args.class_pid, args.out_dir)

if __name__ == '__main__':
    main()
