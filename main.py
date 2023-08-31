from flask import Flask, render_template, session, request, redirect, url_for, send_file, send_from_directory, make_response
from icalendar import Calendar, Event, vCalAddress, vText
from pathlib import Path
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from itsdangerous import URLSafeSerializer
from operator import itemgetter as iget
import datetime as datetime
import pytz, openpyxl, os, sys, json, traceback

os.environ['TZ'] = 'Europe/Budapest'

ALLOWED_USR = ['alma', 'naptrB4fGdP']

config = ""
expversion = '1'

# itt tároljuk el a belépési adatokat a SharePointhoz. Mivel a fejlesztés Windowson, az éles/teszt környezet pedig Linuxon (Ubuntu 22) volt/van,
# ezért linuxon a configok között eltárolt json fájlt, developmenthez pedig a lokális jsont használjuk (így a publikus internetre nem kerül ki a jelszó,
# a szerveren pedig korlátozva van a hozzáférés ezekhez az adatokhoz). Optimális megoldás az lenne, ha OAuth2-vel bejelentkeztetnénk, majd token használatával
# lenne lekérve az új excel, de ez nem került implementálásra. B opció az API használat (api kulcsal), de ez le van tiltva az ELTE SharePointon :(

if(sys.platform == "linux" or sys.platform == "linux2"):
    with open('/etc/config.json') as config_file:
        config = json.load(config_file)
else:
    with open('./localconfig.json') as config_file:
        config = json.load(config_file)

class KartyAdatok():
    def __init__(self) -> None:
        self.data = []
        pass
    def addRow(self, s) -> None:
        self.data.append(s)
    def debugPrinter(self) -> None:
        for x in self.data:
            print(x)
    def getLength(self) -> int:
        return len(self.data)
    def getDataById(self, id) -> list:
        for i in self.data:
            if i[-1] == int(id):
                return i
        return []
    def felsorolo(self) -> str:
        a = []
        for x in self.data:
            if(x[0] == 'ismeretlen' or x[0] == '' or x[0] == ' ' or x[2] == 'ismeretlen' or x[2] == '' or x[2] == ' ' or 'Típus:' in x[6]):
                continue
            a.append(str(x[-1]))
        return ";".join(a)
    def recalculate(self) -> None:
        WB = openpyxl.load_workbook("dl.xlsx", True)
        #WBvizs = openpyxl.load_workbook("dlvizs.xlsx", True)
        self.data = []

        try:
            # félév váltásnál ezt át kell írni!
            SH = WB["2023ősz"]
            #SHvizs = WBvizs["ELTE_GTK_ZH_2023_tavasz"]
        except Exception as e:
            print("Exception occoured while trying to get the workbook. It's basicly the following: "+str(e))
            return
        i = 0
        for row in SH.iter_rows(min_row=3, min_col=1, max_row=2500, max_col=12):  
            interlist = []
            frow = True

            if(row[3].value == "" or row[3].value == " "):
                break
            elif((row[3].value == "EmptyCell" or row[3].value is None) and (row[0].value == "EmptyCell" or row[0].value is None)):
                break

            for cell in row:
                if(frow and type(cell.value) == datetime.datetime):
                    interlist.append(cell.value.strftime('%Y-%m-%d'))
                    frow = False
                elif(frow):
                    interlist.append("ismeretlen")
                    frow = False
                elif(type(cell.value) == None or cell.value == None):
                    interlist.append("ismeretlen")
                elif(cell.value == "Monday"):
                    interlist.append("hétfő")
                elif(cell.value == "Tuesday"):
                    interlist.append("kedd")
                elif(cell.value == "Wednesday"):
                    interlist.append("szerda")
                elif(cell.value == "Thursday"):
                    interlist.append("csütörtök")
                elif(cell.value == "Friday"):
                    interlist.append("péntek")
                elif(cell.value == "Saturday"):
                    interlist.append("szombat")
                elif(cell.value == "Sunday"):
                    interlist.append("vasárnap")
                else:
                    interlist.append(cell.value)

            interlist.append(i)
            lst = interlist
            self.data.append(interlist)
            i += 1
        
        print("  > last row hit at "+str(lst)+", with id "+str(lst[-1]))

        """ for row in SHvizs.iter_rows(min_row=2, min_col=1, max_row=2500, max_col=12):
            interlist = []
            frow = True

            if(row[3].value == "" or row[3].value == " "):
                break
            elif((row[3].value == "EmptyCell" or row[3].value is None) and (row[0].value == "EmptyCell" or row[0].value is None)):
                break

            countr = 0
            trl = ''

            for cell in row:
                if(frow and type(cell.value) == datetime.datetime):
                    interlist.append(cell.value.strftime('%Y-%m-%d'))
                    frow = False
                elif(frow):
                    interlist.append("ismeretlen")
                    frow = False
                elif(type(cell.value) == None or cell.value == None):
                    interlist.append("ismeretlen")
                else:
                    interlist.append(cell.value)

            rebindls = [interlist[0],interlist[1],interlist[2],interlist[3],interlist[4],interlist[5],"Típus: "+interlist[7],interlist[6],i]
            lst = rebindls
            self.data.append(rebindls)
            i += 1
 """
        #self.debugPrinter()
        self.data = sorted(self.data, key=lambda x: (x[0], x[2]))

        print("  > last row hit at "+str(lst)+", with id "+str(lst[-1]))
        print("Recalculated the workbook, now it has "+str(len(self.data))+" rows.")

def calcTextHet(hasznosHetekKezdo):
    textHasznHetek = []
    for x in hasznosHetekKezdo:
        textHasznHetek.append(x.strftime("%Y-%m-%d"))
    return textHasznHetek

def calcMax(databs) -> KartyAdatok:
    outdb = KartyAdatok()
    outdb.data = databs.data[slice(100)]
    return outdb

def calcFilterIDWeek(databs, hasznosHetek, filterWeekId='null', filterRowId='null'):
    outdb=[KartyAdatok(),KartyAdatok(),KartyAdatok(),KartyAdatok(),KartyAdatok(),KartyAdatok()]
    if(filterRowId == 'null'):
        raise Exception("Filter ID sor null értéket adott, ami nem lehetséges.")
    elif(filterRowId == '' or filterRowId == ' ' or filterRowId == ';'):
        return outdb
    for rid in filterRowId.split(";"):
        if(rid == '' or rid == ' '):
            continue
        for x in databs.data:
            if(x[0] == 'ismeretlen'):
                break
            elif x[-1] == int(rid) and datetime.datetime.strptime(x[0], "%Y-%m-%d").weekday() != 6 and datetime.datetime.strptime(x[0], "%Y-%m-%d").isocalendar()[1] == hasznosHetek[int(filterWeekId)].isocalendar()[1]:
                outdb[datetime.datetime.strptime(x[0], "%Y-%m-%d").weekday()].addRow(x)
                break
    return outdb
          
def calcFilterID(databs, filterRowId='null'):
    outdb = KartyAdatok()
    if(filterRowId == 'null'):
        raise Exception("Filter ID sor null értéket adott, ami nem lehetséges.")
    elif(filterRowId == '' or filterRowId == ' ' or filterRowId == ';'):
        return outdb
    for rid in filterRowId.split(";"):
        if(rid == '' or rid == ' '):
            continue
        for x in databs.data:
            if x[-1] == int(rid):
                outdb.addRow(x)
                break
    return outdb

def calcFilterWeeks(databs, hasznosHetek, filterWeekId='null', filterTargykod='null', filterTargynev='null', filterKurz='null') -> KartyAdatok:
    outdb = [KartyAdatok(),KartyAdatok(),KartyAdatok(),KartyAdatok(),KartyAdatok(),KartyAdatok()]
    print("Filtering for: "+filterWeekId+", "+filterTargykod+", "+filterTargynev+", "+filterKurz)
    print(hasznosHetek[int(filterWeekId)])
    if(filterWeekId == 'null'):
        return []
    for row in databs:
        should = True
        if(row[0] == 'ismeretlen'):
            continue
        if(datetime.datetime.strptime(row[0], "%Y-%m-%d").isocalendar()[1] != hasznosHetek[int(filterWeekId)].isocalendar()[1]):
            should = False
        if(filterTargykod != 'null' and should == True):
            if(filterTargykod.lower() not in row[4].lower()):
                should = False
        if(filterTargynev != 'null' and should == True):
            if(filterTargynev.lower() not in row[3].lower()):
                should = False
        if(filterKurz != 'null' and should == True):
            if(filterKurz.lower() not in row[5].lower()):
                should = False
        if(should and datetime.datetime.strptime(row[0], "%Y-%m-%d").weekday() != 6):
            outdb[datetime.datetime.strptime(row[0], "%Y-%m-%d").weekday()].addRow(row)
    return outdb   

def calcFilter(databs, hasznosDatumok, filterDateId='null', filterTargykod='null', filterTargynev='null', filterKurz='null') -> KartyAdatok:
    outdb = KartyAdatok()
    for row in databs:
        should = True
        if(filterDateId != 'null'):
            if(row[0] != hasznosDatumok[int(filterDateId)]):
                should = False
        if(filterTargykod != 'null' and should == True):
            if(filterTargykod.lower() not in row[4].lower()):
                should = False
        if(filterTargynev != 'null' and should == True):
            if(filterTargynev.lower() not in row[3].lower()):
                should = False
        if(filterKurz != 'null' and should == True):
            if(filterKurz.lower() not in row[5].lower()):
                should = False
        if(should):
            outdb.addRow(row)
    return calcMax(outdb)     

def lastHit():
    f = open("lastpull.txt", "r")
    return f.readline()

def nullstr(a):
    if(a == "" or a == "null"):
        return ""
    return a

def nullint(a):
    if(a == "" or a == "" or a == "null"):
        return 99999
    return int(a)

def calcBegins(tex) -> str:
    if(len(tex) > 28):
        return tex[:25]+"..."
    return tex

def refreshExcel():
    f = open("lastpull.txt", "r")
    try:
        datelast = datetime.datetime.strptime(f.readline(), '%Y-%m-%d %H:%M')
        f.close()
    except ValueError as e:
        print("Exception occoured, probably empty file so we'll just include the time now.")
        f.close
        f = open('lastpull.txt', 'w')
        f.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        f.close()
        datelast = datetime.datetime.now()

    datext = datetime.datetime.now() - datetime.timedelta(minutes=15)

    if(datelast >= datext):
        print("Shouldn't refresh table: it's not too old")
        return False
    else:
        f = open("lastpull.txt", "w")
        f.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        f.close()
        print("We should refresh the table now!")

    url = "https://eltehu.sharepoint.com/sites/GTKstudents"
    username = config.get('GTKUSER')
    password = config.get('GTKPASS')

    ctx_auth = AuthenticationContext(url)
    ctx_auth.acquire_token_for_user(username, password)   
    ctx = ClientContext(url, ctx_auth)
    file_url = "/sites/GTKstudents/Megosztott%20dokumentumok/%C3%93rarendek/ELTE_GTK_orarend_2023_2024_I.xlsx"
    filename = "dl.xlsx"

    file_path = os.path.abspath(filename)
    with open(file_path, "wb") as local_file:
        file = ctx.web.get_file_by_server_relative_url(file_url)
        file.download(local_file)
        ctx.execute_query()
    print(f" Excel refreshed: {file_path}")

    file_url = ""
    filename = "dlvizs.xlsx"

    if(file_url == ""):
        print(f" Excel skipped - no URL given")
    else:
        file_path = os.path.abspath(filename)
        with open(file_path, "wb") as local_file:
            file = ctx.web.get_file_by_server_relative_url(file_url)
            file.download(local_file)
            ctx.execute_query()
        print(f" Excel refreshed: {file_path}")
        db.recalculate()
    return True

## összehasonlítja a tárolt órarendet (ami jsonben van) a jelenlegi órarendel, majd feldobja a választ

def calcDiff(db:KartyAdatok, username:str) -> list:
    f = open(os.getcwd()+'/tarolo/'+username+'.json', encoding='utf-8')
    oldjs = json.load(f)
    backdb = []

    if(oldjs['expversion'] != expversion):
        raise Exception("Export version missmatch.")

    for x in oldjs['entries']:
        sor = db.getDataById(x['id'])
        if("." in sor[2]):
            dt = {
                "date":sor[0],
                "from":sor[2].split(".")[0],
                "to":sor[2].split(".")[1],
                "location":sor[7],
                "course_name":sor[3],
                "course_code":sor[5],
                "subj_code":sor[4],
                "groups":sor[6],
                "id":sor[-1]
            }
        else:
            dt = {
                "date":sor[0],
                "from":sor[2].split("-")[0],
                "to":sor[2].split("-")[1],
                "location":sor[7],
                "course_name":sor[3],
                "course_code":sor[5],
                "subj_code":sor[4],
                "groups":sor[6],
                "id":sor[-1]
            }

        if(x['date'] != dt['date'] or x['course_name'] != dt['course_name'] or x['course_code'] != dt['course_code'] or x['subj_code'] != dt['subj_code'] or (x['location'] != dt['location'] and (x['from'] != dt['from'] or x['to'] != dt['to']))):
            backdb.append(["Fő tulajdonság-változás: valószínűleg elcsúszott a táblázat", x, dt])
        elif(x['from'] != dt['from'] or x['to'] != dt['to']):
            backdb.append(["Kezdő és/vagy végdátum változás", x, dt])
        elif(x['location'] != dt['location']):
            backdb.append(["Teremváltozás", x, dt])
        elif(x['groups'] != dt['groups']):
            backdb.append(["Csoportváltozás", x, dt])

    return backdb
    
## itt számoljuk ki a hasznos dátumokat > azokat amiket meg is fogunk jeleníteni a dropdownban

def calcHasznosHetek():
    WB = openpyxl.load_workbook("dl.xlsx", True)
    #WBvizs = openpyxl.load_workbook("dlvizs.xlsx", True)
    hasznosHetek = []
    weekNums = []
    startDate = []

    try:
        SH = WB["2023ősz"]
        #SHvizs = WBvizs["ELTE_GTK_ZH_2023_tavasz"]
    except Exception as e:
        return ["2000-01-01"]
    
    for row in SH.iter_rows(min_row=3, min_col=1, max_row=2500, max_col=12):
        if(row[0].value == None or row[0].value == "" or row[0].value == " "):
            continue
        if row[0].value.isocalendar()[1] not in weekNums:
            weekNums.append(row[0].value.isocalendar()[1])
            startDate.append(row[0].value)

    #for row in SHvizs.iter_rows(min_row=2, min_col=1, max_row=2500, max_col=12):
    #    if(row[0].value == None or row[0].value == "" or row[0].value == " "):
    #        continue
    #    if row[0].value.isocalendar()[1] not in weekNums:
    #        weekNums.append(row[0].value.isocalendar()[1])
    #        startDate.append(row[0].value)

    for x in range(0,len(weekNums)):
        hasznosHetek.append(str(weekNums[x]))

    return (hasznosHetek, startDate)

def calcHasznosDatumok():
    WB = openpyxl.load_workbook("dl.xlsx", True)
    #WBvizs = openpyxl.load_workbook("dlvizs.xlsx", True)
    hasznosDatumok = []
    dates = []
    naps = []

    try:
        SH = WB["2023ősz"]
        #SHvizs = WBvizs["ELTE_GTK_ZH_2023_tavasz"]
    except Exception as e:
        return ["2000-01-01"]
    
    for row in SH.iter_rows(min_row=3, min_col=1, max_row=2500, max_col=12):
        if(row[0].value == None or row[0].value == "" or row[0].value == " "):
            continue
        if row[0].value not in dates:
            dates.append(row[0].value)
            if(row[1].value == "Monday"):
                naps.append("hétfő")
            elif(row[1].value == "Tuesday"):
                naps.append("kedd")
            elif(row[1].value == "Wednesday"):
                naps.append("szerda")
            elif(row[1].value == "Thursday"):
                naps.append("csütörtök")
            elif(row[1].value == "Friday"):
                naps.append("péntek")
            elif(row[1].value == "Saturday"):
                naps.append("szombat")
            elif(row[1].value == "Sunday"):
                naps.append("vasárnap")
            else:
                naps.append(row[1].value)

    """ for row in SHvizs.iter_rows(min_row=2, min_col=1, max_row=2500, max_col=12):
        if(row[0].value == None or row[0].value == "" or row[0].value == " "):
            continue
        if row[0].value not in dates:
            dates.append(row[0].value)
            if(row[1].value == "Monday"):
                naps.append("hétfő")
            elif(row[1].value == "Tuesday"):
                naps.append("kedd")
            elif(row[1].value == "Wednesday"):
                naps.append("szerda")
            elif(row[1].value == "Thursday"):
                naps.append("csütörtök")
            elif(row[1].value == "Friday"):
                naps.append("péntek")
            elif(row[1].value == "Saturday"):
                naps.append("szombat")
            elif(row[1].value == "Sunday"):
                naps.append("vasárnap")
            else:
                naps.append(row[1].value) """

    for x in range(0,len(dates)):
        hasznosDatumok.append(str(dates[x])[:10])

    return (hasznosDatumok,naps)

app = Flask(__name__)
app.secret_key = config.get("SECRET_KEY")

SECRET_KEY = config.get("SECRET_KEY")
serializer = URLSafeSerializer(SECRET_KEY)

db = KartyAdatok()
    
refreshExcel()
db.recalculate()

interHasznDatumok=calcHasznosDatumok()
interHasznNapok=interHasznDatumok[1]
interHasznDatumok=interHasznDatumok[0]

interHasznHetek=calcHasznosHetek()
interHasznHetKezdo=interHasznHetek[1]
interHasznHetek=interHasznHetek[0]

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=15)

@app.route('/refresh')
def refresh(name="Frissítés"):
    if(refreshExcel()):
        db.recalculate
        return redirect("/?sikeresen_frissitettem_a_tablat")
    db.recalculate
    return redirect("/?nem_tudom_frissiteni_a_tablat_mert_nem_telt_el_15_perc")

@app.route('/diff', methods = ['GET', 'POST'])
def diff(name="Órarendváltozás-ellenőrzés"):
    try:
        a = request.form['username']
        print(a)
    except Exception as e:
        print(e)
        return render_template('diff.html', resp=False, usname="", diffdb=[])
    d = calcDiff(db, a)
    return render_template('diff.html', resp=True, usname=a, diffdb=d)

@app.route('/savecal', methods = ['GET', 'POST'])
def savecal(name="Naptár exportálása", usname="", feldolg=[]):
    feldolg=[]
    if(request.method == "POST"):
        #print("Írás megkezdése naptárba: "+request.form['usnamepost'])
        cal = Calendar()
        dct = {
            "desc":"Tábla Export JSON fájl",
            "expversion":"1",
            "for_user":request.form['usnamepost'],
            "entries":[]
        }
        cal.add('prodid', '-//Órarend//Exportalva ide: '+request.form['usnamepost']+'//')
        cal.add('version', '2.0')
        cal.add('x-wr-timezone', 'Europe/Budapest')
        esemenyek = request.form['valasztottak'].split(";")
        #print(esemenyek)
        if(len(esemenyek) == 0):
            #print("Üres esemenyek lista :()")
            return render_template('savecal.html', name=name, usname=request.form['usnamepost'], feldolg=["Üres volt a lekérés (nem tartalmazott egyetlen eseményt sem).", "0"], feldolghossz=1)
        for i in esemenyek:
            if(i == "" or i == " "):
                continue
            if(db.getDataById(int(i))[0] == "" or db.getDataById(int(i))[0] == " " or db.getDataById(int(i))[0] == None):
                #print("  > feldolgozási hiba, ez nem dátum: "+str(db.getDataById(int(i))[0])+" itt: "+str(i)+" hanem "+str(type(db.getDataById(int(i))[0]))+".")
                feldolg.append(["Hiba történt az elem feldolgozása közben: nem rendelkezik dátummal az adott kártya, így nem tudom naptárba tenni.", i])
            else:
                sor = db.getDataById(int(i))
                #print("van sorunk")
                #print(sor)
                try:
                    event = Event()
                    if "Típus:" in sor[6]:
                        event.add('summary', "🎓 "+sor[3]+" > ["+sor[7]+"]")
                        event.add('description', "Kód: "+sor[5]+" > "+sor[4]+"<br/>"+sor[7]+"<br/>Kalappal :3<br/><br/>(Sorszám táblázatban: "+str(sor[-1])+")")
                    else:
                        event.add('summary', sor[3]+" > ["+sor[7]+"]")
                        event.add('description', "Kód: "+sor[5]+" > "+sor[4]+"<br/>Csoport: "+sor[6]+"<br/>Oktató(k): "+sor[11]+"<br/><br/>(Sorszám táblázatban: "+str(sor[-1])+")")

                    if("." in sor[2]):
                        dt = {
                            "date":sor[0],
                            "from":sor[2].split(".")[0],
                            "to":sor[2].split(".")[1],
                            "location":sor[7],
                            "course_name":sor[3],
                            "course_code":sor[5],
                            "subj_code":sor[4],
                            "groups":sor[6],
                            "id":sor[-1]
                        }
                        event.add('dtstart', datetime.datetime.strptime(sor[0]+" "+sor[2].split(".")[0], '%Y-%m-%d %H:%M'))
                        event.add('dtend', datetime.datetime.strptime(sor[0]+" "+sor[2].split(".")[1], '%Y-%m-%d %H:%M')) 
                    else:
                        dt = {
                            "date":sor[0],
                            "from":sor[2].split("-")[0],
                            "to":sor[2].split("-")[1],
                            "location":sor[7],
                            "course_name":sor[3],
                            "course_code":sor[5],
                            "subj_code":sor[4],
                            "groups":sor[6],
                            "id":sor[-1]
                        }
                        event.add('dtstart', datetime.datetime.strptime(sor[0]+" "+sor[2].split("-")[0], '%Y-%m-%d %H:%M'))
                        event.add('dtend', datetime.datetime.strptime(sor[0]+" "+sor[2].split("-")[1], '%Y-%m-%d %H:%M')) 
                    
                    event.add('priority', 5)
                    event['uid'] = '2023osz/ID'+str(sor[-1])
                    event['location'] = vText(sor[7])
                    
                    cal.add_component(event)

                    dct["entries"].append(dt)
                except Exception as e:
                    feldolg.append(["Hiba történt az elem feldolgozása közben: "+str(e), i])
                    print("  > naptárhiba: "+str(e))
        directory = Path.cwd() / 'cals'
        try:
            directory.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            print("   Folder already exists")
        else:
            print("   Folder was created")
        
        f = open(os.path.join(directory, request.form['usnamepost']+'.ics'), 'wb')
        f.write(cal.to_ical())
        f.close()

        jsonobj = json.dumps(dct, indent=4, ensure_ascii=False).encode('utf-8')

        with open("./tarolo/"+request.form['usnamepost']+".json", "wb") as outfile:
            outfile.write(jsonobj)

        print("Export done, everything went right!")
        return render_template('savecal.html', name=name, usname=request.form['usnamepost'], feldolg=feldolg, feldolghossz=len(feldolg))

@app.route('/', methods = ['GET', 'POST'])
def index(name="Index", usname=""):
    view = session.get('view')
    usernameCookie = request.cookies.get('usrid')
    session['username'] = 'unknown'
    isUser = None

    if(request.method == "POST"):
        try:
            isUser = request.form['username'] 
            print(f'new user:'+request.form['username'])
        except Exception as e:
            print(f"Tried to get username, but "+str(e))
            isUser = None

    if view is None:
        session['view'] = 'list'

    if isUser is not None:
        session['username'] = request.form['username']
    elif usernameCookie:
        try:
            usernameCookie = serializer.loads(usernameCookie)
            session['username'] = usernameCookie
            isUser = usernameCookie
        except Exception as e:
            print("Bad Signature found, returning nothing.")
            session['username'] = 'ismeretlen'

    if(session['username'] in ALLOWED_USR):
        print(f'viewer: '+session['view'])

        try:
            search_date = request.form['sz1']
        except Exception as e:
            print("Tried to filter at sz1, but "+str(e))
        try:
            search_targykod = request.form['sz2']
            if(search_targykod == '' or search_targykod == ' '):
                search_targykod = 'null'
        except Exception as e:
            print("Tried to filter at sz2, but "+str(e))
        try:
            search_targynev = request.form['sz3']
            if(search_targynev == '' or search_targynev == ' '):
                search_targynev = 'null'
        except Exception as e:
            print("Tried to filter at sz3, but "+str(e))
        try:
            search_kurzuskod = request.form['sz4']
            if(search_kurzuskod == '' or search_kurzuskod == ' '):
                search_kurzuskod = 'null'
        except Exception as e:
            print("Tried to filter at sz4, but "+str(e))

        ## after reading through all the filters:

        try:
            ## if everything is null > print selected items
            if(search_targynev == 'null' and search_targykod == 'null' and search_kurzuskod == 'null' and ((search_date != 'null' and session['view'] != 'list') or (session['view'] == 'list' and search_date == 'null'))):
                try: 
                    validk = request.form['validk']
                except Exception as e:
                    print("Tried to get the validk, but it threw an Exception: "+str(e))
                    raise SystemExit
                try:
                    if(session['view'] == 'list'):
                        selectdb = calcFilterID(db, validk)
                        resp = make_response(render_template(
                            'index.html',
                            name=name,
                            usname=session["username"],
                            hasznosDatumok=interHasznDatumok,
                            hasznosNapok=interHasznNapok,
                            hasznosDatHossz=len(interHasznDatumok),
                            hasznosHetek=interHasznHetek,
                            hasznosHetekHossz=len(interHasznHetek),
                            hasznosHetekKezdo=calcTextHet(interHasznHetKezdo),
                            kartyadatok=sorted(selectdb.data, key=iget(0,2)), 
                            kartyahossz=selectdb.getLength(),
                            filterdate=nullint(search_date),
                            filterkod=nullstr(search_targykod),
                            filternev=nullstr(search_targynev),
                            filterkurz=nullstr(search_kurzuskod),
                            lasthit=lastHit(),
                            startpg=True,
                            elerhetoKartyaIdk = selectdb.felsorolo(),
                            view=session['view']
                        ))
                    else:
                        filterdb = calcFilterIDWeek(db, interHasznHetKezdo, search_date, validk)
                        resp = make_response(render_template(
                            'index.html',
                            name=name,
                            usname=session["username"],
                            hasznosDatumok=interHasznDatumok,
                            hasznosNapok=interHasznNapok,
                            hasznosDatHossz=len(interHasznDatumok),
                            hasznosHetek=interHasznHetek,
                            hasznosHetekHossz=len(interHasznHetek),
                            hasznosHetekKezdo=calcTextHet(interHasznHetKezdo),
                            hasznosHetekNapjai=["hétfő","kedd","szerda","csütörtök","péntek","szombat"],
                            kartyadatok=sorted(filterdb, key=iget(0,2)),
                            osszhossz=len(filterdb),
                            kartyahossz=len(filterdb[0].data)+len(filterdb[1].data)+len(filterdb[2].data)+len(filterdb[3].data)+len(filterdb[4].data)+len(filterdb[5].data),
                            filterhet=nullint(search_date),
                            filterkod=nullstr(search_targykod),
                            filternev=nullstr(search_targynev),
                            filterkurz=nullstr(search_kurzuskod),
                            lasthit=lastHit(),
                            startpg=False,
                            elerhetoKartyaIdk = filterdb[0].felsorolo()+filterdb[1].felsorolo()+filterdb[2].felsorolo()+filterdb[3].felsorolo()+filterdb[4].felsorolo()+filterdb[5].felsorolo(),
                            view=session['view']
                        ))
                    resp.set_cookie('usrid', serializer.dumps(session['username']), expires=datetime.datetime.now() + datetime.timedelta(seconds=900), samesite='Strict')
                    return resp
                except Exception as e:
                    print("Error in selectdb, e:"+str(e))
                    print(traceback.format_exc())
    
            elif(session['view'] == 'list'):
                filterdb = calcFilter(db.data, interHasznDatumok, search_date, search_targykod, search_targynev, search_kurzuskod)
                resp = make_response(render_template(
                    'index.html',
                    name=name,
                    usname=session["username"],
                    hasznosDatumok=interHasznDatumok,
                    hasznosNapok=interHasznNapok,
                    hasznosDatHossz=len(interHasznDatumok),
                    hasznosHetek=interHasznHetek,
                    hasznosHetekHossz=len(interHasznHetek),
                    hasznosHetekKezdo=calcTextHet(interHasznHetKezdo),
                    kartyadatok=sorted(filterdb.data, key=iget(0,2)), 
                    kartyahossz=filterdb.getLength(),
                    filterdate=nullint(search_date),
                    filterkod=nullstr(search_targykod),
                    filternev=nullstr(search_targynev),
                    filterkurz=nullstr(search_kurzuskod),
                    lasthit=lastHit(),
                    startpg=False,
                    elerhetoKartyaIdk = filterdb.felsorolo(),
                    view=session['view']
                ))
                resp.set_cookie('usrid', serializer.dumps(session['username']), expires=datetime.datetime.now() + datetime.timedelta(seconds=900), samesite='Strict')
                return resp
            else:
                filterdb = calcFilterWeeks(db.data, interHasznHetKezdo, search_date, search_targykod, search_targynev, search_kurzuskod)
                print("Kartya hossza 1:"+str(len(filterdb[0].data)+len(filterdb[1].data)+len(filterdb[2].data)+len(filterdb[3].data)+len(filterdb[4].data)+len(filterdb[5].data)))
                resp = make_response(render_template(
                    'index.html',
                    name=name,
                    usname=session["username"],
                    hasznosDatumok=interHasznDatumok,
                    hasznosNapok=interHasznNapok,
                    hasznosDatHossz=len(interHasznDatumok),
                    hasznosHetek=interHasznHetek,
                    hasznosHetekHossz=len(interHasznHetek),
                    hasznosHetekKezdo=calcTextHet(interHasznHetKezdo),
                    hasznosHetekNapjai=["hétfő","kedd","szerda","csütörtök","péntek","szombat"],
                    kartyadatok=sorted(filterdb, key=iget(0,2)),
                    osszhossz=len(filterdb),
                    kartyahossz=len(filterdb[0].data)+len(filterdb[1].data)+len(filterdb[2].data)+len(filterdb[3].data)+len(filterdb[4].data)+len(filterdb[5].data),
                    filterhet=nullint(search_date),
                    filterkod=nullstr(search_targykod),
                    filternev=nullstr(search_targynev),
                    filterkurz=nullstr(search_kurzuskod),
                    lasthit=lastHit(),
                    startpg=False,
                    elerhetoKartyaIdk = filterdb[0].felsorolo()+";"+filterdb[1].felsorolo()+";"+filterdb[2].felsorolo()+";"+filterdb[3].felsorolo()+";"+filterdb[4].felsorolo()+";"+filterdb[5].felsorolo(),
                    view=session['view']
                ))
                resp.set_cookie('usrid', serializer.dumps(session['username']), expires=datetime.datetime.now() + datetime.timedelta(seconds=900), samesite='Strict')
                return resp
        except Exception as e:
            print("Tried to show the filtered stuff, but "+str(e))
            #print(traceback.format_exc())
        resp = make_response(render_template(
            'index.html',
            name=name,
            usname=session["username"],
            hasznosDatumok=interHasznDatumok,
            hasznosNapok=interHasznNapok,
            hasznosDatHossz=len(interHasznDatumok),
            hasznosHetek=interHasznHetek,
            hasznosHetekHossz=len(interHasznHetek),
            hasznosHetekKezdo=calcTextHet(interHasznHetKezdo),
            kartyadatok=sorted(calcMax(db).data, key=iget(0,2)), 
            kartyahossz=0,
            filterdate=nullint(""),
            filterhet='ismeretlen',
            filterkod=nullstr(''),
            filternev=nullstr(''),
            filterkurz=nullstr(''),
            lasthit=lastHit(),
            startpg=True,
            elerhetoKartyaIdk = 0,
            view=session['view']
        ))
        resp.set_cookie('usrid', serializer.dumps(session['username']), expires=datetime.datetime.now() + datetime.timedelta(seconds=900), samesite='Strict')
        return resp
    session['view'] = 'list'
    return render_template(
        'index.html',
        name=name,
        usname=usname,
        hasznosDatumok=interHasznDatumok,
        hasznosNapok=interHasznNapok,
        hasznosDatHossz=len(interHasznDatumok),
        kartyadatok=sorted(calcMax(db).data, key=iget(0,2)),
        kartyahossz=0,
        filterdate=nullint(""),
        filterkod=nullstr(""),
        filternev=nullstr(""),
        filterkurz=nullstr(""),
        lasthit=lastHit(),
        startpg = True,
        elerhetoKartyaIdk = 'null',
        view=session['view']
    )

## nézetek
@app.route('/view')
def change_view():
    try:
        if(request.args['origin'] == 'minical'):
            session['view'] = 'list'
        elif(request.args['origin'] == 'list'):
            session['view'] = 'minical'
        else:
            session['view'] = 'list'
        return redirect(url_for('index'))
    except Exception as e:
        return str(e)

## fájlok
@app.route('/cals/<path:path>')
def serve_cals(path):
    try:
        return send_from_directory(os.getcwd()+'/cals', path)
    except Exception as e:
        return str(e) 

@app.route('/tarolo/<path:path>')
def serve_tarolo(path):
    try:
        return send_from_directory(os.getcwd()+'/tarolo', path)
    except Exception as e:
        return str(e)
    
@app.route('/static/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(os.getcwd()+'/static', path)
    except Exception as e:
        return str(e)

@app.route('/favicon.ico', methods = ['GET', 'POST'])
def favicon():
    try:
        return send_file(os.getcwd()+'/static/favicon.ico')
    except Exception as e:
        return str(e)

@app.route('/robots.txt', methods = ['GET', 'POST'])
def robotstxt():
    try:
        return send_file(os.getcwd()+'/static/robots.txt')
    except Exception as e:
        return str(e)

@app.errorhandler(404)
def err404(e):
    try:
        return render_template('404.html')
    except Exception as excp:
        return str(excp)

# ez indítja az actual servinget
if __name__ == "__main__":
    app.run(host='0.0.0.0')