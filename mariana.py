#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2, urllib, re, sys, sqlite3, datetime, hashlib, time
import mylib

class MyException(Exception): pass

conn = sqlite3.connect('mariana.db')
conn.row_factory = sqlite3.Row
"""
CREATE TABLE sms ( 
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    data     TEXT,
    numero   TEXT,
    mensagem TEXT,
    origem   CHAR 
);
"""

def get_aspx_vars(page_source):
    result = {}
    match = re.search('id="__EVENTVALIDATION" value="(.*)" />', page_source, re.MULTILINE)
    result['__EVENTVALIDATION'] = match.group(1)
    match = re.search('id="__VIEWSTATE" value="(.*)" />', page_source, re.MULTILINE)
    result['__VIEWSTATE'] = match.group(1)
    return result

def get_page(url, page=0, postvars={}):
    if page > 0:
        postvars['currentPage']         = page
        postvars['mheader1$txtSearch']  = ''
        postvars['mheader1$sdate']      = 'ultimodia'
        postvars['hdnsdate']            = 'ultimodia'
    data = urllib.urlencode(postvars)
    user_agent = 'Benfica/Glorioso (Ultrix-11) ZBR'
    headers = { 'User-Agent' : user_agent }
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    page_source = response.read()
    return page_source

def parse_ana_page(page_source,last_timestamp):
    result = []
    for match in re.finditer('(?sm)<div class="sms">(?P<all>(.|\n|\r\n)*?)<div class="cB">', page_source, re.UNICODE):
        item = {}
        iteminfo = match.group("all")
        matchi = re.search('<p class="smstxt">(?P<mensagem>.*)</p>', iteminfo, re.UNICODE)
        if matchi is None:
            continue
        msg = matchi.group("mensagem")
        item['msg'] = msg.decode('utf-8')
        matchi = re.search('<div class="tm rosac"><img src="img/ana/tm.png" width="16" height="16">Tm.: (?P<num>.*?)</div>', iteminfo)
        item['num'] = matchi.group("num").replace(' ','')
        matchi = re.search('<div class="data rosac"><img src="img/ana/calend.png" width="16" height="16"> (?P<data>.*?)</div>', iteminfo)
        item['data'] = matchi.group("data")
        matchi = re.search('<div class="hora rosac"><img src="img/ana/relog.png" width="16" height="16"> (?P<hora>.*?)</div>', iteminfo)
        item['hora'] = matchi.group("hora")
        ts = datetime.datetime.strptime(item['data'] + ' ' + item['hora'], "%d.%m.%Y %Hh %Mm")
        item['ts'] = str(time.mktime(ts.timetuple()))[:-2]
        if int(item['ts']) <= int(last_timestamp):
            continue
        result.append(item)
    if len(result) == 0:
        raise MyException("benfica")
    return result

def parse_maria_page(page_source,last_timestamp):
    result = []
    for match in re.finditer('(?sm)<div class="smstop"></div>(?P<all>(.|\n|\r\n)*?)<div class="smsbot">', page_source, re.UNICODE):
        item = {}
        iteminfo = match.group("all")
        matchi = re.search('<p class="smstxt">(?P<mensagem>.*)</p>', iteminfo, re.UNICODE)
        if matchi is None:
            continue
        msg = matchi.group("mensagem")
        item['msg'] = msg.decode('utf-8')
        matchi = re.search('<div class="tm"><img class="icon" src="img/maria/tm.png" width="16" height="16"> Tm.: (?P<num>.*?)</div>', iteminfo)
        item['num'] = matchi.group("num").replace(' ','')
        matchi = re.search('<div class="data"><img class="icon" src="img/maria/calend.png" width="16" height="16"> (?P<data>.*?)</div>', iteminfo)
        item['data'] = matchi.group("data")
        matchi = re.search('<div class="hora"><img class="icon" src="img/maria/relog.png" width="16" height="16"> (?P<hora>.*?)</div>', iteminfo)
        item['hora'] = matchi.group("hora")
        ts = datetime.datetime.strptime(item['data'] + ' ' + item['hora'], "%d.%m.%Y %Hh %Mm")
        item['ts'] = str(time.mktime(ts.timetuple()))[:-2]
        if int(item['ts']) <= int(last_timestamp):
            continue        
        result.append(item)
    if len(result) == 0:
        raise MyException("benfica")

    return result

def get_total_pages(page_source):
    match = re.search(r'<a href="javascript:GoToPage\((\d+)\)" class="">', page_source)
    return int(match.group(1))

def add_records(items,origem):
    for item in items:
        conn.execute('insert into sms (data, numero, mensagem, origem) values(?, ?, ?, ?)', [item['ts'], item['num'], item['msg'], origem])
        conn.commit()

def get_random():
    c = conn.execute('select id, data, numero, mensagem, origem from sms ORDER BY RANDOM() LIMIT 1;')
    rows = c.fetchall()[0]
    msg = "%s - %s, %s [%s]" % (rows[3], rows[2], rows[1], rows[4])
    return msg

def find_record(find, position = 0):
    sql = 'select count(1) from sms where mensagem like ?'
    args = ['%'+find+'%']
    c = conn.execute(sql, args)
    total = c.fetchone()[0]
    if total == 0 or int(position) > int(total-1):
        mylib.print_console("Not found")
        sys.exit()
    if total > 1 and position == 0:
        mylib.print_console("%d found '.fm %s %d' for the next one" % (total, find, position + 1))

    sql = 'select id, data, numero, mensagem, origem from sms WHERE mensagem like ? ORDER BY data LIMIT ?,1'
    args = ['%'+find+'%', position]
    c = conn.execute(sql, args)
    rows = c.fetchall()[0]
    msg = "%s - %s, %s [%s]" % (rows[3], rows[2], rows[1], rows[4])
    return msg

def get_latest_record_ts(origem):
    sql = 'select max(data) from sms where origem = ?'
    c = conn.execute(sql,[origem])
    zbr = c.fetchone()
    if zbr[0] is None:
        return 0
    else:
        data = zbr[0]
        return int(data)

def update_records(revista):
    
    if revista == "a":
        url = "http://amor.revistaana.pt/hp_ana.aspx"
        print "updating ana"
    if revista == "m":
        url = "http://mensagens.maria.pt/hp_maria.aspx"
        print "updating maria"
    
    lastts = get_latest_record_ts(revista)
    print "lastts: %s" % lastts

    page = get_page(url)
    total = get_total_pages(page) + 1
    print "total: %s" % total
    postcrap = get_aspx_vars(page)

    try:
        if revista == "a":
            items = parse_ana_page(page,lastts)
        elif revista == "m":
            items = parse_maria_page(page,lastts)
        add_records(items,revista)
    except MyException:
        return

    for i in range(1,total):
        mylib.print_console("parsing page %d - %s" % (i, revista))
        page = get_page(url, i, postcrap)
        postcrap = get_aspx_vars(page)
        try:
            if revista == "a":
                items = parse_ana_page(page,lastts)
            elif revista == "m":
                items = parse_maria_page(page,lastts)
        except MyException:
            return
        add_records(items,revista)

def get_magic_random(s):
    sql = 'select count(1) from sms'
    c = conn.execute(sql)
    total = c.fetchone()[0]

    h = hashlib.sha256(s).hexdigest()
    n = int(h, 16)
    myid = n % total

    c = conn.execute('select id, data, numero, mensagem, origem from sms where id = ?;', [myid])
    rows = c.fetchall()[0]
    msg = "%s - %s, %si [%s]" % (rows[3], rows[2], rows[1], rows[4])
    return msg


if __name__ == "__main__":
    if len(sys.argv) == 1:
        mylib.print_console(get_random())
    if len(sys.argv) > 1:
        if sys.argv[1] == 'cron':
            mylib.print_console('Updating...')
            update_records('m')
            update_records('a')
        elif sys.argv[1] == 'find':
            if len(sys.argv) == 2:
                mylib.print_console("find argument required")
                sys.exit()
            try:
                pos = int(sys.argv[-1])
                msg = ' '.join(sys.argv[2:][:-1])
            except ValueError:
                pos = 0
                msg = ' '.join(sys.argv[2:])
            mylib.print_console(find_record(msg, pos))
        elif sys.argv[1] == 'magia':
            # desactivado por causa de ID que saltam
            #if len(sys.argv) > 2:
            #    mylib.print_console(get_magic_random(''.join(sys.argv[2:])))
            #else:
            mylib.print_console(get_random())

    conn.close()
