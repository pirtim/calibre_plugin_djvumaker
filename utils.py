#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import argparse
import urllib
import urllib2
import urlparse
import os
# import os.path
import subprocess

from calibre.constants import (isosx, iswindows, islinux, isbsd)
    
def create_cli_parser(self_DJVUmaker, PLUGINNAME, PLUGINVER_DOT, REGISTERED_BACKENDS_KEYS):
    '''Creates CLI for plugin.'''
    parser = argparse.ArgumentParser(prog="calibre-debug -r {} -- ".format(PLUGINNAME))
    parser.add_argument('-V', '--version', action='version', version='v{}'.format(PLUGINVER_DOT),
                        help="show plugin's version number and exit")
    subparsers = parser.add_subparsers(metavar='command')       
    parser_test = subparsers.add_parser('test')
    parser_test.set_defaults(func=self_DJVUmaker.cli_test)
    
    parser_backend = subparsers.add_parser('backend', help='Backends handling. See '
                                            '`{}backend --help`'.format(parser.prog))
    parser_backend.set_defaults(func=self_DJVUmaker.cli_backend)
    parser_backend.add_argument('command', choices=['install', 'set'],
                                help='installs or sets backend')
    parser_backend.add_argument('backend', choices=REGISTERED_BACKENDS_KEYS,
                                        help='choosed backend', nargs="?")

    parser_convert = subparsers.add_parser('convert', help='Convert file to djvu')
    parser_convert.set_defaults(func=self_DJVUmaker.cli_convert)
    group_convert = parser_convert.add_mutually_exclusive_group(required=True)
    group_convert.add_argument('-p', "--path", 
                                help="convert file under PATH to djvu using default settings",
                                action="store", type=str)
    group_convert.add_argument('-i', "--id", 
                                help="convert file with ID to djvu using default settings", 
                                action="store", type=int)
    group_convert.add_argument("--all", help="convert all pdf files in calibre's library", 
                                action="store_true")

    parser_install_deps = subparsers.add_parser('install_deps', 
        help='(depreciated) alias for `{}backend install djvudigital`'.format(parser.prog))
    parser_install_deps.set_defaults(func=self_DJVUmaker.cli_backend, command='install',
                                     backend='djvudigital')
    parser_convert_all  = subparsers.add_parser('convert_all', 
        help='(depreciated) alias for `{}convert --all`'.format(parser.prog))
    parser_convert_all.set_defaults(func=self_DJVUmaker.cli_convert, all=True)
    return parser


def version_str_to_intlist(verstr):
    '''Conversion from 'x.y.z' to [x, y, z] version format.'''
    return [int(x) for x in verstr.split('.')]
def version_intlist_to_str(verintlist):
    '''Conversion from [x, y, z] to 'x.y.z' version format.'''
    return '.'.join(map(str,verintlist))

def discover_backend(backend_name, preferences, folder):
    '''
    Discovers backend locations and versions. Currently works only for pdf2djvu.
    Assumes folder structure and existence of backend cli flag --version, 
    with output in specific format.

    Side effect:
        If value of version under preferences does not reference to existing installed backend
        it's updates preferences to recognize this issue (set's value of version to None). 

    Checks:
        1. Under djvumaker/{backend_name}-{saved_installed_version}/{backend_name}
        2. Under djvumaker/{backend_name}-{other_versions}/{backend_name}
        3. Under {backend_name} (it works if backend_name is on PATH ENV)

    Return values:
    (backend_path, saved_version, best_installed_version, version_under_path)
    
    Return values description:
        1. backend_path            - path to found backend executable
        2. saved_version           - version saved in plugin JSON file
        3. best_installed_version  - best version in coresponding folder
        4. version_under_path      - version of executable under PATH
    backend_path links to first found version during checks. If it's not found it takes None value.
    If there is no valid version under value 2, 3 or 4, this value is None.
    '''
    # Check 1:
    backend_path = None
    saved_version = preferences[backend_name]['version']
    if saved_version is not None:
        try:
            sbp_out = subprocess.check_output([create_backend_link(backend_name, saved_version), 
                '--version'], stderr= subprocess.STDOUT)
            backend_path = create_backend_link(backend_name, saved_version)
        except OSError:
            saved_version = None
            # Side effect:
            preferences[backend_name]['version'] = None
            preferences.commit()

    # Check 2:
    try:
        folders_list = [filename.split('-') for filename in os.listdir(folder) if os.path.isdir(
            os.path.join(folder, filename))]
        installed_versions = [folder_name[1] for folder_name in folders_list if 
            folder_name[0] == backend_name]
        best_installed_version = version_intlist_to_str(sorted(
            [version_str_to_intlist(version) for version in installed_versions])[-1])
        if backend_path is None:
            backend_path = create_backend_link(best_installed_version)
    except OSError, IndexError:
        best_installed_version = None

    # Check 3:
    try:
        sbp_out = subprocess.check_output([backend_name, '--version'], stderr= subprocess.STDOUT)
        version_under_path = sbp_out.splitlines()[0].split()[1]
        if backend_path is None:
            backend_path = backend_name
    except OSError:
        version_under_path = None

    return backend_path, saved_version, best_installed_version, version_under_path

def create_backend_link(backend_name, version):
    return os.path.join(os.path.join('djvumaker', '{}-{}'.format(backend_name, version), backend_name))

def install_pdf2djvu(PLUGINNAME, preferences, log=print):    
    # log(version_intlist_to_str(find_newest_pdf2dju('djvumaker')))   
    log(discover_backend('pdf2djvu', preferences, 'djvumaker'))     
    try:
        sbp_out = subprocess.check_output([os.path.join('djvumaker', 'pdf2djvu-0.9.5', 'pdf2djvu'),
            '--version'], stderr= subprocess.STDOUT)
        curr_version = sbp_out.splitlines()[0].split()[1]
        log('Version {} of pdf2djvu is found locally.'.format(curr_version))
    except OSError:
        curr_version = None
        log('pdf2djvu is not found locally.')
    except:
        log('Output:' + sbp_out)
        raise

    # DEBUG UN
    # github_latest_url = r'https://github.com/jwilk/pdf2djvu/releases/latest'
    # github_page = urllib2.urlopen(github_latest_url)
    # new_version = get_url_basename(github_page.geturl())

    # DEBUG DEL
    new_version = '0.9.5'
    # curr_version = None

    log('Version {} of pdf2djvu is available on program\'s GitHub page.'.format(new_version))



    if curr_version is None:
        if not ask_yesno_input('Do you want to download current version of pdf2djvu?', log):
            return False, None
        fpath = download_pdf2djvu(new_version, log)
        unpack_pdf2djvu(PLUGINNAME, fpath, log)
        return True, new_version

    curr_ver_intlist = version_str_to_intlist(curr_version)
    new_ver_intlist  = version_str_to_intlist(new_version)    
    if new_ver_intlist == curr_ver_intlist:                   
        log('You have already current version of pdf2djvu.')
        return True, curr_version
    elif new_ver_intlist > curr_ver_intlist:
        if not ask_yesno_input('Do you want to download newer version of pdf2djvu?', log):
            return False, None
        fpath = download_pdf2djvu(new_version, log)
        unpack_pdf2djvu(PLUGINNAME, fpath, log)
        return True, new_version
    else: #new_ver_intlist < curr_ver_intlist
        raise Exception("Newer local version than current pdf2djvu found.")

def get_url_basename(url):
    return os.path.basename(urlparse.urlsplit(url).path)

def download_pdf2djvu(new_version, log):
    def gen_zip_url(code):
        return r'https://github.com/jwilk/pdf2djvu/releases/download/{}/pdf2djvu-win32-{}.zip'.format(code, code) 
    def gen_tar_url(code):
        return r'https://github.com/jwilk/pdf2djvu/releases/download/{}/pdf2djvu-{}.tar.xz'.format(code, code)

    fallback_version = '0.9.5'
    if iswindows:                   
        fallback_arch_url = gen_zip_url(fallback_version)
        arch_url = gen_zip_url(new_version)
    else:
        fallback_arch_url = gen_tar_url(fallback_version)
        arch_url = gen_tar_url(new_version)                
    
    # DEBUG DEL
    # arch_url = 'http://pkowalczyk.pl/almost-empty.zip'
    # arch_url = 'http://pkowalczyk.pl/almost-empty.tar.xz'
    

    def download_progress_bar(i, chunk, full):
        ''''args: a count of blocks transferred so far, 
        a block size in bytes, and the total size of the file'''
        printProgressBar(i*chunk, full, prefix = '\tProgress:', suffix = 'Complete', 
                         length=50, prints=print)

    def check_msg(fpath, msg):
        return (
                'Content-Length' in msg and int(msg['Content-Length']) > 0
            and 'Content-Type' in msg and msg['Content-Type'].split('/')[0] == 'application'
            and 'Content-Disposition' in msg 
            and msg['Content-Disposition'].split(';')[0] == 'attachment' 
            and msg['Content-Disposition'].split(';')[1].strip() == 'filename={}'.format(
                os.path.basename(fpath))
                )

    log('Downloading current version of pdf2djvu...')
    if not os.path.isdir('djvumaker'):
        os.mkdir('djvumaker')
    fpath, msg = urllib.urlretrieve(arch_url, os.path.join('.', 'djvumaker', get_url_basename(arch_url)),
                                    download_progress_bar)
    print()
    if not check_msg(fpath, msg):
        log('Cannot download current version {} from GitHub.'.format(new_version))
        if new_version != fallback_version:
            log('Trying download version {}...'.format(fallback_version), download_progress_bar)
            fpath, msg_fallback = urllib.urlretrieve(fallback_arch_url, os.path.join('.','djvumaker', 
                                                     get_url_basename(fallback_arch_url)), 
                                                     download_progress_bar)
            print()
            if not check_msg(fpath, msg_fallback):
                raise Exception('Cannot download pdf2djvu.')
    else:
        log('Dowloaded {} file'.format(os.path.abspath(fpath)))
    return fpath

def unpack_pdf2djvu(PLUGINNAME, fpath, log): 
    # log(fpath)
    log('Extracting now...')
    if iswindows:
        from zipfile import ZipFile
        with ZipFile(fpath, 'r') as myzip:
            myzip.extractall(os.path.dirname(fpath))
        
    else:
        subprocess.call(['tar', 'xf', fpath, '-C', os.path.dirname(fpath)])
        # raise Exception('Python 2.7 Standard Library cannot unpack tar.xz archive, do this manually')
    log('Extracted downloaded archive')
    os.remove(fpath)
    log('Removed downloaded archive')

# Print iterations progress
def printProgressBar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', prints=print):
    """
    source: http://stackoverflow.com/a/34325723/2351523
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    prints('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total:
        prints()

def ask_yesno_input(question, prints=print):
    while True:
        prints(question + ' (y/n)')
        user_input = raw_input().lower()
        if user_input == 'y':
            return True
        elif user_input == 'n':
            return False
        else:
            prints("Your input is not 'y' or 'n'.")
