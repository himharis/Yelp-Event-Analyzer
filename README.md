# Yelp Event Analyzer

## Introduction
This project aims to create a simple web application that returns information about Yelp Fusion events that are associated with cities and states in the US. Some modules are adopted to allow this application to access data efficiently with caching via scraping and web API and manipulate the data using SQLite into information. Then, Plotly and Flask are used for data visualization on this website.


## Data Sources
1. The web from Wikipedia, which is the data source for the table "Cities" in the database. (https://en.wikipedia.org/wiki/List_of_United_States_cities_by_population). 
2. Yelp Fusion, which is the data source for the table "Restaurants" in the database. (https://www.yelp.com/developers/documentation/v3/featured_event)

## Data Processing
1. Create the table named “Cities” in the database
2. Create the table named “Events” in the database
3. Fill the table named Cities with data that are retrieved from scraping Wikipedia website.
4. Fill the table named Events with data that are retrieved from scraping the yelp fusion website.
5. Rated the events by the most interested count from the data
6. Rated the events by the most attending count from the data
7. Rated the 20 most populated cities in the US
8. Compare the city or state by the level of interest of the events

## Data Presentation
This app is represented on a website by using Flask and Plotly to show the data.

## Run the Program
### Step 1: Apply an API Key for Yelp Fusion
1 Go to "https://www.yelp.com/developers/documentation/v3/authentication" and create your app according to the instruction. 

2 Create a new python file "secret.py" in the same folder as "webapp.py". And add the code:
  ```
  API_KEY = '<your key>'
  ```  
### Step 2: Install packages

1. Some packages used on this app are as follow:
    - beautifulsoup
    - bs4
    - requests
    - Flask
    - Jinja2
    - Plotly
    - json
    - sqlite3

2. You can type on your python terminal this code:
   ```
    pip install <'packages'>
   ```
   or
   ```
    pip3 install <'packages'>
   ```

### Step 3: Run program.py  
1. Open your terminal
2. Go to the folder where you store the webapp.py 
3. Type this code on your terminal:

```  
$ python webapp.py
```  
### Step 4: Open "http://127.0.0.1:5000/ " in a browser

## Results
