import datetime
import time
import os
import click
import pysftp
import schedule
import sys
import pathlib
import multiprocessing
from multiprocessing import Process
from multiprocessing import Pool
import itertools
import threading
from datetime import datetime

sessions = {}
dirs = []
files = []
idk = []

now = datetime.now()
cnopts = pysftp.CnOpts(knownhosts=None)
cnopts.hostkeys = None

def getFolderSize(folder):
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += getFolderSize(itempath)
    return total_size

@click.command()
@click.option('--when', default=None, help='schedule backup every n days')
def vmwarebackup(when=None):
    try:
        with open('credentials.txt') as file:
            credentials = [x.strip().split(':') for x in file.readlines()]
    except FileNotFoundError as err:
        print (" File Not Found!  %s" % (err))
        sys.exit()
    
    count = 0
    print('\n')
    with click.progressbar(credentials) as bar:
            for cred_list in bar:
                try:
                    sftp_session = pysftp.Connection(cred_list[0],username=cred_list[1],password=cred_list[2],default_path='/vmfs/volumes',cnopts=cnopts)     
                except Exception as err:
                    print(" Error Occured! %s " % (err))
                    sys.exit()
                else:
                    print ("")
                    print("\n Host %s session created successfully..\n" % (cred_list[0]))
                    pass
                sessions[cred_list[0]] = sftp_session
                count += 1
                 
    if when != None:
        schedule.every(int(when)).days.at("02:00").do(sftp_get)
        date = datetime.today()
        while 1:
            try:
                print(" Next backup on %d|%d|%d ..\r\n" % (int(when) + int(date.day),date.month,date.year))
                schedule.run_pending()
                time.sleep(1500)
            except:
                return vmwarebackup(when)
    else:
        return sftp_get()


def sftp_get():
    
    def dlist(folder):
        dirs.append(folder)

    def flist(file):    
        files.append(file)
    
    def ulist(uknwn):
        idk.append(uknwn)

    vms = [line.rstrip('\n') for line in open('virtualmachines.txt')]
    
    for host in sessions:
        session = sessions[host]
        session.walktree('/vmfs/volumes', flist, dlist, ulist)
        try:
            for vm in vms:
                for folder in dirs:
                    if vm in folder:
                        session = session
                        print(" VM '%s' found on host %s \n" % (vm,host))
                        del vm
                        try:
                            dirs.clear()
                            pathlib.Path('backup%s-%s-%s' % (now.month,now.day,now.year)).mkdir(exist_ok=True)
                            time.sleep(0.3)
                            localpath = 'backup%s-%s-%s' % (now.month,now.day,now.year)
                            print(' Starting download of %s.. \n' % (folder))
                            get = threading.Thread(target=session.get_d, args=(folder,localpath))
                            #get = Process(target=session.get_d, args=(folder,'vmbackup'))
                            get.start()
                        except Exception as err:
                            print(' Something went wrong during download attempt..  %s ' % (err))
                    else:
                        pass
        except Exception:
            print("\n No files left in download queue, continuing..\n\n")
            pass

    start = datetime.today()
    print('\n** Downloads started:  %s **\n' % (start))
    spinner = itertools.cycle(['-', '/', '|', '\\'])

    while get.is_alive():
        spin_icon = sys.stdout.write(spinner.__next__())
        print (" Downloading..  %s bytes " % (getFolderSize(localpath)), end='\r'),
        sys.stdout.flush()
        sys.stdout.write('\b')
        time.sleep(0.1)
        print("")
    print("\n\n Download(s) Complete! \n")
       
    [sessions[host].close() for host in sessions]
    print(" All connections closed, exiting..")
    print("")
    print("""
    
    
         """)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    print(""" 
                                 _             _               _            _ 
 __ ___ ____ __ ____ _ _ _ ___  | |__  __ _ __| |___  _ _ __  | |_ ___  ___| |
 \ V / '  \ V  V / _` | '_/ -_) | '_ \/ _` / _| / / || | '_ \ |  _/ _ \/ _ \ |
  \_/|_|_|_\_/\_/\__,_|_| \___| |_.__/\__,_\__|_\_\\_,_| .__/  \__\___/\___/_|
                                                       |_|       
   by: Clayton M. Moss (clmoss@cisco.com)
             
""")
    time.sleep(3)
    vmwarebackup()
