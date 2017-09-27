import json
import logging
import os
from base64 import b64decode
from urlparse import parse_qs

import boto3
import requests

from tabulate import tabulate

ENCRYPTED_EXPECTED_TOKEN = os.environ["kmsEncryptedToken"]
ENCRYPTED_ACCESS_CODE = os.environ["wsdotAccessCode"]

kms = boto3.client('kms')
expected_token = kms.decrypt(CiphertextBlob=b64decode(ENCRYPTED_EXPECTED_TOKEN))['Plaintext']
access_code = kms.decrypt(CiphertextBlob=b64decode(ENCRYPTED_ACCESS_CODE))['Plaintext']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def tolls(usertrip="help"):

    checktrip = usertrip.lower()

    if checktrip == "help" : # Check for 'help' parameter, return list of valid parameters
        return "Valid parameters are 'help', 'all', 'work' or trip name, i.e. '405tp01370'."

    headers = ["Route","Start","End","Trip","Toll","Message"]
    tolls   = []
    trips   = json.loads((requests.get("http://wsdot.com/traffic/api/api/tolling?AccessCode=" + access_code)).content)

    for trip in trips: # Create list of tolls, combining and discarding fields

        name        = trip.get("TripName")
        start       = trip.get("StartLocationName")
        end         = trip.get("EndLocationName")
        toll        = trip.get("CurrentToll")
        message     = trip.get("CurrentMessage")
        routedir    = trip.get("StateRoute") + trip.get("TravelDirection")
        triptoll    = [routedir,start,end,name,toll,message]

        if (checktrip == "all"): # Check for 'all' parameter, add all tolls to array
            tolls.append(triptoll)
            continue

        if (checktrip == name): # Check for trip, add toll to array
            tolls.append(triptoll)
            break

        if (checktrip == "work"): # Check for 'work' parameter
            if routedir == "405N" and start == "NE 6th": # If trip starts near work, add toll to array
                tolls.append(triptoll)
                continue
                    
    if tolls:
        tolls.sort(key=lambda x: (x[0], x[1], x[2], x[3])) # sort list of tolls
        return tabulate(tolls, headers) # return sorted list of tolls, with formatted headers
    else:
        return "A trip named " + usertrip + " was not found." # no such trip
     
def respond(err, res=None):
    return {
        "statusCode": "400" if err else "200",
        "body": err.message if err else json.dumps(res),
        "headers": {
            "Content-Type": "application/json",
        },
    }

def lambda_handler(event, context):
    params       = parse_qs(event["body"])
    token        = params["token"][0]
        
    if token != expected_token:
        logger.error("Request token (%s) does not match expected", token)
        return respond(Exception("Invalid request token"))
    
    try:
        command_text = params["text"][0]
    except:
        command_text = "help"

    return respond(None, {"text": "```" + tolls(command_text) + "```"})
