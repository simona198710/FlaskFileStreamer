from flask import Flask, render_template_string, url_for, send_from_directory, request, Response, send_file
import os
import re
import sys

app = Flask(__name__)
#path = 'D:/script/testFlv/stream/'
#paths = ['/mnt/usb1/stream/','D:/script/testFlv/stream/','D:/script/testFlv/stream2/','/home/pi/Downloads/']

path = sys.argv[1]
port = int(sys.argv[2])

streamable={".flv":'video/x-flv',".mp4":'video/mp4','.ts':'video/mp2t','.mkv':'video/x-matroska'}
viewable={"jpg":'image/jpg',"png":'image/png'}

validPaths = []

'''
for pathToTest in paths:
	if os.path.exists(pathToTest):
		validPaths.append(pathToTest)
'''

def list_folders_and_files(path):
	folders = []
	files = []
	for item in os.scandir(path):
		if item.is_dir():
			folders.append({'name': item.name, 'path': item.path})
		elif item.is_file():
			files.append({'name': item.name, 'path': item.path})
	return folders, files

@app.route("/", defaults={'folder': ''})
@app.route("/<path:folder>")
def index(folder):
	current_path = os.path.join(path, folder)
	folders, files = list_folders_and_files(current_path)
	parent_folder = os.path.dirname(folder)
	html = """
	<html>
		<head>
			<script>
				function copyLink(link) {{
					var dummy = document.createElement("textarea");
					document.body.appendChild(dummy);
					dummy.value = window.location.origin + link;
					dummy.select();
					document.execCommand("copy");
					document.body.removeChild(dummy);
				}}
			</script>
		</head>
		<body>
			<h1>{}</h1>
	""".format(os.path.basename(os.path.normpath(current_path)))
	if folder != "":
		html += '<a href="' + url_for('index', folder=parent_folder) + '">Go back</a>'
	if folders:
		html += "<h2>Folders</h2>"
		html += "<ul>"
		for f in folders:
			html += '<li><a href="' + url_for('index', folder=os.path.join(folder, f['name'])) + '">' + f['name'] + '</a></li>'
		html += "</ul>"
	if files:
		html += "<h2>Files</h2>"
		html += "<ul>"
		for f in files:
			foundType=False
			for imgtype in viewable:
				if f['name'].endswith(imgtype):
					html += '<li><a href="' + url_for('show_image',mimetype=viewable[imgtype], folder=folder, filename=f['name']) + '">' + f['name'] + '</a></li>'
					foundType=True
					break
					
			if not foundType:
				for imgtype in streamable:
					if f['name'].endswith(imgtype):
						html += '<li><a href="' + url_for('download_video', folder=folder, filename=f['name']) + '">' + f['name'] + '</a>'
						html += ' <button onclick="copyLink(\'' + url_for('play_video', folder=folder, filename=f['name']) + '\')">Copy Link</button></li>'
						html += "</ul>"
						foundType=True
						break
					
			if not foundType:
				html += '<li><a href="' + url_for('download_file', folder=folder, filename=f['name']) + '">' + f['name'] + '</a>'
				html += ' <button onclick="copyLink(\'' + url_for('download_file', folder=folder, filename=f['name']) + '\')">Copy Link</button></li>'
				html += "</ul>"
	return html

@app.route('/download/<path:folder>/<path:filename>')
def download_file(folder, filename):
	return send_from_directory(os.path.join(path, folder), filename, as_attachment=True)

@app.route('/image/<path:folder>/<path:filename>')
def show_image(folder, filename,mimetype=None):
	if not mimetype is None:
		return send_file(os.path.join(path, folder, filename), mimetype=mimetype)
	else:
		return send_file(os.path.join(path, folder, filename))

@app.route('/download_video/<path:folder>/<path:filename>')
def download_video(folder, filename):
	#print(path,folder, filename)
	'''
	return send_file(os.path.join(path, folder, filename), 
					mimetype='video/x-flv', 
					as_attachment=False)
	'''
	#send_from_directory(os.path.join(path, folder), filename, as_attachment=True)
	return send_file(os.path.join(path, folder, filename))

@app.route('/video/<path:folder>/<path:filename>')
def play_video(folder, filename,mimetype=None):
	'''
	return send_file(os.path.join(path, folder, filename), 
					mimetype='video/x-flv', 
					as_attachment=False)
	'''
	return get_file(request,os.path.join(path, folder, filename),mimetype=mimetype)

def get_file(request,full_path,mimetype=None):
	
	if mimetype is None:
		for imgtype in streamable:
			if full_path.endswith(imgtype):
				print("Mime detected as",str(streamable[imgtype]))
	
	range_header = request.headers.get('Range', None)
	byte1, byte2 = 0, None
	if range_header:
		print("Got range header",range_header)
		match = re.search(r'(\d+)-(\d*)', range_header)
		groups = match.groups()

		if groups[0]:
			byte1 = int(groups[0])
		if groups[1]:
			byte2 = int(groups[1])
	   
	chunk, start, length, file_size = get_chunk(full_path,byte1, byte2)
	resp = Response(chunk, 206, mimetype=mimetype,
					  content_type=mimetype, direct_passthrough=True)
	resp.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(start, start + length - 1, file_size))
	resp.headers['Content-Length']=str(file_size)
	print(resp.headers)
	return resp

def get_chunk(full_path,byte1=None, byte2=None):
	#full_path = "D:/script/testFlv/stream/aaaa/1/sample_960x540.flv"
	file_size = os.stat(full_path).st_size
	start = 0
	chunksize=1024*1024*5 #5mb
	#chunksize=1024 #1kb
	#chunksize=1024*1024 #1mb

	print("byte1 "+str(byte1)+" byte2 "+str(byte2))
	if byte1 < file_size:
		start = byte1
	if byte2:
		length = byte2 + 1 - byte1
	else:
		length = file_size - start
		if length > chunksize:
		  print("Sending chunk")
		  length=chunksize

	with open(full_path, 'rb') as f:
		f.seek(start)
		chunk = f.read(length)
	print("Sending", start, length, file_size)
	return chunk, start, length, file_size

@app.after_request
def after_request(response):
	response.headers.add('Accept-Ranges', 'bytes')
	return response

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=port,debug=True)
