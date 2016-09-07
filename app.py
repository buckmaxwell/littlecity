from __future__ import unicode_literals
from flask import Flask, request, url_for
from bs4 import BeautifulSoup as bs
import datetime
from collections import OrderedDict
import uuid
import os
import psycopg2
import urlparse
import pytz
import json
import markdown


# set expires to some time in the past to avoid browser caching
headers = {'Expires': 'Expires: Thu, 01 Dec 1994 16:00:00 GMT'}
app = Flask(__name__)
app.config['DEBUG'] = True

time_per_edit = 25
utc=pytz.UTC


def get_connection():
    # create psycopg2 connection
    urlparse.uses_netloc.append("postgres")
    url = urlparse.urlparse(os.environ["DATABASE_URL"])
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    return conn


# Setup database

#table_setup = """
#CREATE TABLE IF NOT EXISTS edits (id varchar, start_edit timestamp with time zone, 
#    end_edit timestamp with time zone, text varchar);
#CREATE TABLE IF NOT EXISTS style_edits (id varchar, start_edit timestamp with time zone, 
#    end_edit timestamp with time zone, text varchar);
#"""
#conn = get_connection()
#cur = conn.cursor()
#cur.execute(table_setup)
#conn.close()

# INFO ##################################################################################################
@app.route('/info', methods=['GET'])
def info():
    with open('about.md') as f:
        t = f.read()

    result_html = markdown.markdown(t)

    return result_html


# TEXT EDITING ##########################################################################################

@app.route('/text', methods=['POST'])
def text():
    
    # update the postgresql record
    edit_id = request.form['edit_id']
    text = request.form['text']
    ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr)

    try:
        conn = get_connection()
        cur = conn.cursor()
        text.decode('ascii')
        cur.execute("UPDATE edits SET text=%s, ip_addr=%s  where id=%s;", (text, ip_addr, edit_id))
        conn.commit()
        conn.close()
    except UnicodeEncodeError:
        print "it was not a ascii-encoded unicode string"

    return 'redirecting you...', 302, {'Location': '/'}


@app.route('/text/edit', methods=['GET'])
def edit_wait():
    conn = get_connection()
    cur = conn.cursor()
    edit_id = str(uuid.uuid4())
    #edit = dict(id=edit_id, start_edit=None, end_edit=None)

    time_to_wait = 0

    cur.execute("SELECT end_edit from edits order by end_edit desc limit 1")
    try:
        last_edit_scheduled = cur.fetchone()[0]
    except:
        last_edit_scheduled = None

    if last_edit_scheduled and last_edit_scheduled > utc.localize(datetime.datetime.utcnow()):
        time_to_wait = (last_edit_scheduled - utc.localize(datetime.datetime.utcnow())).total_seconds()

    start_edit = utc.localize(datetime.datetime.utcnow()) +\
                         datetime.timedelta(seconds=time_to_wait)

    end_edit = utc.localize(datetime.datetime.utcnow()) +\
                       datetime.timedelta(seconds=time_to_wait + time_per_edit)

    # add the record to postgressql
    cur.execute("INSERT INTO edits (id, start_edit, end_edit) values (%s, %s, %s);",
     (edit_id, start_edit, end_edit))
    conn.commit()

    result =  """
    <html>
    <head>
        <h4>Please wait while others finish editing.  If you refresh this page 
        you will lose you spot in line.  At the right time, you will be redirected</h4>

        <h4>Another option is to visit /text/edit/{edit_id} sometime after your wait 
        is period is done</h4>

        <p>your wait is {wait} seconds</p>

        <meta http-equiv="refresh" content="{wait}; url=/text/edit/{edit_id}" />
    </head>
    <body>
    <p>""".format(wait=time_to_wait, edit_id=edit_id)
    conn.close()
    return result, 200, headers


@app.route('/text/edit/<edit_id>', methods=['GET'])
def edit(edit_id):
    conn = get_connection()
    cur = conn.cursor()

    # Make sure the edit id is not expired
    cur.execute("SELECT end_edit from edits where id=%s limit 1;", (edit_id,))
    try:
        end_edit = cur.fetchone()[0]
        utc.localize(datetime.datetime.utcnow())
        if utc.localize(datetime.datetime.utcnow()) > end_edit:
            return "End time already expired", 400
        else:
            time_per_edit = (end_edit - utc.localize(datetime.datetime.utcnow())).total_seconds()
    except Exception as e:
        print e

        return "Edit id does not exist....", 404

    cur.execute("SELECT text from edits where text IS NOT NULL order by end_edit desc limit 1")
    try:
        last_text = cur.fetchone()[0]
        soup = bs(last_text)
        last_text = soup.prettify()
    except:
        last_text = 'Start us off why don\'t you'

    result = """
<html>
<head>
    <title>LittleCity</title>
    <meta http-equiv="refresh" content="{time_per_edit}; url=/" />
</head>
<body>
<form id="main" action="/text" method="post">
 <textarea name="text" form="main" rows="50" cols="150">
 {text}
 </textarea>
 <input name="edit_id" type="hidden" value="{edit_id}">
 <input type="submit" value="Submit">
</form>
</body>
</html>
    """.format(text=last_text, edit_id=edit_id, time_per_edit=time_per_edit )
    conn.close()
    return result, 200, headers

@app.route("/ip")
def ip():
    return str(request.headers)


@app.route("/unique_visitors")
def uniq():
    # Establish connection
    conn = get_connection()
    cur = conn.cursor()
    #cur.execute("SELECT count(*) from edits where text IS NOT NULL order by end_edit desc limit 1")
    cur.execute("SELECT count(*) FROM (SELECT count(*) AS _ FROM visitors GROUP BY ip_addr) AS uniq_ips;")
    try:

        unique_visitors = cur.fetchone()[0]
        unique_visitors = {'unique_visitor_count': unique_visitors}
    except Exception as e:
        print e
        unique_visitors = {'unique_visitor_count': 'There was a problem'}

    conn.close()

    return json.dumps(unique_visitors), 200, headers


@app.route("/history/<number>")
def history(number):
    # Establish connection
    conn = get_connection()
    cur = conn.cursor()

    # Record visitor ip address
    ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
    timestamp = utc.localize(datetime.datetime.utcnow())
    cur.execute("INSERT INTO visitors (ip_addr, timestamp) VALUES (%s, %s);", (ip_addr, timestamp))
    conn.commit()

    # Get last text
    cur.execute("SELECT text, end_edit, number from edits where number >= %s and text is not null order by number limit 1", (number,))
    try:
        text, end_edit, new_number = cur.fetchone()
    except:
        text = 'Start us off why don\'t you'
        new_number = None

    if new_number and int(number) != int(new_number):
        conn.close()
        return 'redirecting you...', 302, {'Location': '/history/{}'.format(new_number)}
    if not new_number:
        return 'The page number you requested is in the future...', 404, headers

    # Get matching css
    cur.execute("SELECT text, end_edit FROM style_edits WHERE end_edit <= %s and text is not null order by end_edit desc limit 1;", 
        (end_edit,))
    try:
        css = cur.fetchone()[0]
    except:
        css = ''

    conn.close()

    # get mod comment
    with open('about.md', 'r') as f:
        mod_comment = f.read()

    return """
<!DOCTYPE html>
<!--
{comment}
-->
<style>
{style}
</style>
{text}""".format(text=text, comment=mod_comment, style=css)



@app.route("/")
def main():
    # Establish connection
    conn = get_connection()
    cur = conn.cursor()

    # Get last text number
    cur.execute("SELECT number, end_edit from edits where text IS NOT NULL order by end_edit desc limit 1;")
    try:
        last_number = cur.fetchone()[0]
        conn.close()
    except Exception as e:
        print e
        conn.close()
        return "Error finding most recent page"

    return 'redirecting you...', 302, {'Location': '/history/{}'.format(last_number)}



# CSS EDITING #############################################################################################


@app.route('/css', methods=['POST'])
def css():

    try:
        conn = get_connection()
        cur = conn.cursor()
        #    update the postgresql record
        text = request.form['text']
        text.decode('ascii')
        edit_id = request.form['edit_id']
        ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr)

        cur.execute("UPDATE style_edits SET text=%s, ip_addr=%s where id=%s;", (text, ip_addr, edit_id))
        conn.commit()
        with open('static/style.css', 'w+') as f:
            f.write(request.form['text'])

        conn.close()
    except UnicodeEncodeError:
        print "string is not ascii"
    
    return 'redirecting you...', 302, {'Location': '/'}


@app.route('/css/edit', methods=['GET'])
def css_edit_wait():
    conn = get_connection()
    cur = conn.cursor()

    edit_id = str(uuid.uuid4())
    time_to_wait = 0

    cur.execute("SELECT end_edit from style_edits order by end_edit desc limit 1")
    try:
        last_edit_scheduled = cur.fetchone()[0]
    except:
        last_edit_scheduled = None

    if last_edit_scheduled and last_edit_scheduled > utc.localize(datetime.datetime.utcnow()):
        time_to_wait = (last_edit_scheduled - utc.localize(datetime.datetime.utcnow())).total_seconds()

    start_edit = utc.localize(datetime.datetime.utcnow()) +\
                         datetime.timedelta(seconds=time_to_wait)

    end_edit = utc.localize(datetime.datetime.utcnow()) +\
                       datetime.timedelta(seconds=time_to_wait + time_per_edit)

    # add the record to postgressql
    cur.execute("INSERT INTO style_edits (id, start_edit, end_edit) values (%s, %s, %s);",
     (edit_id, start_edit, end_edit))
    conn.commit()

    result =  """
    <html>
    <head>

        <h4>Please wait while others finish editing.  If you refresh this page 
        you will lose your spot in line.  At the right time, you will be redirected</h4>

        <h4>Another option is to visit /css/edit/{edit_id} sometime after your wait 
        is period is done</h4>

        <p>your wait is {wait} seconds</p>
        
        <meta http-equiv="refresh" content="{wait}; url=/css/edit/{edit_id}" />
    </head>
    <body>
    <p>""".format(wait=time_to_wait, edit_id=edit_id)
    conn.close()
    return result, 200, headers


@app.route('/css/edit/<edit_id>', methods=['GET'])
def css_edit(edit_id):
    with open('static/style.css', 'r') as f:
        style_sheet = f.read()

    # Make sure the edit id is not expired
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT end_edit from style_edits where id=%s limit 1;", (edit_id,))

    try:
        end_edit = cur.fetchone()[0]
        conn.close()
        if utc.localize(datetime.datetime.utcnow()) > end_edit:
            return "End time already expired", 400
        else:
            time_per_edit = (end_edit - utc.localize(datetime.datetime.utcnow())).total_seconds()
            conn.close()
    except Exception as e:
        print e
        return "Edit id does not exist....", 404


    result = """
    <html>
    <head>
        <title>LittleCity</title>
        <meta http-equiv="refresh" content="{time_per_edit}; url=/" />
    </head>
    <body>
    <form id="main" action="/css" method="post">
     
     <textarea name="text" form="main" rows="50" cols="150">
     {text}
     </textarea>
     <input name="edit_id" type="hidden" value="{edit_id}">
     <input type="submit" value="Submit">
    </form>
    </body>
    </html>
    """.format(text=style_sheet, edit_id=edit_id, time_per_edit=time_per_edit )
    return result, 200, headers


@app.route("/css")
def css_main():
    with open('style.css', 'r') as f:
        style_sheet = f.read()
    
    return "{}".format(style_sheet)



# FLASK STUFF ###################################################################################



if __name__ == "__main__":
    app.run(debug=True)