from flask import Flask, render_template, session, request, redirect, url_for, send_file
from icalendar import Calendar, Event, vCalAddress, vText
from pathlib import Path
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
import datetime as datetime
import pytz, openpyxl, os, sys, json

os.environ['TZ'] = 'Europe/Budapest'

config = ""

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
            if(x[0] == 'ismeretlen' or x[0] == '' or x[0] == ' ' or x[2] == 'ismeretlen' or x[2] == '' or x[2] == ' '):
                continue
            a.append(str(x[-1]))
        return ";".join(a)
    def recalculate(self) -> None:
        WB = openpyxl.load_workbook("dl.xlsx", True)
        self.data = []

        try:
            # félév váltásnál ezt át kell írni!
            SH = WB["2023tavasz"]
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
                else:
                    interlist.append(cell.value)

            interlist.append(i)
            lst = interlist
            self.data.append(interlist)
            i += 1

        print("  last row hit at "+str(lst)+", with id "+str(lst[-1]))
        print("Recalculated the workbook, now it has "+str(len(self.data))+" rows.")

def calcMax(databs) -> KartyAdatok:
    outdb = KartyAdatok()
    outdb.data = databs.data[slice(100)]
    return outdb

def calcFilterID(databs, hasznosDatumok, filterRowId='null'):
    outdb = KartyAdatok()
    if(filterRowId == 'null'):
        raise Exception("Filter ID sor null értéket adott, ami nem lehetséges.")
    elif(filterRowId == '' or filterRowId == ' ' or filterRowId == ';'):
        return outdb
    for rid in filterRowId.split(";"):
        if(rid == '' or rid == ' '):
            continue
        outdb.addRow(databs.data[int(rid)])
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

    datext = datetime.datetime.now() - datetime.timedelta(days=1)

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
    file_url = "/sites/GTKstudents/Megosztott%20dokumentumok/%C3%93rarendek/ELTE_GTK_orarend_2022_2023_II.xlsx"
    filename = "dl.xlsx"

    file_path = os.path.abspath(filename)
    with open(file_path, "wb") as local_file:
        file = ctx.web.get_file_by_server_relative_url(file_url)
        file.download(local_file)
        ctx.execute_query()
    print(f" Excel refreshed: {file_path}")
    db.recalculate()
    return True

## itt számoljuk ki a hasznos dátumokat > azokat amiket meg is fogunk jeleníteni a dropdownban

def calcHasznosDatumok():
    WB = openpyxl.load_workbook("dl.xlsx", True)
    hasznosDatumok = []
    dates = []
    naps = []

    try:
        SH = WB["2023tavasz"]
    except Exception as e:
        return ["2000-01-01"]
    
    for row in SH.iter_rows(min_row=3, min_col=1, max_row=2500, max_col=12):
        if(row[0].value == None or row[0].value == "" or row[0].value == " "):
            continue
        run = 0
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

    for x in range(0,len(dates)):
        hasznosDatumok.append(str(dates[x])[:10])

    return (hasznosDatumok,naps)

app = Flask(__name__)
app.secret_key = os.urandom(256)

db = KartyAdatok()
    
refreshExcel()
db.recalculate()

interHasznDatumok=calcHasznosDatumok()
interHasznNapok=interHasznDatumok[1]
interHasznDatumok=interHasznDatumok[0]

@app.route('/refresh')
def refresh(name="Frissítés"):
    if(refreshExcel()):
        db.recalculate
        return redirect("/?sikeresen_frissitettem_a_tablat")
    db.recalculate
    return redirect("/?nem_tudom_frissiteni_a_tablat_mert_nem_telt_el_24_ora")

@app.route('/savecal', methods = ['GET', 'POST'])
def savecal(name="Naptár exportálása", usname="", feldolg=[]):
    feldolg=[]
    if(request.method == "POST"):
        print("Írás megkezdése naptárba: "+request.form['usnamepost'])
        cal = Calendar()
        cal.add('prodid', '-//Órarend//Exportalva ide: '+request.form['usnamepost']+'//')
        cal.add('version', '2.0')
        cal.add('x-wr-timezone', 'Europe/Budapest')
        esemenyek = request.form['valasztottak'].split(";")
        print(esemenyek)
        if(len(esemenyek) == 0):
            print("Üres esemenyek lista :()")
            return render_template('savecal.html', name=name, usname=request.form['usnamepost'], feldolg=["Üres volt a lekérés (nem tartalmazott egyetlen eseményt sem).", "0"], feldolghossz=1)
        for i in esemenyek:
            if(i == "" or i == " "):
                continue
            if(db.getDataById(int(i))[0] == "" or db.getDataById(int(i))[0] == " " or db.getDataById(int(i))[0] == None):
                print("  > feldolgozási hiba, ez nem dátum: "+str(db.getDataById(int(i))[0])+" itt: "+str(i)+" hanem "+str(type(db.getDataById(int(i))[0]))+".")
                feldolg.append(["Hiba történt az elem feldolgozása közben: nem rendelkezik dátummal az adott kártya, így nem tudom naptárba tenni.", i])
            else:
                sor = db.getDataById(int(i))
                try:
                    event = Event()

                    event.add('summary', sor[3]+" > ["+sor[7]+"]")
                    event.add('description', "Kód: "+sor[5]+" > "+sor[4]+"<br/>Csoport: "+sor[6]+"<br/>Oktató(k): "+sor[11]+"<br/><br/>(Sorszám táblázatban: "+str(sor[-1])+")")
                    event.add('dtstart', datetime.datetime.strptime(sor[0]+" "+sor[2].split("-")[0], '%Y-%m-%d %H:%M'))
                    event.add('dtend', datetime.datetime.strptime(sor[0]+" "+sor[2].split("-")[1], '%Y-%m-%d %H:%M')) 
                    event.add('priority', 5)
                    event['uid'] = '2023tavasz/ID'+str(sor[-1])
                    event['location'] = vText(sor[7])
                    cal.add_component(event)
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

        print("Export done, everything went right!")
        return render_template('savecal.html', name=name, usname=request.form['usnamepost'], feldolg=feldolg, feldolghossz=len(feldolg))

@app.route('/', methods = ['GET', 'POST'])
def index(name="Index", usname=""):
    if(request.method == "POST" and request.form['username'] in ["alma", "naptr1bPdl"]):
        session['username'] = request.form['username']
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
            if(search_targynev == 'null' and search_targykod == 'null' and search_date == 'null' and search_kurzuskod == 'null'):
                try:
                    validk = request.form['validk']
                except Exception as e:
                    print("Tried to get the validk, but it threw an Exception: "+str(e))
                    raise SystemExit
                try:
                    selectdb = calcFilterID(db,interHasznDatumok, validk)
                except Exception as e:
                    print("Error in selectdb, e:"+str(e))
                return render_template(
                    'index.html',
                    name=name,
                    usname=session["username"],
                    hasznosDatumok=interHasznDatumok,
                    hasznosNapok=interHasznNapok,
                    hasznosDatHossz=len(interHasznDatumok),
                    kartyadatok=selectdb.data, 
                    kartyahossz=selectdb.getLength(),
                    filterdate=nullint(search_date),
                    filterkod=nullstr(search_targykod),
                    filternev=nullstr(search_targynev),
                    filterkurz=nullstr(search_kurzuskod),
                    lasthit=lastHit(),
                    startpg=True,
                    elerhetoKartyaIdk = selectdb.felsorolo()
                )
            filterdb = calcFilter(db.data, interHasznDatumok, search_date, search_targykod, search_targynev, search_kurzuskod)
            return render_template(
                'index.html',
                name=name,
                usname=session["username"],
                hasznosDatumok=interHasznDatumok,
                hasznosNapok=interHasznNapok,
                hasznosDatHossz=len(interHasznDatumok),
                kartyadatok=filterdb.data, 
                kartyahossz=filterdb.getLength(),
                filterdate=nullint(search_date),
                filterkod=nullstr(search_targykod),
                filternev=nullstr(search_targynev),
                filterkurz=nullstr(search_kurzuskod),
                lasthit=lastHit(),
                startpg=False,
                elerhetoKartyaIdk = filterdb.felsorolo()
            )
        except Exception as e:
            print("Tried to filter at sz4, but "+str(e))
    if "username" in session:
        return render_template(
            'index.html',
            name=name,
            usname=session["username"],
            hasznosDatumok=interHasznDatumok,
            hasznosNapok=interHasznNapok,
            hasznosDatHossz=len(interHasznDatumok),
            kartyadatok=calcMax(db).data,
            kartyahossz=0,
            filterdate=nullint(""),
            filterkod=nullstr(""),
            filternev=nullstr(""),
            filterkurz=nullstr(""),
            lasthit=lastHit(),
            startpg = True,
            elerhetoKartyaIdk = 'null'
        )
    return render_template(
        'index.html',
        name=name,
        usname=usname,
        hasznosDatumok=interHasznDatumok,
        hasznosNapok=interHasznNapok,
        hasznosDatHossz=len(interHasznDatumok),
        kartyadatok=calcMax(db).data,
        kartyahossz=0,
        filterdate=nullint(""),
        filterkod=nullstr(""),
        filternev=nullstr(""),
        filterkurz=nullstr(""),
        lasthit=lastHit(),
        startpg = True,
        elerhetoKartyaIdk = 'null'
    )

## fájlok

@app.route('/cals/alma.ics', methods = ['GET', 'POST'])
def calsalma():
    try:
        return send_file(os.getcwd()+'/cals/alma.ics')
    except Exception as e:
        return str(e)
    
@app.route('/cals/naptr1bPdl.ics', methods = ['GET', 'POST'])
def calsnaptr1bPdl():
    try:
        return send_file(os.getcwd()+'/cals/naptr1bPdl.ics')
    except Exception as e:
        return str(e)
    
@app.route('/static/cardPicker.js', methods = ['GET', 'POST'])
def staticcardpicker():
    try:
        return send_file(os.getcwd()+'/static/cardPicker.js')
    except Exception as e:
        return str(e)

@app.route('/static/grid.svg', methods=['GET', 'POST'])
def staticgrid():
    try:
        return send_file(os.getcwd()+'/static/grid.svg')
    except Exception as e:
        return str(e)

@app.route('/robots.txt', methods = ['GET', 'POST'])
def robotstxt():
    try:
        return send_file(os.getcwd()+'/static/robots.txt')
    except Exception as e:
        return str(e)

# ez indítja az actual servinget
if __name__ == "__main__":
    app.run(host='0.0.0.0')