import tweepy
import os
import sys
import telegram_send
import winsound
import datetime as dt
from binance.client import Client
import time

# -----------------------------
# GLOBAL VARS:
# -----------------------------
# POSITION SIZE IN % OF TOTAL BALANCE:
POSITION_PERCENTAGE = 90
POSITION_PERCENTAGE_SMALL = 2  # IN CASE OF A DOGE REPLY!    50
LEVERAGE = 30
LEVERAGE_SMALL = 1  # IN CASE OF A DOGE REPLY!    10
# Elon Musk Twitter ID
TWITTER_ID_ELON = "44196397"
TWITTER_ID_SAM = "604292447"
# -----------------------------
# ENVIRONMENTAL VARIABLES:
# -----------------------------
# authorization tokens
CONSUMER_KEY = os.environ.get("CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("CONSUMER_SECRET")
ACCESS_KEY = os.environ.get("ACCESS_TOKEN")
ACCESS_SECRET = os.environ.get("ACCESS_SECRET")


# Function that checks whether the status object is from original creator or not
# It will only print/save tweet if it is from the original creator.

def from_creator(status):
    if hasattr(status, 'retweeted_status'):
        return False
    elif status.in_reply_to_status_id is not None:
        return False
    elif status.in_reply_to_screen_name is not None:
        return False
    elif status.in_reply_to_user_id is not None:
        return False
    else:
        return True


# StreamListener class inherits from tweepy.StreamListener and overrides on_status/on_error methods.
class StreamListener(tweepy.StreamListener):
    def on_status(self, status):

        if from_creator(status):
            # if "retweeted_status" attribute exists, flag this tweet as a retweet.
            is_retweet = hasattr(status, "retweeted_status")

            # check if text has been truncated
            if hasattr(status, "extended_tweet"):
                text = status.extended_tweet["full_text"]
            else:
                text = status.text

            # check if this is a quote tweet.
            is_quote = hasattr(status, "quoted_status")
            quoted_text = ""
            if is_quote:
                # check if quoted tweet's text has been truncated before recording it
                if hasattr(status.quoted_status, "extended_tweet"):
                    quoted_text = status.quoted_status.extended_tweet["full_text"]
                else:
                    quoted_text = status.quoted_status.text

            # remove characters that might cause problems with csv encoding
            remove_characters = [",", "\n"]
            for c in remove_characters:
                text.replace(c, " ")
                quoted_text.replace(c, " ")

            # with open("csv.csv", "a", encoding='utf-8') as f:
            #     f.write("%s,%s,%s,%s,%s,%s,%s\n" % (status.created_at,status.user.screen_name,is_retweet,is_quote,text,quoted_text,status.id_str))

            with open('csv.csv') as csv_file:
                tweets = csv_file.read()
                tweet_list = tweets.split(',')

            new_doge_tweet = (status.id_str not in tweet_list) and (
                        "doge" in text or "Doge" in text) and not is_retweet and not is_quote
            new_non_doge_tweet = (status.id_str not in tweet_list) and (
                        "doge" not in text and "Doge" not in text) and not is_retweet and not is_quote

            if new_non_doge_tweet:
                # NEW NON-DOGE TWEET
                # PRINT TO CONSOLE
                print("NON-DOGE TWEET")
                print("TWEET ID: ", status.id_str)
                print(f"LINK: https://twitter.com/twitter/statuses/{status.id_str}")
                print("TWEET: ", text)
                print("-------------------------------")
                # MAKE NOISE
                duration = 3000  # milliseconds
                freq = 800  # Hz
                winsound.Beep(freq=800, duration=3000)
                # SAVE TWEET ID TO CSV
                with open("csv.csv", "a", encoding='utf-8') as csv_file:
                    csv_file.write(f",{status.id_str}")
                # SEND TELEGRAM MESSAGE
                telegram_send.send(messages=[f"NON-DOGE TWEET:\n"
                                             f"https://twitter.com/twitter/statuses/{status.id_str}"])

            if new_doge_tweet:
                # BINANCE CLIENT
                client = Client(os.environ.get("API_KEY"), os.environ.get("API_SECRET"))
                balance = float(client.futures_account_balance()[1]['balance'])
                position_size = round(balance * (POSITION_PERCENTAGE / 100), 2)

                # DOGE PRICE IN $:
                doge_data = client.futures_coin_mark_price(symbol="DOGEUSD_PERP")
                doge_price = float(doge_data[0]["markPrice"])

                # POSITION SIZE:
                quantity_raw = position_size / doge_price
                quantity = int(quantity_raw)

                # PLACE ORDER ON BINANCE FUTURES
                try:
                    client.futures_change_margin_type(symbol='DOGEUSDT', marginType='CROSSED')
                except:
                    pass
                client.futures_change_leverage(symbol='DOGEUSDT', leverage=LEVERAGE)
                client.futures_create_order(symbol="DOGEUSDT", side="BUY", type="MARKET", quantity=quantity)

                # CONSOLE ORDER MESSAGE
                print("DOGE TWEET!")
                print("TWEET ID: ", status.id_str)
                print(f"LINK: https://twitter.com/twitter/statuses/{status.id_str}")
                print("TWEET: ", text)
                print(f"BOT SENDS BUY ORDER. BUY {quantity} DOGEUSDT Perpetual at $ {doge_price}")
                print(f"{dt.datetime.now().strftime('%x %X')}\n-------------------------------")

                # TELEGRAM ORDER MESSAGE
                telegram_send.send(messages=[f"DOGE TWEET:\n"
                                             f"https://twitter.com/twitter/statuses/{status.id_str}\n"
                                             f"BOT SENDS BUY ORDER!\nBUY {quantity} "
                                             f"DOGEUSDT Perpetual at $ {doge_price}."])

                # CHECK IF ORDER STATUS IS FILLED
                time.sleep(3)
                orders = client.futures_get_all_orders()
                last_order = orders[-1]

                # PLACE STOP-LOSS ORDER
                if last_order['status'] == "FILLED":
                    stop_price = round((float(last_order['avgPrice']) * 0.99), 4)
                    client.futures_create_order(symbol="DOGEUSDT", side="SELL", type="STOP_MARKET",
                                                closePosition="true", stopPrice=stop_price)
                    # CONSOLE STOP-LOSS MESSAGE
                    print("BUY ORDER FILLED. BOT SENDS STOP-LOSS ORDER.")
                    print("-------------------------------")
                    # TELEGRAM STOP-LOSS MESSAGE
                    telegram_send.send(messages=["BUY ORDER FILLED. BOT SENDS STOP-LOSS ORDER."])

                # MAKE NOISE
                duration = 3000  # milliseconds
                freq = 800  # Hz
                winsound.Beep(freq, duration)

                # SAVE TWEET ID TO CSV
                with open("csv.csv", "a", encoding='utf-8') as csv_file:
                    csv_file.write(f",{status.id_str}")

                # EXIT PROGRAM
                sys.exit()

        if status.in_reply_to_status_id != None:
            # tweet is a reply (containing doge)
            # if "retweeted_status" attribute exists, flag this tweet as a retweet.
            is_retweet = hasattr(status, "retweeted_status")

            # check if text has been truncated
            if hasattr(status, "extended_tweet"):
                text = status.extended_tweet["full_text"]
            else:
                text = status.text

            # check if this is a quote tweet.
            is_quote = hasattr(status, "quoted_status")
            quoted_text = ""
            if is_quote:
                # check if quoted tweet's text has been truncated before recording it
                if hasattr(status.quoted_status, "extended_tweet"):
                    quoted_text = status.quoted_status.extended_tweet["full_text"]
                else:
                    quoted_text = status.quoted_status.text

            # remove characters that might cause problems with csv encoding
            remove_characters = [",", "\n"]
            for c in remove_characters:
                text.replace(c, " ")
                quoted_text.replace(c, " ")

            # with open("csv.csv", "a", encoding='utf-8') as f:
            #     f.write("%s,%s,%s,%s,%s,%s,%s\n" % (status.created_at,status.user.screen_name,is_retweet,is_quote,text,quoted_text,status.id_str))

            with open('csv.csv') as csv_file:
                tweets = csv_file.read()
                tweet_list = tweets.split(',')

            new_doge_reply = (status.id_str not in tweet_list) and (
                        "doge" in text or "Doge" in text) and not is_retweet and not is_quote
            if new_doge_reply:
                # TELEGRAM ALERT MESSAGE
                telegram_send.send(messages=[f"DOGE (REPLY) TWEET:\n"
                                             f"https://twitter.com/twitter/statuses/{status.id_str}"])
                # CONSOLE ALERT MESSAGE
                print("DOGE (REPLY) TWEET!")
                print("REPLY TWEET ID: ", status.id_str)
                print(f"LINK: https://twitter.com/twitter/statuses/{status.id_str}")
                print("REPLY TWEET: ", text)

                ## USE BELOW CODE TO PLACE AN ORDER IN CASE OF AN ELON DOGE REPLY
                # # BINANCE CLIENT
                # client = Client(os.environ.get("API_KEY"), os.environ.get("API_SECRET"))
                # balance = float(client.futures_account_balance()[1]['balance'])
                #
                # # use 50% of balance in case of a doge reply tweet!!!!!
                # position_size = round(balance * (POSITION_PERCENTAGE_SMALL / 100), 2)
                #
                # # DOGE PRICE IN $:
                # doge_data = client.futures_coin_mark_price(symbol="DOGEUSD_PERP")
                # doge_price = float(doge_data[0]["markPrice"])
                #
                # # POSITION SIZE:
                # quantity_raw = position_size / doge_price
                # quantity = int(quantity_raw)
                #
                # # PLACE ORDER ON BINANCE FUTURES !!!!!!!!!!!!!!!!!!!!!!!!
                # try:
                #     client.futures_change_margin_type(symbol='DOGEUSDT', marginType='CROSSED')
                # except:
                #     pass
                # # in case of a reply use 10x leverage
                # client.futures_change_leverage(symbol='DOGEUSDT', leverage=LEVERAGE_SMALL)
                # client.futures_create_order(symbol="DOGEUSDT", side="BUY", type="MARKET", quantity=quantity)
                #
                # # CONSOLE ORDER MESSAGE
                # print("DOGE (REPLY) TWEET!")
                # print("REPLY TWEET ID: ", status.id_str)
                # print(f"LINK: https://twitter.com/twitter/statuses/{status.id_str}")
                # print("REPLY TWEET: ", text)
                # print(f"BOT SENDS BUY ORDER. BUY {quantity} DOGEUSDT Perpetual at $ {doge_price}")
                # print(f"{dt.datetime.now().strftime('%x %X')}\n-------------------------------")
                #
                # # TELEGRAM ORDER MESSAGE
                # telegram_send.send(messages=[f"DOGE (REPLY) TWEET:\n"
                #                              f"https://twitter.com/twitter/statuses/{status.id_str}\n"
                #                              f"BOT SENDS BUY ORDER!\nBUY {quantity} "
                #                              f"DOGEUSDT Perpetual at $ {doge_price}."])
                #
                # # CHECK IF ORDER STATUS IS FILLED  !!!!!!!!!!!!!!!!!!!!!!!!
                # time.sleep(3)
                # orders = client.futures_get_all_orders()
                # last_order = orders[-1]
                #
                # # PLACE STOP-LOSS ORDER  !!!!!!!!!!!!!!!!!!!!!!!!
                # if last_order['status'] == "FILLED":
                #     stop_price = round((float(last_order['avgPrice']) * 0.99), 4)
                #     client.futures_create_order(symbol="DOGEUSDT", side="SELL", type="STOP_MARKET",
                #                                 closePosition="true", stopPrice=stop_price)
                #     # CONSOLE STOP-LOSS MESSAGE
                #     print("BUY ORDER FILLED. BOT SENDS STOP-LOSS ORDER.")
                #     print("-------------------------------")
                #     # TELEGRAM STOP-LOSS MESSAGE
                #     telegram_send.send(messages=["BUY ORDER FILLED. BOT SENDS STOP-LOSS ORDER."])

                # MAKE NOISE
                duration = 3000  # milliseconds
                freq = 800  # Hz
                winsound.Beep(freq, duration)

                # SAVE TWEET ID TO CSV
                with open("csv.csv", "a", encoding='utf-8') as csv_file:
                    csv_file.write(f",{status.id_str}")

                # EXIT PROGRAM
                sys.exit()

    def on_error(self, status_code):
        print("Encountered streaming error (", status_code, ")")
        telegram_send.send(messages=["BOT ERROR!!!!"])
        sys.exit()


if __name__ == "__main__":
    # complete authorization and initialize API endpoint
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
    api = tweepy.API(auth)

    # initialize stream
    while True:
        try:
            streamListener = StreamListener()
            stream = tweepy.Stream(auth=api.auth, listener=streamListener, tweet_mode='extended')
            stream.filter(follow=[TWITTER_ID_ELON])
        except:
            time.sleep(1)
            continue
