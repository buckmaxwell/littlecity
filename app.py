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

last_text = {'text':'LAST TEXT', 'last_edit_scheduled':None}  # last edit scheduled is the end time of the 
															  # last edit scheduled
last_css = {'text':'h1 {color: red;}', 'last_edit_scheduled':None}

edits = OrderedDict()  # {id:UUID, start_edit:datetime, end_edit:datetime, text=str}
style_edits = OrderedDict()
time_per_edit = 25
utc=pytz.UTC


# Setup database
table_setup = """
CREATE TABLE IF NOT EXISTS edits (id varchar, start_edit timestamp with time zone, 
	end_edit timestamp with time zone, text varchar);
CREATE TABLE IF NOT EXISTS style_edits (id varchar, start_edit timestamp with time zone, 
	end_edit timestamp with time zone, text varchar);
"""
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
cur = conn.cursor()
cur.execute(table_setup)


# TEXT EDITING ##########################################################################################

@app.route('/text', methods=['POST'])
def text():
	# update the postgresql record
	edit_id = request.form['edit_id']
	text = request.form['text']
	cur.execute("UPDATE edits SET text=%s where id=%s;", (text, edit_id))
	#print request.form['text']
	last_text['text'] = request.form['text']
	return 'redirecting you...', 302, {'Location': '/'}


@app.route('/text/edit', methods=['GET'])
def edit_wait():
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
	return result, 200, headers


@app.route('/text/edit/<edit_id>', methods=['GET'])
def edit(edit_id):
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
     
     <textarea name="text" form="main" rows="100" cols="50">
     {text}
     </textarea>
     <input name="edit_id" type="hidden" value="{edit_id}">
     <input type="submit" value="Submit">
    </form>
    </body>
    </html>
    """.format(text=last_text['text'], edit_id=edit_id, time_per_edit=time_per_edit )
    return result, 200, headers


@app.route("/")
def main():
    stylesheet = url_for('static', filename='style.css')
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
    """.format(text=last_text['text'], stylesheet=stylesheet)


# CSS EDITING #############################################################################################


@app.route('/css', methods=['POST'])
def css():
	print request.form['text']
	#last_css['css'] = request.form['css']
	with open('static/style.css', 'w+') as f:
		f.write(request.form['text'])
	return 'redirecting you...', 302, {'Location': '/'}


@app.route('/css/edit', methods=['GET'])
def css_edit_wait():
	edit_id = str(uuid.uuid4())
	edit = dict(id=edit_id, start_edit=None, end_edit=None)
	time_to_wait = 0

	if last_css['last_edit_scheduled'] and last_css['last_edit_scheduled'] > utc.localize(datetime.datetime.utcnow()):
		time_to_wait = (last_css['last_edit_scheduled'] - utc.localize(datetime.datetime.utcnow())).total_seconds()

	edit['start_edit'] = utc.localize(datetime.datetime.utcnow()) +\
						 datetime.timedelta(seconds=time_to_wait)

	edit['end_edit'] = utc.localize(datetime.datetime.utcnow()) +\
					   datetime.timedelta(seconds=time_to_wait + time_per_edit)

	last_css['last_edit_scheduled'] = edit['end_edit']

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
	return result, 200, headers


@app.route('/css/edit/<edit_id>', methods=['GET'])
def css_edit(edit_id):
    with open('static/style.css', 'r') as f:
        style_sheet = f.read()

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