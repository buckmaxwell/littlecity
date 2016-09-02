from __future__ import unicode_literals
from flask import Flask, request, url_for
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
    conn = get_connection()
    cur = conn.cursor()
    # update the postgresql record
    edit_id = request.form['edit_id']
    text = request.form['text']
    cur.execute("UPDATE edits SET text=%s where id=%s;", (text, edit_id))
    conn.commit()
    conn.close()
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
        <h1>Slate</h1>
        <h4>please wait while others finish editing.  If you refresh this page 
        you will lose you spot in line.  At the right time, you will be redirected</h4>
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
    except:
        last_text = 'Start us off why don\'t you'

    result = """
    <html>
    <head>
        <title>Slate</title>
        <meta http-equiv="refresh" content="{time_per_edit}; url=/" />
    </head>
    <body>
    <form id="main" action="/text" method="post">

     <h1>Slate</h1>
     <h4>feel free to modify the text below</h4>
     
     <textarea name="text" form="main" rows="50" cols="50">
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
    conn.close()
    return """
     <html>
     <head>
        <title>Slate</title>
        <meta http-equiv="refresh" content="5; url=/" />
        <link rel="stylesheet" type="text/css" href="{stylesheet}">
     </head>
     <body>
     <h1>Slate</h1>
     <h4>feel free to modify the text below</h4>
     {text}
     <form action="text/edit" method="get"><input type="submit" value="Edit Text"></form>
     <form action="css/edit" method="get"><input type="submit" value="Edit CSS"></form>
     </body>
     </html>
    """.format(text=last_text, stylesheet=stylesheet)


# CSS EDITING #############################################################################################


@app.route('/css', methods=['POST'])
def css():
    conn = get_connection()
    cur = conn.cursor()
    # update the postgresql record
    edit_id = request.form['edit_id']
    text = request.form['text']
    cur.execute("UPDATE style_edits SET text=%s where id=%s;", (text, edit_id))
    conn.commit()
    with open('static/style.css', 'w+') as f:
        f.write(request.form['text'])
    conn.close()
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
        <h1>Slate</h1>
        <h4>please wait while others finish editing.  If you refresh this page 
        you will lose you spot in line.  At the right time, you will be redirected</h4>
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
        <title>Slate</title>
        <meta http-equiv="refresh" content="{time_per_edit}; url=/" />
    </head>
    <body>
    <form id="main" action="/css" method="post">

     <h1>Slate</h1>
     <h4>feel free to modify the text below</h4>
     
     <textarea name="text" form="main" rows="100" cols="50">
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