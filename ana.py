#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2, urllib, re, sys, sqlite3, datetime, hashlib

url = "http://amor.revistaana.pt/hp_ana.aspx"
conn = sqlite3.connect('ana.db')
conn.row_factory = sqlite3.Row
"""
CREATE TABLE ana (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data TEXT,
  numero TEXT,
  mensagem TEXT,
  UNIQUE(data, numero)
);
"""

def get_gay_vars(page_source):
    result = {}
    match = re.search('id="__EVENTVALIDATION" value="(.*)" />', page_source, re.MULTILINE)
    result['__EVENTVALIDATION'] = match.group(1)
    match = re.search('id="__VIEWSTATE" value="(.*)" />', page_source, re.MULTILINE)
    result['__VIEWSTATE'] = match.group(1)
    return result

def get_page(number=0, postvars={}):
    if number > 0:
        postvars['currentPage'] = number
        postvars['mheader1$txtSearch'] = ''
        postvars['mheader1$sdate'] = 'ultimodia'
        postvars['hdnsdate'] = 'ultimodia'
    data = urllib.urlencode(postvars)
    user_agent = 'Benfica/Glorioso (Ultrix-11) ZBR'
    headers = { 'User-Agent' : user_agent }
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    page_source = response.read()
    return page_source

def parse_page(page_source):
    result = []
    for match in re.finditer('(?sm)<div class="sms">(?P<all>(.|\n|\r\n)*?)<div class="cB">', page_source, re.UNICODE):
        item = {}
        iteminfo = match.group("all")
        matchi = re.search('<p class="smstxt">(?P<mensagem>.*)</p>', iteminfo, re.UNICODE)
        if matchi is None:
            continue
        item['msg'] = matchi.group("mensagem")
        matchi = re.search('<div class="tm rosac"><img src="img/ana/tm.png" width="16" height="16">Tm.: (?P<num>.*?)</div>', iteminfo)
        item['num'] = matchi.group("num")
        matchi = re.search('<div class="data rosac"><img src="img/ana/calend.png" width="16" height="16"> (?P<data>.*?)</div>', iteminfo)
        item['data'] = matchi.group("data")
        matchi = re.search('<div class="hora rosac"><img src="img/ana/relog.png" width="16" height="16"> (?P<hora>.*?)</div>', iteminfo)
        item['hora'] = matchi.group("hora")
        result.append(item)
    return result

def get_total_pages(page_source):
    match = re.search(r'<a href="javascript:GoToPage\((\d+)\)" class="">', page_source)
    return int(match.group(1))

def add_records(items):
    print 'inserting page...'
    for item in items:
        dt = datetime.datetime.strptime(item['data'] + ' ' + item['hora'], "%d.%m.%Y %Hh %Mm")
        msg = item['msg'].decode('utf-8')
        print "%s" % msg
        conn.execute('insert into ana (data, numero, mensagem) values(?, ?, ?)', (dt, item['num'].replace(' ',''), msg) )
        conn.commit()
    print 'done'

def get_random():
    c = conn.execute('select id, data, numero, mensagem from ana ORDER BY RANDOM() LIMIT 1;')
    rows = c.fetchall()[0]
    msg = "%s - %s, %s" % (rows[3], rows[2], rows[1])
    return msg

def find_record(find, position = 0):
    sql = 'select count(1) from ana where mensagem like ?'
    args = ['%'+find+'%']
    c = conn.execute(sql, args)
    total = c.fetchone()[0]
    if total == 0 or int(position) > int(total-1):
        print "Not found"
        sys.exit()
    if total > 1 and position == 0:
        print "%d found '.fm %s %d' for the next one" % (total, find, position + 1)

    sql = 'select id, data, numero, mensagem from ana WHERE mensagem like ? ORDER BY data LIMIT ?,1'
    args = ['%'+find+'%', position]
    c = conn.execute(sql, args)
    rows = c.fetchall()[0]
    msg = "%s - %s, %s" % (rows[3], rows[2], rows[1])
    return msg

def update_records():
     page = get_page()
     total = get_total_pages(page)
     postcrap = get_gay_vars(page)
     try:
         add_records(parse_page(page))
     except sqlite3.IntegrityError:
         return

     for i in range(1,total):
        page = get_page(i, postcrap)
        postcrap = get_gay_vars(page)
        items = parse_page(page)
        try:
            add_records(items)
        except sqlite3.IntegrityError:
            return

def loljews(s):
    sql = 'select count(1) from ana'
    c = conn.execute(sql)
    total = c.fetchone()[0]

    h = hashlib.sha256(s).hexdigest()
    n = int(h, 16)
    myid = n % total

    c = conn.execute('select id, data, numero, mensagem from ana where id = ?;', [myid])
    rows = c.fetchall()[0]
    msg = "%s - %s, %s" % (rows[3], rows[2], rows[1])
    return msg


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print get_random()
    if len(sys.argv) > 1:
        if sys.argv[1] == 'cron':
            print 'Updating...'
            update_records()
        elif sys.argv[1] == 'find':
            if len(sys.argv) == 2:
                print "find argument required"
                sys.exit()
            try:
                pos = int(sys.argv[-1])
                msg = ' '.join(sys.argv[2:][:-1])
            except ValueError:
                pos = 0
                msg = ' '.join(sys.argv[2:])
            print find_record(msg, pos)
        elif sys.argv[1] == 'magia':
            if len(sys.argv) > 2:
                print loljews(''.join(sys.argv[2:]))
            else:
                print get_random()


    conn.close()
