#!/usr/bin/python3
import os
import requests
import queue
import threading
import time
import urllib3
import random
import argparse

#TODO progressbar with time prognose
#TODO logging => exceptions

from progress.bar import Bar

RANGE_NAME_SMALL = "small"
RANGE_NAME_MEDIUM = "medium"
RANGE_NAME_LARGE = "large"
RANGE_NAME_XLARGE = "xlarge"

parser = argparse.ArgumentParser(description='Found web services on domains/ips list')

parser.add_argument('-l', '--list', help="List of targets", required=True)
parser.add_argument('-t', '--threads', help="Threads, 40 by default", default=40, type=int)
parser.add_argument('-o', '--outfile', help="Outfile, default web-finds.txt", default="web-finds.txt")
parser.add_argument('-r', '--range', help="Ports range like aquatone - small, medium, large, xlarge",
                    choices=[RANGE_NAME_SMALL, RANGE_NAME_MEDIUM, RANGE_NAME_LARGE, RANGE_NAME_XLARGE],
                    required=True)
args = parser.parse_args()


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IGNORE_STATUSES = [502, 503, 504, 497]

PORT_RANGES = {
    RANGE_NAME_SMALL: [80, 443],
    RANGE_NAME_MEDIUM: [80, 443, 8000, 8080, 8443],
    RANGE_NAME_LARGE: [80, 81, 443, 591, 2082, 2087, 2095, 2096, 3000, 8000, 8001, 8008, 8080,
                       8083, 8443, 8834, 8888],
    RANGE_NAME_XLARGE: [80, 81, 300, 443, 591, 593, 832, 981, 1010, 1311, 2082, 2087, 2095,
                        2096, 2480, 3000, 3128, 3333, 4243, 4567, 4711, 4712, 4993, 5000, 5104,
                        5108, 5800, 6543, 7000, 7396, 7474, 8000, 8001, 8008, 8014, 8042, 8069,
                        8080, 8081, 8088, 8090, 8091, 8118, 8123, 8172, 8222, 8243, 8280, 8281,
                        8333, 8443, 8500, 8834, 8880, 8888, 8983, 9000, 9043, 9060, 9080, 9090,
                        9091, 9200, 9443, 9800, 9981, 12443, 16080, 18091, 18092, 20720, 28017],
}

ADDITIONAL_PORTS = [5060, 9443, 3000, 9090, 8090]

HTTP_PORTS = PORT_RANGES[args.range]
HTTP_PORTS = set(HTTP_PORTS + ADDITIONAL_PORTS)

if os.path.exists(args.outfile):
    os.remove(args.outfile)


def is_it_http_req_to_https(resp):
    if resp.status_code != 400:
        return False

    phrases =['The plain HTTP request was sent to HTTPS port',
              'speaking plain HTTP to an SSL-enabled']
    for phrase in phrases:
        if phrase not in resp.text:
            continue
        return True

    return False


class Worker(threading.Thread):
    daemon = True

    def run(self) -> None:
        while True:
            try:
                url = q.get(False)
                try:
                    resp = requests.get(
                        url, verify=False, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})

                    if resp.status_code in IGNORE_STATUSES or \
                            is_it_http_req_to_https(resp):
                        continue

                    with open(args.outfile, "a") as fh:
                        fh.write(url + "\n")
                except BaseException as e:
                    # print("Exception: {0} => {1}".format(e, url))
                    pass
                bar.next()
            except queue.Empty:
                break
            except BaseException as e:
                print("Exception: {0} => {1}".format(e, url))
                pass


targets = []
for line in open(args.list):
    line = line.strip()
    if not len(line):
        continue
    host = line

    for port in HTTP_PORTS:
        for proto in ['http', 'https']:
            targets.append("{proto}://{host}:{port}".format(proto=proto, host=host, port=port))

random.shuffle(targets)
q = queue.Queue()
for t in targets:
    q.put(t)

bar = Bar('Progress', max=q.qsize())

start_q_size = q.qsize()
pool = []
for _ in range(args.threads):
    w = Worker()
    w.start()
    pool.append(w)

is_alive = True
while is_alive:
    is_alive = False

    for w in pool:
        if w.is_alive():
            is_alive = True
            break

    time.sleep(10)
