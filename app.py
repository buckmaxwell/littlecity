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


# TEXT EDITING ##########################################################################################

@app.route('/text', methods=['POST'])
def text():
    
    # update the postgresql record
    edit_id = request.form['edit_id']
    text = request.form['text']

    try:
        conn = get_connection()
        cur = conn.cursor()
        text.decode('ascii')
        cur.execute("UPDATE edits SET text=%s where id=%s;", (text, edit_id))
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


@app.route("/")
def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT text, end_edit from edits where text IS NOT NULL order by end_edit desc limit 1")
    try:
        last_text = cur.fetchone()[0]
    except:
        last_text = 'Start us off why don\'t you'

    stylesheet = url_for('static', filename='style.css')
    about = url_for('static', filename='about.html')
    conn.close()

    # get mod comment
    with open('about.md', 'r') as f:
        mod_comment = f.read()

    return """
    <!DOCTYPE html>
    <!--
    {comment}
    -->
    {text}
    """.format(text=last_text, comment=mod_comment)


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
        cur.execute("UPDATE style_edits SET text=%s where id=%s;", (text, edit_id))
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