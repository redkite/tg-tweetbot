from tweepy import StreamListener
from tweepy import Stream
import tweepy
from telegram import Bot
from telegram import ParseMode
from telegram.error import TimedOut
from telegram.utils.helpers import escape_markdown
import logging
import yaml

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

with open('config.yaml', 'r') as cfgfile:
    cfg = yaml.load(cfgfile)

TWITTER_CONSUMER_KEY = cfg['twitter']['consumer_key']
TWITTER_CONSUMER_SECRET = cfg['twitter']['consumer_secret']
TWITTER_ACCESS_KEY = cfg['twitter']['access_key']
TWITTER_ACCESS_SECRET = cfg['twitter']['access_secret']

TG_TOKEN = cfg['telegram']['token']
TG_CHANNEL = cfg['telegram']['channel']

FOLLOW_ACCOUNTS = dict()
for account in cfg['twitter']['follow']:
    FOLLOW_ACCOUNTS[account['user']] = account['id']

REPLACEMENTS = dict()
for replacement in cfg['twitter']['replacements']:
    REPLACEMENTS[replacement['source']] = replacement['target']

auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
auth.set_access_token(TWITTER_ACCESS_KEY, TWITTER_ACCESS_SECRET)
api = tweepy.API(auth)


class StdOutListener(StreamListener):
    def on_connect(self):
        logger.info("Connection successful")
        return

    def on_status(self, status):
        logger.info("Status received")
        if status.author.screen_name in FOLLOW_ACCOUNTS.keys():
            logger.info("Sending new status to Telegram.")
            author_name = status.author.name
            author_user = status.author.screen_name
            tweet_id = status.id
            if status.truncated:
                message = status.extended_tweet['full_text']
            else:
                message = status.text
            if status.in_reply_to_status_id is not None:
                replied_to = api.get_status(id=status.in_reply_to_status_id)
                send_message(
                    "*{replied_to_author_name}* ([@{replied_to_author_user}]"
                    "(https://twitter.com/{replied_to_author_user})):\n{replied_to_message}\n"
                    "*{author_name}* "
                    "([@{author_user}](https://twitter.com/{author_user})):\n{message}\n"
                    "[Original Tweet](https://twitter.com/statuses/{tweet_id})".format(
                        tweet_id=tweet_id,
                        replied_to_author_name=escape_markdown(replied_to.author.name),
                        replied_to_author_user=replied_to.author.screen_name,
                        replied_to_message=escape_markdown(replied_to.text),
                        author_name=escape_markdown(author_name),
                        author_user=author_user,
                        message=escape_markdown(message)))
            else:
                send_message(
                    "*{author_name}* "
                    "([@{author_user}](https://twitter.com/{author_user})):\n{message}\n"
                    "[Original Tweet](https://twitter.com/statuses/{tweet_id})".format(
                        tweet_id=tweet_id,
                        author_name=escape_markdown(author_name),
                        author_user=author_user,
                        message=escape_markdown(message)))
        else:
            logger.info("Message not from followed Account, skipping...")

    def on_error(self, status):
        if status == 420:
            logger.error("Received 420 from Twitter, aborting")
            return False


def send_message(text):
    for source, target in REPLACEMENTS.items():
        text = text.replace(source, target)
    logger.info("Sending: %s" % text)
    try:
        bot.send_message(chat_id=TG_CHANNEL, text=text, parse_mode=ParseMode.MARKDOWN,
                         disable_web_page_preview=True, timeout=10)
    except TimedOut as err:
        logger.error("Connection to Telegram time out with %s" % str(err))
        reset_tg_connection()
        bot.send_message(chat_id=TG_CHANNEL, text=text, parse_mode=ParseMode.MARKDOWN,
                         disable_web_page_preview=True, timeout=10)


def reset_tg_connection():
    logger.info("Connecting to Telegram API")
    bot = Bot(token=TG_TOKEN)


if __name__ == '__main__':
    logger.info("Connecting to Telegram API")
    bot = Bot(token=TG_TOKEN)
    logger.info("Registering Twitter listener")
    listener = StdOutListener()
    twitterStream = Stream(auth, listener)

    follow = list()
    for id in FOLLOW_ACCOUNTS.values():
        follow.append(id)
    twitterStream.filter(follow=follow)
