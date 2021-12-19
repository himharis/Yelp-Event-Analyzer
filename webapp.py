import secret
from bs4 import BeautifulSoup
import requests
import json
import sqlite3
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from plotly.offline import plot
from flask import Flask, render_template, Markup


DB_NAME = 'tableResult.sqlite'
API_KEY = secret.API_KEY #API_KEY is located on the secret.py file
HEADERS = {'Authorization': 'Bearer {}'.format(API_KEY),
           'User-Agent': 'YelpEventAnalyzer',
           'From': 'himharis@icloud.com',
           'Course-Info': 'https://si.umich.edu/programs/courses/507'
}

app = Flask(__name__)

#########################################
################ Class ##################
#########################################

class City:
    '''deifinition of the class city

    Instance Attributes
    -------------------
    id_pos: int
        the id(position) of the city instance in the data
    name: string
        the name of the city instance
    state: string
        the state name that the city is located at
    population: int
        the population of the city
    area: float
        the area of the city in Square mile
    latitude: string
        the latitude of the city center
    longitude: string
        the longitude of the city center

    '''
    def __init__(self, id_pos=0, name=None, state=None, population=0, area=0, latitude='', longitude=''):
        self.id_pos = id_pos
        self.name = name
        self.state = state
        self.population = population
        self.area = area
        self.latitude = latitude
        self.longitude = longitude

class Event:
    '''definition of the class event

     Instance Attributes
    -------------------
    category: string
        the category of the event
    cost: int
        cost of attending the event
    intereseted: int
        the number of people who are intereseted to attend the event
    yelp_id: string
        the unique identifer for the event
    url: string
        the website for the event on Yelp
    participants: int
        the number of participants
    name: string
        the official name of the events
    city: string
        the city name that the event located at
    state: string
        the state name that the event is located at
    city_id: int
        the id of the city in the table "cities"
    '''
    def __init__(self, interested=0, cost=None, category='', yelp_id='', url='',
                 participants=0, name='', city='', state='', city_id = 0):
        self.interested = interested
        self.cost = cost
        self.category = category
        self.yelp_id = yelp_id
        self.url = url
        self.participants = participants
        self.name = name
        self.city = city
        self.state = state
        self.city_id = city_id

#########################################
############### Caching #################
#########################################

def load_cache(cache_file_name):
    '''Load response text cache if already generated, else initiate an empty dictionary.

    Parameters
    ----------
    None

    Returns
    -------
    cache: dictionary
        The dictionary which maps url to response text.
    '''
    try:
        cache_file = open(cache_file_name, 'r')
        cache_file_contents = cache_file.read()
        cache = json.loads(cache_file_contents)
        cache_file.close()
    except:
        cache = {}
    return cache

def save_cache(cache, cache_file_name):
    '''Save the cache

    Parameters
    ----------
    cache: dictionary
        The dictionary which maps url to response.

    Returns
    -------
    None
    '''
    cache_file = open(cache_file_name, 'w')
    contents_to_write = json.dumps(cache)
    cache_file.write(contents_to_write)
    cache_file.close()

CACHE_FILE = 'cache.json'
CACHE_DICT = load_cache(CACHE_FILE)

#########################################
########### Data Processing #############
#########################################

def db_create_table_cities():
    ''' create the table named "Cities" in the database

    Parameters
    ----------
    None

    Returns
    -------
    none
    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # drop_cities_sql = 'DROP TABLE IF EXISTS "Cities"'
    create_cities_sql = '''
        CREATE TABLE IF NOT EXISTS "Cities" (
            "Id" INTEGER PRIMARY KEY UNIQUE,
            "Name" TEXT NOT NULL,
            "State" TEXT NOT NULL,
            "Population" INTEGER NOT NULL,
            "Area" REAL NOT NULL,
            "Latitude" TEXT NOT NULL,
            "Longitude" TEXT NOT NULL
        )
    '''
    # cur.execute(drop_cities_sql)
    cur.execute(create_cities_sql)
    conn.commit()
    conn.close()

def db_create_table_events():
    ''' create the table named "Events" in the database

    Parameters
    ----------
    None

    Returns
    -------
    none
    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # drop_events_sql = 'DROP TABLE IF EXISTS "Events"'
    create_events_sql = '''
        CREATE TABLE IF NOT EXISTS "Events" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "Interested" INTEGER NOT NULL,
            "Name" TEXT NOT NULL UNIQUE,
            "City_id" INTEGER NOT NULL,
            "City" TEXT NOT NULL,
            "State" TEXT NOT NULL,
            "Participants" INTEGER,
            "Cost" INTEGER,
            "Category" TEXT,
            "Yelp_id" TEXT NOT NULL UNIQUE,
            "Url" TEXT
        )
    '''
    # cur.execute(drop_events_sql)
    cur.execute(create_events_sql)
    conn.commit()
    conn.close()

def db_write_table_cities(city_instances):
    ''' write data into the table "Cities" in the database

    Parameters
    ----------
    city_instances: list
        a list of city instances

    Returns
    -------
    none
    '''
    insert_cities_sql = '''
        INSERT OR IGNORE INTO Cities
        VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for c in city_instances:
        cur.execute(insert_cities_sql,
                        [c.id_pos, c.name, c.state, c.population, c.area, c.latitude, c.longitude])

    conn.commit()
    conn.close()

def db_write_table_events(event_instances):
    ''' write data into the table "Events" in the database

    Parameters
    ----------
    event_instances: list
        a list of event instances

    Returns
    -------
    none
    '''
    insert_events_sql = '''
        INSERT OR IGNORE INTO Events
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    for r in event_instances:
        cur.execute(insert_events_sql,
            [ r.interested, r.name, r.city_id, r.city, r.state, r.participants, r.cost, r.category, r.yelp_id, r.url]
        )

    conn.commit()
    conn.close()

def build_city_instance():
    ''' function that scrapes the wikpedia page and build city instances 

    Parameters
    ----------
    none

    Returns
    -------
    city_instances: list
        a list of 314 different city instances
    '''
    # CACHE_DICT = load_cache(CACHE_FILE)
    city_instances = []
    site_url = 'https://en.wikipedia.org/wiki/List_of_United_States_cities_by_population'
    url_text = make_url_request_using_cache(url_or_uniqkey=site_url)
    soup = BeautifulSoup(url_text, 'html.parser')
    tr_list = soup.find('table', class_='wikitable sortable').find('tbody').find_all('tr')[1:] # total 326 cities in the list, each in a row
    for tr in tr_list: # each tr is a city row, td is the data in each column
        td_list = tr.find_all('td')
        id_posts = tr.find_all('th')
        id_pos = int(id_posts[0].text.strip())
        name = str(td_list[0].find('a').text.strip())
        try:
            state = str(td_list[1].find('title').text.strip())
        except:
            state = td_list[1].text.strip()
        population = int(td_list[3].text.strip().replace(',', ''))
        area = float(td_list[5].text.strip().split('\xa0')[0].replace(',', ''))
        lati_longi = td_list[9].find('span', class_='geo-dec').text.strip().split(' ')
        latitude = str(lati_longi[0])
        longitude = str(lati_longi[1])
        instance = City(id_pos=id_pos, name=name, state=state, population=population,
                        area=area, latitude=latitude, longitude=longitude
        )
        city_instances.append(instance)

    return city_instances

def build_event_instance(city_instances):
    ''' function that searches events in different cities
        according to the city_instances list from the Yelp Fusion API

    Parameters
    ----------
    city_instances: list
        a list of 326 different city instances

    Returns
    -------
    event_instances: list
        a list of thousands of different events instances
    '''
    # CACHE_DICT = load_cache(CACHE_FILE)
    event_instances = []
    endpoint_url = 'https://api.yelp.com/v3/events'
    for c in city_instances:
        city = c.name
        params = {'location': city + ',' + c.state}
        uniqkey = construct_unique_key(endpoint_url, params)
        results = make_url_request_using_cache(url_or_uniqkey=uniqkey, params=params)
        if 'events' in results.keys():
            for event in results['events']:
                interested = event['interested_count']
                try:
                    cost = len(event['cost'].strip())
                except:
                    cost = None
                category = event ['category']
                yelp_id = event['id']
                url = event['event_site_url']
                participants = event['attending_count']
                name = event['name']
                state = event['location']['state']
                instance = Event(interested=interested, cost=cost, category=category, yelp_id=yelp_id,
                                      url=url, participants=participants, name=name, city=city, state=state, city_id=c.id_pos)
                event_instances.append(instance)

    return event_instances

def construct_unique_key(baseurl, params):
    ''' constructs a key that is guaranteed to uniquely and
    repeatably identify an API request by its baseurl and params

    Parameters
    ----------
    baseurl: string
        The URL for the API endpoint
    params: dictionary
        A dictionary of param: param_value pairs

    Returns
    -------
    string
        the unique key as a string
    '''
    param_strings = []
    connector = '_'
    for k in params.keys():
        param_strings.append(f'{k}_{params[k]}')

    param_strings.sort()
    unique_key = baseurl + connector + connector.join(param_strings)
    return unique_key

def make_url_request_using_cache(url_or_uniqkey, params=None):
    '''Given a url, fetch if cache not exist, else use the cache.

    Parameters
    ----------
    url: string
        The URL for a specific web page
    cache_dict: dictionary
        The dictionary which maps url to response text
    params: dictionary
        A dictionary of param: param_value pairs

    Returns
    -------
    cache[url]: response
    '''
    if url_or_uniqkey in CACHE_DICT.keys():
        print('Using cache')
        return CACHE_DICT[url_or_uniqkey]

    print('Fetching')
    if params == None: # dictionary: url -> response.text
        # time.sleep(1)
        response = requests.get(url_or_uniqkey, headers=HEADERS)
        CACHE_DICT[url_or_uniqkey] = response.text
    else: # dictionary: uniqkey -> response.json()
        endpoint_url = 'https://api.yelp.com/v3/events'
        response = requests.get(endpoint_url, headers = HEADERS, params=params)
        CACHE_DICT[url_or_uniqkey] = response.json()
    
    save_cache(CACHE_DICT, CACHE_FILE)
    return CACHE_DICT[url_or_uniqkey]

def build_database():
    '''initialize and create the database according to the city instances 
       and event instances (either fetch or use cache)

    Parameters
    ----------
    none

    Returns
    -------
    none
    '''
    print('Building database...')
    city_instances = build_city_instance()
    db_create_table_cities()
    db_write_table_cities(city_instances)
    event_instances = build_event_instance(city_instances)


    db_create_table_events()
    db_write_table_events(event_instances)
    print('Finished building database!')

def searchDB(query):
    '''Search the database and return the results given the sqlite query

    Parameters
    ----------
    query: string
        a sqlite query command

    Returns
    -------
    result: list
        a list of tuples that contains the results
    '''
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    result = cursor.execute(query).fetchall()
    connection.close()
    return result

#########################################
########### Data Presentation ###########
#########################################

def get_avg_and_sort(results):
    '''given a query search results, return the average value for the given category
       and sort the results in descending order

    Parameters
    ----------
    resutls: list of tuples
        the query search returned by the database

    Returns
    -------
    xvals: list
        the name of the attribute
    yvals: list
        the average value for the corresponding attribute
    '''
    # result is the list of tuples returned by database query. The tuple must be length of 2!
    dict_rating = {}
    for row in results:
        data0 = row[0]
        data1 = float(row[1])
        if data0 in dict_rating.keys():
            dict_rating[data0].append(data1)
        else:
            temp = [] #controling others
            temp.append(data1)
            dict_rating[data0] = temp

    dict_avg = {}
    for key, value in dict_rating.items():
        total = 0
        for val in value:
            total += val
        avg = float(total / len(value))
        dict_avg[key] = avg

    sorted_dict = sorted(dict_avg.items(), key=lambda x:x[1], reverse=True)
    xvals = []
    yvals = []
    for i in range(len(sorted_dict)):
        xvals.append(sorted_dict[i][0])
        yvals.append(sorted_dict[i][1])

    return xvals, yvals

def flask_plot(xvals, yvals, title, fig_type):
    ''' this function generetes either bar chart or pie chart 
        and return the plot that is used for displaying in
        the html webpage

    Parammeters
    -----------
    xvals: list
        a list of x values
    yvals: list
        a list of y values that correspond to the x values
    title: string
        the title of the plot
    fig_type: string
        either "bar" or "pie" that defines the output plot type

    Returns
    --------
    fig_div: string
        the plot that is readable by html files
    '''
    fig = make_subplots(rows=1, cols=1, specs=[[{"type": fig_type}]], subplot_titles=(title))
    if fig_type == 'pie':
        fig.add_trace(go.Pie(labels=xvals, values=yvals), row=1, col=1)
        fig.update_traces(hole=.4, hoverinfo="label+percent+name")
    elif fig_type == 'bar':
        fig.add_trace(go.Bar(x=xvals, y=yvals), row=1, col=1)

    fig.update_layout(annotations=[dict(text=title, font_size=25, showarrow=False)])
    fig_div = plot(fig, output_type="div")
    return fig_div

def barplot_city_population():
    ''' a function that generate a barplot for the population 
        according to the cities

    Parameters
    ----------
    none

    Returns
    -------
    string
        the plot that is readable by html files
    '''
    query = '''SELECT Name, Population, State FROM Cities
                ORDER BY Population DESC'''
    result = searchDB(query)
    xvals = []
    yvals = []
    for row in result[:20]:
        xvals.append('{}({})'.format(row[0], row[2]))
        yvals.append(int(row[1]))

    title = 'Top 20 Cities By Population In The US'
    return flask_plot(xvals, yvals, title, 'bar')



########## plots for cities or states ############

def pieplot_event_categories(name, target, id_pos=None):
    ''' a function that generate a pieplot for the percentage
        of each event category in the city or state specified 

    Parameters
    ----------
    name: string
        a city name or a state name
    target: string
        indicates the name is a city or a state
    id_pos: int
        the id that uniquely identify a city

    Returns
    -------
    string
        the plot that is readable by html files
    '''

    query = '''SELECT r.Category FROM Events as r
                JOIN Cities as c ON c.Id=r.City_id'''
    if target == 'city':
        query += ''' WHERE r.City="{}" AND c.Id={}'''.format(name, id_pos)
    elif target == 'state':
        query += ''' WHERE c.State="{}"'''.format(name)

    results = searchDB(query)
    dict_category = {}
    for row in results:
        category = row[0]
        if category in dict_category.keys():
            dict_category[category] += 1
        else:
            dict_category[category] = 1

    sorted_list = sorted(dict_category.items(), key=lambda x:x[1], reverse=True)
    labels = []
    values = []
    for row in sorted_list:
        labels.append(row[0])
        values.append(row[1])
    title = '''Popular Event Types in {} {}'''.format(name, target.capitalize())
    return flask_plot(labels, values, title, 'pie')

def pieplot_interest(name, target, id_pos=None):
    ''' a function that generate a pieplot for the percentage
        of interested people to the events in the city or state specified 

    Parameters
    ----------
    name: string
        a city name or a state name
    target: string
        indicates the name is a city or a state
    id_pos: int
        the id that uniquely identify a city

    Returns
    -------
    string
        the plot that is readable by html files
    '''

    query = '''SELECT r.Interested FROM Events as r
                JOIN Cities as c ON c.Id=r.City_id'''
    if target == 'city':
        query += ''' WHERE r.City="{}" AND c.Id={}'''.format(name, id_pos)
    elif target == 'state':
        query += ''' WHERE c.State="{}"'''.format(name)

    results = searchDB(query)
    dict_interest = {'low': 0, 'netral': 0, 'high': 0}
    for row in results:
        if row[0] <= 50:
            dict_interest['low'] += 1
        elif row[0] <= 100:
            dict_interest['netral'] += 1
        else:
            dict_interest['high'] += 1

    labels = list(dict_interest.keys())
    values = list(dict_interest.values())
    title = 'The Percentage of Interest in {} {}'.format(name, target.capitalize())
    return flask_plot(labels, values, title, 'pie')


def barplot_avgrating_each_category(name, target, id_pos=None):
    ''' a function that generate a barplot for the average rating 
        of differnt event types in the city or state specified 

    Parameters
    ----------
    name: string
        a city name or a state name
    target: string
        indicates the name is a city or a state
    id_pos: int
        the id that uniquely identify a city

    Returns
    -------
    string
        the plot that is readable by html files
    '''
    # name = process_name(name)
    query = '''SELECT r.Category, r.Interested FROM Events as r
                JOIN Cities as c ON c.Id=r.City_id'''
    if target == 'city':
        query += ''' WHERE r.City="{}" AND c.Id={}'''.format(name, id_pos)
    elif target == 'state':
        query += ''' WHERE c.State="{}"'''.format(name)

    results = searchDB(query)
    xvals, yvals = get_avg_and_sort(results)
    title = 'Average Interest of Events By Category in {} {}'.format(name, target.capitalize())
    return flask_plot(xvals, yvals, title, 'bar')


def barplot_avgparticipants_each_category(name, target, id_pos=None):
    ''' a function that generate a barplot for the average number of participants
        of differnt event types in the city or state specified

    Parameters
    ----------
    name: string
        a city name or a state name
    target: string
        indicates the name is a city or a state
    id_pos: int
        the id that uniquely identify a city

    Returns
    -------
    string
        the plot that is readable by html files
    '''
    # name = process_name(name)
    query = '''SELECT r.Category, r.Participants FROM Events as r
                JOIN Cities as c ON c.Id=r.City_id'''
    if target == 'city':
        query += ''' WHERE r.City="{}" AND c.Id={}'''.format(name, id_pos)
    elif target == 'state':
        query += ''' WHERE c.State="{}"'''.format(name)

    results = searchDB(query)
    xvals, yvals = get_avg_and_sort(results)
    title = 'Average Number of Participants of Different Categories in {} {}'.format(name, target.capitalize())
    return flask_plot(xvals, yvals, title, 'bar')

def barplot_toprated_events(name, target, id_pos=None):
    ''' a function that generate a barplot for the top rated events
        in the city or state specified 

    Parameters
    ----------
    name: string
        a city name or a state name
    target: string
        indicates the name is a city or a state
    id_pos: int
        the id that uniquely identify a city

    Returns
    -------
    string
        the plot that is readable by html files
    '''
    # name = process_name(name)
    query = '''SELECT r.Name, r.Interested FROM Events as r
                JOIN Cities as c ON c.Id=r.City_id'''
    if target == 'city':
        query += ''' WHERE r.City="{}" AND c.Id={} ORDER BY r.Interested DESC'''.format(name, id_pos)
    elif target == 'state':
        query += ''' WHERE c.State="{}" ORDER BY r.Interested DESC'''.format(name)

    results = searchDB(query)
    xvals = []
    yvals = []
    for row in results[:50]:
        xvals.append(str(row[0]))
        yvals.append(float(row[1]))

    title = 'Top Rated Events in {} {}'.format(name, target.capitalize())
    return flask_plot(xvals, yvals, title, 'bar')


def barplot_mostattended_event(name, target, id_pos=None):
    ''' a function that generate a barplot for the most 
        attended events in the city or state specified 

    Parameters
    ----------
    name: string
        a city name or a state name
    target: string
        indicates the name is a city or a state
    id_pos: int
        the id that uniquely identify a city

    Returns
    -------
    string
        the plot that is readable by html files
    '''

    query = '''SELECT r.Name, r.Participants FROM Events as r
                JOIN Cities as c ON c.Id=r.City_id'''
    if target == 'city':
        query +=  ''' WHERE r.City="{}" AND c.Id={} ORDER BY r.Participants DESC'''.format(name, id_pos)
    elif target == 'state':
        query += ''' WHERE c.State="{}" ORDER BY r.Participants DESC'''.format(name)

    results = searchDB(query)
    xvals = []
    yvals = []
    for row in results[:50]:
        xvals.append(str(row[0]))
        yvals.append(float(row[1]))

    title = 'Top Events With Most Number of Participants in {} {}'.format(name, target.capitalize())
    return flask_plot(xvals, yvals, title, 'bar')

# ########### plots for comparisons ###########

def compare_city_barplot_interest():
    ''' a function that generate a barplot for the average interest
        of all the events in each city. Ranked by descending order.

    Parameters
    ----------
    none

    Returns
    -------
    string
        the plot that is readable by html files
    '''
    query = '''SELECT City, State, Interested FROM Events'''
    results = searchDB(query)
    res_combined = []
    for row in results:
        uniq = row[0] + "({})".format(row[1])
        temp = []
        temp.append(uniq)
        temp.append(row[2])
        res_combined.append(temp)

    xvals, yvals = get_avg_and_sort(res_combined)
    title = 'City Ranking by Average Interseted Number of Yelp Events'
    return flask_plot(xvals, yvals, title, 'bar')


def compare_state_barplot_interest():
    ''' a function that generate a barplot for the average interest
        of all the events in each state. Ranked by descending order.

    Parameters
    ----------
    none

    Returns
    -------
    string
        the plot that is readable by html files
    '''
    query = '''SELECT c.State, r.Interested FROM Cities as c
               JOIN Events as r ON c.Id=r.City_id'''
    results = searchDB(query)
    xvals, yvals = get_avg_and_sort(results)
    title = 'State Ranking by Average Interested Number of Yelp Events'
    return flask_plot(xvals, yvals, title, 'bar')

#########################################
############# Flask Web App #############
#########################################

@app.route('/')
def home():
    ''' Function to design the home page

    Parameters
    ----------
    None

    Returns
    -------
    html template that contains city_dict which is a dictionary.
    The key is the city id, the value is a list that contains city name, state and population
    '''
    city_dict = {}
    query = '''SELECT Id, Name, State, Population FROM Cities'''
    results = searchDB(query)
    for row in results:
        temp = []
        temp.append(row[1])
        temp.append(row[2])
        temp.append(row[3])
        city_dict[row[0]] = temp

    return render_template('home.html', city_dict=city_dict)

@app.route('/population')
def population():
    ''' a function a that design the population page which contains a barplot

    Parameters
    ----------
    none

    Returns
    ----------
    html template that contains figure which is a plot.
    '''
    figure = barplot_city_population()
    return render_template('plot.html', figure=Markup(figure))

@app.route('/list/<city_or_state>/<nm>/')
def choice_list(city_or_state, nm):
    ''' a function designs the webpage that contains the list of plot options

    Parameters:
    city_or_state: string
        either "city" or "state" that indicates if the nm is a city or state
    nm: string
        the name of the city or the state

    Returns
    -------
    a html template that contains city_or_state and nm.
    '''
    if city_or_state == 'state':
        return render_template('list.html', city_or_state=city_or_state, name=nm)
    else:
        id_city = nm.split('_')
        id_pos = int(id_city[0])
        name = id_city[1]
        return render_template('list.html', city_or_state=city_or_state, name=name, id_pos=id_pos)

@app.route('/plot/<city_or_state>/<nm>/<choice>')
def data(city_or_state, nm, choice):
    ''' a function designs the webpage that contains the plot

    Parameters:
    city_or_state: string
        either "city" or "state" that indicates if the nm is a city or state
    nm: string
        the name of the city or the state

    Returns
    -------
    html template that contains figure which is a plot.
    '''
    if city_or_state == 'state':
        # name = process_name(nm.replace('%20', ' '))
        if choice == 'pieplot_event_categories':
            figure = pieplot_event_categories(nm, city_or_state)
        elif choice == 'pieplot_interest':
            figure = pieplot_interest(nm, city_or_state)
        elif choice == 'barplot_avgrating_each_category':
            figure = barplot_avgrating_each_category(nm, city_or_state)
        elif choice == 'barplot_avgparticipants_each_category':
            figure = barplot_avgparticipants_each_category(nm, city_or_state)
        elif choice == 'barplot_toprated_events':
            figure = barplot_toprated_events(nm, city_or_state)
        elif choice == 'barplot_mostattended_event':
            figure = barplot_mostattended_event(nm, city_or_state)
    else:
        id_city = nm.split('_')
        id_pos = int(id_city[0])
        name = id_city[1]
        if choice == 'pieplot_event_categories':
            figure = pieplot_event_categories(name, city_or_state, id_pos=id_pos)
        elif choice == 'pieplot_interest':
            figure = pieplot_interest(name, city_or_state, id_pos=id_pos)
        elif choice == 'barplot_avgrating_each_category':
            figure = barplot_avgrating_each_category(name, city_or_state, id_pos=id_pos)
        elif choice == 'barplot_avgparticipants_each_category':
            figure = barplot_avgparticipants_each_category(name, city_or_state, id_pos=id_pos)
        elif choice == 'barplot_toprated_events':
            figure = barplot_toprated_events(name, city_or_state, id_pos=id_pos)
        elif choice == 'barplot_mostattended_event':
            figure = barplot_mostattended_event(name, city_or_state, id_pos=id_pos)
    
    return render_template('plot.html', figure=Markup(figure))

@app.route('/compare/<city_or_state>')
def compare(city_or_state):
    ''' a function designs the webpage that contains the plot options for comparison

    Parameters:
    city_or_state: string
        either "city" or "state"

    Returns
    -------
    html template which contains city_or_state
    '''
    return render_template('compare.html', city_or_state=city_or_state)

@app.route('/compare/<city_or_state>/interest')
def compare_choice(city_or_state):
    ''' a function designs the webpage that contains the plot for comparison

    Parameters:
    city_or_state: string
        either "city" or "state"
    interest:
        level of interest

    Returns
    -------
    html template which contains the plot
    '''
    figure = None
    if city_or_state == 'state':
        figure = compare_state_barplot_interest()
    elif city_or_state == 'city':
        figure = compare_city_barplot_interest()

    
    return render_template('plot.html', figure=Markup(figure))

if __name__ == '__main__':
    build_database()
    compare_city_barplot_interest()
 
    app.run(debug=True, use_reloader=False)
