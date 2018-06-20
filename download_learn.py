import requests
from lxml import html
from lxml.cssselect import CSSSelector
from urllib.parse import urlparse, parse_qs, unquote
import pickle
import json
import re
import os


## Change these:

# Cookie can be obtained from Chrome/Firefox Developer tools, inspecting the request header
cookie='COOKIE GOES HERE'
# Best to keep same user-agent as on your browser
UserAgent='User agent string here'
baseurl = 'https://www.learn.ed.ac.uk'


def get_course_ids(cookie):
    # Taking the cookie in, the function makes a request to the learn server
    # and extracts list of courses.
    # Returns list of dictionaries ['id'] & ['name']
    # Query the webpage for list of courses we are enrolled in:
    headers = { 'Cookie' : cookie,
    'User-Agent': UserAgent }
    params = { 'action': 'refreshAjaxModule',
    'modId': '_4_1',
    'tabId': '_1_1',
    'tab_tab_group_id': '_171_1'}
    request_url = '/webapps/portal/execute/tabs/tabAction'
    r = requests.post(baseurl+request_url,params=params,headers=headers)
    tree = html.fromstring(r.content)
    # Select and extract all links
    sel = CSSSelector('a')
    courses = []
    temp = {}
    for e in sel(tree):
        if e.get('href')!= '#':
            temp['id']= parse_qs(e.get('href'))['id'][0]
            temp['name']=e.text
            # Append a new copy of the temporary variable
            courses.append(temp.copy())
    print(courses)
    return courses

def get_folder_structure(cookie, courses):
    baseurl = 'https://www.learn.ed.ac.uk/webapps/blackboard/execute/course/menuFolderViewGenerator'
    headers = { 'Cookie' : cookie,
    'User-Agent': UserAgent }
    folders = []
    for course in courses:
        params = { 'storeScope': 'Session',
        'course_id': course['id'],
        'expandAll': 'true',
        'displayMode': 'courseMenu_newWindow',
        'editMode': 'false',
        'openInParentWindow': 'true'}
        r = requests.post(baseurl,params=params,headers=headers)
        folder = r.json()
        folders.append(folder.copy())
    return folders

def get_item_structure(cookie, item_id, course_id):
    print('requesting item: ID:', item_id, ' Course id: ', course_id)
    baseurl = 'https://www.learn.ed.ac.uk/webapps/blackboard/execute/course/menuFolderViewGenerator'
    headers = { 'Cookie' : cookie,
    'User-Agent': UserAgent }
    params = { 'initTree': 'true',
    'storeScope': 'Session',
    'itemId': item_id,
    'course_id': course_id,
    'displayMode': 'courseMenu_newWindow',
    'editMode': 'false',
    'openInParentWindow': 'true'}
    r = requests.post(baseurl,params=params,headers=headers)
    response = r.json()
    return response

def parse_children(data,course_id, depth=0, path=''):
    # recursive function that parses the folder structure and downloads files by calling 
    # Download_item function.
    # It also creates the folder structure on the go and quite inefficiently
    cwd = os.getcwd()
    os.makedirs(path,exist_ok=True)
    os.chdir(path)
    for child in data['children']:
        if child['hasChildren']==True:
            new_path = ''
            if child['contents']:
                tree = html.fromstring(child['contents'])
                for e in tree.cssselect("a"):
                    #print(path, course_id, e.text.strip())
                    new_path = e.text.strip()
            else:
                new_path = 'UNKNOWN'
            tmp = depth + 1
            path = new_path
            parse_children(child,course_id,tmp,path)
        else:
            if 'CONTENT' in child['id']:
                tree = html.fromstring(child['contents'])
                for e in tree.cssselect("a"):
                    print ('Downloading: ', e.get("title"), e.get("href"))
                    download_item(cookie, e.get("href"))
                #for elem in tree.iterlinks():
                #    print(elem[2])
                Id = child['id'].split(':::')[1]
                #print("\t"*depth, course_id, child['type'], Id)
            elif child['contents']:
                #temp['name']=e.text
                tree = html.fromstring(child['contents'])
                for e in tree.cssselect("a"):
                    pass
                    #print(path, course_id, e.text.strip())
            # here we do magic?
    os.chdir(cwd)



def save_data(data):
    f = open('store.pckl', 'wb')
    pickle.dump(data, f)
    f.close()

def load_data():
    f = open('store.pckl', 'rb')
    obj = pickle.load(f)
    f.close()
    return obj
def download_item(cookie, url, path='./'):
    # Downloads item to a path, unless same item exists and has same content-length
    # The function also looks for all downloadable links using regex pattern.
    cwd = os.getcwd()
    os.makedirs(path,exist_ok=True)
    os.chdir(path)
    headers = { 'Cookie' : cookie,
    'User-Agent': UserAgent }
    params = {'launch_in_new': 'true'}
    r = requests.get(baseurl+url,headers=headers,params=params)
    print(r.status_code)
    # extract urls here??
    pattern = "/bbcswebdav[^'\"]*"
    result = re.findall(pattern, r.text)
    for match in result:
        #print(match)
        p = requests.head(baseurl+match,headers=headers)
        if not 'location' in p.headers:
            continue
        filename = unquote(p.headers['location'].split('/')[-1])
        print(filename)
        r = requests.get(baseurl+p.headers['location'],headers=headers,stream=True)
        print(r.status_code)
        if 'Content-length' in r.headers:
            size = r.headers['Content-length']
        else:
            size = 0
        # if file exists and has same size, we 
        #r.response.close()
        # else we download:
        if os.path.isfile(filename) and int(os.stat(filename).st_size)==int(size):
            print("skipping!")
            r.close()
        else:
            with open(filename, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=128):
                    fd.write(chunk)
    os.chdir(cwd)




# Main program starts here:
courses = get_course_ids(cookie)
folders = get_folder_structure(cookie,courses)

## For debugging purposes, this can be used to save and load the folder structure not to cause much traffic.
#save_data([courses, folders])
#[courses, folders] = load_data()

for i in range(len(courses)):
    print(i,courses[i]['name'])
    # to resume the download at point other than beginning, change the condition below:
    if i>-1:
        parse_children(folders[i],courses[i]['id'], path=courses[i]['name'])





