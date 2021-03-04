#
# archiver.py
#
# Archives TR pages. For the specified range of TRs, requests them from 
#    http://wts.informatics.jax.org/searches/tr.detail.cgi
# Then saves the HTML as files in the archive area.
#

import sys
import math
import os
from urllib.request import Request, urlopen
from argparse import ArgumentParser

url_tmplt = 'http://wts.informatics.jax.org/searches/tr.detail.cgi?TR_Nr=%d'
trfile_tmplt = 'TR%d.html'
hdr = { "Authorization": "Basic amVyOmplbjY4Yg==" }
not_found = b'WTS2.0: Cant Find Tracking Record'

def getOpts () :
    parser = ArgumentParser()
    parser.add_argument(
      "-m", "--minTR",
      default=1,
      type=int,
      help="Minimum TR number. Default=1.")
    parser.add_argument(
      "-M", "--maxTR",
      default=13600,
      type=int,
      help="Maximum TR number. Default=maxiumum TR in WTS.")
    parser.add_argument(
      "-d", "--directory",
      default="./archive",
      help="Output directory. Default=./archive")
    return parser.parse_args()

def archiveTR (tr_key, archive_dir) :
    url = url_tmplt % tr_key
    req = Request(url, headers=hdr)
    fd = urlopen(req)
    page = fd.read()
    fd.close()
    if page.find(not_found) >= 0:
        # tr not valid
        print('?', end='')
        return
    intermediateDir = os.path.join(archive_dir, str(100 * math.floor(tr_key / 100)))
    os.makedirs(intermediateDir, exist_ok=True)
    fname = os.path.join(intermediateDir, trfile_tmplt % tr_key)
    ofd = open(fname, 'wb')
    ofd.write(page)
    ofd.close()
    
def main () :
    opts = getOpts()
    tr_key = opts.minTR
    tr_max_key = opts.maxTR
    while tr_key <= tr_max_key:
        archiveTR(tr_key, opts.directory)
        if tr_key % 50 == 0:
            print(tr_key, end=' ')
            if tr_key % 1000 == 0:
                print()
            sys.stdout.flush()
        tr_key += 1
    print()

#
main()
