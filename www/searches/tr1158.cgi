#!/usr/local/bin/python

# Example QC report for TR1158

# Shows a table of tracking records for which there is no assigned staff
# member, and which are not done, cancelled, or merged.

import os
import sys
import Configuration
import wtslib
import screenlib
import HTMLgen


results = wtslib.sql ('''
	select tr._TR_key, tr.tr_title, cv.status_name
	from WTS_TrackRec tr, CV_WTS_Status cv
	where   (tr._Status_key = cv._Status_key) and
		(cv.status_name not in ("done", "cancelled", "merged")) and
		tr._TR_key not in (select _TR_key from WTS_Staff_Assignment)
	order by tr._TR_key
	''')

page = screenlib.WTS_Document (title = 'Prototype No-Staff Report')
page.append (HTMLgen.Center ('%s records returned' % len(results)),
	HTMLgen.P())

tbl = HTMLgen.TableLite (border=3, align='center')

tbl.append (HTMLgen.TR (HTMLgen.TH ('TR'), HTMLgen.TH ('Title'),
	HTMLgen.TH ('Status')))

for rec in results:
	row = HTMLgen.TR(
		HTMLgen.TD (HTMLgen.Href ('tr.detail.cgi?TR=%s' % \
				rec['_TR_key'],
				'TR%s' % rec['_TR_key'])),
		HTMLgen.TD (rec['tr_title']),
		HTMLgen.TD (rec['status_name']))
	tbl.append (row)

page.append (tbl)
page.write ()

