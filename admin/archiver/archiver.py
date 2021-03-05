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
import db

db.set_sqlServer('bhmgidb01.jax.org')
db.set_sqlDatabase('prod')
db.set_sqlUser('mgd_public')
db.set_sqlPassword('mgdpub')

url_tmplt = 'http://wts.informatics.jax.org/searches/tr.detail.cgi?TR_Nr=%d'
trfile_tmplt = 'TR%d.html'
hdr = { "Authorization": "Basic amVyOmplbjY4Yg==" }
not_found = b'WTS2.0: Cant Find Tracking Record'
ARCHIVE_DIR = '/mgi/all/wts_projects/archive'

def getOpts () :
    q = '''SELECT min(_tr_key), max(_tr_key) FROM "wts"."wts_trackrec";'''
    minmax = db.sql(q)[0]
    #
    parser = ArgumentParser()
    parser.add_argument(
      "-m", "--minTR",
      default=minmax['min'],
      type=int,
      help="Minimum TR number. Default=%(default)d.")
    parser.add_argument(
      "-M", "--maxTR",
      default=minmax['max'],
      type=int,
      help="Maximum TR number. Default=%(default)d.")
    parser.add_argument(
      "-d", "--directory",
      default=ARCHIVE_DIR,
      help="Output directory. Default=%(default)s")
    return parser.parse_args()

def archiveTR (tr_key, archive_dir) :
    url = url_tmplt % tr_key
    req = Request(url, headers=hdr)
    fd = urlopen(req)
    page = fd.read()
    fd.close()
    if page.find(not_found) >= 0:
        # tr not valid
        sys.stdout.write('? ')
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
            sys.stdout.write(str(tr_key) + ' ')
            if tr_key % 1000 == 0:
                sys.stdout.write('\n')
            sys.stdout.flush()
        tr_key += 1
    sys.stdout.write('\n')

#
main()
