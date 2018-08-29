from AlexaBaseHandler import AlexaBaseHandler
import os
import requests
import inflect
from datetime import datetime as date
import json
import pytemperature
import boto3
#module broken will look for alternative some day..
#from yahoo_finance import Share


class AlexaLogicHandler(AlexaBaseHandler):
    """
    Sample concrete implementation of the AlexaBaseHandler to test the
    deployment scripts and process.
    All on_ handlers call the same test response changing the request type
    spoken.
    """

    def __init__(self):
        super(self.__class__, self).__init__()

    def _test_response(self, title, output, msg):
        session_attributes = {}
        card_title = title
        card_output = output
        speech_output = msg
        # If the user either does not reply to the welcome message or says something
        # that is not understood, they will be prompted again with this text.
        reprompt_text = "sorry, what did you say?"
        should_end_session = False

        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))

    # utterance "..introduce yourself"
    def _say_hello(self, intent, session):
        
        requests.packages.urllib3.disable_warnings()

        location = os.environ['WEATHER_LOCATION'] # can be any capital city
        r = requests.get(
            "http://api.openweathermap.org/data/2.5/weather?q={0},AU&appid={1}".format(location,os.environ['OPENWEATHER_APIKEY']),
            verify=False)
        weather = r.json()
        
        temp_raw = weather["main"]["temp"] # in Kelvin
        temp_clean = round(pytemperature.k2c(temp_raw),1)

        session_attributes = {}
        day = date.today().strftime("%A")
        card_title = "Introducing myself"
        
        message = "Hello! Thank you for allowing me to introduce myself. My name is Alexa and it's a pleasure to meet you today in {0}, and I hope you are having a fantastic {1}. In case you were wondering, the weather outside is currently {2} degrees celcius.".format(location,day,temp_clean)
        
        card_output = "Greetings! I'm the Bank of Alexa"
        speech_output = message
        # If the user either does not reply to the welcome message or says something
        # that is not understood, they will be prompted again with this text.
        reprompt_text = "I am sorry, can you repeat your request?"
        should_end_session = True

        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))

    def interact_bank_account(self,method,payload):
        requests.packages.urllib3.disable_warnings()
        print ("accessing API GW for bank account details")
        if method == "GET": # retrieving account balance
            url = os.environ['BANKOFALEXA_APIGW']
            r = requests.get(url)
            return (r.json())
        elif method == "POST": # when sending updated values to DDB
            """
                Using Boto3 client instance instead to use update_item method to retain transaction data
            """
            print ("the payload used for boto: {}".format(payload))
            client = boto3.client("dynamodb","us-east-1")
            myKey = {'account_type': {"S": str(payload["account_type"])}}
            myVal = {':b': {"S": str(payload["balance"])}}
            response = client.update_item(                                                                           
                TableName = "BankOfAlexa",                                                                                 
                Key = myKey,                                                                                                
                UpdateExpression = "SET balance = :b",                                                                     
                ExpressionAttributeValues=myVal                                                                            
            ) 
            return (response)
        else:
            message = "error encountered at interact_bank_account as method: {} is not supported".format(method)
            print (message)
            return (message)

    def _welcome(self):
        session_attributes = {}
        card_title = "Welcome to the Bank of Alexa"
        message = "Welcome to the Bank of Alexa. Please authenticate by saying, my passcode is, followed by your 4 digit security code"
        card_output = "Please authenticate using your 4 Digit Code"
        speech_output = message

        # the user either does not reply to the welcome message or says something
        # that is not understood, they will be prompted again with this text.
        reprompt_text = "I am sorry, can you repeat your request?"
        should_end_session = False

        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))

    # utterance ".. how much is in my X account? (slots: debit, mortgage, credit, savings)"
    def _get_balance(self, intent, session):
        session_attributes = session["attributes"]
        card_title = "Current Account Balance"
        card_output = ""
        should_end_session = False
        balance = 0.00
        account_summary = self.interact_bank_account("GET",None)
        valid_types = [x['account_type']['S'] for x in account_summary]
        
        try:
            if 'Account' in intent['slots']:
                account_type = intent['slots']['Account']['value']

                if account_type in valid_types:
                    for acc in account_summary:
                        if account_type == acc['account_type']['S']:
                            balance = float(acc['balance']['S'])
                            balance_arr = self._format_currency(balance)
                            p = inflect.engine()
                            message = "You have %s dollars and %s cents in your %s account." % (p.number_to_words(balance_arr[0]), balance_arr[1], account_type)
                            speech_output = message
                            card_output = message
                            reprompt_text = "You can ask me a balance to retrieve by saying for example, What is my savings account balance?"
                else: # when value given foro account type does not match existing intent slot values
                    message = "I'm sorry, I was unable to detect the type of account you are after. I can support debit, mortgage, credit and savings"
                    card_output = "Unable to detect valid account type"
                    speech_output =  message
                    reprompt_text =  "I'm sorry, I was unable to detect the type of account you are after. I can support debit, mortgage, credit and savings"
        except Exception as e:
            print ("Exception caught on _get_balance as: {0}".format(e))
            message = "I'm sorry, I was unable to detect the type of account you are after. I can support debit, mortgage, credit and savings"
            speech_output =  message
            reprompt_text =  message
            card_title = "Uh-Oh"
            card_output = "Computer says no."


        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))

    def _format_currency(self, balance):
        balance_str = "%.2f" % balance
        balance_arr = balance_str.split(".")

        if balance_arr[1] == "00":
            balance_arr[1] = "0"
        return (balance_arr)

    def _get_pub_spend(self, intent, session):
        session_attributes = session["attributes"]
        card_title = "Beer Money at the Pub"
        card_output = ""
        should_end_session = False
        balance = 0
        account_summary = self.interact_bank_account("GET",None)

        for acc in account_summary:
            if acc['account_type']['S'] == "savings":
                balance = float(acc['balance']['S'])

        balance_arr = self._format_currency(balance)

        price_per_beer = 8.0
        number_of_beers = (balance / price_per_beer)
        number_of_beers = int(number_of_beers)

        message = "You have %s dollars and %s cents in your savings account. " % (balance_arr[0], balance_arr[1])
        message += "Based on today's prices, %s dollars per beers, you can run your savings dry by buying %s beers" % (str(price_per_beer), str(number_of_beers))

        card_output = "Drink your beers, just don't pour it on me!"
        speech_output = message
        reprompt_text = "You can ask me a balance to retrieve by saying for example, What is my savings account balance?"
        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)
        return (self._build_response(session_attributes, speechlet))

    # utterance ".. what accounts do I have?"
    def _list_account(self, intent, session):
        session_attributes = session["attributes"]
        card_title = "Listing my accounts"
        message = "You have a debit, mortgage, credit and a savings account. " #lazy
        card_output = "Debit, Mortage, Credit and Savings"
        should_end_session = False
        # should really get list from slots, not hard coding..        
        speech_output = message
        reprompt_text = "I am sorry, I didnt catch that, can you please repeat your request"

        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))

    def _do_transfer(self, intent, session):

        session_attributes = session["attributes"]
        card_title = "Transferring Money"
        card_output = ""
        reprompt_text = "I am sorry, can you repeat your request?"
        speech_output = "Transferring Money"
        should_end_session = False
        account_summary = self.interact_bank_account("GET",None)
        valid_types = [x['account_type']['S'] for x in account_summary]
        sourceValid = None
        accountValid = None
        try:
            amountDollars = intent['slots']['AmountDollars']['value']
            # check if there is cents, else assign it to 0
            if not 'value' in intent['slots']['AmountCents']:
                amountCents = "0"
            else:
                amountCents = intent['slots']['AmountCents']['value']

            if 'SourceAccount' in intent['slots']:
                try:    
                    if intent['slots']['SourceAccount']['value'] in valid_types:
                        sourceAccount_type = intent['slots']['SourceAccount']['value']
                except Exception as e:
                    print ("unable to detect source account in utterance: {}".format(e))
                    
            if 'DestinationAccount' in intent['slots']:
                try:
                    if intent['slots']['SourceAccount']['value'] in valid_types:
                        destinationAccount_type = intent['slots']['DestinationAccount']['value']
                except Exception as e:
                    print ("unable to detect Destination account in utterance: {}".format(e))
                    
            try:  
                if (destinationAccount_type == sourceAccount_type):
                    # if account type is not supported types
                    if intent['slots']['SourceAccount']['value'] in valid_types:
                        message = "I'm Sorry. You cannot move funds to the same account"
            except Exception as e:
                print ("Error detecting if source and des account is same: {}".format(e))

            try:
                if sourceAccount_type and destinationAccount_type: # if both source and destination account not present, will throw exception and retry message
                    print ("source: {} dest: {}".format(sourceAccount_type,destinationAccount_type))
                    try:  
                        if not destinationAccount_type == sourceAccount_type:
                            if intent['slots']['SourceAccount']['value'] in valid_types: # supported slot value
                                for acc in account_summary:
                                    if acc['account_type']['S'] == sourceAccount_type:
                                        sourceBalance = float(acc['balance']['S']) # current
                                        # calculate the new balance and send updated values 
                                        newSourceBalance = sourceBalance - float(amountDollars) - float(amountCents) / 100 # new value
                                        # prevent transfer with value more than existing (also screws up dashboard chart rendering)
                                        if not newSourceBalance < 0: 
                                            newSourceBalance_arr = self._format_currency(newSourceBalance)
                                            # send the updated value to DDB
                                            payload = {"account_type": sourceAccount_type, "balance": newSourceBalance}
                                            self.interact_bank_account("POST",payload)
                                        else: # illegal transfer attempt, will return insufficient message later
                                            sourceValid = False
                                    if not sourceValid is False: 
                                        if acc['account_type']['S'] == destinationAccount_type:
                                            destinationBalance = float(acc['balance']['S'])
                                            # calculate the new balance and send updated values 
                                            newDestinationBalance = destinationBalance + float(amountDollars) + float(amountCents) / 100 # new value
                                            if not newDestinationBalance < 0:
                                                newDestinationBalance_arr = self._format_currency(newDestinationBalance)
                                                # send the updated value to DDB
                                                payload = {"account_type": destinationAccount_type, "balance": newDestinationBalance}
                                                self.interact_bank_account("POST",payload)        
                        else:
                            accountValid = False
                    except Exception as e:
                        print ("Error detecting if source and des account is same: {}".format(e))
            except NameError: # sourceAccount_type or destinationAccount_type not defined (missing input)
                print ("Either sourceAccount_type or destinationAccount_type doesnt exist!")
                pass # continue on
            except:
                print ("some other error")
                pass
                
            try:
                if accountValid is False:
                    message = "Sorry, you can't transfer between the same account."
                    speech_output = message
                    card_title = "You can't transfer from and to the same account!"
                    reprompt_text = "I am sorry, can you repeat your request?"
                if sourceValid is False:
                    message = "Sorry, you have insufficient amount for that transaction. Please check the amount and try again."
                    speech_output = message
                    card_title = "transferring money - insufficient amount"
                    card_output = "Insufficient amount for transfer"
                    reprompt_text = "I am sorry, can you repeat your request?"

                else:
                    p = inflect.engine() # to make sound output for audio good
                    message = "Thank you. I will move " + amountDollars + " dollars and " + amountCents + " cents from your " + sourceAccount_type + " account to your " + destinationAccount_type + " account. "
                    message += "In your {} account, you now have {} dollars and {} cents. ".format(sourceAccount_type,p.number_to_words(newSourceBalance_arr[0]),p.number_to_words(newSourceBalance_arr[1]))
                    message += "In your {} account, you now have {} dollars and {} cents. ".format(destinationAccount_type,p.number_to_words(newDestinationBalance_arr[0]),p.number_to_words(newDestinationBalance_arr[1]))
                    message += "Would you like to do another transfer?"
                    speech_output = message
                    card_title = "transferring money"
                    card_output = "Transferring ${}.{} from {} to {}".format(amountDollars,amountCents,sourceAccount_type,destinationAccount_type)
                    reprompt_text = "I am sorry, can you repeat your request?"

            except Exception as e:
                print ("Exception caught on _do_transfer [2nd Excep] as: {0}".format(e))
                message = "I was unable to complete the transaction. Please try again."      
                speech_output = message
                card_title = "Uh-Oh"
                card_output = "Computer says no."
                reprompt_text = "I am sorry, can you repeat your request?"
        except Exception as e:
            print ("Exception caught on _do_transfer [1st Excep] as: {0}".format(e))
            message = "I was unable to complete the transaction. Please try again."      
            speech_output = message
            card_title = "Uh-Oh"
            card_output = "Computer says no."
            reprompt_text = "I am sorry, can you repeat your request?"
            

        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))

    def _get_transaction(self, intent, session):
        session_attributes = session["attributes"]
        card_title = "Transaction History"
        card_output = ""
        reprompt_text = "I am sorry, can you repeat your request?"
        speech_output = "Transaction History"
        should_end_session = False

        try:
            if 'Account' in intent['slots']:
                account_type = intent['slots']['Account']['value']
                # debugging section
                print ("input account type in slot: {}".format(account_type))
                print ("type of account in slot: {}".format(type(account_type)))

                response = self.interact_bank_account("GET",None) # get data from DDB
                for r in response:
                    # debugging
                    print ("input: {} and comparing with: {}".format(account_type,r["account_type"]["S"]))
                    if r["account_type"]["S"] == account_type:
                        data_t = r['transactions']['M'] # JSON of transactions     
                    else:
                        print ("unable to match input: {} with list of supported account types.".format(account_type))# will go to exception and return unsupported type message to user

                message = "You have {} transactions in your {} account. ".format(str(len(data_t)),account_type)
                 
                for t in data_t:
                    date = data_t[t]['M']['date']['S']
                    description = data_t[t]['M']['description']['S']
                    amount = data_t[t]['M']['value']['S'] 
                    message += "On {}, a transaction for {} dollars was made for {}. ".format(date,amount,description)
                
                message += "That's all the history for that account. Would you like any other transactions?"
                card_output = message
                speech_output = message
                reprompt_text = "I am sorry, can you repeat your request?"

        except Exception as e:
            print ("Exception caught on _get_transactions as: {0}".format(e))
            speech_output =  "I'm sorry, I was unable to detect the type of account you are after. I can support debit, mortgage, credit and savings"
            reprompt_text =  "I'm sorry, I was unable to detect the type of account you are after. I can support debit, mortgage, credit and savings"
            card_title = "Uh-Oh"
            card_output = "Computer says no."

        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))

    def _end_session(self, intent, session):
        session_attributes = {}
        card_title = "Goodbye"
        message = "Thank you for using the bank of Alexa. We will miss you, please come back soon"

        card_output = "Thank you and goodbye!"
        reprompt_text = "I am sorry, can you repeat your request?"
        speech_output = message
        should_end_session = True
        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))

    # utterance "..say hello/hi"
    def _say_hi_to_cop(self, intent, session):
        session_attributes = {}
        card_title = "Hello"
        message = "Hello. I am the Bank of Alexa. I can help you with your personal banking."
        card_output = "Hi. Let's get started."
        reprompt_text = "I am sorry, can you repeat your request?"
        speech_output = message
        should_end_session = False
        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)
        return (self._build_response(session_attributes, speechlet))

    def _get_api_payload(self):
        url = os.environ['NAB_FX_API_ENDPOINT']
        payload = {'x-nab-key': os.environ['NAB_FX_APIKEY']}  # not sure why this is here twice with header request
        requests.packages.urllib3.disable_warnings()
        
        r = requests.get(
            url,
            headers={'x-nab-key': os.environ['NAB_FX_APIKEY']},
            verify=False,
            timeout=60)
        return (r.json())

    # API payload containing JSON of all ASX listed companies' and their codes
    def _get_asx_api_payload(self):
        url = os.environ['ASX_COMPANIES_APIGW']
        requests.packages.urllib3.disable_warnings()
        
        r = requests.get(
            url,
            verify=False,
            timeout=60)
        return (r.json())

    def _list_currency(self, intent, session):
        session_attributes = session["attributes"]
        card_title = "Currency Exchange Rates"
        card_output = ""
        speech_output = "Currency Exchange Rates"
        should_end_session = False
        major_currency_list = ["USD","EUR","GBP","NZD","CNY","JPY"]
        currency_list = ""
        
        try:
            jData = self._get_api_payload()
            
            for fxrates in jData['fxRatesResponse']['fxRates']:
                if fxrates["buyCurrency"] in major_currency_list:
                    curr = self._pronounce_currency_(fxrates["buyCurrency"]) # changing to more friendly sounding format
                    currency_list += "{0} {1}. ".format(round(float(fxrates["currentBuyRate"]),2),curr)
            message = "Here are some of the major currency exchange rates against the Australian Dollar. " + currency_list
            card_output = currency_list
            speech_output = message
            reprompt_text = "You can ask me for a list of major currency exchange rate"
        
        except Exception as e:
            print ("Exception caught on _list_currency_ as: {0}".format(e))
            speech_output =  "I'm sorry, I was unable list the currency rates"
            reprompt_text =  "I'm sorry, I was unable list the currency rates"
            card_title = "Uh-Oh"
            card_output = "Computer says no."
        
        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)
        return (self._build_response(session_attributes, speechlet))

    def _pronounce_currency_(self,currency):
        return (
            {
            "USD": "US Dollar",
            "EUR": "Euro",
            "GBP": "British Pound",
            "NZD": "New Zealand Dollar",
            "CNY": "Chinese Yuan",
            "JPY": "Japanese Yen"
        }.get(currency, "")
        ) # returns nothing if currency not found
    """
    #"..get share price of X" - doesnt work: yahoo_finance module broken
    def _get_share_price(self, intent, session):
        session_attributes = session["attributes"]
        card_title = "Share Price"
        card_output = "Share Price"
        reprompt_text = "I am sorry, can you repeat your request?"
        speech_output = ""
        should_end_session = False

        try:
            if 'Company' in intent['slots']:
                company_name = intent['slots']['Company']['value']

                jData = self._get_asx_api_payload()
                
                company_name = company_name.upper()
                print ("Got {0} as the company name".format(company_name))
                
                for i in jData:
                    print ("Searching {0} against {1}".format(company_name,str(i["Company"])))

                    if company_name in str(i["Company"]):
                        print ("Found Company in the list. Querying stock price for {0}".format(company_name))
                        code = str(i["Code"])
                        code += ".AX" # adding for Australian Market. Required for yahoo_finance module
                        print ("Ticket code: {0}".format(code))
                        balance_arr = self._format_currency(float(Share(code).get_price()))
                        print (balance_arr)


                        message = "You have chosen {0}. The current share price for this company is {1} dollars and {2} cents. ".format(company_name,balance_arr[0],balance_arr[1])
                        message += "Would you like any other transactions?"
                        
                        speech_output = message
                        card_output = message
                        break # stop searching

        except Exception as e:
            print ("Exception caught on _get_share_price as: {0}".format(e))
            speech_output =  "Sorry. I was unable to find {0} in the ASX listed companies data.".format(company_name)
            card_title = "Uh-Oh"
            card_output = "Computer says no."

        speechlet = self._build_speechlet_response(
            card_title, card_output, speech_output, reprompt_text,
            should_end_session)

        return (self._build_response(session_attributes, speechlet))
    """
    def _set_passCode(self, intent, session):
        session_attributes = {}
        card_title = "Setting PassCode"
        card_output = ""
        reprompt_text = "I am sorry, can you repeat your request?"
        speech_output = ""
        should_end_session = False
        
        try:
            if 'passCode' in intent['slots']:
                passCode = str(intent['slots']['passCode']['value'])
                print ("user passed passCode: {0}".format(passCode))
                # change | to do cloudformation set env var on lambda
                myPassCode = os.environ['AUTHENTICATION_PASSCODE']
                # change | set session data in dynamodb
                if passCode == myPassCode:
                    # this session attribute is used later to authenticate requests
                    session_attributes = {
                        "passCode": passCode
                    }
                    message = "Thank you. You have successfully authenticated and may now interact with your account."
                    card_output = "Successfully Authenticated."
                else:
                    message = "Sorry, that is not a valid passcode. Please try authenticating again by saying, my passcode is, followed by your 4 digit security code."
                    card_output = "Incorrect Passcode."

            speech_output = message
            
        except Exception as e:
            print ("Exception caught on _set_passCode as: {0}".format(e))
            speech_output = "Sorry. I was unable to detect a valid passCode. Please try again."
            card_title = "Invalid Passcode"
            card_output = "Invalid Passcode" 
        
        speechlet = self._build_speechlet_response(
        card_title, card_output, speech_output, reprompt_text,
        should_end_session)

        return (self._build_response(session_attributes, speechlet))
    
    def _get_passCode(self, session):
        # change | to do check dynamodb session
        print ("Checking if session is authenticated")
        try:
            data = session["attributes"]["passCode"]
            print ("Detected an authenticated session: {0}".format(data))
            return (True)
        except Exception as e:
            print ("Unable to detect authenticated session: {0}".format(e))   
            return (False)

    def on_processing_error(self, event, context, exc):
        print ("processing error")
        return (self._test_response("processing error", "processing error", "processing error as: {}".format(exc)))

    def on_launch(self, launch_request, session):
        return (self._welcome())

    def on_session_started(self, session_started_request, session):
        return (self._test_response("session started", "session started", "on session started"))

    def on_intent(self, intent_request, session):
        intent = intent_request['intent']
        intent_name = intent_request['intent']['name']
        print ("detected intent: {}".format(intent_name))

        if self._get_passCode(session) is False: # not an authenticated session, only allow some intents
            print ("UnAuth session. Selecting routing from available intents")
            if intent_name == "CopIntent":
                return (self._say_hi_to_cop(intent, session))
            elif intent_name == "SayHelloIntent":
                return (self._say_hello(intent, session))
            elif intent_name == "AuthenticateIntent":
                return (self._set_passCode(intent, session))
            elif intent_name == "EndSession":
                return (self._end_session(intent, session))
            else:
                return (self._test_response("No matching intent", "No matching intent", "Sorry, I wasn't able to detect an authenticated session. Please try authenticating first by saying, my passcode is, followed by your 4 digit security code."))
        else: # authenticated session
            print ("Authenticated session. Selecting routing from available intents")
            # Dispatch to your skill's intent handlers
            if intent_name == "ListCurrencyIntent":
                return (self._list_currency(intent, session))
            elif intent_name == "BalanceIntent":
                return (self._get_balance(intent, session))
            elif intent_name == "ListAccountIntent":
                return (self._list_account(intent, session))
            elif intent_name == "EndSession":
                return (self._end_session(intent, session))
            elif intent_name == "TransactionIntent":
                return (self._get_transaction(intent, session))
            elif intent_name == "TransferIntent":
                return (self._do_transfer(intent, session))
            elif intent_name == "getPubSpend":
                return (self._get_pub_spend(intent, session))
            elif intent_name == "CopIntent":
                return (self._say_hi_to_cop(intent, session))
            elif intent_name == "SayHelloIntent":
                return (self._say_hello(intent, session))
            #elif intent_name == "SharePriceIntent":
             #   return (self._get_share_price(intent, session))
            elif intent_name == "AuthenticateIntent":
                return (self._set_passCode(intent, session))
            else:
                return (self._test_response("Unable to find matching intent", "Unable to find matching intent", "on intent"))
                
    def on_session_ended(self, session_end_request, session):
        return (self._test_response("session ended", "session ended", "on session end"))
