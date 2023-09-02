import requests
from bs4 import BeautifulSoup
import time
import sqlite3
import os
from dotenv import load_dotenv
import smtplib

# globals
url = "https://github.com/ReaVNaiL/New-Grad-2024/tree/main"
intervalSeconds = 3600 # scrape every hour
jobData = []
carriers = {
    "att": "@mms.att.net",
    "tmobile": "@tmomail.net",
    "verizon": "@vtext.com",
    "sprint": "@messaging.sprintpcs.com"
}

# load environment variables from .env file
load_dotenv()

# function to send SMS
def sendSMS(message, pNum, carrier):
    recipient = pNum + carriers[carrier]
    auth = (os.getenv('EMAIL'), os.getenv('PW'))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])

    server.sendmail(auth[0], recipient, message)

# function to initialize sqlite database
def dbInit():
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            location TEXT,
            role TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# function to check for updates
def checkUpdates():
    # send http get request
    response = requests.get(url)

    # if success
    if response.status_code == 200:
        # parse with beautifulsoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # find table
        jobTable = soup.find('table')
        # if exists
        if jobTable:
            # find all table rows not including header
            rows = jobTable.find_all('tr')[1:]

            for row in rows:
                # get columns from each row
                columns = row.find_all('td')

                # add info into a data dictionary
                if len(columns) >= 5:
                    jobDict = {
                        "company": columns[0].get_text(),
                        "location": columns[1].get_text(),
                        "role": columns[2].get_text(),
                    }
                    jobData.append(jobDict)

        # connect to database
        conn = sqlite3.connect('jobs.db')
        cursor = conn.cursor()

        # find updates not in database
        newJobs = []
        for update in jobData:
            company = update['company']
            location = update['location']
            role = update['role']
            cursor.execute('SELECT id FROM jobs WHERE company = ?', (company,))
            result = cursor.fetchone()
            if not result:
                newJobs.append({
                        "company": company,
                        "location": location,
                        "role": role,
                    })
                cursor.execute('INSERT INTO jobs (company, location, role) VALUES (?, ?, ?)', (company, location, role,))
        
        conn.commit()
        conn.close()

        # send sms with update
        message = ""
        if len(newJobs) > 4:
            message = "There are 5+ new job updates on Github! https://github.com/ReaVNaiL/New-Grad-2024/tree/main"
        elif newJobs:
            message = "New Job Updates:\n"
            for job in newJobs:
                message += job['company'] + " is hiring " + job['role'] + " for these locations: " + job['location'] + "\n"
        if not message == "":
            sendSMS(message, os.getenv('PHONE_ONE'), "tmobile")
            sendSMS(message, os.getenv('PHONE_TWO'), "tmobile")

    else:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")

# init database
dbInit()

# do scraping
while True:
    checkUpdates()
    print(f"Scraped at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    time.sleep(intervalSeconds)