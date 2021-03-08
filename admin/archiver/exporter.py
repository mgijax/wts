#
# wts_export_active.py
#
# Exports the active TRs from WTS in CSV format.
# Merges with data from the top-10 spreadsheet.
# Usage:
#     python3 wts_export_active.py top10file.tsv
#

import sys
import db

db.set_sqlServer('bhmgidb01.jax.org')
db.set_sqlDatabase('prod')
db.set_sqlUser('mgd_public')
db.set_sqlPassword('mgdpub')

COMMA = ','
DQ = '"'
NL = '\n'

WTS_DIR='http://wts.informatics.jax.org/wts_projects/'

def mapWtsUser (user) :
    m = {
    }

def mapTop10PI (pi) :
    m = {
        "carol"   : "Carol",
        "cindy"   : "Cindy",
        "joel"    : "Joel",
        "judy"    : "Judy",
        "martin"  : "Martin",
        "richard" : "Richard",
        "bug"     : "",  # ok?
    }
    return m[pi.lower()]

def mapWtsStatus (status) :
    map = {
        "new"          : "Open",
        "notScheduled" : "IS-READY",
        "analysis"     : "Requirements",
        "in-progress"  : "In Progress",
        "test"         : "In Progress",
        "ready"        : "IS-READY",
        "monitoring"   : "Requirements",
        "waiting"      : "Requirements",
        "PI-decide"    : "PI-Decide",
        "design"       : "Requirements",# ok?
        "review"       : "In Progress", # ok?
        "scheduled"    : "IS-READY",    # ok?
        "preliminary"  : "Open",        # ok?
        "study"        : "Open",        # ok?
        # for completeness... (not actually used, because we're only importing open TRs)
        "tabled"       : "Closed",
        "merged"       : "Closed",
        "done"         : "Closed",
        "cancelled"    : "Closed",
    }
    return map[status]

def mapWtsArea (area) :
    map = {
    "backend/custom_sql"     : "Backend/Custom_SQL",
    "backend/data_cleanup"   : "Backend/Data_Cleanup",
    "backend/load"           : "Backend/Load",
    "backend/public_reports" : "Backend/Public_Reports",
    "backend/pwi"            : "Backend/PWI",
    "backend/qc_reports"     : "Backend/QC_Reports",
    "dataMigration"          : "Data",
    "dbAdmin"                : "DB_Admin",
    "EIPerms"                : "Unknown",       # ok?
    "faq"                    : "User_Support",  # ok?
    "frontend/wi_pub"        : "Frontend/WI_Pub",
    "mgihome"                : "Frontend/WI_Pub", # ok?
    "misc"                   : "Misc",
    "mouseBlast"             : "Unknown",       # ok?
    "mtb"                    : "Unknown",       # ok?
    "schema"                 : "DB_Admin",      # ok?
    "seAdmin"                : "Unknown",       # ok?
    "seInfrastructure"       : "Unknown",       # ok?
    "unknown"                : "Unknown",
    "user_support"           : "User_Support",
    "wi"                     : "Frontend/WI_Pub",
    "wi-prod"                : "Backend/PWI",
    }
    return map[area]

def mapWtsPriority (priority) :
    map = {
        "emergengy" : "Highest",
        "high"      : "High",
        "medium"    : "Medium",
        "low"       : "Low",
        "unknown"   : "",
    }
    return map[priority]

def mapRequestorToPI (requestor) :
    map = {
    "anna"    : "Cindy",
    "cjb"     : "Carol",
    "cms"     : "Martin",
    "csmith"  : "Cindy",
    "dbradt"  : "Carol",
    "djr"     : "Carol",
    "dmk"     : "Carol",
    "dph"     : "Judy",
    "drs"     : "Carol",
    "hjd"     : "Judy",
    "honda"   : "Cindy",
    "jak"     : "Joel",
    "jb"      : "Carol",
    "jblake"  : "Judy",
    "jeffc"   : "Joel",
    "jer"     : "Joel",
    "jfinger" : "Martin",
    "jlewis"  : "Richard",
    "jrecla"  : "Carol",
    "jsb"     : "Richard",
    "krc"     : "Judy",
    "kstone"  : "Joel",
    "lec"     : "Joel",
    "ln"      : "Judy",
    "lnh"     : "Richard",
    "marka"   : "Richard",
    "mdolan"  : "Judy",
    "mmh"     : "Carol",
    "mnk"     : "Cindy",
    "pf"      : "Joel",
    "ringwald": "Martin",
    "rmb"     : "Richard",
    "sc"      : "Richard",
    "smb"     : "Cindy",
    "smc"     : "Carol",
    "wilmil"  : "Cindy",
    "yz"      : "Carol",
    }
    return map[requestor]

def getTop10 (fname) :
    tr2top10 = {}
    fd = open(fname, 'r')
    for line in fd:
        cols = line.split('\t')
        if cols[0] == "TR" and cols[1] == "Priority":
            continue
        tr = int(cols[5])
        pi = mapTop10PI(cols[2])
        pri = cols[1]
        tr2top10[tr] = (pi,pri)
    fd.close()
    return tr2top10

def getAreas () :
    q_areas = '''
        SELECT
            t._tr_key,
            a.area_name
        FROM
            wts_trackrec t,
            wts_area ta,
            cv_wts_area a
        WHERE
            t._status_key not in (11, 12, 13, 14)
        AND t._tr_key = ta._tr_key
        AND ta._area_key = a._area_key
        '''
    tr2areas = {}
    for r in db.sql(q_areas):
        tr2areas.setdefault(r['_tr_key'], []).append(mapWtsArea(r['area_name']))
    return tr2areas

def getStatusHistory () :
    q_statusHistory = '''
        SELECT
            t._tr_key,
            h.set_date,
            s.status_name,
            u.staff_username
        FROM
            wts_trackrec t,
            wts_status_history h,
            cv_wts_status s,
            cv_staff u
        WHERE
            t._status_key not in (11, 12, 13, 14)
        AND t._tr_key = h._tr_key
        AND h._status_key = s._status_key
        AND h._staff_key = u._staff_key
        '''
    tr2history = {}
    for r in db.sql(q_statusHistory):
        tr2history.setdefault(r['_tr_key'],[]).append((r['status_name'],r['set_date'],r['staff_username']))
    return tr2history

def getRequestedBy () :
    q_requestedBy = '''
        SELECT
            t._tr_key,
            u.staff_username
        FROM
            wts_trackrec t,
            wts_requested_by r,
            cv_staff u
        WHERE
            t._status_key not in (11, 12, 13, 14)
        AND t._tr_key = r._tr_key
        AND r._staff_key = u._staff_key
        '''
    tr2requestors = {}
    for r in db.sql(q_requestedBy) :
        # there can be multiples, but most are just 1
        tr2requestors[r['_tr_key']] = r['staff_username']
    return tr2requestors

def getActiveTRs (tr2top10) :
    global maxAreas
    tr2requestors = getRequestedBy()
    tr2status = getStatusHistory()
    tr2areas = getAreas()
    #
    q_activeTRs = '''
        SELECT
            t._tr_key,
            t.tr_title,
            p.priority_name,
            s.status_name,
            t.status_set_date,
            t.directory_variable,
            t.creation_date,
            t.modification_date
        FROM
            wts_trackrec t,
            cv_wts_priority p,
            cv_wts_status s
        WHERE
            t._status_key not in (11, 12, 13, 14)
        AND t._priority_key = p._priority_key
        AND t._status_key = s._status_key
        ORDER BY t._tr_key
        '''
    recs = db.sql(q_activeTRs)
    maxAreas = 0
    for r in recs:
        r['requestedBy'] = tr2requestors.get(r['_tr_key'],"")
        #
        wtsPi = mapRequestorToPI(r['requestedBy'])
        t10pi,t10sort = tr2top10.get(r['_tr_key'], ("",""))
        r['pi'] = t10pi if t10pi else wtsPi
        r['piSort'] = t10sort
        #
        r['areas'] = tr2areas.get(r['_tr_key'],[])
        maxAreas = max(maxAreas, len(r['areas']))
        r['statusHistory'] = tr2status.get(r['_tr_key'],[])
        r['top10'] = tr2top10.get(r['_tr_key'], ("",""))
        r['status_name'] = mapWtsStatus(r['status_name'])
        r['priority'] = mapWtsPriority(r['priority_name'])
        r['directory_url'] = '' if r['directory_variable'] in [None,"None"] else WTS_DIR + r['directory_variable']
        r['summary'] = '%s (TR%d)' % (r['tr_title'], r['_tr_key'])
        pdir = int(r['_tr_key'] / 100) * 100
        r['description'] = WTS_DIR + ("archive/%s/TR%d.html" % (pdir, r['_tr_key'])) + '\nRequested by: ' + r['requestedBy']
        r['labels'] = ['WTS1', 'Top_10' if t10pi else '']
    return recs

def quote (v) :
    vs = str(v)
    if '"' in vs or ',' in vs or '\n' in vs:
        return '"%s"' % vs.replace('"', '""')
    else:
        return vs

def printCsv (rec) :
    line = COMMA.join(map(lambda f: quote(f), rec))
    print(line)

def printTR (tr) :
    global maxAreas
    areas = tr['areas'] + (maxAreas - len(tr['areas'])) * ['']
    rec = [
        tr['summary'],
        tr['description'],
        tr['pi'],
        tr['piSort'],
        tr['directory_url'],
        tr['status_name'],
        tr['priority'],
        tr['labels'][0],
        tr['labels'][1],
    ] + areas
    printCsv(rec)

def printHeaderLine ():
    global maxAreas
    colHdrs = [
        "Summary",
        "Description",
        "PI",
        "Sort Order",
        "TR directory",
        "Status",
        "Priority",
        "Labels",
        "Labels",
    ] + maxAreas * ['Components']
    printCsv(colHdrs)

def main () :
    tr2top10 = getTop10(sys.argv[1])
    for i,r in enumerate(getActiveTRs(tr2top10)):
        if i == 0:
            printHeaderLine()
        printTR(r)

###
main()
