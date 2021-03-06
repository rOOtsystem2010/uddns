#!/usr/bin/python3
import os
try:
	import bcrypt
except ImportError:
	print("oops. bcrypt for python3 not found. trying to install it ourself")
	if (os.system("pip install bcrypt") != 0):
		print("Apparently you'll have to do it yourself. Check README ;)")
import cgi, socket, sqlite3, ssl, subprocess, sys
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler,HTTPServer


bind = ['0.0.0.0', 4443]	#IP/Port to bind to
db="uddns.db"

def updateZone():
	ns="m00t.xyz"
	ip=socket.gethostbyname(socket.gethostname())
	if ip.find("127.0.") == 0:
		print("Warning, local ip returned by gethostname()!")
	dir="/etc/tinydns/root/"
	e = selectAll("entries")
	txt = "."+ns+":"+ip+":a:259200\n"
	ips = []
	for x  in e:
		print(x)
		if x[1] in ips:
			chr = "+"			# sets an alias
		else:
			ips.append(x[1])
			chr = "="			# sets a ptr
		txt += chr+x[0]+"."+ns+":"+x[1]+":21600\n" 	# in seconds. 6h
#TODO: Possibly different classes of expiration time
	try:
		with open(dir+"data", "w") as of:
			of.write(txt)
		return subprocess.Popen(["/usr/bin/tinydns-data"], cwd=dir)
	except Exception:
		pass;

def selectAll(table, opt=""):
		co = sqlite3.connect(db);
		c = co.cursor()
		x = c.execute("select * from "+table+" "+opt+";").fetchall()
		co.commit()
		co.close()
		return x

#TODO: macroize / save chars / deredundancy
class EntryList:
	def __init__(self, user, ul):
		self.user = user
		self.entries = False
		self.ul = ul
		self.getEm(ul)
	def get(self):
		return self.entries;
	def create(self):
#		print("EntryList::create")
		co = sqlite3.connect(db);
		c = co.cursor()
		c.execute('''create table entries (name text, ip text, user text)''')
		co.commit()
		co.close()
	def getEm(self, ul):
		try:
			s = "where user like '"+self.user+"'"
			if (ul == 4):
				s = ""
			self.entries = selectAll("entries", s)
#			print(' self.entries', self.entries)
		except sqlite3.OperationalError as e:
#			print("error", e)
			self.create()
	def add(self, name, ip, user):
		co = sqlite3.connect(db);
#		print(name,ip,user)
		c = co.cursor()
		c.execute('''insert into entries values (?,?,?)''', [name, ip, user])
		co.commit()
		co.close()
		return 1
	def upd(self, name, ip):
		co = sqlite3.connect(db);
		c = co.cursor()
		c.execute('''update entries set ip = ? where name like ?''', [ip, name])
		co.commit()
		co.close()
		return 1
	def chown(self,name, user):
		co = sqlite3.connect(db);
		c = co.cursor()
		c.execute('''update entries set user = ? where name like ?''', [user, name])
		co.commit()
		co.close()
		return 1
	def dlt(self, name):
		co = sqlite3.connect(db);
		c = co.cursor()
		c.execute('''delete from entries where name like ?''', [name])
		co.commit()
		co.close()
		return 1
	def aur(self, user, pwd, ul): #AddUseR
		if self.ul < 4:
			return -1;
		u = Users();
		if (int(ul) > 3 or int(ul) < 1):
			return -1;
		hp = bcrypt.hashpw(pwd.encode("utf8"),bcrypt.gensalt())
		u.add(user, hp, int(ul));
		return -1;
		
class User:
	def __init__(self, ip, user, ulevel):
		self.u = user
		self.ul = ulevel
		self.ip = ip
#		print("user", user)
		self.el = EntryList(user, ulevel)
		self.e = self.el.get()
#		print('self.e', self.e)
	ulevels = {
		1:'simple',
		2:'adv',
		3:'veryadv',
		4:'admin'
	}
	def cmd(self, c, args):
		try:
			a = self.fundict[c]
		except KeyError:
			return False
		return a[1](self, args)
	def create4(self, n):
		try:
			nn = n["n"][0]
		except KeyError:
			return "vbad"
		if self.e:
			for x in self.e:
				if (nn == x[0]):
					return "bad"
		if self.ul < 2:
			return "ask"
		self.el.add(nn, self.ip[0],self.u)
		return "good"
	def update4(self, n):
		try:
			nn = n["n"][0]
		except KeyError:
			return "vbad"
		if ((self.e == None)):
			return "bad"
		for x in self.e:
			if x[0] == nn:
				if (self.ul == 4 or self.u == x[2]):
					self.el.upd(nn, self.ip[0])
					return "good"
		return "bad"
	def delete4(self, n):
		try:
			nn = n["n"][0]
		except KeyError:
			return "vbad"
		if ((self.e != None)):
			for x in self.e:
				if x[0] == nn:
					if (self.ul == 4 or self.u == x[2] and self.ul > 1):
						self.el.dlt(nn)
						return "good"
		return "bad"
	def dump(self,n):
		if (self.e == [] or self.e is False):
			return "(empty)"
		s = ""
		for x in self.e:
			if (self.ul == 4 or x[2] == self.u):
				s += str(x)+'\n'
		if s == "":
			s = "(empty)"
		return s
	def chown(self,n):
		if self.ul != 4:
			return "ask"
		try:
			nn = n["n"][0]
			new = n["o"][0]
		except KeyError:
			return "vbad"
		if (self.e != None):
			for x in self.e:
				if x[0] == nn:
					self.el.chown(nn, new)
					return "good"
	def zupd(self,n):
		if self.ul != 4:
			return "ask"
		updateZone();
		return "done"
#WARNING ON CHECK PAS LES DOUBLONS ;-)
	def addu(self,n):
		if self.ul != 4:
			return "ask"
		try:
			u = n["uu"][0]
			p = n["pp"][0]
			l = n["l"][0]
		except KeyError:
			return "vbad"
		self.el.aur(u, p, l)
		return "good"

	fundict = {
		'create4': [1, create4],
		'update4': [1, update4],
		'delete4': [1, delete4],
		'dump':	[0, dump],
		'chown': [1, chown],
		'ausr': [1, addu],
		'zud': [1,zupd]
	}

class Users:
	def __init__(self):
		self.users = False
		self.uu = False;
		try:
			self.getAll()
		except sqlite3.OperationalError:
			self.create()
	def getAll(self):
		co = sqlite3.connect(db);
		c = co.cursor()
		self.users = selectAll("users")
		self.users = c.execute("select * from users;").fetchall()
		co.commit()
		co.close()
	def create(self):
		print("Users::create")
		co = sqlite3.connect(db);
		c = co.cursor()
		c.execute('''create table users (user text, pass blob, um tinyint)''')
		co.commit()
		co.close()
	def authorized(self, a):
		try:
			for u in self.users:
				if (a['u'][0] == u[0]):
					self.uu = u
					break
		except KeyError:
			return False;
		if (False == self.uu):
			return False;
		if (bcrypt.hashpw(a['p'][0].encode("utf8"), self.uu[1]) == self.uu[1]):
			return True;
		return False;
	def get(self, a):
		return self.uu[0], self.uu[2]
	def add(self, u, p, m):
		co = sqlite3.connect(db)
		c = co.cursor()
		c.execute("insert into users values (?, ?, ?)", [u, sqlite3.Binary(p), m])
		co.commit()
		co.close()
	def delete(self, u,p):
		return a
	def getMode(self, u):
		return a
	def setMode(self, u):
		return a

def doCmd(c,a,ad):
	if (len(c) < 2):
		return 500, "bad request"
	u = Users();
	if (u.authorized(a)):
		u, ul = u.get(a)
		cmd = User(ad, u, ul).cmd(c[1:],a)
		if (cmd == False or cmd == None):
			return 500, "bad request"
		return 200, cmd
	else:
		return 403, "forbidden"

class UddnsRequestHandler(BaseHTTPRequestHandler):
#	def handle(self):
#		return self.do_GET()
	def do_GET(self):
		q = urlparse(self.path)
		cmd = q.path
		args = parse_qs(q.query)
		r,c = doCmd(cmd,args,self.client_address)
		self.send_response(r)
		self.send_header('Content-Type', 'text/plain')
		self.end_headers()
		self.wfile.write(bytes(c, 'UTF-8'))
		self.close_connection = True

# taken from http://www.piware.de/2011/01/creating-an-https-server-in-python/
# generate server.xml with the following command:
#    openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes
# run as follows:
#    python simple-https-server.py
# then in your browser, visit:
#    https://localhost:4443

def updateRecord(d):
	co = sqlite3.connect(db);
	c = co.cursor()
	c.execute("xxx")
	co.commit()
	co.close()

av = sys.argv
if (len(av) > 3):

	print("adding user", av[1], "as", User.ulevels[int(av[3])])
	u = Users();
	hp = bcrypt.hashpw(av[2].encode("utf8"),bcrypt.gensalt())
	if type(hp) is str:	#wierd: 2 computers, same bcrypt&&python versions, one has bytes other str
		print("WARNING: hashing will be broken. See readme/pip install bcrypt/or fix it")
		hp = bytes(hp,'utf8')
	errlvl = u.add(av[1], hp, int(av[3]))
	exit(errlvl)

if (len(av) == 1):
	httpd = HTTPServer((bind[0], bind[1]), UddnsRequestHandler)
	while 42:
		try:
			httpd.socket = ssl.wrap_socket(httpd.socket, certfile='./server.pem', server_side=True)
		except FileNotFoundError:
			print("Making cert. Remember to enter FQDN")
			os.system("openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes")
			continue
		break
	print("Launching server")
	httpd.serve_forever()

exit(updateZone())
